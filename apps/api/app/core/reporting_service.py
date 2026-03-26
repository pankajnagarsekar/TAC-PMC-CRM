from typing import Dict, Any, List, Optional, Literal
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

ReportType = Literal["project_summary", "work_order_tracker", "payment_certificate_tracker", "petty_cash_tracker"]

class ReportingService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    async def generate_report(self, project_id: str, report_type: ReportType, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> Dict[str, Any]:
        return {"rows": [], "totals": {}}

    def _to_decimal(self, value: Any) -> Decimal:
        if isinstance(value, Decimal): return value
        try: return Decimal(str(value))
        except: return Decimal("0")
