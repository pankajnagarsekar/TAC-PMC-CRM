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
└── pnpm-workspace.yaml # Workspace configuration
```

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
│   ├── (admin)/       # Admin routes (DPR review, attendance view)
│   ├── (client)/      # Client routes (project overview)
│   ├── (supervisor)/  # Supervisor routes (attendance, worker logs)
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

- **Error Detection**: @error-detective + @debugging-toolkit + @software-architecture
- **New Features**: @software-architecture + @[language]-pro + @database-design
- **UI/UX Changes**: @antigravity-design-expert + @tailwind-design-system + @react-best-practices
- **Database Changes**: @database-design + @data-integrity-patterns + @sql-pro
- **API Development**: @api-design-principles + @[language]-pro + @security-best-practices

### 2. **RuFlo V3 Framework** (Ruflo.md)

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
- `financial/application/master_data_service.py`: Reference data management
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
- **Server State**: SWR for API data fetching
- **Component State**: React hooks for local state
- **No Redux**: Zustand is preferred for its simplicity and performance

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

### Frontend Testing

TypeScript type checking:
```bash
cd apps/web
npx tsc --noEmit
```

Jest + React Testing Library available for component and integration tests. Test files use `__tests__` directory convention.

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

## Recent Implementations

### Supervisor Attendance & Site Operations (v1.5)

- **Supervisor Attendance**: Mobile attendance marking with GPS and photo capture
- **Admin Attendance Dashboard**: View and manage attendance records across projects
- **Worker Logs**: Track daily worker presence and hours
- **Site Overheads**: Manage site-level overhead costs
- **DPR Status Machine**: Daily Progress Reports with status transitions

### Cash Management & Financial Services (v1.4)

- **Cash Service**: Real-time cash position tracking and reconciliation
- **Master Data Service**: Reference data management for financial codes (LABOR, MATERIAL, EQUIPMENT, OVERHEAD, CONTINGENCY)
- **Payment Service**: Payment processing and transaction management
- **Work Order Creation**: Financial grid with line-item management and budget validation
- **Idempotency**: Duplicate-safe financial operations

### Reporting & AI Insights

- **AI Summary Service**: LLM-powered project and financial summaries (OpenAI integration)
- **Analytics Dashboard**: Real-time project metrics and KPIs

### Infrastructure

- **CI/CD Pipeline**: GitHub Actions — API lint+test, Web lint+typecheck, Docker builds
- **Docker**: Production containers for both API (Python 3.11-slim) and Web (Node 20 multi-stage)
- **Production Seeding**: `seed_production.py` for initial database setup

---

## Additional Resources

- **FastAPI Docs**: http://localhost:8000/docs (when running)
- **Next.js Docs**: https://nextjs.org/docs
- **Tailwind CSS**: https://tailwindcss.com/docs
- **Zustand**: https://github.com/pmndrs/zustand
- **MongoDB Motor**: https://motor.readthedocs.io/
