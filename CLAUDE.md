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
    ├── identity/      # Auth, Users, Roles
    ├── project/       # Projects, Clients, Timelines
    ├── financial/     # Payments, Budgets, Cash Flow
    ├── contracting/   # Work Orders, Vendors
    ├── site_operations/ # DPRs, Attendance, Site Logs
    ├── reporting/     # AI Summaries, Analytics
    └── shared/        # Shared Kernel (Audit, Alerts, BaseRepo)
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
├── app/               # Expo Router navigation
├── screens/           # Screen components
└── components/        # Reusable components
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

# Lint all apps
pnpm lint

# Format code (Prettier)
pnpm format
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

### 1. **Skill-First Rule** (CLAUDE_Skills.md)

**Every task MUST identify and document relevant skills before beginning work.** Skill files are in `.claude/skills/`. Stack skills strategically based on task type:

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

**Aggregation**: The central `apps/api/app/api/router.py` imports and registers these modular routers.

### Services Layer

Business logic resides in the `application/` layer of each module:
- `identity/application/auth_service.py`: Authentication logic
- `financial/application/master_data_service.py`: Reference data management
- `project/application/scheduler_service.py`: Critical path and scheduling
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

No test framework configured yet—use Jest + React Testing Library when adding tests.

---

## Deployment & CI/CD

### Environment Variables

Each app requires `.env` file:

**API (.env)**:
```
MONGODB_URI=mongodb://...
JWT_SECRET=...
AWS_ACCESS_KEY_ID=...
REDIS_URL=...
```

**Web (.env.local)**:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Build & Deployment

- **API**: Python app, runs on port 8000 (uvicorn)
- **Web**: Next.js app, runs on port 3000
- **Mobile**: Expo web on port 3001

Docker/Kubernetes config not yet configured—add when deploying to production.

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

- **CLAUDE_Skills.md**: Mandatory skill usage documentation
- **Ruflo.md**: RuFlo V3 orchestration framework & CLI commands
- **apps/api/CLAUDE.md**: API-specific RuFlo configuration
- **turbo.json**: Monorepo task definitions
- **pnpm-workspace.yaml**: Workspace configuration

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

## Additional Resources

- **FastAPI Docs**: http://localhost:8000/docs (when running)
- **Next.js Docs**: https://nextjs.org/docs
- **Tailwind CSS**: https://tailwindcss.com/docs
- **Zustand**: https://github.com/pmndrs/zustand
- **MongoDB Motor**: https://motor.readthedocs.io/
