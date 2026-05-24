import pytest
from app.modules.reporting.application.reporting_service import ReportingService


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

        # 4. Create Work Orders and Payment Certificates (Authoritative sources for BUG-001/002)
        await test_db.work_orders.insert_many([
            {
                "project_id": test_project_id,
                "category_id": cat1_id,
                "grand_total": 500.0,
                "status": "Approved",
                "wo_ref": "WO-001"
            },
            {
                "project_id": test_project_id,
                "category_id": cat2_id,
                "grand_total": 1000.0,
                "status": "Approved",
                "wo_ref": "WO-002"
            }
        ])

        await test_db.payment_certificates.insert_many([
            {
                "project_id": test_project_id,
                "category_id": cat1_id,
                "grand_total": 400.0,
                "status": "Approved",
                "pc_ref": "PC-001"
            },
            {
                "project_id": test_project_id,
                "category_id": cat2_id,
                "grand_total": 800.0,
                "status": "Approved",
                "pc_ref": "PC-002"
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

        assert len(rows) == 2, f"Expected 2 rows, but found {len(rows)}. Rows: {rows}"

        # Verify no "Unnamed Category" or "N/A" code (which usually indicates the MASTER row)
        for row in rows:
            assert row[1] != "Unnamed Category"
            assert row[0] != "N/A"
            assert row[0] in ["CAT1", "CAT2"]

        # Verify totals (should be sum of CAT1 and CAT2)
        # Budget: 1000 + 2000 = 3000
        assert report["totals"]["budget"] == "\u20b93,000.00"
        assert report["totals"]["committed"] == "\u20b91,500.00"
        assert report["totals"]["remaining"] == "\u20b91,500.00"

    async def test_progress_report_date_filter(self, reporting_service, sample_data, test_project_id):
        user = {"user_id": "test-user", "organisation_id": "test-org"}

        # Test with date filter strings
        start_date = "2023-01-01T00:00:00+00:00"
        end_date = "2023-12-31T00:00:00+00:00"

        report = await reporting_service.get_report(
            user=user,
            project_id=test_project_id,
            report_type="weekly_progress",
            start_date=start_date,
            end_date=end_date
        )
        assert "rows" in report

    def test_indian_currency_formatting(self):
        """
        Verify standard Indian Currency formatting (INR grouping).
        NR-007 requires ₹30,085,000.00 to format as ₹3,00,85,000.00
        """
        from app.core.export_service import ExportService
        
        # Test basic, decimals, large numbers
        assert ExportService.format_currency(0) == "₹0.00"
        assert ExportService.format_currency(100) == "₹100.00"
        assert ExportService.format_currency(1000) == "₹1,000.00"
        assert ExportService.format_currency(100000) == "₹1,00,000.00"
        assert ExportService.format_currency(10000000) == "₹1,00,00,000.00"
        assert ExportService.format_currency(30085000) == "₹3,00,85,000.00"
        
        # Test negative numbers
        assert ExportService.format_currency(-30085000) == "₹-3,00,85,000.00"
        
        # Test None
        assert ExportService.format_currency(None) == "₹0.00"
        
        # Test float/invalid values
        assert ExportService.format_currency("invalid") == "invalid"

    async def test_report_metadata_enrichment_and_export(self, reporting_service, sample_data, test_project_id, test_db):
        """
        Verify reports get enriched with project and user context,
        and verify they successfully run through PDF/Excel compilers without errors.
        """
        # Seed project details
        await test_db.projects.insert_one({
            "project_id": test_project_id,
            "name": "Luxury Palm Villa",
            "code": "LPV-901",
            "company": {"name": "Sovereign Developers", "address": "Jubilee Hills, Hyderabad"}
        })

        user = {
            "user_id": "usr-1234",
            "name": "Ananya Sharma",
            "role": "Super Admin",
            "organisation_id": "org-99"
        }

        report = await reporting_service.get_report(
            user=user,
            project_id=test_project_id,
            report_type="project_summary",
            start_date=None,
            end_date=None
        )

        # 1. Assert Metadata Enrichment
        assert report["project_name"] == "Luxury Palm Villa"
        assert report["project_code"] == "LPV-901"
        assert report["generator_name"] == "Ananya Sharma"
        assert report["generator_role"] == "Super Admin"
        assert report["company"]["name"] == "Sovereign Developers"
        assert report["company"]["address"] == "Jubilee Hills, Hyderabad"

        # 2. Verify PDF compilation pipeline passes
        from app.core.export_service import ExportService
        pdf_bytes = ExportService.export_to_pdf_service("project_summary", report)
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0

        # 3. Verify Excel compilation pipeline passes
        excel_bytes = ExportService.export_to_excel("project_summary", report)
        assert isinstance(excel_bytes, bytes)
        assert len(excel_bytes) > 0
