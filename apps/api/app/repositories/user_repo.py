from typing import Optional, Dict, Any
from app.repositories.base_repo import BaseRepository
from app.schemas.user import User, UserProjectMap

class UserRepository(BaseRepository[User]):
    def __init__(self, db):
        super().__init__(db, "users", User)

    async def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        doc = await self.collection.find_one({"email": email})
        from app.core.utils import serialize_doc
        return serialize_doc(doc) if doc else None

class UserProjectMapRepository(BaseRepository[UserProjectMap]):
    def __init__(self, db):
        super().__init__(db, "user_project_map", UserProjectMap)

    async def get_mapping(self, user_id: str, project_id: str) -> Optional[Dict[str, Any]]:
        from bson import ObjectId
        u_id = ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id
        p_id = ObjectId(project_id) if ObjectId.is_valid(project_id) else project_id
        return await self.find_one({"user_id": u_id, "project_id": p_id})
