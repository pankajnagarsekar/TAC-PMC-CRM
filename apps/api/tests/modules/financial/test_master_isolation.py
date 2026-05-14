import pytest
from unittest.mock import MagicMock, AsyncMock
from app.modules.financial.infrastructure.repository import FinancialStateRepository
from app.modules.shared.domain.financial_engine import FinancialEngine


@pytest.mark.asyncio
async def test_list_categorical_states_excludes_master():
    # Setup
    db = MagicMock()
    repo = FinancialStateRepository(db)

    # Mock data with both categorical and MASTER records
    mock_records = [
        {"category_id": "CAT-001", "original_budget": 100},
        {"category_id": "CAT-002", "original_budget": 200},
        {"category_id": FinancialEngine.MASTER_CATEGORY, "original_budget": 300},
    ]

    # Mock the list method which is called by list_categorical_states
    repo.list = AsyncMock(return_value=[r for r in mock_records if r["category_id"] != FinancialEngine.MASTER_CATEGORY])

    # Execute
    project_id = "proj-123"
    categorical_states = await repo.list_categorical_states(project_id)

    # Assert
    assert len(categorical_states) == 2
    assert all(s["category_id"] != FinancialEngine.MASTER_CATEGORY for s in categorical_states)

    # Verify the query passed to repo.list
    repo.list.assert_called_once()
    query = repo.list.call_args[0][0]
    assert query["category_id"]["$ne"] == FinancialEngine.MASTER_CATEGORY


@pytest.mark.asyncio
async def test_get_master_state_fetches_only_master():
    # Setup
    db = MagicMock()
    repo = FinancialStateRepository(db)

    # Mock find_one
    repo.find_one = AsyncMock(return_value={"category_id": FinancialEngine.MASTER_CATEGORY, "original_budget": 300})

    # Execute
    project_id = "proj-123"
    master_state = await repo.get_master_state(project_id)

    # Assert
    assert master_state["category_id"] == FinancialEngine.MASTER_CATEGORY

    # Verify query
    repo.find_one.assert_called_once()
    query = repo.find_one.call_args[0][0]
    assert query["category_id"] == FinancialEngine.MASTER_CATEGORY
