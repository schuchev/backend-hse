import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from database import init_db, close_db, get_db_connection
from model import load_model_smart
from ml.predictor import ModerationPredictor

from repositories.items import ItemRepository
from repositories.moderation_results import ModerationResultRepository

logger = logging.getLogger("moderation_worker")
logging.basicConfig(level=logging.INFO)

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC = os.getenv("KAFKA_MODERATION_TOPIC", "moderation")
DLQ_TOPIC = os.getenv("KAFKA_DLQ_TOPIC", "moderation_dlq")
GROUP_ID = os.getenv("KAFKA_GROUP_ID", "moderation-worker")

USE_MLFLOW = os.getenv("USE_MLFLOW", "false").lower() == "true"

MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
RETRY_DELAY_SECONDS = int(os.getenv("RETRY_DELAY_SECONDS", "5"))


class RetryableMLError(Exception):
    pass


async def send_to_dlq(
    dlq_producer: AIOKafkaProducer,
    original_message: Any,
    error: str,
    retry_count: int = 1,
) -> None:
    payload = {
        "original_message": original_message,
        "error": error,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "retry_count": retry_count,
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    await dlq_producer.send_and_wait(DLQ_TOPIC, data)



async def process_one(item_id: int, dlq_producer: AIOKafkaProducer, original_message: Any) -> None:

    row = await ItemRepository.get_item_with_user(item_id)

    task_id = await ModerationResultRepository.get_latest_pending_task(item_id)

    if task_id is None:
        return

    if row is None:
        err = f"Item {item_id} not found"
        await ModerationResultRepository.mark_failed(task_id, err)
        await send_to_dlq(dlq_producer, original_message, err, retry_count=1)
        return

    try:
        is_violation, probability = await asyncio.to_thread(
            ModerationPredictor.predict,
            seller_id=row["user_id"],
            is_verified_seller=row["is_verified"],
            item_id=row["id"],
            name=row["name"],
            description=row["description"],
            category=row["category"],
            images_qty=row["images_qty"],
        )
    except Exception as e:
        raise RetryableMLError(str(e)) from e

    await ModerationResultRepository.mark_completed(
        task_id,
        bool(is_violation),
        float(probability),
    )


async def main() -> None:
    await init_db()

    model = load_model_smart(use_mlflow=USE_MLFLOW)
    ModerationPredictor.init(model)

    consumer = AIOKafkaConsumer(
        TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP,
        group_id=GROUP_ID,
        enable_auto_commit=False,
        auto_offset_reset="earliest",
    )

    dlq_producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP)

    await consumer.start()
    await dlq_producer.start()
    try:
        async for msg in consumer:
            original_message: Any = None

            try:
                original_message = json.loads(msg.value.decode("utf-8"))
                item_id = int(original_message["item_id"])
            except Exception as e:
                err = f"Bad message: {e}"
                logger.exception(err)
                await send_to_dlq(dlq_producer, original_message, err, retry_count=1)
                await consumer.commit()
                continue

            attempt = 1
            try:
                while True:
                    try:
                        await process_one(item_id, dlq_producer, original_message)
                        break

                    except RetryableMLError as e:
                        if attempt < MAX_RETRIES:
                            logger.warning(
                                "Retryable ML error. attempt=%s/%s; sleep=%ss; error=%s",
                                attempt,
                                MAX_RETRIES,
                                RETRY_DELAY_SECONDS,
                                e,
                            )
                            await asyncio.sleep(RETRY_DELAY_SECONDS)
                            attempt += 1
                            continue

                        err = f"ML error after {attempt} attempts: {e}"
                        logger.exception(err)

                        task_id = await ModerationResultRepository.get_latest_pending_task(item_id)
                        if task_id is not None:
                            await ModerationResultRepository.mark_failed(task_id, err)

                        await send_to_dlq(dlq_producer, original_message, err, retry_count=attempt)
                        break

                    except Exception as e:
                        err = f"Unexpected error: {e}"
                        logger.exception(err)

                        task_id = await ModerationResultRepository.get_latest_pending_task(item_id)
                        if task_id is not None:
                            await ModerationResultRepository.mark_failed(task_id, err)

                        await send_to_dlq(dlq_producer, original_message, err, retry_count=1)
                        break
            finally:
                await consumer.commit()
    finally:
        await dlq_producer.stop()
        await consumer.stop()
        await close_db()


if __name__ == "__main__":
    asyncio.run(main())
