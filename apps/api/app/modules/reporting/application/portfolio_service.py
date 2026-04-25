import logging
from datetime import datetime, timezone
from typing import Any, Dict, List
from bson import ObjectId
from app.modules.shared.domain.financial_engine import FinancialEngine
from app.modules.project.infrastructure.repository import ProjectRepository

logger = logging.getLogger(__name__)

class PortfolioService:
    """
    Service for cross-project portfolio analytics.
    """

    def __init__(self, db):
        self.db = db
        self.project_repo = ProjectRepository(db)

    async def get_summary(self, organisation_id: str) -> Dict[str, Any]:
        """
        Aggregate financial and task KPIs across all projects in the organisation.
        """
        # 1. Fetch all projects
        projects = await self.project_repo.list({"organisation_id": organisation_id})
        project_ids = [str(p["_id"]) for p in projects]

        # 2. Fetch Master Financial States
        master_states = await self.db.financial_state.find({
            "project_id": {"$in": project_ids},
            "category_id": "MASTER"
        }).to_list(length=1000)

        total_budget = 0.0
        net_committed = 0.0
        net_certified = 0.0

        for s in master_states:
            total_budget += float(FinancialEngine.to_decimal(s.get("original_budget", 0)))
            net_committed += float(FinancialEngine.to_decimal(s.get("committed_value", 0)))
            net_certified += float(FinancialEngine.to_decimal(s.get("certified_value", 0)))

        # 3. Count Overdue Tasks across all projects
        now = datetime.now(timezone.utc).isoformat()
        overdue_tasks_count = await self.db.tasks.count_documents({
            "organisation_id": organisation_id,
            "status": {"$in": ["Open", "In Progress"]},
            "deadline": {"$lt": now}
        })

        # 4. Exposure Metrics (Phase 7 fix)
        critical_projects = await self.db.projects.count_documents({
            "organisation_id": organisation_id,
            "status": "critical"
        })

        return {
            "total_projects": len(projects),
            "total_budget": total_budget,
            "net_committed": net_committed,
            "net_certified": net_certified,
            "overdue_tasks": overdue_tasks_count,
            "exposure_metrics": {
                "critical_project_count": critical_projects,
                "at_risk_milestones": overdue_tasks_count  # Using overdue as at-risk for now
            },
            "updated_at": datetime.now(timezone.utc).isoformat() + "Z"
        }

    async def get_resource_heatmap(self, organisation_id: str) -> List[Dict[str, Any]]:
        """
        Returns task distribution and utilization heatmap across resources.
        """
        pipeline = [
            {"$match": {"organisation_id": organisation_id, "status": {"$ne": "Closed"}}},
            {
                "$group": {
                    "_id": "$assigned_to_name",
                    "total_tasks": {"$sum": 1},
                    "in_progress": {
                        "$sum": {
                            "$cond": [{"$eq": ["$status", "In Progress"]}, 1, 0]
                        }
                    },
                    "completed": {
                        "$sum": {
                            "$cond": [{"$eq": ["$status", "Completed"]}, 1, 0]
                        }
                    },
                    "overdue": {
                        "$sum": {
                            "$cond": [
                                {
                                    "$and": [
                                        {"$in": ["$status", ["Open", "In Progress"]]},
                                        {"$lt": ["$deadline", datetime.now(timezone.utc).isoformat()]}
                                    ]
                                },
                                1,
                                0
                            ]
                        }
                    }
                }
            },
            {"$sort": {"total_tasks": -1}}
        ]

        results = await self.db.tasks.aggregate(pipeline).to_list(length=100)
        
        return [
            {
                "resource_name": r["_id"] or "Unassigned",
                "total_tasks": r["total_tasks"],
                "in_progress": r["in_progress"],
                "completed": r["completed"],
                "overdue": r["overdue"],
                "utilization_score": round((r["in_progress"] + r["overdue"] * 1.5) / 10, 2)
            }
            for r in results
        ]

    async def get_milestones(self, organisation_id: str) -> List[Dict[str, Any]]:
        """
        Retrieves upcoming and recently completed milestones across all projects.
        """
        # Fetch projects for name mapping
        projects = await self.project_repo.list({"organisation_id": organisation_id})
        project_map = {str(p["_id"]): (p.get("project_name") or p.get("name") or "Unknown") for p in projects}

        # Query tasks marked as milestones
        milestones = await self.db.tasks.find({
            "organisation_id": organisation_id,
            "is_milestone": True
        }).sort("deadline", 1).to_list(length=50)

        results = []
        for m in milestones:
            results.append({
                "task_id": str(m["_id"]),
                "project_id": m.get("project_id"),
                "project_name": project_map.get(m.get("project_id"), "Unknown"),
                "task_description": m.get("task_description"),
                "deadline": m.get("deadline"),
                "status": m.get("status"),
                "percent_complete": m.get("percent_complete", 0),
                "is_overdue": m.get("status") in ["Open", "In Progress"] and m.get("deadline") < datetime.now(timezone.utc).isoformat() if m.get("deadline") else False
            })

        return results
