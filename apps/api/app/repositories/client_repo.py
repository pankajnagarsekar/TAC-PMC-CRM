from pymongo import ASCENDING
from app.repositories.base_repo import BaseRepository
from app.schemas.client import Client

class ClientRepository(BaseRepository[Client]):
    def __init__(self, db):
        super().__init__(db, "clients", Client)

    async def ensure_indexes(self):
        await super().ensure_indexes()
        await self.collection.create_index([("organisation_id", ASCENDING)])
        await self.collection.create_index([("client_id", ASCENDING)], unique=True)
