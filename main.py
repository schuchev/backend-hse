import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from aiokafka import AIOKafkaProducer
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from database import init_db, close_db, get_pool
from ml.predictor import ModerationPredictor, ModelNotAvailableError
from model import load_model_smart
from routes.predict import router as predict_router
from routes.async_predict import router as async_predict_router
from routes.moderation_result import router as moderation_result_router

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

USE_MLFLOW = os.getenv("USE_MLFLOW", "false").lower() == "true"

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_MODERATION_TOPIC = os.getenv("KAFKA_MODERATION_TOPIC", "moderation")


class KafkaProducerAdapter:
    def __init__(self, producer: AIOKafkaProducer):
        self._producer = producer

    async def send_moderation_request(self, item_id: int) -> None:
        payload = {"item_id": item_id, "timestamp": datetime.now(timezone.utc).isoformat()}
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        await self._producer.send_and_wait(KAFKA_MODERATION_TOPIC, data)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up application...")
    logger.info("Using MLflow: %s", USE_MLFLOW)

    await init_db()
    app.state.pg_pool = get_pool()
    logger.info("Database pool initialized")

    try:
        model = load_model_smart(use_mlflow=USE_MLFLOW)
        ModerationPredictor.init(model)
        logger.info("Model loaded successfully")
    except Exception as e:
        ModerationPredictor.reset()
        logger.error("Failed to load model: %s", e)

    kafka_producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP)
    await kafka_producer.start()
    app.state.kafka_producer = KafkaProducerAdapter(kafka_producer)
    logger.info("Kafka producer started (%s)", KAFKA_BOOTSTRAP)

    yield

    logger.info("Shutting down application...")
    await kafka_producer.stop()
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
app.include_router(async_predict_router)
app.include_router(moderation_result_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
