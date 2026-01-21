from fastapi import FastAPI
from pydantic import BaseModel, Field


app=FastAPI()

@app.get("/")
async def root():
    return {'message':'Hello World'}

class PredictRequest(BaseModel):
    seller_id: int
    is_verified_seller: bool
    item_id: int
    name: str
    description: str
    category: int
    images_qty: int = Field(ge=0)


@app.post("/predict")
async def predict(request: PredictRequest) -> bool:
    if request.is_verified_seller:
        return True

    return request.images_qty > 0