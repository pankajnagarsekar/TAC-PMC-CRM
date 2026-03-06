# Enterprise Technical Architecture Specification

## CRM Financial Management System -- Version 2.0 (Turborepo & MongoDB Edition)

**Document 3 of 6 -- Upgraded Enterprise Edition** **Generated On:** 04 March 2026

------------------------------------------------------------------------

# 1. Engineering Standard

This system is a **financial-grade, audit-sensitive, ACID-compliant enterprise application**.

Design Goals:
-   Zero rounding drift (Strict `Decimal128` enforcement)
-   Deterministic financial calculations (Backend authority only)
-   Strict transactional integrity via MongoDB Multi-Document Sessions
-   Concurrency-safe budget deductions
-   Immutable audit history
-   Template-parity exports (Excel & PDF)
-   High-volume scalability
-   Multi-project financial isolation
-   Idempotent financial operations
-   No silent failures

Every paisa must be traceable.

------------------------------------------------------------------------

# 2. Architectural Pattern

## 2.1 Architecture Type
**Modular Monolith within a Monorepo ecosystem.**
The codebase MUST be structured using **Turborepo** to ensure a single source of truth for types, UI components, and utilities, preventing drift between the Web and Mobile interfaces.

## 2.2 Layered Directory Structure
```text
/tac-pmc-crm
├── /apps
│   ├── /mobile        (Expo React Native - Supervisors, Admin Field App, Client App)
│   ├── /web           (Next.js 14+ App Router - Admin CRM, Client Portal)
│   └── /api           (FastAPI + Motor MongoDB Backend)
├── /packages
│   ├── /types         (Shared TypeScript API contracts & DTOs)
│   ├── /ui            (Shared Tailwind configs, Shadcn primitives)
│   └── /eslint-config (Universal linting rules)

3. Financial Integrity Core Rules
3.1 Monetary Storage Rules (CRITICAL)
MongoDB lacks a native SQL DECIMAL type.

Mandate: All monetary fields MUST be stored using MongoDB Decimal128 (BSON type) or stored as integers (paise) to prevent IEEE 754 floating-point rounding drift.

No float or double allowed for currency anywhere in the stack.

Rounding Mode: Round Half Up (Standard Financial Rounding) executed server-side only.

Frontend calculations are display-only.

3.2 Calculation Authority
Only the FastAPI backend performs authoritative calculations:

Subtotal & Discount impact

Tax calculations (CGST/SGST)

Retention calculation

Grand totals & Budget deductions

Vendor payable adjustments

4. Database Design (Strict)
4.1 Database Engine
MongoDB 5.0+ (Requires Replica Set or MongoDB Atlas for Multi-Document Transactions).

4.2 Concurrency Control & ACID Transactions
Critical operations (WO Save, PC Close, Petty Cash Expense) MUST utilize MongoDB Sessions to prevent race conditions on budget deduction.

Work Order Save Transaction Flow:
async with await client.start_session() as session:

async with session.start_transaction():

Check Idempotency-Key against operation_logs.

Fetch & Validate Category Remaining Budget.

Deduct amount from project_category_budgets and projects.

Insert work_orders document.

Insert audit_logs document.

Commit Transaction. (Rollback automatically on any exception).

PC Close (Fund Transfer Model):
Start MongoDB Transaction.

Check Idempotency-Key.

Deduct allocation_remaining and master_remaining_budget.

Increase Cash-in-Hand.

Update last_pc_closed_date.

Insert Audit Snapshot.

Commit Transaction.

5. Idempotency Strategy
Critical operations (PC Close, WO Save, Petty Expense):

Each transaction generates a unique operation ID (UUID) from the frontend.

Passed to the backend via the Idempotency-Key HTTP header.

Operation ID stored in the operation_logs collection.

If a duplicate request is detected (e.g., due to network retry) → ignore safely and return 200 OK with the previous result.

Prevents double deduction.

6. Status State Machine & Vendor Ledger
6.1 Status Transitions
WO & PC States: Draft → Pending → Completed → Closed → Cancelled.

State transitions are strictly enforced at the FastAPI service layer. Cannot reduce WO below total generated PC. Cannot delete if PC exists.

6.2 Vendor Payable Ledger
The Vendor Ledger is an append-only (immutable) collection tracking vendor balances.

Increases on PC Save.

Decreases on PC Close (Payment Made) or Retention Held.

7. Web UI Tech Stack (The "Fintech" Aesthetic)
Framework: Next.js 14+ (React).

Styling: Tailwind CSS.

Component Library: Shadcn UI / Radix UI for accessible, unstyled primitives.

Dashboards: Tremor.so for high-fidelity financial KPI cards and charts.

Data Grids: AG Grid (Enterprise) with a custom Tailwind theme for strict Excel-parity data entry. Keyboard navigation and 2-decimal alignment are mandatory.

8. Audit System (Immutable)
The audit_logs collection is append-only. No updates or deletions are allowed.
Fields captured:

_id (ObjectId)

entity_name & entity_id

action_type

previous_state (BSON/JSON)

new_state (BSON/JSON)

user_id & timestamp

9. Reporting Engine (Scalable)
Use MongoDB Aggregation Pipelines for generating real-time reports.

For heavy reports (Project Summary, Custom Date Range), utilize MongoDB Materialized Views or $merge aggregation outputs scheduled via background cron jobs.

Financial graphs (Budget vs WO, WO vs PC Paid) are computed strictly from authoritative DB values. No frontend aggregation allowed.

10. Template Engine (Enterprise Level)
10.1 Excel Export
Library: ExcelJS.

Maintain master template files. Data injected via named placeholders.

Column positions fixed. Formula ranges pre-configured. Protected cells for calculated fields.

10.2 PDF Export
Engine: Puppeteer (HTML → PDF) executed in a background worker (e.g., Celery/Redis).

Dedicated HTML template strictly controlled by CSS to mirror the Excel sheet layout.

Final page auto-appends 3000-word Default Terms & Conditions. Logo embedded from storage.

11. Data Volume & Scalability
Designed to handle:

1000+ projects

100k+ WOs

500k+ PCs

1M+ petty entries

Strategies:

Compound indexes on project_id + category_id.

Pagination (Cursor-based) for all list endpoints.

Background job queue (Celery/Redis) for heavy PDF generation and OCR invoice scanning.

12. Security Model & Data Validation
12.1 Security
JWT Authentication with short-lived access tokens and http-only refresh tokens.

Role-based middleware (Admin, Supervisor, Client).

Rate limiting on financial endpoints.

Input validation strictly enforced by Pydantic v2 models.

12.2 Data Validation Layer
Before any financial save, the backend MUST validate:

Totals match line-item sum exactly.

Retention and GST calculations match mathematical expectations.

Category match for WO is valid.

No arithmetic drift in Decimal128 conversions.
Reject transaction with 400 Bad Request if any mismatch occurs.

13. Hard Constraints (Enforced at Code + DB Level)
Downward category budget edit blocked.

Cannot create Petty/OVH PC if remaining allocation = 0.

Cannot reduce WO below generated PC.

Cannot delete used category.

All financial actions logged.

14. Performance Benchmarks (Target)
WO Save < 200ms

PC Close < 200ms

Petty Entry < 100ms

Report generation < 2s (without export)

PDF generation < 5s async

Conclusion
This system is engineered as a:

Financially deterministic

Concurrency-safe (via MongoDB Transactions)

Audit-complete

Template-parity

Enterprise-grade CRM platform

No calculation ambiguity permitted. All financial mutations are atomic and traceable.

End of Enterprise Technical Architecture -- Version 2.0 Locked