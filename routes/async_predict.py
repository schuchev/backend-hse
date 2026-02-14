from fastapi import APIRouter, HTTPException, Request
from schemas.async_predict import AsyncPredictRequest, AsyncPredictResponse

router = APIRouter(tags=["moderation"])


@router.post("/async_predict", response_model=AsyncPredictResponse)
async def async_predict(payload: AsyncPredictRequest, request: Request) -> AsyncPredictResponse:
    pool = request.app.state.pg_pool
    producer = request.app.state.kafka_producer

    async with pool.acquire() as conn:
        exists = await conn.fetchval("SELECT 1 FROM items WHERE id = $1", payload.item_id)
        if not exists:
            raise HTTPException(status_code=404, detail="Item not found")

        task_id = await conn.fetchval(
            """
            INSERT INTO moderation_results (item_id, status, created_at)
            VALUES ($1, 'pending', now())
            RETURNING id
            """,
            payload.item_id,
        )

    await producer.send_moderation_request(payload.item_id)

    return AsyncPredictResponse(
        task_id=task_id,
        status="pending",
        message="Moderation request accepted",
    )
