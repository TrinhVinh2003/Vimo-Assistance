from typing import Annotated

from fastapi import Depends
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.settings import settings
from app.db.base import Base
from app.db.keyword_index import create_keyword_index_if_not_exists
from app.db.models import PgVectorCollection
from app.db.utils import async_engine, session_factory


class PgVectorClient:
    def __init__(
        self,
        engine: AsyncEngine,
        session_maker: async_sessionmaker[AsyncSession],
    ) -> None:
        self.engine = engine
        self.session_maker = session_maker
        self._metadata = Base.metadata

    async def setup(self) -> None:
        await self.sync()
        await create_keyword_index_if_not_exists("vimo_documents")

    async def sync(self) -> None:
        async with self.engine.begin() as conn:
            await conn.run_sync(self._metadata.reflect)

    async def create_collection(
        self,
        collection_name: str,
        dimension: int,
    ) -> PgVectorCollection:
        try:
            logger.info(f"Creating collection {collection_name}...")
            collection = PgVectorCollection(
                collection_name=collection_name,
                dimension=dimension,
                session_maker=self.session_maker,
            )
            collection.build_table()
            async with self.engine.begin() as conn:
                await conn.run_sync(self._metadata.create_all)
            return collection
        except Exception as e:
            logger.error(f"Error creating collection: {e}")
            raise e

    async def get_collection(self, collection_name: str) -> PgVectorCollection:
        try:
            logger.info(f"Getting collection {collection_name}...")
            await self.sync()
            if self.__is_collection_exists(collection_name):
                return self.__construct_collection(collection_name)
            raise ValueError(f"Collection {collection_name} does not exist")
        except Exception as e:
            logger.error(f"Error getting collection: {e}")
            raise e

    async def get_or_create_collection(
        self,
        collection_name: str,
        dimension: int,
    ) -> PgVectorCollection:
        try:
            return await self.get_collection(collection_name)
        except Exception:
            return await self.create_collection(collection_name, dimension)

    def __construct_collection(self, collection_name: str) -> PgVectorCollection:
        collection_uri = f"{settings.DB_VECTOR_SCHEMA}.{collection_name}"
        dim = self._metadata.tables[collection_uri].c.embedding.type.dim
        return PgVectorCollection(
            collection_name=collection_name,
            dimension=dim,  # Hardcoded for now
            session_maker=self.session_maker,
        )

    def __is_collection_exists(self, collection_name: str) -> bool:
        return f"{settings.DB_VECTOR_SCHEMA}.{collection_name}" in self._metadata.tables


async def get_client() -> PgVectorClient:
    return PgVectorClient(engine=async_engine, session_maker=session_factory)


pg_client = Annotated[PgVectorClient, Depends(get_client)]
