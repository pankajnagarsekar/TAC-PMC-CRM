from app.modules.tasks.domain.exceptions import (
    TaskNotFoundError,
    TaskStatusTransitionError,
    TaskModificationForbiddenError,
    TaskSummaryGenerationError,
)


def test_task_not_found_error_message():
    """TaskNotFoundError should have clear message"""
    error = TaskNotFoundError(task_id="123")
    assert "123" in str(error)
    assert "not found" in str(error).lower()


def test_status_transition_error_message():
    """TaskStatusTransitionError should show invalid transition"""
    error = TaskStatusTransitionError(current="Open", target="Invalid")
    assert "Open" in str(error)
    assert "Invalid" in str(error)


def test_modification_forbidden_error_message():
    """TaskModificationForbiddenError should indicate frozen state"""
    error = TaskModificationForbiddenError(status="Closed")
    assert "Closed" in str(error)
    assert "modify" in str(error).lower()


def test_summary_generation_error_message():
    """TaskSummaryGenerationError should wrap underlying error"""
    original_error = ValueError("API key invalid")
    error = TaskSummaryGenerationError(str(original_error))
    assert "API key invalid" in str(error)
