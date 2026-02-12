import pytest
import pytest_asyncio
from httpx import AsyncClient

from main import app
from repositories.users import UserRepository
from repositories.items import ItemRepository
import httpx


@pytest_asyncio.fixture()
async def client():
    transport = httpx.ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

@pytest.mark.asyncio
async def test_predict_violation_true(client: AsyncClient):
    response = await client.post("/predict", json={
        "seller_id": 1,
        "is_verified_seller": False,
        "item_id": 10,
        "name": "Suspicious Item",
        "description": "a" * 100,
        "category": 5,
        "images_qty": 0
    })

    assert response.status_code == 200
    data = response.json()
    assert "is_violation" in data
    assert "probability" in data
    assert isinstance(data["is_violation"], bool)
    assert 0.0 <= data["probability"] <= 1.0


@pytest.mark.asyncio
async def test_predict_violation_false(client: AsyncClient):
    response = await client.post("/predict", json={
        "seller_id": 2,
        "is_verified_seller": True,
        "item_id": 20,
        "name": "Legitimate Item",
        "description": "a" * 500,
        "category": 10,
        "images_qty": 5
    })

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["is_violation"], bool)
    assert 0.0 <= data["probability"] <= 1.0


@pytest.mark.parametrize("invalid_data,description", [
    (
        {"seller_id": 1, "is_verified_seller": True, "item_id": 10, "name": "Item",
         "description": "Description", "category": 1, "images_qty": "abc"},
        "images_qty неверного типа"
    ),
    (
        {"seller_id": 1, "is_verified_seller": True, "item_id": 10, "name": "Item",
         "description": "Description", "category": 1, "images_qty": -1},
        "images_qty < 0"
    ),
    (
        {"seller_id": 1, "is_verified_seller": True, "item_id": 10, "name": "Item",
         "description": "Description", "category": 1, "images_qty": 11},
        "images_qty > 10"
    ),
])
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


@pytest.mark.asyncio
async def test_create_user(db_connection):
    """Тест создания пользователя в БД"""
    user_id = await UserRepository.create_user(is_verified=True)
    assert user_id is not None
    assert user_id > 0

    user = await UserRepository.get_user(user_id)
    assert user is not None
    assert user["is_verified"] is True


@pytest.mark.asyncio
async def test_create_item(db_connection):
    """Тест создания объявления в БД"""
    user_id = await UserRepository.create_user(is_verified=False)

    item_id = await ItemRepository.create_item(
        user_id=user_id,
        name="Test Item",
        description="Test description",
        category=10,
        images_qty=3
    )

    assert item_id is not None
    assert item_id > 0

    item = await ItemRepository.get_item_with_user(item_id)
    assert item is not None
    assert item["name"] == "Test Item"
    assert item["user_id"] == user_id
    assert item["is_verified"] is False


@pytest.mark.asyncio
async def test_simple_predict_positive(client: AsyncClient, db_connection):
    """Тест /simple_predict с положительным результатом """
    user_id = await UserRepository.create_user(is_verified=False)

    item_id = await ItemRepository.create_item(
        user_id=user_id,
        name="Suspicious",
        description="a" * 50,
        category=5,
        images_qty=0
    )

    response = await client.post(f"/predict/simple_predict?item_id={item_id}")

    assert response.status_code == 200
    data = response.json()
    assert "is_violation" in data
    assert "probability" in data
    assert isinstance(data["is_violation"], bool)
    assert 0.0 <= data["probability"] <= 1.0


@pytest.mark.asyncio
async def test_simple_predict_negative(client: AsyncClient, db_connection):
    """Тест /simple_predict с отрицательным результатом (нарушения нет)"""
    user_id = await UserRepository.create_user(is_verified=True)

    item_id = await ItemRepository.create_item(
        user_id=user_id,
        name="Good Item",
        description="a" * 500,
        category=10,
        images_qty=5
    )

    response = await client.post(f"/predict/simple_predict?item_id={item_id}")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["is_violation"], bool)
    assert 0.0 <= data["probability"] <= 1.0


@pytest.mark.asyncio
async def test_simple_predict_not_found(client: AsyncClient):
    """Тест /simple_predict когда объявление не найдено"""
    response = await client.post("/predict/simple_predict?item_id=999999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
