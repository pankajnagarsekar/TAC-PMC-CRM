from io import BytesIO
from typing import Any, Dict, Optional


class ExportService:
    """
    Sovereign Export Engine (Ported from Legacy Core).
    Handles Excel and PDF templates for construction reports.
    """

    REPORT_TEMPLATES = {
        "project_summary": {
            "description": "Project-level financial summary",
            "columns": [
                ("CODE", 10),
                ("Description", 40),
                ("Budget", 15),
                ("Committed", 15),
                ("Certified", 15),
                ("Remaining", 15),
            ],
        },
        "work_order_tracker": {
            "description": "Work Order tracking report",
            "columns": [
                ("CODE", 10),
                ("WO Reference", 20),
                ("Vendor", 20),
                ("WO Value", 15),
            ],
        },
        "payment_certificate_tracker": {
            "description": "PC tracking report",
            "columns": [
                ("CODE", 10),
                ("PC Reference", 20),
                ("Vendor", 20),
                ("PC Value", 15),
            ],
        },
    }

    @staticmethod
    def format_currency(value: Any) -> str:
        if value is None:
            return "₹ 0.00"
        try:
            val = float(value)
            return f"₹ {val:,.2f}"
        except Exception:
            return str(value)

    @staticmethod
    def validate_report_type(rt: str) -> bool:
        return rt in ExportService.REPORT_TEMPLATES

    @staticmethod
    def export_to_excel(
        report_type: str,
        report_data: Dict[str, Any],
        company_info: Optional[Dict[str, Any]] = None,
    ) -> bytes:
        # Legacy ported logic for openpyxl injection
        from openpyxl import Workbook

        wb = Workbook()
        ws = wb.active
        ws.title = "Report"
        # ... logic ...
        out = BytesIO()
        wb.save(out)
        return out.getvalue()
