"""
PPM Scheduler — Pydantic models package.
Import from this module for all scheduler collection schemas.
"""
from .shared_types import (
    PyObjectId,
    TaskStatus,
    TaskMode,
    DependencyType,
    DependencyStrength,
    ConstraintType,
    SummaryType,
    ProjectStatus,
    SystemState,
    ResourceType,
    CostRateType,
    ChangeSource,
    AuditAction,
    SchedulerRole,
    CostVarianceFlag,
    TASK_STATE_TRANSITIONS,
    CONSTRAINTS_REQUIRING_DATE,
    MAX_TASKS_PER_PROJECT,
    MAX_DEPENDENCIES_PER_TASK,
    WARN_DEPENDENCIES_PER_TASK,
    MAX_CONCURRENT_USERS,
    MAX_BASELINES_PER_PROJECT,
    MAX_PROJECTS_IN_PORTFOLIO,
    CPM_TIMEOUT_SECONDS,
    API_REQUEST_TIMEOUT_SECONDS,
)
from .project_calendars import (
    ProjectCalendar,
    ProjectCalendarCreate,
    ProjectCalendarUpdate,
    ResourceCalendarOverride,
)
from .enterprise_resources import (
    EnterpriseResource,
    EnterpriseResourceCreate,
    EnterpriseResourceUpdate,
    EnterpriseResourceResponse,
)
from .project_schedules import (
    Predecessor,
    ProjectScheduleTask,
    ProjectScheduleTaskCreate,
    ScheduleChangeRequest,
    TaskChanges,
)
from .schedule_baselines import (
    ScheduleBaseline,
    BaselineTaskSnapshot,
    BaselineFinancialSnapshot,
    BaselineComparisonResult,
    BaselineLockRequest,
)
from .project_metadata import (
    ProjectMetadata,
    AuditLogEntry,
)

__all__ = [
    # Shared types
    "PyObjectId",
    "TaskStatus",
    "TaskMode",
    "DependencyType",
    "DependencyStrength",
    "ConstraintType",
    "SummaryType",
    "ProjectStatus",
    "SystemState",
    "ResourceType",
    "CostRateType",
    "ChangeSource",
    "AuditAction",
    "SchedulerRole",
    "CostVarianceFlag",
    "TASK_STATE_TRANSITIONS",
    "CONSTRAINTS_REQUIRING_DATE",
    "MAX_TASKS_PER_PROJECT",
    "MAX_DEPENDENCIES_PER_TASK",
    "WARN_DEPENDENCIES_PER_TASK",
    "MAX_CONCURRENT_USERS",
    "MAX_BASELINES_PER_PROJECT",
    "MAX_PROJECTS_IN_PORTFOLIO",
    "CPM_TIMEOUT_SECONDS",
    "API_REQUEST_TIMEOUT_SECONDS",
    # Calendars
    "ProjectCalendar",
    "ProjectCalendarCreate",
    "ProjectCalendarUpdate",
    "ResourceCalendarOverride",
    # Resources
    "EnterpriseResource",
    "EnterpriseResourceCreate",
    "EnterpriseResourceUpdate",
    "EnterpriseResourceResponse",
    # Schedules
    "Predecessor",
    "ProjectScheduleTask",
    "ProjectScheduleTaskCreate",
    "ScheduleChangeRequest",
    "TaskChanges",
    # Baselines
    "ScheduleBaseline",
    "BaselineTaskSnapshot",
    "BaselineFinancialSnapshot",
    "BaselineComparisonResult",
    "BaselineLockRequest",
    # Metadata & Audit
    "ProjectMetadata",
    "AuditLogEntry",
]
