import pytest
from app.modules.shared.domain.state_machine import StateMachine
from app.modules.shared.domain.exceptions import DataFreezeError, IllegalTransitionError
from app.modules.tasks.domain.types import TaskStatus


def test_task_open_to_in_progress_transition_valid():
    """Test valid transition from Open to In Progress."""
    result = StateMachine.validate_transition("TASK", TaskStatus.OPEN.value, TaskStatus.IN_PROGRESS.value)
    assert result is True


def test_task_open_to_closed_transition_valid():
    """Test valid direct transition from Open to Closed."""
    result = StateMachine.validate_transition("TASK", TaskStatus.OPEN.value, TaskStatus.CLOSED.value)
    assert result is True


def test_task_in_progress_to_completed_transition_valid():
    """Test valid transition from In Progress to Completed."""
    result = StateMachine.validate_transition("TASK", TaskStatus.IN_PROGRESS.value, TaskStatus.COMPLETED.value)
    assert result is True


def test_task_completed_to_closed_transition_valid():
    """Test valid transition from Completed to Closed."""
    result = StateMachine.validate_transition("TASK", TaskStatus.COMPLETED.value, TaskStatus.CLOSED.value)
    assert result is True


def test_task_closed_is_terminal():
    """Test that Closed state is terminal (no outgoing transitions)."""
    with pytest.raises(DataFreezeError):
        StateMachine.validate_transition("TASK", TaskStatus.CLOSED.value, TaskStatus.COMPLETED.value)


def test_task_invalid_transition_rejected():
    """Test that invalid transitions are rejected."""
    with pytest.raises(IllegalTransitionError):
        StateMachine.validate_transition("TASK", TaskStatus.COMPLETED.value, TaskStatus.OPEN.value)


def test_check_modification_allowed_in_closed_state():
    """Test that modification is not allowed in Closed (terminal) state."""
    with pytest.raises(DataFreezeError):
        StateMachine.check_modification_allowed("TASK", TaskStatus.CLOSED.value)


def test_check_modification_allowed_in_open_state():
    """Test that modification is allowed in Open state."""
    result = StateMachine.check_modification_allowed("TASK", TaskStatus.OPEN.value)
    assert result is True or result is None
