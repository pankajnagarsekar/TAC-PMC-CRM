# Scheduler CPM Enhancements (doc plan)

## Summary
- Update `apps/api/app/modules/scheduler/calculate_critical_path.py` so that the CPM engine respects manual-mode tasks, the full set of dependency link and constraint types, the auto-summary roll-up, deadline tracking, draft-to-not-started transitions, and calculation metadata that AI agents need when editing or validating the scheduler.
- Audience: AI agent writers/implementers who will edit `calculate_critical_path.py` and validate its outputs for project scheduling.

## Architecture snapshot
The core CPM flow lives in `apps/api/app/modules/scheduler/calculate_critical_path.py`:
1. Input parsing (project start, task durations, predecessors/dependencies) and construction of `task_map`/`preds_full` (lines ~40-140).
2. Graph build via successor lists and Kahn's topological sort (lines ~160-220).
3. Forward/backward passes that compute ES/EF/LS/LF/slack (lines ~224-318) and apply constraints/calc link types.
4. Summary rollup pass that updates auto summaries from their children (lines ~320-356).
5. Output loop that assembles JSON plus metadata, constraints, deadline/critical info, and status corrections (lines ~360-430).

## Step 2 (Manual mode)
- Each task already stores `is_manual = (task_mode  or "Auto") == "Manual"`, and the forward pass currently "freezes" manual tasks (lines ~234-253). Document that the concrete behavior is to read `scheduled_start`/`scheduled_finish` from the original input, defaulting them to the project start and duration when missing, and then to skip any CPM adjustments or constraint enforcement so their ES/EF remain untouched.
- Emphasize that altering manual fields should be avoided during CPM and that the engine should treat their ES/EF as provided even if their predecessors or constraints would normally move them.

## Step 3 (Dependency link types)
- `_compute_es_from_predecessors` (lines ~110-152) collects each `preds_full` entry (populated from `predecessors` plus the legacy `dependencies` list). The forward pass forwards FS/SS/FF/SF link types plus `lag_days` when determining the successor earliest start.
- The backward pass (lines ~252-318) mirrors the same link metadata when determining LF/LS, so the doc should note that `preds_full` entries must be consistent in both directions (link type, lag, `task_id`, `strength`).
- Agents reading this doc should ensure that `preds_full` is cleaned (no empty IDs) and that each `lag_days` is converted to an `int` before CPM begins.

## Step 4 (Constraint types)
- `_apply_constraint` (lines ~62-107) is called in the forward pass after predecessor-based ES/EF computation. Detail how each constraint is meant to behave: ASAP (no change), ALAP (handled later in backward pass), SNET/SNLT/FNET/FNLT (bounding ES/EF against the provided `constraint_date`), and MSO/MFO (force ES/EF to the constraint date).
- Note that `ALAP` is intentionally skipped in `_apply_constraint` because its effect occurs in the backward pass so that late dates answer the constraint.
- The doc should reaffirm the expected outcome: after `_apply_constraint`, the computed early dates for auto tasks must respect the constraint, and downstream calculations rely on those bounded values.

## Step 5 (Parent rollup)
- Describe the children map creation (lines ~300-305) and reverse-topological processing (lines ~310-356) that recalc auto summaries.
- Summaries with `is_summary == True` and `summary_type == "auto"` set their ES to `MIN(child ES)`, EF to `MAX(child EF)`, duration to `EF - ES`, slack to `MIN(child slack)`, and `is_critical` accordingly.
- Document that `percent_complete` is recomputed as a baseline-cost-weighted average of the children's original percentages, and highlight that summary-related changes cascade to dependent tasks that may be manual (emphasize manual tasks already freeze their own dates but may be successors of summaries).

## Step 6 (Deadline variance)
- Mention that the output loop (lines ~374-410) computes two fields only when a task has a `deadline`: `deadline_variance_days = (EF - deadline).days` and `is_deadline_breached = deadline_variance_days > 0`. Document the expectation that these fields are `null`/`false` when no deadline is present.

## Step 7 (DRAFT auto-transition)
- Explain that as part of result assembly (lines ~384-398) every task currently maps `task_status` from the original data, but if the status equals `"draft"`, CPM should update it to `"not_started"` before emitting the response so downstream agents see the new status.

## Step 8 (Calculation metadata)
- State that `calculation_version` (a UUID) and `calculated_at` (UTC ISO timestamp) are generated once per CPM run (lines ~345-347 and ~418-423) and attached to both each task (`updated` dictionary) and the response wrapper (`return` payload) to help agents track results.
- Clarify when they are set (before the output loop) and propagated into the final JSON that the API returns.

## Testing & Verification
- Recommend unit tests that feed mock task lists covering each link type (FS/SS/FF/SF with positive/negative lag), each constraint type, a hierarchy of summaries, and a manual task to ensure ES/EF remain unchanged.
- Suggest tests that assert `deadline_variance_days`/`is_deadline_breached` for tasks with deadlines (both before and after the planned finish) and that these fields stay `null` when no deadline exists.
- Advise verifying that tasks marked manual keep their original scheduled dates even if their predecessors change and that draft statuses become `not_started` post-run.

## Assumptions
- Only `calculate_critical_path.py` needs editing for these steps; no other files are required.
- Input tasks already include `predecessors`, `deadline`, `baseline_cost`, `scheduled_start`, `scheduled_finish`, and normalized `task_status` values.
