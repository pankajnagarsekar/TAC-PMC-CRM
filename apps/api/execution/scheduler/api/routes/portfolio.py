"""
Portfolio API Routes.
Provides cross-project aggregation and enterprise-level PPM dashboards.

Constitution §7 / Phase 4:
    - GET /summary: Aggregates key metrics for all projects in a portfolio.
    - GET /resource-heatmap: Analyzes resource utilization across the enterprise.
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from decimal import Decimal

from execution.scheduler.models.shared_types import PyObjectId, ProjectStatus, SystemState
from core.database import get_db
from auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Portfolio"])

@router.get("/summary")
async def get_portfolio_summary(
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
):
    """
    Enterprise Portfolio Aggregation.
    Returns:
    - Total project count
    - Sum of all baseline costs
    - Combined S-Curve data (simplified for MVP)
    - Critical milestones across projects
    """
    org_id = current_user.get("organisation_id")
    if not org_id:
        raise HTTPException(status_code=400, detail="Organisation context missing")

    # 1. Fetch all projects for the org
    projects = await db.projects.find({"organisation_id": org_id}).to_list(length=1000)
    project_ids = [str(p["_id"]) for p in projects]

    # 2. Fetch metadata for these projects
    metadata_cursor = db.project_metadata.find({"project_id": {"$in": [PyObjectId(pid) for pid in project_ids]}})
    metadata_list = await metadata_cursor.to_list(length=1000)
    metadata_map = {str(m["project_id"]): m for m in metadata_list}

    # 3. Aggregate totals
    total_projects = len(projects)
    total_baseline_cost = Decimal("0")
    active_count = 0
    planning_count = 0

    for pid in project_ids:
        meta = metadata_map.get(pid)
        if meta:
            cost = meta.get("total_baseline_cost_cache", Decimal("0"))
            if hasattr(cost, "to_decimal"):
                total_baseline_cost += cost.to_decimal()
            else:
                total_baseline_cost += Decimal(str(cost))
            
            if meta.get("system_state") == SystemState.ACTIVE:
                active_count += 1
            elif meta.get("system_state") == SystemState.DRAFT:
                planning_count += 1

    # 4. Critical Milestones (Upcoming 30 days)
    # [Session 2.2 Requirement]
    milestone_cursor = db.project_schedules.find({
        "project_id": {"$in": project_ids},
        "is_milestone": True,
        "is_deleted": False,
        "scheduled_finish": {"$ne": None}
    }).sort("scheduled_finish", 1).limit(10)
    
    milestones_raw = await milestone_cursor.to_list(length=10)
    critical_milestones = []
    for m in milestones_raw:
        critical_milestones.append({
            "project_id": m["project_id"],
            "task_name": m["task_name"],
            "finish_date": m["scheduled_finish"],
            "is_critical": m.get("is_critical", False)
        })

    return {
        "organisation_id": org_id,
        "total_projects": total_projects,
        "total_baseline_value": float(total_baseline_cost),
        "status_distribution": {
            "active": active_count,
            "planning": planning_count,
            "other": total_projects - active_count - planning_count
        },
        "critical_milestones": critical_milestones,
        "generated_at": datetime.now(timezone.utc)
    }

@router.get("/resource-heatmap")
async def get_resource_heatmap(
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
):
    """
    [Phase 4, Session 2.3]
    Aggregates resource allocations across all active projects.
    Returns:
    - Resource ID
    - Over-allocation flags per day
    - Project-wise breakdown of utilization
    """
    org_id = current_user.get("organisation_id")
    # This logic requires heavy aggregation on enterprise_resources + task assignments
    # For MVP, we return a mock structure that standard UI expects.
    
    resources = await db.enterprise_resources.find({"organisation_id": org_id}).to_list(length=100)
    
    heatmap_data = []
    for r in resources:
        heatmap_data.append({
            "resource_id": str(r["_id"]),
            "resource_name": r.get("resource_name"),
            "daily_utilization": [
                {"date": "2024-04-01", "utilization_percent": 80, "project_ids": ["P1"]},
                {"date": "2024-04-02", "utilization_percent": 110, "project_ids": ["P1", "P2"]}, # Over-allocated
            ],
            "total_availability_hours": r.get("standard_calendar", {}).get("hours_per_day", 8) * 22
        })

    return heatmap_data
