# RuFlo V3 Agent Orchestration Framework

This document defines the **System Architecture & Orchestration Guidelines** for the project. RuFlo V3 is a hierarchical-mesh swarm framework that enforces architectural integrity across all logic layers.

---

## 1. Universal Orchestration Protocol

Any agent session or swarm MUST adhere to these global directives:

### A. Context First (ReasoningBank)
Before proposing any code or architectural changes, agents MUST load relevant context from the **ReasoningBank**.
```bash
npx -y ruflo@latest memory search --query "[Module Name/Task Context]"
```

### B. Swarm Topology
- **MANDATORY Swarm Init**: Every major task or phase starts with a literal swarm command.
- **Topology**: Defaults to `hierarchical-mesh`. Use `--topology hierarchical` for lead-driven work or `--strategy adaptive` for exploratory tasks.
- **No Internal Simulation**: Local agent-in-agent simulations are forbidden. Real agents must be spawned via the CLI.

### C. Safety & Audit Hooks
Every task MUST verify its output against the System Constitution before commit.
```bash
npx -y ruflo@latest hooks worker dispatch --trigger audit
```

---

## 2. Generic Task Instruction Template

Use this structure to define a new task or phase for RuFlo.

### [Task: Feature Name]
- **Objective:** [Clear description of the goal]
- **Primary Swarm Command:**
  ```bash
  npx -y ruflo@latest swarm "[Unique Phase Title]" --strategy [specialized|hierarchical|adaptive|balanced]
  ```
- **Assigned Agents:**
  - `system-architect` (Lead/Architecture)
  - `coder` (Implementation)
  - `tester` (QA/Verification)
  - `security-auditor` (Audit/Review)
- **Hard Rules & Invariants:**
  - [Constraint 1: e.g., No direct legacy DB mutations]
  - [Constraint 2: e.g., All state must reside in Zustand store]
  - [Constraint 3: e.g., All API calls must include idempotency keys]
- **Verification Criteria:**
  - [Metric 1: e.g., Recalculation completes in < 5s]
  - [Metric 2: e.g., 100% test coverage on new endpoints]

---

## 3. Strict Audit Triggers

The `security-auditor` and `perf-analyzer` agents automatically reject work if:
1. **Unprotected State**: Frontend UI state operates independently from the source-of-truth store.
2. **Missing Transactions**: Database updates lack atomic blocks in the API.
3. **Property Violations**: Modification of properties explicitly marked as `is_immutable`.
4. **Context Failure**: Work started without a `memory search` command.

---

## 4. Reference Implementation: PPM Scheduler Module

*Example of the orchestration pattern applied to the PPM module.*

### Phase 3: Interactive UI (Ref. Implementation)
- **Objective:** Next.js UI, Kanban, and Gantt with optimistic Zustand updates.
- **Swarm Command:** `npx -y ruflo@latest swarm "Phase 3: Interactive UI" --strategy adaptive`
- **Agents:** `coder`, `reviewer`, `performance-engineer`.
- **Hard Rules:**
  - **Optimistic Updates:** Gantt drags update UI instantly; debounced API call (300ms).
  - **Undo Stack:** Zustand store must implement a 50-action local `undoStack`.
  - **Version Conflict:** HTTP 409 resets local state from server.
- **Performance:** Render 5,000 tasks in **< 2 seconds** with virtualization.

### Phase 4: AI Integration & Enterprise PPM
- **Objective:** AI auto-duration and MoM extraction.
- **Rules:** Every AI suggestion MUST include an `ai_confidence_score`.
- **Human-in-the-loop:** AI must NEVER auto-commit a task; stages as `draft`.

---
## 5. RuFlo CLI Command Reference

Quick reference for orchestrating the swarm:

| Command | Purpose | Example |
| :--- | :--- | :--- |
| `swarm` | Initialize or update a swarm | `npx -y ruflo@latest swarm "Task Title" --strategy balanced` |
| `agent spawn` | Spawn a specific worker role | `npx -y ruflo@latest agent spawn coder` |
| `memory search` | Search the ReasoningBank | `npx -y ruflo@latest memory search --query "Zustand patterns"` |
| `hooks worker dispatch` | Trigger a manual audit/hook | `npx -y ruflo@latest hooks worker dispatch --trigger audit` |
| `status` | Check swarm and agent health | `npx -y ruflo@latest status` |
| `swarm init` | Start a new project objective | `npx -y ruflo@latest swarm init --objective "New Project"` |

---
*End of Framework Guide.*
