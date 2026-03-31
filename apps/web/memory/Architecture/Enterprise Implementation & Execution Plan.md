# Enterprise Implementation & Execution Plan

## CRM Financial Management System -- Version 2.0 (Monorepo Build Plan)

**Document 6 of 6 -- FINAL LOCKED VERSION** **Generated On:** 04 March 2026

------------------------------------------------------------------------

# 1. Implementation Philosophy

This CRM is a financial-grade system pivoting to a Monorepo and MongoDB ecosystem.
Build principles:
-   ACID-compliant MongoDB Transactions from Day 1
-   Decimal128 strict enforcement (No arithmetic drift)
-   Single source of truth for Types via `/packages/types`
-   No phase proceeds without invariant validation

------------------------------------------------------------------------

# Phase 0: Monorepo Foundation & Database Refactoring
**Deliverables:**
-   Initialize Turborepo structure (`apps/web`, `apps/mobile`, `apps/api`, `packages/types`).
-   Migrate existing React Native types (`types/api.ts`) to `/packages/types` for universal consumption.
-   Refactor FastAPI `models.py` to enforce `Decimal128` fields instead of native floats.
-   Implement MongoDB Transaction Manager utility in the backend core.
-   Create `global_settings` collection with `client_permissions` matrix.

**Validation:** Ensure Mobile App builds successfully with shared types. Verify MongoDB transaction context manager successfully rolls back on simulated exception.

------------------------------------------------------------------------

# Phase 1: Web CRM Shell & Global Settings
**Deliverables:**
-   Initialize Next.js App Router project in `/apps/web`.
-   Configure Tailwind CSS, Shadcn UI, and AG Grid (Enterprise).
-   Build Global Sidebar and Sticky Project Context Header.
-   Develop UI for Global Settings (GST rates, T&C, Category Master, Client Toggle Board).

**Validation:** Project Context Switcher successfully purges state. Client toggle board successfully updates backend document.

------------------------------------------------------------------------

# Phase 2: Core Financial Engine (Commitment Model)
**Deliverables:**
-   Implement Clients & Projects CRUD (Web).
-   Implement Category Budget initialization (Web).
-   Implement Work Order (WO) Module with AG Grid Excel-parity.
-   Implement Payment Certificate (PC) Module (WO-Linked).
-   Wire MongoDB Transactions for WO Save and PC Close.

**Validation:** `committed_amount = SUM(WO.grand_total)`. `master_remaining_budget = SUM(category.remaining_budget)`. Concurrency test (simulate 50 parallel WO saves).

------------------------------------------------------------------------

# Phase 3: Liquidity Engine & Admin Mobile
**Deliverables:**
-   Implement Fund Request PC logic.
-   Build new Admin Petty Cash / OVH UI inside the **Expo Mobile App** (Red text for negative, persistent Amber warnings for thresholds).
-   Build identical Web CRM Petty Cash / OVH UI.
-   Implement backend 15-day countdown logic and threshold triggers.

**Validation:** `allocation_remaining` cannot be negative. Mobile UI correctly renders negative cash in Red.

------------------------------------------------------------------------

# Phase 4: Site Operations Parity (Web CRM)
**Deliverables:**
-   Build Web CRM dashboards to consume `daily_progress_reports`, `worker_attendance`, and `voice_logs`.
-   Implement "Approve" workflow for Admin to verify Mobile-submitted data.
-   Ensure Approved status correctly cascades to Client views.

**Validation:** Supervisor submits DPR via Mobile → Admin sees DRAFT on Web → Admin Approves → Client sees APPROVED DPR.

------------------------------------------------------------------------

# Phase 5: Client Omnichannel Rollout & Reporting
**Deliverables:**
-   Implement Role-based routing in Next.js and Expo React Native.
-   Apply Read-Only CSS rules to hide all inputs/buttons when `role === 'Client'`.
-   Develop Reporting Engine (Tremor.so charts for Web, Victory/Recharts for Mobile).
-   Implement Puppeteer PDF Export and ExcelJS Template Export.

**Validation:** Client login correctly respects the `global_settings.client_permissions` matrix. Exported PDF layout exactly matches Excel grids.

------------------------------------------------------------------------

# Phase 6: Go-Live & Audit Validation
**Checklist Before Production:**
-   All invariants validated (No cross-category WO-PC mismatch, Ledger balance correctness).
-   Idempotency enforcement verified under simulated network failure.
-   MongoDB Replica Set deployed and transactions confirmed stable.
-   Immutable audit logs capture all Previous/New states.

------------------------------------------------------------------------
**End of Enterprise Implementation Plan -- Version 2.0 Final Locked**