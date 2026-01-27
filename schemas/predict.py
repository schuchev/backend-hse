from pydantic import BaseModel, Field

class PredictRequest(BaseModel):
    seller_id: int = Field(gt=0, description="ID продавца (должен быть > 0)")
    is_verified_seller: bool = Field(description="Подтверждён ли продавец")
    item_id: int = Field(gt=0, description="ID объявления (должен быть > 0)")
    name: str = Field(min_length=1, max_length=255, description="Название объявления")
    description: str = Field(min_length=1, max_length=5000, description="Описание объявления")
    category: int = Field(gt=0, description="Категория (должна быть > 0)")
    images_qty: int = Field(ge=0, description="Количество изображений (не может быть < 0)")

class PredictResponse(BaseModel):
    is_approved: bool = Field(description="Одобрено ли объявление")
