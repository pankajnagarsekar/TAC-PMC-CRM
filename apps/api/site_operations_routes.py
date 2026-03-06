from fastapi import APIRouter, HTTPException, Depends, status, Query
from typing import List, Optional, Literal
from datetime import datetime
from bson import ObjectId
from auth import get_current_user
from models import DPR, WorkersDailyLog, VoiceLog
from core.database import db_manager
from permissions import PermissionChecker
from audit_service import AuditService

router = APIRouter(prefix="/api/site-operations", tags=["Site Operations"])

class _LazyDB:
    def __getattr__(self, name):
        database = db_manager.db
        if database is None:
            raise RuntimeError("Database not initialized")
        return getattr(database, name)


class _LazyPermissionChecker:
    def __getattr__(self, name):
        database = db_manager.db
        if database is None:
            raise RuntimeError("Database not initialized")
        checker = PermissionChecker(database)
        return getattr(checker, name)


class _LazyAuditService:
    def __getattr__(self, name):
        database = db_manager.db
        if database is None:
            raise RuntimeError("Database not initialized")
        service = AuditService(database)
        return getattr(service, name)


# Services (lazy-bound after db_manager.connect in server startup path)
db = _LazyDB()
permission_checker = _LazyPermissionChecker()
audit_service = _LazyAuditService()

# DPR Status Machine Constants
DPR_STATUS_DRAFT = "DRAFT"
DPR_STATUS_PENDING_APPROVAL = "PENDING_APPROVAL"
DPR_STATUS_APPROVED = "APPROVED"
DPR_STATUS_REJECTED = "REJECTED"

# Valid status transitions per spec
VALID_DPR_TRANSITIONS = {
    DPR_STATUS_DRAFT: [DPR_STATUS_PENDING_APPROVAL],
    DPR_STATUS_PENDING_APPROVAL: [DPR_STATUS_APPROVED, DPR_STATUS_REJECTED],
    DPR_STATUS_APPROVED: [],  # Terminal state
    DPR_STATUS_REJECTED: [DPR_STATUS_DRAFT]  # Can be resubmitted from rejected
}

def serialize_doc(doc):
    if doc is None:
        return None
    doc["_id"] = str(doc["_id"])
    for key, value in doc.items():
        if isinstance(value, datetime):
            doc[key] = value.isoformat()
    return doc

def validate_dpr_transition(current_status: str, target_status: str) -> bool:
    """Validate if a DPR status transition is allowed per the state machine"""
    if current_status not in VALID_DPR_TRANSITIONS:
        return False
    return target_status in VALID_DPR_TRANSITIONS[current_status]

# ============================================
# DPR ENDPOINTS
# ============================================

@router.get("/projects/{project_id}/dprs", response_model=List[dict])
async def list_project_dprs(
    project_id: str,
    status_filter: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: dict = Depends(get_current_user)
):
    """List DPRs for a project with filters and pagination"""
    user = await permission_checker.get_authenticated_user(current_user)
    await permission_checker.check_project_access(user, project_id)
    
    query = {"project_id": project_id}
    if status_filter:
        query["status"] = status_filter
    
    if start_date or end_date:
        date_query = {}
        if start_date:
            date_query["$gte"] = datetime.fromisoformat(start_date)
        if end_date:
            date_query["$lte"] = datetime.fromisoformat(end_date)
        query["date"] = date_query
        
    dprs = await db.dprs.find(query).sort("date", -1).skip(skip).limit(limit).to_list(length=limit)
    return [serialize_doc(d) for d in dprs]

@router.get("/dprs/{dpr_id}", response_model=dict)
async def get_dpr_detail(dpr_id: str, current_user: dict = Depends(get_current_user)):
    """Get single DPR detail"""
    user = await permission_checker.get_authenticated_user(current_user)
    dpr = await db.dprs.find_one({"_id": ObjectId(dpr_id)})
    if not dpr:
        raise HTTPException(status_code=404, detail="DPR not found")
    
    await permission_checker.check_project_access(user, dpr["project_id"])
    return serialize_doc(dpr)

@router.patch("/dprs/{dpr_id}/approve", status_code=status.HTTP_200_OK)
async def approve_dpr(dpr_id: str, current_user: dict = Depends(get_current_user)):
    """Approve a DPR (Admin only) - Transitions DRAFT/PENDING_APPROVAL → APPROVED"""
    user = await permission_checker.get_authenticated_user(current_user)
    await permission_checker.check_admin_role(user)
    
    # Fetch current DPR to validate transition
    dpr = await db.dprs.find_one({"_id": ObjectId(dpr_id)})
    if not dpr:
        raise HTTPException(status_code=404, detail="DPR not found")
    
    current_status = dpr.get("status", DPR_STATUS_DRAFT)
    
    # Validate transition to APPROVED
    if not validate_dpr_transition(current_status, DPR_STATUS_APPROVED):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid transition: cannot approve DPR with status '{current_status}'. "
                   f"DPR must be in {', '.join(VALID_DPR_TRANSITIONS.keys())} state."
        )
    
    result = await db.dprs.find_one_and_update(
        {"_id": ObjectId(dpr_id)},
        {"$set": {
            "status": DPR_STATUS_APPROVED,
            "approved_by": user["user_id"],
            "approved_at": datetime.utcnow()
        }},
        return_document=True
    )
    
    # Audit log
    await audit_service.log_action(
        organisation_id=user["organisation_id"],
        module_name="SITE_OPERATIONS",
        entity_type="DPR",
        entity_id=dpr_id,
        action_type="APPROVE",
        user_id=user["user_id"],
        project_id=result["project_id"]
    )
    
    return {"status": DPR_STATUS_APPROVED, "message": "DPR approved successfully"}

@router.patch("/dprs/{dpr_id}/reject", status_code=status.HTTP_200_OK)
async def reject_dpr(
    dpr_id: str,
    reason: str = Query(..., min_length=1, max_length=500),
    current_user: dict = Depends(get_current_user)
):
    """Reject a DPR (Admin only) - Transitions DRAFT/PENDING_APPROVAL → REJECTED"""
    user = await permission_checker.get_authenticated_user(current_user)
    await permission_checker.check_admin_role(user)
    
    # Fetch current DPR to validate transition
    dpr = await db.dprs.find_one({"_id": ObjectId(dpr_id)})
    if not dpr:
        raise HTTPException(status_code=404, detail="DPR not found")
    
    current_status = dpr.get("status", DPR_STATUS_DRAFT)
    
    # Validate transition to REJECTED
    if not validate_dpr_transition(current_status, DPR_STATUS_REJECTED):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid transition: cannot reject DPR with status '{current_status}'. "
                   f"DPR must be in {', '.join(VALID_DPR_TRANSITIONS.keys())} state."
        )
    
    result = await db.dprs.find_one_and_update(
        {"_id": ObjectId(dpr_id)},
        {"$set": {
            "status": DPR_STATUS_REJECTED,
            "rejection_reason": reason,
            "rejected_by": user["user_id"],
            "rejected_at": datetime.utcnow()
        }},
        return_document=True
    )
    
    # Audit log
    await audit_service.log_action(
        organisation_id=user["organisation_id"],
        module_name="SITE_OPERATIONS",
        entity_type="DPR",
        entity_id=dpr_id,
        action_type="REJECT",
        user_id=user["user_id"],
        project_id=result["project_id"]
    )
    
    return {"status": DPR_STATUS_REJECTED, "message": "DPR rejected successfully"}

# ============================================
# ATTENDANCE ENDPOINTS
# ============================================

@router.get("/projects/{project_id}/attendance", response_model=List[dict])
async def list_project_attendance(
    project_id: str,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """List attendance for a project (from attendance collection)"""
    user = await permission_checker.get_authenticated_user(current_user)
    await permission_checker.check_project_access(user, project_id)
    
    query = {"project_id": project_id, "organisation_id": user["organisation_id"]}
    
    if start_date or end_date:
        date_query = {}
        if start_date:
            date_query["$gte"] = datetime.fromisoformat(start_date)
        if end_date:
            date_query["$lte"] = datetime.fromisoformat(end_date)
        query["check_in_time"] = date_query
        
    records = await db.attendance.find(query).sort("check_in_time", -1).to_list(length=200)
    return [serialize_doc(r) for r in records]

@router.patch("/attendance/{log_id}/verify", status_code=status.HTTP_200_OK)
async def verify_attendance(log_id: str, current_user: dict = Depends(get_current_user)):
    """Verify attendance record (Admin only)"""
    user = await permission_checker.get_authenticated_user(current_user)
    await permission_checker.check_admin_role(user)
    
    result = await db.attendance.find_one_and_update(
        {"_id": ObjectId(log_id)},
        {"$set": {
            "verified_by_admin": True,
            "verified_at": datetime.utcnow(),
            "verified_user_id": user["user_id"]
        }},
        return_document=True
    )
    
    if not result:
        # Fallback to workers_daily_logs if not in attendance
        result = await db.workers_daily_logs.find_one_and_update(
            {"_id": ObjectId(log_id)},
            {"$set": {
                "verified_by_admin": True,
                "verified_at": datetime.utcnow(),
                "verified_user_id": user["user_id"]
            }},
            return_document=True
        )
        
    if not result:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    
    return {"status": "verified"}

# ============================================
# VOICE LOG ENDPOINTS
# ============================================

@router.get("/projects/{project_id}/voice-logs", response_model=List[dict])
async def list_project_voice_logs(
    project_id: str,
    current_user: dict = Depends(get_current_user)
):
    """List voice logs for a project"""
    user = await permission_checker.get_authenticated_user(current_user)
    await permission_checker.check_project_access(user, project_id)
    
    logs = await db.voice_logs.find({"project_id": project_id}).sort("created_at", -1).to_list(length=100)
    return [serialize_doc(log) for log in logs]

@router.get("/voice-logs/{log_id}", response_model=dict)
async def get_voice_log_detail(log_id: str, current_user: dict = Depends(get_current_user)):
    """Get single voice log detail"""
    user = await permission_checker.get_authenticated_user(current_user)
    log = await db.voice_logs.find_one({"_id": ObjectId(log_id)})
    if not log:
        raise HTTPException(status_code=404, detail="Voice log not found")
    
    await permission_checker.check_project_access(user, log["project_id"])
    return serialize_doc(log)
