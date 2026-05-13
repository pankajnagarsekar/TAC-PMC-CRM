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
        self.session: Optional[AsyncIOMotorClientSession] = None

    async def ensure_indexes(self):
        """Authoritative index enforcement hook (Point 118)."""
        pass

    async def _pre_create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Lifecycle hook before document creation."""
        return data

    async def _post_create(self, doc: Dict[str, Any], session=None):
        """Lifecycle hook after document creation."""
        pass

    async def _pre_update(self, id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Lifecycle hook before document update."""
        return data

    async def _post_update(self, doc: Dict[str, Any], session=None):
        """Lifecycle hook after document update."""
        pass

    async def _pre_delete(self, id: str):
        """Lifecycle hook before document deletion."""
        pass

    async def _post_delete(self, id: str, session=None):
        """Lifecycle hook after document deletion."""
        pass

    async def get_by_id(
        self, id: str, session: Optional[AsyncIOMotorClientSession] = None, **filters
    ) -> Optional[Dict[str, Any]]:
        """Retrieve a single document by its hex ID or string ID with optional filtering."""
        effective_session = session or self.session
        try:
            query = {"_id": ObjectId(id)} if ObjectId.is_valid(id) else {"_id": id}
        except Exception:
            query = {"_id": id}

        # Enforce additional filters (e.g. organisation_id) for security (Point 115)
        if filters:
            query.update(filters)

        doc = await self.collection.find_one(query, session=effective_session)
        return self._format_id(doc)

    async def find_one(
        self,
        query: Dict[str, Any],
        session: Optional[AsyncIOMotorClientSession] = None,
        sort=None,
    ) -> Optional[Dict[str, Any]]:
        """Find the first matching document."""
        effective_session = session or self.session
        if sort:
            doc = await self.collection.find_one(query, session=effective_session, sort=sort)
        else:
            doc = await self.collection.find_one(query, session=effective_session)
        return self._format_id(doc)

    async def create(
        self, data: Dict[str, Any], session: Optional[AsyncIOMotorClientSession] = None
    ) -> Dict[str, Any]:
        """Atomic document insertion with timestamping (Point 75)."""
        effective_session = session or self.session
        from app.core.utils import prepare_for_db
        data = await self._pre_create(data)
        data = prepare_for_db(data)
        data["created_at"] = datetime.now(timezone.utc)
        data["updated_at"] = data["created_at"]

        result = await self.collection.insert_one(data, session=effective_session)
        data["_id"] = result.inserted_id
        formatted_doc = self._format_id(data)
        await self._post_create(formatted_doc, session=effective_session)
        return formatted_doc

    async def update(
        self,
        id: str,
        data: Dict[str, Any],
        expected_version: Optional[int] = None,
        session: Optional[AsyncIOMotorClientSession] = None,
        **filters,
    ) -> Optional[Dict[str, Any]]:
        """
        Update a document with Optimistic Concurrency Control (Point 75, Hardened).
        If expected_version is provided, the update will only succeed if the
        current version in DB matches.
        """
        effective_session = session or self.session
        from app.core.utils import prepare_for_db
        data = await self._pre_update(id, data)
        data = prepare_for_db(data)
        data["updated_at"] = datetime.now(timezone.utc)

        try:
            query = {"_id": ObjectId(id)} if ObjectId.is_valid(id) else {"_id": id}
        except Exception:
            query = {"_id": id}

        if expected_version is not None:
            query["version"] = expected_version

        if filters:
            query.update(filters)

        result = await self.collection.find_one_and_update(
            query, {"$set": data}, return_document=True, session=effective_session
        )
        formatted_doc = self._format_id(result)
        if formatted_doc:
            await self._post_update(formatted_doc, session=effective_session)
        return formatted_doc

    async def list(
        self,
        query: Dict[str, Any],
        limit: int = 100,
        skip: int = 0,
        sort: List = None,
        session: Optional[AsyncIOMotorClientSession] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve multiple documents with optional sorting and pagination."""
        effective_session = session or self.session
        cursor = self.collection.find(query, session=effective_session).skip(skip).limit(limit)
        if sort:
            cursor = cursor.sort(sort)
        docs = await cursor.to_list(length=limit)
        return [self._format_id(doc) for doc in docs]

    def aggregate(
        self,
        pipeline: List[Dict[str, Any]],
        session: Optional[AsyncIOMotorClientSession] = None,
    ):
        """Authoritative aggregation hook (Point 118)."""
        effective_session = session or self.session
        return self.collection.aggregate(pipeline, session=effective_session)

    async def distinct(
        self,
        key: str,
        filter: Dict[str, Any] = None,
        session: Optional[AsyncIOMotorClientSession] = None,
    ) -> List[Any]:
        """Authoritative distinct hook."""
        effective_session = session or self.session
        return await self.collection.distinct(key, filter, session=effective_session)

    async def count(
        self, query: Dict[str, Any], session: Optional[AsyncIOMotorClientSession] = None
    ) -> int:
        """Atomic document counting."""
        effective_session = session or self.session
        return await self.collection.count_documents(query, session=effective_session)

    async def update_one(
        self,
        query: Dict[str, Any],
        update: Dict[str, Any],
        upsert: bool = False,
        session: Optional[AsyncIOMotorClientSession] = None,
    ):
        """Atomic single document update with automatic ID conversion (Point 75)."""
        effective_session = session or self.session
        if "_id" in query and isinstance(query["_id"], str) and ObjectId.is_valid(query["_id"]):
            query["_id"] = ObjectId(query["_id"])

        from app.core.utils import prepare_for_db
        update = prepare_for_db(update)
        # ENSURE updated_at is always set (Fixes BUG-35 for $inc/other operators)
        if "$set" not in update:
            update["$set"] = {}
        update["$set"]["updated_at"] = datetime.now(timezone.utc)

        return await self.collection.update_one(
            query, update, upsert=upsert, session=effective_session
        )

    async def delete(
        self, id: str, session: Optional[AsyncIOMotorClientSession] = None
    ) -> bool:
        """Physical deletion (Use with caution - Point 87)."""
        effective_session = session or self.session
        try:
            query = {"_id": ObjectId(id)} if ObjectId.is_valid(id) else {"_id": id}
        except Exception:
            query = {"_id": id}

        result = await self.collection.delete_one(query, session=effective_session)
        return result.deleted_count > 0

    async def delete_many(
        self, query: Dict[str, Any], session: Optional[AsyncIOMotorClientSession] = None
    ) -> int:
        """Atomic batch deletion (Point 87)."""
        effective_session = session or self.session
        result = await self.collection.delete_many(query, session=effective_session)
        return result.deleted_count

    def _format_id(self, doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Move _id to id string for JSON parity and recursively serialize.
        Fixed CR-19/75: Uses authoritative serialize_doc for consistency.
        RE-FIX: Preserves _id for frontend compatibility (Point 226).
        """
        if not doc:
            return None

        from app.core.utils import serialize_doc

        # 1. Authoritative serialization (ObjectId -> str, datetime -> isoformat)
        serialized = serialize_doc(doc)

        # 2. Add 'id' and preserve '_id' for frontend parity
        if "_id" in serialized:
            oid = serialized["_id"]
            serialized["id"] = oid
            # We keep _id as well because the React frontend uses it extensively
        elif "id" in serialized:
            # If it already has 'id' but no '_id', provide both
            serialized["_id"] = serialized["id"]

        return serialized
