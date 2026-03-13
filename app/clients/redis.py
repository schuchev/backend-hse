import os
from contextlib import asynccontextmanager
from redis.asyncio import Redis, ConnectionPool

_pool: ConnectionPool | None = None


def init_redis_pool():
    global _pool
    if _pool is None:
        host = os.getenv("REDIS_HOST", "redis")
        port = int(os.getenv("REDIS_PORT", 6379))
        db = int(os.getenv("REDIS_DB", 0))
        password = os.getenv("REDIS_PASSWORD", None)
        _pool = ConnectionPool(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=True,
        )


async def close_redis_pool():
    global _pool
    if _pool:
        await _pool.disconnect()
        _pool = None

@asynccontextmanager
async def get_redis_connection():
    if _pool is None:
        raise RuntimeError("Redis pool not initialized. Call init_redis_pool() first.")
    conn = Redis(connection_pool=_pool)
    try:
        yield conn
    finally:
        await conn.aclose() 
        
def create_redis_pool():
    global _pool
    if _pool is None:
        init_redis_pool()
    return _pool
    
async def flushall():
    async with get_redis_connection() as conn:
        await conn.flushall()