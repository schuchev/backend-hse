import asyncio
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator, List, Dict, Any, Optional

import asyncpg
import httpx
import pytest
import pytest_asyncio
from httpx import AsyncClient

from main import app as fastapi_app
from database import init_db, close_db, get_db_connection
from model import load_or_train_model
from ml.predictor import ModerationPredictor


class FakeRedisStorage:
    def __init__(self):
        self._data: Dict[str, Any] = {}
        self._ttl: Dict[str, int] = {} 

    async def get(self, key: str) -> Optional[Any]:
        return self._data.get(key)

    async def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    async def delete(self, key: str) -> None:
        self._data.pop(key, None)


class MockRedisClient:
    def __init__(self):
        self._data = {}
        self._pipeline_commands = []

    async def get(self, key):
        return self._data.get(key)

    async def set(self, key, value, *args, **kwargs):
        self._data[key] = value
        return True

    async def setex(self, key, seconds, value):
        self._data[key] = value
        return True

    async def delete(self, key):
        self._data.pop(key, None)
        return 1

    def pipeline(self):
        self._pipeline_commands = []
        return self

    async def execute(self):
        results = []
        for cmd in self._pipeline_commands:
            if cmd[0] == "set":
                self._data[cmd[1]] = cmd[2]
                results.append(True)
            elif cmd[0] == "expire":
                results.append(True)
        self._pipeline_commands = []
        return results

    def set(self, key, value):
        self._pipeline_commands.append(("set", key, value))
        return self

    def expire(self, key, seconds):
        self._pipeline_commands.append(("expire", key, seconds))
        return self


@asynccontextmanager
async def fake_redis_connection():
    yield MockRedisClient()


async def drop_all_tables(conn):
    await conn.execute("SET session_replication_role = 'replica';")
    try:
        rows = await conn.fetch("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public' AND tablename != 'migrations'
        """)
        for row in rows:
            table = row['tablename']
            await conn.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE')
    finally:
        await conn.execute("SET session_replication_role = 'origin';")


async def run_migrations():
    from database import DATABASE_URL
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await drop_all_tables(conn)
        migrations_dir = os.path.join(os.path.dirname(__file__), "..", "db", "migrations")
        if not os.path.exists(migrations_dir):
            return
        migration_files = sorted(f for f in os.listdir(migrations_dir) if f.endswith(".sql"))
        for file in migration_files:
            with open(os.path.join(migrations_dir, file), "r") as f:
                sql = f.read()
            await conn.execute(sql)
    finally:
        await conn.close()


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


@pytest_asyncio.fixture(scope="session")
async def setup_database():
    await run_migrations()


@pytest_asyncio.fixture(scope="function",autouse=True)
async def initialize_database(setup_database):
    await init_db()
    yield
    await close_db()


@pytest_asyncio.fixture(scope="function")
async def db_connection(initialize_database) -> AsyncGenerator[asyncpg.Connection, None]:
    async with get_db_connection() as conn:
        tr = conn.transaction()
        await tr.start()
        try:
            yield conn
        finally:
            await tr.rollback()


class PoolAdapter:
    def acquire(self):
        return get_db_connection()


class FakeKafkaProducer:
    def __init__(self):
        self.sent_item_ids: List[int] = []

    async def send_moderation_request(self, item_id: int) -> None:
        self.sent_item_ids.append(item_id)


@pytest_asyncio.fixture()
async def fake_kafka_producer() -> FakeKafkaProducer:
    return FakeKafkaProducer()


@pytest_asyncio.fixture(autouse=True)
async def patch_app_state(fake_kafka_producer: FakeKafkaProducer, monkeypatch):
    fastapi_app.state.pg_pool = PoolAdapter()
    fastapi_app.state.kafka_producer = fake_kafka_producer

    from app.storage.prediction_storage import PredictionRedisStorage
    from app.storage.moderation_result_storage import ModerationResultRedisStorage
    fastapi_app.state.prediction_storage = FakeRedisStorage()
    fastapi_app.state.moderation_result_storage = FakeRedisStorage()

    import app.clients.redis as redis_module
    import repositories.moderation_results
    import app.storage.prediction_storage
    import app.storage.account_storage 
    
    fake_conn = fake_redis_connection

    monkeypatch.setattr(redis_module, "get_redis_connection", fake_conn)
    monkeypatch.setattr(repositories.moderation_results, "get_redis_connection", fake_conn)
    monkeypatch.setattr(app.storage.prediction_storage, "get_redis_connection", fake_conn)
    monkeypatch.setattr(app.storage.account_storage, "get_redis_connection", fake_conn)

    yield


@pytest_asyncio.fixture()
async def client():
    transport = httpx.ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
        
        
@pytest_asyncio.fixture
async def auth_client(client: AsyncClient):
    await client.post("/auth/register", json={"login": "authuser", "password": "pass"})
    login_resp = await client.post("/auth/login", json={"login": "authuser", "password": "pass"})
    token = login_resp.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    yield client