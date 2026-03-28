from typing import Optional, Dict, Any
from app.modules.shared.infrastructure.base_repository import BaseRepository
from ..schemas.dto import User, UserProjectMap
from pydantic import BaseModel
from datetime import datetime
from pymongo import ASCENDING

# Token management models (internal to infra/auth)
class TokenBlacklist(BaseModel):
    jti: str
    token_type: str
    revoked_at: datetime

class RefreshToken(BaseModel):
    user_id: str
    jti: str
    is_revoked: bool
    revoked_at: datetime

class UserRepository(BaseRepository[User]):
    def __init__(self, db):
        super().__init__(db, "users", User)

    async def ensure_indexes(self):
        await super().ensure_indexes()
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

class TokenBlacklistRepository(BaseRepository[TokenBlacklist]):
    def __init__(self, db):
        super().__init__(db, "token_blacklist", TokenBlacklist)

class RefreshTokenRepository(BaseRepository[RefreshToken]):
    def __init__(self, db):
        super().__init__(db, "refresh_tokens", RefreshToken)

class SettingsRepository(BaseRepository[Any]):
    def __init__(self, db):
        super().__init__(db, "organisation_settings", Any)

    async def ensure_indexes(self):
        await super().ensure_indexes()
        await self.collection.create_index([("organisation_id", ASCENDING)], unique=True)
