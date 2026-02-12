import asyncio
from typing import AsyncGenerator

import asyncpg
import pytest
import pytest_asyncio

from database import init_db, close_db, get_db_connection
from model import load_or_train_model
from ml.predictor import ModerationPredictor


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def initialize_model():
    model = load_or_train_model("test_model.pkl")
    ModerationPredictor.init(model)
    yield
    ModerationPredictor.reset()


@pytest_asyncio.fixture(scope="function", autouse=True)
async def initialize_database():
    await init_db()
    yield
    await close_db()


@pytest_asyncio.fixture(scope="function")
async def db_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    async with get_db_connection() as conn:
        tr = conn.transaction()
        await tr.start()
        try:
            yield conn
        finally:
            await tr.rollback()
