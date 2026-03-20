import hashlib
from typing import Optional
from database import get_db_connection
from app.storage.account_storage import AccountRedisStorage


def hash_password_md5(password: str) -> str:
    return hashlib.md5(password.encode()).hexdigest()


def verify_password_md5(plain_password: str, hashed_password: str) -> bool:
    return hash_password_md5(plain_password) == hashed_password


class AccountRepository:
    storage = AccountRedisStorage()

    @staticmethod
    async def create(login: str, password: str) -> int:
        hashed = hash_password_md5(password)
        async with get_db_connection() as conn:
            user_id = await conn.fetchval(
                "INSERT INTO account (login, password) VALUES ($1, $2) RETURNING id",
                login, hashed
            )
        await AccountRepository.storage.set(user_id, {"id": user_id, "login": login, "is_blocked": False})
        return user_id

    @staticmethod
    async def get_by_id(user_id: int) -> Optional[dict]:
        cached = await AccountRepository.storage.get(user_id)
        if cached:
            return cached

        async with get_db_connection() as conn:
            row = await conn.fetchrow(
                "SELECT id, login, is_blocked FROM account WHERE id = $1",
                user_id
            )
            if not row:
                return None
            data = dict(row)
            await AccountRepository.storage.set(user_id, data)
            return data

    @staticmethod
    async def get_by_login(login: str) -> Optional[dict]:
        async with get_db_connection() as conn:
            row = await conn.fetchrow(
                "SELECT id, login, password, is_blocked FROM account WHERE login = $1",
                login
            )
            return dict(row) if row else None

    @staticmethod
    async def verify_password(login: str, password: str) -> Optional[int]:
        user = await AccountRepository.get_by_login(login)
        if user and verify_password_md5(password, user["password"]):
            return user["id"]
        return None

    @staticmethod
    async def delete(user_id: int) -> bool:
        async with get_db_connection() as conn:
            result = await conn.execute("DELETE FROM account WHERE id = $1", user_id)
            await AccountRepository.storage.delete(user_id)
            return result == "DELETE 1"

    @staticmethod
    async def set_blocked(user_id: int, blocked: bool) -> None:
        async with get_db_connection() as conn:
            await conn.execute(
                "UPDATE account SET is_blocked = $2 WHERE id = $1",
                user_id, blocked
            )
        await AccountRepository.storage.delete(user_id)

    @staticmethod
    async def is_blocked(user_id: int) -> bool:
        user = await AccountRepository.get_by_id(user_id)
        return user["is_blocked"] if user else False