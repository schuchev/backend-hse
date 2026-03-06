import json
import os
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Mapping, Optional

from app.clients.redis import get_redis_connection

dumps = json.dumps
loads = json.loads

DEFAULT_TTL = int(os.getenv("MODERATION_RESULT_CACHE_TTL", 86400))


@dataclass(frozen=True)
class ModerationResultRedisStorage:
    _TTL: timedelta = timedelta(seconds=DEFAULT_TTL)

    async def set(self, task_id: int, data: Mapping[str, Any]) -> None:
        key = str(task_id)
        async with get_redis_connection() as conn:
            pipeline = conn.pipeline()
            pipeline.set(key, dumps(data))
            pipeline.expire(key, int(self._TTL.total_seconds()))
            await pipeline.execute()

    async def get(self, task_id: int) -> Optional[Mapping[str, Any]]:
        key = str(task_id)
        async with get_redis_connection() as conn:
            raw = await conn.get(key)
            if raw is not None:
                return loads(raw)
            return None

    async def delete(self, task_id: int) -> None:
        key = str(task_id)
        async with get_redis_connection() as conn:
            await conn.delete(key)