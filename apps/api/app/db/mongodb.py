from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages the MongoDB connection lifecycle."""
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None

    async def connect(self, mongo_url: str, db_name: str):
        """Establish connection and verify with ping."""
        try:
            self.client = AsyncIOMotorClient(
                mongo_url,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000
            )
            # Verify connection works (Point 49)
            await self.client.admin.command("ping")
            self.db = self.client[db_name]
            logger.info(f"LIFECYCLE: Standardized connection to MongoDB: {db_name}")
        except Exception as e:
            logger.error(f"LIFECYCLE_FATAL: Database connection failed: {e}")
            raise

    def close(self):
        """Close the MongoDB connection."""
        if self.client:
            self.client.close()
            logger.info("LIFECYCLE: MongoDB connection closed gracefully")

# Global singleton for app lifecycle management (Point 7)
db_manager = DatabaseManager()

async def get_db() -> AsyncIOMotorDatabase:
    """FastAPI Dependency to get the database instance (Point 2, 7)"""
    if db_manager.db is None:
        raise RuntimeError("DATABASE_DOMAIN_ERROR: Engine not initialized. Access blocked.")
    return db_manager.db
