from typing import Optional
from database import get_db_connection


class ItemRepository:
    @staticmethod
    async def create_item(
        *,
        user_id: int,
        name: str,
        description: str,
        category: int,
        images_qty: int,
    ) -> int:
        async with get_db_connection() as conn:
            item_id = await conn.fetchval(
                """
                INSERT INTO items (user_id, name, description, category, images_qty)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id
                """,
                user_id, name, description, category, images_qty,
            )
            return int(item_id)

    @staticmethod
    async def get_item_with_user(item_id: int) -> Optional[dict]:
        async with get_db_connection() as conn:
            row = await conn.fetchrow(
                """
                SELECT
                    i.id,
                    i.user_id,
                    i.name,
                    i.description,
                    i.category,
                    i.images_qty,
                    u.is_verified
                FROM items AS i
                JOIN users AS u ON u.id = i.user_id
                WHERE i.id = $1::int
                """,
                item_id,
            )
            return dict(row) if row else None


@staticmethod
async def close_item(item_id: int) -> bool:
    async with get_db_connection() as conn:
        result = await conn.execute(
            "UPDATE items SET is_closed = TRUE WHERE id = $1",
            item_id
        )
        return result.split()[1] == '1'