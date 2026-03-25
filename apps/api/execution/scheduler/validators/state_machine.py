"""
Task State Machine validator.
Enforces valid task status transitions (Constitution §5).
Validates transition pre-conditions (requires actual_start for IN_PROGRESS, etc.)

Constitution Reference: §5 (state machine), §4 Step 1 (input validation)
Schema Reference: §1.3 (task_status), §4.1 (pre-save validators)
"""
from dataclasses import dataclass
from typing import Optional
from datetime import date

from ..models.shared_types import TaskStatus, TASK_STATE_TRANSITIONS


# =============================================================================
# Input / Output contracts
# =============================================================================

@dataclass
class StateMachineInput:
    """Context passed to the state machine validator."""
    current_status: TaskStatus
    target_status: TaskStatus
    task_id: str

    # Execution fields needed for transition pre-condition checks
    actual_start: Optional[date] = None
    actual_finish: Optional[date] = None
    percent_complete: int = 0


@dataclass
class StateMachineResult:
    """Result of a state transition validation."""
    is_valid: bool
    from_status: TaskStatus
    to_status: TaskStatus
    error_message: Optional[str] = None

    # Side effects the API must apply when transition is approved
    # e.g. reopen clears actual_finish and resets percent_complete
    side_effects: Optional[dict] = None


# =============================================================================
# Validator
# =============================================================================

def validate_state_transition(input_data: StateMachineInput) -> StateMachineResult:
    """
    Validates a task status transition and returns any required side effects.

    Transition Rules (Constitution §5):
    ─────────────────────────────────────────────────────────────────
    DRAFT → NOT_STARTED
        Happens automatically on first successful CPM run.
        No pre-conditions.

    NOT_STARTED → IN_PROGRESS
        Requires: actual_start date set.

    IN_PROGRESS → COMPLETED
        Requires: percent_complete == 100 AND actual_finish set.

    COMPLETED → IN_PROGRESS  (reopen)
        Side effects: reset actual_finish to null, set percent_complete < 100.
        API must apply these side effects to the task document.

    COMPLETED → CLOSED
        Requires: admin approval (enforced at API layer, not here).
        State machine approves the transition; API checks role.

    CLOSED
        Terminal state. No transitions allowed from CLOSED.
    ─────────────────────────────────────────────────────────────────

    Args:
        input_data: StateMachineInput with current/target status and task fields

    Returns:
        StateMachineResult — is_valid=True if transition is allowed,
        with side_effects dict if the API must make additional field changes.
    """
    current = input_data.current_status
    target = input_data.target_status

    # No-op: transitioning to the same state
    if current == target:
        return StateMachineResult(
            is_valid=True,
            from_status=current,
            to_status=target,
        )

    # Check transition table
    allowed_targets = TASK_STATE_TRANSITIONS.get(current, set())
    if target not in allowed_targets:
        return StateMachineResult(
            is_valid=False,
            from_status=current,
            to_status=target,
            error_message=(
                f"Invalid state transition for task {input_data.task_id}: "
                f"{current.value} → {target.value}. "
                f"Allowed transitions from {current.value}: "
                f"{[s.value for s in allowed_targets] or ['(none — terminal state)']}"
            ),
        )

    # Pre-condition checks per transition
    # ─────────────────────────────────────
    # NOT_STARTED → IN_PROGRESS: requires actual_start
    if current == TaskStatus.NOT_STARTED and target == TaskStatus.IN_PROGRESS:
        if not input_data.actual_start:
            return StateMachineResult(
                is_valid=False,
                from_status=current,
                to_status=target,
                error_message=(
                    f"Transition {current.value} → {target.value} requires "
                    f"actual_start to be set on task {input_data.task_id}"
                ),
            )

    # IN_PROGRESS → COMPLETED: requires 100% complete AND actual_finish
    if current == TaskStatus.IN_PROGRESS and target == TaskStatus.COMPLETED:
        if input_data.percent_complete != 100:
            return StateMachineResult(
                is_valid=False,
                from_status=current,
                to_status=target,
                error_message=(
                    f"Transition {current.value} → {target.value} requires "
                    f"percent_complete == 100 (currently {input_data.percent_complete}) "
                    f"on task {input_data.task_id}"
                ),
            )
        if not input_data.actual_finish:
            return StateMachineResult(
                is_valid=False,
                from_status=current,
                to_status=target,
                error_message=(
                    f"Transition {current.value} → {target.value} requires "
                    f"actual_finish to be set on task {input_data.task_id}"
                ),
            )

    # COMPLETED → IN_PROGRESS (reopen): side effects
    side_effects = None
    if current == TaskStatus.COMPLETED and target == TaskStatus.IN_PROGRESS:
        # Constitution §5: "resets actual_finish to null, sets percent_complete < 100"
        # We set percent_complete to 99 as a sensible reopen default.
        # The user can immediately edit it.
        side_effects = {
            "actual_finish": None,
            "percent_complete": 99,
        }

    return StateMachineResult(
        is_valid=True,
        from_status=current,
        to_status=target,
        side_effects=side_effects,
    )


# =============================================================================
# Batch validation helper (used during import / bulk updates)
# =============================================================================

@dataclass
class BatchStateMachineResult:
    all_valid: bool
    results: list  # List[StateMachineResult]
    failure_count: int


def validate_batch_transitions(inputs: list) -> BatchStateMachineResult:
    """
    Validates multiple state transitions in a single pass.
    Used during import and bulk schedule updates.

    Args:
        inputs: List[StateMachineInput]

    Returns:
        BatchStateMachineResult with all_valid flag and per-item results.
        If any transition is invalid, all_valid is False.
        The API layer must reject the entire batch (no partial commits).
    """
    results = [validate_state_transition(inp) for inp in inputs]
    failures = [r for r in results if not r.is_valid]

    return BatchStateMachineResult(
        all_valid=len(failures) == 0,
        results=results,
        failure_count=len(failures),
    )
