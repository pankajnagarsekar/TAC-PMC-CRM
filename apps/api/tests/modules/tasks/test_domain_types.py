from app.modules.tasks.domain.types import TaskStatus, TaskPriority, AssignmentType


def test_task_status_enum_values():
    """TaskStatus enum should have all valid states"""
    assert TaskStatus.OPEN.value == "Open"
    assert TaskStatus.IN_PROGRESS.value == "In Progress"
    assert TaskStatus.COMPLETED.value == "Completed"
    assert TaskStatus.CLOSED.value == "Closed"


def test_task_priority_enum_values():
    """TaskPriority enum should have all priority levels"""
    assert TaskPriority.LOW.value == "Low"
    assert TaskPriority.NORMAL.value == "Normal"
    assert TaskPriority.HIGH.value == "High"
    assert TaskPriority.CRITICAL.value == "Critical"


def test_assignment_type_enum_values():
    """AssignmentType enum should support user and external"""
    assert AssignmentType.USER.value == "user"
    assert AssignmentType.EXTERNAL.value == "external"


def test_task_status_from_string():
    """Should convert string to TaskStatus"""
    status = TaskStatus("Open")
    assert status == TaskStatus.OPEN
