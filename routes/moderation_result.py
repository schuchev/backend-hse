from fastapi import APIRouter, HTTPException, Request
from schemas.moderation_result import ModerationResultResponse

router = APIRouter(tags=["moderation"])


@router.get("/moderation_result/{task_id}", response_model=ModerationResultResponse)
async def moderation_result(task_id: int, request: Request) -> ModerationResultResponse:
    pool = request.app.state.pg_pool

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, status, is_violation, probability
            FROM moderation_results
            WHERE id = $1
            """,
            task_id,
        )

    if row is None:
        raise HTTPException(status_code=404, detail="Task not found")

    return ModerationResultResponse(
        task_id=row["id"],
        status=row["status"],
        is_violation=row["is_violation"],
        probability=row["probability"],
    )
