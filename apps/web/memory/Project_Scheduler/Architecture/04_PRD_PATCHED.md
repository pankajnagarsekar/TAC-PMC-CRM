# Product Requirements Document (PATCHED)
**Module:** Enterprise Project Portfolio Management (PPM) Scheduler  
**Objective:** Replace the existing "Payment Schedule" module with a standalone, AI-driven, MS Project-grade relational scheduling engine.  
**Constraint:** Must integrate with, but completely isolate from, the existing Work Order (WO) and Payment Certificate (PC) creation logic.  
**Patch Notes:** Tier 1 gap fixes marked with `[GAP-FIX]`.

---

## 1. Product Overview

The PPM Scheduler transforms the CRM from a static financial tracker into an active project orchestrator. It introduces a Relational Calculation Engine (Critical Path Method) that automatically calculates project timelines, manages resource capacity, and tracks cash flow forecasts against a locked baseline.

**`[GAP-FIX]` Core Design Principles:**
- **Deterministic:** Same input always produces same output. The CPM pipeline runs in a fixed, defined order (see Constitution §4).
- **Financially Isolated:** The Scheduler cannot create, edit, or delete Work Orders or Payment Certificates. Read-only aggregation only.
- **Audit-Complete:** Every change is logged with who, when, what, and (optionally) why.
- **Gracefully Degrading:** AI unavailability, financial aggregation failures, and network issues never break core scheduling.

---

## 2. Target Audience

- **Admins/Project Managers:** "God View" — Gantt, Kanban, Master Grid. Manipulate dependencies, handle resource leveling, lock baselines. Full edit access.
- **Site Supervisors:** Mobile App to log daily progress (DPRs) and timesheets. Edit restricted to assigned tasks only.
- **Clients:** Read-only portal showing live S-Curves, simplified Gantt timelines, and real-time cash flow forecasts. `[GAP-FIX]` Cannot see retention values, internal costs, or cost variance. Field-level security enforced server-side.

---

## 3. Core Features & Requirements

### 3.1. The Master Grid (Data Layer)

- **WBS Hierarchy:** Infinite parent/child nesting. Parent tasks auto-rollup dates (min/max), costs (sum), and completion percentage (**`[GAP-FIX]` weighted by baseline_cost**, not simple average).
- **`[GAP-FIX]` Summary Task Types:** Parents can be "auto" (rollup enforced, fields read-only) or "manual" (admin can override calculated values; system flags divergence).
- **Locked Baselines:** Freeze Baseline Start, Finish, Duration, and Cost. Up to 11 historical snapshots. **`[GAP-FIX]` Baselines are immutable after locking — no API can modify them. Each baseline also captures a financial snapshot (total WO value, payment value at lock time) for accurate historical S-Curve comparison.**
- **Dependency Engine:** Full support for FS, SS, FF, and SF relationships with Lead and Lag modifiers. **`[GAP-FIX]` Hard vs Soft dependencies.** Hard = engine enforces strictly. Soft = engine calculates but allows violation with warning.
- **`[GAP-FIX]` Constraint System:** Per-task scheduling constraints: ASAP, ALAP, Start No Earlier Than, Start No Later Than, Finish No Earlier Than, Finish No Later Than, Must Start On, Must Finish On. Constraints bound the CPM engine output.
- **`[GAP-FIX]` Circular Dependency Prevention:** The system validates the dependency graph (DAG check) before every CPM run. Circular dependencies are rejected with clear error messages identifying the cycle.
- **Analytical Columns:** Auto-calculated Total Slack (positive/negative), Critical Path identification, **`[GAP-FIX]` Deadline Variance (days), Deadline Breach flag (persisted for alerting and audit).**
- **Read-Only Financial Sync:** Displays WO Value, WO Retention Value, Payment Value, and Weightage (%) pulled dynamically from WO/PC modules. **`[GAP-FIX]` Weightage uses a cached project_total_baseline_cost to avoid expensive re-aggregation.**
- **`[GAP-FIX]` Cross-Project Dependencies:** Tasks can reference predecessors in other projects. External dependencies are flagged visually in the Gantt and managed separately in the dependency table.

### 3.2. Interactive Interfaces

- **Gantt Chart:** Visual timeline with drag-and-drop linking, Baseline overlay comparisons, visual red flags for Critical Path and breached Deadlines.
  - **`[GAP-FIX]` Drag Guardrails:** Prevents dragging tasks into invalid positions (before hard predecessors). Shows warnings when moving critical path tasks.
  - **`[GAP-FIX]` Dependency Rendering Limits:** At >200 visible dependency lines, shows critical-path-only dependencies by default with toggle for all.
- **Kanban Board:** State-based board bidirectionally synced with Master Grid.
  - **`[GAP-FIX]` State Machine Enforcement:** Invalid state transitions (e.g., Draft → Completed) are rejected with visual feedback. Card snaps back.
- **Task Deep-Dive Panel:** Modal for editing dependencies, uploading task-specific files, viewing synced timesheets, and Interactive MoM thread.
  - **`[GAP-FIX]` Audit History tab:** Shows chronological change log for the task.
  - **`[GAP-FIX]` AI confidence scores:** Shown alongside AI suggestions in MoM tab.

### 3.3. Enterprise PPM & AI Layer

- **Resource Leveling:** Global capacity tracking across all active projects.
  - **`[GAP-FIX]` Multi-Resource Assignment:** Tasks can have multiple assigned resources (not just one).
  - **`[GAP-FIX]` Resource Cost Rates:** Per-resource cost_rate_per_hour enables accurate earned value calculation.
  - **`[GAP-FIX]` Resource Calendars:** Individual resources can have calendar overrides (different work days/holidays than the project default).
  - **`[GAP-FIX]` Deterministic Resolution:** When overallocation is detected, tasks are delayed based on strict priority rules: critical path first → project priority → task priority → FIFO. Same input always produces same leveling output.
- **AI Auto-Pilot:** AI suggests Category Codes, Task Durations, and Resource Allocations based on historical data. AI extracts Action Items from MoM thread to auto-generate sub-tasks.
  - **`[GAP-FIX]` Confidence Scores:** Every AI suggestion includes a confidence score (0.0 - 1.0) displayed to the admin.
  - **`[GAP-FIX]` Feedback Loop:** System stores AI-suggested values alongside actual values. AI accuracy is trackable over time.
  - **`[GAP-FIX]` Validation Layer:** AI-generated tasks are checked for duplicates, circular dependencies, and resource existence before preview.
  - **`[GAP-FIX]` Human Confirmation Required:** AI never auto-commits changes. All AI outputs pass through a preview → confirm workflow.
- **Predictive Risk Alerts:** Automated warnings if critical path task slips, detailing day-count impact on final delivery. **`[GAP-FIX]` Alerts are persisted (via `is_deadline_breached` flag) and delivered via in-app notification + email for HIGH priority events.**

### 3.4. Native BI Dashboards

- **S-Curve:** Planned Value (Baseline) vs. Earned Value (Actuals) **`[GAP-FIX]` vs. Actual Cost (WO Value).** Uses exact Earned Value formulas from Constitution §9.
- **Cash Flow Forecaster:** Future capital requirements mapped against scheduled finish dates. **`[GAP-FIX]` Overlays actual past spend against future forecast.**
- **Resource Heatmap:** Visual grid of over/under-utilized vendors. **`[GAP-FIX]` Clickable cells showing which tasks cause overallocation.**
- **`[GAP-FIX]` KPI Cards:** SPI, CPI, Schedule Variance, Cost Variance with color-coded health indicators.
- **`[GAP-FIX]` Baseline Comparison:** Visual diff between two baselines showing schedule variance and cost variance per task.

### 3.5. `[GAP-FIX]` Operational Features

- **Undo System:** `Ctrl+Z` to undo the last 50 actions (per-user, per-session). Undo fires a new engine recalculation with reverted values.
- **Bulk Operations:** Multi-select tasks for bulk resource assignment, status change, category change, or deletion.
- **Search & Filter:** Full-text search + filter by status, criticality, resource, category, date range. Filters apply across all views simultaneously.
- **Keyboard Shortcuts:** Tab navigation, Enter to open drawer, Delete with confirmation, Ctrl+Click for multi-select.
- **Data Export:** Excel, PDF (Gantt image + summary), CSV.
- **Import Error Handling:** Partial failure support with validation report. Admin reviews and fixes invalid rows before committing.

### 3.6. `[GAP-FIX]` Security & Access Control

- **Role-Based Access Control (RBAC):** Super Admin, Project Manager, Supervisor, Client, Viewer roles with granular permissions per Constitution §12.
- **Field-Level Security:** Sensitive financial fields stripped from API responses based on role.
- **Project Lifecycle Locking:** Projects transition through Draft → Planning → Active → Substantially Complete → Closed, with progressively restricted editing permissions at each stage.
