# Phase 9: Strategic Hardening & Consolidation

## Objective
Remediate gaps identified in the `abstract-percolating-sutherland.md` verification report to achieve "Strict DDD" status.

## Skills Used
- `@gsd-plan-phase`
- `@domain-driven-design`
- `@ddd-tactical-patterns`
- `@backend-architect`
- `@financial-integrity-patterns`
- `@python-pro`

## Context
The verification report revealed that while the modular structure exists, significant architectural leakage and logic duplication persist. Specifically:
1. `HTTPException` is used in the `application/` layer instead of translating at the `api/` edge.
2. `FinancialEngine` is duplicated and fragmented.
3. `WorkOrderService` remains "fat" with duplicated pricing logic and cross-context dependencies.
4. `reporting` and `scheduler` contexts are under-implemented.

## Tasks & Acceptance Criteria

### Task 1: Consolidate Financial Engines (Priority 1)
- **Goal:** Move all financial calculations to a single canonical `FinancialEngine` in `shared/domain/`.
- [ ] Merge `financial/domain/financial_engine.py` into `shared/domain/financial_engine.py`.
- [ ] Delete `financial/domain/financial_engine.py`.
- [ ] Identify and remove `app/core/financial_utils.py` once logic is moved to `shared/domain/`.
- **Verification:** All financial logic (WO, PC, Rounding) is imported solely from `shared.domain.financial_engine`.

### Task 2: Remove HTTPException from Application Layer (Priority 1)
- **Goal:** Decouple the application layer from HTTP concerns.
- [ ] Replace `HTTPException` in all services with appropriate `DomainException` or custom `ApplicationError`.
- [ ] Implement/Update exception handlers at the `api/` route level to catch domain exceptions and transform them to HTTP status codes.
- **Verification:** `grep -r "HTTPException" app/modules/*/application` returns 0 results.

### Task 3: Refactor WorkOrderService (Priority 1)
- **Goal:** Thin the service and remove cross-context dependency.
- [ ] Move pricing loops and calculations (lines 57-66, 127-138) into `shared/domain/financial_engine.py`.
- [ ] Remove `financial_service.round_half_up` cross-context dependency, use `FinancialEngine.round` instead.
- [ ] Use `SequenceRepository` for work order number generation instead of inline logic.
- **Verification:** `WorkOrderService` contains strictly coordination logic.

### Task 4: Fix Under-implemented Contexts (Priority 2)
- [ ] Create `reporting/domain/models.py` with initial models/exceptions.
- [ ] Structure `scheduler/` into `api/`, `application/`, `domain/`, `infrastructure/`.
- **Verification:** Folders are present and consistent with the 5-layer architecture.

### Task 5: Hardening Domain Guards (Priority 2/3)
- [ ] In `FinancialState`, convert detection properties (`is_over_committed`, `is_threshold_breached`) into validation methods that raise `FinancialIntegrityError`.
- [ ] Ensure `WorkOrderAggregate` is instantiated and used in the `create_work_order` path in `WorkOrderService`.

## Verification Protocol
- Standard `@testing-patterns` checklist after each task.
- Automated audit of imports using script/grep.
- Unit tests for the consolidated `FinancialEngine`.

## Risk Mitigation
- **Logic Regressions:** Financial logic is sensitive. We will use `pytest` with a data-driven test suite for the consolidated `FinancialEngine` before swapping.
- **Breaking API:** Changes to exception handling must not change Error Model for clients.
