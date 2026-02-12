import os
import asyncpg
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from typing import AsyncGenerator

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/moderation_db",
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
