import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from main import app
from database import init_db, close_db, get_db_connection
from model import load_or_train_model
from ml.predictor import ModerationPredictor
from app.clients.redis import init_redis_pool, close_redis_pool, flushall


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def initialize_model():
    model = load_or_train_model("test_model.pkl")
    ModerationPredictor.init(model)
    yield
    ModerationPredictor.reset()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def initialize_database():
    await init_db()
    yield
    await close_db()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def redis_pool():
    init_redis_pool()
    yield
    await close_redis_pool()


@pytest_asyncio.fixture(autouse=True)
async def clear_redis():
    await flushall()
    yield


@pytest_asyncio.fixture
async def db_connection():
    async with get_db_connection() as conn:
        tr = conn.transaction()
        await tr.start()
        try:
            yield conn
        finally:
            await tr.rollback()


class FakeKafkaProducer:
    def __init__(self):
        self.sent_item_ids = []

    async def send_moderation_request(self, item_id: int) -> None:
        self.sent_item_ids.append(item_id)


@pytest_asyncio.fixture()
async def fake_kafka_producer() -> FakeKafkaProducer:
    return FakeKafkaProducer()


class PoolAdapter:
    def acquire(self):
        return get_db_connection()


@pytest_asyncio.fixture(autouse=True)
async def patch_app_state(fake_kafka_producer: FakeKafkaProducer):
    from app.storage.prediction_storage import PredictionRedisStorage
    app.state.pg_pool = PoolAdapter()
    app.state.kafka_producer = fake_kafka_producer
    app.state.prediction_storage = PredictionRedisStorage()
    yield


@pytest_asyncio.fixture()
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c