import logging

from fastapi import HTTPException
from schemas.predict import PredictRequest, PredictResponse
from ml.predictor import ModerationPredictor
from repositories.items import ItemRepository

logger = logging.getLogger(__name__)

THRESHOLD = 0.5

def predict_violation(request: PredictRequest) -> PredictResponse:
    """
    Предсказание по полным данным (старый эндпоинт /predict).
    """
    proba = ModerationPredictor.instance().predict_proba_violation(request)
    is_violation = proba >= THRESHOLD

    response = PredictResponse(is_violation=is_violation, probability=proba)

    logger.info(
        "Prediction for seller_id=%d, item_id=%d: is_violation=%s, probability=%.4f",
        request.seller_id,
        request.item_id,
        response.is_violation,
        response.probability,
    )
    return response


async def simple_predict_violation(item_id: int) -> PredictResponse:
    """
    новый эндпоинт /simple_predict

    Получает данные из БД и делает предсказание
    """
    item_data = await ItemRepository.get_item_with_user(item_id)

    if not item_data:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")

    request = PredictRequest(
        seller_id=item_data["user_id"],
        is_verified_seller=item_data["is_verified"],
        item_id=item_data["id"],
        name=item_data["name"],
        description=item_data["description"],
        category=item_data["category"],
        images_qty=item_data["images_qty"]
    )

    return predict_violation(request)
