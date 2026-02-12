import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from model import load_model_smart
from routes.predict import router as predict_router
from ml.predictor import ModerationPredictor, ModelNotAvailableError
from database import init_db, close_db

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

USE_MLFLOW = os.getenv("USE_MLFLOW", "false").lower() == "true"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up application...")
    logger.info("Using MLflow: %s", USE_MLFLOW)

    try:
        await init_db()
        logger.info("Database pool initialized")
    except Exception as e:
        logger.error("Failed to initialize database: %s", e)

    try:
        model = load_model_smart(use_mlflow=USE_MLFLOW)
        ModerationPredictor.init(model)
        logger.info("Model loaded successfully")
    except Exception as e:
        ModerationPredictor.reset()
        logger.error("Failed to load model: %s", e)

    yield

    logger.info("Shutting down application...")
    ModerationPredictor.reset()
    await close_db()
    logger.info("Database pool closed")


app = FastAPI(
    title="Moderation Service",
    description="API для модерации объявлений с ML моделью и PostgreSQL",
    version="3.0.0",
    lifespan=lifespan,
)


@app.exception_handler(ModelNotAvailableError)
async def model_not_available_handler(request: Request, exc: ModelNotAvailableError):
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.get("/")
async def root():
    return {
        "message": "Welcome to Moderation Service",
        "version": "3.0.0",
        "docs": "/docs",
        "using_mlflow": USE_MLFLOW,
    }


app.include_router(predict_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
