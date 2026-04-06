# AGENTS.md — TAC-PMC-CRM

## Critical Rules

1. **Platform Neutrality**: Never use backslashes (`\`) or `.exe`. Always use `/` and `python -m` for cross-platform CI safety.
2. **Zero Error Policy**: No merges allowed if `pnpm lint` or `pytest` returns ERRORS (warnings allowed).
3. **Read Before Edit**: Always read a file before modifying it.
4. **One Message = All Concurrent Operations**: Batch related reads/writes/bash commands.

## Commands

```bash
# Monorepo
pnpm start-all          # All 3 services (API + Web + Mobile) concurrently
pnpm dev                # Turbo dev mode all apps
pnpm build              # Build all
pnpm lint                # Lint all (API flake8 + Web ESLint)
pnpm format             # Prettier format (ts/tsx/md)
pnpm test:e2e          # Playwright E2E tests

# API (port 8000)
cd apps/api && python -m uvicorn app.main:app --reload --host 0.0.0.0
cd apps/api && python -m pytest                        # Tests
cd apps/api && python -m flake8 .                   # Lint

# Web (port 3000)
cd apps/web && npm run dev
cd apps/web && npx tsc --noEmit                    # Type check

# Mobile (port 3001)
cd apps/mobile && npm run dev
```

## Architecture

- **Monorepo**: pnpm workspace + Turbo
- **API**: Python FastAPI + MongoDB/Motor, DDD bounded contexts in `apps/api/app/modules/`
- **Web**: Next.js 16 + React 19 + Zustand + Tailwind (port 3000)
- **Mobile**: React Native/Expo (port 3001)
- **Orchestration**: RuFlo v3 (`npx -y ruflo@latest`)

## Key Gotchas

- API docs at `http://localhost:8000/docs` when running
- Financial codes: LABOR, MATERIAL, EQUIPMENT, OVERHEAD, CONTINGENCY
- DPR flow: Supervisor creates → Admin reviews/approves
- PDF generation requires WeasyPrint system libs (libcairo2, libpango)
- Connection pooling uses Motor (async MongoDB driver)

## Existing Docs

- `CLAUDE.md` — Comprehensive (472 lines)
- `AwesomeGSD_Skills.md` — Skill-first protocol
- `Ruflo.md` — RuFlo v3 swarm framework

<!-- code-review-graph MCP tools -->
## MCP Tools: code-review-graph

**IMPORTANT: This project has a knowledge graph. ALWAYS use the
code-review-graph MCP tools BEFORE using Grep/Glob/Read to explore
the codebase.** The graph is faster, cheaper (fewer tokens), and gives
you structural context (callers, dependents, test coverage) that file
scanning cannot.

### When to use graph tools FIRST

- **Exploring code**: `semantic_search_nodes` or `query_graph` instead of Grep
- **Understanding impact**: `get_impact_radius` instead of manually tracing imports
- **Code review**: `detect_changes` + `get_review_context` instead of reading entire files
- **Finding relationships**: `query_graph` with callers_of/callees_of/imports_of/tests_for
- **Architecture questions**: `get_architecture_overview` + `list_communities`

Fall back to Grep/Glob/Read **only** when the graph doesn't cover what you need.

### Key Tools

| Tool | Use when |
|------|----------|
| `detect_changes` | Reviewing code changes � gives risk-scored analysis |
| `get_review_context` | Need source snippets for review � token-efficient |
| `get_impact_radius` | Understanding blast radius of a change |
| `get_affected_flows` | Finding which execution paths are impacted |
| `query_graph` | Tracing callers, callees, imports, tests, dependencies |
| `semantic_search_nodes` | Finding functions/classes by name or keyword |
| `get_architecture_overview` | Understanding high-level codebase structure |
| `refactor_tool` | Planning renames, finding dead code |

### Workflow

1. The graph auto-updates on file changes (via hooks).
2. Use `detect_changes` for code review.
3. Use `get_affected_flows` to understand impact.
4. Use `query_graph` pattern="tests_for" to check coverage.
