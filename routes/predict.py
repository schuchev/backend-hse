import logging
from fastapi import APIRouter, Request, Depends
from schemas.predict import PredictRequest, PredictResponse
from services.moderation import predict_violation, simple_predict_violation
from dependencies.auth import get_current_account

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/predict", tags=["moderation"])


@router.post("", response_model=PredictResponse)
async def predict(request: Request, predict_req: PredictRequest,account: dict = Depends(get_current_account)) -> PredictResponse:
    logger.info("Predict request for item_id=%d by user_id=%d", predict_req.item_id, account["id"])
    storage = request.app.state.prediction_storage
    return await predict_violation(predict_req, storage)


@router.post("/simple_predict", response_model=PredictResponse)
async def simple_predict(request: Request, item_id: int, account: dict = Depends(get_current_account)) -> PredictResponse:
    logger.info("Simple predict request for item_id=%d by user_id=%d", item_id, account["id"])
    storage = request.app.state.prediction_storage
    return await simple_predict_violation(item_id, storage)


@router.get("/health")
async def health():
    from ml.predictor import ModerationPredictor
    _ = ModerationPredictor.instance()
    return {"status": "healthy", "model_loaded": True}