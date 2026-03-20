from fastapi import APIRouter, HTTPException, Depends
from repositories.moderation_results import ModerationResultRepository
from schemas.moderation_result import ModerationResultResponse
from dependencies.auth import get_current_account

router = APIRouter(tags=["moderation"])


@router.get("/moderation_result/{task_id}", response_model=ModerationResultResponse)
async def moderation_result(task_id: int,account: dict = Depends(get_current_account)) -> ModerationResultResponse:
    result = await ModerationResultRepository.get_task_with_cache(task_id)
    if not result:
        raise HTTPException(status_code=404, detail="Task not found")
    return result