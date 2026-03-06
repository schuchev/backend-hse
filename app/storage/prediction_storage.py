import json
import os
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Mapping, Optional

from app.clients.redis import get_redis_connection

dumps = json.dumps
loads = json.loads

# Значение 3600 (1 час) выбрано как компромисс:
# - слишком маленький TTL увеличит нагрузку на ML‑модель при повторных запросах,
# - слишком большой может привести к выдаче устаревших результатов,
#   если объявление было отредактировано или модель переобучена.
# 1 час покрывает большинство сценариев повторных запросов в рамках сессии,
# при этом гарантирует обновление данных не позднее чем через час после изменений.
DEFAULT_TTL = int(os.getenv("PREDICTION_CACHE_TTL", 3600))


@dataclass(frozen=True)
class PredictionRedisStorage:
    
    _TTL: timedelta = timedelta(seconds=DEFAULT_TTL)

    async def set(self, item_id: int, data: Mapping[str, Any]) -> None:
        key = str(item_id)
        async with get_redis_connection() as conn:
            pipeline = conn.pipeline()
            pipeline.set(key, dumps(data))
            pipeline.expire(key, int(self._TTL.total_seconds()))
            await pipeline.execute()

    async def get(self, item_id: int) -> Optional[Mapping[str, Any]]:
        key = str(item_id)
        async with get_redis_connection() as conn:
            raw = await conn.get(key)
            if raw is not None:
                return loads(raw)
            return None

    async def delete(self, item_id: int) -> None:
        key = str(item_id)
        async with get_redis_connection() as conn:
            await conn.delete(key)