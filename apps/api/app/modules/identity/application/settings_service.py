import logging
from typing import Any, Dict

from ..infrastructure.repository import SettingsRepository

logger = logging.getLogger(__name__)


class SettingsService:
    """
    Sovereign Settings Controller.
    Manages organizational configuration and profile data.
    """

    def __init__(self, db, permission_checker, audit_service):
        self.db = db
        self.permission_checker = permission_checker
        self.audit_service = audit_service
        self.settings_repo = SettingsRepository(db)

    async def get_settings(self, user: dict) -> Dict[str, Any]:
        """Fetch settings for organisation with default fallback."""
        settings = await self.settings_repo.find_one(
            {"organisation_id": user["organisation_id"]}
        )
        if not settings:
            return {
                "organisation_id": user["organisation_id"],
                "cgst_percentage": 9.0,
                "sgst_percentage": 9.0,
                "retention_percentage": 5.0,
                "currency": "INR",
                "currency_symbol": "₹",
                "company_profile": {
                    "name": "TAC PMC",
                    "address": "Default Address",
                    "registration_no": "",
                    "contact_email": "",
                },
                "client_permissions": {
                    "can_view_dpr": True,
                    "can_view_financials": False,
                    "can_view_reports": True,
                },
            }
        return settings

    async def update_settings(self, user: dict, settings_data: dict) -> Dict[str, Any]:
        """Atomic update of global settings with mandatory audit logging."""
        await self.permission_checker.check_admin_role(user)

        # Sanitize sensitive fields
        payload = {
            k: v
            for k, v in settings_data.items()
            if k not in ("id", "_id", "organisation_id")
        }

        existing = await self.settings_repo.find_one(
            {"organisation_id": user["organisation_id"]}
        )
        if existing:
            updated = await self.settings_repo.update(existing["id"], payload)
        else:
            payload["organisation_id"] = user["organisation_id"]
            updated = await self.settings_repo.create(payload)

        # Mandatory Audit Logging
        await self.audit_service.log_action(
            organisation_id=user["organisation_id"],
            module_name="SETTINGS",
            entity_type="GLOBAL_SETTINGS",
            entity_id=str(
                updated.get("id") or existing.get("id") if existing else "NEW"
            ),
            action_type="UPDATE",
            user_id=user["user_id"],
            old_value=existing,
            new_value=updated,
        )

        return updated
