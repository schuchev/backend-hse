import os
import asyncpg
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from typing import AsyncGenerator
import time
from contextlib import contextmanager
from app.metrics import DB_QUERY_DURATION

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5435/hw",
)

_pool: asyncpg.Pool | None = None

async def init_db() -> None:
    global _pool
    _pool = await asyncpg.create_pool(dsn=DATABASE_URL)

async def close_db() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None

@asynccontextmanager
async def get_db_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    assert _pool is not None, "DB pool is not initialized"
    async with _pool.acquire() as conn:
        yield conn

def get_pool() -> asyncpg.Pool:
    assert _pool is not None, "DB pool is not initialized"
    return _pool


@contextmanager
def measure_query(query_type: str):
    start = time.time()
    try:
        yield
    finally:
        duration = time.time() - start
        DB_QUERY_DURATION.labels(query_type=query_type).observe(duration)