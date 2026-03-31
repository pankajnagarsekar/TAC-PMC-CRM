from datetime import datetime, timezone
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClientSession, AsyncIOMotorDatabase
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class BaseRepository(Generic[T]):
    """
    Sovereign Base Repository (Point 75, 115).
    Abstracts MongoDB operations with automatic audit hooks and type safety.
    """

    def __init__(
        self, db: AsyncIOMotorDatabase, collection_name: str, model_class: Type[T]
    ):
        self.db = db
        self.collection = db[collection_name]
        self.model_class = model_class

    async def ensure_indexes(self):
        """Authoritative index enforcement hook (Point 118)."""
        pass

    async def get_by_id(
        self, id: str, session: Optional[AsyncIOMotorClientSession] = None, **filters
    ) -> Optional[Dict[str, Any]]:
        """Retrieve a single document by its hex ID or string ID with optional filtering."""
        try:
            query = {"_id": ObjectId(id)} if ObjectId.is_valid(id) else {"_id": id}
        except Exception:
            query = {"_id": id}

        # Enforce additional filters (e.g. organisation_id) for security (Point 115)
        if filters:
            query.update(filters)

        doc = await self.collection.find_one(query, session=session)
        return self._format_id(doc)

    async def find_one(
        self,
        query: Dict[str, Any],
        session: Optional[AsyncIOMotorClientSession] = None,
        sort=None,
    ) -> Optional[Dict[str, Any]]:
        """Find the first matching document."""
        if sort:
            doc = await self.collection.find_one(query, session=session, sort=sort)
        else:
            doc = await self.collection.find_one(query, session=session)
        return self._format_id(doc)

    async def create(
        self, data: Dict[str, Any], session: Optional[AsyncIOMotorClientSession] = None
    ) -> Dict[str, Any]:
        """Atomic document insertion with timestamping (Point 75)."""
        data["created_at"] = datetime.now(timezone.utc)
        data["updated_at"] = data["created_at"]

        result = await self.collection.insert_one(data, session=session)
        data["id"] = str(result.inserted_id)
        return data

    async def update(
        self,
        id: str,
        data: Dict[str, Any],
        session: Optional[AsyncIOMotorClientSession] = None,
    ) -> Optional[Dict[str, Any]]:
        """Update a document and return the new version."""
        data["updated_at"] = datetime.now(timezone.utc)

        try:
            query = {"_id": ObjectId(id)} if ObjectId.is_valid(id) else {"_id": id}
        except Exception:
            query = {"_id": id}

        result = await self.collection.find_one_and_update(
            query, {"$set": data}, return_document=True, session=session
        )
        return self._format_id(result)

    async def list(
        self,
        query: Dict[str, Any],
        limit: int = 100,
        sort: List = None,
        session: Optional[AsyncIOMotorClientSession] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve multiple documents with optional sorting."""
        cursor = self.collection.find(query, session=session).limit(limit)
        if sort:
            cursor = cursor.sort(sort)
        docs = await cursor.to_list(length=limit)
        return [self._format_id(doc) for doc in docs]

    async def aggregate(
        self, pipeline: List[Dict[str, Any]], session: Optional[AsyncIOMotorClientSession] = None
    ):
        """Authoritative aggregation hook (Point 118)."""
        return self.collection.aggregate(pipeline, session=session)

    async def count(
        self, query: Dict[str, Any], session: Optional[AsyncIOMotorClientSession] = None
    ) -> int:
        """Atomic document counting."""
        return await self.collection.count_documents(query, session=session)

    async def update_one(
        self,
        query: Dict[str, Any],
        update: Dict[str, Any],
        upsert: bool = False,
        session: Optional[AsyncIOMotorClientSession] = None,
    ):
        """Atomic single document update."""
        return await self.collection.update_one(
            query, update, upsert=upsert, session=session
        )

    async def delete(
        self, id: str, session: Optional[AsyncIOMotorClientSession] = None
    ) -> bool:
        """Physical deletion (Use with caution - Point 87)."""
        try:
            query = {"_id": ObjectId(id)} if ObjectId.is_valid(id) else {"_id": id}
        except Exception:
            query = {"_id": id}

        result = await self.collection.delete_one(query, session=session)
        return result.deleted_count > 0

    def _format_id(self, doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Move _id to id string for JSON parity and recursively serialize.
        Fixed CR-19/75: Uses authoritative serialize_doc for consistency.
        """
        if not doc:
            return None

        from app.core.utils import serialize_doc

        # 1. Authoritative serialization (ObjectId -> str, datetime -> isoformat)
        serialized = serialize_doc(doc)

        # 2. Map _id to id for API parity
        if "_id" in serialized:
            serialized["id"] = serialized.pop("_id")

        return serialized
