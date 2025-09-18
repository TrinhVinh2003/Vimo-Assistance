from __future__ import annotations

from functools import cached_property
from typing import Any, AsyncIterator, Dict, List, Optional, Type

from pgvector.sqlalchemy import Vector
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import (
    String,
    and_,
    cast,
    delete,
    or_,
    select,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import AbstractConcreteBase
from sqlalchemy.orm import Mapped, declared_attr, mapped_column

from app.db.base import Base
from app.schemas.pgvector_schema import CollectionPoint, CollectionPointResult

N_DIM = 1536


class AbstractCollection(AbstractConcreteBase, Base):
    __abstract__ = True

    id: Mapped[str] = mapped_column(
        "id",
        String,
        autoincrement=False,
        nullable=False,
        unique=True,
        primary_key=True,
    )

    @declared_attr
    def embedding(cls) -> Mapped[List[float]]:  # noqa: N805
        return mapped_column("embedding", Vector(), nullable=False)

    payload: Mapped[Dict[str, Any]] = mapped_column(
        "payload",
        JSONB,
        server_default=text("'{}'::jsonb"),
        nullable=False,
    )

    @classmethod
    async def read_all(
        cls,
        session: AsyncSession,
        include_metadata: bool,
    ) -> AsyncIterator:
        stmt = select(cls)
        stream = await session.stream_scalars(stmt.order_by(cls.id))
        async for row in stream:
            yield row

    @classmethod
    async def read_by_id(
        cls,
        session: AsyncSession,
        point_id: str,
        include_metadata: bool = False,
    ) -> AsyncIterator:
        stmt = select(cls).where(cls.id == point_id)
        return await session.scalar(stmt.order_by(cls.id))

    @classmethod
    async def create(
        cls,
        session: AsyncSession,
        id: str,
        embedding: List[float],
        payload: Dict[str, Any],
    ) -> None:
        collection = cls(
            id=id,
            embedding=embedding,
            payload=payload,
        )
        session.add(collection)
        await session.commit()
        await session.flush()

    @classmethod
    async def update(
        cls,
        session: AsyncSession,
        id: str,
        embedding: List[float],
        payload: Dict[str, Any],
    ) -> None:
        stmt = select(cls).where(cls.id == id)
        result = await session.execute(stmt)
        collection = result.scalar_one_or_none()

        if collection:
            collection.embedding = embedding
            collection.payload = payload

            await session.commit()

    @classmethod
    async def delete(cls, session: AsyncSession, id: str) -> None:
        stmt = delete(cls).where(cls.id == id)
        await session.execute(stmt)
        await session.commit()


class PgVectorCollection(BaseModel):
    collection_name: str
    dimension: int
    session_maker: async_sessionmaker[AsyncSession] = Field(..., exclude=True)
    model_config = ConfigDict(arbitrary_types_allowed=True)

    @cached_property
    def table(self) -> Type[AbstractCollection]:
        return self.build_table()

    def build_table(self) -> Type[AbstractCollection]:
        class CustomCollectionTable(AbstractCollection):
            __tablename__ = self.collection_name
            __dimensions__ = self.dimension
            __mapper_args__ = {  # noqa: RUF012
                "polymorphic_identity": self.collection_name,
                "concrete": True,
            }
            __table_args__ = {"extend_existing": True}  # noqa: RUF012

            @declared_attr
            def embedding(cls) -> Mapped[List[float]]:  # noqa: N805
                return mapped_column(
                    "embedding",
                    Vector(self.dimension),
                    nullable=False,
                )

        return CustomCollectionTable

    async def insert(
        self,
        id: str,
        embedding: List[float],
        payload: Dict[str, Any],
    ) -> None:
        async with self.session_maker() as session:
            await self.table.create(
                session=session,
                id=id,
                embedding=embedding,
                payload=payload,
            )

    async def insert_many(
        self,
        ids: List[str],
        embeddings: List[List[float]],
        payloads: List[Dict[str, Any]],
    ) -> None:
        async with self.session_maker() as session:
            for id, embedding, payload in zip(ids, embeddings, payloads):
                await self.table.create(
                    session=session,
                    id=id,
                    embedding=embedding,
                    payload=payload,
                )

    async def create(self) -> None:
        pass

    async def delete(self, id: str) -> None:
        async with self.session_maker() as session:
            await self.table.delete(session=session, id=id)

    async def query(
        self,
        query: List[float],
        limit: int = 10,
        filter_dict: Optional[Dict[str, Any]] = None,
    ) -> List[CollectionPointResult]:
        if self.table is None:
            return []

        stmt = select(self.table).order_by(self.table.embedding.cosine_distance(query))
        # add column with cosine similarity
        stmt = stmt.column(
            (1 - self.table.embedding.cosine_distance(query)).label(
                "cosine_similarity",
            ),
        )
        if filter_dict is not None:
            filter_expressions = self._build_filter_expressions(
                self.table.metadata,
                filter_dict,
            )
            stmt = stmt.filter(filter_expressions)

        stmt = stmt.limit(limit)
        async with self.session_maker() as session:
            query_execution = await session.execute(stmt)
            # After adding column cosine_similarity to stmt
            # the result is a tuple of (CollectionTable, cosine_similarity)
            results = query_execution.all()

        return [
            CollectionPointResult(
                payload=CollectionPoint(
                    id=result[0].id,
                    embedding=result[0].embedding,
                    payload=result[0].payload,
                ),
                score=result[1],
            )
            for result in results
        ]

    async def get(self, id: str) -> CollectionPoint:
        # Get collection point with the given id
        async with self.session_maker() as session:
            result = await self.table.read_by_id(session=session, point_id=id)
            if result is None:
                raise ValueError(
                    f"Point with id {id} not found in {self.collection_name}",
                )
            return CollectionPoint(
                id=result.id,
                embedding=result.embedding,
                payload=result.payload,
            )

    async def query_all(self) -> list:
        async with self.session_maker() as session:
            results = self.table.read_all(session=session, include_metadata=True)
            return [
                CollectionPoint(
                    id=result.id,
                    embedding=result.embedding,
                    payload=result.payload,
                )
                async for result in results
            ]

    async def update(
        self,
        id: str,
        embedding: List[float],
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        # Update collection point with the given id
        if payload is None:
            payload = {}
        async with self.session_maker() as session:
            if self.table is not None:
                await self.table.update(
                    session=session,
                    id=id,
                    embedding=embedding,
                    payload=payload,
                )

    async def upsert(
        self,
        id: str,
        embedding: List[float],
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        try:
            await self.insert(id, embedding, payload)
        except Exception as e:
            if is_duplicate_key_error(e.args[0]):
                await self.update(id, embedding, payload)
            else:
                raise e

    def _build_filter_expressions(
        self,
        col: Mapped[Dict[str, Any]],
        filter_dict: Dict[str, Any],
    ) -> Any:
        """
        Recursively build SQLAlchemy filter expressions based on the filter_dict dictionary.

        Args:
            col (sqlalchemy.sql.Column): The metadata key on which to apply the filter.
            filter_dict (Dict[str, Any]): A dictionary representing the filter criteria.

        Returns:
            sqlalchemy.sql.expression.ColumnElement: A SQLAlchemy filter expression.

        Raises:
            CollectionPointFilterError: If the filter criteria are not valid or supported.

        Supported Filter Operators:
            - "$and": Logical AND operator for combining multiple filter conditions. Uses recursion.
            - "$or": Logical OR operator for combining multiple filter conditions. Uses recursion.
            - "$eq": Equality operator.
            - "$ne": Inequality operator.
        """  # noqa: E501
        ##TODO: Check data types and edge cases
        key, value = list(filter_dict.items())[-1]

        if key == "$and":
            return and_(
                *[self._build_filter_expressions(col, filter) for filter in value],
            )
        if key == "$or":
            return or_(
                *[self._build_filter_expressions(col, filter) for filter in value],
            )

        operator, filter_value = value.copy().popitem()

        if not isinstance(filter_value, str):
            raise ValueError("Filter value must be a string")

        value = cast(filter_value, JSONB)
        operation = col.op("->")(key)

        if operator == "$eq":
            return operation == value
        if operator == "$ne":
            return operation != value

        raise ValueError(f"Unsupported operator {operator}")

    def __repr__(self) -> str:
        return f"Collection(name={self.collection_name}, dimension={self.dimension})"


def is_duplicate_key_error(error_message: str) -> bool:
    """Check if the error message indicates a duplicate key constraint violation."""
    return "duplicate key value violates unique constraint" in error_message
