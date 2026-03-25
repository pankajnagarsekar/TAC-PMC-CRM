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

    # 5. Financial Aggregations (Portfolio Wide)
    # [Session 2.4 Requirement]
    from execution.scheduler.pipelines.financial_aggregations import build_wo_value_pipeline, build_payment_value_pipeline
    
    total_wo_value = Decimal("0")
    total_payment_value = Decimal("0")
    
    for pid in project_ids:
        wo_pipeline = build_wo_value_pipeline(pid)
        wo_res = await db.project_schedules.aggregate(wo_pipeline).to_list(length=1000)
        total_wo_value += sum([Decimal(str(r.get("wo_value", "0"))) for r in wo_res])
        
        pc_pipeline = build_payment_value_pipeline(pid)
        pc_res = await db.project_schedules.aggregate(pc_pipeline).to_list(length=1000)
        total_payment_value += sum([Decimal(str(r.get("payment_value", "0"))) for r in pc_res])

    # 6. Risk Exposure (Critical Path)
    # [Session 2.5 Requirement]
    exposure_cursor = db.project_schedules.find({
        "project_id": {"$in": project_ids},
        "is_milestone": True,
        "is_deleted": False,
        "is_critical": True,
        "scheduled_finish": {"$ne": None}
    }).sort("scheduled_finish", 1)
    
    exposure_raw = await exposure_cursor.to_list(length=100)
    exposure_projects = set([m["project_id"] for m in exposure_raw])

    return {
        "organisation_id": org_id,
        "total_projects": total_projects,
        "total_baseline_value": float(total_baseline_cost),
        "total_work_order_value": float(total_wo_value),
        "total_payment_value": float(total_payment_value),
        "status_distribution": {
            "active": active_count,
            "planning": planning_count,
            "other": total_projects - active_count - planning_count
        },
        "critical_milestones": critical_milestones,
        "exposure_metrics": {
            "critical_project_count": len(exposure_projects),
            "at_risk_milestones": len(exposure_raw)
        },
        "generated_at": datetime.now(timezone.utc)
    }

from datetime import datetime, timezone, timedelta

@router.get("/resource-heatmap")
async def get_resource_heatmap(
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
):
    """
    [Phase 4, Session 2.3 Gap Fix]
    Aggregates resource allocations across all active projects.
    Returns daily utilization percentage for the next 30 days.
    """
    org_id = current_user.get("organisation_id")
    if not org_id:
         raise HTTPException(status_code=400, detail="Organisation context missing")

    # 1. Fetch resources
    resources = await db.enterprise_resources.find({"organisation_id": org_id}).to_list(length=200)
    
    # 2. Daily Range (Next 30 days)
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    days = [(today + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(30)]
    
    # 3. Fetch active tasks for the organisation
    projects = await db.projects.find({"organisation_id": org_id}).to_list(length=1000)
    project_ids = [str(p["_id"]) for p in projects]
    
    tasks = await db.project_schedules.find({
        "project_id": {"$in": project_ids},
        "assigned_resources": {"$exists": True, "$not": {"$size": 0}},
        "is_deleted": False
    }).to_list(length=10000)
    
    # 4. Aggregate load
    # For now, each task assignment consumes 100% of a daily slot. 
    # Future enhancement: lookup resource hours per task.
    load_map = {str(r["_id"]): {d: 0 for d in days} for r in resources}
    proj_map = {str(r["_id"]): {d: set() for d in days} for r in resources}
    
    for t in tasks:
        start = t.get("scheduled_start")
        finish = t.get("scheduled_finish")
        assigned = t.get("assigned_resources") or []
        
        if not start or not finish:
            continue
            
        for d in days:
            if start <= d <= finish:
                for rid in assigned:
                    rid_str = str(rid)
                    if rid_str in load_map:
                        load_map[rid_str][d] += 100
                        proj_map[rid_str][d].add(t["project_id"])

    # 5. Format results
    results = []
    for r in resources:
        rid = str(r["_id"])
        daily_util = []
        for d in days:
            daily_util.append({
                "date": d,
                "utilization_percent": load_map[rid][d],
                "project_ids": list(proj_map[rid][d])
            })
        
        results.append({
            "resource_id": rid,
            "resource_name": r.get("name") or "Unnamed Resource",
            "daily_utilization": daily_util,
            "total_availability_hours": r.get("max_capacity_per_day", 8) * 22
        })

    return results

@router.get("/milestones")
async def get_portfolio_milestones(
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
):
    """
    [Phase 4, Session 2.2 Gap Fix]
    Returns all milestones across all projects for the Cross-Project Portfolio Gantt.
    """
    org_id = current_user.get("organisation_id")
    if not org_id:
        raise HTTPException(status_code=400, detail="Organisation context missing")

    # 1. Fetch all projects to map IDs to Names
    projects = await db.projects.find({"organisation_id": org_id}).to_list(length=1000)
    project_map = {str(p["_id"]): p.get("project_name", "Unknown Project") for p in projects}
    project_ids = list(project_map.keys())

    # 2. Fetch all milestones
    milestone_cursor = db.project_schedules.find({
        "project_id": {"$in": project_ids},
        "is_milestone": True,
        "is_deleted": False,
        "scheduled_finish": {"$ne": None}
    }).sort([("project_id", 1), ("scheduled_finish", 1)])
    
    milestones_raw = await milestone_cursor.to_list(length=1000)
    
    results = []
    for m in milestones_raw:
        results.append({
            "task_id": str(m["_id"]),
            "project_id": m["project_id"],
            "project_name": project_map.get(m["project_id"]),
            "task_name": m["task_name"],
            "finish_date": m["scheduled_finish"],
            "is_critical": m.get("is_critical", False)
        })

    return results

@router.get("/dependencies")
async def get_portfolio_dependencies(
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
):
    """
    [Phase 4, Session 2.6 Requirement]
    Aggregates inter-project links for cross-project dependency visualization.
    """
    org_id = current_user.get("organisation_id")
    if not org_id:
        raise HTTPException(status_code=400, detail="Organisation context missing")

    # 1. Fetch project map
    projects = await db.projects.find({"organisation_id": org_id}).to_list(length=1000)
    project_map = {str(p["_id"]): p.get("project_name", "Unknown Project") for p in projects}
    project_ids = list(project_map.keys())

    # 2. Fetch tasks with external predecessors
    cursor = db.project_schedules.find({
        "project_id": {"$in": project_ids},
        "predecessors.is_external": True,
        "is_deleted": False
    })
    tasks_with_ext = await cursor.to_list(length=500)

    results = []
    for t in tasks_with_ext:
        for p in t.get("predecessors", []):
            if p.get("is_external") and p.get("project_id"):
                results.append({
                    "source_project_id": str(p["project_id"]),
                    "source_project_name": project_map.get(str(p["project_id"]), "Unknown"),
                    "source_task_id": str(p["task_id"]),
                    "target_project_id": str(t["project_id"]),
                    "target_project_name": project_map.get(str(t["project_id"]), "Unknown"),
                    "target_task_id": str(t["_id"]),
                    "dependency_type": p.get("type", "FS"),
                    "lag": p.get("lag_days", 0)
                })

    return results
