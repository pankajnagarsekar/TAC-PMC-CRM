# RuFlo V3 Orchestration Rules: PPM Scheduler Module

This document is the **Comprehensive Agent Master Guide** for implementing the Enterprise PPM Scheduler using Claude, Antigravity, and RuFlo V3. It strictly enforces the architecture across all 6 documentation pillars (Schema, Tech Arch, Frontend, PRD, Flow, Implementation).

---

## 1. Global Swarm & Memory Directives

Any agent session working on this project MUST adhere to these global directives (NON-NEGOTIABLE):

1. **Topology:** `hierarchical-mesh` minimum 5 agents. Literal execution of the `npx ruflo swarm` command is MANDATORY for every phase. Internal simulation of roles is STRICTLY FORBIDDEN.
2. **Context Loading:** Before *any* code is written or proposed, agents must execute a semantic search on the RuFlo ReasoningBank. Failure to run this command will result in immediate architectural rejection:
   ```bash
   npx -y ruflo@latest memory search --query "PPM Scheduler [specific module context]"
   ```
3. **Cross-View Consistency Check:** Frontend agents must NEVER implement independent state. All views must read from the single Zustand `useScheduleStore`.
4. **No Legacy DB Mutations:** Backend agents must NEVER attempt to write to `work_orders` or `payment_certificates`. The `security-auditor` agent MUST be triggered via CLI to block any PR that violates this.
5. **Idempotency & Versioning:** Every database write must increment `version` and check `idempotency_key`.

---

## 2. Phase-by-Phase Agent Orchestration

### Phase 1: Foundation & Database Isolation
**Goal:** Schema creation, Idempotency, and Financial `$lookup` Read-Only Pipelines.
- **Swarm Command:** `npx -y ruflo@latest swarm "Phase 1: DB Foundation" --strategy specialized`
- **Agents:** `system-architect` (Lead), `backend-dev` (Worker), `security-auditor` (Reviewer).
- **Hard Rules:**
  - `external_ref_id` MUST be implemented as immutable.
  - `schedule_baselines` MUST have database-level middleware rejecting updates if `is_immutable == true`.
  - Financial aggregations (PV, EV, AC) must be done in-memory via `export_service.py` to prevent DB bloat.

### Phase 2: The Core Execution Engine (CPM)
**Goal:** Mathematical determinism and Python engine implementation.
- **Swarm Command:** `npx -y ruflo@latest swarm "Phase 2: CPM Engine" --topology hierarchical`
- **Agents:** `system-architect` (Lead), `perf-analyzer` (Validator), `tester` (QA).
- **Hard Rules:**
  - The CPM engine `calculate_critical_path.py` MUST NOT have DB access. It takes JSON in and returns JSON out.
  - A pre-calculation DAG (Directed Acyclic Graph) validation must run to reject circular dependencies.
  - All output dates must respect `constraint_type` (e.g., SNET, MFO).
  - Validation: API recalculation must complete in **< 5 seconds** for 5,000 rows. Tested by `perf-analyzer`.

### Phase 3: The Frontend Grid & Canvas
**Goal:** Next.js UI, Kanban, and Gantt with optimistic Zustand updates.
- **Swarm Command:** `npx -y ruflo@latest swarm "Phase 3: Interactive UI" --strategy adaptive`
- **Agents:** `coder` (Lead for UI), `reviewer` (UX Audit), `performance-engineer` (FPS Audit).
- **Hard Rules:**
  - **Optimistic Updates:** Gantt bar drags must instantly update the UI and send a debounced API call (300ms).
  - **Undo Stack:** Zustand store must implement a 50-action local `undoStack`.
  - **Version Conflict:** HTTP 409 responses must overwrite local state from the server. No merge resolution.
  - Performance constraint: The Grid and Gantt must render 5,000 tasks in **< 2 seconds**. Virtualization is mandatory.

### Phase 4: AI Integration & Enterprise PPM
**Goal:** AI auto-duration, MoM extraction, and cross-project portfolio integration.
- **Swarm Command:** `npx -y ruflo@latest swarm "Phase 4: AI & PPM" --strategy specialized`
- **Agents:** `ml-developer` (Lead), `researcher` (Data patterns), `coder` (API integration).
- **Hard Rules:**
  - Every AI suggestion MUST include an `ai_confidence_score` (0.0 - 1.0).
  - Human-in-the-loop: AI must NEVER auto-commit a task. It stages tasks in `draft` status for admin approval.
  - Graceful Degradation: If the AI API times out (> 5s), the UI must seamlessly default to manual entry without breaking the page.

### Phase 5: Native BI & Cutover
**Goal:** Recharts S-Curves, KPI cards, and caching strategies.
- **Swarm Command:** `npx -y ruflo@latest swarm "Phase 5: BI Analytics" --strategy balanced`
- **Agents:** `coder`, `perf-analyzer`.
- **Hard Rules:**
  - Dashboards must rely directly on the `useScheduleStore` to instantly re-render (target: **< 100ms**) when dates shift.
  - Financial data failures must show localized "data unavailable" errors, leaving the timeline fully functional.

---

## 3. Strict Development Enforcements & Audit Triggers

Agents reviewing code on this project must automatically reject Pull Requests if they contain:
1. Direct `$set` or update queries to `payment_certificates` or `work_orders`.
2. A `POST /calculate` endpoint without MongoDB `bulkWrite` transaction blocks.
3. Lack of an `is_immutable` property check before rewriting baselines.
4. A frontend UI state that operates independently from the main `useScheduleStore`.
5. Missing UI debouncing for dragged tasks in the Gantt.

*To activate these enforcements, run the RuFlo auditor before committing any code:*
```bash
npx -y ruflo@latest hooks worker dispatch --trigger audit
```
