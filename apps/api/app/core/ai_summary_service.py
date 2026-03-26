from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, timezone, date
from typing import Optional, Dict, Any
from bson import ObjectId, Decimal128
import logging
import os

from app.repositories.ai_summary_repo import AISummaryRepository
from app.repositories.project_repo import ProjectRepository

logger = logging.getLogger(__name__)

class SummaryProvider:
    async def generate_summary(self, report_data: Dict[str, Any], project_name: str) -> str:
        raise NotImplementedError

class MockSummaryProvider(SummaryProvider):
    async def generate_summary(self, report_data: Dict[str, Any], project_name: str) -> str:
        logger.info("[AI:SUMMARY:MOCK] Generating mock project summary")
        over_budget = len(report_data.get("over_budget_categories", []))
        cash = report_data.get("total_cash_in_hand", 0)
        committed_pct = 0
        if report_data.get("total_budget", 0) > 0:
            committed_pct = round(
                report_data["total_committed"] / report_data["total_budget"] * 100, 1
            )
        return (
            f"[MOCK SUMMARY] Project '{project_name}' is {committed_pct}% committed against budget. "
            f"Cash in hand: ₹{cash:,.2f}. "
            f"{over_budget} categories are over-budget. "
            f"Work orders: {report_data.get('wo_total', 0)} total. "
            f"Configure OPENAI_API_KEY for actual AI briefings."
        )

class EmergentSummaryProvider(SummaryProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def generate_summary(self, report_data: Dict[str, Any], project_name: str) -> str:
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=self.api_key)
            prompt = self._build_summary_prompt(report_data, project_name)

            response = await client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=500
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            return await MockSummaryProvider().generate_summary(report_data, project_name)

    def _build_summary_prompt(self, report_data: Dict[str, Any], project_name: str) -> str:
        return f"Generate executive summary for {project_name}. Data: {report_data}"

class AISummaryService:
    def __init__(self, db: AsyncIOMotorDatabase, api_key: Optional[str] = None):
        self.db = db
        self.provider = EmergentSummaryProvider(api_key) if api_key else MockSummaryProvider()
        self.model = "gpt-4o" if api_key else "mock"
        self.ai_repo = AISummaryRepository(db)
        self.project_repo = ProjectRepository(db)

    async def generate_and_store(self, project_id: str, organisation_id: str, triggered_by: str = "scheduler") -> Dict[str, Any]:
        report_data = await self._aggregate_report_data(project_id, organisation_id)
        
        project = await self.project_repo.get_by_id(project_id)
        if not project:
            project = await self.project_repo.find_one({"project_id": project_id})
            
        project_name = project.get("project_name", project_id) if project else project_id
        summary_text = await self.provider.generate_summary(report_data, project_name)
        
        doc = {
            "project_id": project_id,
            "organisation_id": organisation_id,
            "summary_text": summary_text,
            "report_data": report_data,
            "model": self.model,
            "triggered_by": triggered_by
        }
        return await self.ai_repo.create(doc)

    async def get_latest(self, project_id: str) -> Optional[Dict[str, Any]]:
        return await self.ai_repo.find_one({"project_id": project_id}, sort=[("generated_at", -1)])

    async def _aggregate_report_data(self, project_id: str, organisation_id: str) -> Dict[str, Any]:
        # Minimalist aggregation for MVP, full version in legacy
        return {"total_budget": 0.0, "total_committed": 0.0}
