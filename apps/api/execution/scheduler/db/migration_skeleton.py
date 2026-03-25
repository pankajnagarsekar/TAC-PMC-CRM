"""
Migration Skeleton — Legacy Payment Schedule → project_schedules.
STRUCTURE ONLY. Actual mapping logic implemented in Phase 5, Session 5.3.

This file defines:
    1. The data shape expected from the legacy system
    2. The transformation interface (signatures, not implementation)
    3. Validation report structure
    4. Rollback interface

Phase 5 (Session 5.3) will fill in the actual migration logic.
The skeleton is here so Phase 2-4 work can reference the migration
interface without needing the implementation.

Schema Reference: §1.3 (external_ref_id immutability)
Phase Feeding Map: Session 1.3 (migration script skeleton — structure only)
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from decimal import Decimal
from datetime import datetime


# =============================================================================
# Legacy source document shape
# =============================================================================

@dataclass
class LegacyScheduleTask:
    """
    Shape of a task document in the legacy payment_schedule collection
    (or equivalent legacy scheduler format).

    Fields discovered from legacy system — add more as mapping is confirmed
    in Phase 5 with the actual legacy data dump.
    """
    # Legacy identifiers
    legacy_id: str                  # Original _id from legacy system
    project_id: str
    legacy_wbs_code: Optional[str]  # May not exist in all legacy records
    task_name: str

    # Schedule fields (may be in different formats)
    start_date: Optional[str]       # Various legacy date formats
    finish_date: Optional[str]
    duration_days: Optional[int]

    # Financial fields (source of truth stays in WO/PC — these are reference only)
    estimated_cost: Optional[Decimal]

    # Status — may need mapping to new TaskStatus enum
    legacy_status: Optional[str]

    # Parent reference
    legacy_parent_id: Optional[str]

    # Sort / WBS ordering
    legacy_sort_order: Optional[int]


# =============================================================================
# Migration result shape
# =============================================================================

@dataclass
class MigrationTaskResult:
    """Per-task result from the migration process."""
    legacy_id: str
    new_task_id: Optional[str]          # Set when migration succeeds
    external_ref_id: Optional[str]      # The new immutable stable reference
    status: str                          # "success" | "skipped" | "failed"
    error_message: Optional[str] = None
    warnings: List[str] = field(default_factory=list)


@dataclass
class MigrationReport:
    """
    Summary report of the migration run.
    Validated against legacy totals before cutover (Phase 5).
    """
    project_id: str
    migration_run_at: datetime
    total_legacy_tasks: int
    total_migrated: int
    total_skipped: int
    total_failed: int

    # Financial reconciliation
    legacy_total_estimated_cost: Decimal
    migrated_total_baseline_cost: Decimal
    cost_variance: Decimal              # Should be 0 if mapping is correct

    # Detailed results
    task_results: List[MigrationTaskResult] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    @property
    def success_rate_percent(self) -> float:
        if self.total_legacy_tasks == 0:
            return 100.0
        return (self.total_migrated / self.total_legacy_tasks) * 100


# =============================================================================
# Migration interface (stubs — Phase 5 implementation)
# =============================================================================

async def migrate_project_schedule(
    db,
    project_id: str,
    dry_run: bool = True,
) -> MigrationReport:
    """
    Migrates one project's legacy schedule data to project_schedules format.

    STUB — Full implementation in Phase 5 Session 5.3.

    Algorithm (to be implemented):
        1. Load all legacy tasks for project_id from legacy collection
        2. For each legacy task:
            a. Generate external_ref_id (stable UUID, never changes)
            b. Map legacy_status → TaskStatus enum
            c. Map date formats to ISO8601
            d. Assign sort_index using gap-based float ordering
            e. Set task_mode = Auto (legacy tasks have no CPM mode)
        3. Bulk insert into project_schedules (NOT upsert — fresh migration)
        4. Run DAG validation on migrated tasks
        5. Create project_metadata document
        6. Return MigrationReport

    Args:
        db: Motor database instance
        project_id: Project to migrate
        dry_run: If True, validate and report without writing to DB.
                 Always start with dry_run=True to catch errors early.

    Returns:
        MigrationReport with full per-task status

    Raises:
        MigrationError: If migration cannot proceed safely (e.g. target
                        collection already has documents for this project)
    """
    raise NotImplementedError(
        "Migration implementation deferred to Phase 5 Session 5.3. "
        f"Called for project_id={project_id}, dry_run={dry_run}"
    )


async def generate_validation_report(
    db,
    project_id: str,
) -> Dict[str, Any]:
    """
    Compares legacy totals vs migrated totals for a project.

    STUB — Full implementation in Phase 5 Session 5.3.

    Checks:
        - Task count matches
        - Total baseline_cost matches legacy estimated_cost
        - All WBS codes are present
        - No orphaned tasks (parent references resolved)
        - Financial linkage: every migrated task with a WO/PC has a valid
          external_ref_id that resolves in the legacy financial collections

    Returns:
        Validation report dict with pass/fail for each check
    """
    raise NotImplementedError(
        "Validation report deferred to Phase 5 Session 5.3. "
        f"Called for project_id={project_id}"
    )


async def rollback_migration(
    db,
    project_id: str,
    migration_run_at: datetime,
) -> Dict[str, Any]:
    """
    Reverts migrated data for a project within 48-hour rollback window.

    STUB — Full implementation in Phase 5 Session 5.3.

    Safety constraints:
        - Only allowed within 48 hours of migration_run_at
        - Requires project to be in DRAFT or PLANNING state (no live data)
        - Leaves audit_log entries intact (soft-delete migrated tasks only)

    Args:
        db: Motor database instance
        project_id: Project to roll back
        migration_run_at: Timestamp of the migration run to roll back

    Returns:
        Dict with rollback status and count of documents removed
    """
    raise NotImplementedError(
        "Rollback deferred to Phase 5 Session 5.3. "
        f"Called for project_id={project_id}, run_at={migration_run_at}"
    )


# =============================================================================
# Legacy status mapping table (partial — complete in Phase 5)
# =============================================================================

# Maps legacy status strings → new TaskStatus enum values
# Completed in Phase 5 when actual legacy data is examined
LEGACY_STATUS_MAP: Dict[str, str] = {
    # Placeholder — fill in from actual legacy data analysis
    "Not Started":   "not_started",
    "In Progress":   "in_progress",
    "Completed":     "completed",
    "Closed":        "closed",
    # Unknown/unmapped legacy statuses default to "draft"
}

DEFAULT_LEGACY_STATUS = "draft"


def map_legacy_status(legacy_status: Optional[str]) -> str:
    """Maps a legacy status string to the new TaskStatus value."""
    if not legacy_status:
        return DEFAULT_LEGACY_STATUS
    return LEGACY_STATUS_MAP.get(legacy_status, DEFAULT_LEGACY_STATUS)
