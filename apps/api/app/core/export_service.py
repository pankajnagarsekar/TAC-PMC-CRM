from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from decimal import Decimal
from io import BytesIO
import os

class ExportService:
    REPORT_TEMPLATES = {
        "project_summary": {"description": "Project-level financial summary", "columns": [("CODE", 10), ("Description", 40), ("Budget", 15), ("Committed", 15), ("Certified", 15), ("Remaining", 15), ("Deadline", 15)]},
        "work_order_tracker": {"description": "Work Order tracking report", "columns": [("CODE", 10), ("WO Reference", 20), ("Vendor", 20), ("WO Value", 15), ("Retention Value", 15), ("Start Date", 15), ("End Date", 15)]},
        "payment_certificate_tracker": {"description": "Payment Certificate tracking report", "columns": [("CODE", 10), ("PC Reference", 20), ("Vendor", 20), ("PC Value", 15), ("PC Date", 15), ("Payment Value", 15), ("Payment Date", 15)]},
        "petty_cash_tracker": {"description": "Petty Cash and OVH transaction report", "columns": [("Date", 15), ("PC Refn", 20), ("PC Value", 15), ("Bill / Invoice", 30)]}
    }

    @staticmethod
    def validate_report_type(report_type: str) -> bool:
        return report_type in ExportService.REPORT_TEMPLATES

    @staticmethod
    def format_currency(value: Any) -> str:
        return f"₹ {float(value):,.2f}" if value else "₹ 0.00"
