import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from bson import ObjectId

from app.modules.financial.application.cash_service import CashService
from app.modules.shared.domain.exceptions import NotFoundError, ValidationError
from app.modules.shared.domain.financial_engine import FinancialEngine


class TestCashServiceUnit:
    """Unit tests for CashService (no DB)."""

    @pytest.mark.asyncio
    async def test_reconcile_balanced(self):
        """Reconcile with balanced debits and ledger expenses."""
        db_mock = MagicMock()
        permission_mock = AsyncMock()
        audit_mock = AsyncMock()

        service = CashService(db_mock, permission_mock, audit_mock)

        # Mock repositories
        service.fund_repo.list = AsyncMock(
            return_value=[
                {
                    "_id": ObjectId(),
                    "category_id": "cat1",
                    "category_name": "Petty Cash",
                    "total_expenses": Decimal("1000.00"),
                },
                {
                    "_id": ObjectId(),
                    "category_id": "cat2",
                    "category_name": "Overhead",
                    "total_expenses": Decimal("500.00"),
                },
            ]
        )

        # Mock aggregation pipeline (debits = expenses)
        cursor_mock = AsyncMock()
        cursor_mock.to_list = AsyncMock(
            return_value=[
                {"_id": "cat1", "actual_expenses": Decimal("1000.00")},
                {"_id": "cat2", "actual_expenses": Decimal("500.00")},
            ]
        )
        db_mock.cash_transactions.aggregate.return_value = cursor_mock

        result = await service.reconcile_cash_flow(
            {"user_id": "u1", "organisation_id": "org1"}, "proj1"
        )

        assert result["status"] == "BALANCED"
        assert len(result["categories"]) == 2
        assert all(c["is_balanced"] for c in result["categories"])
        assert result["total_variance"] == 0.0

    @pytest.mark.asyncio
    async def test_reconcile_discrepancy(self):
        """Reconcile with variance > 0.01."""
        db_mock = MagicMock()
        permission_mock = AsyncMock()
        audit_mock = AsyncMock()

        service = CashService(db_mock, permission_mock, audit_mock)

        service.fund_repo.list = AsyncMock(
            return_value=[
                {
                    "_id": ObjectId(),
                    "category_id": "cat1",
                    "category_name": "Petty Cash",
                    "total_expenses": Decimal("1000.00"),
                }
            ]
        )

        cursor_mock = AsyncMock()
        cursor_mock.to_list = AsyncMock(
            return_value=[
                {"_id": "cat1", "actual_expenses": Decimal("900.00")},
            ]
        )
        db_mock.cash_transactions.aggregate.return_value = cursor_mock

        result = await service.reconcile_cash_flow(
            {"user_id": "u1", "organisation_id": "org1"}, "proj1"
        )

        assert result["status"] == "DISCREPANCY_FOUND"
        assert result["categories"][0]["is_balanced"] is False
        assert abs(result["categories"][0]["variance"] - 100.0) < 0.01

    @pytest.mark.asyncio
    async def test_cash_flow_statement_calc(self):
        """Verify opening/closing balance calculation."""
        from app.core.time import now

        db_mock = MagicMock()
        permission_mock = AsyncMock()
        audit_mock = AsyncMock()

        service = CashService(db_mock, permission_mock, audit_mock)

        now_dt = now()
        from_dt = now_dt.replace(day=1)
        to_dt = now_dt.replace(day=28)

        # Mock two separate aggregate calls
        call_count = [0]

        def mock_aggregate_fn(pipeline):
            cursor = AsyncMock()
            if call_count[0] == 0:
                # Opening balance
                cursor.to_list = AsyncMock(
                    return_value=[{"_id": None, "total": Decimal("5000.00")}]
                )
            else:
                # Period data
                cursor.to_list = AsyncMock(
                    return_value=[
                        {
                            "_id": from_dt.strftime("%Y-%m-%d"),
                            "credits": Decimal("2000.00"),
                            "debits": Decimal("1000.00"),
                        },
                        {
                            "_id": (from_dt + timedelta(days=1)).strftime("%Y-%m-%d"),
                            "credits": Decimal("1000.00"),
                            "debits": Decimal("500.00"),
                        },
                    ]
                )
            call_count[0] += 1
            return cursor

        db_mock.cash_transactions.aggregate.side_effect = mock_aggregate_fn

        result = await service.get_cash_flow_statement(
            {"user_id": "u1", "organisation_id": "org1"},
            "proj1",
            from_dt.isoformat(),
            to_dt.isoformat(),
        )

        assert result["opening_balance"] == 5000.0
        assert abs(result["closing_balance"] - 6500.0) < 0.01
        assert result["net_flow"] == 1500.0
        assert len(result["daily_data"]) == 2



class TestCashServiceIntegration:
    """Integration tests for CashService (real DB)."""

    @pytest.mark.asyncio
    async def test_create_fund_allocation_success(self, test_db, test_user):
        """Create fund allocation, verify DB write."""
        from app.core.dependencies import (
            get_authenticated_user,
            get_cash_service,
            get_db,
        )
        from unittest.mock import AsyncMock

        # Setup
        db = test_db
        user = test_user
        project_id = "proj_test_" + str(ObjectId())
        category_id = str(ObjectId())

        # Insert category
        await db.code_master.insert_one(
            {
                "_id": ObjectId(category_id),
                "organisation_id": user["organisation_id"],
                "code": "PETTY",
                "category_name": "Petty Cash",
                "budget_type": "fund_transfer",
            }
        )

        # Create service
        permission_mock = AsyncMock()
        permission_mock.check_write_access_with_role = AsyncMock()
        audit_mock = AsyncMock()
        service = CashService(db, permission_mock, audit_mock)

        # Create allocation
        result = await service.create_fund_allocation(
            user,
            {
                "project_id": project_id,
                "category_id": category_id,
                "allocation_original": "10000.00",
                "allocation_received": "5000.00",
            },
        )

        # Verify result
        assert result["project_id"] == project_id
        assert result["category_id"] == category_id
        assert float(result["allocation_received"]) == 5000.0
        assert float(result["cash_in_hand"]) == 5000.0

        # Verify DB
        doc = await db.fund_allocations.find_one(
            {"project_id": project_id, "category_id": category_id}
        )
        assert doc is not None
        assert float(FinancialEngine.to_decimal(doc["cash_in_hand"])) == 5000.0

    @pytest.mark.asyncio
    async def test_create_fund_allocation_upsert(self, test_db, test_user):
        """Upsert: same allocation overwrites prev values."""
        from unittest.mock import AsyncMock

        db = test_db
        user = test_user
        project_id = "proj_test_upsert_" + str(ObjectId())
        category_id = str(ObjectId())

        await db.code_master.insert_one(
            {
                "_id": ObjectId(category_id),
                "organisation_id": user["organisation_id"],
                "code": "OVH",
                "category_name": "Overhead",
                "budget_type": "fund_transfer",
            }
        )

        permission_mock = AsyncMock()
        permission_mock.check_write_access_with_role = AsyncMock()
        audit_mock = AsyncMock()
        service = CashService(db, permission_mock, audit_mock)

        # First call
        result1 = await service.create_fund_allocation(
            user,
            {
                "project_id": project_id,
                "category_id": category_id,
                "allocation_original": "20000.00",
                "allocation_received": "10000.00",
            },
        )

        # Second call with same key should upsert
        result2 = await service.create_fund_allocation(
            user,
            {
                "project_id": project_id,
                "category_id": category_id,
                "allocation_original": "30000.00",
                "allocation_received": "15000.00",
            },
        )

        assert result1["id"] == result2["id"]
        assert float(result2["allocation_received"]) == 15000.0

    @pytest.mark.asyncio
    async def test_get_transaction_by_id(self, test_db, test_user):
        """Fetch single transaction by ID."""
        from unittest.mock import AsyncMock

        db = test_db
        user = test_user
        project_id = "proj_test_txn_" + str(ObjectId())
        category_id = str(ObjectId())

        await db.code_master.insert_one(
            {
                "_id": ObjectId(category_id),
                "organisation_id": user["organisation_id"],
                "code": "PETTY",
                "category_name": "Petty Cash",
            }
        )

        permission_mock = AsyncMock()
        permission_mock.check_project_access = AsyncMock()
        audit_mock = AsyncMock()
        service = CashService(db, permission_mock, audit_mock)

        # Insert transaction
        txn = {
            "project_id": project_id,
            "organisation_id": user["organisation_id"],
            "category_id": category_id,
            "amount": FinancialEngine.to_d128("100.00"),
            "type": "DEBIT",
            "description": "Test expense",
            "created_by": user["user_id"],
        }
        result = await db.cash_transactions.insert_one(txn)
        txn_id = str(result.inserted_id)

        # Fetch
        fetched = await service.get_transaction_by_id(user, txn_id)

        assert fetched["project_id"] == project_id
        assert fetched["type"] == "DEBIT"
        assert fetched["amount"] == 100.0

    @pytest.mark.asyncio
    async def test_list_transactions_category_filter(self, test_db, test_user):
        """Filter transactions by category_id."""
        from unittest.mock import AsyncMock

        db = test_db
        user = test_user
        project_id = "proj_test_filter_" + str(ObjectId())
        cat1 = str(ObjectId())
        cat2 = str(ObjectId())

        for cat_id in [cat1, cat2]:
            await db.code_master.insert_one(
                {
                    "_id": ObjectId(cat_id),
                    "organisation_id": user["organisation_id"],
                    "category_name": f"Category {cat_id[:4]}",
                }
            )

        # Insert transactions for both categories
        await db.cash_transactions.insert_many(
            [
                {
                    "project_id": project_id,
                    "organisation_id": user["organisation_id"],
                    "category_id": cat1,
                    "amount": FinancialEngine.to_d128("100.00"),
                    "type": "DEBIT",
                    "created_by": user["user_id"],
                },
                {
                    "project_id": project_id,
                    "organisation_id": user["organisation_id"],
                    "category_id": cat2,
                    "amount": FinancialEngine.to_d128("200.00"),
                    "type": "DEBIT",
                    "created_by": user["user_id"],
                },
            ]
        )

        permission_mock = AsyncMock()
        permission_mock.check_project_access = AsyncMock()
        audit_mock = AsyncMock()
        service = CashService(db, permission_mock, audit_mock)

        # List with cat1 filter
        result = await service.list_cash_transactions(user, project_id, category_id=cat1)

        assert len(result["items"]) == 1
        assert result["items"][0]["category_id"] == cat1

    @pytest.mark.asyncio
    async def test_reconcile_cash_flow_empty(self, test_db, test_user):
        """Reconcile with no transactions returns all balanced."""
        from unittest.mock import AsyncMock

        db = test_db
        user = test_user
        project_id = "proj_test_empty_" + str(ObjectId())

        permission_mock = AsyncMock()
        permission_mock.check_project_access = AsyncMock()
        audit_mock = AsyncMock()
        service = CashService(db, permission_mock, audit_mock)

        result = await service.reconcile_cash_flow(user, project_id)

        assert result["status"] == "BALANCED"
        assert result["total_variance"] == 0.0
        assert len(result["categories"]) == 0

    @pytest.mark.asyncio
    async def test_get_cash_flow_statement(self, test_db, test_user):
        """Generate period-based statement with daily breakdown."""
        from unittest.mock import AsyncMock
        from app.core.time import now

        db = test_db
        user = test_user
        project_id = "proj_test_stmt_" + str(ObjectId())

        permission_mock = AsyncMock()
        permission_mock.check_project_access = AsyncMock()
        audit_mock = AsyncMock()
        service = CashService(db, permission_mock, audit_mock)

        now_dt = now()
        from_date = (now_dt - timedelta(days=3)).replace(hour=0, minute=0, second=0)
        to_date = (now_dt + timedelta(days=1)).replace(hour=23, minute=59, second=59)

        # Insert transactions across dates
        await db.cash_transactions.insert_many(
            [
                {
                    "project_id": project_id,
                    "organisation_id": user["organisation_id"],
                    "category_id": "cat1",
                    "amount": FinancialEngine.to_d128("1000.00"),
                    "type": "CREDIT",
                    "transaction_date": from_date,
                },
                {
                    "project_id": project_id,
                    "organisation_id": user["organisation_id"],
                    "category_id": "cat1",
                    "amount": FinancialEngine.to_d128("300.00"),
                    "type": "DEBIT",
                    "transaction_date": from_date + timedelta(days=1),
                },
            ]
        )

        result = await service.get_cash_flow_statement(
            user,
            project_id,
            from_date.isoformat(),
            to_date.isoformat(),
        )

        assert result["project_id"] == project_id
        assert result["opening_balance"] == 0.0
        assert result["closing_balance"] == 700.0
        assert result["net_flow"] == 700.0
        assert len(result["daily_data"]) >= 1
