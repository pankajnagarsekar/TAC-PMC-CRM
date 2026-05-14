import logging
from bson import ObjectId
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Optional, AsyncGenerator
from app.core.config import settings
from app.modules.financial.infrastructure.repository import FinancialStateRepository
from app.modules.project.infrastructure.repository import (
    BudgetRepository,
    ProjectRepository,
)
from app.modules.shared.domain.exceptions import ValidationError
from app.modules.shared.domain.financial_engine import FinancialEngine

from ..infrastructure.repository import AISummaryRepository

logger = logging.getLogger(__name__)


class SummaryProvider:
    async def generate_summary(
        self, report_data: Dict[str, Any], project_name: str
    ) -> str:
        raise NotImplementedError


class MockSummaryProvider(SummaryProvider):
    async def generate_summary(
        self, report_data: Dict[str, Any], project_name: str
    ) -> str:
        # Smart mock based on data type
        if "status" in report_data:  # Schedule
            status = report_data.get("status", "unknown")
            at_risk = report_data.get("at_risk_tasks", 0)
            if at_risk > 0:
                return f"[MOCK] {project_name} is {status}. {at_risk} tasks at risk."
            return f"[MOCK] {project_name} on track."
        elif "total_budget" in report_data:  # Financial
            spent = report_data.get("total_spent", 0)
            budget = report_data.get("total_budget", 1)
            pct = round(spent / budget * 100, 1) if budget > 0 else 0
            return f"[MOCK] {project_name}: {pct}% of budget consumed."
        elif "average_utilization_pct" in report_data:  # Resources
            util = report_data.get("average_utilization_pct", 0)
            over = report_data.get("over_allocated_count", 0)
            if over > 0:
                msg = f"Team at {util}% utilization. {over} overallocated."
                return f"[MOCK] {project_name}: {msg}"
            return f"[MOCK] {project_name}: Team well-balanced."
        return f"[MOCK] {project_name} summary not available."


class EmergentSummaryProvider(SummaryProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def generate_summary(
        self, report_data: Dict[str, Any], project_name: str
    ) -> str:
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=self.api_key)
            prompt = self._build_prompt(report_data, project_name)
            res = await client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
            )
            return res.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"AI_GEN_FAIL: {e}")
            return await MockSummaryProvider().generate_summary(
                report_data, project_name
            )

    async def stream_summary(
        self, report_data: Dict[str, Any], project_name: str
    ) -> AsyncGenerator[str, None]:
        """Stream summary word-by-word via AsyncOpenAI."""
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=self.api_key)
            prompt = self._build_prompt(report_data, project_name)
            stream = await client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                stream=True,
            )

            buffer = ""
            async for event in stream:
                if event.choices[0].delta.content:
                    buffer += event.choices[0].delta.content
                    # Yield complete words only
                    words = buffer.split(" ")
                    for word in words[:-1]:
                        yield word + " "
                    buffer = words[-1]

            # Yield remaining buffer
            if buffer:
                yield buffer
        except Exception as e:
            logger.error(f"AI_STREAM_FAIL: {e}")
            # Fallback: yield mock summary word-by-word
            mock_text = await MockSummaryProvider().generate_summary(
                report_data, project_name
            )
            for word in mock_text.split():
                yield word + " "

    def _build_prompt(self, report_data, name):
        """Build a detailed prompt for AI summarization."""
        if "status" in report_data:  # Schedule health
            return (
                f"Provide a clear executive summary of schedule health for {name}:\n"
                f"- Status: {report_data.get('status', 'unknown')}\n"
                f"- On Track Tasks: {report_data.get('on_track_tasks', 0)}\n"
                f"- At Risk Tasks: {report_data.get('at_risk_tasks', 0)}\n"
                f"- Critical Path: {report_data.get('critical_path_days', 0)} days\n"
                "Explain if the project is on track or at risk, highlight critical path issues, "
                "and give a professional recommendation."
            )
        elif "total_budget" in report_data:  # Financial
            return (
                f"Provide a clear executive summary of financial status for {name}:\n"
                f"- Total Budget: ${report_data.get('total_budget', 0):.2f}\n"
                f"- Total Spent: ${report_data.get('total_spent', 0):.2f}\n"
                f"- Remaining: ${report_data.get('remaining_budget', 0):.2f}\n"
                f"- Burn Rate: {report_data.get('burn_rate_pct', 0)}%\n"
                "Assess if the budget is healthy, at risk, or overrun. "
                "Mentions any significant variance and next steps."
            )
        elif "average_utilization_pct" in report_data:  # Resources
            return (
                f"Provide a clear executive summary of resource allocation for {name}:\n"
                f"- Average Utilization: {report_data.get('average_utilization_pct', 0)}%\n"
                f"- Over-Allocated: {report_data.get('over_allocated_count', 0)} people\n"
                f"- Total Resources: {report_data.get('total_resources', 0)}\n"
                f"Assess if the team is healthy, busy, or overloaded. Highlight resource bottlenecks."
            )

        else:
            return f"Executive summary for {name}. Data: {report_data}"


class AISummaryService:
    def __init__(self, db, permission_checker, analytics_service=None):
        self.db = db
        self.permission_checker = permission_checker
        self.analytics_service = analytics_service
        self.ai_repo = AISummaryRepository(db)
        self.project_repo = ProjectRepository(db)
        self.budget_repo = BudgetRepository(db)
        self.fin_state_repo = FinancialStateRepository(db)

    async def _get_provider(self, organisation_id: str) -> SummaryProvider:
        """Fetch AI configuration and return appropriate provider."""
        from ...identity.infrastructure.repository import SettingsRepository
        repo = SettingsRepository(self.db)
        settings_doc = await repo.find_one({"organisation_id": organisation_id})

        api_key = settings.OPENAI_API_KEY  # System fallback

        if settings_doc:
            api_key = settings_doc.get("ai_api_key") or api_key

        return EmergentSummaryProvider(api_key) if api_key else MockSummaryProvider()

    async def get_latest(self, user: dict, project_id: str) -> Optional[Dict[str, Any]]:
        await self.permission_checker.check_project_access(user, project_id)
        summary = await self.ai_repo.find_one(
            {"project_id": project_id}, sort=[("created_at", -1)]
        )
        if not summary:
            return await self.refresh_summary(user, project_id)
        return summary

    async def refresh_summary(self, user: dict, project_id: str) -> Dict[str, Any]:
        await self.permission_checker.check_project_access(user, project_id)
        try:
            organisation_id = user.get("organisation_id")
            if not organisation_id:
                # Fallback: check if we can get it from the project directly
                res_id = ObjectId(project_id) if ObjectId.is_valid(project_id) else project_id
                resilient_query = {
                    "$or": [{"_id": res_id}, {"project_id": project_id}]
                }
                if ObjectId.is_valid(project_id):
                    resilient_query["$or"].append({"project_id": ObjectId(project_id)})

                project = await self.project_repo.find_one(resilient_query)
                if not project:
                    # Final attempt with direct field match
                    project = await self.db.projects.find_one(resilient_query)

                organisation_id = project.get("organisation_id") if project else None

            if not organisation_id:
                raise ValidationError(f"Organisation ID missing for project {project_id}. User: {user.get('email')}")

            return await self.generate_and_store(
                project_id=project_id,
                organisation_id=organisation_id,
                triggered_by="manual",
            )
        except Exception as e:
            logger.error(f"AI Summary failed for project {project_id}: {str(e)}", exc_info=True)
            raise ValidationError(f"Generation failed: {str(e)}")

    async def generate_and_store(
        self, project_id: str, organisation_id: str, triggered_by: str = "scheduler"
    ) -> Dict[str, Any]:
        report_data = await self._aggregate_report_data(project_id, organisation_id)

        res_id = ObjectId(project_id) if ObjectId.is_valid(project_id) else project_id
        resilient_query = {
            "$or": [{"_id": res_id}, {"project_id": project_id}]
        }
        if ObjectId.is_valid(project_id):
            resilient_query["$or"].append({"project_id": ObjectId(project_id)})

        project = await self.project_repo.find_one(resilient_query)
        if not project:
            project = await self.db.projects.find_one(resilient_query)

        project_name = (
            project.get("project_name", project_id) if project else project_id
        )

        provider = await self._get_provider(organisation_id)
        summary_text = await provider.generate_summary(report_data, project_name)

        doc = {
            "project_id": project_id,
            "organisation_id": organisation_id,
            "summary_text": summary_text,
            "report_data": report_data,
            "triggered_by": triggered_by,
            "date_key": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        }
        return await self.ai_repo.create(doc)

    async def summarize_schedule(
        self, project_id: str, organisation_id: str
    ) -> str:
        """Generate executive summary of schedule health."""
        if not self.analytics_service:
            return "[SCHEDULE] Analytics service not available."

        try:
            metrics = await self.analytics_service.calculate_schedule_health(
                project_id, organisation_id
            )
            metrics_dict = metrics.to_dict() if hasattr(metrics, 'to_dict') else metrics

            report_data = {
                "status": metrics_dict.get("status", "unknown"),
                "on_track_tasks": metrics_dict.get("on_track_tasks", 0),
                "at_risk_tasks": metrics_dict.get("at_risk_tasks", 0),
                "critical_path_days": metrics_dict.get("critical_path_days", 0),
            }

            provider = await self._get_provider(organisation_id)
            return await provider.generate_summary(report_data, "Schedule Health")
        except Exception as e:
            logger.error(f"Schedule summary failed: {e}")
            return "[SCHEDULE] Unable to generate summary at this time."

    async def summarize_financials(
        self, project_id: str, organisation_id: str
    ) -> str:
        """Generate executive summary of financial status."""
        if not self.analytics_service:
            return "[FINANCIAL] Analytics service not available."

        try:
            data = await self.analytics_service.calculate_financial_summary(
                project_id, organisation_id
            )
            fin_dict = data.to_dict() if hasattr(data, 'to_dict') else data

            report_data = {
                "total_budget": float(fin_dict.get("total_budget", 0)),
                "total_spent": float(fin_dict.get("total_spent", 0)),
                "remaining_budget": float(fin_dict.get("remaining_budget", 0)),
                "burn_rate_pct": float(fin_dict.get("burn_rate_pct", 0)),
            }

            provider = await self._get_provider(organisation_id)
            return await provider.generate_summary(report_data, "Financial Status")
        except Exception as e:
            logger.error(f"Financial summary failed: {e}")
            return "[FINANCIAL] Unable to generate summary at this time."

    async def summarize_resources(
        self, project_id: str, organisation_id: str
    ) -> str:
        """Generate executive summary of resource allocation."""
        if not self.analytics_service:
            return "[RESOURCES] Analytics service not available."

        try:
            data = await self.analytics_service.calculate_resource_utilization(
                project_id, organisation_id
            )
            res_dict = data.to_dict() if hasattr(data, 'to_dict') else data

            report_data = {
                "average_utilization_pct": float(res_dict.get("average_utilization_pct", 0)),
                "over_allocated_count": res_dict.get("over_allocated_count", 0),
                "total_resources": res_dict.get("total_resources", 0),
            }

            provider = await self._get_provider(organisation_id)
            return await provider.generate_summary(report_data, "Resource Allocation")
        except Exception as e:
            logger.error(f"Resource summary failed: {e}")
            return "[RESOURCES] Unable to generate summary at this time."

    async def stream_summary(
        self, project_type: str, project_id: str, organisation_id: str
    ) -> AsyncGenerator[str, None]:
        """Stream a summary word-by-word. Types: schedule, financial, resources."""
        try:
            if not self.analytics_service:
                yield "[ERROR] Analytics service not available."
                return

            # Gather metrics based on type
            if project_type == "schedule":
                metrics = await self.analytics_service.calculate_schedule_health(
                    project_id, organisation_id
                )
                report_data = metrics.to_dict() if hasattr(metrics, 'to_dict') else metrics
                project_name = "Schedule Health"
            elif project_type == "financial":
                metrics = await self.analytics_service.calculate_financial_summary(
                    project_id, organisation_id
                )
                report_data = metrics.to_dict() if hasattr(metrics, 'to_dict') else metrics
                project_name = "Financial Status"
            elif project_type == "resources":
                metrics = await self.analytics_service.calculate_resource_utilization(
                    project_id, organisation_id
                )
                report_data = metrics.to_dict() if hasattr(metrics, 'to_dict') else metrics
                project_name = "Resource Allocation"
            else:
                yield "Unknown summary type."
                return

            # Use provider's stream if available, else fallback to word-by-word
            provider = await self._get_provider(organisation_id)
            if hasattr(provider, 'stream_summary'):
                async for chunk in provider.stream_summary(report_data, project_name):
                    yield chunk
            else:
                summary = await provider.generate_summary(report_data, project_name)
                for word in summary.split():
                    yield word + " "
        except Exception as e:
            logger.error(f"Stream summary failed: {e}")
            yield f"Error: {str(e)}"

    async def _aggregate_report_data(
        self, project_id: str, organisation_id: str
    ) -> Dict[str, Any]:
        def to_d(v):
            if v is None:
                return Decimal("0.00")
            return FinancialEngine.to_decimal(v)

        res_id = ObjectId(project_id) if ObjectId.is_valid(project_id) else project_id
        resilient_id = {"$in": [project_id, res_id]}

        query = {"project_id": resilient_id, "organisation_id": organisation_id}

        budgets = await self.budget_repo.list(query, limit=100)
        financials = await self.fin_state_repo.list(query, limit=100)
        # Create map using all possible ID keys for maximum resilience
        fin_map = {}
        for f in financials:
            cid = str(f.get("category_id") or f.get("code_id") or "")
            if cid:
                fin_map[cid] = f

        total_budget = sum((to_d(b.get("original_budget")) for b in budgets), Decimal("0.00"))

        def get_cid(b):
            return str(b.get("category_id") or b.get("code_id") or "")

        total_committed = sum(
            (to_d(fin_map.get(get_cid(b)).get("committed_value"))
             if get_cid(b) in fin_map else Decimal("0.00")
             for b in budgets),
            Decimal("0.00")
        )
        total_certified = sum(
            (to_d(fin_map.get(get_cid(b)).get("certified_value"))
             if get_cid(b) in fin_map else Decimal("0.00")
             for b in budgets),
            Decimal("0.00")
        )

        # Fallback to MASTER financial state if categorical budget is missing (CRIT-09)
        if total_budget == 0:
            master_state = fin_map.get(FinancialEngine.MASTER_CATEGORY)
            if not master_state:
                master_state = await self.fin_state_repo.get_master_state(resilient_id, organisation_id)

            # Aggregate report level totals
            if master_state:
                total_budget = to_d(master_state.get("original_budget"))
                total_committed = to_d(master_state.get("committed_value"))
                total_certified = to_d(master_state.get("certified_value"))
                logger.info(f"AI_SUMMARY_BUDGET_RECONCILED: Using MASTER state for {project_id}")

        from app.modules.contracting.infrastructure.repository import WorkOrderRepository
        from app.modules.financial.infrastructure.repository import (
            PCRepository,
            FundAllocationRepository,
        )
        from app.modules.tasks.infrastructure.repository import TaskRepository

        wo_repo = WorkOrderRepository(self.db)
        pc_repo = PCRepository(self.db)
        fund_repo = FundAllocationRepository(self.db)
        task_repo = TaskRepository(self.db)

        # Count stats using resilient queries
        wo_total = await wo_repo.count(query)
        wo_open = await wo_repo.count({
            **query,
            "status": {"$in": ["Pending", "Draft", "Approved"]}
        })
        wo_closed = await wo_repo.count({
            **query,
            "status": {"$in": ["Closed", "Completed"]}
        })

        pc_total = await pc_repo.count(query)
        pc_closed = await pc_repo.count({
            **query,
            "status": {"$in": ["Approved", "Processing", "Paid"]}
        })

        # Cash & Payable stats
        allocations = await fund_repo.list(query)
        total_cash_in_hand = sum((to_d(a.get("cash_in_hand")) for a in allocations), Decimal("0.00"))

        paid_pcs = await pc_repo.list({**query, "status": "Paid"})
        total_paid_amount = sum((to_d(p.get("grand_total")) for p in paid_pcs), Decimal("0.00"))
        total_vendor_payable = max(Decimal("0.00"), total_certified - total_paid_amount)

        # Petty Cash & OVH Status
        petty_pcs = await pc_repo.list({**query, "pc_type": "PETTY_OVH"})

        # Split statuses based on category conventions (OVH code from seed)
        petty_cash_pending = [
            p for p in petty_pcs
            if p.get("category_id") != "OVH" and p.get("status") not in ["Paid", "Cancelled"]
        ]
        ovh_pending = [
            p for p in petty_pcs
            if p.get("category_id") == "OVH" and p.get("status") not in ["Paid", "Cancelled"]
        ]
        petty_status = "Action Required" if petty_cash_pending else "Healthy"
        ovh_status = "Action Required" if ovh_pending else "Healthy"

        schedule_task_count = await task_repo.count(query)

        over_budget_categories = []
        for b in budgets:
            cid = str(b.get("category_id") or b.get("code_id") or "")
            if not cid:
                continue
            o_b = to_d(b.get("original_budget"))
            committed_val = to_d(fin_map.get(cid, {}).get("committed_value"))
            if committed_val > o_b:
                over_budget_categories.append(cid)

        return {
            "total_budget": total_budget,
            "total_committed": total_committed,
            "total_certified": total_certified,
            "total_remaining": total_budget - total_committed,
            "total_vendor_payable": total_vendor_payable,
            "total_cash_in_hand": total_cash_in_hand,
            "petty_cash_status": petty_status,
            "ovh_status": ovh_status,
            "wo_total": wo_total,
            "wo_open": wo_open,
            "wo_closed": wo_closed,
            "pc_total": pc_total,
            "pc_closed": pc_closed,
            "schedule_task_count": schedule_task_count,
            "over_budget_categories": over_budget_categories
        }
