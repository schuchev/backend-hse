import pytest
from repositories.users import UserRepository
from repositories.items import ItemRepository
from repositories.moderation_results import ModerationResultRepository
from app.storage.prediction_storage import PredictionRedisStorage
from app.storage.moderation_result_storage import ModerationResultRedisStorage
from app.clients.redis import get_redis_connection

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_create_user(db_connection):
    user_id = await UserRepository.create_user(is_verified=True)
    assert user_id > 0
    async with db_connection as conn:
        row = await conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
    assert row["is_verified"] is True


@pytest.mark.asyncio
async def test_create_item(db_connection):
    user_id = await UserRepository.create_user(is_verified=False)
    item_id = await ItemRepository.create_item(
        user_id=user_id, name="Test", description="desc", category=5, images_qty=3
    )
    async with db_connection as conn:
        row = await conn.fetchrow("SELECT * FROM items WHERE id = $1", item_id)
    assert row["name"] == "Test"
    assert row["is_closed"] is False


@pytest.mark.asyncio
async def test_get_item_with_user(db_connection):
    user_id = await UserRepository.create_user(is_verified=True)
    item_id = await ItemRepository.create_item(user_id, "Test", "desc", 5, 3)
    item = await ItemRepository.get_item_with_user(item_id)
    assert item["is_verified"] is True


@pytest.mark.asyncio
async def test_close_item(db_connection):
    user_id = await UserRepository.create_user(is_verified=True)
    item_id = await ItemRepository.create_item(user_id, "Test", "desc", 5, 3)
    result = await ItemRepository.close_item(item_id)
    assert result is True
    async with db_connection as conn:
        row = await conn.fetchrow("SELECT is_closed FROM items WHERE id = $1", item_id)
    assert row["is_closed"] is True


@pytest.mark.asyncio
async def test_close_item_not_found():
    result = await ItemRepository.close_item(999999)
    assert result is False


@pytest.mark.asyncio
async def test_moderation_results_crud(db_connection):
    user_id = await UserRepository.create_user(is_verified=True)
    item_id = await ItemRepository.create_item(user_id, "Test", "desc", 5, 3)
    task_id = await ModerationResultRepository.create_pending(item_id)

    task = await ModerationResultRepository.get_task(task_id)
    assert task["status"] == "pending"

    await ModerationResultRepository.mark_completed(task_id, True, 0.75)
    task = await ModerationResultRepository.get_task(task_id)
    assert task["status"] == "completed"
    assert task["probability"] == 0.75

    task_ids = await ModerationResultRepository.get_task_ids_by_item_id(item_id)
    assert task_id in task_ids


@pytest.mark.asyncio
async def test_get_task_with_cache_integration(db_connection, clear_redis):
    user_id = await UserRepository.create_user(is_verified=True)
    item_id = await ItemRepository.create_item(user_id, "Test", "desc", 5, 3)
    task_id = await ModerationResultRepository.create_pending(item_id)
    await ModerationResultRepository.mark_completed(task_id, True, 0.75)

    result1 = await ModerationResultRepository.get_task_with_cache(task_id)
    assert result1.probability == 0.75

    async with db_connection as conn:
        await conn.execute("UPDATE moderation_results SET probability = 0.99 WHERE id = $1", task_id)

    result2 = await ModerationResultRepository.get_task_with_cache(task_id)
    assert result2.probability == 0.75

    async with get_redis_connection() as redis:
        await redis.delete(f"moderation_result:{task_id}")

    result3 = await ModerationResultRepository.get_task_with_cache(task_id)
    assert result3.probability == 0.99