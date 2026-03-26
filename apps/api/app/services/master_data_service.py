from typing import List, Dict, Any, Optional
from fastapi import HTTPException
import logging
from app.repositories.financial_repo import CodeMasterRepository
from app.core.permissions import PermissionChecker
from app.schemas.financial import CodeMasterCreate, CodeMasterUpdate

logger = logging.getLogger(__name__)

class MasterDataService:
    """
    Sovereign Controller for Master Data (Point 1).
    Enforces organizational scoping and uniqueness for reference codes.
    """
    def __init__(self, db):
        self.db = db
        self.code_repo = CodeMasterRepository(db)
        self.permission_checker = PermissionChecker(db)

    async def list_codes(self, user: dict, category_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """List category codes scoped to organisation."""
        query = {"organisation_id": user["organisation_id"]}
        if category_name:
            query["category_name"] = category_name
        return await self.code_repo.list(query)

    async def create_code(self, user: dict, code_data: CodeMasterCreate) -> Dict[str, Any]:
        """Fixed CR-28: Implemented authoritative master data creation with uniqueness guard."""
        await self.permission_checker.check_admin_role(user)
        
        # Uniqueness Guard: (Organisation, CodeShort)
        existing = await self.code_repo.find_one({
            "organisation_id": user["organisation_id"],
            "code_short": code_data.code_short
        })
        if existing:
            raise HTTPException(status_code=400, detail="CODE_EXISTS: A master code with this short name already exists.")

        doc = code_data.dict()
        doc["organisation_id"] = user["organisation_id"]
        doc["active_status"] = True
        
        return await self.code_repo.create(doc)

    async def update_code(self, user: dict, code_id: str, update_data: CodeMasterUpdate) -> Dict[str, Any]:
        """Fixed CR-28: Master data update with scoping."""
        await self.permission_checker.check_admin_role(user)
        
        existing = await self.code_repo.get_by_id(code_id)
        if not existing or existing.get("organisation_id") != user["organisation_id"]:
            raise HTTPException(status_code=404, detail="Master code not found.")

        updated = await self.code_repo.update(code_id, update_data.dict(exclude_unset=True))
        return updated

    async def get_code_by_id(self, user: dict, code_id: str) -> Dict[str, Any]:
        """Get details for a specific category code with scoping."""
        code = await self.code_repo.get_by_id(code_id)
        if not code or code.get("organisation_id") != user["organisation_id"]:
            raise HTTPException(status_code=404, detail="Master code not found.")
        return code

    async def list_units(self, user: dict) -> List[str]:
        """List standard units of measurement."""
        return ["Rft", "Sft", "Cum", "No", "Lot", "Kg", "Mt", "Hr", "Day", "Month"]
