"""
AI PROJECT SUMMARY SERVICE — Phase 5 Feature

Generates a daily natural-language summary of project health.
Uses the same provider abstraction as AIService (MockSummaryProvider / EmergentSummaryProvider).

RULES:
- Reads ONLY from existing collections (no data mutation)
- Falls back to MockSummaryProvider if OPENAI_API_KEY absent
- Stores result in ai_project_summaries collection
- Idempotent: upserts by (project_id, date) to avoid duplicates
"""

from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, timezone, date
from typing import Optional, Dict, Any
from bson import ObjectId, Decimal128
import logging
import os

logger = logging.getLogger(__name__)


class SummaryProvider:
    """Abstract base for summary generation"""
    async def generate_summary(self, report_data: Dict[str, Any], project_name: str) -> str:
        raise NotImplementedError


class MockSummaryProvider(SummaryProvider):
    """Used when OPENAI_API_KEY is absent"""

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
            f"Work orders: {report_data.get('wo_total', 0)} total, "
            f"{report_data.get('wo_open', 0)} open. "
            f"This is a mock summary — configure OPENAI_API_KEY for AI-generated text."
        )


class EmergentSummaryProvider(SummaryProvider):
    """GPT-4o powered summary via OpenAI API"""

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def generate_summary(self, report_data: Dict[str, Any], project_name: str) -> str:
        try:
            import asyncio
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=self.api_key)
            prompt = _build_summary_prompt(report_data, project_name)

            response = await client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=500
            )
            return response.choices[0].message.content.strip()
        except ImportError:
            logger.warning("[AI:SUMMARY] openai not available, using mock")
            return await MockSummaryProvider().generate_summary(report_data, project_name)
        except Exception as e:
            logger.error(f"[AI:SUMMARY] Generation failed: {e}")
            raise


def _build_summary_prompt(report_data: Dict[str, Any], project_name: str) -> str:
    """
    Constructs the structured prompt for GPT-4o.
    Uses a data-to-narrative pattern — gives concrete numbers, asks for insight.
    """
    over_budget_names = ", ".join(report_data.get("over_budget_categories", [])) or "None"
    committed_pct = 0
    if report_data.get("total_budget", 0) > 0:
        committed_pct = round(
            report_data["total_committed"] / report_data["total_budget"] * 100, 1
        )

    return f"""You are a construction project management assistant generating a daily executive briefing.

PROJECT: {project_name}
DATE: {datetime.now(timezone.utc).strftime('%d %B %Y')}

FINANCIAL SNAPSHOT:
- Master Budget: ₹{report_data.get('total_budget', 0):,.2f}
- Total Committed: ₹{report_data.get('total_committed', 0):,.2f} ({committed_pct}% of budget)
- Total Certified: ₹{report_data.get('total_certified', 0):,.2f}
- Budget Remaining: ₹{report_data.get('total_remaining', 0):,.2f}
- Over-Budget Categories: {over_budget_names}

VENDOR POSITION:
- Total Outstanding Payables: ₹{report_data.get('total_vendor_payable', 0):,.2f}

CASH POSITION:
- Total Cash In Hand: ₹{report_data.get('total_cash_in_hand', 0):,.2f}
- Petty Cash Status: {report_data.get('petty_cash_status', 'Unknown')}
- OVH Status: {report_data.get('ovh_status', 'Unknown')}

DOCUMENT STATUS:
- Work Orders: {report_data.get('wo_total', 0)} total, {report_data.get('wo_open', 0)} open, {report_data.get('wo_closed', 0)} closed
- Payment Certificates: {report_data.get('pc_total', 0)} total, {report_data.get('pc_closed', 0)} certified

SCHEDULE:
- {report_data.get('schedule_task_count', 0)} tasks in the saved schedule baseline

Write a concise 3-4 sentence executive summary in plain English. Highlight the single most important risk or positive signal. Do not use bullet points — write in prose. Be direct and specific with numbers. Use the Indian Rupee symbol (₹) for amounts."""


class AISummaryService:
    """
    Orchestrates data aggregation + AI summary generation + persistence.

    Called by:
    - Celery beat task (triggered_by = "scheduler")
    - Manual refresh API endpoint (triggered_by = "manual")
    """

    def __init__(self, db: AsyncIOMotorDatabase, api_key: Optional[str] = None):
        self.db = db
        if api_key:
            self.provider = EmergentSummaryProvider(api_key)
            self.model = "gpt-4o"
            logger.info("[AI:SUMMARY] Using EmergentSummaryProvider")
        else:
            self.provider = MockSummaryProvider()
            self.model = "mock"
            logger.info("[AI:SUMMARY] Using MockSummaryProvider (no OPENAI_API_KEY)")

    async def generate_and_store(
        self,
        project_id: str,
        organisation_id: str,
        triggered_by: str = "scheduler"
    ) -> Dict[str, Any]:
        """
        Full pipeline:
        1. Aggregate stats from financials, WOs, PCs, cash, schedule
        2. Call LLM provider
        3. Upsert result into ai_project_summaries (idempotent by date)
        4. Return serialized summary doc
        """
        report_data = await self._aggregate_report_data(project_id, organisation_id)

        # Resolve project name
        project = await self.db.projects.find_one(
            {"$or": [{"project_id": project_id}, {"_id": ObjectId(project_id) if ObjectId.is_valid(project_id) else None}]}
        )
        project_name = project.get("project_name", project_id) if project else project_id

        summary_text = await self.provider.generate_summary(report_data, project_name)

        now = datetime.now(timezone.utc)
        today_str = now.strftime("%Y-%m-%d")

        doc = {
            "project_id": project_id,
            "organisation_id": organisation_id,
            "summary_text": summary_text,
            "report_data": report_data,
            "generated_at": now,
            "model": self.model,
            "triggered_by": triggered_by,
            "date_key": today_str,  # used for upsert deduplication
        }

        # Upsert: one summary per project per day (scheduler overwrites, manual always replaces)
        await self.db.ai_project_summaries.update_one(
            {"project_id": project_id, "date_key": today_str},
            {"$set": doc},
            upsert=True
        )

        result = await self.db.ai_project_summaries.find_one(
            {"project_id": project_id, "date_key": today_str}
        )

        logger.info(
            f"[AI:SUMMARY] Generated summary for project {project_id}, "
            f"triggered_by={triggered_by}, model={self.model}"
        )

        return self._serialize(result)

    async def get_latest(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Returns the most recent summary for a project, regardless of date."""
        doc = await self.db.ai_project_summaries.find_one(
            {"project_id": project_id},
            sort=[("generated_at", -1)]
        )
        return self._serialize(doc) if doc else None

    async def _aggregate_report_data(
        self, project_id: str, organisation_id: str
    ) -> Dict[str, Any]:
        """
        Gathers stats from 6 collections using direct DB queries (no HTTP calls).
        This matches the same data the frontend dashboard displays.
        """
        def to_f(v):
            if v is None: return 0.0
            if isinstance(v, Decimal128): return float(v.to_decimal())
            try: return float(v)
            except: return 0.0

        # --- 1. Financials (project_category_budgets + financial_state) ---
        budgets = await self.db.project_category_budgets.find(
            {"project_id": project_id}
        ).to_list(length=500)
        financials = await self.db.financial_state.find(
            {"project_id": project_id}
        ).to_list(length=500)
        fin_map = {str(f["category_id"]): f for f in financials}

        total_budget = sum(to_f(b.get("original_budget")) for b in budgets)
        total_committed = sum(to_f(fin_map.get(str(b["category_id"]), {}).get("committed_value")) for b in budgets)
        total_certified = sum(to_f(fin_map.get(str(b["category_id"]), {}).get("certified_value")) for b in budgets)
        total_remaining = sum(to_f(fin_map.get(str(b["category_id"]), {}).get("balance_budget_remaining", b.get("original_budget", 0))) for b in budgets)

        # Category names for over-budget entries
        over_budget_cat_ids = [
            b["category_id"] for b in budgets
            if fin_map.get(str(b["category_id"]), {}).get("over_commit_flag", False)
        ]
        valid_ids = [ObjectId(cid) if ObjectId.is_valid(str(cid)) else cid for cid in over_budget_cat_ids]
        over_budget_cats = await self.db.code_master.find(
            {"_id": {"$in": valid_ids}}, {"category_name": 1, "code_description": 1}
        ).to_list(length=50)
        over_budget_names = [
            c.get("category_name") or c.get("code_description", "Unknown")
            for c in over_budget_cats
        ]

        # --- 2. Vendor Payables ---
        payables_pipeline = [
            {"$match": {"project_id": project_id}},
            {
                "$group": {
                    "_id": None,
                    "total_certified": {
                        "$sum": {"$cond": [{"$eq": ["$entry_type", "PC_CERTIFIED"]}, "$amount", 0]}
                    },
                    "total_paid": {
                        "$sum": {"$cond": [{"$eq": ["$entry_type", "PAYMENT_MADE"]}, "$amount", 0]}
                    },
                    "total_retention": {
                        "$sum": {"$cond": [{"$eq": ["$entry_type", "RETENTION_HELD"]}, "$amount", 0]}
                    },
                }
            }
        ]
        payable_result = await self.db.vendor_ledger.aggregate(payables_pipeline).to_list(1)
        if payable_result:
            r = payable_result[0]
            total_vendor_payable = to_f(r["total_certified"]) - to_f(r["total_paid"]) - to_f(r["total_retention"])
        else:
            total_vendor_payable = 0.0

        # --- 3. Cash Summary (fund_allocations) ---
        categories = await self.db.code_master.find(
            {"organisation_id": organisation_id, "budget_type": "fund_transfer"}
        ).to_list(length=100)
        cat_ids = [str(c["_id"]) for c in categories]
        allocations = await self.db.fund_allocations.find(
            {"project_id": project_id, "category_id": {"$in": cat_ids}}
        ).to_list(length=50)

        total_cash_in_hand = 0.0
        petty_status = "Unknown"
        ovh_status = "Unknown"
        for alloc in allocations:
            cat = next((c for c in categories if str(c["_id"]) == alloc.get("category_id")), None)
            if not cat:
                continue
            received = to_f(alloc.get("allocation_received", 0))
            expenses = to_f(alloc.get("total_expenses", 0))
            cash = received - expenses
            total_cash_in_hand += cash
            name_lower = cat.get("category_name", "").lower()
            if "petty" in name_lower:
                threshold = to_f(alloc.get("threshold", 1000))
                petty_status = "Low" if cash < threshold else "OK"
            elif "ovh" in name_lower or "overhead" in name_lower:
                threshold = to_f(alloc.get("threshold", 1000))
                ovh_status = "Low" if cash < threshold else "OK"

        # --- 4. Work Orders ---
        wo_pipeline = [
            {"$match": {"project_id": project_id}},
            {"$group": {"_id": "$status", "count": {"$sum": 1}}}
        ]
        wo_counts = await self.db.work_orders.aggregate(wo_pipeline).to_list(length=20)
        wo_total = sum(r["count"] for r in wo_counts)
        wo_open = sum(r["count"] for r in wo_counts if r["_id"] in ("Draft", "Pending"))
        wo_closed = sum(r["count"] for r in wo_counts if r["_id"] in ("Closed", "Completed"))

        # --- 5. Payment Certificates ---
        pc_pipeline = [
            {"$match": {"project_id": project_id}},
            {"$group": {"_id": "$status", "count": {"$sum": 1}}}
        ]
        pc_counts = await self.db.payment_certificates.aggregate(pc_pipeline).to_list(length=20)
        pc_total = sum(r["count"] for r in pc_counts)
        pc_closed = sum(r["count"] for r in pc_counts if r["_id"] == "Closed")

        # --- 6. Schedule ---
        schedule = await self.db.project_schedules.find_one({"project_id": project_id})
        task_count = len(schedule.get("tasks", [])) if schedule else 0

        return {
            "total_budget": total_budget,
            "total_committed": total_committed,
            "total_certified": total_certified,
            "total_remaining": total_remaining,
            "over_budget_categories": over_budget_names,
            "total_vendor_payable": total_vendor_payable,
            "total_cash_in_hand": total_cash_in_hand,
            "petty_cash_status": petty_status,
            "ovh_status": ovh_status,
            "wo_total": wo_total,
            "wo_open": wo_open,
            "wo_closed": wo_closed,
            "pc_total": pc_total,
            "pc_closed": pc_closed,
            "schedule_task_count": task_count,
        }

    @staticmethod
    def _serialize(doc: dict) -> Optional[Dict[str, Any]]:
        if not doc:
            return None
        d = dict(doc)
        if "_id" in d and isinstance(d["_id"], ObjectId):
            d["_id"] = str(d["_id"])
        if "generated_at" in d and hasattr(d["generated_at"], "isoformat"):
            d["generated_at"] = d["generated_at"].isoformat()
        return d

    async def create_indexes(self):
        await self.db.ai_project_summaries.create_index(
            [("project_id", 1), ("date_key", -1)],
            unique=True,
            name="ai_summary_project_date_unique"
        )
        await self.db.ai_project_summaries.create_index(
            [("organisation_id", 1), ("generated_at", -1)],
            name="ai_summary_org_lookup"
        )
