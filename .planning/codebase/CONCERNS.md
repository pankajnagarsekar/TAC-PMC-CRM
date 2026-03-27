# Codebase Concerns

## Resilience & Stability
- **Database Conflicts**: `IndexOptionsConflict` was a recent issue, resolved by ensuring consistent indexing across migrations.
- **Monorepo Resolution**: Occasional module resolution issues between packages (requires `pnpm clean` and `pnpm install`).
- **CORS**: Strict configuration required in `lifecycle.py` to support Web and Mobile concurrently.

## Security
- **Secret Hygiene**: Hard guard implemented in `config.py` to prevent startup if default `JWT_SECRET_KEY` is found in non-development environments.
- **Financial Integrity**: High-risk operations (fund transfer, DPR approval) require strict audit logging and UOW atomicity.

## Technical Debt
- **Frontend Tests**: Lack of a centralized Jest/Vitest suite for web and mobile.
- **Legacy Route Bloat**: `project_management_routes.py` was being decommissioned in favor of DDD-aligned `api/v1/` routes.
- **Documentation**: Constant need to sync `CLAUDE.md` with the rapidly evolving DDD service layer.

## Infrastructure
- **Redis Availability**: Critical dependency for rate limiting; application must fail-gracefully if Redis is unavailable.
