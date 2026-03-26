from typing import Optional, Dict, Any
from app.repositories.base_repo import BaseRepository
from app.schemas.user import User

class UserRepository(BaseRepository[User]):
    def __init__(self, db):
        super().__init__(db, "users", User)

    async def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        doc = await self.collection.find_one({"email": email})
        from app.core.utils import serialize_doc
        return serialize_doc(doc) if doc else None
