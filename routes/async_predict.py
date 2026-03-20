from fastapi import APIRouter, HTTPException, Request, Depends

from schemas.async_predict import AsyncPredictRequest, AsyncPredictResponse
from repositories.items import ItemRepository
from repositories.moderation_results import ModerationResultRepository
from dependencies.auth import get_current_account

router = APIRouter(tags=["moderation"])


@router.post("/async_predict", response_model=AsyncPredictResponse)
async def async_predict(payload: AsyncPredictRequest, request: Request, account: dict = Depends(get_current_account)) -> AsyncPredictResponse:

    producer = request.app.state.kafka_producer

    item = await ItemRepository.get_item_with_user(payload.item_id)

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    task_id = await ModerationResultRepository.create_pending(payload.item_id)

    await producer.send_moderation_request(payload.item_id)

    return AsyncPredictResponse(
        task_id=task_id,
        status="pending",
        message="Moderation request accepted",
    )