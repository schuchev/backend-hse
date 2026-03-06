import json
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

import pytest
from database import get_db_connection

from app.storage.prediction_storage import PredictionRedisStorage
from app.clients.redis import get_redis_connection
from repositories.moderation_results import ModerationResultRepository

pytestmark = pytest.mark.asyncio


async def test_get_task_with_cache_hit(monkeypatch):
    task_id = 123
    cached_data = {
        "id": task_id,
        "status": "completed",
        "is_violation": True,
        "probability": 0.87
    }

    mock_redis = AsyncMock()
    mock_redis.get.return_value = json.dumps(cached_data)

    @asynccontextmanager
    async def mock_get_redis_connection():
        yield mock_redis

    monkeypatch.setattr("repositories.moderation_results.get_redis_connection", mock_get_redis_connection)

    mock_db = AsyncMock()

    @asynccontextmanager
    async def mock_get_db_connection():
        yield mock_db

    monkeypatch.setattr("repositories.moderation_results.get_db_connection", mock_get_db_connection)

    result = await ModerationResultRepository.get_task_with_cache(task_id)

    assert result is not None
    assert result.task_id == task_id
    assert result.status == "completed"
    assert result.is_violation is True
    assert result.probability == 0.87

    mock_redis.get.assert_called_once_with(f"moderation_result:{task_id}")
    mock_db.fetchrow.assert_not_called()


async def test_get_task_with_cache_miss_and_store(monkeypatch):
    task_id = 456
    db_row = {
        "id": task_id,
        "status": "pending",
        "is_violation": None,
        "probability": None
    }

    mock_redis = AsyncMock()
    mock_redis.get.return_value = None
    mock_redis.setex = AsyncMock()

    redis_calls = 0

    @asynccontextmanager
    async def mock_get_redis_connection():
        nonlocal redis_calls
        redis_calls += 1
        yield mock_redis

    monkeypatch.setattr("repositories.moderation_results.get_redis_connection", mock_get_redis_connection)

    mock_conn = AsyncMock()
    mock_conn.fetchrow.return_value = db_row

    @asynccontextmanager
    async def mock_get_db_connection():
        yield mock_conn

    monkeypatch.setattr("repositories.moderation_results.get_db_connection", mock_get_db_connection)

    result = await ModerationResultRepository.get_task_with_cache(task_id)

    assert result is not None
    assert result.task_id == task_id
    assert result.status == "pending"
    assert result.is_violation is None
    assert result.probability is None

    mock_redis.get.assert_called_once_with(f"moderation_result:{task_id}")
    mock_conn.fetchrow.assert_called_once()
    mock_redis.setex.assert_called_once()
    args, kwargs = mock_redis.setex.call_args
    assert args[0] == f"moderation_result:{task_id}"
    assert args[1] == 86400  
    saved_data = json.loads(args[2])
    assert saved_data == db_row

@pytest.mark.integration
async def test_integration_get_task_with_cache_hit(db_connection, clear_redis):
    conn = db_connection
    task_id = await conn.fetchval(
        "INSERT INTO moderation_results (item_id, status, created_at) VALUES (1, 'pending', now()) RETURNING id"
    )
    await conn.execute(
        "UPDATE moderation_results SET status = 'completed', is_violation = $1, probability = $2, processed_at = now() WHERE id = $3",
        True, 0.75, task_id
    )

    result1 = await ModerationResultRepository.get_task_with_cache(task_id)
    assert result1.probability == 0.75

    async with get_redis_connection() as redis:
        cached = await redis.get(f"moderation_result:{task_id}")
    assert cached is not None
    data = json.loads(cached)
    assert data["probability"] == 0.75

    await conn.execute(
        "UPDATE moderation_results SET probability = 0.99 WHERE id = $1", task_id
    )

    result2 = await ModerationResultRepository.get_task_with_cache(task_id)
    assert result2.probability == 0.75

    async with get_redis_connection() as redis:
        await redis.delete(f"moderation_result:{task_id}")

    result3 = await ModerationResultRepository.get_task_with_cache(task_id)
    assert result3.probability == 0.99
    
async def test_prediction_storage_set_get(clear_redis):
    storage = PredictionRedisStorage()
    item_id = 777
    data = {"is_violation": False, "probability": 0.23}

    await storage.set(item_id, data)
    cached = await storage.get(item_id)
    assert cached == data

    async with get_redis_connection() as redis:
        raw = await redis.get(str(item_id))
    assert raw is not None
    assert json.loads(raw) == data


async def test_prediction_storage_delete():
    storage = PredictionRedisStorage()
    item_id = 888
    data = {"is_violation": True, "probability": 0.9}
    await storage.set(item_id, data)
    await storage.delete(item_id)
    cached = await storage.get(item_id)
    assert cached is None