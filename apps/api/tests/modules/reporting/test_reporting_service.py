import pytest
from datetime import datetime, timezone
from decimal import Decimal
from app.modules.reporting.application.reporting_service import ReportingService
from app.modules.shared.domain.financial_engine import FinancialEngine

@pytest.mark.asyncio
class TestReportingService:
    @pytest.fixture
    async def reporting_service(self, test_db):
        from unittest.mock import AsyncMock
        mock_pc = AsyncMock()
        return ReportingService(test_db, mock_pc)

    @pytest.fixture
    async def sample_data(self, test_db, test_project_id):
        # 1. Create categories in code_master
        cat1_id = "507f1f77bcf86cd799439011"
        cat2_id = "507f1f77bcf86cd799439012"
        
        from bson import ObjectId
        await test_db.code_master.insert_many([
            {"_id": ObjectId(cat1_id), "category_name": "Category 1", "code": "CAT1"},
            {"_id": ObjectId(cat2_id), "category_name": "Category 2", "code": "CAT2"},
        ])

        # 2. Create financial state entries for categories
        await test_db.financial_state.insert_many([
            {
                "project_id": test_project_id,
                "category_id": cat1_id,
                "original_budget": 1000.0,
                "committed_value": 500.0,
                "certified_value": 400.0,
                "balance_budget_remaining": 500.0,
            },
            {
                "project_id": test_project_id,
                "category_id": cat2_id,
                "original_budget": 2000.0,
                "committed_value": 1000.0,
                "certified_value": 800.0,
                "balance_budget_remaining": 1000.0,
            },
            # 3. Create MASTER entry (The phantom row)
            {
                "project_id": test_project_id,
                "category_id": "MASTER",
                "original_budget": 3000.0,
                "committed_value": 1500.0,
                "certified_value": 1200.0,
                "balance_budget_remaining": 1500.0,
            }
        ])
        return {"cat1_id": cat1_id, "cat2_id": cat2_id}

    async def test_project_summary_report_excludes_master_row(self, reporting_service, sample_data, test_project_id):
        """
        Verify that _project_summary_report excludes the 'MASTER' record.
        BUG-005: Project Summary report shows a phantom row for the master budget.
        """
        user = {"user_id": "test-user", "organisation_id": "test-org"}
        report = await reporting_service.get_report(
            user=user, 
            project_id=test_project_id, 
            report_type="project_summary",
            start_date=None,
            end_date=None
        )
        
        # We expect 2 rows (CAT1, CAT2), not 3.
        rows = report["rows"]
        
        # Print rows for debugging if test fails
        print(f"Report Rows: {rows}")
        
        # BUG REPRODUCTION: 
        # If the bug exists, len(rows) will be 3.
        # One row will have "Unnamed Category" or "MASTER" details.
        
        # Assertions
        assert len(rows) == 2, f"Expected 2 rows, but found {len(rows)}. Rows: {rows}"
        
        # Verify no "Unnamed Category" or "N/A" code (which usually indicates the MASTER row)
        for row in rows:
            assert row[1] != "Unnamed Category"
            assert row[0] != "N/A"
            assert row[0] in ["CAT1", "CAT2"]

        # Verify totals (should be sum of CAT1 and CAT2)
        # Budget: 1000 + 2000 = 3000
        assert report["totals"]["budget"] == "3,000.00"
