from typing import List, Optional

from loguru import logger
from sqlalchemy import text

from app.core.settings import settings
from app.db.dependencies import pg_client
from app.db.models import PgVectorCollection
from app.schemas.retrieval_schema import RetrievalRecord
from app.utils.openai_connect import embed


class RetrievalService:
    """Service for retrieving and searching vector-based or keyword-based data."""

    def __init__(self, client: pg_client) -> None:
        self.client = client

    async def get_collection(self, collection_name: str) -> PgVectorCollection:
        """Retrieve a PgVectorCollection object by name."""
        try:
            return await self.client.get_collection(collection_name)
        except Exception as e:
            logger.exception("Unhandled exception", exc_info=e)
            raise e from None

    async def search(
        self,
        query: str,
        collection_name: str,
        top_k: int = 5,
        score_threshold: float = 0.5,
        filter_source: Optional[str] = None,
    ) -> List[RetrievalRecord]:
        """Perform semantic vector search using embedding and score filtering."""
        collection = await self.get_collection(collection_name)
        is_success, query_embedding, usage = embed([query])

        logger.info(f"Embedding usage: {usage}")
        if not is_success:
            raise ValueError("Failed to embed query")

        try:
            results = await collection.query(
                query=query_embedding[0],
                limit=top_k,
                filter_dict={"source": {"$eq": filter_source}}
                if filter_source
                else None,
            )
            return [
                RetrievalRecord(
                    content=record.payload.payload["content"],
                    title=record.payload.payload.get("title"),
                    source=record.payload.payload.get("source"),
                    type=record.payload.payload.get("type"),
                    score=record.score,
                    search_type="semantic",
                )
                for record in results
                if record.score >= score_threshold
            ]
        except Exception as e:
            logger.exception("Unhandled exception", exc_info=e)
            raise e from None

    async def get_all_chunks(self, collection_name: str) -> List[RetrievalRecord]:
        """Retrieve all chunks from a given collection."""
        collection = await self.get_collection(collection_name)
        try:
            return await collection.query_all()
        except Exception as e:
            logger.exception(e)
            raise e

    async def delete_all_chunks(self, collection_name: str) -> int:
        """Delete all chunks from a given collection and return the count of deleted items."""
        collection = await self.get_collection(collection_name)
        try:
            # Get all records to count them
            records = await collection.query_all()
            deleted_count = len(records)

            # Delete all records using a SQL DELETE statement
            async with self.client.session_maker() as session:
                await session.execute(
                    text(f"DELETE FROM {settings.DB_VECTOR_SCHEMA}.{collection_name}")
                )
                await session.commit()

            return deleted_count
        except Exception as e:
            logger.exception(f"Error deleting all chunks: {e}")
            raise e

    async def get_chat_history(self, session_id: str) -> list:
        """
        Retrieve all messages for a given session_id and sort them by timestamp.

        Returns:
            A list of message dicts: [{"role": ..., "content": ...}, ...]
        """
        collection = await self.client.get_or_create_collection(
            "vimo_chat_history", 1536
        )
        try:
            records = await collection.query_all()
            messages = [
                r.payload for r in records if r.payload.get("session_id") == session_id
            ]
            messages.sort(key=lambda x: x["timestamp"])
            return [{"role": m["role"], "content": m["content"]} for m in messages]
        except Exception:
            return []

    async def keyword_search(
        self,
        query: str,
        table_name: str,
        top_k: int = 5,
    ) -> List[RetrievalRecord]:
        """Perform keyword-based search using PostgreSQL full-text search."""
        sql = f"""
        SELECT id,
               payload->>'content' AS content,
               payload->'metadata'->>'product_name' AS title,
               payload->'metadata'->>'source' AS source,
               payload->'metadata'->>'type' AS type,
               ts_rank_cd(
                   to_tsvector('english', payload->>'content'),
                   websearch_to_tsquery('english', :q)
               ) AS rank
        FROM {settings.DB_VECTOR_SCHEMA}.{table_name}
        WHERE to_tsvector('english', payload->>'content') @@ websearch_to_tsquery('english', :q)
        ORDER BY rank DESC
        LIMIT :limit
        """  # noqa: E501, S608

        async with self.client.session_maker() as session:
            result = await session.execute(text(sql), {"q": query, "limit": top_k})
            rows = result.fetchall()

        return [
            RetrievalRecord(
                content=row[0],
                title=row[1],
                source=row[2],
                type=row[3],
                score=1.0,
                search_type="keyword",
            )
            for row in rows
        ]

    async def hybrid_search(
        self,
        query: str,
        collection_name: str,
        top_k_semantic: int = 5,
        top_k_keyword: int = 5,
        score_threshold: float = 0.5,
        rerank: bool = False,
        top_n: int = 5,
        filter_source: Optional[str] = None,
        alpha: float = 0.5,
    ) -> List[RetrievalRecord]:
        """Hybrid search with optional re-ranking and score weighting."""
        semantic_records = await self.search(
            query=query,
            collection_name=collection_name,
            top_k=top_k_semantic,
            score_threshold=score_threshold,
            filter_source=filter_source,
        )

        keyword_records = await self.keyword_search(
            query=query,
            table_name=collection_name,
            top_k=top_k_keyword,
        )

        beta = 1.0 - alpha
        combined_scores = {}
        combined_lookup = {}

        for r in semantic_records:
            key = (r.content, r.source)
            combined_scores[key] = alpha * r.score
            combined_lookup[key] = r

        for r in keyword_records:
            key = (r.content, r.source)
            if key in combined_scores:
                combined_scores[key] += beta * r.score
            else:
                combined_scores[key] = beta * r.score
                combined_lookup[key] = r

        results = [
            RetrievalRecord(
                content=combined_lookup[k].content,
                title=combined_lookup[k].title,
                source=combined_lookup[k].source,
                type=combined_lookup[k].type,
                score=v,
                search_type=combined_lookup[k].search_type,
            )
            for k, v in combined_scores.items()
        ]

        results = sorted(results, key=lambda r: r.score, reverse=True)

        if rerank:
            results = await self._rerank_results(query, results, top_n=top_n)

        return results

    async def _rerank_results(
        self,
        query: str,
        records: List[RetrievalRecord],
        top_n: int = 5,
    ) -> List[RetrievalRecord]:
        """Re-rank retrieved records using Cohere re-rank model for better relevance."""
        from cohere import Client

        co = Client(settings.COHERE_API_KEY)

        try:
            documents = [r.content for r in records]
            reranked = co.rerank(
                query=query,
                documents=documents,
                model="rerank-english-v3.0",
                top_n=top_n,
            )

            results = []
            for r in reranked.results:
                rec = records[r.index]
                rec.score = r.relevance_score
                results.append(rec)

            return sorted(results, key=lambda r: r.score, reverse=True)
        except Exception as e:
            logger.error(f"Re-ranking failed: {e!s}")
            return records
