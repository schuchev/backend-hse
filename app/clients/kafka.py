import json
from datetime import datetime, timezone
from typing import Optional

from aiokafka import AIOKafkaProducer


class KafkaProducerClient:
    def __init__(self,bootstrap_servers: str = "localhost:9092",topic: str = "moderation") -> None:
        self._bootstrap_servers = bootstrap_servers
        self._topic = topic
        self._producer: Optional[AIOKafkaProducer] = None

    async def start(self) -> None:
        if self._producer is not None:
            return
        self._producer = AIOKafkaProducer(bootstrap_servers=self._bootstrap_servers)
        await self._producer.start()

    async def stop(self) -> None:
        if self._producer is None:
            return
        await self._producer.stop()
        self._producer = None

    async def send_moderation_request(self, item_id: int) -> None:
        if self._producer is None:
            raise RuntimeError("Kafka producer is not started. Call start() first")

        payload = {
            "item_id": int(item_id),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        value = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        await self._producer.send_and_wait(self._topic, value)
