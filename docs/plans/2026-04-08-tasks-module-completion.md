# Tasks Module Completion Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix 6 bugs and missing features to bring the Tasks module from 90% to 100% complete.

**Architecture:** Each fix targets a specific layer (API routes, service logic, mobile navigation, web sidebar) without cross-cutting changes. All fixes follow the DDD patterns already established in the codebase.

**Tech Stack:** Python FastAPI (API), React 19 / Next.js (Web), React Native / Expo (Mobile)

---

## Summary of Gaps Found

| # | Severity | Location | Issue |
|---|----------|----------|-------|
| 1 | 🔴 CRITICAL | `apps/api/app/modules/tasks/api/routes.py` | Route order bug: `GET /ai-summary` declared AFTER `GET /{task_id}` — FastAPI matches "ai-summary" as a task_id, returning 404 |
| 2 | 🔴 CRITICAL | `apps/mobile/app/(admin)/_layout.tsx` | Tasks screens never registered in admin Tabs navigator — unreachable from mobile |
| 3 | 🟠 HIGH | `apps/api/app/modules/tasks/api/routes.py` | DELETE endpoint missing entirely |
| 4 | 🟠 HIGH | `apps/api/app/modules/tasks/application/task_service.py` | `STATUS_FLOW` local dict disagrees with `StateMachine.TASK_TRANSITIONS` — bypasses the authoritative state machine |
| 5 | 🟡 MEDIUM | `apps/api/app/modules/tasks/schemas/dto.py` | `TaskCreate` requires `organisation_id` in the request body — should come from JWT, not client |
| 6 | 🟡 MEDIUM | `apps/web/src/components/layout/Sidebar.tsx` | Tasks sidebar entry has no `children` tabs (Active / Board) |

---

## Task 1: Fix AI-Summary Route Order (CRITICAL)

**Why critical:** `GET /tasks/ai-summary?project_id=xxx` currently routes to the `get_task` handler with `task_id="ai-summary"`, returns 404. The dashboard AI summary card is broken.

**Files:**
- Modify: `apps/api/app/modules/tasks/api/routes.py`

**Step 1: Move the `/ai-summary` route above `/{task_id}`**

Current order (broken):
```
GET /          (list)
GET /{task_id} (detail)   ← catches "ai-summary" first
PATCH /{task_id}/status
PATCH /{task_id}
GET /ai-summary            ← never reached
```

Target order (fixed):
```
POST /
GET /
GET /ai-summary            ← specific routes first
GET /{task_id}             ← wildcard last
PATCH /{task_id}/status
PATCH /{task_id}
DELETE /{task_id}          ← new
```

**Step 2: Rewrite `routes.py` with correct order**

```python
from typing import List
from fastapi import APIRouter, Depends, status, HTTPException
from app.core.dependencies import (
    get_authenticated_user, get_db, get_audit_service,
    get_permission_checker, get_snapshot_service
)
from app.modules.tasks.application.task_service import TaskService
from app.modules.tasks.schemas.dto import Task, TaskCreate, TaskUpdate, TaskStatusUpdate
from app.modules.shared.domain.schemas import GenericResponse

router = APIRouter(prefix="/tasks", tags=["Tasks"])


def get_task_service(
    db=Depends(get_db),
    audit=Depends(get_audit_service),
    perm=Depends(get_permission_checker),
    snap=Depends(get_snapshot_service),
):
    return TaskService(db, audit, perm, snap)


@router.post("/", response_model=GenericResponse[Task], status_code=status.HTTP_201_CREATED)
async def create_task(
    data: TaskCreate,
    user: dict = Depends(get_authenticated_user),
    service: TaskService = Depends(get_task_service),
):
    result = await service.create_task(user, data)
    return GenericResponse(data=result, message="Task created successfully")


@router.get("/", response_model=GenericResponse[List[Task]])
async def list_tasks(
    project_id: str,
    user: dict = Depends(get_authenticated_user),
    service: TaskService = Depends(get_task_service),
):
    result = await service.get_tasks(user, project_id)
    return GenericResponse(data=result)


# ── SPECIFIC PATHS BEFORE WILDCARD ──────────────────────────────────────────

@router.get("/ai-summary", response_model=GenericResponse)
async def get_task_ai_summary(
    project_id: str,
    user: dict = Depends(get_authenticated_user),
    service: TaskService = Depends(get_task_service),
):
    result = await service.get_task_summary_for_ai(user, project_id)
    return GenericResponse(data=result)


# ── WILDCARD PATHS LAST ──────────────────────────────────────────────────────

@router.get("/{task_id}", response_model=GenericResponse[Task])
async def get_task(
    task_id: str,
    user: dict = Depends(get_authenticated_user),
    service: TaskService = Depends(get_task_service),
):
    result = await service.get_task(user, task_id)
    return GenericResponse(data=result)


@router.patch("/{task_id}/status", response_model=GenericResponse[Task])
async def update_status(
    task_id: str,
    data: TaskStatusUpdate,
    user: dict = Depends(get_authenticated_user),
    service: TaskService = Depends(get_task_service),
):
    result = await service.update_status(user, task_id, data.status)
    return GenericResponse(data=result, message="Status updated successfully")


@router.patch("/{task_id}", response_model=GenericResponse[Task])
async def update_task(
    task_id: str,
    data: TaskUpdate,
    user: dict = Depends(get_authenticated_user),
    service: TaskService = Depends(get_task_service),
):
    result = await service.update_task_details(user, task_id, data)
    return GenericResponse(data=result, message="Task updated successfully")


@router.delete("/{task_id}", response_model=GenericResponse)
async def delete_task(
    task_id: str,
    user: dict = Depends(get_authenticated_user),
    service: TaskService = Depends(get_task_service),
):
    await service.delete_task(user, task_id)
    return GenericResponse(data=None, message="Task deleted successfully")
```

**Step 3: Verify API starts without errors**
```bash
cd apps/api && python -m uvicorn app.main:app --reload
```
Expected: Server starts. `GET /docs` shows `/tasks/ai-summary` listed before `GET /tasks/{task_id}`.

---

## Task 2: Add DELETE method to TaskService

**Why:** Route added in Task 1 calls `service.delete_task()` which doesn't exist yet.

**Files:**
- Modify: `apps/api/app/modules/tasks/application/task_service.py`

**Step 1: Add `delete_task` method**

Add after `get_tasks` method:

```python
async def delete_task(self, user: dict, task_id: str) -> None:
    """
    Hard-delete Open tasks. Transition non-Open tasks to Closed instead.
    Preserves audit trail by logging before deletion.
    """
    task = await self.repo.get_by_id(task_id, organisation_id=user["organisation_id"])
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Tasks with work history are Closed (soft), pristine Open tasks are hard-deleted
    if task.get("status") == "Open" and len(task.get("audit_log", [])) <= 1:
        await self.repo.delete(task_id)
    else:
        # Transition to Closed (data freeze) via existing update_status
        if task.get("status") != "Closed":
            await self.update_status(user, task_id, "Closed")
```

**Step 2: Verify the BaseRepository has a `delete` method**

Check `shared/infrastructure/base_repository.py` for `async def delete(...)`. If it uses `delete_one` or similar, adjust the call name accordingly.

---

## Task 3: Fix STATUS_FLOW to use StateMachine

**Why:** `task_service.py` has its own `STATUS_FLOW` dict that doesn't match `StateMachine.TASK_TRANSITIONS`. Status transitions bypass the authoritative state machine. Example: service allows `In Progress → Completed` but state machine requires `In Progress → Review → Completed`.

**Files:**
- Modify: `apps/api/app/modules/tasks/application/task_service.py`

**Step 1: Remove the local STATUS_FLOW dict and import StateMachine**

Remove lines 18-23:
```python
# DELETE THIS BLOCK:
STATUS_FLOW = {
    "Open": ["In Progress"],
    "In Progress": ["Completed", "Open"],
    "Completed": ["Closed", "In Progress"],
    "Closed": ["Completed"]
}
```

Add import at top of file:
```python
from app.modules.shared.domain.state_machine import StateMachine
```

**Step 2: Replace STATUS_FLOW guard in `update_status` with StateMachine call**

Replace:
```python
current_status = task.get("status", "Open")
if new_status != current_status and new_status not in self.STATUS_FLOW.get(current_status, []):
     raise HTTPException(status_code=400, detail=f"Illegal transition: {current_status} -> {new_status}")
```

With:
```python
current_status = task.get("status", "Open")
try:
    StateMachine.validate_transition("TASK", current_status, new_status)
except Exception as e:
    raise HTTPException(status_code=400, detail=str(e))
```

---

## Task 4: Fix TaskCreate — Remove `organisation_id` from Request Body

**Why:** `organisation_id` is a security-critical field. It must come from the authenticated JWT token (server-side), not from the client request body. A malicious client could set any org_id.

**Files:**
- Modify: `apps/api/app/modules/tasks/schemas/dto.py`
- Modify: `apps/api/app/modules/tasks/application/task_service.py`

**Step 1: Remove `organisation_id` from `TaskCreate`**

```python
class TaskCreate(BaseSchema):
    project_id: str
    task_description: str
    assigned_to_user_id: Optional[str] = None
    assigned_to_name: str
    assigned_to_type: str = "user"
    deadline: Optional[datetime] = None
    priority: str = "Normal"
    notes: Optional[str] = None
    scheduler_task_id: Optional[str] = None
```

**Step 2: Inject `organisation_id` from user in `create_task` service method**

In `task_service.py`, `create_task` already does:
```python
task_dict = data.model_dump()
task_dict.update({
    "status": "Open",
    "sr_no": sr_no,
    "created_by": user["user_id"],
    ...
})
```

Add `organisation_id` to that update block:
```python
task_dict.update({
    "organisation_id": user["organisation_id"],   # ← ADD THIS
    "project_id": data.project_id,                 # ensure it's set
    "status": "Open",
    ...
})
```

**Step 3: Fix web `new/page.tsx` — remove `organisation_id` from POST body**

File: `apps/web/src/app/admin/tasks/new/page.tsx`

The form `formData` state doesn't include `organisation_id`, so the `api.post` call should already be clean. Verify the POST body only contains the fields in `TaskCreate` (without `organisation_id`).

Also fix the hardcoded `created_by_name: "Admin User"` comment on line 38 — this field doesn't belong in the request body either. The API derives it from the JWT. Remove that field from the POST body entirely.

---

## Task 5: Add Tasks to Mobile Admin Navigation

**Why:** `apps/mobile/app/(admin)/tasks/` directory exists with 3 screens, but the admin `_layout.tsx` has no `Tabs.Screen` entry for "tasks". The folder is dead code — users cannot reach it.

**Files:**
- Modify: `apps/mobile/app/(admin)/_layout.tsx`

**Step 1: Add a hidden Tasks `Tabs.Screen` entry**

The tasks screens should be reachable via `router.push('/(admin)/tasks')` but do NOT need a visible bottom tab (user said "separate menu item", implied in More/Settings). Add it as a hidden route:

```tsx
{/* Hidden screens - accessible but not in tab bar */}
<Tabs.Screen
  name="tasks"
  options={{
    href: null,  // hidden from tab bar, reachable via router.push
  }}
/>
```

Place this alongside the other `href: null` entries (after `workers-report`).

**Step 2: Add a Tasks entry in the Settings/More screen**

File: `apps/mobile/app/(admin)/settings/` — find the index or main settings screen and add a Tasks navigation item.

Check what file handles the "More" tab content, then add:
```tsx
<Pressable onPress={() => router.push('/(admin)/tasks')}>
  <Text>Tasks</Text>
</Pressable>
```

Match the existing list item styling in that file.

---

## Task 6: Add Sub-tabs to Web Sidebar Tasks Entry

**Why:** The Tasks sidebar item is a flat link. The Project Planner has expandable sub-tabs (Grid, Gantt, Kanban). Tasks should show Active / Board sub-links consistently.

**Files:**
- Modify: `apps/web/src/components/layout/Sidebar.tsx`

**Step 1: Replace flat Tasks entry with expandable children**

Find (lines ~99-104):
```typescript
{
  href: "/admin/tasks",
  icon: CheckSquare,
  label: "Tasks",
  key: "tasks",
},
```

Replace with:
```typescript
{
  href: "/admin/tasks",
  icon: CheckSquare,
  label: "Tasks",
  key: "tasks",
  children: [
    { href: "/admin/tasks?tab=list", label: "Active Tasks", key: "tasks_active" },
    { href: "/admin/tasks?tab=board", label: "Kanban Board", key: "tasks_board" },
  ],
},
```

**Step 2: Verify the tab param key matches the page**

In `apps/web/src/app/admin/tasks/page.tsx`, the tab toggle uses `?tab=board` for Kanban. Confirm the sidebar href `?tab=board` matches exactly.

---

## Task 7: Fix `update_task_details` — Use StateMachine for Modification Guard

**Why:** `update_task_details` manually checks `if task.get("status") == "Closed"` instead of using `StateMachine.check_modification_allowed()`. This is inconsistent with how other modules guard edits.

**Files:**
- Modify: `apps/api/app/modules/tasks/application/task_service.py`

**Step 1: Replace manual Closed check with StateMachine**

Replace:
```python
if task.get("status") == "Closed": raise HTTPException(status_code=400, detail="Modification not allowed")
```

With:
```python
try:
    StateMachine.check_modification_allowed("TASK", task.get("status", "Open"))
except Exception as e:
    raise HTTPException(status_code=400, detail=str(e))
```

---

## Verification Checklist

After all tasks complete, verify:

```bash
# 1. API starts clean
cd apps/api && python -m uvicorn app.main:app --port 8000

# 2. AI summary endpoint resolves correctly (not 404)
# Open browser: http://localhost:8000/docs
# Find GET /tasks/ai-summary - should be listed BEFORE GET /tasks/{task_id}

# 3. DELETE endpoint exists
# Find DELETE /tasks/{task_id} in /docs

# 4. Lint passes
cd apps/api && flake8 app/modules/tasks/

# 5. Web lint passes
cd apps/web && npm run lint

# 6. Mobile lint passes
cd apps/mobile && npm run lint

# 7. Root lint (zero error policy)
cd D:\_repos\TAC-PMC-CRM && pnpm lint
```

**Manual functional tests:**
- Create a task via web → appears in list
- Move task status Open → In Progress via Kanban drag
- Try illegal transition (Open → Completed) → should 400
- Open mobile tasks list → should load (navigation works)
- Open mobile task detail → should show audit log
- Click AI Summary on dashboard → should return data (not 404)
- Delete a new Open task → disappears from list
- Try editing a Closed task → should 400

---

## Execution Order

Run tasks in this order (each task is independent after Task 1 unblocks Task 2):

1. **Task 1** (Route order fix) — unblocks AI summary on dashboard immediately
2. **Task 2** (DELETE method) — completes the route added in Task 1
3. **Task 3** (StateMachine alignment) — fixes status transition logic
4. **Task 4** (Remove org_id from schema) — security fix
5. **Task 5** (Mobile navigation) — adds tasks to mobile
6. **Task 6** (Sidebar sub-tabs) — UI polish
7. **Task 7** (StateMachine for edits) — consistency fix
