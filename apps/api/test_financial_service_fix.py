"""
Test Suite: Budget Initialization 500 Error Fix

Tests for critical bugs fixed in financial_service.py:
1. Decimal128 BSON serialization in aggregation pipeline
2. Project query fallback validation
3. Master budget recalculation flow
"""

import pytest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from bson import ObjectId, Decimal128

from financial_service import FinancialRecalculationService


class TestDecimal128SerializationFix:
    """
    Verify that aggregation pipelines use raw BSON values, not Python objects.

    CRITICAL BUG: Line 209 was passing Decimal128("0.0") into aggregation spec,
    causing BSON serialization failure on MongoDB driver.
    """

    @pytest.mark.asyncio
    async def test_aggregation_pipeline_uses_raw_values(self):
        """Verify aggregation pipeline spec uses float not Decimal128"""
        # Arrange
        db_mock = MagicMock()
        service = FinancialRecalculationService(db_mock)

        # The aggregation result with empty remaining_budget should use 0.0 as default
        aggregate_mock = AsyncMock()
        aggregate_mock.to_list = AsyncMock(return_value=[
            {
                "total_original": Decimal128("1000.00"),
                "total_remaining": Decimal128("500.00")
            }
        ])

        db_mock.project_category_budgets.aggregate = MagicMock(
            return_value=aggregate_mock
        )
        db_mock.projects.find_one = AsyncMock(
            return_value={"_id": ObjectId(), "name": "Test Project"}
        )
        db_mock.projects.update_one = AsyncMock(
            return_value=MagicMock(matched_count=1, modified_count=1)
        )

        # Act
        result = await service.recalculate_master_budget("507f1f77bcf86cd799439011")

        # Assert
        # Verify pipeline was called (verify aggregation spec is correct)
        call_args = db_mock.project_category_budgets.aggregate.call_args
        pipeline = call_args[0][0] if call_args[0] else []

        # Find the $ifNull in the pipeline
        group_stage = next((s for s in pipeline if "$group" in s), None)
        if_null_expr = group_stage["$group"]["total_remaining"]["$sum"]["$ifNull"][1]

        # CRITICAL ASSERTION: Should be float, not Decimal128
        assert isinstance(if_null_expr, float), f"Expected float but got {type(if_null_expr)}"
        assert if_null_expr == 0.0, f"Expected 0.0 but got {if_null_expr}"

        # Verify result is correct
        assert result["master_original_budget"] == Decimal("1000.00")
        assert result["master_remaining_budget"] == Decimal("500.00")

    @pytest.mark.asyncio
    async def test_aggregation_pipeline_with_empty_results(self):
        """Verify pipeline handles empty budget collections gracefully"""
        # Arrange
        db_mock = MagicMock()
        service = FinancialRecalculationService(db_mock)

        aggregate_mock = AsyncMock()
        aggregate_mock.to_list = AsyncMock(return_value=[])  # Empty result

        db_mock.project_category_budgets.aggregate = MagicMock(
            return_value=aggregate_mock
        )
        db_mock.projects.find_one = AsyncMock(
            return_value={"_id": ObjectId()}
        )
        db_mock.projects.update_one = AsyncMock(
            return_value=MagicMock(matched_count=1, modified_count=1)
        )

        # Act
        result = await service.recalculate_master_budget("507f1f77bcf86cd799439011")

        # Assert
        assert result["master_original_budget"] == Decimal("0.0")
        assert result["master_remaining_budget"] == Decimal("0.0")


class TestProjectQueryFallbackValidation:
    """
    Verify that project query fallback is properly validated.

    CRITICAL BUG: Line 230-234 was updating project_query but never verifying
    project exists after the fallback, leading to failed updates without proper error.
    """

    @pytest.mark.asyncio
    async def test_objectid_project_query_succeeds(self):
        """Verify ObjectId format project lookup works"""
        # Arrange
        db_mock = MagicMock()
        service = FinancialRecalculationService(db_mock)
        project_id = "507f1f77bcf86cd799439011"  # Valid ObjectId string

        aggregate_mock = AsyncMock()
        aggregate_mock.to_list = AsyncMock(return_value=[
            {"total_original": Decimal128("1000"), "total_remaining": Decimal128("500")}
        ])

        db_mock.project_category_budgets.aggregate = MagicMock(
            return_value=aggregate_mock
        )
        db_mock.projects.find_one = AsyncMock(
            return_value={"_id": ObjectId(project_id), "name": "Test"}
        )
        db_mock.projects.update_one = AsyncMock(
            return_value=MagicMock(matched_count=1, modified_count=1)
        )

        # Act
        result = await service.recalculate_master_budget(project_id)

        # Assert
        assert result is not None
        # Verify find_one was called exactly once (ObjectId lookup succeeded)
        assert db_mock.projects.find_one.call_count == 1

    @pytest.mark.asyncio
    async def test_fallback_project_query_verifies_project_exists(self):
        """Verify fallback query properly checks project exists before update"""
        # Arrange
        db_mock = MagicMock()
        service = FinancialRecalculationService(db_mock)
        project_id = "invalid-project-id"  # Will fail ObjectId, trigger fallback

        aggregate_mock = AsyncMock()
        aggregate_mock.to_list = AsyncMock(return_value=[
            {"total_original": Decimal128("1000"), "total_remaining": Decimal128("500")}
        ])

        db_mock.project_category_budgets.aggregate = MagicMock(
            return_value=aggregate_mock
        )

        # First call (ObjectId) returns None, triggers fallback
        # Second call (string project_id) finds the project
        db_mock.projects.find_one = AsyncMock(
            return_value={"_id": ObjectId(), "project_id": project_id}
        )
        db_mock.projects.update_one = AsyncMock(
            return_value=MagicMock(matched_count=1, modified_count=1)
        )

        # Act
        result = await service.recalculate_master_budget(project_id)

        # Assert
        # CRITICAL: find_one should be called TWICE (first ObjectId, then fallback)
        assert db_mock.projects.find_one.call_count == 2, \
            f"Expected 2 find_one calls but got {db_mock.projects.find_one.call_count}"
        assert result is not None

    @pytest.mark.asyncio
    async def test_raises_exception_if_project_not_found(self):
        """Verify proper exception when project doesn't exist"""
        # Arrange
        db_mock = MagicMock()
        service = FinancialRecalculationService(db_mock)
        project_id = "nonexistent-project"

        aggregate_mock = AsyncMock()
        aggregate_mock.to_list = AsyncMock(return_value=[
            {"total_original": Decimal128("1000"), "total_remaining": Decimal128("500")}
        ])

        db_mock.project_category_budgets.aggregate = MagicMock(
            return_value=aggregate_mock
        )
        # Both lookups return None
        db_mock.projects.find_one = AsyncMock(return_value=None)

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await service.recalculate_master_budget(project_id)

        assert "project" in str(exc_info.value).lower()
        assert "not found" in str(exc_info.value).lower()


class TestFinancialStateDocumentSerialization:
    """
    Verify financial_state documents use Decimal128 for all numeric fields.

    BUG: Line 102 was storing Decimal objects instead of Decimal128,
    causing type inconsistencies in MongoDB.
    """

    @pytest.mark.asyncio
    async def test_financial_state_uses_decimal128(self):
        """Verify all numeric fields in financial_state are Decimal128"""
        # Arrange
        db_mock = MagicMock()
        service = FinancialRecalculationService(db_mock)
        project_id = "507f1f77bcf86cd799439011"
        category_id = "507f1f77bcf86cd799439012"

        # Mock budget
        db_mock.project_category_budgets.find_one = AsyncMock(
            return_value={
                "_id": ObjectId(),
                "original_budget": Decimal128("5000"),
                "category_id": category_id,
                "project_id": project_id
            }
        )

        # Mock aggregations
        def mock_aggregate(pipeline, session=None):
            mock = AsyncMock()
            mock.to_list = AsyncMock(return_value=[])  # No work orders/certs
            return mock

        db_mock.work_orders.aggregate = MagicMock(side_effect=mock_aggregate)
        db_mock.payment_certificates.aggregate = MagicMock(side_effect=mock_aggregate)
        db_mock.financial_state.update_one = AsyncMock()

        # Act
        await service.recalculate_project_code_financials(project_id, category_id)

        # Assert
        call_args = db_mock.financial_state.update_one.call_args
        update_doc = call_args[0][1]["$set"]

        # CRITICAL: Verify all monetary fields are Decimal128, not Decimal
        assert isinstance(update_doc["original_budget"], Decimal128), \
            f"original_budget should be Decimal128, got {type(update_doc['original_budget'])}"
        assert isinstance(update_doc["committed_value"], Decimal128), \
            f"committed_value should be Decimal128, got {type(update_doc['committed_value'])}"
        assert isinstance(update_doc["certified_value"], Decimal128), \
            f"certified_value should be Decimal128, got {type(update_doc['certified_value'])}"
        assert isinstance(update_doc["balance_budget_remaining"], Decimal128), \
            f"balance_budget_remaining should be Decimal128, got {type(update_doc['balance_budget_remaining'])}"


class TestBudgetInitializationFlow:
    """
    Integration test: Verify complete budget initialization flow works end-to-end.
    """

    @pytest.mark.asyncio
    async def test_initialize_budgets_completes_without_500_error(self):
        """Verify budget initialization completes successfully"""
        # Arrange
        db_mock = MagicMock()
        service = FinancialRecalculationService(db_mock)
        project_id = "507f1f77bcf86cd799439011"

        # Setup mocks
        db_mock.project_category_budgets.find = AsyncMock(
            return_value=AsyncMock(
                to_list=AsyncMock(return_value=[
                    {
                        "_id": ObjectId(),
                        "project_id": project_id,
                        "category_id": "507f1f77bcf86cd799439012",
                        "original_budget": Decimal128("1000"),
                        "version": 1
                    }
                ])
            )
        )

        db_mock.work_orders.aggregate = MagicMock(
            return_value=AsyncMock(to_list=AsyncMock(return_value=[]))
        )
        db_mock.payment_certificates.aggregate = MagicMock(
            return_value=AsyncMock(to_list=AsyncMock(return_value=[]))
        )

        db_mock.project_category_budgets.aggregate = MagicMock(
            return_value=AsyncMock(
                to_list=AsyncMock(return_value=[
                    {"total_original": Decimal128("1000"), "total_remaining": Decimal128("1000")}
                ])
            )
        )

        db_mock.projects.find_one = AsyncMock(
            return_value={"_id": ObjectId(project_id)}
        )

        db_mock.financial_state.update_one = AsyncMock()
        db_mock.projects.update_one = AsyncMock(
            return_value=MagicMock(matched_count=1, modified_count=1)
        )

        # Act
        result_all = await service.recalculate_all_project_financials(project_id)
        result_master = await service.recalculate_master_budget(project_id)

        # Assert
        assert result_all is not None
        assert result_all["categories_recalculated"] == 1
        assert result_master is not None
        assert result_master["master_original_budget"] == Decimal("1000")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
