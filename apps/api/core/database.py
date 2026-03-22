from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from contextlib import asynccontextmanager
from bson import ObjectId, Decimal128
from decimal import Decimal
import os
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.client: AsyncIOMotorClient = None
        self.db: AsyncIOMotorDatabase = None

    def connect(self, mongo_url: str, db_name: str):
        self.client = AsyncIOMotorClient(mongo_url)
        self.db = self.client[db_name]
        logger.info(f"Connected to MongoDB: {db_name}")

    def disconnect(self):
        if self.client:
            self.client.close()
            logger.info("Disconnected from MongoDB")

    @asynccontextmanager
    async def transaction_session(self):
        """
        Async context manager for MongoDB multi-document transactions.
        Gracefully falls back to a regular session if transactions are not supported.
        """
        from pymongo.errors import OperationFailure
        
        session = await self.client.start_session()
        try:
            # We check if we can start a transaction
            try:
                async with session.start_transaction():
                    yield session
                return # If successful, we are done
            except OperationFailure as e:
                # Code 20 is IllegalOperation (standalone or ephemeral storage engine)
                if e.code == 20: 
                    logger.warning(f"Note: MongoDB transactions not supported in this environment ({e.details.get('errmsg')}).")
                else:
                    raise
            
            # If we are here, transactions are NOT supported. 
            # We yield the session just as a normal session.
            yield session
            
        finally:
            await session.end_session()

    @staticmethod
    def to_bson(data: dict) -> dict:
        """Recursively convert Decimal to Decimal128 and string to ObjectId if needed."""
        if isinstance(data, dict):
            return {k: DatabaseManager.to_bson(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [DatabaseManager.to_bson(v) for v in data]
        elif isinstance(data, Decimal):
            return Decimal128(str(data))
        else:
            return data

    @staticmethod
    def from_bson(doc: dict) -> dict:
        """Recursively convert Decimal128 to Decimal and ObjectId to string."""
        if doc is None:
            return None
        if isinstance(doc, dict):
            return {k: DatabaseManager.from_bson(v) for k, v in doc.items()}
        elif isinstance(doc, list):
            return [DatabaseManager.from_bson(v) for v in doc]
        elif isinstance(doc, Decimal128):
            return str(doc.to_decimal())
        elif isinstance(doc, ObjectId):
            return str(doc)
        else:
            return doc

db_manager = DatabaseManager()

async def get_db() -> AsyncIOMotorDatabase:
    """FastAPI dependency to get the current database instance."""
    if db_manager.db is None:
        # Fallback for manual scripts or uninitialized state
        mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
        db_name = os.environ.get('DB_NAME', 'construction_management')
        db_manager.connect(mongo_url, db_name)
    return db_manager.db
