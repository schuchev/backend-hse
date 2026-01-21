from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_1():
    response = client.post("/predict", json={
        "seller_id": 1,
        "is_verified_seller": True,
        "item_id": 10,
        "name": "yy",
        "description": "gtgt",
        "category": 1,
        "images_qty": 0
    })
    assert response.status_code == 200
    assert response.json() is True


def test_2():
    response = client.post("/predict", json={
        "seller_id": 1,
        "is_verified_seller": False,
        "item_id": 10,
        "name": "ef",
        "description": "gtgtfr",
        "category": 2,
        "images_qty": 3
    })
    assert response.status_code == 200
    assert response.json() is True


def test_3():
    response = client.post("/predict", json={
        "seller_id": 1,
        "is_verified_seller": False,
        "item_id": 10,
        "name": "er",
        "description": "rfrf",
        "category": 3,
        "images_qty": 0
    })
    assert response.status_code == 200
    assert response.json() is False



def test_4():
    response = client.post("/predict", json={
        "seller_id": 1,
        "is_verified_seller": True,
        "item_id": 10,
        "name": "ii",
        "description": "grrgrg",
        "category": 1,
        "images_qty": "abc"
    })
    assert response.status_code == 422


def test_5():
    response = client.post("/predict", json={
        "seller_id": 1,
        "is_verified_seller": True,
        "item_id": 10,
        "name": "rr",
        "description": "rfrge",
        "category": 1
    })
    assert response.status_code == 422


def test_6():
    response = client.post("/predict", json={
        "seller_id": 1,
        "is_verified_seller": False,
        "item_id": 10,
        "name": "re",
        "description": "kfjef",
        "category": 1,
        "images_qty": -5
    })
    assert response.status_code == 422
