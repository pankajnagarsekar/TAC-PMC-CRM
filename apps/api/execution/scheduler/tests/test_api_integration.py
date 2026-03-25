import pytest
from datetime import date, datetime, timezone
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
from decimal import Decimal
from bson import ObjectId

# Import the app and models
from server import app
from execution.scheduler.models.project_schedules import ScheduleChangeRequest, TaskChanges
from execution.scheduler.models.shared_types import SystemState
from core.database import get_db
from auth import get_current_user

# Mock database
# Use MagicMock for the DB structure so sync find() works, but children can be AsyncMock
mock_db = MagicMock()
mock_db.project_metadata = MagicMock()
mock_db.project_calendars = MagicMock()
mock_db.project_schedules = MagicMock()

# Mock user
mock_user = {
    "sub": "user123",
    "user_id": "user123",
    "name": "Test User",
    "email": "test@example.com",
    "role": "Admin",
    "organisation_id": "org123"
}

def override_get_db():
    return mock_db

def override_get_current_user():
    return mock_user

app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = override_get_current_user

# Mock transaction session
async def override_get_transaction_session():
    yield AsyncMock()

from execution.scheduler.api.middleware.transaction import get_transaction_session
app.dependency_overrides[get_transaction_session] = override_get_transaction_session

client = TestClient(app)

@pytest.mark.asyncio
async def test_calculate_flow():
    """
    Test the full /calculate flow:
    1. Idempotency check (miss)
    2. Fetch Metadata
    3. Fetch Calendar
    4. Merge Tasks
    5. Run Engine
    6. Persist
    7. Idempotency save
    """
    project_id = str(ObjectId())
    idempotency_key = "test-key-123"
    
    # Setup Mocks
    # 1. check_duplicate -> None
    with patch("execution.scheduler.api.routes.scheduler.check_duplicate", new_callable=AsyncMock) as mock_check:
        mock_check.return_value = None
        
        # 2. Metadata
        mock_db.project_metadata.find_one = AsyncMock(return_value={
            "project_id": project_id,
            "project_name": "Test Project",
            "system_state": "active",
            "last_calculation_version": "initial-calc-uuid"
        })
        
        # 3. Calendar
        mock_db.project_calendars.find_one = AsyncMock(return_value={
            "project_id": project_id,
            "work_days": [1,2,3,4,5],
            "holidays": []
        })
        
        # 4. Tasks (Mock one existing task)
        task_id = ObjectId()
        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(return_value=[
            {
                "_id": task_id,
                "project_id": project_id,
                "wbs_code": "1",
                "external_ref_id": "EXT-1",
                "task_name": "Initial Task",
                "scheduled_start": "2026-03-30",
                "scheduled_finish": "2026-04-03",
                "scheduled_duration": 5,
                "task_mode": "Auto"
            }
        ])
        mock_db.project_schedules.find.return_value = mock_cursor
        
        payload = {
            "task_id": str(task_id),
            "project_id": project_id,
            "idempotency_key": idempotency_key,
            "trigger_source": "gantt_drag",
            "version": 1,
            "changes": {
                "task_name": "Updated Task",
                "scheduled_duration": 5
            }
        }
        
        # 6. Mock bulk_write
        mock_db.project_schedules.bulk_write = AsyncMock()
        mock_db.project_metadata.update_one = AsyncMock()
        mock_db.project_audit_logs.insert_one = AsyncMock()
        
        # 7. Mock save_idempotent_response
        with patch("execution.scheduler.api.routes.scheduler.save_idempotent_response", new_callable=AsyncMock) as mock_save:
            
            response = client.post(f"/api/scheduler/{project_id}/calculate", json=payload)
            
            # The route might return 500 if something fails deeply, let's see
            if response.status_code != 200:
                print(response.json())
                
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            
            # Verify persistence was called
            assert mock_db.project_schedules.bulk_write.called
            assert mock_save.called

@pytest.mark.asyncio
async def test_baseline_lock():
    project_id = str(ObjectId())
    
    # 1. Mock find active tasks
    mock_cursor = MagicMock()
    mock_cursor.to_list = AsyncMock(return_value=[
        {"_id": ObjectId(), "scheduled_start": datetime(2026, 3, 30), "scheduled_finish": datetime(2026, 4, 3), "scheduled_cost": Decimal("1000")}
    ])
    mock_db.project_schedules.find.return_value = mock_cursor
    
    # 2. Mock writes
    mock_db.project_schedules.bulk_write = AsyncMock()
    mock_db.project_metadata.update_one = AsyncMock()
    mock_db.project_audit_logs.insert_one = AsyncMock()
    
    response = client.post(f"/api/scheduler/{project_id}/baseline/lock")
    
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert float(response.json()["total_baseline_cost_cache"]) == 1000.0
    
    assert mock_db.project_schedules.bulk_write.called
    assert mock_db.project_metadata.update_one.called
