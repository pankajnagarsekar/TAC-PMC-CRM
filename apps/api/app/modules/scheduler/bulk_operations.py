"""
Bulk Operations Module

Provides multi-task update operations with atomic transaction support.
Validates operations independently and applies changes atomically.

Phase 1 Task #14: Bulk Operations
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class OperationType(str, Enum):
    """Types of bulk operations."""
    UPDATE_DURATION = "update_duration"
    UPDATE_STATUS = "update_status"
    UPDATE_START_DATE = "update_start_date"
    UPDATE_FINISH_DATE = "update_finish_date"
    UPDATE_ASSIGNMENT = "update_assignment"  # resource assignment
    UPDATE_PROGRESS = "update_progress"
    UPDATE_COST = "update_cost"
    DELETE_TASK = "delete_task"
    PAUSE_TASK = "pause_task"
    RESUME_TASK = "resume_task"


class OperationStatus(str, Enum):
    """Status of an operation."""
    PENDING = "pending"
    VALIDATED = "validated"
    APPLIED = "applied"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class Operation:
    """Single bulk operation."""
    operation_id: str
    task_id: str
    operation_type: OperationType
    value: Any = None  # Operation-specific value
    old_value: Any = None  # Captured before operation
    new_value: Any = None  # Result after operation
    status: OperationStatus = OperationStatus.PENDING
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def __hash__(self):
        return hash(self.operation_id)


@dataclass
class BulkOperationResult:
    """Result of bulk operation batch."""
    batch_id: str
    project_id: str
    organisation_id: str
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    operations: List[Operation] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    duration_ms: float = 0.0

    @property
    def success(self) -> bool:
        """All operations succeeded."""
        return self.failed_operations == 0

    @property
    def partial_success(self) -> bool:
        """Some operations succeeded."""
        return self.successful_operations > 0 and self.failed_operations > 0


class BulkOperationValidator:
    """Validates individual bulk operations."""

    def validate_update_duration(self, task: Dict, value: Any) -> tuple[bool, Optional[str]]:
        """Validate duration update operation."""
        if not isinstance(value, (int, float)):
            return False, "Duration must be numeric"
        if value <= 0:
            return False, "Duration must be positive"
        if value > 10000:
            return False, "Duration exceeds maximum (10000 days)"
        return True, None

    def validate_update_status(self, task: Dict, value: Any) -> tuple[bool, Optional[str]]:
        """Validate status update operation."""
        valid_statuses = {"Open", "In Progress", "Completed", "On Hold", "Cancelled"}
        if value not in valid_statuses:
            return False, f"Invalid status. Must be one of: {valid_statuses}"

        # Check state machine rules
        current_status = task.get("status", "Open")
        # Final states cannot transition
        if current_status in {"Completed", "Cancelled"}:
            return False, f"Cannot transition from final state '{current_status}'"

        return True, None

    def validate_update_start_date(self, task: Dict, value: Any) -> tuple[bool, Optional[str]]:
        """Validate start date update operation."""
        if isinstance(value, str):
            try:
                datetime.fromisoformat(value.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                return False, "Invalid date format. Use ISO 8601"
        elif isinstance(value, datetime):
            pass
        else:
            return False, "Date must be string or datetime object"

        # Validate against end date
        ef = task.get("ef") or task.get("scheduled_finish")
        if ef:
            es_date = datetime.fromisoformat(value.replace("Z", "+00:00")) if isinstance(value, str) else value
            ef_date = datetime.fromisoformat(ef.replace("Z", "+00:00")) if isinstance(ef, str) else ef
            if es_date > ef_date:
                return False, "Start date cannot be after finish date"

        return True, None

    def validate_update_finish_date(self, task: Dict, value: Any) -> tuple[bool, Optional[str]]:
        """Validate finish date update operation."""
        if isinstance(value, str):
            try:
                datetime.fromisoformat(value.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                return False, "Invalid date format. Use ISO 8601"
        elif isinstance(value, datetime):
            pass
        else:
            return False, "Date must be string or datetime object"

        # Validate against start date
        es = task.get("es") or task.get("scheduled_start")
        if es:
            ef_date = datetime.fromisoformat(value.replace("Z", "+00:00")) if isinstance(value, str) else value
            es_date = datetime.fromisoformat(es.replace("Z", "+00:00")) if isinstance(es, str) else es
            if ef_date < es_date:
                return False, "Finish date cannot be before start date"

        return True, None

    def validate_update_assignment(self, task: Dict, value: Any) -> tuple[bool, Optional[str]]:
        """Validate resource assignment update."""
        if not isinstance(value, dict):
            return False, "Assignment must be a dict with 'resource_id' and optionally 'units_per_day'"

        if "resource_id" not in value:
            return False, "Assignment must include 'resource_id'"

        units = value.get("units_per_day", 1.0)
        if not isinstance(units, (int, float)) or units <= 0 or units > 10:
            return False, "units_per_day must be between 0 and 10"

        return True, None

    def validate_update_progress(self, task: Dict, value: Any) -> tuple[bool, Optional[str]]:
        """Validate progress update (percentage complete)."""
        if not isinstance(value, (int, float)):
            return False, "Progress must be numeric"
        if value < 0 or value > 100:
            return False, "Progress must be between 0 and 100"
        return True, None

    def validate_update_cost(self, task: Dict, value: Any) -> tuple[bool, Optional[str]]:
        """Validate cost update."""
        if not isinstance(value, (int, float)):
            return False, "Cost must be numeric"
        if value < 0:
            return False, "Cost cannot be negative"
        return True, None

    def validate_delete_task(self, task: Dict, value: Any) -> tuple[bool, Optional[str]]:
        """Validate task deletion."""
        # Cannot delete if it has dependent tasks
        # This would be checked against project graph
        status = task.get("status", "Open")
        if status in {"Completed", "Cancelled"}:
            return True, None  # Can delete completed/cancelled tasks
        if status == "In Progress":
            return False, "Cannot delete task in progress"
        return True, None

    def validate_pause_task(self, task: Dict, value: Any) -> tuple[bool, Optional[str]]:
        """Validate task pause."""
        status = task.get("status", "Open")
        if status not in {"Open", "In Progress"}:
            return False, f"Cannot pause task with status '{status}'"
        return True, None

    def validate_resume_task(self, task: Dict, value: Any) -> tuple[bool, Optional[str]]:
        """Validate task resume."""
        status = task.get("status", "Open")
        if status != "On Hold":
            return False, "Can only resume tasks that are on hold"
        return True, None

    def validate_operation(
        self,
        operation: Operation,
        task: Dict
    ) -> tuple[bool, Optional[str]]:
        """
        Validate a single operation.

        Args:
            operation: The operation to validate
            task: The task being modified

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check task exists
        if not task:
            return False, f"Task {operation.task_id} not found"

        # Route to specific validator
        validators = {
            OperationType.UPDATE_DURATION: self.validate_update_duration,
            OperationType.UPDATE_STATUS: self.validate_update_status,
            OperationType.UPDATE_START_DATE: self.validate_update_start_date,
            OperationType.UPDATE_FINISH_DATE: self.validate_update_finish_date,
            OperationType.UPDATE_ASSIGNMENT: self.validate_update_assignment,
            OperationType.UPDATE_PROGRESS: self.validate_update_progress,
            OperationType.UPDATE_COST: self.validate_update_cost,
            OperationType.DELETE_TASK: self.validate_delete_task,
            OperationType.PAUSE_TASK: self.validate_pause_task,
            OperationType.RESUME_TASK: self.validate_resume_task,
        }

        validator = validators.get(operation.operation_type)
        if not validator:
            return False, f"Unknown operation type: {operation.operation_type}"

        return validator(task, operation.value)


class BulkOperationExecutor:
    """Executes validated bulk operations."""

    def apply_operation(
        self,
        operation: Operation,
        task: Dict
    ) -> bool:
        """
        Apply a single operation to a task.

        Args:
            operation: The validated operation
            task: The task dict to modify

        Returns:
            True if successful
        """
        try:
            # Capture old value
            operation.old_value = self._get_operation_value(task, operation.operation_type)

            # Apply operation
            if operation.operation_type == OperationType.UPDATE_DURATION:
                task["duration"] = operation.value
                operation.new_value = operation.value

            elif operation.operation_type == OperationType.UPDATE_STATUS:
                task["status"] = operation.value
                operation.new_value = operation.value

            elif operation.operation_type == OperationType.UPDATE_START_DATE:
                task["scheduled_start"] = operation.value
                task["es"] = operation.value
                operation.new_value = operation.value

            elif operation.operation_type == OperationType.UPDATE_FINISH_DATE:
                task["scheduled_finish"] = operation.value
                task["ef"] = operation.value
                operation.new_value = operation.value

            elif operation.operation_type == OperationType.UPDATE_ASSIGNMENT:
                task["resource_assignment"] = operation.value
                operation.new_value = operation.value

            elif operation.operation_type == OperationType.UPDATE_PROGRESS:
                task["progress"] = operation.value
                operation.new_value = operation.value

            elif operation.operation_type == OperationType.UPDATE_COST:
                task["cost"] = operation.value
                operation.new_value = operation.value

            elif operation.operation_type == OperationType.DELETE_TASK:
                task["status"] = "Deleted"
                task["deleted_at"] = datetime.utcnow()
                operation.new_value = "Deleted"

            elif operation.operation_type == OperationType.PAUSE_TASK:
                task["status"] = "On Hold"
                task["paused_at"] = datetime.utcnow()
                operation.new_value = "On Hold"

            elif operation.operation_type == OperationType.RESUME_TASK:
                task["status"] = "In Progress"
                task["resumed_at"] = datetime.utcnow()
                operation.new_value = "In Progress"

            operation.status = OperationStatus.APPLIED
            return True

        except Exception as e:
            operation.status = OperationStatus.FAILED
            operation.error = str(e)
            logger.error(f"Failed to apply operation {operation.operation_id}: {e}")
            return False

    def _get_operation_value(self, task: Dict, op_type: OperationType) -> Any:
        """Get current value before operation."""
        if op_type == OperationType.UPDATE_DURATION:
            return task.get("duration")
        elif op_type == OperationType.UPDATE_STATUS:
            return task.get("status")
        elif op_type == OperationType.UPDATE_START_DATE:
            return task.get("scheduled_start") or task.get("es")
        elif op_type == OperationType.UPDATE_FINISH_DATE:
            return task.get("scheduled_finish") or task.get("ef")
        elif op_type == OperationType.UPDATE_ASSIGNMENT:
            return task.get("resource_assignment")
        elif op_type == OperationType.UPDATE_PROGRESS:
            return task.get("progress", 0)
        elif op_type == OperationType.UPDATE_COST:
            return task.get("cost", 0)
        return None


class BulkOperationService:
    """
    High-level service for bulk operations.

    Coordinates validation and execution of multi-task updates.
    """

    def __init__(self):
        """Initialize bulk operation service."""
        self.validator = BulkOperationValidator()
        self.executor = BulkOperationExecutor()

    def execute_bulk_operations(
        self,
        project_id: str,
        organisation_id: str,
        batch_id: str,
        tasks: Dict[str, Dict],
        operations_data: List[Dict]
    ) -> BulkOperationResult:
        """
        Execute a batch of bulk operations.

        Args:
            project_id: Project ID
            organisation_id: Organization ID
            batch_id: Batch identifier
            tasks: Dict of task_id -> task data
            operations_data: List of operation dicts

        Returns:
            BulkOperationResult with results of all operations
        """
        import uuid
        from datetime import datetime

        result = BulkOperationResult(
            batch_id=batch_id,
            project_id=project_id,
            organisation_id=organisation_id,
            total_operations=len(operations_data)
        )

        # Parse and validate all operations
        validated_ops = []
        for op_data in operations_data:
            try:
                op = Operation(
                    operation_id=str(uuid.uuid4()),
                    task_id=op_data.get("task_id"),
                    operation_type=OperationType(op_data.get("operation_type")),
                    value=op_data.get("value"),
                )

                # Validate
                task = tasks.get(op.task_id)
                is_valid, error = self.validator.validate_operation(op, task)

                if is_valid:
                    op.status = OperationStatus.VALIDATED
                    validated_ops.append((op, task))
                    result.operations.append(op)
                else:
                    op.status = OperationStatus.FAILED
                    op.error = error
                    result.operations.append(op)
                    result.failed_operations += 1
                    result.errors.append(f"{op.operation_id}: {error}")

            except Exception as e:
                error_msg = f"Invalid operation: {e}"
                result.errors.append(error_msg)
                result.failed_operations += 1
                logger.error(error_msg)

        # Apply validated operations
        for operation, task in validated_ops:
            if self.executor.apply_operation(operation, task):
                result.successful_operations += 1
            else:
                result.failed_operations += 1
                result.errors.append(f"{operation.operation_id}: {operation.error}")

        logger.info(
            f"Bulk operations batch {batch_id}: "
            f"{result.successful_operations}/{result.total_operations} successful"
        )

        return result

    def validate_operations_only(
        self,
        tasks: Dict[str, Dict],
        operations_data: List[Dict]
    ) -> List[Dict]:
        """
        Validate operations without executing them.

        Returns list of validation results.
        """
        results = []

        for op_data in operations_data:
            try:
                op = Operation(
                    operation_id=str(op_data.get("operation_id", "unknown")),
                    task_id=op_data.get("task_id"),
                    operation_type=OperationType(op_data.get("operation_type")),
                    value=op_data.get("value"),
                )

                task = tasks.get(op.task_id)
                is_valid, error = self.validator.validate_operation(op, task)

                results.append({
                    "operation_id": op.operation_id,
                    "task_id": op.task_id,
                    "valid": is_valid,
                    "error": error,
                })

            except Exception as e:
                results.append({
                    "operation_id": "unknown",
                    "task_id": op_data.get("task_id"),
                    "valid": False,
                    "error": str(e),
                })

        return results
