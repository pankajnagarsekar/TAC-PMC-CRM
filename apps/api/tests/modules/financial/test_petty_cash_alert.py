import pytest
from decimal import Decimal
from bson import ObjectId
from unittest.mock import AsyncMock, MagicMock

from app.modules.financial.application.cash_service import CashService
from app.modules.shared.domain.financial_engine import FinancialEngine
from app.modules.shared.application.audit_service import AuditService


@pytest.fixture
async def setup_petty_cash_env(test_db, test_user):
    """Setup project, category and other defaults for petty cash threshold alert tests."""
    project_id = str(ObjectId())
    category_id = str(ObjectId())

    # Create category with name containing 'petty'
    await test_db.code_master.insert_one({
        "_id": ObjectId(category_id),
        "organisation_id": test_user["organisation_id"],
        "category_name": "Site Petty Cash Category",
        "budget_type": "fund_transfer",
        "active_status": True
    })

    # Create project with threshold_petty set to 10000.0
    await test_db.projects.insert_one({
        "_id": ObjectId(project_id),
        "project_id": project_id,
        "project_name": "Test Petty Cash Alert Project",
        "organisation_id": test_user["organisation_id"],
        "threshold_petty": 10000.0
    })

    return project_id, category_id


@pytest.mark.asyncio
async def test_petty_cash_alert_breach_and_resolution(test_db, test_user, setup_petty_cash_env):
    """
    Test transition flow:
    1. CREDIT cash above threshold (₹15,000 > ₹10,000). No alert should be logged.
    2. DEBIT cash below threshold (₹9,000 <= ₹10,000). A BREACH alert must be logged.
    3. Another DEBIT cash further below threshold (₹7,000 <= ₹10,000). No new alert (prevent duplicate logging).
    4. CREDIT cash back above threshold (₹12,000 > ₹10,000). A RESOLVE alert must be logged.
    """
    project_id, category_id = setup_petty_cash_env
    user = test_user

    permission_mock = AsyncMock()
    permission_mock.check_write_access_with_role = AsyncMock()
    
    audit_service = AuditService(test_db)
    cash_service = CashService(test_db, permission_mock, audit_service)

    # Clean existing audit logs just in case
    await test_db.audit_logs.delete_many({"project_id": project_id})

    # Step 1: Initial Credit of ₹15,000
    credit_txn = {
        "project_id": project_id,
        "category_id": category_id,
        "amount": Decimal("15000.00"),
        "type": "CREDIT",
        "description": "Initial funding above threshold"
    }
    await cash_service.create_cash_transaction(user, project_id, credit_txn, None)

    # Check alert logs - should be empty since balance ₹15,000 > threshold ₹10,000
    alerts = await test_db.audit_logs.find({
        "project_id": project_id,
        "entity_type": "PETTY_CASH_ALERT"
    }).to_list(None)
    assert len(alerts) == 0

    # Step 2: Debit of ₹6,000 -> Cash In Hand becomes ₹9,000 (Breached)
    debit_txn = {
        "project_id": project_id,
        "category_id": category_id,
        "amount": Decimal("6000.00"),
        "type": "DEBIT",
        "description": "First debit below threshold"
    }
    await cash_service.create_cash_transaction(user, project_id, debit_txn, None)

    alerts = await test_db.audit_logs.find({
        "project_id": project_id,
        "entity_type": "PETTY_CASH_ALERT"
    }).to_list(None)
    assert len(alerts) == 1
    assert alerts[0]["action_type"] == "BREACH"
    assert alerts[0]["new_value_json"]["cash_in_hand"] == 9000.0

    # Step 3: Second Debit of ₹2,000 -> Cash In Hand becomes ₹7,000 (Still Breached, no new log)
    debit_txn_2 = {
        "project_id": project_id,
        "category_id": category_id,
        "amount": Decimal("2000.00"),
        "type": "DEBIT",
        "description": "Second debit below threshold"
    }
    await cash_service.create_cash_transaction(user, project_id, debit_txn_2, None)

    alerts = await test_db.audit_logs.find({
        "project_id": project_id,
        "entity_type": "PETTY_CASH_ALERT"
    }).to_list(None)
    assert len(alerts) == 1  # Should still be exactly 1 alert log

    # Step 4: Credit of ₹5,000 -> Cash In Hand becomes ₹12,000 (Resolved)
    credit_txn_2 = {
        "project_id": project_id,
        "category_id": category_id,
        "amount": Decimal("5000.00"),
        "type": "CREDIT",
        "description": "Replenishment above threshold"
    }
    await cash_service.create_cash_transaction(user, project_id, credit_txn_2, None)

    alerts = await test_db.audit_logs.find({
        "project_id": project_id,
        "entity_type": "PETTY_CASH_ALERT"
    }).sort([("timestamp", 1)]).to_list(None)
    assert len(alerts) == 2
    assert alerts[1]["action_type"] == "RESOLVE"
    assert alerts[1]["new_value_json"]["cash_in_hand"] == 12000.0
