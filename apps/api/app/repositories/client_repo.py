from app.repositories.base_repo import BaseRepository
from app.schemas.client import Client

class ClientRepository(BaseRepository[Client]):
    def __init__(self, db):
        super().__init__(db, "clients", Client)
