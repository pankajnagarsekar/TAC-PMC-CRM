from fastapi import APIRouter, HTTPException
from app.core.jobs import JobTracker
from app.modules.shared.domain.schemas import GenericResponse

router = APIRouter()

@router.get("/jobs/{job_id}", tags=["System"])
async def get_job_status(job_id: str):
    job = JobTracker.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
