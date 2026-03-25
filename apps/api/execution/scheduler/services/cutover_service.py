from fastapi import HTTPException, status, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from core.database import get_db
from execution.scheduler.models.shared_types import SystemState, PyObjectId

class CutoverService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    async def is_scheduler_active(self, project_id: str) -> bool:
        """Checks if the project has cut over to the PPM Scheduler."""
        try:
            metadata = await self.db.project_metadata.find_one({"project_id": PyObjectId(project_id)})
            if not metadata:
                return False
            return metadata.get("system_state") == SystemState.ACTIVE
        except:
            return False

    async def enforce_cutover(self, project_id: str):
        """Raises HTTPException if the project is in ACTIVE scheduler state."""
        if await self.is_scheduler_active(project_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Project {project_id} has cut over to the PPM Scheduler. Legacy manual modifications are blocked."
            )

async def get_cutover_service(db: AsyncIOMotorDatabase = Depends(get_db)) -> CutoverService:
    return CutoverService(db)
