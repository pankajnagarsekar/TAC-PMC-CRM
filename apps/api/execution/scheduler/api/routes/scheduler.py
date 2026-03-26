"""
PPM Scheduler API Routes.
Orchestrates CPM engine, resource leveling, and database persistence.

Constitution §4 / Tech Arch §3.1:
    - POST /calculate: Merges changes, runs CPM pipeline, persists results.
    - POST /baseline/lock: Snapshots current state as baseline.
    - GET /financials: Returns read-only aggregated financial data.
"""
import logging
import uuid
from decimal import Decimal
from dataclasses import asdict
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, date
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorClientSession
from pydantic import ValidationError
from pymongo import UpdateOne

from execution.scheduler.models.project_schedules import (
    ProjectScheduleTask, TaskChanges, ScheduleChangeRequest, TaskMode
)
from execution.scheduler.models.schedule_baselines import (
    ScheduleBaseline, BaselineTaskSnapshot, BaselineFinancialSnapshot, BaselineLockRequest
)
from execution.scheduler.models.project_metadata import ProjectMetadata
from execution.scheduler.models.project_calendars import ProjectCalendar
from execution.scheduler.models.audit_logs import AuditLogEntry
from execution.scheduler.models.shared_types import (
    PyObjectId, AuditAction, ChangeSource, SystemState, TaskStatus
)
from execution.scheduler.engine.interfaces import (
    CalculationRequest, 
    CalculationResponse, 
    TaskInput, 
    CalculationStatus,
    EngineError,
    PredecessorInput,
    TaskResult
)
from execution.scheduler.engine.dag_validator import validate_dag
from execution.scheduler.engine.calculate_critical_path import calculate_critical_path
from execution.scheduler.engine.invariant_checker import check_invariants
from execution.scheduler.engine.resource_capacity import level_resources, LevelingRequest, ResourceInfo

from execution.scheduler.api.middleware.idempotency import check_duplicate, save_idempotent_response
from execution.scheduler.api.middleware.transaction import get_transaction_session
from execution.scheduler.pipelines.financial_aggregations import build_wo_value_pipeline, build_payment_value_pipeline
from execution.scheduler.db.bridge_installer import migrate_project_schedule

from app.db.mongodb import get_db
from app.core.dependencies import get_authenticated_user, PermissionChecker

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Scheduler"])

# =============================================================================
# Helper: Merge changes into current state
# =============================================================================

async def _get_merged_tasks(
    db: AsyncIOMotorDatabase,
    project_id: str,
    request: ScheduleChangeRequest,
    session: AsyncIOMotorClientSession
) -> List[ProjectScheduleTask]:
    """
    Fetches the current tasks from MongoDB and applies the requested changes.
    """
    # Fetch all existing tasks for the project
    cursor = db.project_schedules.find({"project_id": project_id, "is_deleted": False}, session=session)
    existing_tasks_raw = await cursor.to_list(length=10000)
    
    current_task_map = {str(t["_id"]): ProjectScheduleTask(**t) for t in existing_tasks_raw}
    
    # 2. Apply Deletions
    if request.deleted_task_ids:
        for tid in request.deleted_task_ids:
            tid_str = str(tid)
            if tid_str in current_task_map:
                del current_task_map[tid_str]
    
    # 3. Apply Change Request (Master Task)
    master_tid = str(request.task_id)
    if master_tid in current_task_map:
        # Update existing
        current_task = current_task_map[master_tid]
        updated_data = current_task.model_dump()
        # Only update fields provided in the change request
        change_dict = request.changes.model_dump(exclude_unset=True)
        updated_data.update(change_dict)
        current_task_map[master_tid] = ProjectScheduleTask(**updated_data)
    else:
        # Handle new task creation optimistically during calculation
        logger.info(f"Task {master_tid} not found. Creating new task document.")
        new_id = ObjectId()
        new_tid = str(new_id)
        
        # Build new task from defaults + changes
        new_task_data = {
            "_id": new_id,
            "task_id": new_tid,
            "project_id": project_id,
            "external_ref_id": request.changes.external_ref_id or master_tid,
            "wbs_code": request.changes.wbs_code or "99.new",
            "task_name": request.changes.task_name or "New Task",
            "task_status": request.changes.task_status or TaskStatus.DRAFT,
            "version": 1,
            "is_deleted": False,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        
        # Apply any other fields from the change request
        change_dict = request.changes.model_dump(exclude_unset=True)
        new_task_data.update(change_dict)
        
        # Ensure ID fields are correct
        new_task_data["_id"] = new_id
        new_task_data["task_id"] = new_tid
        
        new_task = ProjectScheduleTask(**new_task_data)
        current_task_map[new_tid] = new_task
        
        # Track ID mapping if necessary (frontend updates via reconciliation)
        logger.info(f"Created new task {new_tid} (mapped from {master_tid})")
    
    return list(current_task_map.values())

# =============================================================================
# Helper: Date Rollup for Summary Tasks
# =============================================================================

def _apply_date_rollups(tasks: List[ProjectScheduleTask]) -> List[ProjectScheduleTask]:
    """
    Constitution §6: Summary tasks MUST have their dates calculated based on children.
    scheduled_start = MIN(child.scheduled_start)
    scheduled_finish = MAX(child.scheduled_finish)
    """
    task_map = {str(t.id): t for t in tasks}
    
    # Identify summary tasks
    summary_tasks = [t for t in tasks if t.is_summary]
    if not summary_tasks:
        return tasks
        
    parent_to_children = {}
    for t in tasks:
        if t.parent_id:
            pid_str = str(t.parent_id)
            if pid_str not in parent_to_children:
                parent_to_children[pid_str] = []
            parent_to_children[pid_str].append(t)
            
    # Recursive rollup
    def rollup(task_id_str: str):
        task = task_map.get(task_id_str)
        if not task or not task.is_summary:
            return
            
        children = parent_to_children.get(task_id_str, [])
        if not children:
            return
            
        child_starts = []
        child_finishes = []
        
        for child in children:
            if child.is_summary:
                rollup(str(child.id))
            
            if child.scheduled_start:
                child_starts.append(child.scheduled_start)
            if child.scheduled_finish:
                child_finishes.append(child.scheduled_finish)
                
        if child_starts:
            task.scheduled_start = min(child_starts)
        if child_finishes:
            task.scheduled_finish = max(child_finishes)
            
    for st in summary_tasks:
        rollup(str(st.id))
        
    return list(task_map.values())

# =============================================================================
# Main Calculation Route
# =============================================================================

@router.post("/{project_id}/calculate", response_model=CalculationResponse)
async def calculate_schedule(
    project_id: str,
    request: ScheduleChangeRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    session: AsyncIOMotorClientSession = Depends(get_transaction_session),
    current_user: dict = Depends(get_authenticated_user)
):
    """
    Orchestrates the full CPM calculation pipeline (Constitution §4).
    """
    # ─── 1. Idempotency Check ────────────────────────────────────────────────
    cached = await check_duplicate(db, request.idempotency_key)
    if cached:
        return cached

    try:
        # ─── 2. Data Gathering & Merging ──────────────────────────────────────
        metadata_doc = await db.project_metadata.find_one({"project_id": PyObjectId(project_id)}, session=session)
        if not metadata_doc:
             raise HTTPException(status_code=404, detail="Project metadata not found")
        metadata = ProjectMetadata(**metadata_doc)
        
        if metadata.system_state == SystemState.LOCKED:
            raise HTTPException(status_code=403, detail="Project is locked.")

        calendar_doc = await db.project_calendars.find_one({"project_id": PyObjectId(project_id)}, session=session)
        calendar = ProjectCalendar(**calendar_doc) if calendar_doc else ProjectCalendar(project_id=PyObjectId(project_id))

        merged_tasks = await _get_merged_tasks(db, project_id, request, session)
        
        # ─── 3. CPM Engine Run (Leaf Tasks) ──────────────────────────────────
        task_inputs = [
            TaskInput(
                task_id=str(t.id),
                task_mode=t.task_mode,
                predecessors=[
                    PredecessorInput(
                        task_id=str(p.task_id),
                        type=p.type,
                        lag_days=p.lag_days,
                        is_external=p.is_external,
                        strength=p.strength
                    ) for p in t.predecessors
                ],
                constraint_type=t.constraint_type,
                constraint_date=t.constraint_date,
                scheduled_start=t.scheduled_start,
                scheduled_finish=t.scheduled_finish,
                scheduled_duration=t.scheduled_duration,
                actual_start=t.actual_start,
                actual_finish=t.actual_finish,
                percent_complete=t.percent_complete,
                is_milestone=t.is_milestone,
                deadline=t.deadline,
                parent_id=str(t.parent_id) if t.parent_id else None,
                is_summary=t.is_summary,
                summary_type=t.summary_type,
                assigned_resources=[str(rid) for rid in t.assigned_resources]
            ) for t in merged_tasks
        ]
        
        calc_request = CalculationRequest(
            project_id=project_id,
            tasks=task_inputs,
            calendar=calendar,
            resource_calendars=[]
        )

        dag_result = validate_dag(calc_request)
        if not dag_result.is_valid:
            raise HTTPException(status_code=400, detail={"error": "CYCLIC_DEPENDENCY", "message": dag_result.error_message})

        calc_response = calculate_critical_path(calc_request)
        if calc_response.status == CalculationStatus.FAILURE:
            raise HTTPException(status_code=400, detail={"errors": calc_response.errors})

        # ─── 4. Apply Engine Results to Merged Tasks ──────────────────────────
        task_result_map = {tr.task_id: tr for tr in calc_response.tasks}
        for task in merged_tasks:
            tid_str = str(task.id)
            if tid_str in task_result_map:
                res = task_result_map[tid_str]
                task.scheduled_start = res.scheduled_start
                task.scheduled_finish = res.scheduled_finish
                task.scheduled_duration = res.scheduled_duration
                task.early_start = res.early_start
                task.early_finish = res.early_finish
                task.late_start = res.late_start
                task.late_finish = res.late_finish
                task.total_slack = res.total_slack
                task.is_critical = res.is_critical

        # ─── 5. Parent Rollups (Dates) ────────────────────────────────────────
        _apply_date_rollups(merged_tasks)

        # ─── 6. Sync CalculationResponse with all tasks ─────────────────────
        # We need to return TaskResult objects for EVERYTHING (Leaf + Summary)
        final_task_results = []
        for task in merged_tasks:
            # For summary tasks, some CPM values (slack, critical) are derived from children
            # For MVP, we'll just populate start/finish and mark slack=0 if critical path passes through
            final_task_results.append(TaskResult(
                task_id=str(task.id),
                scheduled_start=task.scheduled_start,
                scheduled_finish=task.scheduled_finish,
                scheduled_duration=task.scheduled_duration or 0,
                early_start=task.early_start or task.scheduled_start,
                early_finish=task.early_finish or task.scheduled_finish,
                late_start=task.late_start or task.scheduled_start,
                late_finish=task.late_finish or task.scheduled_finish,
                total_slack=task.total_slack or 0,
                is_critical=task.is_critical or False,
                deadline_variance_days=None,
                is_deadline_breached=False
            ))
        
        calc_response.tasks = final_task_results

        # ─── 7. Atomic Persistence ───────────────────────────────────────────
        bulk_ops = []
        for task in merged_tasks:
            update_data = task.model_dump(by_alias=True, exclude={"id"})
            update_data["calculation_version"] = calc_response.calculation_version
            update_data["updated_at"] = datetime.now(timezone.utc)
            
            bulk_ops.append(UpdateOne(
                {"_id": task.id},
                {"$set": update_data},
                upsert=True
            ))
        
        if request.deleted_task_ids:
            for dtid in request.deleted_task_ids:
                bulk_ops.append(UpdateOne({"_id": PyObjectId(dtid)}, {"$set": {"is_deleted": True, "updated_at": datetime.now(timezone.utc)}}))

        if bulk_ops:
            await db.project_schedules.bulk_write(bulk_ops, session=session)

        # Update metadata
        await db.project_metadata.update_one(
            {"project_id": PyObjectId(project_id)},
            {"$set": {"last_calculation_version": calc_response.calculation_version, "last_calculated_at": datetime.now(timezone.utc)}},
            session=session
        )

        # ─── 8. Audit Log ───────────────────────────────────────────────────
        audit_entry = AuditLogEntry(
            project_id=project_id,
            user_id=current_user["sub"],
            action=AuditAction.SCHEDULE_RECALCULATED,
            trigger_source=request.trigger_source,
            task_id=request.task_id,
            changes=request.changes.model_dump(exclude_unset=True),
            idempotency_key=request.idempotency_key,
            calculation_version=calc_response.calculation_version
        )
        await db.project_audit_logs.insert_one(
            audit_entry.model_dump(by_alias=True, exclude={"id"}),
            session=session
        )

        # ─── 9. Idempotency Save ─────────────────────────────────────────────
        await save_idempotent_response(
            db=db, session=session, 
            idempotency_key=request.idempotency_key,
            entity_type="project_schedule", response=asdict(calc_response)
        )

        return calc_response

    except Exception as e:
        logger.exception("Calculation failed")
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# Baseline Lock Route
# =============================================================================

@router.post("/{project_id}/baseline/lock")
async def lock_baseline(
    project_id: str,
    lock_request: BaselineLockRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    session: AsyncIOMotorClientSession = Depends(get_transaction_session),
    current_user: dict = Depends(get_authenticated_user)
):
    """
    Constitution §2.2 & Phase 4: Snapshots current schedule into an immutable baseline.
    Enforces 11 baseline limit and captures financial state.
    """
    # ─── 1. Idempotency Check ────────────────────────────────────────────────
    cached = await check_duplicate(db, lock_request.idempotency_key)
    if cached:
        return cached

    # ─── 2. Limit Check ──────────────────────────────────────────────────────
    existing_count = await db.schedule_baselines.count_documents(
        {"project_id": PyObjectId(project_id)}, session=session
    )
    if existing_count >= 11:
        raise HTTPException(
            status_code=400, 
            detail="Maximum 11 baselines per project reached. Lock disabled."
        )

    # ─── 3. Gather Task Snapshots ────────────────────────────────────────────
    cursor = db.project_schedules.find(
        {"project_id": PyObjectId(project_id), "is_deleted": False}, 
        session=session
    )
    tasks_raw = await cursor.to_list(length=10000)
    if not tasks_raw:
        raise HTTPException(status_code=400, detail="No tasks found to baseline")

    snapshots: List[Dict[str, Any]] = []
    total_baseline_cost = Decimal("0")
    
    for t_doc in tasks_raw:
        # Calculate cost for this task (if applicable)
        cost = Decimal(str(t_doc.get("baseline_cost", "0")))
        total_baseline_cost += cost

        # Create individual task snapshot
        ss = BaselineTaskSnapshot(
            task_id=t_doc["_id"],
            wbs_code=t_doc.get("wbs_code", ""),
            task_name=t_doc.get("task_name", ""),
            external_ref_id=t_doc.get("external_ref_id", ""),
            is_milestone=t_doc.get("is_milestone", False),
            baseline_start=str(t_doc.get("scheduled_start")) if t_doc.get("scheduled_start") else None,
            baseline_finish=str(t_doc.get("scheduled_finish")) if t_doc.get("scheduled_finish") else None,
            baseline_duration=t_doc.get("scheduled_duration"),
            baseline_cost=cost,
            scheduled_start=str(t_doc.get("scheduled_start")) if t_doc.get("scheduled_start") else None,
            scheduled_finish=str(t_doc.get("scheduled_finish")) if t_doc.get("scheduled_finish") else None,
            scheduled_duration=t_doc.get("scheduled_duration"),
            percent_complete=t_doc.get("percent_complete", 0)
        )
        snapshots.append(ss.model_dump())

    # ─── 4. Capture Financial Totals ──────────────────────────────────────────
    # [Session 1.2 Pipeline calls]
    wo_pipeline = build_wo_value_pipeline(project_id)
    wo_summary = await db.project_schedules.aggregate(wo_pipeline, session=session).to_list(length=10000)
    total_wo_value = sum([Decimal(str(r.get("wo_value", "0"))) for r in wo_summary])

    pc_pipeline = build_payment_value_pipeline(project_id)
    pc_summary = await db.project_schedules.aggregate(pc_pipeline, session=session).to_list(length=10000)
    total_pc_value = sum([Decimal(str(r.get("payment_value", "0"))) for r in pc_summary])

    fin_snapshot = BaselineFinancialSnapshot(
        project_total_baseline_cost=total_baseline_cost,
        total_wo_value=total_wo_value,
        total_payment_value=total_pc_value
    )

    # ─── 5. Create & Save Baseline ───────────────────────────────────────────
    new_baseline = ScheduleBaseline(
        project_id=PyObjectId(project_id),
        baseline_number=existing_count + 1,
        label=lock_request.label or f"Baseline {existing_count + 1}",
        snapshot_data=snapshots,
        financial_snapshot=fin_snapshot,
        locked_by=PyObjectId(current_user["sub"]),
        locked_at=datetime.now(timezone.utc),
        is_immutable=True
    )

    await db.schedule_baselines.insert_one(
        new_baseline.model_dump(by_alias=True, exclude={"id"}),
        session=session
    )

    # ─── 6. Update Project Metadata ──────────────────────────────────────────
    await db.project_metadata.update_one(
        {"project_id": PyObjectId(project_id)},
        {"$set": {
            "total_baseline_cost_cache": Decimal128(str(total_baseline_cost)),
            "system_state": SystemState.ACTIVE, # Moves from PLANNING to ACTIVE on first lock
            "updated_at": datetime.now(timezone.utc)
        }},
        session=session
    )

    # ─── 7. Audit Log ───────────────────────────────────────────────────────
    audit_entry = AuditLogEntry(
        project_id=project_id,
        user_id=current_user["sub"],
        action=AuditAction.BASELINE_LOCKED,
        trigger_source=ChangeSource.API,
        comment=f"Baseline {new_baseline.baseline_number} locked. Total Cost: {total_baseline_cost}",
        idempotency_key=lock_request.idempotency_key
    )
    await db.project_audit_logs.insert_one(
        audit_entry.model_dump(by_alias=True, exclude={"id"}),
        session=session
    )

    # ─── 8. Idempotency Save ────────────────────────────────────────────────
    response_data = {
        "status": "success",
        "baseline_number": new_baseline.baseline_number,
        "total_baseline_cost": float(total_baseline_cost)
    }
    await save_idempotent_response(
        db=db, session=session,
        idempotency_key=lock_request.idempotency_key,
        entity_type="baseline_lock",
        response=response_data
    )

    return response_data

# =============================================================================
# Financials Route
# =============================================================================

@router.get("/{project_id}/financials")
async def get_financials(
    project_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_authenticated_user)
):
    """
    Returns read-only financial data.
    """
    # 1. Run WO Pipeline
    wo_pipeline = build_wo_value_pipeline(project_id)
    wo_results = await db.project_schedules.aggregate(wo_pipeline).to_list(length=10000)
    
    # 2. Run Payment Pipeline
    pc_pipeline = build_payment_value_pipeline(project_id)
    pc_results = await db.project_schedules.aggregate(pc_pipeline).to_list(length=10000)
    
    # Merge results
    financials = {str(r["_id"]): r for r in wo_results}
    for pc_r in pc_results:
        tid = str(pc_r["_id"])
        if tid in financials:
            financials[tid]["payment_value"] = pc_r.get("payment_value", 0)
        else:
            financials[tid] = pc_r
            
    return list(financials.values())

from execution.scheduler.services.baseline_comparison import BaselineComparisonService

@router.get("/{project_id}/baseline/compare")
async def compare_baselines(
    project_id: str,
    baseline_a: int = Query(..., ge=1, le=11),
    baseline_b: Optional[int] = Query(None, ge=1, le=11),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_authenticated_user)
):
    """
    Computes variances between two baselines (or baseline vs current).
    """
    service = BaselineComparisonService(db)
    results = await service.compare_baselines(project_id, baseline_a, baseline_b)
    return results

from core.ai_service import AIService

@router.post("/{project_id}/tasks/{task_id}/mom-extract")
async def extract_mom_for_task(
    project_id: str,
    task_id: str,
    notes: Dict[str, str] = Body(...),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_authenticated_user)
):
    """
    Extracts action items from meeting notes with project/task context.
    """
    ai_service = AIService(db)
    result = await ai_service.run_mom_extraction(
        meeting_notes=notes.get("raw_notes", ""),
        organisation_id=current_user["organisation_id"],
        user_id=current_user["sub"],
        project_id=project_id,
        task_id=task_id
    )
    return result

# =============================================================================
# Migration Route
# =============================================================================

@router.post("/{project_id}/migrate")
async def trigger_migration(
    project_id: str,
    dry_run: bool = Query(True),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_authenticated_user)
):
    """
    Triggers the bridge installer to migrate legacy payment schedules to project_schedules.
    """
    # Authorization: Ensure user has write access to the project
    checker = PermissionChecker(db)
    await checker.check_project_access(current_user, project_id, require_write=True)

    report = await migrate_project_schedule(db, project_id, dry_run=dry_run)
    return report
