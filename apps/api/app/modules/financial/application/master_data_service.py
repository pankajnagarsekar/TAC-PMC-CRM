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

    async def list_petty_cash_categories(self, user: dict) -> List[Dict[str, Any]]:
        """
        List only Petty Cash and Site Overhead categories.
        FIX: Uses regex for name resilience (singular/plural) and case-insensitivity.
        """
        query = {
            "organisation_id": user["organisation_id"],
            "category_name": {
                "$regex": r"^(Petty\s*Cash|Site\s*Overhead(s)?)$",
                "$options": "i"
            },
            "active_status": True,
        }
        categories = await self.code_repo.list(query)

        # Force budget_type to 'fund_transfer' for these specific categories
        # to ensure the frontend and cash services treat them as liquid funds.
        for cat in categories:
            if cat.get("budget_type") != "fund_transfer":
                cat["budget_type"] = "fund_transfer"

        return categories

    async def create_code(self, user: dict, code_data: Any) -> Dict[str, Any]:
        """Implemented authoritative master data creation with uniqueness guard."""
        await self.permission_checker.check_admin_role(user)

        # Uniqueness Guard: (Organisation, Code OR Category Name)
        existing = await self.code_repo.find_one(
            {
                "organisation_id": user["organisation_id"],
                "$or": [
                    {"code": code_data.code},
                    {"category_name": code_data.category_name}
                ]
            }
        )
        if existing:
            if existing.get("code") == code_data.code:
                raise ValidationError("CODE_EXISTS: A master code with this ID already exists.")
            raise ValidationError("NAME_EXISTS: A category with this name already exists.")

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

        update_dict = update_data.dict(exclude_unset=True)
        update_dict["version"] = update_data.expected_version + 1

        updated = await self.code_repo.update(
            code_id, update_dict, expected_version=update_data.expected_version
        )
        if not updated:
            raise ValidationError("CONFLICT: Master code was modified by another process (Version Mismatch).")

        # Ensure audit log is consistent if service layer requires version in dict

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

    async def deactivate_code(self, user: dict, code_id: str) -> Dict[str, Any]:
        """Deactivate (soft-delete) a category code. Admin only."""
        await self.permission_checker.check_admin_role(user)

        existing = await self.code_repo.get_by_id(code_id)
        if not existing or existing.get("organisation_id") != user["organisation_id"]:
            raise NotFoundError("Master code", code_id)

        current_version = existing.get("version", 1)
        updated = await self.code_repo.update(
            code_id, {"active_status": False, "version": current_version + 1}, expected_version=current_version
        )
        if not updated:
            raise ValidationError("CONFLICT: Master code was modified by another process (Version Mismatch).")

        await self.audit_service.log_action(
            organisation_id=user["organisation_id"],
            module_name="MASTER_DATA",
            entity_type="CODE_MASTER",
            entity_id=code_id,
            action_type="DELETE",
            user_id=user["user_id"],
            old_value=existing,
            new_value=updated,
        )
        return updated

    async def list_units(self, user: dict) -> List[str]:
        """List standard units of measurement."""
        return ["Rft", "Sft", "Cum", "No", "Lot", "Kg", "Mt", "Hr", "Day", "Month"]
