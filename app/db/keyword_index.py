from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.settings import settings


async def create_keyword_index_if_not_exists(table_name: str) -> None:
    """Create index for content and title if not exists."""
    index_content = f"idx_{table_name}_content_tsv"
    index_title = f"idx_{table_name}_title_tsv"

    sql_content = f"""
    CREATE INDEX IF NOT EXISTS {index_content}
    ON {settings.DB_VECTOR_SCHEMA}.{table_name}
    USING GIN (to_tsvector('english', payload->>'content'));
    """

    sql_title = f"""
    CREATE INDEX IF NOT EXISTS {index_title}
    ON {settings.DB_VECTOR_SCHEMA}.{table_name}
    USING GIN (to_tsvector('english', payload->>'title'));
    """

    engine = create_async_engine(settings.db_url, echo=False)

    try:
        async with engine.begin() as conn:
            await conn.execute(text(sql_content))
            await conn.execute(text(sql_title))
            logger.info("Created GIN indexes for content and title.")
    except Exception as e:
        logger.error(f"Failed to create keyword index: {e}")
