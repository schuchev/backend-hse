import pytest
from unittest.mock import AsyncMock, patch
from services.auth import AuthService
from repositories.account import AccountRepository

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_register_success():
    with patch.object(AccountRepository, "get_by_login", return_value=None) as mock_get, \
         patch.object(AccountRepository, "create", return_value=42) as mock_create:
        user_id = await AuthService.register("test", "pass")
        assert user_id == 42
        mock_get.assert_called_once_with("test")
        mock_create.assert_called_once_with("test", "pass")


@pytest.mark.asyncio
async def test_register_duplicate():
    with patch.object(AccountRepository, "get_by_login", return_value={"id": 1}) as mock_get:
        with pytest.raises(ValueError, match="Login already exists"):
            await AuthService.register("test", "pass")
        mock_get.assert_called_once_with("test")


@pytest.mark.asyncio
async def test_login_success():
    with patch.object(AccountRepository, "verify_password", return_value=42) as mock_verify, \
         patch("services.auth.jwt.encode", return_value="token") as mock_jwt:
        token = await AuthService.login("test", "pass")
        assert token == "token"
        mock_verify.assert_called_once_with("test", "pass")
        mock_jwt.assert_called_once()


@pytest.mark.asyncio
async def test_login_failure():
    with patch.object(AccountRepository, "verify_password", return_value=None) as mock_verify:
        token = await AuthService.login("test", "wrong")
        assert token is None
        mock_verify.assert_called_once_with("test", "wrong")


@pytest.mark.asyncio
async def test_decode_token_valid():
    payload = {"sub": "1", "login": "test", "exp": 9999999999}
    with patch("services.auth.jwt.decode", return_value=payload):
        result = await AuthService.decode_token("token")
        assert result == payload


@pytest.mark.asyncio
async def test_decode_token_invalid():
    import jwt
    with patch("services.auth.jwt.decode", side_effect=jwt.PyJWTError):
        result = await AuthService.decode_token("bad")
        assert result is None


@pytest.mark.asyncio
async def test_get_current_account_valid():
    payload = {"sub": "1"}
    account_data = {"id": 1, "login": "test", "is_blocked": False}
    with patch.object(AuthService, "decode_token", return_value=payload) as mock_decode, \
         patch.object(AccountRepository, "get_by_id", return_value=account_data) as mock_get:
        account = await AuthService.get_current_account("token")
        assert account == account_data
        mock_decode.assert_called_once_with("token")
        mock_get.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_get_current_account_blocked():
    payload = {"sub": "1"}
    account_data = {"id": 1, "login": "test", "is_blocked": True}
    with patch.object(AuthService, "decode_token", return_value=payload), \
         patch.object(AccountRepository, "get_by_id", return_value=account_data):
        account = await AuthService.get_current_account("token")
        assert account is None