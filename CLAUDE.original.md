# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Project Overview

**TAC-PMC-CRM** is a full-stack Customer Relationship Management system with a Luxury Industrial design language. The project uses a monorepo structure with clear separation between API, web, and mobile applications.

- **Tech Stack**: Python (FastAPI) API | React 19 (Next.js 16) Web | React Native (Expo) Mobile | MongoDB
- **Package Manager**: pnpm (workspace)
- **Build System**: Turbo (monorepo orchestration)
- **Orchestration Framework**: RuFlo V3 (hierarchical-mesh swarm coordination)

---

## Architecture Overview

### Monorepo Structure

```
TAC-PMC-CRM/
├── apps/
│   ├── api/           # Python FastAPI backend (Domain-Driven Design)
│   ├── web/           # Next.js 16 frontend (React 19, Zustand, Tailwind)
│   └── mobile/        # React Native (Expo) mobile application
├── packages/
│   ├── types/         # Shared TypeScript types
│   └── ui/            # Shared UI component library
├── scripts/           # Utility scripts
├── tools/             # Tools and CLI utilities
├── graphify-out/      # Knowledge graph data for code flow analysis
└── pnpm-workspace.yaml # Workspace configuration
```

### Context & Knowledge Files (Root)

Strategic documentation for project synchronization:
- **AwesomeGSD_Skills.md**: Mandatory skill stacking and verification protocols
- **SUPERPOWERS_GUIDE.md**: Framework for achieving perfect, error-free code
- **GSDGodScript.md**: Core directives for implementation workflows
- **Ruflo.md**: RuFlo V3 hierarchical swarm coordination reference

### API Architecture (Strict DDD)

The API strictly follows Domain-Driven Design with sovereign Bounded Contexts:

```
apps/api/app/
├── api/               # Central Router registry (router.py)
├── core/              # Shared kernel & dependency injection
├── db/                # Database manager (MongoDB initialization)
└── modules/           # Sovereign Bounded Contexts
    ├── identity/      # Auth, Users, Roles, Settings
    ├── project/       # Projects, Clients, Timelines
    ├── financial/     # Payments, Budgets, Cash Flow, Master Data
    ├── contracting/   # Work Orders, Vendors
    ├── site_operations/ # DPRs, Attendance, Worker Logs, Site Overheads, Voice Logs
    ├── reporting/     # AI Summaries, Analytics, Dashboard
    ├── scheduler/     # PPM/Gantt scheduling (standalone module)
    ├── tasks/         # Task Management, Kanban Board, Change Logs
    └── shared/        # Shared Kernel (Audit, Alerts, Notifications, BaseRepo)
```

**Module Anatomy:**
- `api/`: Route handlers and dependencies
- `application/`: Application services (Use cases)
- `domain/`: Business logic, aggregators, and exceptions
- `infrastructure/`: Repositories and external adapters
- `schemas/`: Pydantic models (DTOs)

**Key Patterns:**
- **BaseRepository**: Hardened CRUD with optimistic locking and checksum integrity
- **Async/Await**: Motor (async MongoDB driver) throughout
- **Event Sourcing**: State changes tracked for audit trails
- **Rate Limiting & Resilience**: slowapi, circuit breakers, retry patterns
- **Idempotency**: Duplicate-safe financial operations via `core/idempotency.py`
- **Unit of Work**: Transactional consistency via `core/uow.py`

**Core Services** (`apps/api/app/core/`):
- `lifecycle.py`: App startup/shutdown, BackgroundGuardian
- `middleware.py`: BackpressureMiddleware, StandardResponseMiddleware
- `pdf_service.py`: PDF generation (WeasyPrint — requires system libs)
- `ai_summary_service.py`: LLM integration (OpenAI)
- `storage.py`: S3 file storage (boto3)
- `resilience.py`: Circuit breakers, retry patterns
- `concurrency.py`: Optimistic locking, version control
- `financial_utils.py`: Monetary calculations (Decimal precision)

### Frontend Architecture (Next.js + React 19)

```
apps/web/src/
├── app/               # Next.js App Router (routes, layouts, pages)
├── components/        # React components (organized by feature)
├── hooks/             # Custom React hooks
├── lib/               # Utilities and helpers
├── store/             # Zustand state management
└── types/             # TypeScript types
```

**Key Patterns:**
- **State Management**: Zustand for global state
- **Styling**: Tailwind CSS 4 with Luxury Industrial design tokens
- **Data Fetching**: SWR for client-side, Server Components where possible
- **UI Library**: Radix UI primitives + custom components

### Mobile Architecture (React Native + Expo)

```
apps/mobile/
├── app/               # Expo Router (role-based navigation)
│   ├── (admin)/       # dashboard, projects, petty-cash, attendance-view,
│   │                  # worker-log, workers-report, ocr, notifications, dpr/, settings/
│   ├── (client)/      # dashboard, reports
│   ├── (supervisor)/  # dashboard, attendance, dpr, worker-log, voice-log, profile
│   └── login.tsx      # Auth entry point
├── components/        # Reusable components
├── contexts/          # React Context providers
├── services/          # API client & business logic
└── types/             # TypeScript type definitions
```

---

## Common Commands

### Monorepo-Level (Root)

```bash
# Start all services (API + Web + Mobile)
pnpm start-all

# Development mode for all apps
pnpm dev

# Build all apps
pnpm build

# Lint all apps (Zero Error State)
pnpm lint

# Format code (Prettier)
pnpm format

# Verify Backend Logic
pnpm -C apps/api exec python -m pytest
```

### API (Python FastAPI)

```bash
cd apps/api

# Start development server
npm run dev
# or directly: python -m uvicorn app.main:app --reload

# Run tests
npm test
# or: pytest

# Lint code
npm run lint
# or: flake8 .

# Format code
black .
isort .

# Run a single test
pytest tests/test_specific.py::test_function
```

### Web (Next.js)

```bash
cd apps/web

# Start development server
npm run dev

# Build for production
npm run build

# Run production build
npm start

# Lint code
npm run lint

# Type check
npx tsc --noEmit
```

### Mobile (React Native/Expo)

```bash
cd apps/mobile

# Start web dev server
npm run dev

# Start iOS development
npm run ios

# Start Android development
npm run android

# Lint
npm run lint
```

---

## Important Project Directives

### 1. **Skill-First Rule** (AwesomeGSD_Skills.md)

**Every task MUST identify and document relevant skills before beginning work.** Stack skills strategically based on task type:

- **New API Module (DDD)**: @api-design-principles + @fastapi-pro + @ddd-tactical-patterns + @database-design
- **New Web Feature**: @software-architecture + @react-best-practices + @tailwind-design-system + @typescript-pro
- **New Mobile Screen**: @mobile-developer + @react-native-architecture + @typescript-pro
- **Error Detection**: @error-detective + @debugging-toolkit + @software-architecture
- **Database Changes**: @database-design + @data-integrity-patterns + @mongodb (or @sql-pro)
- **UI/UX Changes**: @antigravity-design-expert + @tailwind-design-system + @react-best-practices
- **State Machine/Workflow**: @ddd-tactical-patterns + @state-machine-design
- **Integration Work**: @system-architect + @api-design-principles + @integration-patterns

### 2. **Superpowers & Perfect Code** (SUPERPOWERS_GUIDE.md)

**Every agent MUST follow the Superpowers framework to ensure perfect, error-free implementation.** This involves:
1. **Brainstorming**: Refine design through Socratic dialogue before coding.
2. **Planning**: Use `@writing-plans` to create atomic, test-first execution plans.
3. **Multi-Agent Implementation**: Use `gstack` to coordinate multiple agents for planning and implementation.
4. **Testing**: Enforce TDD (RED-GREEN-REFACTOR) for all logic changes.
5. **Verification**: Run exhaustive checks before claiming completion.

### 3. **RuFlo V3 Framework** (Ruflo.md)

For complex tasks or new phases:

```bash
# Search context from ReasoningBank before starting
npx -y ruflo@latest memory search --query "[Task Context]"

# Initialize swarm for major work
npx -y ruflo@latest swarm "[Phase Title]" --strategy [specialized|hierarchical|adaptive]

# Verify against System Constitution
npx -y ruflo@latest hooks worker dispatch --trigger audit
```

**Core Rules:**
- Every major task starts with a literal swarm command
- Context-first: Load ReasoningBank before proposing changes
- Safety hooks: Audit all work against System Constitution before commit
- No local agent simulation: Real agents must be spawned via CLI

### 3. **Behavioral Rules**

- **Read Before Edit**: Always read a file before modifying it
- **No Unnecessary Files**: Only create files absolutely necessary for the task
- **Prefer Editing**: Edit existing files rather than creating new ones
- **No Secrets in Code**: Never hardcode API keys, credentials, or sensitive data
- **One Message = All Concurrent Operations**: Batch all related file reads/writes, bash commands, and agent spawns in a single message
- **Run Tests After Changes**: Always verify tests pass before committing
- **Platform Neutrality (CRITICAL)**: Never use backslashes (`\`) or `.exe` in scripts; always use `/` and `python -m` for cross-platform CI safety
- **Zero Error Policy**: No merges allowed if `pnpm lint` or `pytest` returns any ERRORS (Warnings allowed but monitored)

### 4. **File Organization**

- **Source Code**: Use `/app` for API, `/src` for web/mobile
- **Tests**: Use `/tests` for API, `__tests__` for JS/TS
- **Configuration**: Keep config files at app root or in `/config`
- **Scripts**: Use `/scripts` for utility scripts
- **Never Save to Root**: Keep working files in appropriate directories

---

## Database & Data Integrity

### MongoDB + Motor (Async Driver)

- **Connection**: Configured in `apps/api/app/core/` via `.env`
- **Repository Pattern**: Use `BaseRepository` for all CRUD operations
- **Optimistic Locking**: Built into BaseRepository with version fields
- **Checksum Integrity**: Document checksums validated on update

### Schema Design

- Database schema defined in `apps/api/app/domain/` (entity definitions)
- Pydantic schemas in `apps/api/app/schemas/` for API contracts
- Migrations: Use scripts in `apps/api/scripts/` (if needed)

---

## API Development

### Routes & Endpoints

Routes are organized within each Bounded Context in `apps/api/app/modules/[module]/api/`:
- `identity/api/routes.py`: Auth and User management
- `project/api/routes.py`: Projects and Timelines
- `financial/api/routes.py`: Payments and Master Data
- `contracting/api/routes.py`: Work Orders and Vendors
- `site_operations/api/routes.py`: DPRs, Attendance, Worker Logs
- `reporting/api/routes.py`: AI Summaries, Analytics

**Aggregation**: The central `apps/api/app/api/router.py` imports and registers these modular routers.

### Services Layer

Business logic resides in the `application/` layer of each module:
- `identity/application/auth_service.py`: Authentication logic
- `financial/application/financial_service.py`: Core financial orchestration
- `financial/application/master_data_service.py`: Reference data management (financial codes)
- `financial/application/cash_service.py`: Cash position tracking and reconciliation
- `financial/application/payment_service.py`: Payment processing
- `project/application/scheduler_service.py`: Critical path and scheduling
- `site_operations/application/site_service.py`: DPR, attendance, site logs
- `reporting/application/ai_summary_service.py`: LLM-powered summaries
- `reporting/application/ai_service.py`: AI/LLM provider integration
- `shared/application/alert_service.py`: Cross-context system alerts

### Validation & Error Handling

- **Input Validation**: Pydantic schemas at endpoint level
- **Error Responses**: Standardized error format from core/
- **Rate Limiting**: slowapi configured in lifecycle
- **Resilience**: Retry patterns, circuit breakers in core

### Creating a New API Module (DDD Pattern)

Every module follows this structure:

```
modules/{MODULE_NAME}/
├── __init__.py
├── api/
│   ├── __init__.py
│   └── routes.py              # FastAPI router(s), all HTTP endpoints
├── application/
│   ├── __init__.py
│   └── {entity}_service.py    # Business logic orchestration (use cases)
├── domain/
│   ├── __init__.py
│   ├── models.py              # Aggregate roots, invariants, value objects
│   ├── exceptions.py           # Domain-specific exceptions
│   └── types.py                # Enums, custom types
├── infrastructure/
│   ├── __init__.py
│   └── repository.py           # Data access (extends BaseRepository[T])
└── schemas/
    ├── __init__.py
    └── dto.py                  # Pydantic request/response models
```

**Key Principles:**
1. **Domain Model Owns Invariants**: Business rules enforced in `domain/models.py`, not in the service
2. **Service Orchestrates**: Application service calls domain, repository, and shared services (audit, notification, permission)
3. **Repository is Generic**: Extend `BaseRepository[T]` from `shared/infrastructure/base_repository.py` — handles CRUD, indexes, org-scoping via `**filters`
4. **No Cross-Module Imports**: Modules are sovereign; communicate only via API (REST)
5. **State Transitions via StateMachine**: All status changes validated by `StateMachine.validate_transition(entity_type, current, next)`

**Registration:**
- Add router to `apps/api/app/api/router.py`: `v1_router.include_router(module_router)`
- Add service factory to `apps/api/app/core/dependencies.py` as a FastAPI `Depends()` function

### State Machine & Transitions

All entities with lifecycle states (PROJECT, PAYMENT, DPR, TASK) use the centralized `StateMachine` class:

```python
# apps/api/app/modules/shared/domain/state_machine.py
StateMachine.validate_transition("TASK", "Open", "In Progress")  # Returns True or raises IllegalTransitionError
StateMachine.check_modification_allowed("TASK", "Closed")  # Raises DataFreezeError if state is final (no outgoing transitions)
```

**Important States & Freezing:**
- Entities with empty transition sets (e.g., `"Closed": set()`) are **frozen** — cannot be modified or transitioned further
- Financial entities in final states (Paid, Cancelled) enforce immutability via DataFreezeError on any update attempt
- Always call `StateMachine.check_modification_allowed()` before allowing field edits

### Repository & BaseRepository Pattern

`BaseRepository[T]` provides generic CRUD with org-scoping security:

```python
class TaskRepository(BaseRepository[Task]):
    collection_name = "tasks"

    async def list_by_project(self, project_id: str, filters: TaskListFilter):
        # BaseRepository automatically adds organisation_id scoping via **filters
        query = {"project_id": project_id, "organisation_id": self.org_id}
        return await self.find(query, limit=50, skip=0)
```

**Key Methods:**
- `get_by_id(id, **filters)` — Single document (with org-scoping filters)
- `find(query, limit, skip)` — Multiple documents (cursor-based pagination)
- `create(data)` — Insert (auto-timestamps: created_at, updated_at, version=1)
- `update(id, data, **filters)` — Update (increments version, returns new doc)
- `aggregate(pipeline)` — MongoDB aggregation for complex queries

**Security:** The `**filters` parameter enforces org-scoping. All queries include `organisation_id` automatically.

### Audit Trail & Change Logs

Every state change is immutably logged via `AuditService`:

```python
await audit_service.log_action(
    organisation_id=user["organisation_id"],
    module_name="TASK_MANAGEMENT",
    entity_type="TASK",
    entity_id=task_id,
    action_type="CREATE",  # CREATE, UPDATE, DELETE, APPROVE, TRANSITION, etc.
    user_id=user["user_id"],
    project_id=project_id,
    old_value_json=old_task_dict,  # Before values (for UPDATE)
    new_value_json=new_task_dict,  # After values (all actions)
)
```

**Snapshots:**
- `SnapshotService` creates full entity snapshots on terminal state transitions (Completed, Closed)
- Used for archival and rollback analysis; not for every change (prevents storage bloat)

### Assignment Patterns

For entities with user assignment (Task, WorkOrder, etc.):
- Store `assigned_to_user_id` (FK to users collection, nullable) for CRM users
- Store `assigned_to_name` (always populated) for display — can be a CRM username or free text ("MEP", "Architect", etc.)
- Store `assigned_to_type` ("user" | "external") to distinguish
- This dual model allows assigning to external parties without requiring CRM accounts

---

## Frontend Development

### Component Structure

Components follow atomic design principles:
- **Atoms**: Basic UI elements (buttons, inputs, badges)
- **Molecules**: Simple component compositions
- **Organisms**: Complex, self-contained features
- **Pages**: Full page layouts

### Styling

- **Tailwind CSS 4**: All styling via utility classes
- **Design Tokens**: Luxury Industrial aesthetic (see `packages/ui`)
- **Dark Mode**: Supported via next-themes
- **Responsive**: Mobile-first approach

### State Management

- **Global State**: Zustand in `src/store/`
  - `useProjectStore` — Active project context (mandatory for project-scoped operations)
  - `useScheduleStore` — Scheduler task data with optimistic updates
  - `useAuthStore` — User authentication & role data
- **Server State**: SWR for API data fetching (client-side, cache-aware)
- **Component State**: React hooks for local state
- **No Redux**: Zustand is preferred for its simplicity and performance

### Web API Client Pattern

File: `apps/web/src/lib/api.ts`

The Axios client automatically injects headers and handles authentication:
- Injects `X-Project-Id` header from `useProjectStore` for project-scoped requests
- Injects `Authorization: Bearer {JWT}` token from `useAuthStore`
- 401 responses trigger automatic token refresh via refresh-token endpoint
- GenericResponse envelope unwrapping (v1 spec): `{ data, status_code, timestamp }`

**Usage:**
```typescript
const { data: tasks } = useSWR(
  activeProject ? `/api/v1/tasks/?project_id=${activeProject.project_id}` : null,
  fetcher  // Uses the Axios client above
);
```

### Web Page Patterns

**List Page Example** (reference: `work-orders/page.tsx`):
1. Extract `activeProject` from `useProjectStore()`
2. Use `useSWR` to fetch data with `project_id` filter
3. Display with AG Grid (`FinancialGrid` component)
4. Add filters (search, status dropdowns)
5. Row click → navigate to detail page

**Detail Page Example** (reference: `work-orders/[id]/page.tsx`):
1. Extract `id` from route params: `useParams()`
2. Fetch single record + related data in parallel
3. Implement optimistic updates with version conflict handling
4. Use `VersionConflictModal` for concurrency conflicts
5. Sidebar shows change log (audit entries from API)

### UI Component Library

**Location:** `packages/ui/src/components/` + `apps/web/src/components/ui/`

**Core Components:**
- `GlassCard` — Frosted glassmorphism container (Luxury Industrial aesthetic)
- `KPICard` — Metric display with status colors & trend arrows
- `FinancialGrid` — AG Grid wrapper for financial tables (sortable, filterable)
- Button, Input, Dialog, Breadcrumbs (shadcn + Radix UI primitives)

**Styling Approach:**
- Tailwind CSS 4 with CSS variables for theme colors
- `globals.css` defines Luxury Industrial color tokens
- Dark mode support via `next-themes`
- Mobile-first responsive design

---

## Testing

### API Testing

```bash
cd apps/api
pytest tests/                    # Run all tests
pytest tests/test_routes.py      # Test specific file
pytest -k "test_create"          # Run tests matching pattern
pytest --cov                     # Generate coverage report
```

Test files in `apps/api/tests/`:
- Integration tests use real database (test MongoDB)
- Fixtures in `conftest.py`
- Mocking only for external services

### Web Testing

TypeScript type checking:
```bash
cd apps/web
npx tsc --noEmit
```

Jest + React Testing Library available for component and integration tests. Test files use `__tests__` directory convention.

---

## Mobile Development

### Mobile API Client Pattern

File: `apps/mobile/services/apiClient.ts`

Similar to web but with mobile-specific features:
- JWT stored in secure storage (native) or localStorage (web)
- 15-second request timeout with AbortController
- Token refresh on 401 with exponential backoff retry
- GenericResponse envelope unwrapping (v1 spec)
- Organized into domain-scoped API groups: `authApi`, `projectsApi`, `dprApi`, `tasksApi`, etc.

**Usage:**
```typescript
const tasks = await tasksApi.getAll(projectId, { status: "Open", search: "beam" });
const task = await tasksApi.getById(taskId);
```

### Mobile Navigation & Role-Based Routing

- **Root:** `index.tsx` checks `useAuth()` and redirects by role (admin, supervisor, client)
- **Role Groups:** `(admin)/`, `(supervisor)/`, `(client)/` with separate layout + guards
- **Project Context:** `useProjectContext()` provides selected project for supervisor workflow
- **Tab Navigation:** Admin has 5 tabs (Dashboard, Projects, DPR, Attendance, More); Supervisor has 4 tabs

### Mobile Component Patterns

**Base Components** (`apps/mobile/components/ui/`):
- `Card` — Variant-based (default, outlined, elevated, glass) with padding options
- `Button` — Variants (primary, secondary, outline, danger, ghost) with loading state
- `Input` — Label, error, hint, icon support, password toggle
- Theme context for dynamic styling

**Screen Patterns:**
- **List Screen:** FlatList + filters (search, date range, status chips) + pull-to-refresh
- **Detail Screen:** Scrollable view with editable/read-only sections, nested components
- **Form Screen:** TextInput fields, pickers (date, time), submission handlers

### Mobile Types

File: `apps/mobile/types/api.ts` — Comprehensive TypeScript interfaces for all API contracts, mirroring `packages/types` + mobile-specific aggregates like `AdminDashboardData`, `SupervisorDashboardData`

---

## Deployment & CI/CD

### Environment Variables

Each app requires `.env` file:

**API (.env)**:
```
MONGO_URL=mongodb://...
DB_NAME=tac_pmc_crm
JWT_SECRET_KEY=...
ENVIRONMENT=development
AWS_ACCESS_KEY_ID=...
REDIS_URL=...
```

**Web (.env.local)**:
```
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

### Build & Deployment

- **API**: Python app, runs on port 8000 (uvicorn)
- **Web**: Next.js app, runs on port 3000
- **Mobile**: Expo web on port 3001

**Docker & CI/CD**:
- Docker support: `Dockerfile` in both `apps/api/` (Python 3.11-slim) and `apps/web/` (Node 20 multi-stage)
- GitHub Actions CI/CD: `.github/workflows/ci.yml` — 4 jobs: API lint+test, Web lint+typecheck, Docker build API, Docker build Web
- API container includes WeasyPrint system libs (libcairo2, libpango) for PDF generation
- Web container uses Next.js standalone output with `NEXT_PUBLIC_BACKEND_URL` build arg

**Production Seed Script**:
```bash
cd apps/api
MONGO_URL="mongodb+srv://..." DB_NAME="tac_pmc_crm_prod" python scripts/seed_production.py
```
Creates: 1 org (TAC-PMC), 3 users (admin/supervisor/client), 5 financial codes, 1 project (Majorda Villa) with 45 scheduler tasks.

---

## Troubleshooting

### Module Resolution Issues

If you see "module not found" errors:
1. Ensure you're using workspace imports: `@tac-pmc/types`, `@tac-pmc/ui`
2. Check `pnpm-lock.yaml` is up to date: `pnpm install`
3. Clear caches: `turbo clean && pnpm install`

### API Connection Errors

1. Verify API is running: `curl http://localhost:8000/docs`
2. Check MongoDB connection in `.env`
3. Ensure CORS is configured in `apps/api/app/core/lifecycle.py`

### Port Conflicts

- API: 8000 (check `ps aux | grep uvicorn`)
- Web: 3000 (check `lsof -i :3000`)
- Mobile: 3001 (check `lsof -i :3001`)

---

## Key Files Reference

- **AwesomeGSD_Skills.md**: Skill-first operating manual with GSD protocol
- **Ruflo.md**: RuFlo V3 orchestration framework & CLI commands
- **turbo.json**: Monorepo task definitions
- **pnpm-workspace.yaml**: Workspace configuration
- **.github/workflows/ci.yml**: GitHub Actions CI/CD pipeline (4 jobs)
- **.planning/**: RuFlo memory and planning artifacts (gitignored)
- **apps/api/scripts/seed_production.py**: Production database seeding

---

## Integration with claude-flow

This project uses **claude-flow** for orchestration:

```bash
# Check CLI status
npx @claude-flow/cli@latest doctor --fix

# Search memory
npx @claude-flow/cli@latest memory search --query "authentication"

# Initialize a swarm for new features
npx @claude-flow/cli@latest swarm "Feature Name" --strategy adaptive
```

See Ruflo.md for complete CLI reference.

---

## Key Architectural Principles

1. **Domain-Driven Design**: Every module owns its domain model; business rules live in `domain/models.py`, not services
2. **Org Scoping**: All queries include `organisation_id` filter via BaseRepository `**filters` for multi-tenancy
3. **State Immutability**: Final states (marked in StateMachine with empty transition sets) freeze data — no edits allowed
4. **Audit Everything**: Every state change (CREATE, UPDATE, DELETE, TRANSITION) logged via AuditService
5. **Idempotency**: Financial operations use idempotency keys (`core/idempotency.py`) to prevent duplicates
6. **Project Scoping**: Web and mobile operations require `activeProject` context; no cross-project data leaks
7. **No Soft Deletes**: Entities transitioned to final states (Closed, Cancelled) rather than soft-deleted
8. **Cross-Module Communication**: Via REST API only; no direct database access or Python imports between modules
9. **Type Safety**: End-to-end TypeScript (web, mobile) + Pydantic (API); shared types in `packages/types`
10. **Zero Error Policy**: All merges require passing `pnpm lint` and `pytest` with zero ERRORS (warnings OK)

## Additional Notes

- **FastAPI interactive docs**: available at `http://localhost:8000/docs` when the API is running
- **Financial codes** (master data): LABOR, MATERIAL, EQUIPMENT, OVERHEAD, CONTINGENCY
- **Mobile OCR**: `(admin)/ocr.tsx` handles document scanning via camera
- **Voice Logs**: Supervisor can submit voice-based site logs via `(supervisor)/voice-log.tsx`
- **DPR flow**: Supervisor creates → Admin reviews/approves; status machine lives in `site_operations` module
- **Tasks module**: New module for task management with Kanban board, change logs, and AI summaries
- **Luxury Industrial Design**: All UI follows this aesthetic; check `packages/ui` for design tokens and component examples

<!-- graphiphy knowledge graph tools -->
## Knowledge Graph Tooling (graphiphy)

**IMPORTANT: This project uses a knowledge graph located in `graphify-out/`. ALWAYS use the graph tools (graphiphy) to understand code flow and structural context.** The graph is faster, cheaper, and provides deep insights into callers, dependents, and execution paths.

### When to use graphiphy FIRST

- **Exploring code flow**: Consult `graphify-out/graph.json` or `graphify-out/graph.html` for accurate semantic navigation.
- **Understanding impact**: Analyze relationships to determine the blast radius of any change.
- **Code review**: Compare changes against the graph to ensure architectural consistency.
- **Architecture mapping**: Use community detection (see `graphify-out/GRAPH_REPORT.md`) to verify bounded context sovereignty.

### Key Knowledge Files
- `graphify-out/graph.json`: Structural data for programmatic analysis.
- `graphify-out/graph.html`: Visual exploration of dependencies.
- `graphify-out/GRAPH_REPORT.md`: Summary of communities, God nodes, and knowledge gaps.

### Workflow

1. The graph should be refreshed whenever significant structural changes occur.
2. Use the graph data to plan navigation before using Grep/Glob.
3. Verify that new code aligns with the existing community boundaries.

---

## gstack Integration

**Web Browsing**: Use `/browse` skill from gstack for all web browsing. Never use `mcp__claude-in-chrome__*` tools.

**Available Skills**:
- `/office-hours`, `/plan-ceo-review`, `/plan-eng-review`, `/plan-design-review` — Planning & consultation
- `/design-consultation`, `/design-shotgun`, `/design-html`, `/review` — Design & review
- `/ship`, `/land-and-deploy`, `/canary` — Deployment workflows
- `/benchmark` — Performance testing
- `/browse` — Web browsing (use this, not MCP tools)
- `/qa`, `/qa-only` — QA workflows
- `/design-review`, `/setup-browser-cookies` — Design & browser setup
- `/retro` — Retrospective
- `/investigate` — Investigation & analysis
- `/document-release` — Release documentation
- `/codex`, `/cso`, `/autoplan` — Code & planning
- `/plan-devex-review`, `/devex-review` — DevX review
- `/careful`, `/freeze`, `/guard`, `/unfreeze` — Safety controls
- `/gstack-upgrade` — Upgrade gstack
- `/learn` — Learning

---

## Skill routing

Configure gstack opinionated engineering roles:

- "is this worth building?" -> `/office-hours`
- "i am stuck" -> `/office-hours`
- "plan this" -> `/autoplan`
- "build this" -> `/codex`
- "careful now" -> `/careful`
- "take a checkpoint" -> `/checkpoint`
- "test this" -> `/qa`
- "qa this" -> `/qa`
- "review this" -> `/review`
- "ship this" -> `/ship`
- "check health" -> `/health`
- "investigate this" -> `/investigate`
- "reflect on this" -> `/retro`
- "reflect on the last turn" -> `/retro`
- "guard this" -> `/guard`
- "unfreeze this" -> `/unfreeze`
- "freeze this" -> `/freeze`
- "upgrade gstack" -> `/gstack-upgrade`
