# Backend Restructuring Protocol (RESTRUCTURE_PROTO)

This document provides the specific architectural context and mandates for the TAC-PMC-CRM backend restructuring.

## 1. Active Objective
Restructure `apps/api` from a script-based monolith into a Domain-Driven Design (DDD) layered architecture.

- **Primary Source of Truth**: [Implementation Plan](file:///C:/Users/panka/.gemini/antigravity/brain/724a9e00-33a2-4aa7-a4c1-5f2d907790b8/implementation_plan.md)
- **Status Tracker**: [Task File](file:///C:/Users/panka/.gemini/antigravity/brain/724a9e00-33a2-4aa7-a4c1-5f2d907790b8/task.md)

## 2. Production-Ready Mandates
1.  **DDD Domain Grouping**: Services, repos, and schemas must be grouped by domain (`user`, `project`, `verification`, `ocr`).
2.  **Naming Conventions**: Strict suffixes: `_service.py`, `_repo.py`, `_routes.py`, `_schema.py`.
3.  **Dependency Injection (DI)**: Use FastAPI `Depends` for all services and DB. **Forbidden**: Direct instantiation in routes.
4.  **Transaction Logic**: Services own the transaction boundaries. Partial writes are prohibited.
5.  **Standard Responses**:
    - Error: `{ success: false, message: string, error_code: string }`
    - Success: `{ success: true, data: T, message: string }`
6.  **Async/UTC Strategy**: 100% async IO. All timestamps stored in UTC.

## 3. Background & Heavy Tasks
- OCR and PDF Verification must run as **Background Jobs** via Celery.
- API must return a `job_id` for polling.
- File storage lifecycle (Local/S3) managed in `app/core/storage.py`.

## 4. Execution Pipeline
- **Phase 0**: Pre-Migration Audit (Extract logic into functions in-place).
- **Phase 1**: Structure & Core (`app/core/`).
- **Phase 2**: Repositories & BaseRepository.
- **Phase 3**: Services & DI Wiring.
- **Phase 4**: API Thin Layer & Contracts.
- **Phase 5**: Frontend/Mobile Sync.
