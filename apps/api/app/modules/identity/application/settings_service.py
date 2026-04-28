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
                "name": "TAC PMC",
                "address": "",
                "email": "",
                "phone": "",
                "gst_number": "",
                "pan_number": "",
                "cgst_percentage": 9.0,
                "sgst_percentage": 9.0,
                "retention_percentage": 5.0,
                "wo_prefix": "WO",
                "pc_prefix": "PC",
                "invoice_prefix": "INV",
                "currency": "INR",
                "currency_symbol": "₹",
                "terms_and_conditions": "Standard terms and conditions apply...",
                "client_permissions": {
                    "can_view_dpr": True,
                    "can_view_financials": False,
                    "can_view_reports": True,
                    "can_view_scheduler": False,
                },
            }
        if settings:
            # Strip internal and deprecated nested fields
            organisation_id = settings.get("organisation_id", user["organisation_id"])
            legacy_profile = settings.get("company_profile", {})

            return {
                "organisation_id": organisation_id,
                "name": settings.get("name") or legacy_profile.get("name") or "TAC PMC",
                "address": settings.get("address") or legacy_profile.get("address") or "",
                "email": settings.get("email") or legacy_profile.get("contact_email") or "",
                "phone": settings.get("phone") or "",
                "gst_number": settings.get("gst_number") or legacy_profile.get("registration_no") or "",
                "pan_number": settings.get("pan_number") or "",
                "cgst_percentage": settings.get("cgst_percentage", 9.0),
                "sgst_percentage": settings.get("sgst_percentage", 9.0),
                "retention_percentage": settings.get("retention_percentage", 5.0),
                "wo_prefix": settings.get("wo_prefix", "WO"),
                "pc_prefix": settings.get("pc_prefix", "PC"),
                "invoice_prefix": settings.get("invoice_prefix", "INV"),
                "currency": settings.get("currency", "INR"),
                "currency_symbol": settings.get("currency_symbol", "₹"),
                "terms_and_conditions": settings.get("terms_and_conditions", ""),
                "client_permissions": settings.get("client_permissions", {
                    "can_view_dpr": True,
                    "can_view_financials": False,
                    "can_view_reports": True,
                    "can_view_scheduler": False,
                }),
                "version": settings.get("version", 1),
            }
        return settings

    async def update_settings(self, user: dict, settings_data: Any) -> Dict[str, Any]:
        """Atomic update of global settings with mandatory audit logging."""
        await self.permission_checker.check_admin_role(user)

        # Sanitize sensitive fields
        data_dict = settings_data.dict(exclude_unset=True) if hasattr(settings_data, "dict") else settings_data
        payload = {
            k: v
            for k, v in data_dict.items()
            if k not in ("id", "_id", "organisation_id")
        }

        existing = await self.settings_repo.find_one(
            {"organisation_id": user["organisation_id"]}
        )
        
        expected_version = payload.pop("expected_version", None)
        if existing:
            # Atomic update with version check
            payload["version"] = (existing.get("version", 1)) + 1
            updated = await self.settings_repo.update(
                existing["id"], 
                payload, 
                expected_version=expected_version
            )
            if not updated:
                from app.modules.shared.domain.exceptions import ValidationError
                raise ValidationError("CONFLICT: Settings updated by another user or version mismatch.")
        else:
            payload["organisation_id"] = user["organisation_id"]
            payload["version"] = 1
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
