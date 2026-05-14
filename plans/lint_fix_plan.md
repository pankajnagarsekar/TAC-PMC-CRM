# Implementation Plan - Resolving Remaining Python Linting Issues

## Objective
Fix all reported PEP8 and flake8 linting violations in the backend services to ensure code quality and prevent runtime errors (e.g., undefined `ObjectId`).

## Tasks

### 1. Fix `analytics_service.py`
- **Issue**: Undefined name `ObjectId` on lines 378 and 379.
- **Action**: Add `from bson import ObjectId` to the imports.
- **File**: `apps/api/app/modules/reporting/application/analytics_service.py`

### 2. Fix `reporting_service.py`
- **Issue**: Trailing whitespace on blank lines (W293).
- **Action**: Remove spaces from blank lines at lines 54, 281, 294, 296, 309, and 311.
- **File**: `apps/api/app/modules/reporting/application/reporting_service.py`

### 3. Verification
- Run manual flake8 check: `.venv/Scripts/python -m flake8 apps/api`
- Fix `pnpm lint` script in `apps/api/package.json` to be cross-platform (or at least work on Windows as requested by user).
- Run `pnpm lint` from root.

## Skills Used
- `@python-pro`
- `@lint-and-validate`
- `@systematic-debugging`
- `@software-architecture`
