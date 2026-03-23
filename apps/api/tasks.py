import asyncio
import logging
from core.celery_app import celery_app
from core.database import db_manager, get_db
from core.reporting_service import ReportingService
from core.export_service import ExportService

logger = logging.getLogger(__name__)

def run_async(coro):
    """Utility to run async coroutines in a synchronous Celery worker."""
    loop = asyncio.get_event_loop()
    if loop.is_running():
        # This shouldn't happen in a standard Celery worker process
        new_loop = asyncio.new_event_loop()
        return new_loop.run_until_complete(coro)
    return loop.run_until_complete(coro)

@celery_app.task(name="tasks.generate_heavy_report")
def generate_heavy_report(project_id, report_type, start_date=None, end_date=None):
    """Celery task for heavy report generation."""
    logger.info(f"Starting heavy report task for project {project_id}, type {report_type}")
    
    async def _task():
        db = await get_db()
        reporting_service = ReportingService(db)
        # For now, we just materialize it as an example of heavy lifting
        await reporting_service.materialize_report(project_id, report_type)
        return f"Report {report_type} materialized for project {project_id}"

    return run_async(_task())

@celery_app.task(name="tasks.export_report_task")
def export_report_task(project_id, report_type, format="excel"):
    """Celery task for report export."""
    logger.info(f"Starting export task for project {project_id}, type {report_type}, format {format}")
    
    async def _task():
        db = await get_db()
        export_service = ExportService(db)
        if format == "excel":
            return await export_service.export_to_excel(project_id, report_type)
        else:
            return f"Format {format} not implemented yet for async export"

    return run_async(_task())

@celery_app.task(name="tasks.refresh_all_reports")
def refresh_all_reports():
    """Scheduled task to refresh all materialized reports."""
    logger.info("Starting scheduled refresh of all reports")
    
    async def _task():
        db = await get_db()
        reporting_service = ReportingService(db)
        
        # We fetch all project IDs
        projects = await db.projects.find({}, {"_id": 1}).to_list(None)
        for proj in projects:
            proj_id = str(proj["_id"])
            # Materialize project summary as a hook example
            await reporting_service.materialize_report(proj_id, "project_summary")
            
        return f"Refreshed reports for {len(projects)} projects"

    return run_async(_task())


@celery_app.task(name="tasks.generate_daily_ai_summaries")
def generate_daily_ai_summaries():
    """
    Scheduled daily task: generate AI project summaries for all active projects.
    Runs at midnight UTC via beat_schedule.
    Uses upsert so re-running on the same day is safe (idempotent).
    """
    logger.info("Starting daily AI project summary generation")

    async def _task():
        db = await get_db()
        from core.ai_summary_service import AISummaryService
        import os
        api_key = os.environ.get("OPENAI_API_KEY")
        service = AISummaryService(db=db, api_key=api_key)

        projects = await db.projects.find(
            {"status": "active"}, {"_id": 1, "project_id": 1, "organisation_id": 1}
        ).to_list(None)

        success_count = 0
        for proj in projects:
            try:
                pid = proj.get("project_id") or str(proj["_id"])
                org_id = proj.get("organisation_id", "")
                await service.generate_and_store(
                    project_id=pid,
                    organisation_id=org_id,
                    triggered_by="scheduler"
                )
                success_count += 1
            except Exception as e:
                logger.error(f"[AI:SUMMARY] Failed for project {proj.get('project_id')}: {e}")

        return f"AI summaries generated for {success_count}/{len(projects)} projects"

    return run_async(_task())

