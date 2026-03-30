import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from app.core.config import settings
from app.modules.financial.infrastructure.repository import FinancialStateRepository
from app.modules.project.infrastructure.repository import (
    BudgetRepository,
    ProjectRepository,
)
from app.modules.shared.domain.exceptions import NotFoundError, ValidationError
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
        committed_pct = 0
        if report_data.get("total_budget", 0) > 0:
            committed_pct = round(
                report_data["total_committed"] / report_data["total_budget"] * 100, 1
            )
        return f"[MOCK] Project {project_name} at {committed_pct}% budget commitment."


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

    def _build_prompt(self, report_data, name):
        return f"Executive summary for {name}. Data: {report_data}"


class AISummaryService:
    def __init__(self, db, permission_checker):
        self.db = db
        self.permission_checker = permission_checker
        api_key = settings.OPENAI_API_KEY
        self.provider = (
            EmergentSummaryProvider(api_key) if api_key else MockSummaryProvider()
        )
        self.ai_repo = AISummaryRepository(db)
        self.project_repo = ProjectRepository(db)
        self.budget_repo = BudgetRepository(db)
        self.fin_state_repo = FinancialStateRepository(db)

    async def get_latest(self, user: dict, project_id: str) -> Optional[Dict[str, Any]]:
        await self.permission_checker.check_project_access(user, project_id)
        summary = await self.ai_repo.find_one(
            {"project_id": project_id}, sort=[("created_at", -1)]
        )
        if not summary:
            raise NotFoundError("AI summary", project_id)
        return summary

    async def refresh_summary(self, user: dict, project_id: str) -> Dict[str, Any]:
        await self.permission_checker.check_project_access(user, project_id)
        try:
            return await self.generate_and_store(
                project_id=project_id,
                organisation_id=user["organisation_id"],
                triggered_by="manual",
            )
        except Exception as e:
            logger.error(f"AI Summary failed: {e}")
            raise ValidationError("Generation failed.")

    async def generate_and_store(
        self, project_id: str, organisation_id: str, triggered_by: str = "scheduler"
    ) -> Dict[str, Any]:
        report_data = await self._aggregate_report_data(project_id, organisation_id)

        project = await self.project_repo.get_by_id(project_id)
        if not project:
            project = await self.project_repo.find_one({"project_id": project_id})
        project_name = (
            project.get("project_name", project_id) if project else project_id
        )

        summary_text = await self.provider.generate_summary(report_data, project_name)

        doc = {
            "project_id": project_id,
            "organisation_id": organisation_id,
            "summary_text": summary_text,
            "report_data": report_data,
            "triggered_by": triggered_by,
            "date_key": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        }
        return await self.ai_repo.create(doc)

    async def _aggregate_report_data(
        self, project_id: str, organisation_id: str
    ) -> Dict[str, Any]:
        def to_f(v):
            return float(FinancialEngine.to_decimal(v))

        budgets = await self.budget_repo.list({"project_id": project_id}, limit=100)
        financials = await self.fin_state_repo.list(
            {"project_id": project_id}, limit=100
        )
        fin_map = {str(f.get("category_id")): f for f in financials}

        total_budget = sum(to_f(b.get("original_budget")) for b in budgets)
        total_committed = sum(
            to_f(fin_map.get(str(b.get("category_id")), {}).get("committed_value"))
            for b in budgets
        )

        return {
            "total_budget": total_budget,
            "total_committed": total_committed,
            "total_remaining": total_budget - total_committed,
        }
