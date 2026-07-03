from typing import Any, Dict, List, Optional

import time
from fastapi import APIRouter, Depends, Query, status
from datetime import datetime
import logging


from app.core.dependencies import (
    get_authenticated_user,
    get_client_service,
    get_project_service,
    get_scheduler_service,
    get_ai_service,
    get_reporting_service,
    get_financial_service,
    verify_nonce,
)
from app.modules.financial.application.financial_service import FinancialService
from app.modules.reporting.application.reporting_service import ReportingService

from app.modules.reporting.application.ai_service import AIService
from app.modules.shared.domain.schemas import GenericResponse

from ..application.client_service import ClientService
from ..application.project_service import ProjectService
from ..application.scheduler_service import SchedulerService
from ..schemas.dto import (
    Client,
    ClientCreate,
    ClientUpdate,
    Project,
    ProjectBudgetCreate,
    ProjectCreate,
    ProjectUpdate,
    ProjectCalendarDTO,
    EVMBaselineInitDTO,
)
from ..schemas.scheduler import (
    ScheduleCalculateRequest,
    ScheduleChangeRequest,
    ScheduleResponse,
    ScheduleSaveRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# --- PROJECT ENDPOINTS ---


@router.get(
    "/projects/", response_model=GenericResponse[List[Project]], tags=["Projects"]
)
async def list_projects(
    user: dict = Depends(get_authenticated_user),
    project_service: ProjectService = Depends(get_project_service),
):
    """Fetch all projects accessible to the user (Point 17, 115)."""
    projects = await project_service.list_projects(user)
    return GenericResponse(data=projects)


@router.post(
    "/projects/",
    response_model=GenericResponse[Project],
    status_code=status.HTTP_201_CREATED,
    tags=["Projects"],
)
async def create_project(
    project_data: ProjectCreate,
    user: dict = Depends(get_authenticated_user),
    project_service: ProjectService = Depends(get_project_service),
    nonce: str = Depends(verify_nonce),
):
    """Authoritative project creation (Point 75)."""
    project = await project_service.create_project(user, project_data)
    return GenericResponse(data=project, message="Project created successfully")


@router.get(
    "/projects/{project_id}", response_model=GenericResponse[Project], tags=["Projects"]
)
async def get_project(
    project_id: str,
    user: dict = Depends(get_authenticated_user),
    project_service: ProjectService = Depends(get_project_service),
):
    """Fetch details for a single project."""
    project = await project_service.get_project(user, project_id)
    return GenericResponse(data=project)


@router.put(
    "/projects/{project_id}", response_model=GenericResponse[Project], tags=["Projects"]
)
async def update_project(
    project_id: str,
    project_update: ProjectUpdate,
    user: dict = Depends(get_authenticated_user),
    project_service: ProjectService = Depends(get_project_service),
):
    """Update project metadata."""
    project = await project_service.update_project(user, project_id, project_update)
    return GenericResponse(data=project, message="Project updated successfully")


@router.post(
    "/projects/{project_id}/initialize-budgets",
    response_model=GenericResponse[dict],
    tags=["Projects"],
)
async def initialize_project_budgets(
    project_id: str,
    user: dict = Depends(get_authenticated_user),
    project_service: ProjectService = Depends(get_project_service),
):
    """Seed project budgets from organization cost codes."""
    await project_service.initialize_project_budgets(user, project_id)
    return GenericResponse(data={}, message="Project budgets initialized")


@router.delete(
    "/projects/{project_id}", response_model=GenericResponse[dict], tags=["Projects"]
)
async def delete_project(
    project_id: str,
    user: dict = Depends(get_authenticated_user),
    project_service: ProjectService = Depends(get_project_service),
):
    """Soft-delete a project (authoritative Point 87)."""
    result = await project_service.delete_project(user, project_id)
    return GenericResponse(data=result, message="Project deleted successfully")


@router.post(
    "/projects/{project_id}/evm-baseline",
    response_model=GenericResponse[Project],
    tags=["Projects"],
)
async def initialize_evm_baseline(
    project_id: str,
    baseline_data: EVMBaselineInitDTO,
    user: dict = Depends(get_authenticated_user),
    project_service: ProjectService = Depends(get_project_service),
):
    """Initialize EVM baseline for a project (NR-002)."""
    project = await project_service.initialize_evm_baseline(user, project_id, baseline_data)
    return GenericResponse(data=project, message="EVM Baseline initialized successfully")


@router.get(
    "/projects/{project_id}/evm-baseline",
    response_model=GenericResponse[Optional[Dict[str, Any]]],
    tags=["Projects"],
)
async def get_evm_baseline(
    project_id: str,
    user: dict = Depends(get_authenticated_user),
    project_service: ProjectService = Depends(get_project_service),
):
    """Retrieve the EVM baseline details if initialized (NR-002)."""
    project = await project_service.get_project(user, project_id)
    baseline = project.get("evm_baseline")
    return GenericResponse(data=baseline)


# --- CALENDAR ENDPOINTS ---


@router.get(
    "/projects/{project_id}/calendar",
    response_model=GenericResponse[ProjectCalendarDTO],
    tags=["Calendar"],
)
async def get_project_calendar(
    project_id: str,
    user: dict = Depends(get_authenticated_user),
    project_service: ProjectService = Depends(get_project_service),
):
    """Retrieve project-specific calendar settings."""
    calendar = await project_service.get_project_calendar(user, project_id)
    return GenericResponse(data=calendar)


@router.put(
    "/projects/{project_id}/calendar",
    response_model=GenericResponse[ProjectCalendarDTO],
    tags=["Calendar"],
)
async def update_project_calendar(
    project_id: str,
    calendar_data: ProjectCalendarDTO,
    user: dict = Depends(get_authenticated_user),
    project_service: ProjectService = Depends(get_project_service),
):
    """Update project-specific calendar settings (triggers recalculation)."""
    calendar = await project_service.update_project_calendar(user, project_id, calendar_data)
    return GenericResponse(data=calendar, message="Project calendar updated and schedule recalculated")


# --- CLIENT ENDPOINTS ---


@router.get("/clients/", response_model=GenericResponse[List[Client]], tags=["Clients"])
async def list_clients(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    user: dict = Depends(get_authenticated_user),
    client_service: ClientService = Depends(get_client_service),
):
    """List all clients within the organisation with pagination support."""
    try:
        if not user or not user.get("organisation_id"):
            logger.error(
                f"LIST_CLIENTS_AUTH_ERROR: Missing organisation_id for user "
                f"{user.get('user_id') if user else 'Unknown'}"
            )
            return GenericResponse(
                success=False,
                message="Authorization error: Missing organisation context",
                status_code=403
            )

        clients = await client_service.list_clients(user["organisation_id"], skip=skip, limit=limit)
        return GenericResponse(data=clients)
    except Exception as e:
        logger.error(f"LIST_CLIENTS_SYSTEM_FAULT: {str(e)}", exc_info=True)
        # BUG-001 Recovery: Ensure we always return a GenericResponse envelope
        from pydantic import ValidationError as PydanticValidationError
        error_msg = f"Internal server error in Client Registry: {str(e)}"
        if isinstance(e, PydanticValidationError):
            error_msg = f"Data integrity fault: Backend schema mismatch. Details: {str(e)}"

        return GenericResponse(
            success=False,
            message=error_msg,
            status_code=500
        )


@router.post(
    "/clients/",
    response_model=GenericResponse[Client],
    status_code=status.HTTP_201_CREATED,
    tags=["Clients"],
)
async def create_client(
    client_data: ClientCreate,
    user: dict = Depends(get_authenticated_user),
    client_service: ClientService = Depends(get_client_service),
):
    """Add a new client to the organisation."""
    client = await client_service.create_client(user, client_data)
    return GenericResponse(data=client, message="Client added successfully")


@router.put(
    "/clients/{client_id}",
    response_model=GenericResponse[Client],
    tags=["Clients"],
)
async def update_client(
    client_id: str,
    client_data: ClientUpdate,
    user: dict = Depends(get_authenticated_user),
    client_service: ClientService = Depends(get_client_service),
):
    """Update an existing client profile."""
    client = await client_service.update_client(user, client_id, client_data)
    return GenericResponse(data=client, message="Client updated successfully")


# --- BUDGET ENDPOINTS ---


@router.post(
    "/projects/{project_id}/budgets",
    response_model=GenericResponse[dict],
    tags=["Budgets"],
)
async def create_category_budget(
    project_id: str,
    budget_data: ProjectBudgetCreate,
    user: dict = Depends(get_authenticated_user),
    financial_service: FinancialService = Depends(get_financial_service),
):
    """Define budget for a specific category within a project."""
    budget = await financial_service.create_budget(
        user, project_id, budget_data.category_id, budget_data.original_budget
    )
    return GenericResponse(data=budget, message="Category budget created")


# --- SCHEDULER ENDPOINTS ---


@router.post(
    "/projects/{project_id}/calculate-schedule",
    response_model=GenericResponse[ScheduleResponse],
    tags=["Scheduler"],
)
async def calculate_schedule(
    project_id: str,
    request: ScheduleCalculateRequest,
    user: dict = Depends(get_authenticated_user),
    service: SchedulerService = Depends(get_scheduler_service),
):
    """Trigger schedule recalculation logic."""
    # Safety Check: request.tasks is already a list of dicts based on schema
    task_dicts = request.tasks
    logger.info(f"API_SCHEDULER_CALC: Project {project_id} - reconciling {len(task_dicts)} nodes")
    try:
        result = await service.calculate_schedule(
            project_id,
            [t.model_dump() for t in request.tasks],
            request.project_start or ""
        )
        return GenericResponse(data=result)
    except Exception as e:
        logger.error(f"ROUTE_CALC_FAIL: {str(e)}", exc_info=True)
        from fastapi import HTTPException
        from app.modules.shared.domain.exceptions import DomainError, NotFoundError
        if isinstance(e, NotFoundError):
            raise HTTPException(status_code=404, detail=str(e))
        elif isinstance(e, DomainError):
            raise HTTPException(status_code=400, detail=str(e))
        raise HTTPException(status_code=500, detail=f"Scheduler error: {str(e)}")


@router.post(
    "/scheduler/{project_id}/calculate",
    response_model=GenericResponse[ScheduleResponse],
    tags=["Scheduler"],
)
async def calculate_granular_schedule(
    project_id: str,
    request: ScheduleChangeRequest,
    user: dict = Depends(get_authenticated_user),
    service: SchedulerService = Depends(get_scheduler_service),
):
    """Trigger schedule recalculation for a specific task change (Point 103)."""
    start_time = time.time()
    # 1. Load current schedule state
    schedule = await service.load_schedule(project_id, user["organisation_id"])
    load_time = time.time() - start_time
    tasks = schedule.get("tasks", [])
    project_start = schedule.get("project_start") or datetime.now().strftime("%Y-%m-%d")

    # 2. Apply change to the specific task
    found = False
    for t in tasks:
        if t.get("task_id") == request.task_id:
            t.update(request.changes)
            found = True
            break

    if not found:
        # If it's a new task (draft), add it to the list
        new_task = request.changes
        if "task_id" not in new_task:
            new_task["task_id"] = request.task_id
        if "project_id" not in new_task:
            new_task["project_id"] = project_id
        tasks.append(new_task)

    apply_time = time.time() - (start_time + load_time)

    # 3. Recalculate
    try:
        result = await service.calculate_schedule(
            project_id, tasks, project_start
        )
        total_time = time.time() - start_time

        logger.info(
            f"PERF: scheduler_calculate | total={total_time:.3f}s | "
            f"load={load_time:.3f}s | apply={apply_time:.3f}s"
        )

        return GenericResponse(data=result)
    except Exception as e:
        logger.error(f"GRANULAR_CALC_FAILED: {str(e)}", exc_info=True)
        from fastapi import HTTPException
        from app.modules.shared.domain.exceptions import DomainError
        if isinstance(e, DomainError):
            raise HTTPException(status_code=400, detail=str(e))
        raise HTTPException(status_code=500, detail=f"Granular calculation error: {str(e)}")


@router.delete(
    "/projects/{project_id}/tasks/{task_id}",
    response_model=GenericResponse[dict],
    tags=["Scheduler"],
)
async def delete_task(
    project_id: str,
    task_id: str,
    user: dict = Depends(get_authenticated_user),
    service: SchedulerService = Depends(get_scheduler_service),
):
    """Permanently remove a task from the project schedule."""
    result = await service.delete_task(
        project_id, user["organisation_id"], task_id, user["user_id"]
    )
    return GenericResponse(data=result, message="Task deleted successfully")


@router.post(
    "/projects/{project_id}/tasks/bulk-delete",
    response_model=GenericResponse[dict],
    tags=["Scheduler"],
)
async def delete_tasks_bulk(
    project_id: str,
    task_ids: List[str],
    user: dict = Depends(get_authenticated_user),
    service: SchedulerService = Depends(get_scheduler_service),
):
    """Permanently remove multiple tasks from the project schedule."""
    result = await service.delete_tasks_bulk(
        project_id, user["organisation_id"], task_ids, user["user_id"]
    )
    return GenericResponse(data=result, message=f"Successfully deleted {result['count']} tasks")


@router.post(
    "/projects/{project_id}/save-schedule",
    response_model=GenericResponse[dict],
    tags=["Scheduler"],
)
async def save_schedule(
    project_id: str,
    request: ScheduleSaveRequest,
    user: dict = Depends(get_authenticated_user),
    service: SchedulerService = Depends(get_scheduler_service),
):
    """Persist calculated schedule to the database."""
    try:
        result = await service.save_schedule(
            project_id,
            user["organisation_id"],
            user["user_id"],
            request.model_dump(),
        )
        return GenericResponse(data=result, message="Schedule saved successfully")
    except Exception as e:
        logger.error(f"SAVE_SCHEDULE_FAILED: {str(e)}", exc_info=True)
        from fastapi import HTTPException
        from app.modules.shared.domain.exceptions import DomainError
        if isinstance(e, DomainError):
            raise HTTPException(status_code=400, detail=str(e))
        raise HTTPException(status_code=500, detail=f"Schedule save error: {str(e)}")


@router.get(
    "/projects/{project_id}/load-schedule",
    response_model=GenericResponse[Dict[str, Any]],
    tags=["Scheduler"],
)
async def load_schedule(
    project_id: str,
    user: dict = Depends(get_authenticated_user),
    service: SchedulerService = Depends(get_scheduler_service),
):
    """Retrieve the current project schedule."""
    result = await service.load_schedule(project_id, user["organisation_id"])
    return GenericResponse(data=result)


@router.get(
    "/projects/{project_id}/baseline/compare",
    response_model=GenericResponse[List[Dict[str, Any]]],
    tags=["Scheduler"],
)
async def compare_baselines(
    project_id: str,
    baseline_a: int = Query(1),
    baseline_b: int = Query(None),
    user: dict = Depends(get_authenticated_user),
    service: SchedulerService = Depends(get_scheduler_service),
):
    """Compare two baselines."""
    result = await service.compare_baselines(
        project_id, user["organisation_id"], baseline_a, baseline_b
    )
    return GenericResponse(data=result)


@router.post(
    "/projects/{project_id}/baseline/lock",
    response_model=GenericResponse[dict],
    tags=["Scheduler"],
)
async def lock_baseline(
    project_id: str,
    user: dict = Depends(get_authenticated_user),
    service: SchedulerService = Depends(get_scheduler_service),
):
    """Lock the current schedule as a baseline (immutable snapshot)."""
    try:
        result = await service.lock_baseline(
            project_id,
            user["organisation_id"],
            user["user_id"]
        )
        return GenericResponse(
            data=result,
            message=f"Baseline locked successfully - {result['locked_tasks']} tasks frozen"
        )
    except Exception as e:
        from fastapi import HTTPException
        from app.modules.shared.domain.exceptions import DomainError
        logger.error(f"BASELINE_LOCK_FAILED: {str(e)}", exc_info=True)
        if isinstance(e, DomainError):
            raise HTTPException(status_code=400, detail=str(e))
        raise HTTPException(status_code=500, detail=f"Baseline lock error: {str(e)}")


@router.post(
    "/projects/{project_id}/baseline/unlock",
    response_model=GenericResponse[dict],
    tags=["Scheduler"],
)
async def unlock_baseline(
    project_id: str,
    user: dict = Depends(get_authenticated_user),
    service: SchedulerService = Depends(get_scheduler_service),
):
    """Unlock a baseline to allow further modifications."""
    try:
        result = await service.unlock_baseline(
            project_id,
            user["organisation_id"],
            user["user_id"]
        )
        return GenericResponse(
            data=result,
            message=f"Baseline unlocked successfully - {result['unlocked_tasks']} tasks unfrozen"
        )
    except Exception as e:
        from fastapi import HTTPException
        from app.modules.shared.domain.exceptions import DomainError
        logger.error(f"BASELINE_UNLOCK_FAILED: {str(e)}", exc_info=True)
        if isinstance(e, DomainError):
            raise HTTPException(status_code=400, detail=str(e))
        raise HTTPException(status_code=500, detail=f"Baseline unlock error: {str(e)}")


@router.post(
    "/projects/{project_id}/export/pdf",
    tags=["Scheduler"],
)
async def trigger_scheduler_export_pdf(
    project_id: str,
    user: dict = Depends(get_authenticated_user),
):
    """Trigger background generation of scheduler PDF report."""
    # For now, we assume it's ready immediately
    return GenericResponse(data={"status": "READY", "message": "Export prepared"})


@router.get(
    "/projects/{project_id}/export/download",
    tags=["Scheduler"],
)
async def download_scheduler_export_pdf(
    project_id: str,
    user: dict = Depends(get_authenticated_user),
    reporting_service: ReportingService = Depends(get_reporting_service),
):
    """Download the generated scheduler PDF report."""
    from fastapi.responses import StreamingResponse
    import io
    from app.core.export_service import ExportService

    # We generate on-the-fly for now
    try:
        # Fixed: Use 'scheduler_gantt' template for scheduler export
        report_data = await reporting_service.get_report(
            user, project_id, "scheduler_gantt", None, None
        )
        pdf_bytes = ExportService.export_to_pdf_service("scheduler_gantt", report_data)

        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=Project_Schedule_{project_id}.pdf"}
        )
    except Exception as e:
        import traceback
        error_msg = f"EXPORT_FAILED: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        raise


@router.get(
    "/projects/{project_id}/export/status",
    tags=["Scheduler"],
)
async def get_scheduler_export_status(
    project_id: str,
    user: dict = Depends(get_authenticated_user),
):
    """Check status of background export job."""
    return GenericResponse(data={"status": "COMPLETED"})


@router.post(
    "/scheduler/{project_id}/migrate",
    response_model=GenericResponse[Dict[str, Any]],
    tags=["Scheduler"],
)
async def migrate_legacy_schedule(
    project_id: str,
    dry_run: bool = Query(True),
    user: dict = Depends(get_authenticated_user),
    service: SchedulerService = Depends(get_scheduler_service),
):
    """Migrate legacy payment schedule data to the new PPM scheduler (authoritative)."""
    # Note: SchedulerService needs to implement migrate_legacy_data
    # For now, we stub it or point to a script if available
    if hasattr(service, "migrate_legacy_data"):
        result = await service.migrate_legacy_data(
            project_id, user["organisation_id"], dry_run
        )
        return GenericResponse(data=result)

    return GenericResponse(
        success=False,
        message="Migration service not fully implemented in this context.",
    )


@router.post(
    "/projects/{project_id}/tasks/{task_id}/mom-extract",
    response_model=GenericResponse[Dict[str, Any]],
    tags=["Scheduler"],
)
async def task_mom_extract(
    project_id: str,
    task_id: str,
    data: Dict[str, Any],
    user: dict = Depends(get_authenticated_user),
    ai_service: AIService = Depends(get_ai_service),
):
    """Analyze meeting notes to extract action items and duration suggestions for a specific task."""
    result = await ai_service.extract_mom(
        user["organisation_id"], project_id, task_id, data.get("raw_notes", "")
    )
    return GenericResponse(data=result)
