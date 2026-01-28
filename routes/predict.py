import logging
from fastapi import APIRouter, Depends, HTTPException
from sklearn.linear_model import LogisticRegression

from schemas.predict import PredictRequest, PredictResponse
from services.moderation import predict_violation

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/predict", tags=["moderation"])


def get_model() -> LogisticRegression:

    from main import app

    if app.state.model is None:
        raise HTTPException(
            status_code=503,
            detail="Model is not available"
        )
    return app.state.model


@router.post("", response_model=PredictResponse)
async def predict(request: PredictRequest,model: LogisticRegression = Depends(get_model)) -> PredictResponse:

    try:
        logger.info(
            "Incoming request: seller_id=%d, item_id=%d, "
            "is_verified=%s, images=%d, category=%d, name_len=%d",
            request.seller_id,
            request.item_id,
            request.is_verified_seller,
            request.images_qty,
            request.category,
            len(request.name)
        )

        response = predict_violation(request, model)
        return response

    except ValueError as e:
        logger.error("Validation error: %s", e)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Prediction error for seller_id=%d", request.seller_id)
        raise HTTPException(
            status_code=500,
            detail=f"Prediction failed: {str(e)}"
        )


@router.get("/health")
async def health(model: LogisticRegression = Depends(get_model)):
    return {
        "status": "healthy",
        "model_loaded": model is not None
    }
