# TAC-PMC-CRM: Fix All Critical Issues

## Context
The CRM is not functional for the user. Root causes span four areas:
1. **Mobile app** uses a hardcoded LAN IP (`192.168.31.251`) — broken on any other machine/network
2. **Web data loading** (clients, vendors, settings) fails silently — errors are swallowed in catch blocks, no user feedback, no visibility into what's wrong
3. **PDF exports** fail on Windows — WeasyPrint requires GTK (a Linux dependency), and the fallback to ReportLab is incomplete; also a missing `time` import in project routes
4. **UI bugs** — Settings page uses `alert()` instead of toasts, Gantt bar drag visual feedback is never activated (`isDragging` prop never passed), TaskDrawer missing light-mode color parity

Running locally on Windows in dev mode (API: `http://127.0.0.1:8000`, Web: `http://localhost:3000`).

---

## Phase 1 — Fix Mobile App Connectivity

**Problem:** `apps/mobile/.env` has `EXPO_PUBLIC_BACKEND_URL=http://192.168.31.251:8000` (hardcoded LAN IP).

**Fix:**
- File: `D:\_repos\TAC-PMC-CRM\apps\mobile\.env`
- Change to `EXPO_PUBLIC_BACKEND_URL=http://10.0.2.2:8000` for Android emulator (maps to host's localhost)
- Or `http://localhost:8000` for Expo web / iOS simulator
- Add fallback comment so future devs understand why

**Entry point:**
- `apps/mobile/services/apiClient.ts:53-56` — reads `EXPO_PUBLIC_BACKEND_URL`

---

## Phase 2 — Fix Web Data Loading (Silent Failures)

All three pages swallow errors without UI feedback. Users see blank/empty states with no explanation.

### 2a. Settings Page (`apps/web/src/app/admin/settings/page.tsx`)
- **Lines 89-107**: `catch` block only `console.log`s — show a toast/error state to user
- **Lines 114-117**: Replace `alert("Global settings saved successfully!")` and `alert("Failed to save settings.")` with toast notifications (consistent with `clients/page.tsx:164` pattern)
- Import and use the existing toast pattern from the rest of the app

### 2b. Client Page (`apps/web/src/app/admin/clients/page.tsx`)
- Verify SWR error state is handled — show error message if fetch fails (not just empty state)
- Add error boundary or error display when `useSWR` returns an error

### 2c. Vendor Page (`apps/web/src/app/admin/vendors/`)
- Same pattern — ensure `useSWR` error is surfaced to user, not silently swallowed
- Verify `active_only` query param is correctly appended in the fetcher URL

### 2d. API lib error visibility (`apps/web/src/lib/api.ts`)
- Add a response interceptor log or toast for 4xx/5xx errors that aren't handled at the page level
- Ensure 401 refresh failures redirect to login (not silently fail)

---

## Phase 3 — Fix PDF Exports

**Problem on Windows:** WeasyPrint requires GTK system libraries (Linux/macOS). On Windows it crashes.

### 3a. Missing `time` import
- File: `apps/api/app/modules/project/api/routes.py:225`
- Add `import time` at the top of the file

### 3b. WeasyPrint Windows fallback
- File: `apps/api/app/core/export_service.py`
- The fallback to ReportLab exists but is incomplete for some report types
- Wrap WeasyPrint calls in a try/except that catches `OSError`/`ImportError` (GTK missing) and routes to ReportLab fallback for ALL export types
- Return proper HTTP 500 with descriptive message if both engines fail (instead of silent pass)

### 3c. Remove debug file write
- File: `apps/api/app/modules/project/application/scheduler_service.py:69-74`
- Remove the `# DEBUG: Save payload to file` block that writes `last_scheduler_payload.json` on every calculation

### 3d. Fix bare `except: pass` clauses
- `scheduler_service.py:73-74` and `:211-212` — replace with `except Exception as e: logger.warning(...)` to surface real errors

---

## Phase 4 — Fix UI Bugs (Phase 15)

### 4a. Gantt Bar `isDragging` prop never passed
- File: `apps/web/src/components/scheduler/GanttChart.tsx`
- The `Bar` component accepts `isDragging: boolean` (line 46) with visual feedback styling (lines 84-89)
- Find where `<Bar ...>` is rendered and pass `isDragging={activeDragTaskId === task.id}` (the `activeDragTaskId` state is already tracked at line ~234)
- This unlocks the existing orange ring/scale visual during drag

### 4b. TaskDrawer Light Mode Parity
- File: `apps/web/src/components/scheduler/TaskDrawer.tsx`
- Multiple elements have `dark:` prefixed classes without light equivalents
- Key lines: 40, 107, 163, 206, 209, 218, 323, 329, 336, 339, 353, 401, 402, 419, 432, 439, 455, 476, 486, 522, 529, 530, 531, 534, 539, 540, 545
- Add corresponding light-mode Tailwind color classes for each `dark:` class missing a light equivalent

### 4c. Settings page already covered in Phase 2 (alert → toast)

---

## Critical Files

| File | Change |
|------|--------|
| `apps/mobile/.env` | Fix hardcoded LAN IP |
| `apps/mobile/services/apiClient.ts:53-56` | Verify fallback URL |
| `apps/web/src/app/admin/settings/page.tsx:89-107, 114-117` | Replace alert() with toast, surface errors |
| `apps/web/src/app/admin/clients/page.tsx` | Surface SWR errors in UI |
| `apps/web/src/app/admin/vendors/page.tsx` | Surface SWR errors, fix active_only param |
| `apps/web/src/lib/api.ts` | Ensure 401 failures redirect to login |
| `apps/api/app/modules/project/api/routes.py:225` | Add `import time` |
| `apps/api/app/core/export_service.py` | Fix WeasyPrint Windows fallback |
| `apps/api/app/modules/project/application/scheduler_service.py:69-74, 211-212` | Remove debug write, fix bare excepts |
| `apps/web/src/components/scheduler/GanttChart.tsx:374+` | Pass `isDragging` prop to Bar |
| `apps/web/src/components/scheduler/TaskDrawer.tsx` | Add light-mode color classes |

---

## Execution Order

1. Mobile `.env` fix (30 sec, immediate impact)
2. `import time` fix in routes.py (1 line)
3. Settings page — alert → toast + error visibility
4. Client/vendor pages — surface SWR errors
5. Export service — WeasyPrint Windows fix
6. Scheduler service — remove debug write, fix bare excepts
7. GanttChart — pass `isDragging` to Bar
8. TaskDrawer — light mode parity

---

## Verification

- **Mobile**: Open Expo app → login screen should connect → data loads
- **Web clients**: Navigate to `/admin/clients` → data loads OR a visible error message explains why not
- **Web vendors**: Navigate to `/admin/vendors` → same
- **Settings**: Open settings → save → toast appears (not browser alert)
- **PDF**: Export a payment certificate → file downloads without 500 error
- **Gantt drag**: Drag a task bar → bar shows orange highlight ring while dragging
- **TaskDrawer light mode**: Toggle to light mode → all text/backgrounds readable
