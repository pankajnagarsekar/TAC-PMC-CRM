# Phase-by-Phase Claude Code Feeding Map
**Purpose:** This document tells you EXACTLY which files to feed into each Claude Code session, in what order, and what to ask for in each session.

**Golden Rules:**
1. EVERY session starts with `00_SYSTEM_CONSTITUTION.md`. No exceptions.
2. Never dump all 6 specs into one session. Feed only what's relevant.
3. Each phase ends with a Handoff Artifact (`PHASE_N_CONTRACT.md`) that feeds into the next phase.
4. The Living Types file (`shared_types.ts` / `shared_models.py`) is updated at each phase boundary and fed forward.

---

## Phase 1: Foundation & Database (Weeks 1-2)

### Session 1.1 — Schema Scaffolding
**Feed:**
| Order | Document | Purpose |
|-------|----------|---------|
| 1 | `00_SYSTEM_CONSTITUTION.md` | System laws, invariants, data contracts |
| 2 | `01_Backend_Schema_Spec.md` (patched) | Full schema definitions |
| 3 | `05_Application_Flow.md` → Section 1 only | Project setup flow context |

**Prompt Strategy:**
> "Create all MongoDB collection schemas as Pydantic models in Python. Include all fields from the spec, all validators (state machine transitions, DAG validation hooks, invariant checks from the Constitution §2). Generate the `shared_models.py` file with all type definitions. Do NOT implement any API routes or business logic yet."

**Expected Output:**
- `models/project_calendars.py`
- `models/enterprise_resources.py`
- `models/project_schedules.py`
- `models/schedule_baselines.py`
- `models/shared_types.py` (enums, constants, shared types)
- `validators/dag_validator.py` (circular dependency detection — stub with interface)
- `validators/state_machine.py` (task state transitions)

### Session 1.2 — Financial Handshake Pipelines
**Feed:**
| Order | Document | Purpose |
|-------|----------|---------|
| 1 | `00_SYSTEM_CONSTITUTION.md` | Financial invariants (§2.3), earned value formulas (§9) |
| 2 | `01_Backend_Schema_Spec.md` → Section 2 only | Financial integrity spec |
| 3 | Code from Session 1.1 | The Pydantic models (so pipelines match schema) |

**Prompt Strategy:**
> "Build the read-only MongoDB aggregation pipelines in FastAPI for the financial handshake. Three pipelines: WO Value aggregation, Retention Value aggregation, Payment Value aggregation. All must be `$lookup` only — zero writes to legacy collections. Include parent rollup aggregation for summary tasks. Write unit tests that verify zero write operations."

**Expected Output:**
- `pipelines/financial_aggregations.py`
- `tests/test_financial_readonly.py`

### Session 1.3 — Index Strategy & Migration Foundation
**Feed:**
| Order | Document | Purpose |
|-------|----------|---------|
| 1 | `00_SYSTEM_CONSTITUTION.md` → §10 (system limits) |
| 2 | `06_Implementation_Plan.md` → Week 1 details |
| 3 | Code from Sessions 1.1 + 1.2 |

**Prompt Strategy:**
> "Create MongoDB index definitions for all collections. Optimize for: project_id + wbs_code queries, task_id lookups, parent_id hierarchy traversal, and the financial $lookup join conditions. Also create the migration script skeleton that will map legacy Payment Schedule data to the new project_schedules format — structure only, not the actual mapping logic yet."

**Expected Output:**
- `db/indexes.py`
- `db/migration_skeleton.py`

### Phase 1 Handoff Artifact
At the end of Week 2, create `PHASE_1_CONTRACT.md` documenting:
- Exact collection schemas (copy from generated Pydantic models)
- Financial pipeline interfaces (input params, output shape)
- Any deviations from the spec and why
- The `shared_models.py` file (this becomes the Living Types file)

---

## Phase 2: CPM Execution Engine (Weeks 3-5)

### Session 2.1 — Engine Interface & Test Fixtures
**Feed:**
| Order | Document | Purpose |
|-------|----------|---------|
| 1 | `00_SYSTEM_CONSTITUTION.md` | Calculation pipeline (§4), invariants (§2.1), data contracts (§7.2, §7.3) |
| 2 | `02_Technical_Architecture_Spec.md` → Section 4 | Engine architecture |
| 3 | `PHASE_1_CONTRACT.md` | Schema context from previous phase |

**Prompt Strategy:**
> "Define the Python function signatures and I/O contracts for the CPM engine. Create: `calculate_critical_path(input: CalculationRequest) -> CalculationResponse` matching the Constitution §7.2 and §7.3 contracts exactly. Also create 5 test fixtures: (1) simple 3-task linear chain, (2) parallel tasks with shared predecessor, (3) all 4 dependency types (FS/SS/FF/SF) with lag, (4) task with deadline breach, (5) circular dependency that must be rejected. Do NOT implement the math yet."

**Expected Output:**
- `engine/interfaces.py` (function signatures, I/O types)
- `engine/test_fixtures.py` (5 fixture datasets)
- `tests/test_engine_contracts.py` (test shells)

### Session 2.2 — Forward & Backward Pass
**Feed:**
| Order | Document | Purpose |
|-------|----------|---------|
| 1 | `00_SYSTEM_CONSTITUTION.md` → §4 (Steps 1-4), §2.1 (invariants) |
| 2 | `02_Technical_Architecture_Spec.md` → Section 4.1 |
| 3 | Code from Session 2.1 (interfaces + fixtures) |

**Prompt Strategy:**
> "Implement the Forward Pass and Backward Pass in `calculate_critical_path.py`. Must handle: the 6-day Goa work week, holiday skipping from the project calendar, all 4 dependency types (FS/SS/FF/SF) with lead/lag parsing (e.g., '4FF-2d'). After both passes, calculate Total Slack and flag critical path tasks. All tests from Session 2.1 fixtures must pass."

**Expected Output:**
- `engine/calculate_critical_path.py`
- `engine/calendar_utils.py` (working day math, holiday skipping)
- `engine/dependency_parser.py` (predecessor string parsing)

### Session 2.3 — Constraint System & DAG Validation
**Feed:**
| Order | Document | Purpose |
|-------|----------|---------|
| 1 | `00_SYSTEM_CONSTITUTION.md` → §4 (Steps 1, 3), §2.2 (DAG invariant) |
| 2 | Code from Sessions 2.1 + 2.2 |

**Prompt Strategy:**
> "Implement: (1) DAG validation using topological sort — reject circular dependencies with clear error messages identifying the cycle. (2) Constraint system supporting ASAP, ALAP, SNET, SNLT, FNET, FNLT, MSO, MFO. Constraints modify the CPM output as bounds, not replacements. (3) Post-calculation invariant checks from Constitution §2.1 — every engine run must verify all invariants before returning results. Add test cases for each constraint type and circular dependency scenarios."

**Expected Output:**
- `engine/dag_validator.py` (full implementation)
- `engine/constraints.py`
- `engine/invariant_checker.py`
- `tests/test_dag_validation.py`
- `tests/test_constraints.py`

### Session 2.4 — Resource Leveling
**Feed:**
| Order | Document | Purpose |
|-------|----------|---------|
| 1 | `00_SYSTEM_CONSTITUTION.md` → §4 (Step 5), §10 (limits) |
| 2 | `02_Technical_Architecture_Spec.md` → Section 4.2 |
| 3 | `01_Backend_Schema_Spec.md` → enterprise_resources schema |
| 4 | Code from Sessions 2.2 + 2.3 (CPM engine) |

**Prompt Strategy:**
> "Implement resource_capacity.py. Must: (1) detect overallocations across the enterprise resource pool, (2) resolve conflicts using priority rules: task criticality (critical path first) → project priority → task priority field → FIFO. (3) Support resource-level calendars (different work days per resource). (4) After leveling shifts any dates, re-run affected CPM subgraph. Algorithm must be deterministic — same input always produces same output."

**Expected Output:**
- `engine/resource_capacity.py`
- `tests/test_resource_leveling.py`

### Session 2.5 — API Endpoints & Transaction Safety
**Feed:**
| Order | Document | Purpose |
|-------|----------|---------|
| 1 | `00_SYSTEM_CONSTITUTION.md` → §4 (Step 7), §7 (all contracts), §11 (error recovery) |
| 2 | `02_Technical_Architecture_Spec.md` → Section 3 |
| 3 | All engine code from Sessions 2.2-2.4 |
| 4 | `PHASE_1_CONTRACT.md` (schema context) |

**Prompt Strategy:**
> "Build the FastAPI routes: POST /calculate, POST /baseline/lock, GET /financials. The /calculate endpoint must: accept the §7.1 contract, run the full §4 pipeline, persist via atomic bulkWrite transaction, return the §7.3 contract. Include idempotency key handling, request debouncing (300ms), and all error recovery behaviors from Constitution §11."

**Expected Output:**
- `api/routes/scheduler.py`
- `api/middleware/idempotency.py`
- `api/middleware/transaction.py`
- `tests/test_api_integration.py`

### Phase 2 Handoff Artifact
Create `PHASE_2_CONTRACT.md` documenting:
- Exact API endpoint signatures with request/response examples
- Engine calculation behavior for edge cases encountered during testing
- Performance benchmarks from test runs
- Updated `shared_models.py`

---

## Phase 3: Frontend Grid & Canvas (Weeks 6-8)

### Session 3.1 — Zustand Store & Type Contracts
**Feed:**
| Order | Document | Purpose |
|-------|----------|---------|
| 1 | `00_SYSTEM_CONSTITUTION.md` | Data contracts (§7.1, §7.4), state machine (§5), rollup rules (§6) |
| 2 | `03_Frontend_Engineering_Spec.md` → Section 3 | State management spec |
| 3 | `PHASE_2_CONTRACT.md` | API contracts from backend phase |

**Prompt Strategy:**
> "Build the Zustand schedule store (`useScheduleStore`). Must contain: (1) TaskMap (normalized dictionary by task_id for O(1) lookups), (2) DependencyGraph structure, (3) optimistic update action that immediately mutates state then fires API call, (4) reconciliation action that ingests engine response and snaps to engine truth, (5) rollback action for API failures. Generate the TypeScript types matching the Constitution §7.4 response shape exactly."

**Expected Output:**
- `stores/useScheduleStore.ts`
- `types/schedule.types.ts` (the frontend Living Types file)
- `stores/actions/optimisticUpdate.ts`
- `stores/actions/reconcile.ts`

### Session 3.2 — Master Grid Component
**Feed:**
| Order | Document | Purpose |
|-------|----------|---------|
| 1 | `00_SYSTEM_CONSTITUTION.md` → §5 (state machine), §6 (rollups), §12 (RBAC) |
| 2 | `03_Frontend_Engineering_Spec.md` → Section 2.1 (left pane) |
| 3 | Code from Session 3.1 (store + types) |

**Prompt Strategy:**
> "Build the `<SchedulerGrid />` component. Requirements: (1) Virtualized rows using @tanstack/react-virtual — must handle 10,000 rows. (2) Collapsible WBS hierarchy with chevron expand/collapse. (3) Inline editing for task_name, task_mode, percent_complete. (4) Memoized row components — changing Task 4 re-renders only Task 4 and its direct parent rollup. (5) Role-based column visibility per Constitution §12."

**Expected Output:**
- `components/scheduler/SchedulerGrid.tsx`
- `components/scheduler/GridRow.tsx` (memoized)
- `components/scheduler/GridHeader.tsx`
- `hooks/useVirtualizedGrid.ts`

### Session 3.3 — Gantt Chart
**Feed:**
| Order | Document | Purpose |
|-------|----------|---------|
| 1 | `00_SYSTEM_CONSTITUTION.md` → §7.1 (change request contract), §4 (pipeline) |
| 2 | `03_Frontend_Engineering_Spec.md` → Section 2.1 (right pane timeline) |
| 3 | Code from Sessions 3.1 + 3.2 (store + grid) |

**Prompt Strategy:**
> "Build the `<GanttChart />` component. Requirements: (1) Dragging bar center changes start/finish, dragging edge changes duration. (2) Dependency SVG lines between tasks. (3) Click-drag from finish dot of Task A to start dot of Task B creates FS link. (4) Baseline overlay toggle (grey bars behind colored bars). (5) Critical path highlight toggle (red bars + red SVG links). (6) All drags fire optimistic update from store, debounced API call at 300ms. (7) Performance: only re-render changed bars and their direct successors."

**Expected Output:**
- `components/scheduler/GanttChart.tsx`
- `components/scheduler/GanttBar.tsx` (memoized)
- `components/scheduler/DependencyLines.tsx`
- `hooks/useGanttDrag.ts`

### Session 3.4 — Kanban Board
**Feed:**
| Order | Document | Purpose |
|-------|----------|---------|
| 1 | `00_SYSTEM_CONSTITUTION.md` → §5 (state machine transitions) |
| 2 | `03_Frontend_Engineering_Spec.md` → Section 2.2 |
| 3 | Code from Session 3.1 (store) |

**Prompt Strategy:**
> "Build the `<KanbanBoard />`. Columns map to task states from Constitution §5. Drag-and-drop via @hello-pangea/dnd. Dropping into 'Done' column sets percent_complete=100 and actual_finish=now. Dropping from 'Done' back to 'In-Progress' triggers reopen transition (resets actual_finish, sets percent_complete to previous value). All moves fire the store's optimistic update. Invalid state transitions (per Constitution §5) show a toast error and snap the card back."

**Expected Output:**
- `components/scheduler/KanbanBoard.tsx`
- `components/scheduler/KanbanCard.tsx`
- `components/scheduler/KanbanColumn.tsx`

### Session 3.5 — Task Drawer
**Feed:**
| Order | Document | Purpose |
|-------|----------|---------|
| 1 | `00_SYSTEM_CONSTITUTION.md` → §7.4 (full response shape) |
| 2 | `03_Frontend_Engineering_Spec.md` → Section 2.3 |
| 3 | Code from Session 3.1 (store + types) |

**Prompt Strategy:**
> "Build the `<TaskDrawer />` sliding panel with 4 tabs: (1) Details & Dependencies — form for adding predecessors with type selector (FS/SS/FF/SF), lag input, hard/soft toggle. (2) MoM AI Chat — text area with submit, AI loading state, action item preview with confirm/reject per item. Stub the AI API call. (3) Financials — read-only display of wo_value, payment_value, cost_variance, weightage from store. (4) Work Logs — list view of timesheets. Drawer pushes canvas left, doesn't overlay."

**Expected Output:**
- `components/scheduler/TaskDrawer.tsx`
- `components/scheduler/tabs/DependencyTab.tsx`
- `components/scheduler/tabs/MoMTab.tsx`
- `components/scheduler/tabs/FinancialsTab.tsx`
- `components/scheduler/tabs/WorkLogsTab.tsx`

### Phase 3 Handoff Artifact
Create `PHASE_3_CONTRACT.md` documenting:
- Component hierarchy and prop contracts
- Store action signatures and their API call mappings
- Any Gantt interaction edge cases discovered and how they were handled
- Updated TypeScript types file

---

## Phase 4: AI Integration & Portfolio (Weeks 9-10)

### Session 4.1 — AI Microservices
**Feed:**
| Order | Document | Purpose |
|-------|----------|---------|
| 1 | `00_SYSTEM_CONSTITUTION.md` → §3 (truth hierarchy — AI is lowest priority) |
| 2 | `02_Technical_Architecture_Spec.md` → Section 5 |
| 3 | `PHASE_2_CONTRACT.md` (API contracts for task creation) |

**Prompt Strategy:**
> "Build the async AI worker services: (1) Import processor — accepts .mpp/Excel file, sends WBS descriptions to LLM, returns suggested category codes and durations. All suggestions marked with confidence score and require human confirmation. (2) MoM parser — accepts meeting notes text, extracts action items as JSON with assignee and deadline fields. Output goes to preview, never auto-commits. (3) Both services degrade gracefully — if LLM is unavailable, import proceeds without suggestions, MoM shows 'AI unavailable'. Store ai_suggested_duration alongside actual duration for feedback loop."

**Expected Output:**
- `services/ai/import_processor.py`
- `services/ai/mom_parser.py`
- `services/ai/llm_client.py` (abstracted LLM interface)
- `tests/test_ai_degradation.py`

### Session 4.2 — Portfolio Dashboard
**Feed:**
| Order | Document | Purpose |
|-------|----------|---------|
| 1 | `00_SYSTEM_CONSTITUTION.md` → §10 (portfolio limits) |
| 2 | `04_PRD.md` → Section 3.3 (Enterprise PPM) |
| 3 | `03_Frontend_Engineering_Spec.md` → Portfolio View reference |
| 4 | `PHASE_3_CONTRACT.md` (component patterns) |

**Prompt Strategy:**
> "Build the Portfolio view: (1) Master dashboard aggregating summary-level data from multiple project_ids. (2) Cross-project Gantt showing top-level milestones only. (3) Resource heatmap showing utilization across all projects in the portfolio. Paginated at 50 projects. Supports external dependency visualization between projects."

**Expected Output:**
- `components/portfolio/PortfolioDashboard.tsx`
- `components/portfolio/CrossProjectGantt.tsx`
- `components/portfolio/ResourceHeatmap.tsx`
- `api/routes/portfolio.py`

### Session 4.3 — Baseline System
**Feed:**
| Order | Document | Purpose |
|-------|----------|---------|
| 1 | `00_SYSTEM_CONSTITUTION.md` → §2.2 (baseline immutability), §9 (earned value) |
| 2 | `01_Backend_Schema_Spec.md` → schedule_baselines schema |
| 3 | `PHASE_2_CONTRACT.md` → /baseline/lock endpoint |

**Prompt Strategy:**
> "Complete the baseline system: (1) Lock endpoint creates immutable snapshot including financial values at lock time (baseline_cost_snapshot, wo_value_snapshot, payment_value_snapshot). (2) Baseline comparison engine — given two baseline numbers, compute schedule_variance_days and cost_variance_percent per task. (3) Gantt overlay reads from baseline snapshots to render grey bars. (4) Enforce hard immutability — no endpoint can modify locked baselines. (5) Maximum 11 baselines per project."

**Expected Output:**
- `services/baseline_service.py`
- `services/baseline_comparison.py`
- `tests/test_baseline_immutability.py`

### Phase 4 Handoff Artifact
Create `PHASE_4_CONTRACT.md` documenting:
- AI service interfaces and degradation behavior
- Portfolio aggregation query patterns
- Baseline snapshot schema (actual, not just planned)

---

## Phase 5: BI Dashboards & Cutover (Weeks 11-12)

### Session 5.1 — Reactive BI Charts
**Feed:**
| Order | Document | Purpose |
|-------|----------|---------|
| 1 | `00_SYSTEM_CONSTITUTION.md` → §9 (earned value formulas — exact formulas to implement) |
| 2 | `03_Frontend_Engineering_Spec.md` → Section 4 |
| 3 | `PHASE_3_CONTRACT.md` + `PHASE_4_CONTRACT.md` (store + baseline context) |

**Prompt Strategy:**
> "Build the BI dashboard components using Recharts, all subscribing to useScheduleStore: (1) S-Curve LineChart with PV and EV series using exact formulas from Constitution §9. (2) Cash Flow Forecaster BarChart — X-axis = future months, Y-axis = sum of wo_value for tasks finishing in that month. (3) SPI/CPI KPI cards. (4) All charts must reactively redraw when the store changes (e.g., Gantt drag shifts a task from December to January → cash flow bar moves instantly)."

**Expected Output:**
- `components/dashboard/SCurveChart.tsx`
- `components/dashboard/CashFlowChart.tsx`
- `components/dashboard/KPICards.tsx`
- `components/dashboard/DashboardView.tsx`

### Session 5.2 — Stress Testing & Performance
**Feed:**
| Order | Document | Purpose |
|-------|----------|---------|
| 1 | `00_SYSTEM_CONSTITUTION.md` → §10 (system limits) |
| 2 | `06_Implementation_Plan.md` → Week 12 details |
| 3 | All API + Engine code from previous phases |

**Prompt Strategy:**
> "Create: (1) Load test script generating a project with 5,000 WBS rows and 7,000 dependencies. (2) Benchmark the /calculate endpoint — must complete in under 5 seconds. (3) Frontend render benchmark — initial load of 5,000 rows must paint in under 2 seconds with virtualization. (4) Concurrent user simulation — 10 simultaneous schedule changes must all resolve without data corruption. (5) Edge case test suite: circular dependency attempts, maximum dependency depth, all constraint types simultaneously."

**Expected Output:**
- `tests/stress/generate_large_project.py`
- `tests/stress/benchmark_engine.py`
- `tests/stress/concurrent_users.py`
- `tests/stress/edge_cases.py`

### Session 5.3 — Migration & Cutover
**Feed:**
| Order | Document | Purpose |
|-------|----------|---------|
| 1 | `00_SYSTEM_CONSTITUTION.md` → §11 (error recovery) |
| 2 | `06_Implementation_Plan.md` → Week 12 migration details |
| 3 | `PHASE_1_CONTRACT.md` (schema context) |

**Prompt Strategy:**
> "Build the migration system: (1) Script to map legacy Payment Schedule data to project_schedules format. (2) Validation report that compares legacy totals vs migrated totals for every project. (3) Rollback script that can revert to legacy format if issues found within 48 hours. (4) Dual-read verification mode — for 1 week post-cutover, both old and new systems serve data, and a diff report catches any discrepancies. (5) Next.js route update to redirect /admin/payment-schedule to /admin/scheduler."

**Expected Output:**
- `migration/legacy_to_scheduler.py`
- `migration/validation_report.py`
- `migration/rollback.py`
- `migration/dual_read_verifier.py`

---

## Cross-Phase Artifacts (Maintained Throughout)

| Artifact | Updated When | Fed Into |
|----------|-------------|----------|
| `shared_models.py` (Python types) | End of every backend phase | Every backend session |
| `schedule.types.ts` (TS types) | End of every frontend phase | Every frontend session |
| `PHASE_N_CONTRACT.md` | End of each phase | All sessions in N+1 and beyond |
| `00_SYSTEM_CONSTITUTION.md` | Only if a system law changes (rare) | Every session always |

---

## Quick Reference: Document → Phase Matrix

| Document | Phase 1 | Phase 2 | Phase 3 | Phase 4 | Phase 5 |
|----------|---------|---------|---------|---------|---------|
| `00_SYSTEM_CONSTITUTION.md` | FULL | FULL | FULL | FULL | FULL |
| `01_Backend_Schema_Spec.md` | FULL | §1.3 only | §1.3 ref | §1.4 only | ref |
| `02_Technical_Architecture_Spec.md` | §3 ref | FULL | §3 ref | §5 only | ref |
| `03_Frontend_Engineering_Spec.md` | — | — | FULL | §portfolio | §4 only |
| `04_PRD.md` | — | — | — | §3.3 only | — |
| `05_Application_Flow.md` | §1 only | §2 only | §3 only | — | §4 only |
| `06_Implementation_Plan.md` | Wk 1-2 | Wk 3-5 | Wk 6-8 | Wk 9-10 | Wk 11-12 |
