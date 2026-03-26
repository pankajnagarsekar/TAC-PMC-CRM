from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    client: AsyncIOMotorClient = None
    db: AsyncIOMotorDatabase = None

    def connect(self, mongo_url: str, db_name: str):
        self.client = AsyncIOMotorClient(mongo_url)
        self.db = self.client[db_name]
        logger.info(f"Connected to MongoDB: {db_name}")

    def close(self):
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")

db_manager = DatabaseManager()

async def get_db() -> AsyncIOMotorDatabase:
    """Dependency for getting the database instance."""
    if db_manager.db is None:
        # Fallback for scripts or if not initialized via app lifecycle
        db_manager.connect(settings.MONGO_URL, settings.DB_NAME)
    return db_manager.db
