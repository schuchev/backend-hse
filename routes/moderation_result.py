from fastapi import APIRouter, HTTPException
from repositories.moderation_results import ModerationResultRepository
from schemas.moderation_result import ModerationResultResponse

router = APIRouter(tags=["moderation"])


@router.get("/moderation_result/{task_id}", response_model=ModerationResultResponse)
async def moderation_result(task_id: int) -> ModerationResultResponse:
    result = await ModerationResultRepository.get_task_with_cache(task_id)
    if not result:
        raise HTTPException(status_code=404, detail="Task not found")
    return result