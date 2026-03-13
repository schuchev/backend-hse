import logging
import time
from fastapi import HTTPException
from schemas.predict import PredictRequest, PredictResponse
from ml.predictor import ModerationPredictor, ModelNotAvailableError
from repositories.items import ItemRepository
from app.storage.prediction_storage import PredictionRedisStorage
from app.metrics import (
    PREDICTIONS_TOTAL,
    PREDICTION_DURATION,
    PREDICTION_ERRORS_TOTAL,
    MODEL_PREDICTION_PROBABILITY,
)

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

    start_time = time.time()
    try:
        proba = ModerationPredictor.instance().predict_proba_violation(request)
        duration = time.time() - start_time

        PREDICTION_DURATION.observe(duration)

        is_violation = proba >= THRESHOLD
        result_label = "violation" if is_violation else "no_violation"
        PREDICTIONS_TOTAL.labels(result=result_label).inc()

        MODEL_PREDICTION_PROBABILITY.observe(proba)

        await storage.set(request.item_id, {
            "is_violation": is_violation,
            "probability": proba
        })

        response = PredictResponse(is_violation=is_violation, probability=proba)
        logger.info("Prediction for item_id=%d: is_violation=%s, probability=%.4f",
                    request.item_id, is_violation, proba)
        return response

    except Exception as e:
        if isinstance(e, ModelNotAvailableError):
            error_type = "model_unavailable"
        else:
            error_type = "prediction_error"
        PREDICTION_ERRORS_TOTAL.labels(error_type=error_type).inc()
        logger.error("Prediction error for item_id=%d: %s", request.item_id, str(e))
        raise 


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