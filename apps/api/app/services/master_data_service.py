from typing import List, Dict, Any
import logging
from app.repositories.financial_repo import CodeMasterRepository
from app.core.dependencies import PermissionChecker

logger = logging.getLogger(__name__)

class MasterDataService:
    def __init__(self, db):
        self.db = db
        self.code_repo = CodeMasterRepository(db)
        self.permission_checker = PermissionChecker(db)

    async def list_codes(self, user: dict) -> List[Dict[str, Any]]:
        """List all category codes (CodeMaster)."""
        await self.permission_checker.check_web_crm_access(user)
        return await self.code_repo.list({})

    async def get_code_by_id(self, user: dict, code_id: str) -> Dict[str, Any]:
        """Get details for a specific category code."""
        await self.permission_checker.check_web_crm_access(user)
        return await self.code_repo.get_by_id(code_id)

    async def list_units(self, user: dict) -> List[str]:
        """List standard units of measurement."""
        # Hardcoded for now or fetched from a settings repo
        return ["Rft", "Sft", "Cum", "No", "Lot", "Kg", "Mt", "Hr", "Day", "Month"]
