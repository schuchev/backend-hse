import json
from typing import Optional, Mapping, Any
from app.clients.redis import get_redis_connection

class AccountRedisStorage:

    TTL = 3600

    async def set(self, user_id: int, data: Mapping[str, Any]) -> None:
        key = f"account:{user_id}"
        async with get_redis_connection() as redis:
            await redis.setex(key, self.TTL, json.dumps(data))

    async def get(self, user_id: int) -> Optional[dict]:
        key = f"account:{user_id}"
        async with get_redis_connection() as redis:
            raw = await redis.get(key)
            if raw:
                return json.loads(raw)
            return None

    async def delete(self, user_id: int) -> None:
        key = f"account:{user_id}"
        async with get_redis_connection() as redis:
            await redis.delete(key)

    async def invalidate(self, user_id: int) -> None:
        await self.delete(user_id)