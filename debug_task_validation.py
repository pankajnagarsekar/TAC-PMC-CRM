import asyncio
import os
import sys
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient

# Add app to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "apps/api")))

from app.modules.tasks.application.task_service import TaskService
from app.modules.tasks.schemas.dto import TaskCreate, Task
from app.core.config import settings

async def test_validation():
    client = AsyncIOMotorClient(settings.MONGO_URL)
    db = client["tac_pmc_test_db"]
    
    service = TaskService(db)
    
    user = {
        "user_id": "test-user-id",
        "organisation_id": "test-org-123",
        "name": "Test User"
    }
    
    data = TaskCreate(
        project_id="test-proj-456",
        task_description="Validation Test Task",
        assigned_to_name="Test User"
    )
    
    try:
        print("Starting create_task...")
        result = await service.create_task(user, data)
        print("Create complete. Validating with Task schema...")
        # Simulating FastAPI's internal validation
        task_obj = Task(**result)
        print(f"VALIDATION SUCCESS: {task_obj.model_dump()}")
    except Exception as e:
        print(f"VALIDATION FAILED: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.drop_database("tac_pmc_test_db")
        client.close()

if __name__ == "__main__":
    asyncio.run(test_validation())
