from typing import Optional, Dict, Any, List
from datetime import datetime
from fastapi import HTTPException

from app.core.reporting_service import ReportingService as CoreReportingService
from app.core.export_service import ExportService

class ReportingService:
    def __init__(self, db, permission_checker):
        self.db = db
        self.permission_checker = permission_checker
        self.core_service = CoreReportingService(db)

    async def get_report(self, user: dict, project_id: str, report_type: str, start_date: Optional[str], end_date: Optional[str]) -> Dict[str, Any]:
        await self.permission_checker.check_project_access(user, project_id)
        
        if not ExportService.validate_report_type(report_type):
            raise HTTPException(status_code=400, detail="Invalid report type.")

        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None

        return await self.core_service.generate_report(
            project_id=project_id,
            report_type=report_type,
            start_date=start_dt,
            end_date=end_dt
        )
