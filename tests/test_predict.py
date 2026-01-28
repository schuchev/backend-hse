import pytest
from fastapi.testclient import TestClient
from sklearn.linear_model import LogisticRegression
import numpy as np

from main import app
from model import load_or_train_model


@pytest.fixture(scope="session", autouse=True)
def initialize_model():

    app.state.model = load_or_train_model("test_model.pkl")

    yield

    app.state.model = None


client = TestClient(app)



def test_predict_violation_true():
    response = client.post("/predict", json={
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


def test_predict_violation_false():
    response = client.post("/predict", json={
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
        {
            "seller_id": 1,
            "is_verified_seller": True,
            "item_id": 10,
            "name": "Item",
            "description": "Description",
            "category": 1,
            "images_qty": "abc"
        },
        "images_qty неверного типа (строка)"
    ),
    (
        {
            "seller_id": 1,
            "is_verified_seller": True,
            "item_id": 10,
            "name": "Item",
            "description": "Description",
            "category": 1,
            "images_qty": -1
        },
        "images_qty < 0"
    ),
    (
        {
            "seller_id": 1,
            "is_verified_seller": True,
            "item_id": 10,
            "name": "Item",
            "description": "Description",
            "category": 1,
            "images_qty": 11
        },
        "images_qty > 10"
    ),
    (
        {
            "seller_id": -1,
            "is_verified_seller": True,
            "item_id": 10,
            "name": "Item",
            "description": "Description",
            "category": 1,
            "images_qty": 5
        },
        "seller_id < 0"
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
        "name пуста"
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
        "description пуста"
    ),
    (
        {
            "seller_id": 1,
            "is_verified_seller": True,
            "item_id": 10,
            "name": "Item",
            "description": "Description",
            "category": 101,
            "images_qty": 0
        },
        "category > 100"
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
        "Отсутствует images_qty"
    ),
])
def test_validation_errors(invalid_data, description):
    response = client.post("/predict", json=invalid_data)
    assert response.status_code == 422, f"Ошибка валидации: {description}"



def test_health_check():
    response = client.get("/predict/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["model_loaded"] is True



def test_max_length_name():
    response = client.post("/predict", json={
        "seller_id": 1,
        "is_verified_seller": True,
        "item_id": 10,
        "name": "A" * 255,
        "description": "Description",
        "category": 50,
        "images_qty": 5
    })
    assert response.status_code == 200


def test_max_length_description():
    response = client.post("/predict", json={
        "seller_id": 1,
        "is_verified_seller": True,
        "item_id": 10,
        "name": "Item",
        "description": "A" * 5000,
        "category": 50,
        "images_qty": 5
    })
    assert response.status_code == 200


def test_min_images_qty():
    response = client.post("/predict", json={
        "seller_id": 1,
        "is_verified_seller": False,
        "item_id": 10,
        "name": "Item",
        "description": "Description",
        "category": 1,
        "images_qty": 0
    })
    assert response.status_code == 200


def test_max_images_qty():
    response = client.post("/predict", json={
        "seller_id": 1,
        "is_verified_seller": True,
        "item_id": 10,
        "name": "Item",
        "description": "Description",
        "category": 50,
        "images_qty": 10
    })
    assert response.status_code == 200
