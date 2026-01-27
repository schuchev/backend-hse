from fastapi import APIRouter
from schemas.predict import PredictRequest, PredictResponse
from services.moderation import predict_listing

router = APIRouter(prefix="/predict", tags=["moderation"])

@router.post("", response_model=PredictResponse)
async def predict(request: PredictRequest) -> PredictResponse:
    """
    Проверяет, одобрено ли объявление.

    Args:
        request: Данные объявления с обязательными полями

    Returns:
        PredictResponse с результатом проверки
    """
    is_approved = predict_listing(request)
    return PredictResponse(is_approved=is_approved)