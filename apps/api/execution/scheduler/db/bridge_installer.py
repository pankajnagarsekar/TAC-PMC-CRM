import uuid
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Dict, Any, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from execution.scheduler.models.project_schedules import ProjectScheduleTask, TaskMode
from execution.scheduler.models.project_metadata import ProjectMetadata
from execution.scheduler.models.shared_types import TaskStatus, SystemState, PyObjectId
from execution.scheduler.db.migration_skeleton import MigrationReport, MigrationTaskResult

logger = logging.getLogger(__name__)

async def migrate_project_schedule(
    db: AsyncIOMotorDatabase,
    project_id: str,
    dry_run: bool = True,
) -> MigrationReport:
    """
    Migrates legacy project schedule data to project_schedules format.
    Ensures external_ref_id immutability.
    """
    # 1. Verification of project metadata
    metadata_doc = await db.project_metadata.find_one({"project_id": PyObjectId(project_id)})
    if not metadata_doc:
        # Create default metadata if missing
        metadata_doc = {
            "project_id": PyObjectId(project_id),
            "system_state": SystemState.PLANNING,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        if not dry_run:
            await db.project_metadata.insert_one(metadata_doc)
    
    metadata = ProjectMetadata(**metadata_doc)
    
    # 2. Extract legacy tasks
    # We assume legacy tasks are in a collection named 'payment_schedule'
    legacy_cursor = db.payment_schedule.find({"project_id": project_id})
    legacy_tasks = await legacy_cursor.to_list(length=10000)
    
    total_legacy_tasks = len(legacy_tasks)
    total_migrated = 0
    total_failed = 0
    legacy_total_cost = Decimal("0")
    migrated_total_cost = Decimal("0")
    
    task_results = []
    new_tasks = []
    
    # Mapping logic
    for lt in legacy_tasks:
        try:
            legacy_id = str(lt["_id"])
            est_cost = Decimal(str(lt.get("estimated_cost", "0")))
            legacy_total_cost += est_cost
            
            # Check if already migrated (external_ref_id check)
            existing = await db.project_schedules.find_one({"external_ref_id": legacy_id})
            
            if existing:
                task_results.append(MigrationTaskResult(
                    legacy_id=legacy_id,
                    new_task_id=str(existing["_id"]),
                    external_ref_id=legacy_id,
                    status="skipped",
                    warnings=["Already migrated"]
                ))
                continue
            
            # New task creation
            # Rule: Legacy start_date -> scheduled_start
            # Rule: legacy_status -> TaskStatus
            # Rule: task_mode = Auto
            
            task_name = lt.get("task_name", "Unnamed Legacy Task")
            
            new_task = ProjectScheduleTask(
                project_id=project_id,
                task_name=task_name,
                external_ref_id=legacy_id, # Immutability bond
                task_mode=TaskMode.AUTO,
                task_status=TaskStatus.NOT_STARTED, # Default
                baseline_cost=est_cost,
                scheduled_duration=lt.get("duration_days", 1),
                wbs_code=lt.get("legacy_wbs_code", ""),
                predecessors=[]
            )
            
            # Dates
            if lt.get("start_date"):
                # Handle various formats or assume ISO
                try:
                    new_task.scheduled_start = datetime.fromisoformat(lt["start_date"]).date()
                except:
                    pass
            
            new_tasks.append(new_task)
            total_migrated += 1
            migrated_total_cost += est_cost
            
        except Exception as e:
            logger.error(f"Failed to migrate legacy task {lt.get('_id')}: {str(e)}")
            total_failed += 1
            task_results.append(MigrationTaskResult(
                legacy_id=str(lt.get("_id", "unknown")),
                new_task_id=None,
                external_ref_id=None,
                status="failed",
                error_message=str(e)
            ))

    if not dry_run and new_tasks:
        # Perform bulk insert
        converted_tasks = [t.model_dump(by_alias=True, exclude={"id"}) for t in new_tasks]
        result = await db.project_schedules.insert_many(converted_tasks)
        
        # Populate result IDs
        for i, tid in enumerate(result.inserted_ids):
            task_results.append(MigrationTaskResult(
                legacy_id=new_tasks[i].external_ref_id,
                new_task_id=str(tid),
                external_ref_id=new_tasks[i].external_ref_id,
                status="success"
            ))

    report = MigrationReport(
        project_id=project_id,
        migration_run_at=datetime.now(timezone.utc),
        total_legacy_tasks=total_legacy_tasks,
        total_migrated=total_migrated,
        total_skipped=total_legacy_tasks - total_migrated - total_failed,
        total_failed=total_failed,
        legacy_total_estimated_cost=legacy_total_cost,
        migrated_total_baseline_cost=migrated_total_cost,
        cost_variance=legacy_total_cost - migrated_total_cost,
        task_results=task_results
    )
    
    return report

async def is_project_cutover(db: AsyncIOMotorDatabase, project_id: str) -> bool:
    """
    Cutover Hook: Checks if a project is in ACTIVE state (meaning scheduler is source of truth).
    """
    metadata = await db.project_metadata.find_one({"project_id": PyObjectId(project_id)})
    if not metadata:
        return False
    return metadata.get("system_state") == SystemState.ACTIVE

async def block_legacy_writes(db: AsyncIOMotorDatabase, project_id: str):
    """
    Enforces cutover by raising error if legacy modification is attempted on active projects.
    """
    if await is_project_cutover(db, project_id):
        raise Exception(f"Project {project_id} is ACTIVE in Scheduler. Legacy writes are blocked.")
