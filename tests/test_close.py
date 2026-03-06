import pytest
from unittest.mock import AsyncMock
from httpx import AsyncClient
from repositories.items import ItemRepository
from repositories.moderation_results import ModerationResultRepository

pytestmark = [pytest.mark.asyncio, pytest.mark.unit]


async def test_close_item_success(client: AsyncClient, monkeypatch):
    mock_close_item = AsyncMock(return_value=True)
    monkeypatch.setattr(ItemRepository, "close_item", mock_close_item)

    mock_get_task_ids = AsyncMock(return_value=[1, 2])
    monkeypatch.setattr(ModerationResultRepository, "get_task_ids_by_item_id", mock_get_task_ids)

    mock_pred_storage = AsyncMock()
    mock_mod_storage = AsyncMock()
    from main import app
    app.state.prediction_storage = mock_pred_storage
    app.state.moderation_result_storage = mock_mod_storage

    response = await client.post("/close", params={"item_id": 42})
    assert response.status_code == 200
    assert response.json() == {"status": "closed", "item_id": 42}

    mock_close_item.assert_called_once_with(42)
    mock_get_task_ids.assert_called_once_with(42)
    mock_pred_storage.delete.assert_called_once_with(42)
    assert mock_mod_storage.delete.call_count == 2
    mock_mod_storage.delete.assert_any_call(1)
    mock_mod_storage.delete.assert_any_call(2)


async def test_close_item_not_found(client: AsyncClient, monkeypatch):
    mock_close_item = AsyncMock(return_value=False)
    monkeypatch.setattr(ItemRepository, "close_item", mock_close_item)

    mock_pred_storage = AsyncMock()
    mock_mod_storage = AsyncMock()
    from main import app
    app.state.prediction_storage = mock_pred_storage
    app.state.moderation_result_storage = mock_mod_storage

    response = await client.post("/close", params={"item_id": 999})
    assert response.status_code == 404
    mock_pred_storage.delete.assert_not_called()
    mock_mod_storage.delete.assert_not_called()