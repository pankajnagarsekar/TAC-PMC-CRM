import logging
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.financial_utils import to_decimal
from app.modules.shared.application.alert_service import AlertService

logger = logging.getLogger(__name__)

class ConsistencyGuardian:
    """
    Sovereign Monitor for Data Integrity (Point 61, 82, 103, 122).
    Detects Zombie Records and Financial Divergence; Triggers System Alerts.
    """
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.alert_service = AlertService(db)

    async def find_zombies(self):
        """Fixed CR-27: Detect and Alert for records with missing mandatory dependencies."""
        # Check Payments without Projects
        pipeline = [
            {"$lookup": {
                "from": "projects",
                "localField": "project_id",
                "foreignField": "project_id",
                "as": "project"
            }},
            {"$match": {"project": {"$size": 0}}}
        ]
        
        zombie_pcs = await self.db.payment_certificates.aggregate(pipeline).to_list(length=100)
        
        if zombie_pcs:
            logger.critical(f"CONSISTENCY_FAULT: Found {len(zombie_pcs)} zombie PCs.")
            for pc in zombie_pcs:
                await self.alert_service.raise_alert(
                    organisation_id=pc.get("organisation_id", "GLOBAL"),
                    alert_type="ZOMBIE_RECORD",
                    severity="high",
                    message=f"Payment Certificate {pc.get('pc_ref')} exists without a valid Project ID {pc.get('project_id')}",
                    project_id=pc.get("project_id"),
                    data={"pc_id": str(pc["_id"]), "ref": pc.get("pc_ref")}
                )

        return zombie_pcs

    async def verify_financial_sync(self, project_id: str, organisation_id: str):
        """Fixed CR-27: Detect and Alert for Master Budget divergence."""
        master = await self.db.financial_state.find_one({"project_id": project_id, "category_id": None})
        if not master: return True
        
        category_sum = await self.db.financial_state.aggregate([
            {"$match": {"project_id": project_id, "category_id": {"$ne": None}}},
            {"$group": {
                "_id": None,
                "total_committed": {"$sum": "$committed_value"}
            }}
        ]).to_list(length=1)
        
        if category_sum:
            actual = to_decimal(category_sum[0]["total_committed"])
            expected = to_decimal(master["total_committed"])
            
            if actual != expected:
                 logger.critical(f"INTEGRITY_FAILURE: Project {project_id} Master ({expected}) != Category Sum ({actual})")
                 await self.alert_service.raise_alert(
                     organisation_id=organisation_id,
                     alert_type="FINANCIAL_DIVERGENCE",
                     severity="critical",
                     message=f"Financial divergence in Project {project_id}. Master committed {expected} vs Sum of categories {actual}.",
                     project_id=project_id,
                     data={"master": str(expected), "sum": str(actual)}
                 )
                 return False
                 
        return True
