import json
import pytest
from httpx import AsyncClient
from contextlib import asynccontextmanager

from repositories.users import UserRepository
from repositories.items import ItemRepository
from database import get_db_connection
from ml.predictor import ModerationPredictor
from app.workers.moderation_worker import process_one, DLQ_TOPIC


class FakeDLQProducer:
    def __init__(self):
        self.sent = []

    async def send_and_wait(self, topic: str, value: bytes):
        self.sent.append((topic, value))


@pytest.mark.asyncio
async def test_predict_violation_true(client: AsyncClient):
    response = await client.post(
        "/predict",
        json={
            "seller_id": 1,
            "is_verified_seller": False,
            "item_id": 10,
            "name": "Suspicious Item",
            "description": "a" * 100,
            "category": 5,
            "images_qty": 0,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "is_violation" in data
    assert "probability" in data
    assert isinstance(data["is_violation"], bool)
    assert 0.0 <= data["probability"] <= 1.0


@pytest.mark.asyncio
async def test_predict_violation_false(client: AsyncClient):
    response = await client.post(
        "/predict",
        json={
            "seller_id": 2,
            "is_verified_seller": True,
            "item_id": 20,
            "name": "Legitimate Item",
            "description": "a" * 500,
            "category": 10,
            "images_qty": 5,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["is_violation"], bool)
    assert 0.0 <= data["probability"] <= 1.0


@pytest.mark.parametrize(
    "invalid_data,description",
    [
        (
            {
                "seller_id": 1,
                "is_verified_seller": True,
                "item_id": 10,
                "name": "Item",
                "description": "Description",
                "category": 1,
                "images_qty": "abc",
            },
            "images_qty неверного типа",
        ),
        (
            {
                "seller_id": 1,
                "is_verified_seller": True,
                "item_id": 10,
                "name": "Item",
                "description": "Description",
                "category": 1,
                "images_qty": -1,
            },
            "images_qty < 0",
        ),
        (
            {
                "seller_id": 1,
                "is_verified_seller": True,
                "item_id": 10,
                "name": "Item",
                "description": "Description",
                "category": 1,
                "images_qty": 11,
            },
            "images_qty > 10",
        ),
    ],
)
@pytest.mark.asyncio
async def test_validation_errors(client: AsyncClient, invalid_data, description):
    response = await client.post("/predict", json=invalid_data)
    assert response.status_code == 422, f"Ошибка валидации: {description}"


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/predict/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["model_loaded"] is True


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_user(db_connection):
    user_id = await UserRepository.create_user(is_verified=True)
    assert user_id is not None
    assert user_id > 0

    user = await UserRepository.get_user(user_id)
    assert user is not None
    assert user["is_verified"] is True


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_item(db_connection):
    user_id = await UserRepository.create_user(is_verified=False)

    item_id = await ItemRepository.create_item(
        user_id=user_id,
        name="Test Item",
        description="Test description",
        category=10,
        images_qty=3,
    )

    assert item_id is not None
    assert item_id > 0

    item = await ItemRepository.get_item_with_user(item_id)
    assert item is not None
    assert item["name"] == "Test Item"
    assert item["user_id"] == user_id
    assert item["is_verified"] is False


@pytest.mark.integration
@pytest.mark.asyncio
async def test_simple_predict_positive(client: AsyncClient, db_connection):
    user_id = await UserRepository.create_user(is_verified=False)
    item_id = await ItemRepository.create_item(
        user_id=user_id,
        name="Suspicious",
        description="a" * 50,
        category=5,
        images_qty=0,
    )

    response = await client.post(f"/predict/simple_predict?item_id={item_id}")
    assert response.status_code == 200
    data = response.json()
    assert "is_violation" in data
    assert "probability" in data
    assert isinstance(data["is_violation"], bool)
    assert 0.0 <= data["probability"] <= 1.0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_simple_predict_negative(client: AsyncClient, db_connection):
    user_id = await UserRepository.create_user(is_verified=True)
    item_id = await ItemRepository.create_item(
        user_id=user_id,
        name="Good Item",
        description="a" * 500,
        category=10,
        images_qty=5,
    )

    response = await client.post(f"/predict/simple_predict?item_id={item_id}")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["is_violation"], bool)
    assert 0.0 <= data["probability"] <= 1.0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_simple_predict_not_found(client: AsyncClient, db_connection):
    response = await client.post("/predict/simple_predict?item_id=999999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_async_predict_creates_task_and_sends_message(client: AsyncClient, fake_kafka_producer, db_connection):
    user_id = await UserRepository.create_user(is_verified=False)
    item_id = await ItemRepository.create_item(
        user_id=user_id,
        name="Async Item",
        description="a" * 100,
        category=1,
        images_qty=1,
    )

    resp = await client.post("/async_predict", json={"item_id": item_id})
    assert resp.status_code == 200
    data = resp.json()

    assert isinstance(data["task_id"], int)
    assert data["task_id"] > 0
    assert data["status"] == "pending"
    assert fake_kafka_producer.sent_item_ids == [item_id]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_moderation_result_by_task_id(client: AsyncClient, db_connection):
    user_id = await UserRepository.create_user(is_verified=False)
    item_id = await ItemRepository.create_item(
        user_id=user_id,
        name="Async Item 2",
        description="a" * 120,
        category=1,
        images_qty=1,
    )

    create_resp = await client.post("/async_predict", json={"item_id": item_id})
    task_id = create_resp.json()["task_id"]

    status_resp = await client.get(f"/moderation_result/{task_id}")
    assert status_resp.status_code == 200
    row = status_resp.json()

    assert row["task_id"] == task_id
    assert row["status"] == "pending"
    assert row["is_violation"] is None
    assert row["probability"] is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_worker_process_one_completes_task(monkeypatch, client: AsyncClient, db_connection):
    user_id = await UserRepository.create_user(is_verified=True)
    item_id = await ItemRepository.create_item(
        user_id=user_id,
        name="Good item",
        description="a" * 500,
        category=10,
        images_qty=5,
    )

    create_resp = await client.post("/async_predict", json={"item_id": item_id})
    task_id = create_resp.json()["task_id"]

    import app.workers.moderation_worker as mw

    def fake_predict(**kwargs):
        return False, 0.12

    monkeypatch.setattr(mw.ModerationPredictor, "predict", fake_predict, raising=False)

    dlq = FakeDLQProducer()
    await mw.process_one(item_id=item_id, dlq_producer=dlq, original_message={"item_id": item_id})

    status_resp = await client.get(f"/moderation_result/{task_id}")
    assert status_resp.status_code == 200
    row = status_resp.json()

    assert row["status"] == "completed"
    assert isinstance(row["is_violation"], bool)
    assert 0.0 <= float(row["probability"]) <= 1.0
    assert dlq.sent == []


@pytest.mark.asyncio
async def test_worker_sends_to_dlq_on_missing_item(monkeypatch):
    import app.workers.moderation_worker as mw
    from repositories.items import ItemRepository
    from repositories.moderation_results import ModerationResultRepository

    async def mock_get_item_with_user(item_id):
        return None
    monkeypatch.setattr(ItemRepository, "get_item_with_user", mock_get_item_with_user)

    async def mock_get_latest_pending_task(item_id):
        return 12345
    monkeypatch.setattr(ModerationResultRepository, "get_latest_pending_task", mock_get_latest_pending_task)

    mark_failed_called = False
    async def mock_mark_failed(task_id, error_message):
        nonlocal mark_failed_called
        mark_failed_called = True
        assert task_id == 12345
        assert "not found" in error_message.lower()
    monkeypatch.setattr(ModerationResultRepository, "mark_failed", mock_mark_failed)

    dlq = FakeDLQProducer()
    await mw.process_one(item_id=999, dlq_producer=dlq, original_message={"item_id": 999})

    assert mark_failed_called
    assert len(dlq.sent) == 1
    topic, raw = dlq.sent[0]
    assert topic == mw.DLQ_TOPIC
    payload = json.loads(raw.decode("utf-8"))
    assert payload["original_message"]["item_id"] == 999
    assert "not found" in payload["error"].lower()
    assert "timestamp" in payload
    assert payload["retry_count"] == 1