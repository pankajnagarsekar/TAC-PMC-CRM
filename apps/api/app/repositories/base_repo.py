from typing import Generic, TypeVar, List, Optional, Any, Dict
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection, AsyncIOMotorClientSession
from pydantic import BaseModel
from bson import ObjectId
import logging

from app.core.utils import serialize_doc
from app.core.time import now

T = TypeVar("T", bound=BaseModel)
logger = logging.getLogger(__name__)

class BaseRepository(Generic[T]):
    """
    Sovereign Gatekeeper for Data Layer (Point 14, 41, 43, 46, 52).
    Enforces Text Clipping, Deterministic Sorting, and Optimistic Locking.
    """
    def __init__(self, db: AsyncIOMotorDatabase, collection_name: str, model_class: type):
        self.db = db
        self.collection: AsyncIOMotorCollection = db[collection_name]
        self.model_class = model_class

    def _clip_text(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Hard Guard: Prevent DB bloating from OCR/AI noise (Point 46)."""
        limit = 4000
        for k, v in data.items():
            if isinstance(v, str) and len(v) > limit:
                data[k] = v[:limit] + "... [CLIPPED]"
        return data

    async def get_by_id(self, id: str, session: Optional[AsyncIOMotorClientSession] = None) -> Optional[Dict[str, Any]]:
        if not ObjectId.is_valid(id): return None
        doc = await self.collection.find_one({"_id": ObjectId(id)}, session=session)
        return serialize_doc(doc) if doc else None

    async def list(
        self, 
        query: Dict[str, Any] = None, 
        skip: int = 0, 
        limit: int = 100,
        sort: List[tuple] = None,
        session: Optional[AsyncIOMotorClientSession] = None
    ) -> List[Dict[str, Any]]:
        if query is None: query = {}
        
        # DETERMINISTIC ORDER (Point 42)
        if not sort:
            sort = [("created_at", -1)]
            
        cursor = self.collection.find(query, session=session).skip(skip).limit(limit).sort(sort)
        docs = await cursor.to_list(length=limit)
        return [serialize_doc(d) for d in docs]

    async def create(self, data: Dict[str, Any], session: Optional[AsyncIOMotorClientSession] = None) -> Dict[str, Any]:
        """Sovereign Insert: Force Timestamps, Clipping, and Logic Version."""
        data = self._clip_text(data)
        
        data["created_at"] = now()
        data["updated_at"] = data["created_at"]
        data["version"] = 1 # Init Optimistic Locking (Point 43)
            
        result = await self.collection.insert_one(data, session=session)
        data["_id"] = result.inserted_id
        return serialize_doc(data)

    async def update(self, id: str, data: Dict[str, Any], session: Optional[AsyncIOMotorClientSession] = None) -> Optional[Dict[str, Any]]:
        """
        Sovereign Update: Optimistic locking (Point 43).
        Matches by ID AND version to prevent race conditions.
        """
        if not ObjectId.is_valid(id): return None
        data = self._clip_text(data)
        
        # Versioning logic
        version = data.pop("version", None)
        query = {"_id": ObjectId(id)}
        if version:
            query["version"] = version # Hard match version

        data["updated_at"] = now()
        
        doc = await self.collection.find_one_and_update(
            query,
            {"$set": data, "$inc": {"version": 1}},
            return_document=True,
            session=session
        )
        
        if not doc and version:
            logger.error(f"OPTIMISTIC_LOCK_FAILURE: Entity {id} modified by another process.")
            # We could raise a specific exception here for the service to handle
            
        return serialize_doc(doc) if doc else None

    async def find_one(self, query: Dict[str, Any], session: Optional[AsyncIOMotorClientSession] = None) -> Optional[Dict[str, Any]]:
        doc = await self.collection.find_one(query, session=session)
        return serialize_doc(doc) if doc else None
