"""Task module domain-specific exceptions."""


class TaskDomainError(Exception):
    """Base exception for task domain errors."""
    pass


class TaskNotFoundError(TaskDomainError):
    """Raised when a task cannot be found."""

    def __init__(self, task_id: str):
        self.task_id = task_id
        super().__init__(f"Task with ID '{task_id}' not found")


class TaskStatusTransitionError(TaskDomainError):
    """Raised when an invalid status transition is attempted."""

    def __init__(self, current: str, target: str):
        self.current = current
        self.target = target
        super().__init__(
            f"Cannot transition from '{current}' to '{target}'. "
            f"This transition is not allowed by the state machine."
        )


class TaskModificationForbiddenError(TaskDomainError):
    """Raised when attempting to modify a task in a frozen state."""

    def __init__(self, status: str, detail: str = None):
        self.status = status
        msg = f"Cannot modify task in '{status}' state. This state is immutable."
        if detail:
            msg += f" {detail}"
        super().__init__(msg)


class TaskSummaryGenerationError(TaskDomainError):
    """Raised when AI summary generation fails."""

    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(f"Failed to generate task summary: {detail}")


class TaskAuthorizationError(TaskDomainError):
    """Raised when user is not authorized to perform an action on a task."""

    def __init__(self, user_id: str, task_id: str, action: str):
        self.user_id = user_id
        self.task_id = task_id
        self.action = action
        super().__init__(
            f"User '{user_id}' is not authorized to {action} task '{task_id}'"
        )
