# Tasks Module Documentation

## Overview

The Tasks module implements task management with domain-driven design principles. It provides:

- **Atomic serial numbering** (sr_no) to ensure uniqueness within projects
- **State machine-based lifecycle** with immutable terminal states
- **Multi-tenant security** via organization scoping
- **AI-powered summaries** with intelligent caching
- **Audit trails** for compliance and debugging
- **Optimistic locking** via version fields

## Architecture

### Module Structure

```
modules/tasks/
├── api/
│   └── routes.py              # HTTP endpoints
├── application/
│   └── task_service.py        # Business logic orchestration
├── domain/
│   ├── models.py              # Aggregate roots & value objects
│   ├── types.py               # Enums (TaskStatus, TaskPriority)
│   ├── exceptions.py          # Domain-specific exceptions
│   ├── authorization.py       # Authorization checks
│   └── constants.py           # Configuration constants
├── infrastructure/
│   ├── repository.py          # Data access layer
│   ├── counter.py             # Atomic sr_no counter
│   ├── cache_manager.py       # Cache invalidation
│   └── indexes.py             # MongoDB index definitions
└── schemas/
    └── dto.py                 # Pydantic request/response models
```

### DDD Layers

1. **Domain Layer** (`domain/`)
   - Business rules and invariants
   - State machine validation
   - Domain exceptions

2. **Application Layer** (`application/`)
   - Use cases (create, update, delete tasks)
   - Service orchestration
   - Dependency injection

3. **Infrastructure Layer** (`infrastructure/`)
   - Repository pattern with BaseRepository
   - MongoDB atomic operations
   - Cache management

4. **API Layer** (`api/`)
   - FastAPI route handlers
   - HTTP input validation
   - Response formatting

## State Machine

### Task States and Transitions

```
Open
├─→ In Progress
│   └─→ Completed
│       └─→ Closed (TERMINAL)
│           └─ [No outgoing transitions]
└─→ Closed (TERMINAL)

```

**Terminal States (Immutable):**
- `Closed`: No further updates allowed

**Valid Transitions:**
- `Open` → `In Progress` | `Closed`
- `In Progress` → `Completed` | `Closed`
- `Completed` → `Closed`
- `Closed` → [No transitions]

Enforced by `StateMachine.validate_transition()` in `shared/domain/state_machine.py`.

## Database Schema

### Collections

#### tasks
Main task collection with organization scoping.

**Fields:**
- `_id`: MongoDB ObjectId
- `organisation_id`: Org tenant key (indexes)
- `project_id`: FK to projects
- `sr_no`: Unique sequence number per (org, project)
- `status`: Current state (Open, In Progress, Completed, Closed)
- `task_description`: Main task text
- `assigned_to_user_id`: FK to users (nullable)
- `assigned_to_name`: Display name (always populated)
- `assigned_to_type`: "user" | "external"
- `priority`: Low, Normal, High, Critical
- `deadline`: Optional deadline datetime
- `version`: Optimistic lock counter
- `created_by`: User ID who created
- `created_by_name`: Display name
- `created_at`, `updated_at`: Timestamps
- `audit_log`: Array of {action, timestamp, user, detail}

**Indexes:**
- `(organisation_id, project_id)` - Most common query
- `(organisation_id, project_id, status)` - Status filtering
- `(organisation_id, assigned_to_user_id)` - Assignment queries
- `(deadline)` - Overdue detection

#### task_sr_no_counters
Atomic counter for sequential sr_no generation.

**Fields:**
- `organisation_id`: Org tenant key
- `project_id`: Project ID
- `sequence`: Current counter value

**Indexes:**
- `(organisation_id, project_id)` - UNIQUE

#### task_ai_summaries
Cached AI summaries for projects.

**Fields:**
- `_id`: MongoDB ObjectId
- `organisation_id`: Org tenant key
- `project_id`: Project ID
- `summary_text`: AI-generated summary
- `metrics`: Aggregated task metrics
- `created_at`: Cache creation timestamp

**Indexes:**
- `(organisation_id, project_id, created_at DESC)` - Cache lookups

## Atomic Serial Numbers (sr_no)

### Implementation

Uses MongoDB's atomic `find_one_and_update` with `$inc` operator:

```python
# In AtomicCounter
result = await collection.find_one_and_update(
    {"organisation_id": org_id, "project_id": project_id},
    {"$inc": {"sequence": 1}},
    upsert=True,
    return_document=ReturnDocument.AFTER,
)
```

**Benefits:**
- Thread-safe without explicit locks
- Works across distributed systems
- Guaranteed unique values
- Scales horizontally

### Scoping

sr_no is unique per (organization, project) pair:
- org-1/proj-1: sr_no 1, 2, 3, ...
- org-1/proj-2: sr_no 1, 2, 3, ... (separate counter)
- org-2/proj-1: sr_no 1, 2, 3, ... (separate counter)

## Authorization

### Organization Scoping

All queries include `organisation_id` filter:

```python
task = await repo.get_by_id(task_id, organisation_id=user["organisation_id"])
```

Returns `404` if task belongs to different org (secure approach).

### Permission Checks

`TaskAuthorizationManager` validates:
- User organization matches task organization
- Project ID is provided and valid

## Caching

### Summary Cache

AI summaries are cached with 6-hour TTL to reduce API calls:

```python
# Constants
TASK_AI_SUMMARY_CACHE_TTL_SECONDS = 6 * 60 * 60
TASK_AI_SUMMARY_GENERATION_TIMEOUT_SECONDS = 30
```

### Cache Invalidation

Cache is automatically invalidated on:
- Task creation (`create_task`)
- Task status update (`update_status`)
- Task field updates (`update_task_details`)
- Task deletion (`delete_task`)

Handled by `TaskAISummaryCache.invalidate_for_project()`.

## API Endpoints

### Create Task
```
POST /api/v1/tasks/
Content-Type: application/json

{
  "project_id": "proj-123",
  "task_description": "Fix login bug",
  "assigned_to_name": "John Doe",
  "priority": "High",
  "deadline": "2026-04-15T00:00:00Z"
}

Response 201:
{
  "data": {
    "_id": "507f1f77bcf86cd799439011",
    "sr_no": 5,
    "status": "Open",
    "audit_log": [{"action": "CREATE", ...}],
    ...
  }
}
```

### Update Status
```
PATCH /api/v1/tasks/{task_id}/status
Content-Type: application/json

{"status": "In Progress"}

Response 200:
{
  "data": {
    "status": "In Progress",
    "version": 2,
    "audit_log": [{...}, {"action": "STATUS_CHANGE", ...}]
  }
}
```

### Update Task Details
```
PATCH /api/v1/tasks/{task_id}
Content-Type: application/json

{"task_description": "Updated description"}

Response 200:
{
  "data": {
    "task_description": "Updated description",
    "version": 2,
    "audit_log": [{...}, {"action": "UPDATE", ...}]
  }
}
```

### Get Task Summary
```
GET /api/v1/tasks/summary?project_id=proj-123

Response 200:
{
  "data": {
    "summary_text": "Project has 10 tasks: 3 open, 4 in progress, 3 completed",
    "metrics": {
      "total": 10,
      "open": 3,
      "overdue": 1,
      "completed": 3,
      "status_distribution": {...},
      "top_assignees": {...}
    }
  }
}
```

## Error Handling

### Domain Exceptions

- `TaskNotFoundError`: Task doesn't exist
- `TaskStatusTransitionError`: Invalid state transition
- `TaskModificationForbiddenError`: Cannot modify frozen task
- `TaskSummaryGenerationError`: AI generation failed
- `TaskAuthorizationError`: User not authorized

### HTTP Exceptions

- `400 Bad Request`: Invalid transitions, missing data
- `403 Forbidden`: Authorization failed (when not using org scoping)
- `404 Not Found`: Task not found OR org scoping denied access
- `500 Internal Server Error`: Database or external service errors

## Audit Trail

### Audit Log Structure

Every task has an `audit_log` array with entries:

```python
{
  "action": "CREATE" | "UPDATE" | "STATUS_CHANGE" | "DELETE",
  "timestamp": datetime,
  "user": "John Doe",
  "detail": "Status changed from Open to In Progress"
}
```

### Access Pattern

```python
task = await service.get_task(user, task_id)
for entry in task["audit_log"]:
    print(f"{entry['timestamp']} - {entry['user']}: {entry['detail']}")
```

## Constants

Defined in `domain/constants.py`:

```python
# Cache
TASK_AI_SUMMARY_CACHE_TTL_SECONDS = 6 * 60 * 60  # 6 hours
TASK_AI_SUMMARY_GENERATION_TIMEOUT_SECONDS = 30

# Pagination
DEFAULT_PAGE_LIMIT = 50
MAX_PAGE_LIMIT = 500

# Summary
MAX_TOP_ASSIGNEES_IN_SUMMARY = 3
```

## Testing

### Test Coverage

- `test_state_machine_task.py`: StateMachine transitions
- `test_sr_no_atomicity.py`: Atomic counter concurrency
- `test_task_authorization.py`: Authorization checks
- `test_error_handling.py`: Error handling and timeouts
- `test_cache_invalidation.py`: Cache lifecycle
- `test_database_indexes.py`: Index creation and usage
- `test_integration_complete.py`: End-to-end workflows

### Running Tests

```bash
cd apps/api

# All task tests
pytest tests/modules/tasks/ -v

# Specific test
pytest tests/modules/tasks/test_state_machine_task.py -v

# With coverage
pytest tests/modules/tasks/ --cov=app.modules.tasks
```

## Known Limitations

1. **Soft Deletes Not Used**: Tasks transition to Closed instead of soft-delete
2. **No Bulk Operations**: Single-task operations only (N+1 for bulk updates)
3. **Cache TTL**: Fixed 6-hour cache for all projects
4. **AI Timeout**: All AI providers must respond within 30 seconds

## Future Enhancements

1. **Task Dependencies**: Add task-to-task relationships
2. **Batch Operations**: Bulk create/update for performance
3. **Advanced Filtering**: Full-text search, date range queries
4. **Webhooks**: Notify external systems on state changes
5. **Subtasks**: Hierarchical task structures
6. **Time Tracking**: Log work hours and estimates

## Related Modules

- **project**: Project context for task grouping
- **identity**: User/auth context for ownership
- **reporting**: Uses task summaries for dashboards
- **shared**: StateMachine, BaseRepository, AuditService

## References

- Project Architecture: `CLAUDE.md` - DDD Architecture section
- State Machine: `shared/domain/state_machine.py`
- Base Repository: `shared/infrastructure/base_repository.py`
