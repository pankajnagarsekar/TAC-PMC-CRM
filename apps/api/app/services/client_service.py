from typing import List, Dict, Any
from datetime import datetime, timezone
from bson import ObjectId
from fastapi import HTTPException

from app.schemas.client import ClientCreate, ClientUpdate
from app.core.utils import serialize_doc

class ClientService:
    def __init__(self, db, audit_service):
        self.db = db
        self.audit_service = audit_service

    async def list_clients(self, organisation_id: str, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        clients = await self.db.clients.find({"organisation_id": organisation_id}).skip(skip).limit(limit).to_list(length=limit)
        return [serialize_doc(c) for c in clients]

    async def create_client(self, user: dict, client_data: ClientCreate) -> Dict[str, Any]:
        client_dict = client_data.dict()
        client_dict["organisation_id"] = user["organisation_id"]
        client_dict["created_at"] = datetime.now(timezone.utc)
        client_dict["updated_at"] = datetime.now(timezone.utc)
        client_dict["active_status"] = True

        result = await self.db.clients.insert_one(client_dict)
        client_id = str(result.inserted_id)

        # Audit log
        await self.audit_service.log_action(
            organisation_id=user["organisation_id"],
            module_name="CLIENT_MANAGEMENT",
            entity_type="CLIENT",
            entity_id=client_id,
            action_type="CREATE",
            user_id=user["user_id"],
            new_value={"client_name": client_data.name}
        )
        client_dict["_id"] = result.inserted_id
        return serialize_doc(client_dict)

    async def get_client(self, client_id: str, organisation_id: str) -> Dict[str, Any]:
        client = await self.db.clients.find_one({"_id": ObjectId(client_id), "organisation_id": organisation_id})
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        return serialize_doc(client)

    async def update_client(self, user: dict, client_id: str, client_data: ClientUpdate) -> Dict[str, Any]:
        update_data = {k: v for k, v in client_data.dict().items() if v is not None}
        update_data["updated_at"] = datetime.now(timezone.utc)

        result = await self.db.clients.find_one_and_update(
            {"_id": ObjectId(client_id), "organisation_id": user["organisation_id"]},
            {"$set": update_data},
            return_document=True
        )
        if not result:
            raise HTTPException(status_code=404, detail="Client not found")

        # Audit log
        await self.audit_service.log_action(
            organisation_id=user["organisation_id"],
            module_name="CLIENT_MANAGEMENT",
            entity_type="CLIENT",
            entity_id=client_id,
            action_type="UPDATE",
            user_id=user["user_id"],
            new_value=update_data
        )
        return serialize_doc(result)

    async def delete_client(self, user: dict, client_id: str) -> Dict[str, Any]:
        project_count = await self.db.projects.count_documents({"client_id": client_id, "organisation_id": user["organisation_id"]})
        if project_count > 0:
            raise HTTPException(status_code=400, detail="Cannot delete client with associated projects")

        result = await self.db.clients.find_one_and_update(
            {"_id": ObjectId(client_id), "organisation_id": user["organisation_id"]},
            {"$set": {"active_status": False, "updated_at": datetime.now(timezone.utc)}},
            return_document=True
        )
        if not result:
            raise HTTPException(status_code=404, detail="Client not found")

        # Audit log
        await self.audit_service.log_action(
            organisation_id=user["organisation_id"],
            module_name="CLIENT_MANAGEMENT",
            entity_type="CLIENT",
            entity_id=client_id,
            action_type="DELETE",
            user_id=user["user_id"]
        )
        return {"message": "Client deleted successfully"}
