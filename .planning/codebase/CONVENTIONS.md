# Coding Conventions

## Python (Backend)
- **Formatting**: `black` for code, `isort` for imports.
- **Type Hinting**: Mandatory type hints for all function signatures.
- **Linting**: `flake8` and `mypy` for static analysis.
- **Async**: Asynchronous-first approach for all I/O operations (Motor, FastAPI).
- **Naming**: `snake_case` for variables/functions, `PascalCase` for classes.
- **Patterns**:
  - Use `BaseRepository` for DB access.
  - Inject dependencies via FastAPI `Depends`.
  - Prefer `financial_utils.py` for monetary calculations.

## TypeScript (Web & Mobile)
- **Naming**: `PascalCase` for React components/files, `camelCase` for variables/hooks.
- **Types**: Interfaces over types where possible; mandatory types for all props.
- **Structure**: Feature-based organization within `components/`.
- **State**: Use Zustand for global state; prefer local state (`useState`) for UI-only logic.

## Monorepo
- **Commits**: Conventional Commits (feat, fix, docs, chore).
- **Exports**: Use barrels (`index.ts`) for package entry points.
- **Scripts**: Execute commands via `pnpm -C apps/target exec ...` or Turbo.
