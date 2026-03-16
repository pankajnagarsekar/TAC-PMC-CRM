from fastapi import APIRouter, Depends, HTTPException, Query, Response
from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from datetime import datetime
from io import BytesIO

from core.database import get_db
from core.export_service import ExportService
from core.reporting_service import ReportingService
from core.job_orchestrator import job_orchestrator
from auth import get_current_user
from permissions import PermissionChecker
from fastapi import BackgroundTasks

reporting_router = APIRouter(prefix="/api", tags=["Reporting"])

# ============================================
# REPORT GENERATION ENDPOINTS
# ============================================

@reporting_router.get("/projects/{project_id}/reports/{report_type}")
async def get_report(
    project_id: str,
    report_type: str,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Generate report data for specified type.
    Supported types: project_summary, work_order_tracker, payment_certificate_tracker, 
                    petty_cash_tracker, csa_report, weekly_progress, 15_days_progress, monthly_progress
    
    Returns: {title, rows, totals, metadata}
    """
    # Verify user has access to project
    permission_checker = PermissionChecker(db)
    user = await permission_checker.get_authenticated_user(current_user)
    await permission_checker.check_project_access(user, project_id)
    
    # Validate report type
    if not ExportService.validate_report_type(report_type):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid report type: {report_type}. Supported: {', '.join([r['type'] for r in ExportService.list_supported_reports()])}"
        )
    
    # Parse dates if provided
    start_dt = None
    end_dt = None
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format. Use ISO format (YYYY-MM-DD)")
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format. Use ISO format (YYYY-MM-DD)")
    
    # Generate report
    reporting_service = ReportingService(db)
    try:
        report_data = await reporting_service.generate_report(
            project_id=project_id,
            report_type=report_type,
            start_date=start_dt,
            end_date=end_dt,
        )
        return report_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")


# ============================================
# EXCEL EXPORT ENDPOINTS
# ============================================

@reporting_router.get("/projects/{project_id}/reports/{report_type}/export/excel")
async def export_report_excel(
    project_id: str,
    report_type: str,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    sync: bool = Query(False, description="Force synchronous export response"),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    background_tasks: BackgroundTasks = None,
):
    """
    Export report as Excel file (.xlsx)
    """
    # Verify permissions
    permission_checker = PermissionChecker(db)
    user = await permission_checker.get_authenticated_user(current_user)
    await permission_checker.check_project_access(user, project_id)
    
    if not ExportService.validate_report_type(report_type):
        raise HTTPException(status_code=400, detail=f"Invalid report type: {report_type}")
    
    # Generate report data
    reporting_service = ReportingService(db)
    parse_dates = lambda d: datetime.fromisoformat(d) if d else None
    
    report_data = await reporting_service.generate_report(
        project_id=project_id,
        report_type=report_type,
        start_date=parse_dates(start_date),
        end_date=parse_dates(end_date),
    )
    
    # Fetch company info for branding
    settings = await db.global_settings.find_one({})
    company_info = {
        "name": settings.get("company_name", "Financial Report") if settings else "Financial Report",
        "gstin": settings.get("gstin", "") if settings else "",
    }
    
    # Prepare task data
    # In a real heavy job, we'd pass IDs only and fetch data in the worker
    # But for this abstraction, we'll follow the orchestrator pattern
    
    if not sync:
        celery_export_task = None
        try:
            from tasks import export_report_task as celery_export_task
        except Exception:
            # Celery is optional in local/dev mode
            celery_export_task = None

        job_id = job_orchestrator.enqueue(
            ExportService.export_to_excel,
            project_id,
            report_type,
            celery_task=celery_export_task,
            background_tasks=background_tasks
        )
        
        if not job_id.startswith("local_"):
            return {"job_id": job_id, "status": "accepted"}

    # Existing synchronous logic for non-celery mode
    try:
        excel_bytes = ExportService.export_to_excel(
            report_type=report_type,
            report_data=report_data,
            company_info=company_info,
            include_terms=True,
            terms_text=settings.get("default_terms", "") if settings else "",
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    
    filename = f"{report_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ============================================
# PDF EXPORT ENDPOINTS
# ============================================

@reporting_router.get("/projects/{project_id}/reports/{report_type}/export/pdf")
async def export_report_pdf(
    project_id: str,
    report_type: str,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Export report as PDF file
    """
    # Verify permissions
    permission_checker = PermissionChecker(db)
    user = await permission_checker.get_authenticated_user(current_user)
    await permission_checker.check_project_access(user, project_id)
    
    if not ExportService.validate_report_type(report_type):
        raise HTTPException(status_code=400, detail=f"Invalid report type: {report_type}")
    
    # Generate report data
    reporting_service = ReportingService(db)
    parse_dates = lambda d: datetime.fromisoformat(d) if d else None
    
    report_data = await reporting_service.generate_report(
        project_id=project_id,
        report_type=report_type,
        start_date=parse_dates(start_date),
        end_date=parse_dates(end_date),
    )
    
    # Fetch company info
    settings = await db.global_settings.find_one({})
    company_info = {
        "name": settings.get("company_name", "Financial Report") if settings else "Financial Report",
        "address": settings.get("address", "") if settings else "",
    }
    
    # Generate PDF
    try:
        pdf_bytes = ExportService.export_to_pdf(
            report_type=report_type,
            report_data=report_data,
            company_info=company_info,
            include_terms=True,
            terms_text=settings.get("default_terms", "") if settings else "",
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    
    filename = f"{report_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ============================================
# STANDALONE WORK ORDER EXPORT
# ============================================

@reporting_router.get("/work-orders/{wo_id}/export/pdf")
async def export_work_order_pdf(
    wo_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Export single Work Order as PDF
    """
    permission_checker = PermissionChecker(db)
    user = await permission_checker.get_authenticated_user(current_user)
    
    # Fetch WO
    wo = await db.work_orders.find_one({"_id": ObjectId(wo_id)})
    if not wo:
        raise HTTPException(status_code=404, detail="Work Order not found")
    
    await permission_checker.check_project_access(user, wo["project_id"])
    
    # Build report data from WO
    report_data = {
        "rows": [
            [
                wo.get("wo_ref", ""),
                f"{len(wo.get('line_items', []))} items",
                float(wo.get("grand_total", 0)),
                wo.get("status", "Draft"),
                wo.get("created_at", datetime.utcnow()).strftime("%Y-%m-%d"),
            ]
        ]
    }
    
    settings = await db.global_settings.find_one({})
    company_info = {"name": settings.get("company_name", "") if settings else ""}
    
    try:
        pdf_bytes = ExportService.export_to_pdf(
            report_type="work_order_tracker",
            report_data=report_data,
            company_info=company_info,
            include_terms=False,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    
    filename = f"WO_{wo.get('wo_ref', wo_id)}_{datetime.now().strftime('%Y%m%d')}.pdf"
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ============================================
# STANDALONE PAYMENT CERTIFICATE EXPORT
# ============================================

@reporting_router.get("/payment-certificates/{pc_id}/export/pdf")
async def export_payment_certificate_pdf(
    pc_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Export single Payment Certificate as PDF
    """
    permission_checker = PermissionChecker(db)
    user = await permission_checker.get_authenticated_user(current_user)
    
    # Fetch PC
    pc = await db.payment_certificates.find_one({"_id": ObjectId(pc_id)})
    if not pc:
        raise HTTPException(status_code=404, detail="Payment Certificate not found")
    
    await permission_checker.check_project_access(user, pc["project_id"])
    
    # Build report data from PC
    report_data = {
        "rows": [
            [
                pc.get("pc_ref", ""),
                f"{len(pc.get('line_items', []))} items",
                float(pc.get("grand_total", 0)),
                pc.get("status", "Draft"),
                pc.get("created_at", datetime.utcnow()).strftime("%Y-%m-%d"),
            ]
        ]
    }
    
    settings = await db.global_settings.find_one({})
    company_info = {"name": settings.get("company_name", "") if settings else ""}
    
    try:
        pdf_bytes = ExportService.export_to_pdf(
            report_type="payment_certificate_tracker",
            report_data=report_data,
            company_info=company_info,
            include_terms=False,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    
    filename = f"PC_{pc.get('pc_ref', pc_id)}_{datetime.now().strftime('%Y%m%d')}.pdf"
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@reporting_router.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    """
    Check the status of a background job.
    """
    if job_id.startswith("local_"):
        return {"job_id": job_id, "status": "COMPLETED"}
    
    from core.celery_app import celery_app
    result = celery_app.AsyncResult(job_id)
    return {
        "job_id": job_id,
        "status": result.status,
        "ready": result.ready(),
        "result": str(result.result) if result.ready() else None
    }


# ============================================
# LEGACY ENDPOINTS (DEPRECATED - For backward compatibility)
# ============================================

def serialize_doc(doc):
    """Helper to serialize MongoDB docs"""
    if doc is None:
        return None
    doc["_id"] = str(doc["_id"])
    for key, value in doc.items():
        if isinstance(value, datetime):
            doc[key] = value.isoformat()
    return doc


@reporting_router.get("/projects/{project_id}/summary")
async def get_project_summary(
    project_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    DEPRECATED: Use /api/projects/{project_id}/reports/project_summary instead.
    Get high-level summary for project reports and dashboards.
    """
    project = await db.projects.find_one({"_id": ObjectId(project_id)})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    financials = await db.project_category_budgets.find({"project_id": project_id}).to_list(length=100)
    
    total_budget = sum(f.get("original_budget", 0) for f in financials)
    total_committed = sum(f.get("committed_value", 0) for f in financials)
    
    recent_dprs = await db.dprs.find({"project_id": project_id}).sort("date", -1).limit(5).to_list(length=5)

    return {
        "project_name": project.get("project_name"),
        "completion_percentage": project.get("completion_percentage", 0),
        "total_budget": total_budget,
        "total_committed": total_committed,
        "balance_remaining": total_budget - total_committed,
        "recent_dprs": [serialize_doc(d) for d in recent_dprs]
    }

