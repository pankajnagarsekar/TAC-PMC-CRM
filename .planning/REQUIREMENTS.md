# Requirements: DDD Restructuring

## Functional
- Maintain endpoint parity for all `/api/v1` routes.
- Ensure all business logic remains functionally identical.
- Implement domain event patterns for inter-module communication.

## Non-Functional
- **Domain Invariants**: Move logic from services to Aggregate Roots.
- **Context Isolation**: Modules must not have circular dependencies.
- **Standardized Error Handling**: Translate domain exceptions to HTTP status codes centrally.
- **Backward Compatibility**: No changes to existing frontend/mobile API calls.

## Acceptance Criteria
- [x] All 5 Bounded Contexts implemented in `app/modules/`.
- [x] Central `router.py` correctly routes to modular API handlers.
- [x] No monolithic `app/services/` or `app/repositories/` remain. (Deleted: services, repositories, schemas, api/v1, domain)
- [x] Full test suite passes without logic changes.
