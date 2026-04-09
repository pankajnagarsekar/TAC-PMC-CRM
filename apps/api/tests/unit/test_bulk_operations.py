"""
Unit Tests: Bulk Operations Module

Tests for Phase 1 Task #14: Bulk Operations
- Multi-task update operations with validation
- Atomic transaction support
- Operation type validation
- Status transitions
"""

import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from app.modules.scheduler.bulk_operations import (
    BulkOperationService,
    BulkOperationValidator,
    BulkOperationExecutor,
    Operation,
    OperationType,
    OperationStatus,
    BulkOperationResult,
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def service():
    """Create bulk operation service."""
    return BulkOperationService()


@pytest.fixture
def validator():
    """Create operation validator."""
    return BulkOperationValidator()


@pytest.fixture
def executor():
    """Create operation executor."""
    return BulkOperationExecutor()


@pytest.fixture
def base_date():
    """Base date for operations."""
    return datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def sample_tasks(base_date):
    """Sample tasks for testing."""
    return {
        "T1": {
            "task_id": "T1",
            "task_name": "Task 1",
            "duration": 5,
            "status": "Open",
            "scheduled_start": base_date,
            "scheduled_finish": base_date + timedelta(days=4),
            "progress": 0,
            "cost": 1000.0,
        },
        "T2": {
            "task_id": "T2",
            "task_name": "Task 2",
            "duration": 10,
            "status": "In Progress",
            "scheduled_start": base_date + timedelta(days=5),
            "scheduled_finish": base_date + timedelta(days=14),
            "progress": 50,
            "cost": 2000.0,
        },
        "T3": {
            "task_id": "T3",
            "task_name": "Task 3",
            "duration": 8,
            "status": "Completed",
            "scheduled_start": base_date - timedelta(days=10),
            "scheduled_finish": base_date - timedelta(days=2),
            "progress": 100,
            "cost": 1500.0,
        },
    }


# ============================================================================
# TEST: Validator - Duration Updates
# ============================================================================

class TestValidateDuration:
    """Test duration update validation."""

    def test_valid_duration_update(self, validator, sample_tasks):
        """Valid duration accepts numeric positive value."""
        task = sample_tasks["T1"]
        is_valid, error = validator.validate_update_duration(task, 10)
        assert is_valid
        assert error is None

    def test_invalid_duration_not_numeric(self, validator, sample_tasks):
        """Non-numeric duration rejected."""
        task = sample_tasks["T1"]
        is_valid, error = validator.validate_update_duration(task, "ten days")
        assert not is_valid
        assert "numeric" in error

    def test_invalid_duration_negative(self, validator, sample_tasks):
        """Negative duration rejected."""
        task = sample_tasks["T1"]
        is_valid, error = validator.validate_update_duration(task, -5)
        assert not is_valid
        assert "positive" in error

    def test_invalid_duration_zero(self, validator, sample_tasks):
        """Zero duration rejected."""
        task = sample_tasks["T1"]
        is_valid, error = validator.validate_update_duration(task, 0)
        assert not is_valid

    def test_invalid_duration_exceeds_max(self, validator, sample_tasks):
        """Duration exceeding max rejected."""
        task = sample_tasks["T1"]
        is_valid, error = validator.validate_update_duration(task, 15000)
        assert not is_valid
        assert "maximum" in error

    def test_valid_fractional_duration(self, validator, sample_tasks):
        """Fractional durations accepted."""
        task = sample_tasks["T1"]
        is_valid, error = validator.validate_update_duration(task, 2.5)
        assert is_valid


# ============================================================================
# TEST: Validator - Status Updates
# ============================================================================

class TestValidateStatus:
    """Test status update validation."""

    def test_valid_status_transitions(self, validator, sample_tasks):
        """Valid status transitions accepted."""
        task = sample_tasks["T1"]  # Currently "Open"

        for status in ["In Progress", "On Hold", "Cancelled"]:
            is_valid, error = validator.validate_update_status(task, status)
            assert is_valid, f"Status {status} should be valid"

    def test_invalid_status_value(self, validator, sample_tasks):
        """Invalid status rejected."""
        task = sample_tasks["T1"]
        is_valid, error = validator.validate_update_status(task, "Invalid")
        assert not is_valid
        assert "Invalid status" in error

    def test_cannot_transition_from_completed(self, validator, sample_tasks):
        """Cannot transition from completed status."""
        task = sample_tasks["T3"]  # Status is "Completed"
        is_valid, error = validator.validate_update_status(task, "Open")
        assert not is_valid
        assert "final state" in error

    def test_cannot_transition_from_cancelled(self, validator, sample_tasks):
        """Cannot transition from cancelled status."""
        task = sample_tasks["T1"].copy()
        task["status"] = "Cancelled"
        is_valid, error = validator.validate_update_status(task, "Open")
        assert not is_valid


# ============================================================================
# TEST: Validator - Date Updates
# ============================================================================

class TestValidateDateUpdates:
    """Test date update validation."""

    def test_valid_start_date_iso_string(self, validator, sample_tasks):
        """ISO string start date accepted."""
        task = sample_tasks["T1"]
        is_valid, error = validator.validate_update_start_date(
            task,
            "2024-01-02T00:00:00Z"  # Before finish date
        )
        assert is_valid

    def test_valid_start_date_datetime_object(self, validator, sample_tasks):
        """Datetime object start date accepted."""
        task = sample_tasks["T1"]
        new_date = datetime(2024, 1, 2, 0, 0, 0, tzinfo=timezone.utc)  # Before finish
        is_valid, error = validator.validate_update_start_date(task, new_date)
        assert is_valid

    def test_invalid_start_date_format(self, validator, sample_tasks):
        """Invalid date format rejected."""
        task = sample_tasks["T1"]
        is_valid, error = validator.validate_update_start_date(task, "invalid-date")
        assert not is_valid
        assert "ISO 8601" in error

    def test_start_date_after_finish_rejected(self, validator, sample_tasks, base_date):
        """Start date after finish date rejected."""
        task = sample_tasks["T1"]
        is_valid, error = validator.validate_update_start_date(
            task,
            base_date + timedelta(days=10)  # After finish date
        )
        assert not is_valid
        assert "Start date cannot be after finish date" in error

    def test_valid_finish_date(self, validator, sample_tasks):
        """Valid finish date accepted."""
        task = sample_tasks["T1"]
        is_valid, error = validator.validate_update_finish_date(
            task,
            "2024-01-20T00:00:00Z"
        )
        assert is_valid

    def test_finish_date_before_start_rejected(self, validator, sample_tasks, base_date):
        """Finish date before start date rejected."""
        task = sample_tasks["T1"]
        is_valid, error = validator.validate_update_finish_date(
            task,
            base_date - timedelta(days=5)  # Before start date
        )
        assert not is_valid


# ============================================================================
# TEST: Validator - Assignment Updates
# ============================================================================

class TestValidateAssignment:
    """Test resource assignment validation."""

    def test_valid_assignment(self, validator, sample_tasks):
        """Valid assignment accepted."""
        task = sample_tasks["T1"]
        assignment = {"resource_id": "R1", "units_per_day": 1.0}
        is_valid, error = validator.validate_update_assignment(task, assignment)
        assert is_valid

    def test_valid_assignment_without_units(self, validator, sample_tasks):
        """Assignment without units defaults to 1.0."""
        task = sample_tasks["T1"]
        assignment = {"resource_id": "R1"}
        is_valid, error = validator.validate_update_assignment(task, assignment)
        assert is_valid

    def test_invalid_assignment_not_dict(self, validator, sample_tasks):
        """Non-dict assignment rejected."""
        task = sample_tasks["T1"]
        is_valid, error = validator.validate_update_assignment(task, "R1")
        assert not is_valid

    def test_invalid_assignment_missing_resource_id(self, validator, sample_tasks):
        """Assignment without resource_id rejected."""
        task = sample_tasks["T1"]
        assignment = {"units_per_day": 1.0}
        is_valid, error = validator.validate_update_assignment(task, assignment)
        assert not is_valid

    def test_invalid_assignment_negative_units(self, validator, sample_tasks):
        """Negative units rejected."""
        task = sample_tasks["T1"]
        assignment = {"resource_id": "R1", "units_per_day": -0.5}
        is_valid, error = validator.validate_update_assignment(task, assignment)
        assert not is_valid

    def test_invalid_assignment_excessive_units(self, validator, sample_tasks):
        """Units exceeding max rejected."""
        task = sample_tasks["T1"]
        assignment = {"resource_id": "R1", "units_per_day": 15}
        is_valid, error = validator.validate_update_assignment(task, assignment)
        assert not is_valid


# ============================================================================
# TEST: Validator - Progress & Cost
# ============================================================================

class TestValidateProgressAndCost:
    """Test progress and cost validation."""

    def test_valid_progress(self, validator, sample_tasks):
        """Valid progress (0-100) accepted."""
        task = sample_tasks["T1"]
        for progress in [0, 50, 100]:
            is_valid, error = validator.validate_update_progress(task, progress)
            assert is_valid

    def test_invalid_progress_negative(self, validator, sample_tasks):
        """Negative progress rejected."""
        task = sample_tasks["T1"]
        is_valid, error = validator.validate_update_progress(task, -10)
        assert not is_valid

    def test_invalid_progress_exceeds_100(self, validator, sample_tasks):
        """Progress over 100 rejected."""
        task = sample_tasks["T1"]
        is_valid, error = validator.validate_update_progress(task, 150)
        assert not is_valid

    def test_valid_cost(self, validator, sample_tasks):
        """Valid positive cost accepted."""
        task = sample_tasks["T1"]
        is_valid, error = validator.validate_update_cost(task, 5000)
        assert is_valid

    def test_invalid_cost_negative(self, validator, sample_tasks):
        """Negative cost rejected."""
        task = sample_tasks["T1"]
        is_valid, error = validator.validate_update_cost(task, -1000)
        assert not is_valid


# ============================================================================
# TEST: Validator - Task Lifecycle Operations
# ============================================================================

class TestValidateLifecycleOperations:
    """Test task lifecycle operation validation."""

    def test_valid_delete_open_task(self, validator, sample_tasks):
        """Can delete open task."""
        task = sample_tasks["T1"]  # Status is "Open"
        is_valid, error = validator.validate_delete_task(task, None)
        assert is_valid

    def test_valid_delete_completed_task(self, validator, sample_tasks):
        """Can delete completed task."""
        task = sample_tasks["T3"]  # Status is "Completed"
        is_valid, error = validator.validate_delete_task(task, None)
        assert is_valid

    def test_invalid_delete_in_progress_task(self, validator, sample_tasks):
        """Cannot delete task in progress."""
        task = sample_tasks["T2"]  # Status is "In Progress"
        is_valid, error = validator.validate_delete_task(task, None)
        assert not is_valid

    def test_valid_pause_open_task(self, validator, sample_tasks):
        """Can pause open task."""
        task = sample_tasks["T1"]  # Status is "Open"
        is_valid, error = validator.validate_pause_task(task, None)
        assert is_valid

    def test_valid_pause_in_progress_task(self, validator, sample_tasks):
        """Can pause in-progress task."""
        task = sample_tasks["T2"]  # Status is "In Progress"
        is_valid, error = validator.validate_pause_task(task, None)
        assert is_valid

    def test_invalid_pause_completed_task(self, validator, sample_tasks):
        """Cannot pause completed task."""
        task = sample_tasks["T3"]  # Status is "Completed"
        is_valid, error = validator.validate_pause_task(task, None)
        assert not is_valid

    def test_valid_resume_on_hold_task(self, validator):
        """Can resume task on hold."""
        task = {"task_id": "T", "status": "On Hold"}
        is_valid, error = validator.validate_resume_task(task, None)
        assert is_valid

    def test_invalid_resume_open_task(self, validator, sample_tasks):
        """Cannot resume open task."""
        task = sample_tasks["T1"]  # Status is "Open"
        is_valid, error = validator.validate_resume_task(task, None)
        assert not is_valid


# ============================================================================
# TEST: Executor - Apply Operations
# ============================================================================

class TestExecutorApplyOperations:
    """Test operation execution."""

    def test_apply_duration_update(self, executor, sample_tasks):
        """Duration update applied correctly."""
        task = sample_tasks["T1"].copy()
        operation = Operation(
            operation_id="op1",
            task_id="T1",
            operation_type=OperationType.UPDATE_DURATION,
            value=15,
        )

        result = executor.apply_operation(operation, task)
        assert result
        assert task["duration"] == 15
        assert operation.old_value == 5
        assert operation.new_value == 15
        assert operation.status == OperationStatus.APPLIED

    def test_apply_status_update(self, executor, sample_tasks):
        """Status update applied correctly."""
        task = sample_tasks["T1"].copy()
        operation = Operation(
            operation_id="op2",
            task_id="T1",
            operation_type=OperationType.UPDATE_STATUS,
            value="In Progress",
        )

        result = executor.apply_operation(operation, task)
        assert result
        assert task["status"] == "In Progress"
        assert operation.old_value == "Open"

    def test_apply_progress_update(self, executor, sample_tasks):
        """Progress update applied correctly."""
        task = sample_tasks["T1"].copy()
        operation = Operation(
            operation_id="op3",
            task_id="T1",
            operation_type=OperationType.UPDATE_PROGRESS,
            value=75,
        )

        result = executor.apply_operation(operation, task)
        assert result
        assert task["progress"] == 75

    def test_apply_delete_task(self, executor, sample_tasks):
        """Delete operation marks task as deleted."""
        task = sample_tasks["T1"].copy()
        operation = Operation(
            operation_id="op4",
            task_id="T1",
            operation_type=OperationType.DELETE_TASK,
        )

        result = executor.apply_operation(operation, task)
        assert result
        assert task["status"] == "Deleted"
        assert "deleted_at" in task

    def test_apply_pause_task(self, executor, sample_tasks):
        """Pause operation sets status to on hold."""
        task = sample_tasks["T1"].copy()
        operation = Operation(
            operation_id="op5",
            task_id="T1",
            operation_type=OperationType.PAUSE_TASK,
        )

        result = executor.apply_operation(operation, task)
        assert result
        assert task["status"] == "On Hold"

    def test_apply_resume_task(self, executor):
        """Resume operation sets status to in progress."""
        task = {"task_id": "T", "status": "On Hold"}
        operation = Operation(
            operation_id="op6",
            task_id="T",
            operation_type=OperationType.RESUME_TASK,
        )

        result = executor.apply_operation(operation, task)
        assert result
        assert task["status"] == "In Progress"


# ============================================================================
# TEST: Service - Bulk Operations
# ============================================================================

class TestServiceBulkOperations:
    """Test bulk operation service."""

    def test_execute_single_valid_operation(self, service, sample_tasks):
        """Single valid operation executes successfully."""
        operations_data = [
            {
                "task_id": "T1",
                "operation_type": OperationType.UPDATE_DURATION.value,
                "value": 10,
            }
        ]

        result = service.execute_bulk_operations(
            project_id="proj-1",
            organisation_id="org-1",
            batch_id="batch-1",
            tasks=sample_tasks,
            operations_data=operations_data,
        )

        assert result.successful_operations == 1
        assert result.failed_operations == 0
        assert result.success

    def test_execute_multiple_operations(self, service, sample_tasks):
        """Multiple operations executed independently."""
        operations_data = [
            {
                "task_id": "T1",
                "operation_type": OperationType.UPDATE_DURATION.value,
                "value": 10,
            },
            {
                "task_id": "T2",
                "operation_type": OperationType.UPDATE_STATUS.value,
                "value": "Completed",
            },
            {
                "task_id": "T3",
                "operation_type": OperationType.UPDATE_PROGRESS.value,
                "value": 100,
            },
        ]

        result = service.execute_bulk_operations(
            project_id="proj-1",
            organisation_id="org-1",
            batch_id="batch-2",
            tasks=sample_tasks,
            operations_data=operations_data,
        )

        assert result.successful_operations == 3
        assert result.failed_operations == 0

    def test_execute_mixed_valid_invalid_operations(self, service, sample_tasks):
        """Partial success when some operations fail validation."""
        operations_data = [
            {
                "task_id": "T1",
                "operation_type": OperationType.UPDATE_DURATION.value,
                "value": 10,
            },
            {
                "task_id": "T2",
                "operation_type": OperationType.UPDATE_PROGRESS.value,
                "value": 150,  # Invalid: > 100
            },
            {
                "task_id": "T1",
                "operation_type": OperationType.UPDATE_STATUS.value,
                "value": "In Progress",
            },
        ]

        result = service.execute_bulk_operations(
            project_id="proj-1",
            organisation_id="org-1",
            batch_id="batch-3",
            tasks=sample_tasks,
            operations_data=operations_data,
        )

        assert result.successful_operations == 2
        assert result.failed_operations == 1
        assert result.partial_success

    def test_execute_all_invalid_operations(self, service, sample_tasks):
        """All operations fail validation."""
        operations_data = [
            {
                "task_id": "T1",
                "operation_type": OperationType.UPDATE_DURATION.value,
                "value": -5,  # Invalid: negative
            },
            {
                "task_id": "T2",
                "operation_type": OperationType.UPDATE_STATUS.value,
                "value": "Invalid Status",
            },
        ]

        result = service.execute_bulk_operations(
            project_id="proj-1",
            organisation_id="org-1",
            batch_id="batch-4",
            tasks=sample_tasks,
            operations_data=operations_data,
        )

        assert result.successful_operations == 0
        assert result.failed_operations == 2
        assert not result.success

    def test_execute_nonexistent_task(self, service, sample_tasks):
        """Operation on nonexistent task fails validation."""
        operations_data = [
            {
                "task_id": "NONEXISTENT",
                "operation_type": OperationType.UPDATE_DURATION.value,
                "value": 10,
            }
        ]

        result = service.execute_bulk_operations(
            project_id="proj-1",
            organisation_id="org-1",
            batch_id="batch-5",
            tasks=sample_tasks,
            operations_data=operations_data,
        )

        assert result.failed_operations == 1
        assert "not found" in result.errors[0].lower()

    def test_validate_operations_only(self, service, sample_tasks):
        """Validate without executing."""
        operations_data = [
            {
                "operation_id": "op-1",
                "task_id": "T1",
                "operation_type": OperationType.UPDATE_DURATION.value,
                "value": 10,
            },
            {
                "operation_id": "op-2",
                "task_id": "T1",
                "operation_type": OperationType.UPDATE_DURATION.value,
                "value": -5,  # Invalid
            },
        ]

        results = service.validate_operations_only(sample_tasks, operations_data)

        assert len(results) == 2
        assert results[0]["valid"]
        assert not results[1]["valid"]


# ============================================================================
# TEST: Result Structure
# ============================================================================

class TestBulkOperationResult:
    """Test BulkOperationResult structure."""

    def test_result_success_flag(self):
        """Success flag is true when no failed operations."""
        result = BulkOperationResult(
            batch_id="batch-1",
            project_id="proj-1",
            organisation_id="org-1",
            total_operations=3,
            successful_operations=3,
            failed_operations=0,
        )
        assert result.success

    def test_result_partial_success_flag(self):
        """Partial success when some succeed and some fail."""
        result = BulkOperationResult(
            batch_id="batch-2",
            project_id="proj-1",
            organisation_id="org-1",
            total_operations=3,
            successful_operations=2,
            failed_operations=1,
        )
        assert result.partial_success
        assert not result.success

    def test_result_all_failed(self):
        """No partial success when all fail."""
        result = BulkOperationResult(
            batch_id="batch-3",
            project_id="proj-1",
            organisation_id="org-1",
            total_operations=3,
            successful_operations=0,
            failed_operations=3,
        )
        assert not result.partial_success
        assert not result.success
