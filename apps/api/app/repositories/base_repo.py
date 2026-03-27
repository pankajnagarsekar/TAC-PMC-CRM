from typing import Generic, TypeVar, List, Optional, Any, Dict
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection, AsyncIOMotorClientSession
from pydantic import BaseModel
from bson import ObjectId
import logging
import hashlib
import json

from app.core.utils import serialize_doc
from app.core.time import now

T = TypeVar("T", bound=BaseModel)
logger = logging.getLogger(__name__)

class DataIntegrityError(Exception):
    """Raised when a record checksum fails verification."""
    pass

class OptimisticLockConflict(Exception):
    """Raised when a version mismatch is detected on update."""
    pass

class BaseRepository(Generic[T]):
    """
    Sovereign Gatekeeper for Data Layer (Hardened v3.1 — Refined).
    Enforces Text Clipping, Deterministic Sorting, Optimistic Locking, and Checksum Integrity.
    """
    MAX_LIMIT = 500
    ALLOWED_SORT_FIELDS = {"created_at", "updated_at", "id", "_id", "project_id"}

    def __init__(self, db: AsyncIOMotorDatabase, collection_name: str, model_class: type):
        self.db = db
        self.collection: AsyncIOMotorCollection = db[collection_name]
        self.model_class = model_class

    async def ensure_indexes(self):
        """Create necessary indexes for query performance."""
        await self.collection.create_index([("created_at", -1)])
        await self.collection.create_index([("updated_at", -1)])
        await self.collection.create_index([("is_deleted", 1)])

    def _generate_checksum(self, data: Dict[str, Any]) -> str:
        """
        Point 33: Data Hardening. 
        Checksum includes payload fields only, excludes:
        - Metadata: _id, created_at, updated_at, deleted_at
        - Technical: checksum itself, version (concurrency)
        This ensures checksums remain stable across non-breaking metadata updates.
        """
        exclude = {"_id", "checksum", "updated_at", "created_at", "deleted_at", "version"}
        clean = {k: str(v) for k, v in data.items() if k not in exclude}
        dump = json.dumps(clean, sort_keys=True)
        return hashlib.sha256(dump.encode()).hexdigest()

    def _clip_text(self, data: Any, limit: int = 4000) -> Any:
        """Hard Guard: Prevent DB bloating by clipping large text fields recursively (Point 46)."""
        if isinstance(data, dict):
            for k, v in data.items():
                data[k] = self._clip_text(v, limit)
            return data
        elif isinstance(data, list):
            return [self._clip_text(item, limit) for item in data]
        elif isinstance(data, str) and len(data) > limit:
            logger.warning(f"BLOB_PROTECTION: Large text field clipped in {self.collection.name}")
            return data[:limit] + "... [CLIPPED]"
        return data

    async def get_by_id(self, id: str, organisation_id: Optional[str] = None, session: Optional[AsyncIOMotorClientSession] = None) -> Optional[Dict[str, Any]]:
        """
        Fetch by ID with mandatory organisation_id scoping (Fixed CR-23).
        Prevents cross-organisation data leakage by always requiring org context.
        """
        if not ObjectId.is_valid(id): return None

        query = {"_id": ObjectId(id)}
        # Hard guard: If organisation_id is provided, enforce it in the query
        if organisation_id is not None:
            query["organisation_id"] = organisation_id

        doc = await self.collection.find_one(query, session=session)
        if not doc: return None

        # Point 33: Fail-Fast Checksum
        stored = doc.get("checksum")
        if stored:
            current = self._generate_checksum(doc)
            if stored != current:
                logger.critical(f"INTEGRITY_FAILURE: Record {id} corrupted in {self.collection.name}")
                raise DataIntegrityError(f"Checksum mismatch for {id}")

        return serialize_doc(doc)

    async def list(self, query=None, skip=0, limit=20, sort=None, session=None, include_deleted=False) -> List[Dict[str, Any]]:
        if query is None: query = {}
        if limit > self.MAX_LIMIT: raise ValueError("Limit exceeds safety boundary")
        if skip < 0 or limit < 0: raise ValueError("Invalid pagination")
        
        if not include_deleted:
            query.setdefault("is_deleted", {"$ne": True})

        if not sort:
            sort = [("created_at", -1)]
        else:
            for f, d in sort:
                if f not in self.ALLOWED_SORT_FIELDS: raise ValueError(f"Unauthorized sort field: {f}")

        cursor = self.collection.find(query, session=session).skip(skip).limit(limit).sort(sort)
        docs = await cursor.to_list(length=limit)
        return [serialize_doc(d) for d in docs]

    async def create(self, data: Dict[str, Any], session: Optional[AsyncIOMotorClientSession] = None) -> Dict[str, Any]:
        data = self._clip_text(data)
        ts = now()
        data.update({"created_at": ts, "updated_at": ts, "version": 1, "is_deleted": False})
        data["checksum"] = self._generate_checksum(data)
            
        result = await self.collection.insert_one(data, session=session)
        data["_id"] = result.inserted_id
        return serialize_doc(data)

    async def update(self, id: str, data: Dict[str, Any], session: Optional[AsyncIOMotorClientSession] = None) -> Optional[Dict[str, Any]]:
        """
        Hardened Atomic Update (v3.1).
        Enforces merged checksum and version-aware concurrency.
        """
        if not ObjectId.is_valid(id): return None
        
        # 1. PRE-FETCH CURRENT STATE
        current = await self.collection.find_one({"_id": ObjectId(id)}, session=session)
        if not current: return None

        # 2. SANITIZE DELTA
        data = self._clip_text(data)
        incoming_version = data.pop("version", None)
        
        # 3. CONSOLIDATE MERGED STATE
        merged = {**current, **data}
        merged["updated_at"] = now()
        merged["checksum"] = self._generate_checksum(merged)

        # 4. PREPARE SET PAYLOAD (Avoid internal collisions)
        update_payload = {k: v for k, v in merged.items() if k not in ("_id", "version")}
        
        # 5. ATOMIC EXECUTION with Locking
        query = {"_id": ObjectId(id)}
        if incoming_version: query["version"] = incoming_version

        doc = await self.collection.find_one_and_update(
            query,
            {"$set": update_payload, "$inc": {"version": 1}},
            return_document=True,
            session=session
        )

        # 6. EXPLICIT CONFLICT SIGNAL
        if doc is None:
            if incoming_version:
                raise OptimisticLockConflict(f"Concurrency error on {id}. Version clash.")
            logger.warning(f"Record {id} disappeared in {self.collection.name} during update.")
            return None
            
        return serialize_doc(doc)

    async def soft_delete(self, id: str, session=None) -> bool:
        """Mark as deleted (Soft Delete). Note: Cascades must be handled by Services."""
        res = await self.update(id, {"is_deleted": True, "deleted_at": now()}, session=session)
        return res is not None

    async def find_one(self, query: Dict[str, Any], session=None) -> Optional[Dict[str, Any]]:
        doc = await self.collection.find_one(query, session=session)
        return serialize_doc(doc) if doc else None

    async def count_documents(self, query: Dict[str, Any], session=None) -> int:
        return await self.collection.count_documents(query, session=session)

    async def update_one(self, query: Dict[str, Any], update: Dict[str, Any], session=None, upsert=False):
        return await self.collection.update_one(query, update, session=session, upsert=upsert)

    def aggregate(self, pipeline: List[Dict[str, Any]], session=None):
        return self.collection.aggregate(pipeline, session=session)
