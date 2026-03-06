import logging
from fastapi import APIRouter, Request
from schemas.predict import PredictRequest, PredictResponse
from services.moderation import predict_violation, simple_predict_violation

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/predict", tags=["moderation"])


@router.post("", response_model=PredictResponse)
async def predict(request: Request, predict_req: PredictRequest) -> PredictResponse:
    logger.info("Predict request for item_id=%d", predict_req.item_id)
    storage = request.app.state.prediction_storage
    return await predict_violation(predict_req, storage)


@router.post("/simple_predict", response_model=PredictResponse)
async def simple_predict(request: Request, item_id: int) -> PredictResponse:
    logger.info("Simple predict request for item_id=%d", item_id)
    storage = request.app.state.prediction_storage
    return await simple_predict_violation(item_id, storage)


@router.get("/health")
async def health():
    from ml.predictor import ModerationPredictor
    _ = ModerationPredictor.instance()
    return {"status": "healthy", "model_loaded": True}