"""Task module domain types and enums."""

from enum import Enum


class TaskStatus(str, Enum):
    """Valid task status values."""
    OPEN = "Open"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"
    CLOSED = "Closed"

    @property
    def is_terminal(self) -> bool:
        """Returns True if this is a terminal (immutable) state."""
        return self in {TaskStatus.CLOSED}


class TaskPriority(str, Enum):
    """Valid task priority levels."""
    LOW = "Low"
    NORMAL = "Normal"
    HIGH = "High"
    CRITICAL = "Critical"


class AssignmentType(str, Enum):
    """Type of task assignment."""
    USER = "user"
    EXTERNAL = "external"


# State Machine Definition for TASK entity
TASK_STATE_TRANSITIONS = {
    TaskStatus.OPEN: {TaskStatus.IN_PROGRESS, TaskStatus.CLOSED},
    TaskStatus.IN_PROGRESS: {TaskStatus.COMPLETED, TaskStatus.OPEN, TaskStatus.CLOSED},
    TaskStatus.COMPLETED: {TaskStatus.CLOSED},
    TaskStatus.CLOSED: set(),  # Terminal state - no outgoing transitions
}
