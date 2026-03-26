from typing import Generic, TypeVar, List, Optional, Any, Dict
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection, AsyncIOMotorClientSession
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

    async def get_by_id(self, id: str, organisation_id: Optional[str] = None, session: Optional[AsyncIOMotorClientSession] = None) -> Optional[Dict[str, Any]]:
        query = {"_id": ObjectId(id)}
        if organisation_id:
            query["organisation_id"] = organisation_id
        
        doc = await self.collection.find_one(query, session=session)
        return serialize_doc(doc) if doc else None

    async def find_one(self, query: Dict[str, Any], session: Optional[AsyncIOMotorClientSession] = None) -> Optional[Dict[str, Any]]:
        doc = await self.collection.find_one(query, session=session)
        return serialize_doc(doc) if doc else None

    async def list(
        self, 
        query: Dict[str, Any] = None, 
        skip: int = 0, 
        limit: int = 100,
        sort: List[tuple] = None,
        session: Optional[AsyncIOMotorClientSession] = None
    ) -> List[Dict[str, Any]]:
        if query is None:
            query = {}
            
        cursor = self.collection.find(query, session=session).skip(skip).limit(limit)
        if sort:
            cursor = cursor.sort(sort)
            
        docs = await cursor.to_list(length=limit)
        return [serialize_doc(d) for d in docs]

    async def create(self, data: Dict[str, Any], session: Optional[AsyncIOMotorClientSession] = None) -> Dict[str, Any]:
        if "created_at" not in data:
            data["created_at"] = datetime.now(timezone.utc)
        if "updated_at" not in data:
            data["updated_at"] = datetime.now(timezone.utc)
            
        result = await self.collection.insert_one(data, session=session)
        doc = await self.collection.find_one({"_id": result.inserted_id}, session=session)
        return serialize_doc(doc)

    async def update(self, id: str, data: Dict[str, Any], organisation_id: Optional[str] = None, session: Optional[AsyncIOMotorClientSession] = None) -> Optional[Dict[str, Any]]:
        query = {"_id": ObjectId(id)}
        if organisation_id:
            query["organisation_id"] = organisation_id
            
        if "updated_at" not in data:
            data["updated_at"] = datetime.now(timezone.utc)
            
        doc = await self.collection.find_one_and_update(
            query,
            {"$set": data},
            return_document=True,
            session=session
        )
        return serialize_doc(doc) if doc else None

    async def update_one(self, query: Dict[str, Any], data: Dict[str, Any], session: Optional[AsyncIOMotorClientSession] = None) -> bool:
        if "updated_at" not in data.get("$set", {}):
            if "$set" not in data:
                data["$set"] = {}
            data["$set"]["updated_at"] = datetime.now(timezone.utc)
            
        result = await self.collection.update_one(query, data, session=session)
        return result.modified_count > 0

    async def delete(self, id: str, organisation_id: Optional[str] = None, session: Optional[AsyncIOMotorClientSession] = None) -> bool:
        query = {"_id": ObjectId(id)}
        if organisation_id:
            query["organisation_id"] = organisation_id
            
        result = await self.collection.delete_one(query, session=session)
        return result.deleted_count > 0

    async def count(self, query: Dict[str, Any] = None, session: Optional[AsyncIOMotorClientSession] = None) -> int:
        if query is None:
            query = {}
        return await self.collection.count_documents(query, session=session)

    async def count_documents(self, query: Dict[str, Any] = None, session: Optional[AsyncIOMotorClientSession] = None) -> int:
        return await self.count(query, session)

    async def update_many(self, query: Dict[str, Any], data: Dict[str, Any], session: Optional[AsyncIOMotorClientSession] = None) -> int:
        if "updated_at" not in data.get("$set", {}):
            if "$set" not in data:
                data["$set"] = {}
            data["$set"]["updated_at"] = datetime.now(timezone.utc)
            
        result = await self.collection.update_many(query, data, session=session)
        return result.modified_count

    async def aggregate(self, pipeline: List[Dict[str, Any]], session: Optional[AsyncIOMotorClientSession] = None) -> List[Dict[str, Any]]:
        cursor = self.collection.aggregate(pipeline, session=session)
        docs = await cursor.to_list(length=None)
        return [serialize_doc(d) for d in docs]

    async def find_one_and_update(self, query: Dict[str, Any], update: Dict[str, Any], session: Optional[AsyncIOMotorClientSession] = None) -> Optional[Dict[str, Any]]:
        doc = await self.collection.find_one_and_update(
            query,
            update,
            return_document=True,
            session=session
        )
        return serialize_doc(doc) if doc else None
