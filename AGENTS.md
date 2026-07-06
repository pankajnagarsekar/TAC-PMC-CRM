# AGENTS.md — TAC-PMC-CRM

This file is the single-most authoritative brain for AI coding agents regarding project rules, safety protocols, bug fixing, and coding standards, following the standard format from https://github.com/agentsmd/agents.md.

## 🚨 MANDATORY SAFETY PROTOCOLS (ZERO-DELETION GUARANTEE) 🚨
- **Never use Bash for File Edits**: NEVER use `sed`, `awk`, `echo >`, or `cat >` to edit or manipulate files in bulk. 
- **Use Built-in Editor Tools**: ALWAYS use native programmatic tools (`replace_file_content` and `multi_replace_file_content`) which require exact matching before applying changes. This prevents accidental file clipping.
- **Incremental Application**: When fixing lint errors, apply the correct types or fixes specifically to the exact lines mentioned in the error logs. Never attempt to rewrite an entire file blindly.
- **Zero Error Policy**: Before creating a commit or deploying, ensure `pnpm lint` and tests pass without errors. Never push incomplete logic that breaks the application entry points (`main.py`, `router.py`).

## 🛠️ Dev Environment & Coding Instructions
- **Platform Neutrality**: Never use backslashes (`\`) or `.exe` in scripts. Always use cross-platform paths (`/`).
- **Backend (API)**: Python FastAPI with Motor (MongoDB). Follow strict Domain-Driven Design (DDD). Sovereign modules (`project`, `financial`, `reporting`) should never cross-import; use the shared kernel or API layers.
- **Frontend (Web)**: React 19, Next.js 16 App Router, Tailwind CSS 4. Use `Zustand` for state management. Avoid Redux.
- **Database Operations**: Always use `BaseRepository` to ensure strict organisation ID scoping (`**filters`) and optimistic locking.

## 🧪 Testing Instructions
- **Backend Tests**: 
  - **Module-Specific**: When modifying code within a specific module, run only its target test directory to keep iteration fast (e.g., `pnpm -C apps/api exec python -m pytest tests/modules/reporting/` for changes in the `reporting` module).
  - **Full Application**: Run the full suite `pnpm -C apps/api exec python -m pytest` when verifying the entire application's integrity before committing or submitting a PR.
- **Linting**: Run `pnpm lint` from root or specific packages.
- **Iterative Fixing**: Address lint warnings and test failures sequentially until the pipeline runs green.

## 👁️ Code Reviews & PRs
- Always double-check `main.py` and `router.py` entry points before considering backend bug-fixes complete to ensure ASGI is intact.
- Use `graphify-out/graph.json` or related tools to evaluate architectural blast radius before making widespread module changes.
