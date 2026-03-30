from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from ..infrastructure.alert_repo import AlertRepository


class AlertService:
    """
    Sovereign Alert Service.
    Manages system-level alerts across all contexts.
    """

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.alert_repo = AlertRepository(db)

    async def raise_alert(
        self,
        organisation_id: str,
        alert_type: str,
        severity: str,
        message: str,
        project_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        session=None,
    ) -> Dict[str, Any]:
        """Raise a new system alert."""
        alert_doc = {
            "organisation_id": organisation_id,
            "project_id": project_id,
            "alert_type": alert_type,
            "severity": severity,
            "message": message,
            "data": data,
            "detected_at": datetime.now(timezone.utc),
            "resolved": False,
        }
        return await self.alert_repo.create(alert_doc, session=session)

    async def list_active_alerts(self, organisation_id: str) -> List[Dict[str, Any]]:
        """List all unresolved alerts for an organisation."""
        return await self.alert_repo.list_active_alerts(organisation_id)

    async def resolve_alert(self, alert_id: str, user_id: str) -> bool:
        """Mark an alert as resolved."""
        update_data = {
            "resolved": True,
            "resolved_at": datetime.now(timezone.utc),
            "resolved_by": user_id,
        }
        return await self.alert_repo.update(alert_id, update_data)
