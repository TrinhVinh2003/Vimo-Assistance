from loguru import logger
from sqlalchemy import AdaptedConnection, event, text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.schema import CreateSchema

from app.core.settings import settings


async def _create_db_if_not_exists() -> None:
    base_engine = create_async_engine(settings.base_db_url)
    # create database if it doesn't exist yet
    check_db_query = (
        f"SELECT 1 FROM pg_database WHERE datname = '{settings.PGVECTOR_DB}'"  # noqa: S608, E501
    )
    create_db_query = f'CREATE DATABASE "{settings.PGVECTOR_DB}"'

    # First check if the database exists
    async with base_engine.connect() as conn:
        result = await conn.execute(text(check_db_query))
        exists = result.scalar()

    if not exists:
        # Create a new connection with autocommit mode specifically for creating the database
        # Fix: await both connect() and execution_options()
        conn = await base_engine.connect()
        conn = await conn.execution_options(isolation_level="AUTOCOMMIT")
        try:
            await conn.execute(text(create_db_query))
            logger.info(f"Database '{settings.PGVECTOR_DB}' created.")
        finally:
            await conn.close()
    else:
        logger.info(f"Database '{settings.PGVECTOR_DB}' already exists.")


def _setup_db() -> AsyncEngine:
    """
    Creates connection to the database.

    This function creates SQLAlchemy engine instance,
    session_factory for creating sessions
    and stores them in the application's state property.

    :param app: fastAPI application.
    """
    logger.info("Connecting to the database...")
    async_engine: AsyncEngine = create_async_engine(
        settings.db_url,
        pool_pre_ping=True,
        echo=settings.PGVECTOR_ECHO,
    )

    @event.listens_for(async_engine.sync_engine, "connect")
    def register_vector(dbapi_connection: AdaptedConnection, *args) -> None:  # noqa: ANN002, E501
        # register vector extension
        create_extension = "CREATE EXTENSION IF NOT EXISTS vector"
        dbapi_connection.run_async(lambda conn: conn.execute(create_extension))

        logger.info("Vector extension creation check attempted.")
        # create schema if it doesn't exist yet
        create_vectordb_schema = CreateSchema(
            settings.DB_VECTOR_SCHEMA,
            if_not_exists=True,
        )
        dbapi_connection.run_async(
            lambda conn: conn.execute(create_vectordb_schema.compile().string),
        )

        logger.info("Database connected.")

        logger.info("Database initialized and all tables created if they didn't exist.")

    return async_engine


async_engine = _setup_db()
session_factory = async_sessionmaker(
    bind=async_engine,
    autoflush=False,
    future=True,
)
