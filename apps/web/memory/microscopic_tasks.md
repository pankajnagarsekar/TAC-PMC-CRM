# Microscopic Task Breakdown — TAC-PMC-CRM v2.0

> **Scope:** Backend (FastAPI) + Next.js Web CRM only. No mobile.
> **Executive Decisions Applied:** AG Grid Community, Python-native PDF (WeasyPrint), FastAPI BackgroundTasks, Vendor as CRUD, OCR audit+wire, Tremor.so charts.
> **Spec Source:** All 6 documents in `apps/web/memory/`

---

## PHASE 0: Monorepo Foundation & Database Hardening

### 0.1 — Shared Types Alignment (`packages/types`)

- [ ] **0.1.1** Add `Vendor` interface to `packages/types/src/index.ts` — fields: `_id`, `organisation_id`, `name`, `gstin`, `contact_person`, `phone`, `email`, `address`, `active_status`, `created_at`, `updated_at`
- [ ] **0.1.2** Add `VendorCreate` interface — fields: `name`, `gstin`, `contact_person`, `phone`, `email`, `address`
- [ ] **0.1.3** Add `VendorUpdate` interface — all fields optional
- [ ] **0.1.4** Update `Project` interface — add `client_id`, `master_original_budget`, `master_remaining_budget`, `threshold_petty`, `threshold_ovh`, `version` fields per DB Schema §2.2
- [ ] **0.1.5** Update `ProjectCreate` interface — add `client_id` (required), `threshold_petty`, `threshold_ovh` fields
- [ ] **0.1.6** Add `CashTransaction` interface — fields per DB Schema §4.2: `_id`, `project_id`, `category_id`, `amount`, `type` (`'DEBIT'|'CREDIT'`), `bill_reference`, `image_url`, `created_at`
- [ ] **0.1.7** Add `VendorLedgerEntry` interface — fields per DB Schema §4.3: `_id`, `vendor_id`, `project_id`, `ref_id`, `entry_type` (`'PC_CERTIFIED'|'PAYMENT_MADE'|'RETENTION_HELD'`), `amount`, `created_at`
- [ ] **0.1.8** Add `VoiceLog` interface — fields per DB Schema §5.3: `_id`, `project_id`, `supervisor_id`, `audio_url`, `transcribed_text`, `created_at`
- [ ] **0.1.9** Add `AuditLog` interface — fields per DB Schema §6.1: `_id`, `entity_name`, `entity_id`, `previous_state`, `new_state`, `action_type`, `user_id`, `created_at`
- [ ] **0.1.10** Add `OperationLog` interface — fields per DB Schema §6.2: `_id`, `operation_key`, `entity_type`, `created_at`
- [ ] **0.1.11** Verify all monetary fields in `WorkOrder`, `PaymentCertificate`, `ProjectBudget`, `FundAllocation`, `SiteOverhead` use `number` type (will render as `Decimal128` on backend) — confirm no `string` mismatches
- [ ] **0.1.12** Add `ProjectCategoryBudget` interface aligned to DB Schema §3.1 — fields: `_id`, `project_id`, `category_id`, `original_budget`, `committed_amount`, `remaining_budget`, `version`
- [ ] **0.1.13** Add `budget_type` field (`'commitment' | 'fund_transfer'`) to `CodeMaster` interface if not present (verify existing)

### 0.2 — Backend Model Hardening (`apps/api/models.py`)

- [ ] **0.2.1** Add `Vendor` Pydantic model with Decimal fields for any monetary amounts
- [ ] **0.2.2** Add `VendorCreate` Pydantic model
- [ ] **0.2.3** Add `VendorUpdate` Pydantic model
- [ ] **0.2.4** Add `CashTransaction` Pydantic model with `Decimal` for `amount`
- [ ] **0.2.5** Add `VendorLedgerEntry` Pydantic model — all monetary fields as `Decimal`
- [ ] **0.2.6** Add `VoiceLog` Pydantic model
- [ ] **0.2.7** Add `OperationLog` Pydantic model for idempotency tracking
- [ ] **0.2.8** Verify `WorkOrder` model uses `Decimal` for all monetary fields (`subtotal`, `discount`, `total_before_tax`, `cgst`, `sgst`, `grand_total`, `retention_percent`, `retention_amount`, `total_payable`, `actual_payable`, and all `line_items` `qty`, `rate`, `total`)
- [ ] **0.2.9** Verify `PaymentCertificate` model uses `Decimal` for all monetary fields
- [ ] **0.2.10** Add `version: int = 1` field to `WorkOrder`, `PaymentCertificate`, and `ProjectBudget` models for optimistic concurrency
- [ ] **0.2.11** Add `idempotency_key: Optional[str] = None` field to `PaymentCertificate` model
- [ ] **0.2.12** Add `status` field with enum validation (`Draft`, `Pending`, `Completed`, `Closed`, `Cancelled`) to `WorkOrder` and `PaymentCertificate` models if not enforced via literal types
- [ ] **0.2.13** Add `threshold_petty` and `threshold_ovh` Decimal fields to `Project` model
- [ ] **0.2.14** Add `master_original_budget` and `master_remaining_budget` Decimal fields to `Project` model
- [ ] **0.2.15** Add `client_id: str` field to `Project` model for client-project linking

### 0.3 — Database Transaction Infrastructure (`apps/api/core/`)

- [ ] **0.3.1** Verify `DatabaseManager.transaction_session()` works with MongoDB Replica Set (test context manager commit/rollback) — ✅ exists in `core/database.py`
- [ ] **0.3.2** Create `core/idempotency.py` — utility function `check_idempotency(session, operation_key)` that checks `operation_logs` collection and returns `True` if duplicate
- [ ] **0.3.3** Create `core/idempotency.py` — utility function `record_operation(session, operation_key, entity_type)` that inserts into `operation_logs`
- [ ] **0.3.4** Ensure MongoDB compound indexes exist: `project_id + category_id` on `project_category_budgets`, `work_orders`, `payment_certificates`, `cash_transactions`
- [ ] **0.3.5** Ensure MongoDB unique index on `work_orders.wo_ref`
- [ ] **0.3.6** Ensure MongoDB unique index on `operation_logs.operation_key`
- [ ] **0.3.7** Create `core/indexes.py` — startup function `ensure_indexes(db)` that creates all required indexes

### 0.4 — Financial Service Refactoring (`apps/api/financial_service.py`)

- [ ] **0.4.1** Refactor `recalculate_project_code_financials()` — currently aggregates from `petty_cash` collection, but per spec it should aggregate `committed_value` from `work_orders.grand_total` (Commitment Model) and `certified_value` from `payment_certificates.grand_total`
- [ ] **0.4.2** Add `recalculate_master_budget(project_id, session)` — sum all `project_category_budgets.original_budget` → update `projects.master_original_budget`; sum all `project_category_budgets.remaining_budget` → update `projects.master_remaining_budget`
- [ ] **0.4.3** Add `compute_cash_in_hand(project_id, category_id, session)` — sum all `cash_transactions` (CREDIT - DEBIT) for Fund-Transfer categories (Petty/OVH)
- [ ] **0.4.4** Add `check_threshold_breach(project_id, category_id)` — returns boolean if cash_in_hand ≤ threshold
- [ ] **0.4.5** Add `compute_15_day_countdown(project_id, category_id)` — calculates days since `fund_allocations.last_pc_closed_date`
- [ ] **0.4.6** Fix bug in `recalculate_all_project_financials()` — line 109 references `session=session` parameter but the method signature doesn't accept a `session` keyword argument

---

## PHASE 1: Web CRM Shell & Global Settings Completion

### 1.1 — Install & Configure AG Grid Community

- [ ] **1.1.1** Install `ag-grid-community` and `ag-grid-react` npm packages in `apps/web`
- [ ] **1.1.2** Create `apps/web/src/components/ui/FinancialGrid.tsx` — reusable wrapper component around `AgGridReact` with Tailwind theme classes
- [ ] **1.1.3** Configure AG Grid default column definitions: right-aligned numeric columns, 2-decimal currency formatter (`₹ X,XX,XXX.XX` Indian numbering), row auto-increment Sr No column
- [ ] **1.1.4** Implement keyboard navigation (Tab to next cell, Enter to confirm, Escape to cancel)
- [ ] **1.1.5** Implement inline cell validation: `Qty > 0`, `Rate ≥ 0`, `Total = Qty × Rate` row validation
- [ ] **1.1.6** Implement row-level validation status indicator (green/red border or icon)
- [ ] **1.1.7** Implement "Save blocked if any row invalid" logic — disable Save button and show error count
- [ ] **1.1.8** Abstract Enterprise features (copy-paste, range selection) behind a feature flag so Enterprise license can be dropped in later with zero refactor

### 1.2 — Install & Configure Tremor.so

- [ ] **1.2.1** Install `@tremor/react` npm package in `apps/web`
- [ ] **1.2.2** Verify Tremor.so Tailwind CSS compatibility with existing tailwind config
- [ ] **1.2.3** Create `apps/web/src/components/ui/KPICard.tsx` — reusable financial KPI card (value, label, trend indicator, color-coded status)
- [ ] **1.2.4** Create `apps/web/src/components/ui/FinancialChart.tsx` — reusable bar/line chart wrapper for budget vs. expenditure comparisons

### 1.3 — Global Settings Enhancements

- [ ] **1.3.1** Audit existing `admin/settings/page.tsx` — verify it has fields for: Company Name, Address, Email, Phone, GST Number, PAN, CGST%, SGST%, WO Prefix, PC Prefix, Invoice Prefix, Terms & Conditions, Currency, Currency Symbol
- [ ] **1.3.2** Add **Company Logo Upload** field with image preview (per PRD §5.7)
- [ ] **1.3.3** Add **Client Permissions Toggle Board** section — three toggle switches: `can_view_dpr`, `can_view_financials`, `can_view_reports` (per PRD §5.7, Frontend Spec §6)
- [ ] **1.3.4** Wire Client Permissions toggles to backend `PATCH /api/settings` endpoint — save to `global_settings.client_permissions`
- [ ] **1.3.5** Add backend route `GET /api/settings/client-permissions` to fetch just the client permissions matrix
- [ ] **1.3.6** Add backend route `PATCH /api/settings/client-permissions` to update just the client permissions matrix

### 1.4 — Project Context Enforcement Refinements

- [ ] **1.4.1** Audit existing `projectStore.ts` — verify project switch triggers full state purge (SWR cache clear, reset all Zustand stores except auth)
- [ ] **1.4.2** Implement `window.location.reload()` strategy on project switch (as per conversation history — full page reload for financial data integrity)
- [ ] **1.4.3** Verify all API calls in `lib/api.ts` inject `project_id` from project store into requests where required

### 1.5 — Sidebar Navigation Updates

- [ ] **1.5.1** Add "Work Orders" menu item in Sidebar (between Projects and Payment Certificates)
- [ ] **1.5.2** Add "Vendors" menu item in Sidebar
- [ ] **1.5.3** Add "Petty Cash" menu item in Sidebar
- [ ] **1.5.4** Add "Site Operations" menu item in Sidebar (group: DPRs, Attendance, Voice Logs)
- [ ] **1.5.5** Add "Reports" menu item in Sidebar
- [ ] **1.5.6** Ensure Sidebar dynamically hides items for Client role based on `client_permissions`

---

## PHASE 2: Core Financial Engine (Commitment Model)

### 2.1 — Vendor Management Module (Backend)

- [ ] **2.1.1** Create backend route `GET /api/vendors` — list all vendors for organisation
- [ ] **2.1.2** Create backend route `POST /api/vendors` — create vendor (Name, GSTIN, Contact Person, Phone, Email, Address)
- [ ] **2.1.3** Create backend route `GET /api/vendors/{vendor_id}` — get single vendor
- [ ] **2.1.4** Create backend route `PUT /api/vendors/{vendor_id}` — update vendor
- [ ] **2.1.5** Create backend route `DELETE /api/vendors/{vendor_id}` — soft-delete (set `active_status = false`); block deletion if vendor has associated WOs
- [ ] **2.1.6** Add audit logging on vendor create/update/delete

### 2.2 — Vendor Management Module (Frontend)

- [ ] **2.2.1** Create `apps/web/src/app/admin/vendors/page.tsx` — list page with table showing all vendors
- [ ] **2.2.2** Create `apps/web/src/components/vendors/VendorModal.tsx` — create/edit form with fields: Name, GSTIN, Contact Person, Phone, Email, Address
- [ ] **2.2.3** Wire API calls: list, create, update, delete
- [ ] **2.2.4** Add form validation: Name required, GSTIN format validation (15-char alphanumeric)
- [ ] **2.2.5** Add delete confirmation dialog with warning if vendor has associated WOs

### 2.3 — Category Budget Initialization Enhancement

- [ ] **2.3.1** Audit existing `initialize_project_budgets` endpoint in `hardened_routes.py` — verify it creates `project_category_budgets` with `original_budget`, `committed_amount` (default 0), `remaining_budget`
- [ ] **2.3.2** Ensure budget initialization uses `Decimal128("0")` for all monetary defaults
- [ ] **2.3.3** After budget init, auto-compute `projects.master_original_budget = SUM(original_budgets)` and `projects.master_remaining_budget = SUM(remaining_budgets)` using transaction
- [ ] **2.3.4** Add backend validation: `original_budget` cannot be reduced below `committed_amount` (Hard Constraint — Tech Arch §13)
- [ ] **2.3.5** Frontend: On Project Detail page (`admin/projects/[id]/page.tsx`), display budget table per category with "Original Budget" editable field and "Remaining" read-only field
- [ ] **2.3.6** Frontend: Show Master Budget (sum) and Master Remaining (sum) as prominent header KPI cards on Project Detail page
- [ ] **2.3.7** Frontend: "Initialize Budgets" button triggers `/api/hardened/projects/{id}/initialize-budgets`

### 2.4 — Work Order Module (Backend)

- [ ] **2.4.1** Create `apps/api/work_order_service.py` — WO business logic service class
- [ ] **2.4.2** Implement WO Create logic inside MongoDB transaction (Tech Arch §4.2 WO Save Flow):
  1. Check Idempotency-Key against `operation_logs`
  2. Validate single-category enforcement (1 WO = 1 Category)
  3. Validate vendor_id exists
  4. Server-side calculate: `subtotal = SUM(line_items.qty × line_items.rate)`, apply discount, calculate `total_before_tax`, `cgst`, `sgst`, `grand_total`, `retention_amount`, `total_payable`, `actual_payable`
  5. Deduct `grand_total` from `project_category_budgets.remaining_budget`
  6. Increment `project_category_budgets.committed_amount` by `grand_total`
  7. Update `projects.master_remaining_budget`
  8. Auto-generate unique `wo_ref` using `GlobalSettings.wo_prefix + sequence`
  9. Insert `work_orders` document
  10. Insert `audit_logs` document
  11. Record idempotency operation
  12. If budget goes negative → still save, but include `warning: "over_budget"` in response
- [ ] **2.4.3** Create backend route `POST /api/projects/{project_id}/work-orders` — calls WO Create
- [ ] **2.4.4** Create backend route `GET /api/projects/{project_id}/work-orders` — list WOs with pagination (cursor-based)
- [ ] **2.4.5** Create backend route `GET /api/work-orders/{wo_id}` — get single WO with all line items
- [ ] **2.4.6** Implement WO Update logic — within transaction:
  1. Cannot update if status is `Closed` or `Cancelled`
  2. Cannot reduce `grand_total` below sum of linked PCs (`SUM(payment_certificates.grand_total) WHERE work_order_id = wo_id`) — Lock Rule per PRD §5.2
  3. Reverse old budget deduction, apply new deduction
  4. Recalculate `committed_amount` and `remaining_budget`
  5. Update `master_remaining_budget`
  6. Audit log with previous/new state
- [ ] **2.4.7** Create backend route `PUT /api/work-orders/{wo_id}` — calls WO Update
- [ ] **2.4.8** Implement WO Status Transition enforcement (Tech Arch §6.1):
  - `Draft → Pending → Completed → Closed`
  - `Any → Cancelled` (only if no PCs exist)
  - Cannot skip states
  - Cannot revert from `Closed`
- [ ] **2.4.9** Create backend route `PATCH /api/work-orders/{wo_id}/status` — status transition
- [ ] **2.4.10** Implement WO Delete — only allowed if status is `Draft` and no PCs linked; reverse budget deduction within transaction

### 2.5 — Work Order Module (Frontend)

- [ ] **2.5.1** Create route `apps/web/src/app/admin/work-orders/page.tsx` — WO list page
- [ ] **2.5.2** Implement WO list table with columns: WO Ref, Category, Vendor, Grand Total (₹), Status, Date
- [ ] **2.5.3** Add status badge styling (Draft=gray, Pending=yellow, Completed=blue, Closed=green, Cancelled=red)
- [ ] **2.5.4** Create route `apps/web/src/app/admin/work-orders/new/page.tsx` — WO creation form
- [ ] **2.5.5** WO form header section: Category dropdown (single-select, enforced), Vendor dropdown (from Vendor CRUD), auto-generated WO Ref display
- [ ] **2.5.6** WO form grid section: AG Grid with columns — Sr No (auto), Description (text), Qty (number), Rate (currency), Total (calculated = Qty×Rate)
- [ ] **2.5.7** WO form: "Add Row" button to insert new line item
- [ ] **2.5.8** WO form: "Delete Row" button per row (with confirmation)
- [ ] **2.5.9** WO form footer section: Display Subtotal, Discount input, Total Before Tax, CGST (auto from settings), SGST (auto from settings), Grand Total, Retention % input, Retention Amount (calculated), Total Payable, Actual Payable
- [ ] **2.5.10** WO form: All footer values are display-only preview — actual calculation done by backend on save (Frontend Spec §3)
- [ ] **2.5.11** Implement pessimistic save: disable Save button → POST to API → on success, replace all displayed totals with backend authoritative values → show success toast
- [ ] **2.5.12** Implement over-budget warning: if response includes `warning: "over_budget"`, show amber alert modal (not blocking — PRD §6: warning only)
- [ ] **2.5.13** Create route `apps/web/src/app/admin/work-orders/[id]/page.tsx` — WO detail/edit view
- [ ] **2.5.14** WO detail: read-only mode for `Completed`/`Closed`/`Cancelled` statuses (row locking per Frontend Spec §4.1)
- [ ] **2.5.15** WO detail: show linked Payment Certificates list below the grid
- [ ] **2.5.16** Implement Idempotency-Key: generate UUID on form mount, include as `Idempotency-Key` header in save request, clear on success (Frontend Spec §8.2)

### 2.6 — Payment Certificate Module (Backend)

- [ ] **2.6.1** Create `apps/api/payment_certificate_service.py` — PC business logic service
- [x] **2.6.2** Implement PC Create (Mode A: WO-Linked) — within transaction:
  1. Check idempotency key
  2. Validate `work_order_id` exists and is not `Cancelled`
  3. Auto-derive `category_id` and `vendor_id` from the linked WO
  4. Server-side calculate: `subtotal`, `retention_amount`, `cgst`, `sgst`, `grand_total`
  5. Auto-generate `pc_ref` using `GlobalSettings.pc_prefix + sequence`
  6. Insert `payment_certificates` document
  7. Insert `vendor_ledger` entry: `entry_type = 'PC_CERTIFIED'`, `amount = grand_total`
  8. Audit log
  9. Record idempotency
- [ ] **2.6.3** Implement PC Create (Mode B: Petty/OVH Fund Request) — within transaction:
  1. `work_order_id` is null, `vendor_id` is null
  2. Validate `category_id` is a Petty Cash or OVH category (`budget_type = 'fund_transfer'`)
  3. Validate `fund_allocations.allocation_remaining > 0` (Hard Constraint — PRD §6: cannot raise if remaining = 0)
  4. Calculate totals server-side
  5. Insert PC tagged as `fund_request = true`
  6. No vendor ledger entry
  7. Audit log
- [ ] **2.6.4** Implement PC Close (WO-Linked) — within transaction:
  1. Update PC status to `Closed`
  2. Insert `vendor_ledger` entry: `entry_type = 'PAYMENT_MADE'`
  3. If retention: insert `vendor_ledger` entry: `entry_type = 'RETENTION_HELD'`
  4. Audit log
- [ ] **2.6.5** Implement PC Close (Petty/OVH) — within transaction (Tech Arch §PC Close):
  1. Update PC status to `Closed`
  2. Deduct `fund_allocations.allocation_remaining`
  3. Deduct `projects.master_remaining_budget`
  4. Insert `cash_transactions` entry: `type = 'CREDIT'` (funds received)
  5. Update `fund_allocations.last_pc_closed_date` to now
  6. Audit log
- [ ] **2.6.6** Refactor existing `create_payment_certificate` route in `server.py` to use new service
- [ ] **2.6.7** Create backend route `POST /api/projects/{project_id}/payment-certificates` — unified create with mode detection (if `work_order_id` provided → Mode A, else → Mode B)
- [x] **2.6.8** Create backend route `GET /api/projects/{project_id}/payment-certificates` — list with filters (by WO, by category, by status)
- [ ] **2.6.9** Create backend route `GET /api/payment-certificates/{pc_id}` — single PC detail
- [ ] **2.6.10** Create backend route `PATCH /api/payment-certificates/{pc_id}/close` — close PC
- [ ] **2.6.11** Implement PC Status Transitions: `Draft → Pending → Completed → Closed` (same as WO)

### 2.7 — Payment Certificate Module (Frontend)

- [x] **2.7.1** Refactor existing `admin/payment-certificates/page.tsx` — ensure it displays proper list with columns: PC Ref, WO Ref (or "Fund Request"), Category, Vendor, Grand Total, Status, Date
- [ ] **2.7.2** Create route `apps/web/src/app/admin/payment-certificates/new/page.tsx` — unified PC creation form
- [ ] **2.7.3** PC form: Mode selector — "WO-Linked" toggle at top. If checked, show WO Ref dropdown; if unchecked, show Category dropdown (Petty/OVH only)
- [ ] **2.7.4** PC form: When WO selected, auto-populate Category and Vendor (read-only)
- [ ] **2.7.5** PC form: AG Grid with columns — Sr No, Scope of Work (text), Rate (currency), Qty (number), Unit (text), Total (calculated)
- [ ] **2.7.6** PC form footer: Subtotal, Retention %, Retention Amount, Total Payable, CGST, SGST, Grand Total
- [ ] **2.7.7** Implement pessimistic save with idempotency key
- [x] **2.7.8** Create route `apps/web/src/app/admin/payment-certificates/[id]/page.tsx` — PC detail/edit view
- [ ] **2.7.9** Add "Close PC" button on PC detail page with confirmation dialog
- [ ] **2.7.10** After Close PC success, show updated Cash-in-Hand and Master Remaining values (response from backend)

### 2.8 — Vendor Ledger (Backend)

- [ ] **2.8.1** Vendor Ledger entries are auto-created by PC service (§2.6.2, §2.6.4, §2.6.5) — no manual create
- [x] **2.8.2** Create backend route `GET /api/projects/{project_id}/vendor-ledger` — list all ledger entries, filterable by `vendor_id`
- [ ] **2.8.3** Create backend route `GET /api/vendors/{vendor_id}/ledger` — ledger for a specific vendor across projects
- [x] **2.8.4** Create backend aggregation endpoint `GET /api/projects/{project_id}/vendor-payables` — sum vendor payable per vendor (total certified - total paid - total retention held)

### 2.9 — Version Conflict Handling (Cross-cutting)

- [x] **2.9.1** Backend: On every update to WO/PC/Budget, check `version` field matches — if mismatch, return `409 Conflict` with `error: "concurrency_conflict"` and include current server state in response
- [x] **2.9.2** Backend: On successful update, increment `version` by 1
- [x] **2.9.3** Frontend: Create `apps/web/src/components/ui/VersionConflictModal.tsx` — blocking modal per Frontend Spec §8.1: message "This record was updated by another session", "Reload" button to fetch latest state
- [x] **2.9.4** Frontend: Wire conflict modal into WO save, PC save, and Budget save flows — trigger on 409 response

---

## PHASE 3: Liquidity Engine (Fund-Transfer Model)

### 3.1 — Fund Allocation Backend

- [ ] **3.1.1** Ensure `fund_allocations` collection exists with schema per DB Schema §4.1
- [ ] **3.1.2** Auto-create `fund_allocations` entry when project budget is initialized for Petty Cash and OVH categories (`budget_type = 'fund_transfer'`) — `allocation_original = original_budget`, `allocation_remaining = original_budget`, `allocation_received = 0`
- [ ] **3.1.3** Create backend route `GET /api/projects/{project_id}/fund-allocations` — returns allocation status per fund-transfer category

### 3.2 — Petty Cash & OVH Expense Module (Backend)

- [ ] **3.2.1** Create `apps/api/cash_service.py` — cash transaction business logic
- [ ] **3.2.2** Implement "Record Expense" — within transaction:
  1. Insert `cash_transactions` entry: `type = 'DEBIT'`, `amount`, `bill_reference`, `image_url`
  2. Recalculate `cash_in_hand` for the category
  3. If `cash_in_hand ≤ threshold` → include `warning: "threshold_breach"` in response
  4. If `cash_in_hand < 0` → include `warning: "negative_cash"` in response
  5. Audit log
  6. Do NOT block on negative cash (PRD §2.2, §5.4)
- [ ] **3.2.3** Create backend route `POST /api/projects/{project_id}/cash-transactions` — record expense
- [ ] **3.2.4** Create backend route `GET /api/projects/{project_id}/cash-transactions` — list all transactions with pagination
- [ ] **3.2.5** Create backend route `GET /api/projects/{project_id}/cash-summary` — returns: `cash_in_hand`, `allocation_remaining`, `threshold`, `days_since_last_pc_close`, `threshold_breached` (boolean), `is_negative` (boolean)

### 3.3 — Petty Cash & OVH Module (Frontend — Web CRM)

- [ ] **3.3.1** Create route `apps/web/src/app/admin/petty-cash/page.tsx` — Petty Cash & OVH dashboard
- [ ] **3.3.2** Dashboard top section: Two Tremor.so KPI cards — "Petty Cash in Hand" and "OVH Cash in Hand" with color-coded values (Red if negative — `#EF4444`, Amber if ≤ threshold — `#F59E0B`, Green otherwise)
- [ ] **3.3.3** Dashboard: 15-day countdown timer per category — display days since last PC close. Color: Normal (0–10 days), Amber (11–14 days), Red (15+ days) per Frontend Spec §5.3
- [ ] **3.3.4** Implement client-side timer recalculation every 60 seconds (Frontend Spec §5.3)
- [ ] **3.3.5** Dashboard: Threshold alert banner — persistent Amber banner when cash ≤ threshold, with "Create PC" quick-link button (Frontend Spec §5.2)
- [ ] **3.3.6** Dashboard: Negative cash tooltip/modal explaining the negative state (Frontend Spec §5.1)
- [ ] **3.3.7** Create `apps/web/src/components/petty-cash/ExpenseEntryModal.tsx` — form with: Amount, Purpose, Bill/Invoice photo upload, Category selector (Petty/OVH)
- [ ] **3.3.8** Wire expense entry to `POST /api/projects/{project_id}/cash-transactions`
- [ ] **3.3.9** Show threshold/negative warnings from API response after expense save
- [ ] **3.3.10** Transaction history table below — columns: Date, Amount, Purpose, Bill Reference, Type (Debit/Credit), Running Balance

### 3.4 — OCR Integration for Petty Cash

- [ ] **3.4.1** Audit existing `admin/ocr/page.tsx` — document what it currently does
- [ ] **3.4.2** Audit existing backend OCR endpoint in `project_management_routes.py` (OCRBase64Request) — document input/output
- [ ] **3.4.3** Wire OCR into Expense Entry Modal: "Scan Invoice" button → captures/uploads image → calls OCR API → auto-fills Amount field from OCR response
- [ ] **3.4.4** Show OCR confidence score next to auto-filled amount; allow admin to override

---

## PHASE 4: Site Operations Parity (Web CRM)

### 4.1 — DPR Review Module (Backend)

- [ ] **4.1.1** Create/verify backend route `GET /api/projects/{project_id}/dprs` — list DPRs with status filter (`DRAFT`, `PENDING_APPROVAL`, `APPROVED`)
- [ ] **4.1.2** Create/verify backend route `GET /api/dprs/{dpr_id}` — get single DPR with photos and notes
- [ ] **4.1.3** Create backend route `PATCH /api/dprs/{dpr_id}/approve` — set status to `APPROVED`, set `approved_by` to current user ID, audit log
- [ ] **4.1.4** Create backend route `PATCH /api/dprs/{dpr_id}/reject` — set status to `REJECTED` with rejection reason
- [ ] **4.1.5** Ensure DPR list endpoint supports date range filtering

### 4.2 — DPR Review Module (Frontend)

- [ ] **4.2.1** Create route `apps/web/src/app/admin/site-operations/page.tsx` — Site Operations hub with tabs: DPRs, Attendance, Voice Logs
- [ ] **4.2.2** DPR Tab: List of DPRs with columns: Date, Supervisor, Status, # Photos, Notes preview
- [ ] **4.2.3** DPR Tab: Status filter (All / Draft / Pending / Approved)
- [ ] **4.2.4** Create route `apps/web/src/app/admin/site-operations/dprs/[id]/page.tsx` — DPR detail view
- [ ] **4.2.5** DPR detail: Photo gallery (lightbox viewer) showing all uploaded site photos per Frontend Spec §7
- [ ] **4.2.6** DPR detail: Notes section with progress deltas
- [ ] **4.2.7** DPR detail: Prominent "Approve" button (green) and "Reject" button (red) — only shown for DRAFT/PENDING status
- [ ] **4.2.8** DPR detail: After approval, show "Approved by [Admin Name] on [Date]" badge

### 4.3 — Worker Attendance Verification (Backend)

- [ ] **4.3.1** Create/verify backend route `GET /api/projects/{project_id}/attendance` — list attendance records with date filter
- [ ] **4.3.2** Create backend route `PATCH /api/attendance/{id}/verify` — set `verified_by_admin = true`

### 4.4 — Worker Attendance Verification (Frontend)

- [ ] **4.4.1** Attendance Tab: AG Grid table with columns: Worker Name, Date, Selfie (thumbnail), GPS Map Link (clickable "View on Maps"), Check-in Time, Verified (checkbox)
- [ ] **4.4.2** Selfie column: thumbnail image that opens in lightbox on click
- [ ] **4.4.3** GPS column: link opens Google Maps at `gps_lat, gps_lng` in new tab
- [ ] **4.4.4** "Verify" checkbox triggers `PATCH /api/attendance/{id}/verify`
- [ ] **4.4.5** Date range filter on attendance list

### 4.5 — Voice Logs Module (Backend)

- [ ] **4.5.1** Create/verify backend route `GET /api/projects/{project_id}/voice-logs` — list voice logs
- [ ] **4.5.2** Create/verify backend route `GET /api/voice-logs/{id}` — get single voice log with audio URL and transcription

### 4.6 — Voice Logs Module (Frontend)

- [ ] **4.6.1** Voice Logs Tab: list showing Date, Supervisor, Duration/Status, Transcription preview
- [ ] **4.6.2** Create `apps/web/src/components/site-operations/AudioPlayer.tsx` — custom HTML5 audio player per Frontend Spec §7
- [ ] **4.6.3** Voice Log detail: audio player component + text block displaying backend-transcribed text side by side

---

## PHASE 5: Client Portal & Reporting Engine

### 5.1 — Client Role Routing (Frontend)

- [ ] **5.1.1** Modify `Sidebar.tsx` — if JWT role is `Client`, fetch `GlobalSettings.client_permissions` and dynamically show/hide menu items per Frontend Spec §6.2
- [ ] **5.1.2** Modify `admin/layout.tsx` — if role is `Client`, apply read-only CSS class to entire layout wrapper
- [ ] **5.1.3** Create global CSS utility `.client-readonly` — hides all `button[type="submit"]`, disables all `input`, `select`, `textarea`, hides all `.admin-only` elements
- [ ] **5.1.4** Add `admin-only` class to all create/edit/delete buttons across all existing modules
- [ ] **5.1.5** Test: Client login → only permitted modules visible in sidebar → all inputs disabled → no save/delete buttons visible

### 5.2 — Reporting Engine (Backend)

- [ ] **5.2.1** Create `apps/api/reporting_service.py` — reporting aggregation service
- [ ] **5.2.2** Implement **Project Summary Report** — MongoDB aggregation pipeline: per-category budget, committed, certified, remaining; master totals; vendor payables summary
- [ ] **5.2.3** Implement **WO Tracker Report** — list all WOs with status rollup, total committed per category, linked PC count per WO
- [ ] **5.2.4** Implement **PC Tracker Report** — list all PCs with status, linked WO ref, amounts
- [ ] **5.2.5** Implement **Petty Cash/OVH Tracker** — cash transactions summary, cash-in-hand per category, allocation remaining
- [ ] **5.2.6** Implement **CSA Report** — filter to CSA category only, show budget vs committed vs certified
- [ ] **5.2.7** Implement **Date-Range filtered reports** — accept `start_date`, `end_date` query params; filter by `created_at`
- [ ] **5.2.8** Create backend route `GET /api/projects/{project_id}/reports/{report_type}` — returns JSON data for each report type
- [ ] **5.2.9** All report aggregations computed from MongoDB — zero frontend aggregation per Tech Arch §9

### 5.3 — Reporting Engine (Frontend)

- [ ] **5.3.1** Create route `apps/web/src/app/admin/reports/page.tsx` — Reports hub
- [ ] **5.3.2** Report selector: dropdown with report types (Project Summary, WO Tracker, PC Tracker, Petty/OVH Tracker, CSA Report)
- [ ] **5.3.3** Date range filter: start date, end date pickers
- [ ] **5.3.4** "Generate Report" button → calls backend report endpoint → renders results
- [ ] **5.3.5** Render **Project Summary** report using Tremor.so: budget vs committed bar chart, category breakdown table, master totals KPI cards
- [ ] **5.3.6** Render **WO Tracker** report: table + status distribution donut chart
- [ ] **5.3.7** Render **PC Tracker** report: table + amounts bar chart
- [ ] **5.3.8** Render **Petty/OVH Tracker**: transactions table + cash-in-hand trend line chart
- [ ] **5.3.9** Render **CSA Report**: budget vs actual bar chart + detailed table

### 5.4 — Dashboard Enhancement

- [ ] **5.4.1** Refactor existing `admin/dashboard/page.tsx` to use Tremor.so components
- [ ] **5.4.2** Add KPI cards: Master Budget, Master Remaining, Total Committed, Total Certified (per PRD §5.6)
- [ ] **5.4.3** Add "Vendor Payables" summary card — total outstanding across all vendors
- [ ] **5.4.4** Add "Petty Cash Status" card — cash-in-hand value with color coding
- [ ] **5.4.5** Add "OVH Status" card — cash-in-hand value with color coding
- [ ] **5.4.6** Add "15-Day Countdown" widgets — one for Petty, one for OVH, with day count and color
- [ ] **5.4.7** Add "Over-Budget Alerts" section — list categories where `committed_amount > original_budget`
- [ ] **5.4.8** Add "Budget vs Committed" bar chart (Tremor.so BarChart)
- [ ] **5.4.9** Add "WO Status Distribution" donut chart (Tremor.so DonutChart)

### 5.5 — Excel Export (Backend — openpyxl)

> **Note:** Since backend is Python, using `openpyxl` instead of ExcelJS (Node.js library). Same template-filling approach.

- [ ] **5.5.1** Install `openpyxl` in `apps/api/requirements.txt`
- [ ] **5.5.2** Create `apps/api/export_service.py` — export engine
- [ ] **5.5.3** Create Excel template file `apps/api/templates/project_summary.xlsx` based on `majorda templates.xlsx` reference
- [ ] **5.5.4** Implement Project Summary Excel export — fill template with data from report aggregation, enforce column positions, formula ranges, protected calculated cells per Tech Arch §10.1
- [ ] **5.5.5** Create WO Detail Excel export template and implementation
- [ ] **5.5.6** Create PC Detail Excel export template and implementation
- [ ] **5.5.7** Create backend route `GET /api/projects/{project_id}/reports/{report_type}/export/excel` — returns downloadable `.xlsx` file
- [ ] **5.5.8** Run export via `FastAPI BackgroundTasks` if report is heavy; return `202 Accepted` with job ID; poll for completion

### 5.6 — PDF Export (Backend — WeasyPrint)

- [ ] **5.6.1** Install `weasyprint` in `apps/api/requirements.txt`
- [ ] **5.6.2** Create `apps/api/templates/report_pdf.html` — Jinja2 HTML template styled with CSS to mirror Excel layout per Tech Arch §10.2
- [ ] **5.6.3** Include company logo placeholder, letterhead styling, and header section in template
- [ ] **5.6.4** Include Terms & Conditions auto-append on final page per Tech Arch §10.2 (use `GlobalSettings.terms_and_conditions`)
- [ ] **5.6.5** Implement PDF generation function: populate Jinja2 template → render with WeasyPrint → return bytes
- [ ] **5.6.6** Create backend route `GET /api/projects/{project_id}/reports/{report_type}/export/pdf` — returns downloadable `.pdf` file
- [ ] **5.6.7** Run via `FastAPI BackgroundTasks` for heavy reports; target < 5s per Tech Arch §14
- [ ] **5.6.8** Create standalone WO PDF export: `GET /api/work-orders/{wo_id}/export/pdf`
- [ ] **5.6.9** Create standalone PC PDF export: `GET /api/payment-certificates/{pc_id}/export/pdf`

### 5.7 — Export Integration (Frontend)

- [ ] **5.7.1** Add "Export to Excel" button on Reports page — triggers Excel download
- [ ] **5.7.2** Add "Export to PDF" button on Reports page — triggers PDF download
- [x] **5.7.3** Add "Export PDF" button on individual WO detail page
- [x] **5.7.4** Add "Export PDF" button on individual PC detail page
- [x] **5.7.5** For Client role: prominent "Export to PDF" button on all visible screens per Frontend Spec §6.5
- [x] **5.7.6** Handle async exports: show "Generating…" spinner, poll for completion, auto-download when ready

---

## PHASE 6: Go-Live Hardening & Cross-Cutting Concerns

### 6.1 — Audit System Verification

- [x] **6.1.1** Verify `audit_logs` is append-only — ensure no update/delete operations exist on this collection anywhere in the codebase
- [x] **6.1.2** Verify audit logs capture `previous_state` and `new_state` as full JSON snapshots for all: WO create/update/delete, PC create/close, Budget modify, Cash transaction, Vendor create/update
- [x] **6.1.3** Create backend route `GET /api/audit-logs` — query audit logs with filters: `entity_name`, `entity_id`, `action_type`, `date_range`, `user_id`
- [x] **6.1.4** Create `apps/web/src/app/admin/audit-log/page.tsx` — admin-accessible audit trail viewer

### 6.2 — Error Handling UX (Frontend — Cross-cutting)

- [x] **6.2.1** Create `apps/web/src/components/ui/ErrorBoundary.tsx` — React error boundary with user-friendly fallback
- [x] **6.2.2** Create `apps/web/src/components/ui/NetworkErrorRetry.tsx` — retry banner component for network failures per Frontend Spec §8.2
- [x] **6.2.3** Create `apps/web/src/lib/idempotency.ts` — utility to generate UUID, track in-flight requests, prevent duplicate submissions
- [x] **6.2.4** Implement request locking: if a financial save is in-flight, subsequent clicks are silently blocked (Frontend Spec §8.2)
- [x] **6.2.5** Create `apps/web/src/lib/errorLogger.ts` — client-side error logger (non-sensitive data only per Frontend Spec §8.2)
- [x] **6.2.6** Wire field-specific validation errors from backend 400/422 responses into form field error messages

### 6.3 — Security Hardening

- [x] **6.3.1** Verify rate limiting on financial endpoints (`/work-orders`, `/payment-certificates`, `/cash-transactions`) per Tech Arch §12.1
- [x] **6.3.2** Verify all backend routes have `Depends(get_current_user)` authentication
- [x] **6.3.3** Verify role-based middleware: Admin can access all routes; Client cannot access create/update/delete; Supervisor blocked from Web CRM routes
- [x] **6.3.4** Verify Pydantic v2 input validation on all create/update models — no raw data passes through

### 6.4 — Data Validation Layer (Backend)

- [x] **6.4.1** Before WO save: validate `SUM(line_items.qty × rate)` equals submitted `subtotal` per Tech Arch §12.2 — reject with `400` if mismatch
- [x] **6.4.2** Before WO save: validate Retention and GST calculations match mathematical expectations
- [x] **6.4.3** Before WO save: validate `category_id` exists and is valid for the project
- [x] **6.4.4** Before PC save: same validation as WO
- [x] **6.4.5** Before Budget update: validate `new amount ≥ committed_amount` — reject if downward edit goes below committed

### 6.5 — Performance Optimization

- [x] **6.5.1** Verify compound indexes on `project_id + category_id` for all financial collections
- [x] **6.5.2** Implement cursor-based pagination on all list endpoints (Tech Arch §11)
- [x] **6.5.3** Target benchmarks: WO Save < 200ms, PC Close < 200ms, Petty Entry < 100ms, Report gen < 2s (Tech Arch §14)

---

## PHASE 7: Source-Alignment Addendum (Missing Tasks)

### 7.1 — Core Module Completeness (Web + Backend)

- [x] **7.1.1** Implement explicit Clients CRUD module (backend routes + Web CRM pages/forms) per PRD §5.1
- [x] **7.1.2** Verify/complete Projects CRUD module end-to-end (backend + Web CRM) with `client_id` linkage and threshold fields
- [x] **7.1.3** Add audit coverage for Client and Project create/update/delete flows

### 7.2 — Category Governance & Global Settings

- [x] **7.2.1** Add Category Master management UI in Global Settings (create/update/soft-delete category metadata)
- [x] **7.2.2** Add backend endpoints for Category Master CRUD with validation for unique `code` and name
- [x] **7.2.3** Enforce hard constraint: cannot delete category if referenced by any `project_category_budgets`, WO, or PC (Tech Arch §13)

### 7.3 — Reporting Variants & Template Parity

- [x] **7.3.1** Add backend report variant `weekly-progress` (last 7 days window) aligned with template expectations
- [x] **7.3.2** Add backend report variant `15-days-progress` (rolling 15-day window)
- [x] **7.3.3** Add backend report variant `monthly-progress` (calendar month grouping + totals)
- [x] **7.3.4** Add frontend report selector options and renderers for Weekly, 15 Days, and Monthly reports
- [x] **7.3.5** Create additional Excel templates in `apps/api/templates/` aligned to `majorda templates.xlsx`: `weekly_progress.xlsx`, `work_order_tracker.xlsx`, `payment_certificate_tracker.xlsx`, `petty_cash_tracker.xlsx`, `csa_tracker.xlsx`
- [x] **7.3.6** Wire export endpoint routing so each report type maps to its corresponding template and sheet structure

### 7.4 — Heavy-Job Infrastructure (Architecture Compliance)

- [x] **7.4.1** Add async worker stack for heavy jobs (Celery + Redis) as optional production mode for report export and OCR pipelines (Tech Arch §10, §11)
- [x] **7.4.2** Add job orchestration abstraction so runtime can switch between `FastAPI BackgroundTasks` and queue worker without endpoint contract changes
- [x] **7.4.3** Add report pre-aggregation strategy for heavy queries (MongoDB `$merge`/materialized outputs) with scheduled refresh hooks (Tech Arch §9)

### 7.5 — Financial Determinism & Idempotency Contracts

- [x] **7.5.1** Implement explicit Round-Half-Up monetary rounding helper in backend financial service layer and use it in WO/PC totals (Tech Arch §3.1)
- [x] **7.5.2** Add unit tests validating Round-Half-Up behavior for edge decimals and tax/retention calculations
- [x] **7.5.3** Extend idempotency flow to persist serialized prior response for critical operations (WO save, PC close, cash expense)
- [x] **7.5.4** On duplicate `Idempotency-Key`, return `200 OK` with previously stored authoritative response payload (Tech Arch §5)

### 7.6 — Security Session Model Completion

- [x] **7.6.1** Implement refresh-token flow with HTTP-only cookie strategy and short-lived access tokens (Tech Arch §12.1)
- [x] **7.6.2** Add token rotation + revocation checks for logout and compromised-session handling

### 7.7 — Omnichannel Mobile Parity Backlog (Tracked, Not in Current Web-Only Scope)

- [x] **7.7.1** Implement Admin Mobile Petty Cash/OVH specialized UI (negative cash red state, threshold banner, correct project-scoped API)
- [x] **7.7.2** Implement Mobile Client Dashboard routing + permissions parity aligned to `global_settings.client_permissions`
- [x] **7.7.3** Implement Mobile report rendering parity (Weekly/15-Day/Monthly + PDF export & share access)
  - Add Report Selector on Mobile Client Dashboard (if reports permission enabled)
  - Add backend-driven report list for mobile view
  - Implement "Email PDF Report" button on mobile for Weekly/15-Day/Monthly variants
  - Support mobile-friendly list rendering of Progress Reports

---

## PHASE 8: Gap Remediation Backlog (Audit-Driven)

### 8.1 â€” Phase 0 Remediation (Foundation & Financial Core)

- [x] **8.1.1** Refactor `financial_service.recalculate_project_code_financials()` to aggregate commitment model data from `work_orders.grand_total` and certification data from `payment_certificates.grand_total` (remove legacy `petty_cash` aggregation path)
- [x] **8.1.2** Fix `recalculate_all_project_financials()` signature and call sites to consistently accept optional `session` and execute inside active transactions where applicable
- [x] **8.1.3** Standardize collection and field naming across financial modules (`project_category_budgets` + `category_id`) and remove mixed legacy usage (`project_budgets` + `code_id`) in core flows
- [x] **8.1.4** Fix missing runtime imports and typing defects in hardened financial routes (`Decimal`, `Decimal128`, and required model imports) and add startup smoke test for those routes
- [x] **8.1.5** Resolve duplicate/conflicting shared type declarations (e.g., duplicate `FundAllocation` interfaces) in `packages/types/src/index.ts`

### 8.2 â€” Phase 1 Remediation (Web Shell & Global Settings)

- [x] **8.2.1** Expand Global Settings UI to include full required fields (company profile block, prefixes, and logo upload with preview) and persist all values through backend
- [x] **8.2.2** Add dedicated backend endpoints `GET /api/settings/client-permissions` and `PATCH /api/settings/client-permissions` and wire Settings page to use them for permission-board updates
- [x] **8.2.3** Replace broad client CSS hide strategy with explicit `.client-readonly` + `.admin-only` enforcement pattern and validate all create/edit/delete actions are correctly classified

### 8.3 â€” Phase 2 Remediation (Commitment Engine)

- [x] **8.3.1** Add missing Work Order endpoints: `PUT /api/work-orders/{wo_id}` (full update) and guarded delete flow per lock rules
- [x] **8.3.2** Enforce full WO status state machine (no skipped transitions, no invalid reversions, cancellation constraints) at service layer
- [x] **8.3.3** Add linked Payment Certificate listing on WO detail page and load it from backend relation query
- [x] **8.3.4** Fix PC idempotency duplicate behavior to return deterministic prior-success response contract (not hard failure) and align with transaction-safe replay model
- [x] **8.3.5** Resolve route contract mismatch for WO listing by project (`/api/projects/{project_id}/work-orders` vs current usage) by choosing one canonical API shape and aligning backend + frontend
- [x] **8.3.6** Complete optimistic concurrency UX for budget edits: send `version`, handle `409 concurrency_conflict`, and show `VersionConflictModal` in project budget save flow

### 8.4 â€” Phase 3 Remediation (Liquidity Engine)

- [x] **8.4.1** Update cash expense business logic to allow negative cash-in-hand and return warning flags instead of blocking save when balance goes below zero
- [x] **8.4.2** Add backend endpoint `GET /api/projects/{project_id}/cash-summary` with required response shape (`cash_in_hand`, `allocation_remaining`, `threshold`, `days_since_last_pc_close`, flags)
- [x] **8.4.3** Implement threshold-breach and negative-cash UX in petty cash pages (persistent amber banner, red negative state, explanatory helper)
- [x] **8.4.4** Wire OCR output into petty expense entry flow (scan/upload -> autofill amount + confidence + manual override) instead of isolated OCR-only workflow

### 8.5 â€” Phase 4 Remediation (Site Operations Parity)

- [x] **8.5.1** Align DPR status vocabulary and transitions with locked spec states across backend and frontend filters/badges
- [x] **8.5.2** Normalize Site Operations route contracts to canonical endpoints expected by task spec and remove path-shape drift between modules

### 8.6 â€” Phase 5 Remediation (Reporting & Export)

- [x] **8.6.1** Implement report-type endpoint contract `GET /api/projects/{project_id}/reports/{report_type}` with supported types from microscopic tasks
- [x] **8.6.2** Build template-driven export service layer (`export_service.py`) and migrate current ad-hoc export generation to template mapping
- [x] **8.6.3** Add missing export endpoints: `.../export/excel`, `.../export/pdf`, plus standalone WO/PC PDF export routes
- [x] **8.6.4** Create and version report templates under `apps/api/templates/` and align field injection with approved workbook/PDF layout structure
- [x] **8.6.5** Update Reports UI to support full report selector, backend report generation contract, and async export lifecycle states (generate/poll/download)

### 8.7 â€” Phase 6 Remediation (Hardening)

- [x] **8.7.1** Create Audit Log viewer screen at `apps/web/src/app/admin/audit-log/page.tsx` and wire filters to backend `GET /api/audit-logs`
- [x] **8.7.2** Add missing frontend resilience utilities/components: `NetworkErrorRetry.tsx`, `lib/idempotency.ts`, and `lib/errorLogger.ts`
- [x] **8.7.3** Implement rate limiting on financial write endpoints (`work-orders`, `payment-certificates`, `cash-transactions`) and add integration tests
- [x] **8.7.4** Upgrade list endpoints to cursor-based pagination where microscopic tasks require it and align frontend pagination clients
- [x] **8.7.5** Add strict pre-save financial validation layer coverage (line-item sum parity, GST/retention correctness, category validity, budget floor checks) with automated tests

---

## PHASE 9: Audit Delta Remediation (Code + Task Reconciliation)

### 9.1 — Backend Contract & Runtime Fixes

- [x] **9.1.1** Fix `payment_certificate_service.py` runtime defect: import `Decimal` and compute PC line-item totals from dict payloads safely
- [x] **9.1.2** Fix ObjectId lookup handling in PC create flow for `work_order_id` and `category_id` fetches
- [x] **9.1.3** Add canonical project-scoped WO routes: `GET /api/projects/{project_id}/work-orders` and `POST /api/projects/{project_id}/work-orders`
- [x] **9.1.4** Register project-scoped WO router in `server.py`
- [x] **9.1.5** Fix missing `ObjectId` import in `financial_service.py` used by `recalculate_master_budget()`

### 9.2 — Settings & Permission Consistency

- [x] **9.2.1** Unify `settings_routes.py` persistence to `global_settings` (remove `db.settings` drift for settings + client permissions)
- [x] **9.2.2** Wire Settings page save/load to dedicated `GET/PATCH /api/settings/client-permissions` endpoints
- [x] **9.2.3** Fix client-readonly enforcement: attach `is-client` class to `body` and apply selective readonly CSS in admin layout content area

### 9.3 — Reporting Export Async Lifecycle

- [x] **9.3.1** Add `sync` query flag to Excel export endpoint to support deterministic post-job download
- [x] **9.3.2** Update Reports page export flow: detect async `job_id` response, poll `/api/jobs/{job_id}`, then download via sync export

### 9.4 — Remaining Structural Cleanup (Not Yet Remediated)

- [x] **9.4.1** Deduplicate conflicting legacy endpoints in `server.py` (`/projects`, `/codes`, etc.) and keep one canonical implementation per route
- [x] **9.4.2** Standardize financial collection schema usage to one model (`project_category_budgets + category_id`) across services/indexes
- [x] **9.4.3** Remove duplicate model declarations in `apps/api/models.py` (`CashTransaction`, `FundAllocation`) and align single authoritative shape
- [x] **9.4.4** Complete `admin-only` class tagging across all create/edit/delete actions for strict client-role UI hardening

---

## TASK STATISTICS

| Phase     | Task Count |
| --------- | ---------- |
| Phase 0   | 41         |
| Phase 1   | 27         |
| Phase 2   | 73         |
| Phase 3   | 22         |
| Phase 4   | 25         |
| Phase 5   | 55         |
| Phase 6   | 22         |
| Phase 7   | 25         |
| Phase 8   | 30         |
| Phase 9   | 14         |
| **TOTAL** | **333**    |

---

> **Reconciliation complete. Ready for execution.**
