from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from app.db.utils import _create_db_if_not_exists, _setup_db


@asynccontextmanager
async def lifespan_setup(
    app: FastAPI,
) -> AsyncGenerator[None, None]:  # pragma: no cover
    """
    Actions to run on application startup.

    This function uses fastAPI app to store data
    in the state, such as db_engine.

    :param app: the fastAPI application.
    :return: function that actually performs actions.
    """
    await _create_db_if_not_exists()
    async_engine = _setup_db()
    app.state.db_engine = async_engine
    app.middleware_stack = None
    app.middleware_stack = app.build_middleware_stack()

    yield
    await app.state.db_engine.dispose()
