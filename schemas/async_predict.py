from pydantic import BaseModel, Field

class AsyncPredictRequest(BaseModel):
    item_id: int = Field(gt=0, description="ID объявления")


class AsyncPredictResponse(BaseModel):
    task_id: int = Field(description="ID записи в moderation_results")
    status: str = Field(description="pending/completed/failed")
    message: str = Field(description="Текстовое сообщение")
