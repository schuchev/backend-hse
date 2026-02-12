import logging

from fastapi import APIRouter
from schemas.predict import PredictRequest, PredictResponse
from services.moderation import predict_violation, simple_predict_violation
from ml.predictor import ModerationPredictor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/predict", tags=["moderation"])


@router.post("", response_model=PredictResponse)
async def predict(request: PredictRequest) -> PredictResponse:
    logger.info(
        "Incoming request: seller_id=%d, item_id=%d, is_verified=%s, images=%d, category=%d, name_len=%d",
        request.seller_id,
        request.item_id,
        request.is_verified_seller,
        request.images_qty,
        request.category,
        len(request.name),
    )
    return predict_violation(request)


@router.post("/simple_predict", response_model=PredictResponse)
async def simple_predict(item_id: int) -> PredictResponse:
    """
    только item_id
    Остальные данные берутся из БД
    """
    logger.info("Simple predict request for item_id=%d", item_id)
    return await simple_predict_violation(item_id)


@router.get("/health")
async def health():
    """Проверка здоровья сервиса"""
    _ = ModerationPredictor.instance()
    return {"status": "healthy", "model_loaded": True}
