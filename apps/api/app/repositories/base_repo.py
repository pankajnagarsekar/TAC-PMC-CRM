from typing import Generic, TypeVar, List, Optional, Any, Dict
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
from pydantic import BaseModel
from bson import ObjectId
from datetime import datetime, timezone
import logging

from app.core.utils import serialize_doc

T = TypeVar("T", bound=BaseModel)

logger = logging.getLogger(__name__)

class BaseRepository(Generic[T]):
    def __init__(self, db: AsyncIOMotorDatabase, collection_name: str, model_class: type):
        self.db = db
        self.collection: AsyncIOMotorCollection = db[collection_name]
        self.model_class = model_class

    async def get_by_id(self, id: str, organisation_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        query = {"_id": ObjectId(id)}
        if organisation_id:
            query["organisation_id"] = organisation_id
        
        doc = await self.collection.find_one(query)
        return serialize_doc(doc) if doc else None

    async def list(
        self, 
        query: Dict[str, Any] = None, 
        skip: int = 0, 
        limit: int = 100,
        sort: List[tuple] = None
    ) -> List[Dict[str, Any]]:
        if query is None:
            query = {}
            
        cursor = self.collection.find(query).skip(skip).limit(limit)
        if sort:
            cursor = cursor.sort(sort)
            
        docs = await cursor.to_list(length=limit)
        return [serialize_doc(d) for d in docs]

    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if "created_at" not in data:
            data["created_at"] = datetime.now(timezone.utc)
        if "updated_at" not in data:
            data["updated_at"] = datetime.now(timezone.utc)
            
        result = await self.collection.insert_one(data)
        doc = await self.collection.find_one({"_id": result.inserted_id})
        return serialize_doc(doc)

    async def update(self, id: str, data: Dict[str, Any], organisation_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        query = {"_id": ObjectId(id)}
        if organisation_id:
            query["organisation_id"] = organisation_id
            
        if "updated_at" not in data:
            data["updated_at"] = datetime.now(timezone.utc)
            
        doc = await self.collection.find_one_and_update(
            query,
            {"$set": data},
            return_document=True
        )
        return serialize_doc(doc) if doc else None

    async def delete(self, id: str, organisation_id: Optional[str] = None) -> bool:
        query = {"_id": ObjectId(id)}
        if organisation_id:
            query["organisation_id"] = organisation_id
            
        result = await self.collection.delete_one(query)
        return result.deleted_count > 0

    async def count(self, query: Dict[str, Any] = None) -> int:
        if query is None:
            query = {}
        return await self.collection.count_documents(query)
