import logging
from typing import Any, Dict, List, Optional

from app.modules.shared.domain.exceptions import NotFoundError, ValidationError

from ..infrastructure.repository import CodeMasterRepository

logger = logging.getLogger(__name__)


class MasterDataService:
    """
    Sovereign Controller for Master Data.
    Enforces organizational scoping and uniqueness for reference codes.
    """

    def __init__(self, db, audit_service, permission_checker):
        self.db = db
        self.audit_service = audit_service
        self.code_repo = CodeMasterRepository(db)
        self.permission_checker = permission_checker

    async def list_codes(
        self, user: dict, category_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List category codes scoped to organisation."""
        query = {"organisation_id": user["organisation_id"]}
        if category_name:
            query["category_name"] = category_name
        return await self.code_repo.list(query)

    async def create_code(self, user: dict, code_data: Any) -> Dict[str, Any]:
        """Implemented authoritative master data creation with uniqueness guard."""
        await self.permission_checker.check_admin_role(user)

        # Uniqueness Guard: (Organisation, Code)
        existing = await self.code_repo.find_one(
            {
                "organisation_id": user["organisation_id"],
                "code": code_data.code,
            }
        )
        if existing:
            raise ValidationError(
                "CODE_EXISTS: A master code with this name already exists."
            )

        doc = code_data.dict()
        doc["organisation_id"] = user["organisation_id"]
        doc["active_status"] = True

        new_code = await self.code_repo.create(doc)

        await self.audit_service.log_action(
            organisation_id=user["organisation_id"],
            module_name="MASTER_DATA",
            entity_type="CODE_MASTER",
            entity_id=new_code["id"],
            action_type="CREATE",
            user_id=user["user_id"],
            new_value=new_code,
        )
        return new_code

    async def update_code(
        self, user: dict, code_id: str, update_data: Any
    ) -> Dict[str, Any]:
        """Master data update with scoping."""
        await self.permission_checker.check_admin_role(user)

        existing = await self.code_repo.get_by_id(code_id)
        if not existing or existing.get("organisation_id") != user["organisation_id"]:
            raise NotFoundError("Master code", code_id)

        updated = await self.code_repo.update(
            code_id, update_data.dict(exclude_unset=True)
        )

        await self.audit_service.log_action(
            organisation_id=user["organisation_id"],
            module_name="MASTER_DATA",
            entity_type="CODE_MASTER",
            entity_id=code_id,
            action_type="UPDATE",
            user_id=user["user_id"],
            old_value=existing,
            new_value=updated,
        )
        return updated

    async def get_code_by_id(self, user: dict, code_id: str) -> Dict[str, Any]:
        """Get details for a specific category code with scoping."""
        code = await self.code_repo.get_by_id(code_id)
        if not code or code.get("organisation_id") != user["organisation_id"]:
            raise NotFoundError("Master code", code_id)
        return code

    async def list_units(self, user: dict) -> List[str]:
        """List standard units of measurement."""
        return ["Rft", "Sft", "Cum", "No", "Lot", "Kg", "Mt", "Hr", "Day", "Month"]
