import logging
from fastapi import HTTPException
from schemas.predict import PredictRequest, PredictResponse
from ml.predictor import ModerationPredictor
from repositories.items import ItemRepository
from app.storage.prediction_storage import PredictionRedisStorage

logger = logging.getLogger(__name__)

THRESHOLD = 0.5


async def predict_violation(request: PredictRequest, storage: PredictionRedisStorage) -> PredictResponse:
    cached = await storage.get(request.item_id)
    if cached:
        logger.info("Cache hit for item_id=%d", request.item_id)
        return PredictResponse(
            is_violation=cached["is_violation"],
            probability=cached["probability"]
        )

    proba = ModerationPredictor.instance().predict_proba_violation(request)
    is_violation = proba >= THRESHOLD

    await storage.set(request.item_id, {
        "is_violation": is_violation,
        "probability": proba
    })

    response = PredictResponse(is_violation=is_violation, probability=proba)
    logger.info("Prediction for item_id=%d: is_violation=%s, probability=%.4f",
                request.item_id, is_violation, proba)
    return response


async def simple_predict_violation(item_id: int, storage: PredictionRedisStorage) -> PredictResponse:
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

    return await predict_violation(request, storage)