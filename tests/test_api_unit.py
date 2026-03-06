import pytest
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient
from repositories.items import ItemRepository
from repositories.moderation_results import ModerationResultRepository
from ml.predictor import ModerationPredictor
from main import app

pytestmark = [pytest.mark.asyncio, pytest.mark.unit]


@pytest.fixture
def mock_item_repo(monkeypatch):
    mock = AsyncMock()
    monkeypatch.setattr(ItemRepository, "get_item_with_user", mock)
    monkeypatch.setattr(ItemRepository, "create_item", mock)
    monkeypatch.setattr(ItemRepository, "close_item", mock)
    return mock


@pytest.fixture
def mock_moderation_repo(monkeypatch):
    mock = AsyncMock()
    monkeypatch.setattr(ModerationResultRepository, "create_pending", mock)
    monkeypatch.setattr(ModerationResultRepository, "get_task_with_cache", mock)
    monkeypatch.setattr(ModerationResultRepository, "get_task_ids_by_item_id", mock)
    return mock


@pytest.fixture
def mock_predictor(monkeypatch):
    mock_instance = MagicMock()
    mock_instance.predict_proba_violation.return_value = 0.8
    monkeypatch.setattr(ModerationPredictor, "instance", lambda: mock_instance)
    return mock_instance


@pytest.fixture(autouse=True)
def mock_storages(monkeypatch):
    mock_pred_storage = AsyncMock()
    mock_mod_storage = AsyncMock()
    app.state.prediction_storage = mock_pred_storage
    app.state.moderation_result_storage = mock_mod_storage
    return mock_pred_storage, mock_mod_storage


async def test_predict_unit(client: AsyncClient, mock_predictor, mock_storages):
    mock_pred_storage, _ = mock_storages
    mock_pred_storage.get.return_value = None
    response = await client.post("/predict", json={
        "seller_id": 1, "is_verified_seller": False, "item_id": 10,
        "name": "Test", "description": "desc", "category": 5, "images_qty": 0
    })
    assert response.status_code == 200
    data = response.json()
    assert "is_violation" in data
    mock_predictor.predict_proba_violation.assert_called_once()
    mock_pred_storage.set.assert_called_once()


async def test_predict_cache_hit_unit(client: AsyncClient, mock_storages):
    mock_pred_storage, _ = mock_storages
    mock_pred_storage.get.return_value = {"is_violation": False, "probability": 0.2}
    response = await client.post("/predict", json={
        "seller_id": 1, "is_verified_seller": True, "item_id": 20,
        "name": "Test", "description": "desc", "category": 5, "images_qty": 5
    })
    assert response.status_code == 200
    assert response.json() == {"is_violation": False, "probability": 0.2}
    mock_pred_storage.set.assert_not_called()


async def test_simple_predict_unit(client: AsyncClient, mock_item_repo, mock_predictor, mock_storages):
    mock_pred_storage, _ = mock_storages
    mock_item_repo.get_item_with_user.return_value = {
        "user_id": 1, "is_verified": True, "id": 30,
        "name": "Item", "description": "desc", "category": 5, "images_qty": 3
    }
    mock_pred_storage.get.return_value = None
    mock_predictor.predict_proba_violation.return_value = 0.1

    response = await client.post("/predict/simple_predict?item_id=30")
    assert response.status_code == 200
    assert response.json() == {"is_violation": False, "probability": 0.1}
    mock_pred_storage.set.assert_called_once_with(30, {"is_violation": False, "probability": 0.1})


async def test_simple_predict_not_found_unit(client: AsyncClient, mock_item_repo):
    mock_item_repo.get_item_with_user.return_value = None
    response = await client.post("/predict/simple_predict?item_id=999")
    assert response.status_code == 404


async def test_async_predict_unit(client: AsyncClient, mock_item_repo, mock_moderation_repo, fake_kafka_producer):
    mock_item_repo.get_item_with_user.return_value = {"id": 40}
    mock_moderation_repo.create_pending.return_value = 123
    response = await client.post("/async_predict", json={"item_id": 40})
    assert response.status_code == 200
    assert response.json()["task_id"] == 123
    assert fake_kafka_producer.sent_item_ids == [40]


async def test_moderation_result_unit(client: AsyncClient, mock_moderation_repo):
    mock_moderation_repo.get_task_with_cache.return_value = MagicMock(
        task_id=123, status="completed", is_violation=True, probability=0.75
    )
    response = await client.get("/moderation_result/123")
    assert response.status_code == 200
    assert response.json()["probability"] == 0.75


async def test_close_item_unit(client: AsyncClient, mock_item_repo, mock_moderation_repo, mock_storages):
    mock_pred_storage, mock_mod_storage = mock_storages
    mock_item_repo.close_item.return_value = True
    mock_moderation_repo.get_task_ids_by_item_id.return_value = [1, 2]

    response = await client.post("/close", params={"item_id": 42})
    assert response.status_code == 200
    assert response.json() == {"status": "closed", "item_id": 42}

    mock_item_repo.close_item.assert_called_once_with(42)
    mock_moderation_repo.get_task_ids_by_item_id.assert_called_once_with(42)
    mock_pred_storage.delete.assert_called_once_with(42)
    assert mock_mod_storage.delete.call_count == 2
    mock_mod_storage.delete.assert_any_call(1)
    mock_mod_storage.delete.assert_any_call(2)


async def test_close_item_not_found_unit(client: AsyncClient, mock_item_repo, mock_storages):
    mock_item_repo.close_item.return_value = False
    mock_pred_storage, mock_mod_storage = mock_storages

    response = await client.post("/close", params={"item_id": 999})
    assert response.status_code == 404
    mock_pred_storage.delete.assert_not_called()
    mock_mod_storage.delete.assert_not_called()


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
async def test_validation_errors(client: AsyncClient, invalid_data, description):
    response = await client.post("/predict", json=invalid_data)
    assert response.status_code == 422, f"Ошибка валидации: {description}"


async def test_health_check(client: AsyncClient):
    response = await client.get("/predict/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["model_loaded"] is True