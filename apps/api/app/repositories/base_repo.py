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
    Sovereign Gatekeeper for Data Layer (Hardened v2).
    Addresses all 11 points from the Architectural Code Review.
    """
    MAX_LIMIT = 500
    ALLOWED_SORT_FIELDS = {"created_at", "updated_at", "id", "_id", "project_id"}

    def __init__(self, db: AsyncIOMotorDatabase, collection_name: str, model_class: type):
        self.db = db
        self.collection: AsyncIOMotorCollection = db[collection_name]
        self.model_class = model_class

    async def ensure_indexes(self):
        """Create necessary indexes for query performance (Point 6)."""
        await self.collection.create_index([("created_at", -1)])
        await self.collection.create_index([("updated_at", -1)])
        await self.collection.create_index([("is_deleted", 1)])

    def _generate_checksum(self, data: Dict[str, Any]) -> str:
        """
        Point 33/5: Data Hardening. 
        Includes 'version' in the hash to represent full logical state.
        Excludes ID and timestamps which are physical/temporal metadata.
        """
        clean = {
            k: str(v) for k, v in data.items() 
            if k not in ("_id", "checksum", "updated_at", "created_at", "deleted_at")
        }
        dump = json.dumps(clean, sort_keys=True)
        return hashlib.sha256(dump.encode()).hexdigest()

    def _clip_text(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Hard Guard: Prevent DB bloating with audit log warning (Point 4/46)."""
        limit = 4000
        clipped_fields = []
        for k, v in data.items():
            if isinstance(v, str) and len(v) > limit:
                clipped_fields.append(k)
                data[k] = v[:limit] + "... [CLIPPED]"
        
        if clipped_fields:
            logger.warning(f"TEXT_CLIPPED: {self.collection.name} fields {clipped_fields} truncated at 4k limit.")
        return data

    async def get_by_id(self, id: str, session: Optional[AsyncIOMotorClientSession] = None) -> Optional[Dict[str, Any]]:
        if not ObjectId.is_valid(id): return None
        doc = await self.collection.find_one({"_id": ObjectId(id)}, session=session)
        if not doc: return None
        
        # FAIL-FAST CHECKSUM VERIFICATION (Point 1)
        stored_checksum = doc.get("checksum")
        if stored_checksum:
            current_checksum = self._generate_checksum(doc)
            if stored_checksum != current_checksum:
                logger.critical(f"DATA_CORRUPTION: Record {id} in {self.collection.name} invalid.")
                raise DataIntegrityError(f"Checksum mismatch for {id}")
        
        return serialize_doc(doc)

    async def list(
        self, 
        query: Dict[str, Any] = None, 
        skip: int = 0, 
        limit: int = 20,
        sort: List[tuple] = None,
        session: Optional[AsyncIOMotorClientSession] = None,
        include_deleted: bool = False
    ) -> List[Dict[str, Any]]:
        """List with pagination validation and sort-injection protection (Point 7/8/10)."""
        if query is None: query = {}
        
        # VALIDATE PAGINATION (Point 7)
        if limit > self.MAX_LIMIT: raise ValueError(f"Limit exceeds max {self.MAX_LIMIT}")
        if skip < 0 or limit < 0: raise ValueError("Skip/Limit must be positive")

        # SOFT DELETE FILTER (Point 10)
        if not include_deleted:
            query.setdefault("is_deleted", {"$ne": True})

        # VALIDATE SORT (Point 8)
        if not sort:
            sort = [("created_at", -1)]
        else:
            for field, direction in sort:
                if field not in self.ALLOWED_SORT_FIELDS or direction not in (1, -1):
                    raise ValueError(f"Invalid or unauthorized sort field: {field}")

        cursor = self.collection.find(query, session=session).skip(skip).limit(limit).sort(sort)
        docs = await cursor.to_list(length=limit)
        return [serialize_doc(d) for d in docs]

    async def create(self, data: Dict[str, Any], session: Optional[AsyncIOMotorClientSession] = None) -> Dict[str, Any]:
        data = self._clip_text(data)
        data["created_at"] = now()
        data["updated_at"] = data["created_at"]
        data["version"] = 1
        data["is_deleted"] = False
        data["checksum"] = self._generate_checksum(data)
            
        result = await self.collection.insert_one(data, session=session)
        data["_id"] = result.inserted_id
        return serialize_doc(data)

    async def update(self, id: str, data: Dict[str, Any], session: Optional[AsyncIOMotorClientSession] = None) -> Optional[Dict[str, Any]]:
        """
        Hardened Update: Merged Checksum & Explicit Version Conflict (Point 2/3).
        """
        if not ObjectId.is_valid(id): return None
        data = self._clip_text(data)
        
        # 1. FETCH CURRENT STATE FOR COMPLETE HASH (Point 2)
        current = await self.collection.find_one({"_id": ObjectId(id)}, session=session)
        if not current: return None

        version = data.pop("version", None)
        
        # 2. MERGE DATA (Point 2)
        merged = {**current, **data}
        merged["updated_at"] = now()
        merged["checksum"] = self._generate_checksum(merged)

        query = {"_id": ObjectId(id)}
        if version: query["version"] = version # Optimistic Locking

        # 3. ATOMIC UPDATE
        doc = await self.collection.find_one_and_update(
            query, 
            {"$set": merged, "$inc": {"version": 1}}, 
            return_document=True, 
            session=session
        )

        # 4. EXPLICIT CONFLICT SIGNAL (Point 3)
        if doc is None and version:
            raise OptimisticLockConflict(f"Version mismatch for {id}. Expected {version}.")
            
        return serialize_doc(doc)

    async def soft_delete(self, id: str, session: Optional[AsyncIOMotorClientSession] = None) -> bool:
        """Mark as deleted without physical removal (Point 10)."""
        res = await self.update(id, {"is_deleted": True, "deleted_at": now()}, session=session)
        return res is not None

    async def find_one(self, query: Dict[str, Any], session: Optional[AsyncIOMotorClientSession] = None) -> Optional[Dict[str, Any]]:
        doc = await self.collection.find_one(query, session=session)
        return serialize_doc(doc) if doc else None
