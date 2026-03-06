from typing import Optional
from database import get_db_connection
import json
from typing import Optional
from schemas.moderation_result import ModerationResultResponse
from app.clients.redis import get_redis_connection


MODERATION_CACHE_TTL = 86400

class ModerationResultRepository:

    @staticmethod
    async def create_pending(item_id: int) -> int:
        async with get_db_connection() as conn:
            task_id = await conn.fetchval(
                """
                INSERT INTO moderation_results (item_id, status, created_at)
                VALUES ($1, 'pending', now())
                RETURNING id
                """,
                item_id,
            )
            return int(task_id)

    @staticmethod
    async def get_task(task_id: int) -> Optional[dict]:
        async with get_db_connection() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, status, is_violation, probability
                FROM moderation_results
                WHERE id = $1
                """,
                task_id,
            )
            return dict(row) if row else None

    @staticmethod
    async def get_latest_pending_task(item_id: int) -> Optional[int]:
        async with get_db_connection() as conn:
            task_id = await conn.fetchval(
                """
                SELECT id
                FROM moderation_results
                WHERE item_id = $1 AND status = 'pending'
                ORDER BY created_at DESC
                LIMIT 1
                """,
                item_id,
            )
            return task_id

    @staticmethod
    async def mark_completed(task_id: int, is_violation: bool, probability: float):
        async with get_db_connection() as conn:
            await conn.execute(
                """
                UPDATE moderation_results
                SET status = 'completed',
                    is_violation = $2,
                    probability = $3,
                    processed_at = now()
                WHERE id = $1
                """,
                task_id,
                is_violation,
                probability,
            )

    @staticmethod
    async def mark_failed(task_id: int, error_message: str):
        async with get_db_connection() as conn:
            await conn.execute(
                """
                UPDATE moderation_results
                SET status = 'failed',
                    error_message = $2,
                    processed_at = now()
                WHERE id = $1
                """,
                task_id,
                error_message,
            )
            
    @staticmethod
    async def get_task_with_cache(task_id: int) -> Optional[ModerationResultResponse]:
        key = f"moderation_result:{task_id}"

        async with get_redis_connection() as redis:
            cached = await redis.get(key)
            if cached:
                data = json.loads(cached)
                return ModerationResultResponse(
                    task_id=data["id"],
                    status=data["status"],
                    is_violation=data["is_violation"],
                    probability=data["probability"]
                )

        # 2. Если нет в кэше, идём в БД
        async with get_db_connection() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, status, is_violation, probability
                FROM moderation_results
                WHERE id = $1
                """,
                task_id
            )
            if not row:
                return None
            data = dict(row)

        async with get_redis_connection() as redis:
            await redis.setex(key, MODERATION_CACHE_TTL, json.dumps(data))

        return ModerationResultResponse(
            task_id=data["id"],
            status=data["status"],
            is_violation=data["is_violation"],
            probability=data["probability"]
        )

@staticmethod
async def get_task_ids_by_item_id(item_id: int) -> List[int]:
    async with get_db_connection() as conn:
        rows = await conn.fetch(
            "SELECT id FROM moderation_results WHERE item_id = $1",
            item_id
        )
        return [row["id"] for row in rows]