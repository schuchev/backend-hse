import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_verified_seller_always_approved():
    response = client.post("/predict", json={
        "seller_id": 1,
        "is_verified_seller": True,
        "item_id": 10,
        "name": "iPhone 13",
        "description": "Хорошее состояние, оригинал",
        "category": 1,
        "images_qty": 0
    })
    assert response.status_code == 200
    assert response.json()["is_approved"] is True


def test_unverified_seller_with_images_approved():
    response = client.post("/predict", json={
        "seller_id": 1,
        "is_verified_seller": False,
        "item_id": 10,
        "name": "Samsung Galaxy",
        "description": "Продам смартфон",
        "category": 2,
        "images_qty": 3
    })
    assert response.status_code == 200
    assert response.json()["is_approved"] is True


def test_unverified_seller_without_images_rejected():
    response = client.post("/predict", json={
        "seller_id": 1,
        "is_verified_seller": False,
        "item_id": 10,
        "name": "Планшет",
        "description": "Продам планшет",
        "category": 3,
        "images_qty": 0
    })
    assert response.status_code == 200
    assert response.json()["is_approved"] is False



@pytest.mark.parametrize("invalid_data,description", [
    (
        {
            "seller_id": 1,
            "is_verified_seller": True,
            "item_id": 10,
            "name": "Item",
            "description": "Description",
            "category": 1,
            "images_qty": "abc"
        },
        "images_qty имеет неверный тип (строка)"
    ),
    (
        {
            "seller_id": 1,
            "is_verified_seller": True,
            "item_id": 10,
            "name": "Item",
            "description": "Description",
            "category": 1

        },
        "Отсутствует обязательное поле images_qty"
    ),
    (
        {
            "seller_id": 1,
            "is_verified_seller": True,
            "item_id": 10,
            "name": "Item",
            "description": "Description",
            "category": 1,
            "images_qty": -5
        },
        "images_qty < 0 (некорректное значение)"
    ),
    (
        {
            "seller_id": -1,
            "is_verified_seller": True,
            "item_id": 10,
            "name": "Item",
            "description": "Description",
            "category": 1,
            "images_qty": 0
        },
        "seller_id < 0 (некорректное значение)"
    ),
    (
        {
            "seller_id": 1,
            "is_verified_seller": True,
            "item_id": -10,
            "name": "Item",
            "description": "Description",
            "category": 1,
            "images_qty": 0
        },
        "item_id < 0 (некорректное значение)"
    ),
    (
        {
            "seller_id": 1,
            "is_verified_seller": True,
            "item_id": 10,
            "name": "Item",
            "description": "Description",
            "category": -1,
            "images_qty": 0
        },
        "category < 0 (некорректное значение)"
    ),
    (
        {
            "seller_id": 1,
            "is_verified_seller": True,
            "item_id": 10,
            "name": "",
            "description": "Description",
            "category": 1,
            "images_qty": 0
        },
        "name пуста (некорректное значение)"
    ),
    (
        {
            "seller_id": 1,
            "is_verified_seller": True,
            "item_id": 10,
            "name": "Item",
            "description": "",
            "category": 1,
            "images_qty": 0
        },
        "description пуста (некорректное значение)"
    ),
])
def test_validation_errors(invalid_data, description):
    response = client.post("/predict", json=invalid_data)
    assert response.status_code == 422, f"Ошибка валидации: {description}"



def test_unverified_seller_with_one_image_approved():
    response = client.post("/predict", json={
        "seller_id": 999,
        "is_verified_seller": False,
        "item_id": 555,
        "name": "Товар",
        "description": "Описание товара",
        "category": 5,
        "images_qty": 1
    })
    assert response.status_code == 200
    assert response.json()["is_approved"] is True


def test_with_max_length_strings():
    response = client.post("/predict", json={
        "seller_id": 1,
        "is_verified_seller": True,
        "item_id": 10,
        "name": "A" * 255,
        "description": "B" * 5000,
        "category": 1,
        "images_qty": 0
    })
    assert response.status_code == 200
    assert response.json()["is_approved"] is True


def test_with_zero_seller_id_rejected():
    response = client.post("/predict", json={
        "seller_id": 0,
        "is_verified_seller": True,
        "item_id": 10,
        "name": "Item",
        "description": "Description",
        "category": 1,
        "images_qty": 0
    })
    assert response.status_code == 422
