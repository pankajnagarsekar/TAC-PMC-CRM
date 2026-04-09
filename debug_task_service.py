import asyncio
import os
import sys
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient

# Add app to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "apps/api")))

from app.modules.tasks.application.task_service import TaskService
from app.modules.tasks.schemas.dto import TaskCreate
from app.core.config import settings

async def test_minimal_create():
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
        task_description="Minimal Test Task",
        assigned_to_name="Test User"
    )
    
    try:
        print("Starting create_task...")
        result = await service.create_task(user, data)
        print(f"SUCCESS: {result}")
    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.drop_database("tac_pmc_test_db")
        client.close()

if __name__ == "__main__":
    asyncio.run(test_minimal_create())
