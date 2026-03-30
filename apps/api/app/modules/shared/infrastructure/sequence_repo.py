from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClientSession
from pydantic import BaseModel

from app.modules.shared.infrastructure.base_repository import BaseRepository


class SequenceModel(BaseModel):
    id: str
    seq: int


class SequenceRepository(BaseRepository[SequenceModel]):
    def __init__(self, db):
        super().__init__(db, "sequences", SequenceModel)

    async def get_next_sequence(
        self, name: str, session: Optional[AsyncIOMotorClientSession] = None
    ) -> int:
        doc = await self.collection.find_one_and_update(
            {"_id": name},
            {"$inc": {"seq": 1}},
            upsert=True,
            return_document=True,
            session=session,
        )
        return doc["seq"]
