from typing import List, Dict, Any
from fastapi import HTTPException
import logging

from ..infrastructure.repository import ClientRepository, ProjectRepository
from ..schemas.dto import Client, ClientCreate, ClientUpdate

logger = logging.getLogger(__name__)

class ClientService:
    def __init__(self, db, audit_service):
        self.db = db
        self.audit_service = audit_service
        self.client_repo = ClientRepository(db)
        self.project_repo = ProjectRepository(db)

    async def list_clients(self, organisation_id: str, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        return await self.client_repo.list({"organisation_id": organisation_id}, skip=skip, limit=limit)

    async def create_client(self, user: dict, client_data: ClientCreate) -> Dict[str, Any]:
        client_dict = client_data.dict()
        client_dict["organisation_id"] = user["organisation_id"]
        client_dict["active_status"] = True

        new_client = await self.client_repo.create(client_dict)

        await self.audit_service.log_action(
            organisation_id=user["organisation_id"],
            module_name="CLIENT_MANAGEMENT",
            entity_type="CLIENT",
            entity_id=new_client["id"],
            action_type="CREATE",
            user_id=user["user_id"],
            new_value=new_client
        )
        return new_client

    async def get_client(self, client_id: str, organisation_id: str) -> Dict[str, Any]:
        client = await self.client_repo.get_by_id(client_id, organisation_id=organisation_id)
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        return client

    async def update_client(self, user: dict, client_id: str, client_data: ClientUpdate) -> Dict[str, Any]:
        existing = await self.get_client(client_id, user["organisation_id"])
        
        update_data = client_data.dict(exclude_unset=True)
        
        result = await self.client_repo.update(client_id, update_data, organisation_id=user["organisation_id"])
        if not result:
            raise HTTPException(status_code=404, detail="Client not found")

        await self.audit_service.log_action(
            organisation_id=user["organisation_id"],
            module_name="CLIENT_MANAGEMENT",
            entity_type="CLIENT",
            entity_id=client_id,
            action_type="UPDATE",
            user_id=user["user_id"],
            old_value=existing,
            new_value=result
        )
        return result

    async def delete_client(self, user: dict, client_id: str) -> Dict[str, Any]:
        existing = await self.get_client(client_id, user["organisation_id"])
        
        projects = await self.project_repo.list({"client_id": client_id, "organisation_id": user["organisation_id"]}, limit=1)
        if projects:
            raise HTTPException(status_code=400, detail="Cannot delete client with associated projects")

        result = await self.client_repo.update(client_id, {"active_status": False}, organisation_id=user["organisation_id"])
        if not result:
            raise HTTPException(status_code=404, detail="Client not found")

        await self.audit_service.log_action(
            organisation_id=user["organisation_id"],
            module_name="CLIENT_MANAGEMENT",
            entity_type="CLIENT",
            entity_id=client_id,
            action_type="DELETE",
            user_id=user["user_id"],
            old_value=existing,
            new_value=result
        )
        return {"message": "Client deleted successfully"}
