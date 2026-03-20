import pytest
from repositories.account import AccountRepository
from app.storage.account_storage import AccountRedisStorage

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_create_account(db_connection):
    user_id = await AccountRepository.create("testuser", "secret123")
    assert user_id is not None
    assert user_id > 0

    row = await db_connection.fetchrow(
        "SELECT login, password FROM account WHERE id = $1", user_id
    )
    assert row is not None
    assert row["login"] == "testuser"
    assert len(row["password"]) == 32
    assert row["password"] != "secret123"


@pytest.mark.asyncio
async def test_get_by_id(db_connection):
    user_id = await AccountRepository.create("getbyid", "pass")
    user = await AccountRepository.get_by_id(user_id)
    assert user is not None
    assert user["id"] == user_id
    assert user["login"] == "getbyid"
    assert "password" not in user
    assert "is_blocked" in user
    assert user["is_blocked"] is False


@pytest.mark.asyncio
async def test_get_by_login(db_connection):
    user_id = await AccountRepository.create("getbylogin", "pass")
    user = await AccountRepository.get_by_login("getbylogin")
    assert user is not None
    assert user["id"] == user_id
    assert user["login"] == "getbylogin"
    assert "password" in user
    assert user["is_blocked"] is False


@pytest.mark.asyncio
async def test_verify_password_success(db_connection):
    user_id = await AccountRepository.create("verify_success", "correct_pass")
    result_id = await AccountRepository.verify_password("verify_success", "correct_pass")
    assert result_id == user_id


@pytest.mark.asyncio
async def test_verify_password_failure(db_connection):
    await AccountRepository.create("verify_fail", "correct_pass")
    result_id = await AccountRepository.verify_password("verify_fail", "wrong_pass")
    assert result_id is None


@pytest.mark.asyncio
async def test_verify_password_nonexistent_user(db_connection):
    result_id = await AccountRepository.verify_password("nonexistent", "any")
    assert result_id is None


@pytest.mark.asyncio
async def test_delete_account(db_connection):
    user_id = await AccountRepository.create("todelete", "pass")
    assert await AccountRepository.get_by_id(user_id) is not None

    deleted = await AccountRepository.delete(user_id)
    assert deleted is True

    assert await AccountRepository.get_by_id(user_id) is None


@pytest.mark.asyncio
async def test_block_unblock_account(db_connection):
    user_id = await AccountRepository.create("toblock", "pass")

    assert await AccountRepository.is_blocked(user_id) is False

    await AccountRepository.set_blocked(user_id, True)
    assert await AccountRepository.is_blocked(user_id) is True

    user = await AccountRepository.get_by_id(user_id)
    assert user["is_blocked"] is True

    await AccountRepository.set_blocked(user_id, False)
    assert await AccountRepository.is_blocked(user_id) is False


@pytest.mark.asyncio
async def test_is_blocked_for_nonexistent_user(db_connection):
    assert await AccountRepository.is_blocked(999999) is False