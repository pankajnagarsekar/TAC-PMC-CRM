# Tasks Management Module - Implementation Plan

## Context

The TAC-PMC-CRM project tracks construction tasks in an Excel sheet (`01-Task List`) with columns: Sr No, Task Description, Action By, Deadline, Status/Notes, split into OPEN and COMPLETED sections. This module digitizes that workflow into the CRM with full lifecycle management, Kanban visualization, change logs, AI summaries, and mobile read-only access.

---

## Scope

| Area | Capability |
|------|-----------|
| **Web CRM** | Full CRUD: create, edit, assign, transition status, Kanban drag-drop, past tasks view, change log, AI summary |
| **Mobile CRM** | Read-only: list tasks, filter by status, view detail + change log |
| **API** | New `tasks` bounded context following DDD patterns |
| **AI** | OpenAI-powered task summary on dashboard |

---

## Phase 1: API Backend

### 1.1 State Machine Extension
**File:** `apps/api/app/modules/shared/domain/state_machine.py`
- Add `TASK_TRANSITIONS` dict:
  - `Open` -> `{In Progress, Closed}`
  - `In Progress` -> `{Review, Open, Closed}`
  - `Review` -> `{Completed, In Progress}`
  - `Completed` -> `{Closed}`
  - `Closed` -> `{}` (FINAL: Data Freeze)
- Update `validate_transition()` and `check_modification_allowed()` to handle `entity_type == "TASK"`

### 1.2 New Module: `apps/api/app/modules/tasks/`

```
tasks/
├── __init__.py
├── api/
│   ├── __init__.py
│   └── routes.py           # FastAPI router with all endpoints
├── application/
│   ├── __init__.py
│   └── task_service.py     # Business logic orchestration
├── domain/
│   ├── __init__.py
│   └── models.py           # Task aggregate root
├── infrastructure/
│   ├── __init__.py
│   └── repository.py       # TaskRepository(BaseRepository)
└── schemas/
    ├── __init__.py
    └── dto.py              # Pydantic models (Task, TaskCreate, TaskUpdate, etc.)
```

### 1.3 MongoDB Schema (`tasks` collection)

```
{
  _id, organisation_id, project_id, sr_no (auto-increment per project),
  task_description (text),
  assigned_to_user_id (nullable FK), assigned_to_name (always set), assigned_to_type ("user"|"external"),
  deadline (datetime|null), status (enum), priority ("Low"|"Normal"|"High"|"Urgent"),
  notes (text),
  scheduler_task_id (nullable, soft FK to scheduler),
  created_by, created_by_name, version, created_at, updated_at
}
```

Indexes: `(project_id, status)`, `(project_id, sr_no) UNIQUE`, `(organisation_id, project_id)`, `(assigned_to_user_id)`, `(deadline)`

### 1.4 API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/v1/tasks/` | Create task |
| GET | `/v1/tasks/` | List tasks (filters: status, assignee, priority, deadline range, search) |
| GET | `/v1/tasks/{task_id}` | Get single task |
| PUT | `/v1/tasks/{task_id}` | Update task fields |
| PATCH | `/v1/tasks/{task_id}/status` | Status transition (Kanban move) |
| DELETE | `/v1/tasks/{task_id}` | Close/delete task |
| GET | `/v1/tasks/kanban-counts` | Status distribution counts |
| GET | `/v1/tasks/completed` | Past tasks (Completed + Closed) |
| GET | `/v1/tasks/{task_id}/changelog` | Audit trail for specific task |
| GET | `/v1/tasks/ai-summary` | AI-generated task summary |

### 1.5 Registration
- **`apps/api/app/api/router.py`**: Add `from app.modules.tasks.api.routes import router as tasks_router` + `v1_router.include_router(tasks_router)`
- **`apps/api/app/core/dependencies.py`**: Add `get_task_service` factory

### 1.6 Change Logs
- Use existing `AuditService.log_action()` with `module_name="TASK_MANAGEMENT"`, `entity_type="TASK"`
- Every create/update/status-change/delete logged with old/new values
- `SnapshotService` creates full snapshots on terminal transitions (Completed, Closed)

---

## Phase 2: Shared Types

**File:** `packages/types/src/index.ts` - Add:
- `Task`, `TaskCreate`, `TaskUpdate`, `TaskStatusUpdate` interfaces
- `TaskStatus` = `"Open" | "In Progress" | "Review" | "Completed" | "Closed"`
- `TaskPriority` = `"Low" | "Normal" | "High" | "Urgent"`
- `TaskKanbanCounts`, `TaskAISummary` response types

---

## Phase 3: Web CRM

### 3.1 Sidebar Entry
**File:** `apps/web/src/components/layout/Sidebar.tsx`
- Add `Tasks` nav item with icon `CheckSquare` (lucide-react)
- Children tabs: Active (list), Kanban, Past Tasks

### 3.2 Pages

**`apps/web/src/app/admin/tasks/page.tsx`** - Main tasks page with tab switching:
- **Active tab**: AG Grid (FinancialGrid) with search, status/priority filters, "New Task" button
- **Kanban tab**: Drag-drop board with 5 status columns (Open, In Progress, Review, Completed, Closed)
- **Past Tasks tab**: Read-only AG Grid of Completed + Closed tasks

**`apps/web/src/app/admin/tasks/new/page.tsx`** - Create task form:
- Fields: Description (textarea), Assignee (combo: CRM user dropdown + free-text for external), Deadline, Priority, Notes
- Optional: "Link to Scheduler Task" searchable dropdown
- Redirect to detail page on success

**`apps/web/src/app/admin/tasks/[id]/page.tsx`** - Task detail/edit:
- GlassCard with task details, inline edit mode
- Status transition buttons (context-aware)
- Version conflict detection (optimistic locking)
- Change log timeline at bottom
- Scheduler task link (if present)

### 3.3 Components (under `apps/web/src/components/tasks/`)

| Component | Purpose |
|-----------|---------|
| `TaskKanbanBoard.tsx` | 5-column drag-drop Kanban (simpler than scheduler Kanban) |
| `TaskCard.tsx` | Kanban card: description, assignee, deadline, priority color |
| `TaskChangeLog.tsx` | Timeline of audit entries with field-level diffs |
| `AssigneeComboBox.tsx` | Dual-mode: CRM user dropdown + free-text for external parties |
| `TaskAISummary.tsx` | AI summary widget (for dashboard or tasks page header) |
| `PastTasksTable.tsx` | AG Grid for completed/closed tasks |

### 3.4 Store (Optional)
**`apps/web/src/store/useTaskStore.ts`** - Only if Kanban needs optimistic drag-drop updates. Otherwise, SWR direct fetching per the work-orders pattern.

### 3.5 Dashboard Integration
Add `TaskAISummary` card to `apps/web/src/app/admin/dashboard/page.tsx` alongside existing AISummaryCard.

---

## Phase 4: Mobile CRM (Read-Only)

### 4.1 Screens

```
apps/mobile/app/(admin)/tasks/
├── _layout.tsx     # Stack navigator
├── index.tsx       # Task list with filters (pattern: dpr/index.tsx)
└── [id].tsx        # Task detail with change log (read-only)
```

### 4.2 Navigation
**File:** `apps/mobile/app/(admin)/_layout.tsx` - Add Tasks tab or "More" menu entry

### 4.3 API Client
**File:** `apps/mobile/services/apiClient.ts` - Add `tasksApi` with `getAll`, `getById`, `getAuditLog`

### 4.4 Types
**File:** `apps/mobile/types/api.ts` - Add `Task`, `TaskStatus`, `TaskPriority` interfaces

---

## Phase 5: AI Summary

- Task service method `get_task_summary_for_ai(project_id)` aggregates: total tasks, open count, overdue count, status distribution, top assignees
- Passes to `EmergentSummaryProvider` (same pattern as `core/ai_summary_service.py`) with construction-specific prompt
- Cached in `task_ai_summaries` collection with TTL
- Endpoint: `GET /v1/tasks/ai-summary?project_id=xxx`

---

## Key Design Decisions

1. **Assignment**: Dual model - `assigned_to_user_id` (CRM users) + `assigned_to_name` (always set, supports "Omkar/Rajesh", "MEP", etc.) + `assigned_to_type` discriminator
2. **Scheduler Linkage**: Optional soft FK `scheduler_task_id` - display-only, no bidirectional sync
3. **Change Logs**: Existing AuditService (field-level diffs) + SnapshotService (full entity on terminal states)
4. **Kanban**: Simpler than scheduler Kanban - no CPM/dependency graph, just drag-drop status transitions
5. **No soft-delete flag**: Tasks removed by transitioning to `Closed`. Hard delete only for `Open` status tasks.

---

## Implementation Order

1. State machine extension (state_machine.py)
2. Task schemas (dto.py)
3. Task domain model (models.py)
4. Task repository (repository.py)
5. Task service (task_service.py)
6. Task routes (routes.py)
7. Router + dependency registration
8. Shared types (packages/types)
9. Web sidebar entry
10. Web task list page (Active tab)
11. Web create task page + AssigneeComboBox
12. Web task detail page + TaskChangeLog
13. Web Kanban board + TaskCard
14. Web past tasks tab
15. AI summary endpoint + TaskAISummary component
16. Dashboard AI card integration
17. Mobile types + API client
18. Mobile task list screen
19. Mobile task detail screen

---

## Verification

1. **API**: Run `cd apps/api && python -m pytest` after backend changes
2. **Web**: Run `cd apps/web && npx tsc --noEmit` for type checking, `npm run lint` for lint
3. **Mobile**: Run `cd apps/mobile && npm run lint`
4. **E2E**: Create a task via web -> verify in API docs (`/docs`) -> verify on mobile
5. **Kanban**: Drag task between columns -> verify status change persists on reload
6. **Change Log**: Edit task fields -> verify audit entries appear on detail page
7. **AI Summary**: Call `/v1/tasks/ai-summary` -> verify OpenAI response (or mock fallback)
8. **Monorepo**: Run `pnpm lint` from root for zero-error policy
