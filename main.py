import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from sklearn.linear_model import LogisticRegression
from dotenv import load_dotenv

from model import load_model_smart
from routes.predict import router as predict_router

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

USE_MLFLOW = os.getenv("USE_MLFLOW", "false").lower() == "true"


@asynccontextmanager
async def lifespan(app: FastAPI):

    logger.info("Starting up application...")
    logger.info(f"Using MLflow: {USE_MLFLOW}")

    try:
        app.state.model = load_model_smart(use_mlflow=USE_MLFLOW)
        logger.info(" Model loaded successfully")
    except Exception as e:
        logger.error(f" Failed to load model: {e}")
        app.state.model = None

    yield

    logger.info("Shutting down application...")
    app.state.model = None


app = FastAPI(
    title="Moderation Service",
    description="API для модерации объявлений с ML моделью",
    version="2.0.0",
    lifespan=lifespan
)


@app.get("/")
async def root():
    return {
        "message": "Welcome to Moderation Service",
        "version": "2.0.0",
        "docs": "/docs",
        "using_mlflow": USE_MLFLOW
    }


app.include_router(predict_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
