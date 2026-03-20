import asyncio
from repositories.users import UserRepository
from repositories.items import ItemRepository
from database import init_db, close_db
from dotenv import load_dotenv
load_dotenv()

async def seed():
    await init_db()
    user_id = await UserRepository.create_user(is_verified=False)
    item_id = await ItemRepository.create_item(
        user_id=user_id,
        name="Test item",
        description="a" * 50,
        category=5,
        images_qty=0
    )
    print(f"Created item with id {item_id}")
    await close_db()

asyncio.run(seed())