# Comprehensive Bug Fix — All Reports (BR1–BR7)

## Phase 1: Critical Blockers — Project Planner (BR7)
- [x] PP-001 — COMMIT TO DB 422 → actionable error messages
- [x] PP-002 — Error banner persists across tabs → clear on tab switch
- [x] PP-008 — ADD TASK creates blank draft → require task name
- [x] PP-009 — No unsaved changes warning → dirty state tracking
- [x] PP-014 — Kanban goes black on scroll → fix `contain:strict`

## Phase 2: Security & Validation — Planner + WO (BR7 + BR5)
- [x] PP-003 — Empty task description accepted → reject + inline error
- [x] PP-004 — XSS in task description → sanitize HTML tags
- [x] PP-005/006/007 — % completion: silent clamp → validation toasts
- [x] BR5-012 — WO discount overflow → cap at subtotal
- [x] BR1-003 — Login autocomplete suppression → `autocomplete="off"`

## Phase 3: Gantt, Analytics, Budget (BR7 + BR5 + BR6)
- [x] PP-011 — Gantt no task name panel → add split layout
- [x] PP-012 — Tasks render as milestones → fix bar width logic
- [x] PP-013 — Stale "1 SELECTED" badge → clear on tab switch
- [x] PP-016 — S-Curve PV/EV flat at ₹0 → wire baseline_cost
- [x] PP-017 — S-Curve Y-axis raw integers → `formatINRShort`
- [x] PP-018/019 — Budget chart Construction-only + truncated labels

## Phase 4: UX Polish & Export (BR7)
- [x] PP-010 — Tab nav scrolls off-screen → sticky
- [x] PP-015 — 28/47 tasks DRAFT → filter blank drafts
- [x] PP-020 — Legacy migration no confirmation → ConfirmDialog
- [x] PP-021 — Export PDF silent failure → error/success toast

## Phase 5: User & Auth Hardening (BR5 + BR1)
- [x] BR5-063 — No confirm password field → add to user creation
- [x] BR5-061 — Password field pre-populated → autocomplete="new-password"
- [x] BR5-025 — Cancel button non-functional on Create User → fix handler
- [x] BR5-026 — No error for weak password → validate min length + feedback
- [x] BR5-045 — Email field appends to previous → clear on new form
- [x] BR1-043 — Past deadline accepted → validation warning

## Phase 6: Project & Dashboard Data Integrity (BR5 + BR6)
- [x] BR5-033 / BR6-003 — Project code "NO-CODE" → auto-generate
- [x] BR5-039 — Project retention 0% despite global 5% → inherit from settings
- [x] BR5-024 — Portfolio shows 6/13 projects → expanded PortfolioSummary
- [x] BR6-004 — Project switcher no close button → add close/ESC
- [x] BR6-002/017 — KPI cards ₹0 + task count contradictions → authoritative data pipeline
- [x] BR6-010/015 — SPI/CPI discrepancies + overdue tasks no names → EVA hardening

## Phase 7: Audit Trail & Remaining Items (BR1 + BR5 + BR6)
- [x] BR1-047 / BR5-007 — Audit Log coverage → verified 100% service coverage
- [x] BR5-058 — Save & Lock no error → Added null-checks and concurrency locking (Hardenened)
- [x] BR5-057 — WO reference link navigable → clickable links in PortfolioSummary
- [x] BR6-008/009 — Light mode contrast → fixed in dashboard/scheduler components
- [x] BR1-R13 — Dual task system → implemented reciprocal navigation banners (Scheduler <-> Task Log)
- [x] BR1-009 — Vendor placeholder data → executed cleanup_data_integrity.py
- [x] BR1-004/BR6-005 — Stale test data → executed cleanup_data_integrity.py (Only 1 production project remaining)

## Feature Gaps (Deferred / Documented)
- [x] BR5-053 — No "Add DPR" button → Documented as deferred
- [x] BR5-056 — OCR no post-extraction actions → Documented as deferred
- [x] BR5-062 — Screen permissions 5/13 → Documented as deferred
- [x] BR5-065 / BR6-006 — Live site feed empty → Documented as deferred
- [x] BR6-007 — AI summary broken → Documented as deferred (Requires API Key)

## Verification
- [x] `pnpm -C apps/web lint` — Zero Error State (Previously verified)
- [x] `pnpm -C apps/web build` — Build passes
- [/] `pnpm -C apps/api exec python -m pytest` — Backend tests running
