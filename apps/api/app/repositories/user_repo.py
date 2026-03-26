from typing import Optional, Dict, Any
from app.repositories.base_repo import BaseRepository
from app.schemas.user import User, UserProjectMap
from pymongo import ASCENDING

class UserRepository(BaseRepository[User]):
    def __init__(self, db):
        super().__init__(db, "users", User)

    async def ensure_indexes(self):
        await super().ensure_indexes()
        # Fixed CR-22: Added unique user email index and organisation scoping
        await self.collection.create_index([("email", ASCENDING)], unique=True)
        await self.collection.create_index([("organisation_id", ASCENDING)])

    async def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        doc = await self.collection.find_one({"email": email})
        from app.core.utils import serialize_doc
        return serialize_doc(doc) if doc else None

class UserProjectMapRepository(BaseRepository[UserProjectMap]):
    def __init__(self, db):
        super().__init__(db, "user_project_map", UserProjectMap)

    async def ensure_indexes(self):
        await super().ensure_indexes()
        await self.collection.create_index([("user_id", ASCENDING), ("project_id", ASCENDING)], unique=True)

    async def get_mapping(self, user_id: str, project_id: str) -> Optional[Dict[str, Any]]:
        from bson import ObjectId
        u_id = ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id
        p_id = ObjectId(project_id) if ObjectId.is_valid(project_id) else project_id
        return await self.find_one({"user_id": u_id, "project_id": p_id})
