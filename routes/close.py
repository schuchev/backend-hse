from fastapi import APIRouter, HTTPException, Request
from repositories.items import ItemRepository
from repositories.moderation_results import ModerationResultRepository
from app.storage.prediction_storage import PredictionRedisStorage
from app.storage.moderation_result_storage import ModerationResultRedisStorage

router = APIRouter(prefix="/close", tags=["items"])


@router.post("")
async def close_item(request: Request, item_id: int):

    success = await ItemRepository.close_item(item_id)
    if not success:
        raise HTTPException(status_code=404, detail="Item not found")

    pred_storage: PredictionRedisStorage = request.app.state.prediction_storage
    await pred_storage.delete(item_id)

    task_ids = await ModerationResultRepository.get_task_ids_by_item_id(item_id)

    mod_storage: ModerationResultRedisStorage = request.app.state.moderation_result_storage
    for task_id in task_ids:
        await mod_storage.delete(task_id)

    return {"status": "closed", "item_id": item_id}