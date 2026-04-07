# Tasks Management Module Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Digitize the construction task workflow into the CRM with full lifecycle management, Kanban visualization, change logs, AI summaries, and mobile read-only access.

**Architecture:** A new `tasks` bounded context using DDD patterns in the backend API (Python/FastAPI). The web frontend (React.js/Next.js) will use a Kanban board and Data Grids for open and past tasks. The mobile app will offer read-only access. State machine extensions will govern task lifecycle transitions.

**Tech Stack:** React 18+, Tailwind CSS (Luxury Industrial), Node.js, Python 3 (FastAPI), MongoDB.

**Skills Used:** `@software-architecture`, `@python-pro`, `@react-best-practices`, `@database-design`, `@api-design-principles`, `@writing-plans`, `@concise-planning`.

---

## Scope

- **In:** Web task CRUD, Kanban board, past tasks grid, change logs timeline, AI summaries, mobile read-only views, API backend in Python following DDD.
- **Out:** Complex dependencies/CPM (Kanban drag-and-drop only), bidirectional sync with scheduler.

## Action Items

### Task 1: Backend Domain & State Machine (API)

**Files:**
- Modify: `apps/api/app/modules/shared/domain/state_machine.py`
- Create: `apps/api/app/modules/tasks/domain/models.py`
- Create: `apps/api/app/modules/tasks/schemas/dto.py`

**Step 1: Write the failing tests**
- Create `apps/api/tests/modules/tasks/test_domain.py` with failing tests for state transitions and domain models.
- Run tests to verify they fail.

**Step 2: Implement State Machine Extension**
- Add `TASK_TRANSITIONS` to `state_machine.py` (Open -> {In Progress, Closed}, In Progress -> {Review, Open, Closed}, Review -> {Completed, In Progress}, Completed -> {Closed}).
- Update `validate_transition()` and `check_modification_allowed()` for `"TASK"`.

**Step 3: Implement domain models and schemas**
- Write `models.py` for task aggregate root.
- Write `dto.py` for Pydantic models (`Task`, `TaskCreate`, `TaskUpdate`, `TaskStatusUpdate`).

**Step 4: Run tests to verify they pass**
- Run: `pytest apps/api/tests/modules/tasks/test_domain.py -v`

**Step 5: Commit**
```bash
git add apps/api/app/modules/shared/domain/state_machine.py apps/api/app/modules/tasks/
git commit -m "feat(api): add task domain models and state machine transitions"
```

### Task 2: Backend Controllers & Services (API)

**Files:**
- Create: `apps/api/app/modules/tasks/infrastructure/repository.py`
- Create: `apps/api/app/modules/tasks/application/task_service.py`
- Create: `apps/api/app/modules/tasks/api/routes.py`
- Modify: `apps/api/app/api/router.py`, `apps/api/app/core/dependencies.py`

**Step 1: Write failing tests**
- Add tests for service logic and API routes.

**Step 2: Implement repository and service**
- Implement `TaskRepository` for MongoDB operations.
- Implement `task_service.py` with CRUD, `SnapshotService` integration for terminal states, and `AuditService` log_action.

**Step 3: Implement API endpoints & register**
- Write `routes.py` for `/v1/tasks/*` and `/v1/tasks/ai-summary` (mocked).
- Register router in `router.py` and factory in `dependencies.py`.

**Step 4: Run tests**
- Run: `pytest apps/api/tests/modules/tasks/test_api.py -v`

**Step 5: Commit**
```bash
git add apps/api/app/modules/tasks/ apps/api/app/api/router.py apps/api/app/core/dependencies.py
git commit -m "feat(api): implement task repository, service, and routes"
```

### Task 3: Shared Types & Web Skeleton

**Files:**
- Modify: `packages/types/src/index.ts`
- Modify: `apps/web/src/components/layout/Sidebar.tsx`
- Create: `apps/web/src/app/admin/tasks/page.tsx`
- Create: `apps/web/src/app/admin/tasks/new/page.tsx`
- Create: `apps/web/src/app/admin/tasks/[id]/page.tsx`

**Step 1: Add types**
- Extend `TaskStatus`, `TaskPriority`, `Task`, `TaskCreate`, `TaskUpdate`, `TaskStatusUpdate`.

**Step 2: Sidebar**
- Add `Tasks` nav item under `Sidebar.tsx`.

**Step 3: Scaffold Web Pages**
- Create basic structural placeholders for Tasks list, new task, and task details pages adhering to the Luxury Industrial UI design.

**Step 4: Verify**
- `cd packages/types && npx tsc --noEmit`
- `cd apps/web && npx tsc --noEmit`

**Step 5: Commit**
```bash
git add packages/types/src/index.ts apps/web/src/
git commit -m "feat(web): adding shared task types and web page skeletons"
```

### Task 4: Web CRM UI Components (Active, Kanban, Past)

**Files:**
- Create: `apps/web/src/components/tasks/TaskKanbanBoard.tsx`
- Create: `apps/web/src/components/tasks/TaskCard.tsx`
- Create: `apps/web/src/components/tasks/TaskChangeLog.tsx`
- Create: `apps/web/src/components/tasks/AssigneeComboBox.tsx`
- Create: `apps/web/src/components/tasks/PastTasksTable.tsx`
- Modify: `apps/web/src/app/admin/tasks/page.tsx`
- Modify: `apps/web/src/app/admin/tasks/[id]/page.tsx`

**Step 1: Implement UI Components**
- Construct the drag-and-drop `TaskKanbanBoard` with `TaskCard`.
- Construct `PastTasksTable` using `FinancialGrid` (AG Grid).
- Implement `TaskChangeLog` for detail page.
- Apply Luxury Industrial dark/metallic styles.

**Step 2: Integrate into Pages**
- Wire forms, mutations and queries using `SWR` in `new/page.tsx` and `[id]/page.tsx`.

**Step 3: Verification**
- Lint/tsc checks.

**Step 4: Commit**
```bash
git add apps/web/src/components/tasks/ apps/web/src/app/admin/tasks/
git commit -m "feat(web): implement task kanban, datagrid, and forms"
```

### Task 5: Mobile CRM (Read-Only)

**Files:**
- Create: `apps/mobile/app/(admin)/tasks/_layout.tsx`
- Create: `apps/mobile/app/(admin)/tasks/index.tsx`
- Create: `apps/mobile/app/(admin)/tasks/[id].tsx`
- Modify: `apps/mobile/app/(admin)/_layout.tsx`
- Modify: `apps/mobile/services/apiClient.ts`
- Modify: `apps/mobile/types/api.ts`

**Step 1: Mobile Types and API Client**
- Update types and `apiClient.ts` with `tasksApi`.

**Step 2: Screens**
- Write list and detail screens (Read-Only). Register navigation.

**Step 3: Verify**
- `cd apps/mobile && npm run lint`

**Step 4: Commit**
```bash
git add apps/mobile/
git commit -m "feat(mobile): add read-only tasks to mobile CRM"
```

### Task 6: AI Summary & Dashboard Integration

**Files:**
- Modify: `apps/api/app/modules/tasks/application/task_service.py`
- Modify: `apps/web/src/app/admin/dashboard/page.tsx`
- Create: `apps/web/src/components/tasks/TaskAISummary.tsx`

**Step 1: Backend AI integration**
- Implement `get_task_summary_for_ai()` caching into `task_ai_summaries` utilizing ChatGPT summaries.

**Step 2: Web Integration**
- Create `TaskAISummary.tsx` display component. Include in dashboard and task pages.

**Step 3: Commit**
```bash
git add apps/api/ apps/web/
git commit -m "feat: integrate task AI summary in backend and dashboard"
```
