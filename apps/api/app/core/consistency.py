import logging
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.financial_utils import to_decimal

logger = logging.getLogger(__name__)

class ConsistencyGuardian:
    """
    Sovereign Monitor for Data Integrity (Point 61, 82, 103).
    Detects Zombie Records and Financial Divergence.
    """
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    async def find_zombies(self):
        """Detect records with missing mandatory dependencies (Point 103)."""
        # Example: Payments without existing project
        pipeline = [
            {"$lookup": {
                "from": "projects",
                "localField": "project_id",
                "foreignField": "project_id", # or project_id if string
                "as": "project"
            }},
            {"$match": {"project": {"$size": 0}}}
        ]
        zombies = await self.db.payment_certificates.aggregate(pipeline).to_list(length=100)
        if zombies:
            logger.error(f"CONSISTENCY_FAULT: Found {len(zombies)} zombie PCs without valid project.")
        
        return zombies

    async def verify_financial_sync(self, project_id: str):
        """Verify Master vs Sum(Categories) (Point 61)."""
        master = await self.db.financial_state.find_one({"project_id": project_id, "category_id": None})
        if not master: return True # Nothing to check
        
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
                 return False
                 
        return True
