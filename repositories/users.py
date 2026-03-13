from typing import Optional
from database import get_db_connection
from database import measure_query


class UserRepository:
    @staticmethod
    async def create_user(*, is_verified: bool = False) -> int:
        async with get_db_connection() as conn:
            with measure_query("insert"):
                user_id = await conn.fetchval(
                    """
                    INSERT INTO users (is_verified)
                    VALUES ($1)
                    RETURNING id
                    """,
                    is_verified,
                )
            return int(user_id)

    @staticmethod
    async def get_user(user_id: int) -> Optional[dict]:
        async with get_db_connection() as conn:
            with measure_query("select"):
                row = await conn.fetchrow(
                    """
                    SELECT id, is_verified
                    FROM users
                    WHERE id = $1::int
                    """,
                    user_id,
                )
            return dict(row) if row else None
