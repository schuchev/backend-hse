import jwt
import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

from repositories.account import AccountRepository

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "my-very-secret-key-at-least-32-characters")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


class AuthService:
    @staticmethod
    async def register(login: str, password: str) -> int:
        existing = await AccountRepository.get_by_login(login)
        if existing:
            raise ValueError("Login already exists")
        user_id = await AccountRepository.create(login, password)
        return user_id

    @staticmethod
    async def login(login: str, password: str) -> Optional[str]:
        user_id = await AccountRepository.verify_password(login, password)
        if user_id is None:
            return None
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        payload = {
            "sub": str(user_id),
            "login": login,
            "exp": expire,
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        return token

    @staticmethod
    async def decode_token(token: str) -> Optional[Dict[str, Any]]:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except jwt.PyJWTError:
            return None

    @staticmethod
    async def get_current_account(token: str) -> Optional[Dict[str, Any]]:
        payload = await AuthService.decode_token(token)
        if not payload:
            return None
        user_id = payload.get("sub")
        if not user_id:
            return None
        account = await AccountRepository.get_by_id(int(user_id))
        if not account:
            return None
        if account.get("is_blocked"):
            return None
        return account