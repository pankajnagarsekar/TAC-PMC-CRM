# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Monorepo Structure

TAC-PMC-CRM is a full-stack CRM built with a **pnpm monorepo** using **Turbo** for task orchestration. The three main applications are:

| App | Path | Tech Stack | Purpose |
|-----|------|-----------|---------|
| **Web (Desktop)** | `apps/web/` | Next.js 16 + React 19 + Tailwind CSS | Main SPA for desktop/browser |
| **Mobile** | `apps/mobile/` | React Native + Expo | Native mobile app (iOS/Android) |
| **API** | `apps/api/` | FastAPI (Python) | REST API backend with DDD architecture |

**Shared Packages:**
- `packages/types/` — Shared TypeScript type definitions
- `packages/ui/` — Shared UI component library

---

## Quick Start Commands

All commands run from the **root directory**:

### Development (All Apps)
```bash
pnpm install           # Install dependencies
pnpm dev               # Start all apps (web + mobile + API)
```

### Individual App Development
```bash
pnpm -C apps/web dev              # Start Next.js frontend only (port 3000)
pnpm -C apps/mobile start         # Start Expo mobile (web mode, port 3001)
pnpm -C apps/api exec python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Build & Lint
```bash
pnpm build             # Build all apps (Turbo-orchestrated)
pnpm lint              # Lint all apps (TypeScript, Python)
pnpm format            # Format all code (Prettier)
```

### Tests
```bash
# Coming soon — add test configuration to each app's package.json
```

---

## Backend Architecture (apps/api)

The **FastAPI backend** follows **Domain-Driven Design (DDD)** organized by bounded contexts:

```
apps/api/
├── app/
│   ├── main.py                 # FastAPI app setup, middleware, router registration
│   ├── core/
│   │   ├── config.py           # Settings & environment variables
│   │   ├── dependencies.py     # FastAPI dependency injection
│   │   ├── utils.py            # Shared utilities
│   │   ├── storage.py          # File/S3 storage logic
│   │   └── ...service.py       # Cross-cutting services (AI, PDF, etc.)
│   │
│   ├── api/v1/                 # API routes (thin controllers)
│   │   ├── user_routes.py      # User endpoints
│   │   ├── project_routes.py   # Project endpoints
│   │   ├── auth_routes.py      # Authentication endpoints
│   │   └── ...                 # Other domain routes
│   │
│   ├── services/               # Business logic (DDD service layer)
│   │   ├── user_service.py     # User business logic
│   │   ├── auth_service.py     # Auth logic (JWT, password hashing)
│   │   ├── project_service.py  # Project logic
│   │   └── ...                 # Other domain services
│   │
│   ├── repositories/           # Data access layer
│   │   ├── base_repo.py        # Base repository (shared CRUD)
│   │   ├── user_repo.py        # User queries/mutations
│   │   ├── project_repo.py     # Project queries/mutations
│   │   └── ...                 # Other domain repositories
│   │
│   ├── schemas/                # Pydantic validation/serialization
│   │   ├── user.py             # User DTOs
│   │   ├── project.py          # Project DTOs
│   │   └── ...                 # Other domain schemas
│   │
│   └── db/
│       └── mongodb.py          # MongoDB connection manager
│
├── execution/                  # Enterprise scheduler (separate subsystem)
│   └── scheduler/
│
└── pyproject.toml              # Python dependencies
```

### Key Architectural Principles

1. **Dependency Injection**: All services and repositories are injected via `FastAPI.Depends()` in route handlers. Never instantiate directly.
2. **Service Layer**: Services own transaction boundaries and business logic. Routes are thin.
3. **Repository Pattern**: All DB access goes through repositories. Queries in repositories, business logic in services.
4. **Async/Await**: 100% async—no blocking I/O.
5. **Standard Responses**:
   - Error: `{ "success": false, "message": "...", "error_code": "..." }`
   - Success: `{ "success": true, "data": {...}, "message": "..." }`

---

## Frontend Architecture (apps/web)

**Next.js 16 + React 19 + Tailwind CSS**

```
apps/web/
├── pages/              # Next.js page routes
├── components/         # Reusable React components
├── lib/                # Utilities, API client, hooks
├── styles/             # Global styles, Tailwind config
└── public/             # Static assets
```

### Key Details
- **Styling**: Tailwind CSS + custom design tokens (Luxury Industrial aesthetic)
- **UI Components**: From `packages/ui/` for consistency
- **API Client**: Axios or native `fetch` (TBD)
- **State Management**: Zustand for app state (see `zustand` in package.json)

---

## Mobile Architecture (apps/mobile)

**React Native + Expo + Expo Router**

```
apps/mobile/
├── app/                # Expo Router file-based routing
├── components/         # React Native components
├── hooks/              # Custom hooks
├── lib/                # Utilities, API client
└── scripts/            # Setup scripts
```

### Targets
- **Web**: `pnpm -C apps/mobile start --web` (port 3001)
- **iOS/Android**: `pnpm -C apps/mobile ios` / `pnpm -C apps/mobile android`

---

## Shared Packages

### `packages/types/`
- Centralized TypeScript types used by web and mobile
- Single source of truth for type definitions
- Auto-imported via `@tac-pmc/types` in `tsconfig.json`

### `packages/ui/`
- Shared component library (React components, Tailwind utilities)
- Used by both web and mobile
- Import as `@tac-pmc/ui`

---

## Database: MongoDB

- **Connection**: via `app/db/mongodb.py`
- **URL**: `MONGO_URL` environment variable (default: `mongodb://localhost:27017`)
- **Database Name**: `tac_pmc_crm` (configurable)
- **Collections**: One per domain (users, projects, clients, etc.)
- **Financial Integrity**: All monetary fields use fixed-point arithmetic (no floats); audit trail required for mutations

---

## Environment Configuration

Create `.env` files in each app as needed:

```bash
# apps/api/.env
MONGO_URL=mongodb://localhost:27017
DB_NAME=tac_pmc_crm
JWT_SECRET_KEY=your-super-secret-key-change-in-prod
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# apps/web/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000

# apps/mobile/.env
API_URL=http://localhost:8000
```

**Never commit `.env` files with secrets.** Use `.env.example` for documentation.

---

## Git Workflow & Commits

### Commit Message Format
```
[type]: Brief description

Detailed explanation of changes.

Apps Changed: [web|mobile|api|packages|multiple]
Skills Used: @skill1, @skill2
```

**Types**: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`

### Common Scenarios

**Frontend Feature**:
```bash
git commit -m "feat: add user settings page

- Created new page component with form validation
- Integrated with user service API
- Added responsive Tailwind styling

Apps Changed: web
```

**Backend Bug Fix**:
```bash
git commit -m "fix: prevent duplicate project creation

- Added uniqueness check in project_service
- Added database index on project_slug
- Added test case for race condition

Apps Changed: api
```

---

## Turbo Task Orchestration

The monorepo uses **Turbo** to run tasks across all apps:

- `pnpm dev` — runs `dev` script in each app (web, mobile, API)
- `pnpm build` — runs `build` script (respects dependency graph)
- `pnpm lint` — runs `lint` script across all apps

**Config**: See `turbo.json` for task definitions (inputs, outputs, caching rules).

---

## Testing Strategy

- **Web**: Jest + React Testing Library (TBD)
- **Mobile**: Jest + React Native Testing Library (TBD)
- **API**: pytest (Python) — create tests alongside services/repos

### Test Location Convention
- Services: `tests/services/test_<domain>_service.py`
- Repositories: `tests/repositories/test_<domain>_repo.py`
- Routes: `tests/routes/test_<domain>_routes.py`

---

## Common Development Tasks

### Adding a New API Endpoint

1. **Schema** — Define request/response in `apps/api/app/schemas/<domain>.py`
2. **Repository** — Add query/mutation in `apps/api/app/repositories/<domain>_repo.py`
3. **Service** — Add business logic in `apps/api/app/services/<domain>_service.py`
4. **Route** — Add endpoint in `apps/api/app/api/v1/<domain>_routes.py`
5. **Test** — Add pytest in `apps/api/tests/routes/test_<domain>_routes.py`

### Adding a New Type to Frontend
1. Add TypeScript interface to `packages/types/src/index.ts`
2. Update `packages/ui/` if new component needed
3. Use `import type { MyType } from '@tac-pmc/types'` in web/mobile

### Running Single Test
```bash
# Backend (Python)
pnpm -C apps/api exec pytest tests/routes/test_user_routes.py::test_create_user -v

# Frontend (Jest)
pnpm -C apps/web test UserForm --watch
```

---

## Debugging

### Backend (Python/FastAPI)
```bash
# Run with logging enabled
LOGLEVEL=DEBUG pnpm -C apps/api exec python -m uvicorn app.main:app --reload

# Access API docs
http://localhost:8000/docs
```

### Frontend (Next.js)
- Open DevTools (F12) for React + JavaScript debugging
- Use `next/image` for optimized images
- Check `_app.tsx` for global context/theme setup

### Mobile (Expo)
```bash
pnpm -C apps/mobile start
# Press 'i' for iOS simulator, 'a' for Android emulator
```

---

## Performance Considerations

1. **API**: Use MongoDB aggregation pipelines for complex queries (avoid N+1)
2. **Frontend**: Lazy-load routes with `next/dynamic`, memoize expensive components
3. **Mobile**: Use Expo's `expo-image` for optimized images, avoid re-renders with hooks
4. **Caching**: Use SWR (web) for API caching; React Query patterns if needed

---

## Known Limitations & TODOs

- [ ] Tests not yet configured (setup jest/pytest)
- [ ] API pagination not yet implemented (add limit/offset)
- [ ] Mobile push notifications (Firebase setup needed)
- [ ] Database migrations (Alembic or manual scripts)
- [ ] Secrets management (move JWT secret to vault)

---

## Links & Resources

- **Turbo Docs**: https://turbo.build
- **pnpm Workspaces**: https://pnpm.io/workspaces
- **FastAPI**: https://fastapi.tiangolo.com
- **Next.js**: https://nextjs.org
- **Expo**: https://expo.io
- **MongoDB**: https://docs.mongodb.com

---

## For Future Claude Instances

When working in this repo:

1. **Identify the app** first — is this web, mobile, or API?
2. **Follow DDD in backend** — service → repository pattern, never query in routes
3. **Use shared packages** — `@tac-pmc/types` and `@tac-pmc/ui` for consistency
4. **Test before commit** — run `pnpm build && pnpm lint` at root
5. **Document non-obvious changes** — architectural decisions in commit messages

---

**Document Owner**: TAC-PMC-CRM Development Team
**Last Updated**: 2026-03-26
