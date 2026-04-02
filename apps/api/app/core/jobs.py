import uuid
from datetime import datetime
from typing import Any, Dict, Optional

# In-memory store for demo/development. 
# In production, this should be in Redis or MongoDB.
_jobs = {}

class JobTracker:
    @staticmethod
    def create_job(job_type: str) -> str:
        job_id = str(uuid.uuid4())
        _jobs[job_id] = {
            "id": job_id,
            "type": job_type,
            "status": "PENDING",
            "ready": False,
            "created_at": datetime.now().isoformat(),
            "result": None,
            "error": None
        }
        return job_id

    @staticmethod
    def update_job(job_id: str, status: str, result: Any = None, error: str = None):
        if job_id in _jobs:
            _jobs[job_id]["status"] = status
            _jobs[job_id]["ready"] = status in ["SUCCESS", "COMPLETED", "FAILED"]
            if result:
                _jobs[job_id]["result"] = result
            if error:
                _jobs[job_id]["error"] = error

    @staticmethod
    def get_job(job_id: str) -> Optional[Dict[str, Any]]:
        return _jobs.get(job_id)
