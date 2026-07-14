from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings

client = AsyncIOMotorClient(settings.mongo_uri)
database = client[settings.mongo_db_name]

users_collection = database["users"]
conversations_collection = database["conversations"]
messages_collection = database["messages"]


async def init_indexes() -> None:
    """Create indexes needed for performance and uniqueness constraints."""
    await users_collection.create_index("email", unique=True)
    await conversations_collection.create_index("user_id")
    await messages_collection.create_index([("conversation_id", 1), ("created_at", 1)])
