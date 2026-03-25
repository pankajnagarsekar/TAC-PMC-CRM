import sys
import os
import uuid
import concurrent.futures
from fastapi.testclient import TestClient
from bson import ObjectId
from unittest.mock import AsyncMock, patch, MagicMock

# Add apps/api to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from server import app
from core.database import get_db
from auth import get_current_user

# Mock setup
mock_db = MagicMock()
mock_db.project_metadata = MagicMock()
mock_db.project_calendars = MagicMock()
mock_db.project_schedules = MagicMock()

def override_get_db(): return mock_db
def override_get_current_user(): return {"user_id": "test_user", "organisation_id": "test_org", "role": "Admin"}

app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = override_get_current_user

client = TestClient(app)

def send_request(project_id, task_id, idempotency_key):
    payload = {
        "task_id": task_id,
        "project_id": project_id,
        "idempotency_key": idempotency_key,
        "trigger_source": "stress_test",
        "version": 1,
        "changes": {"task_name": f"Concurrent Update {uuid.uuid4()}"}
    }
    # We patch check_duplicate and save_idempotent_response to simulate real persistence
    # but for a pure API stress test, we just want to see if the server handles concurrent hits
    response = client.post(f"/api/projects/{project_id}/scheduler/calculate", json=payload)
    return response.status_code

def run_concurrent_test():
    project_id = str(ObjectId())
    task_id = str(ObjectId())
    # Use the same idempotency key to test deduplication
    shared_key = "stress-key-999"
    
    # Pre-mock metadata and calendar
    mock_db.project_metadata.find_one = AsyncMock(return_value={"project_id": project_id, "system_state": "active"})
    mock_db.project_calendars.find_one = AsyncMock(return_value={"project_id": project_id, "work_days": [1,2,3,4,5], "holidays": []})
    
    mock_cursor = MagicMock()
    mock_cursor.to_list = AsyncMock(return_value=[{"_id": ObjectId(task_id), "task_id": task_id, "task_mode": "Auto", "predecessors": []}])
    mock_db.project_schedules.find.return_value = mock_cursor
    mock_db.project_schedules.bulk_write = AsyncMock(return_value=MagicMock(modified_count=1))
    
    print(f"Simulating 10 concurrent requests with SHARED idempotency key...")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(send_request, project_id, task_id, shared_key) for _ in range(10)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    print(f"Results: {results}")
    # We expect several 200s (one real, others might be cached 200s)
    success_count = results.count(200)
    print(f"Total Success: {success_count}/10")
    
    if success_count == 10:
        print("PASS: System handled concurrent requests gracefully.")
    else:
        print("FAIL: Some requests failed.")

if __name__ == "__main__":
    # We need to patch the routes properly as seen in test_api_integration
    with patch("execution.scheduler.api.routes.scheduler.check_duplicate", new_callable=AsyncMock) as mock_check, \
         patch("execution.scheduler.api.routes.scheduler.save_idempotent_response", new_callable=AsyncMock) as mock_save:
        
        # Simulate: first one misses, subsequent ones hit (for the sake of this simulation)
        tracker = {"count": 0}
        async def side_effect_check(*args, **kwargs):
            if tracker["count"] == 0:
                tracker["count"] += 1
                return None
            return {"status": "success", "from_cache": True}
        
        mock_check.side_effect = side_effect_check
        mock_save.return_value = None
        
        run_concurrent_test()
