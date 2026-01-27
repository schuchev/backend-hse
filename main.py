from fastapi import FastAPI
from routes.predict import router as predict_router

app = FastAPI(
    title="Moderation Service",
    description="API для модерации объявлений",
    version="1.0.0"
)

@app.get("/")
async def root():
    return {"message": "Hello World"}

app.include_router(predict_router)
