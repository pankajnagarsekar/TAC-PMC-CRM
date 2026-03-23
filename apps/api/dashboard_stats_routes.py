from fastapi import APIRouter, HTTPException, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from core.database import get_db
from auth import get_current_user
from permissions import PermissionChecker
from datetime import datetime, timezone
import logging
from typing import Dict, Any, List
from decimal import Decimal
from bson import Decimal128

logger = logging.getLogger(__name__)

dashboard_stats_router = APIRouter(prefix="/api/v2/projects", tags=["Dashboard Statistics"])

def parse_date(date_str: str) -> datetime:
    """Parses DD-MM-YY, DD/MM/YYYY, or YYYY-MM-DD to datetime."""
    if not date_str:
        return datetime.max.replace(tzinfo=timezone.utc)
    
    # Handle possible variations in separator
    date_str = date_str.replace("/", "-")
    
    for fmt in ("%d-%m-%y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    
    # Fallback: try isoformat if provided
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except ValueError:
        logger.warning(f"Failed to parse date string: {date_str}")
        return datetime.max.replace(tzinfo=timezone.utc)

def to_decimal(value: Any) -> Decimal:
    """Safely converts various types to Decimal for fixed-point arithmetic."""
    if value is None:
        return Decimal("0.0")
    if isinstance(value, Decimal128):
        return value.to_decimal()
    if isinstance(value, (int, float, str)):
        try:
            # Convert float to str first to avoid precision issues
            return Decimal(str(value))
        except:
            return Decimal("0.0")
    return Decimal("0.0")

@dashboard_stats_router.get("/{project_id}/dashboard-stats")
async def get_dashboard_stats(
    project_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Returns aggregated statistics for the dashboard using spec-aligned fixed-point arithmetic.
    """
    checker = PermissionChecker(db)
    user = await checker.get_authenticated_user(current_user)
    await checker.check_project_access(user, project_id)

    # 1. Project Overview & Financial Totals
    total_phases = await db.project_category_budgets.count_documents({"project_id": project_id})
    active_items_count = await db.work_orders.count_documents({
        "project_id": project_id, 
        "status": {"$in": ["Pending", "Draft"]}
    })
    
    # Calculate Project-Wide Totals
    budgets = await db.project_category_budgets.find({"project_id": project_id}).to_list(length=500)
    financials = await db.financial_state.find({"project_id": project_id}).to_list(length=500)
    fin_map = {str(f["category_id"]): f for f in financials}
    
    master_budget = Decimal("0.0")
    total_committed = Decimal("0.0")
    
    for b in budgets:
        cid = str(b.get("category_id"))
        master_budget += to_decimal(b.get("original_budget"))
        total_committed += to_decimal(fin_map.get(cid, {}).get("committed_value"))

    # 2. Overdue Milestones & Schedule Metrics
    schedule = await db.project_schedules.find_one({"project_id": project_id})
    overdue_milestones = 0
    critical_path_status = "ON TRACK"
    variance = Decimal("0.0")
    
    now = datetime.now(timezone.utc)
    
    if schedule and "tasks" in schedule:
        tasks = schedule["tasks"]
        total_pv = Decimal("0.0")  # Planned Value
        total_ev = Decimal("0.0")  # Earned Value
        
        for t in tasks:
            is_milestone = t.get("isMilestone") or t.get("is_milestone") or t.get("duration") == 0
            finish_date = parse_date(t.get("finish"))
            progress_val = t.get("percentComplete") or t.get("progress") or 0
            progress = Decimal(str(progress_val)) / Decimal("100.0")
            is_critical = t.get("is_critical") or t.get("isCritical") or False
            cost = to_decimal(t.get("cost"))
            
            # Milestone Check
            if is_milestone and finish_date < now and progress_val < 100:
                overdue_milestones += 1
            
            # EVA
            total_pv += cost
            total_ev += (cost * progress)
            
            if is_critical and progress < Decimal("1.0") and finish_date < now:
                critical_path_status = "DELAYED"

        if total_pv > Decimal("0.0"):
            variance = ((total_ev - total_pv) / total_pv) * Decimal("100.0")

    # 3. Project Log & Compliance
    open_tasks = active_items_count
    resolved_tasks = await db.work_orders.count_documents({
        "project_id": project_id, 
        "status": {"$in": ["Closed", "Completed"]}
    })
    
    # Check if a DPR was submitted in the last 24 hours
    yesterday = now.replace(hour=0, minute=0, second=0, microsecond=0)
    dpr_recent = await db.dpr.count_documents({
        "project_id": project_id,
        "created_at": {"$gte": yesterday}
    })
    
    total_log_tasks = open_tasks + resolved_tasks
    compliance_rate = Decimal("100.0")
    if total_log_tasks > 0:
        compliance_rate = (Decimal(str(resolved_tasks)) / Decimal(str(total_log_tasks))) * Decimal("100.0")
    
    # Adjust compliance slightly if DPR is missing (penalty for lack of reporting)
    if dpr_recent == 0 and compliance_rate > Decimal("10"):
        compliance_rate -= Decimal("5.0")

    # 4. Task Manager - Latest 3 Actionable Items
    task_manager_items = []
    # Fetch Pending Work Orders
    async for wo in db.work_orders.find(
        {"project_id": project_id, "status": {"$in": ["Pending", "Draft"]}},
        sort=[("updated_at", -1)],
        limit=3
    ):
        grand_total = to_decimal(wo.get("grand_total"))
        priority = "Routine"
        if grand_total > Decimal("100000"): priority = "Financial"
        
        task_manager_items.append({
            "id": wo.get("wo_ref") or f"WO-{str(wo['_id'])[:6]}",
            "label": f"Approve Work Order",
            "priority": priority,
            "color": "text-primary" if priority == "Financial" else "text-zinc-400"
        })

    # If we have space, add a notice about RFIs (Feature Coming Soon)
    if len(task_manager_items) < 3:
        task_manager_items.append({
            "id": "BETA",
            "label": "RFI Management coming soon",
            "priority": "System",
            "color": "text-zinc-500"
        })

    return {
        "project_id": project_id,
        "overview": {
            "total_phases": total_phases,
            "active_items": active_items_count,
            "overdue_milestones": overdue_milestones,
            "master_budget": float(master_budget),
            "total_committed": float(total_committed)
        },
        "schedule_status": {
            "variance": float(round(variance, 1)),
            "critical_path_status": critical_path_status
        },
        "task_log": {
            "open_tasks": open_tasks,
            "resolved_tasks": resolved_tasks,
            "compliance_rate": float(round(compliance_rate, 1))
        },
        "task_manager": task_manager_items
    }
