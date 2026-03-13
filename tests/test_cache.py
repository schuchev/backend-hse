import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from schemas.predict import PredictRequest, PredictResponse
from services.moderation import predict_violation, simple_predict_violation
from ml.predictor import ModerationPredictor


@pytest.mark.asyncio
async def test_predict_violation_cache_hit():
    item_id = 42
    cached_data = {"is_violation": True, "probability": 0.95}
    mock_storage = AsyncMock()
    mock_storage.get.return_value = cached_data

    request = PredictRequest(
        seller_id=1,
        is_verified_seller=False,
        item_id=item_id,
        name="Test",
        description="desc",
        category=1,
        images_qty=1
    )

    with patch.object(ModerationPredictor, "instance") as mock_instance:
        mock_predictor = MagicMock()
        mock_instance.return_value = mock_predictor

        response = await predict_violation(request, mock_storage)

        assert isinstance(response, PredictResponse)
        assert response.is_violation == cached_data["is_violation"]
        assert response.probability == cached_data["probability"]
        mock_storage.get.assert_awaited_once_with(item_id)
        mock_predictor.predict_proba_violation.assert_not_called()
        mock_storage.set.assert_not_called()


@pytest.mark.asyncio
async def test_predict_violation_cache_miss():
    item_id = 42
    mock_storage = AsyncMock()
    mock_storage.get.return_value = None

    request = PredictRequest(
        seller_id=1,
        is_verified_seller=False,
        item_id=item_id,
        name="Test",
        description="desc",
        category=1,
        images_qty=1
    )

    fake_proba = 0.78
    fake_is_violation = fake_proba >= 0.5

    with patch.object(ModerationPredictor, "instance") as mock_instance:
        mock_predictor = MagicMock()
        mock_predictor.predict_proba_violation.return_value = fake_proba
        mock_instance.return_value = mock_predictor

        response = await predict_violation(request, mock_storage)

        assert response.is_violation == fake_is_violation
        assert response.probability == fake_proba
        mock_storage.get.assert_awaited_once_with(item_id)
        mock_predictor.predict_proba_violation.assert_called_once_with(request)
        mock_storage.set.assert_awaited_once_with(
            item_id,
            {"is_violation": fake_is_violation, "probability": fake_proba}
        )


@pytest.mark.asyncio
async def test_simple_predict_violation_calls_predict():
    with patch("services.moderation.ItemRepository.get_item_with_user") as mock_get_item, \
         patch("services.moderation.predict_violation") as mock_predict:

        item_id = 42
        mock_get_item.return_value = {
            "user_id": 1,
            "is_verified": True,
            "id": item_id,
            "name": "Test",
            "description": "desc",
            "category": 1,
            "images_qty": 1
        }

        expected_response = PredictResponse(is_violation=False, probability=0.12)
        mock_predict.return_value = expected_response

        mock_storage = AsyncMock()

        response = await simple_predict_violation(item_id, mock_storage)

        assert response == expected_response
        mock_get_item.assert_awaited_once_with(item_id)
        call_args = mock_predict.call_args[0]
        assert isinstance(call_args[0], PredictRequest)
        assert call_args[0].item_id == item_id
        assert call_args[1] is mock_storage