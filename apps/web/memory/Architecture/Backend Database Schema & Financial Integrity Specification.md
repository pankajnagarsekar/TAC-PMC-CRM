# Backend Database Schema & Financial Integrity Specification

## CRM Financial Management System — Version 3.0 (MongoDB Edition)

**Document 5 of 6 — Single Source of Truth**
**Last Updated:** 21 March 2026 (reconciled against live `apps/api/models.py`, route files, and service files)

---

# 1. Core Engineering Standards

| Property | Value |
|---|---|
| Database | MongoDB 5.0+ with Replica Set (required for transactions) |
| Transaction Level | Multi-Document ACID Sessions (Motor async sessions) |
| Monetary Type | `Decimal128` (BSON) on disk; `Decimal` (Python) in-process |
| Primary Keys | `ObjectId` (`_id`) |
| String IDs | All cross-collection references stored as `str`, not `ObjectId` |
| All financial writes | Atomic, idempotent, audited |
| Multi-tenancy | All collections (except `sequences`, `token_blacklist`) scoped by `organisation_id` |
| Async Driver | `motor==3.3.1` (AsyncIOMotorClient) |
| Validation Layer | Pydantic v2 (`models.py`) |

System supports: Commitment Model, Liquidity Model, Warning-only over-budget, Negative cash-in-hand, per-project financial isolation.

---

# 2. IDENTITY & AUTHENTICATION COLLECTIONS

## 2.1 `organisations`
```
{
  _id:          ObjectId,
  name:         String,
  created_at:   Date
}
```

## 2.2 `users`
```
{
  _id:                      ObjectId,
  organisation_id:          String,
  name:                     String,
  email:                    String (unique per org),
  hashed_password:          String (bcrypt),
  role:                     String  -- 'Admin' | 'Supervisor' | 'Other',
  active_status:            Boolean (default: true),
  dpr_generation_permission: Boolean (default: false),
  assigned_projects:        [String],   -- project_id list
  screen_permissions:       [String],   -- permission key list
  created_at:               Date,
  updated_at:               Date
}
```
*Note:* `user_id` used in JWT and cross-collection references is the string form of `_id`.

## 2.3 `user_project_map`
```
{
  _id:          ObjectId,
  user_id:      String,
  project_id:   String,
  created_at:   Date
}
```

## 2.4 `refresh_tokens`
```
{
  _id:          ObjectId,
  jti:          String (JWT ID, unique),
  user_id:      String,
  token_hash:   String (bcrypt hash of token),
  expires_at:   Date,
  is_revoked:   Boolean (default: false),
  revoked_at:   Date (nullable),
  created_at:   Date
}
```

## 2.5 `token_blacklist`
```
{
  _id:          ObjectId,
  jti:          String (JWT ID, unique),
  token_type:   String  -- 'access' | 'refresh',
  revoked_at:   Date
}
```
*Rule:* Append-only. Checked on every authenticated request.
*Access tokens:* 30-minute expiry. *Refresh tokens:* 7-day expiry.

---

# 3. MASTER / CONFIGURATION COLLECTIONS

## 3.1 `clients`
```
{
  _id:              ObjectId,
  organisation_id:  String,
  name:             String,
  address:          String (nullable),
  phone:            String (nullable),
  email:            String (nullable),
  gstin:            String (nullable),
  created_at:       Date,
  updated_at:       Date
}
```

## 3.2 `projects`
```
{
  _id:                          ObjectId,
  organisation_id:              String,
  project_name:                 String,
  client_id:                    String (nullable, ref: clients._id),
  project_code:                 String (nullable, unique per org),
  status:                       String  -- 'active' | 'inactive' | 'completed',
  address:                      String (nullable),
  city:                         String (nullable),
  state:                        String (nullable),
  project_retention_percentage: Decimal128 (0–100, default: 0.0),
  project_cgst_percentage:      Decimal128 (0–100, default: 9.0),
  project_sgst_percentage:      Decimal128 (0–100, default: 9.0),
  completion_percentage:        Decimal128 (0–100, default: 0.0),
  master_original_budget:       Decimal128 (default: 0.0),
  master_remaining_budget:      Decimal128 (default: 0.0),
  threshold_petty:              Decimal128 (default: 0.0),
  threshold_ovh:                Decimal128 (default: 0.0),
  version:                      Int (optimistic lock),
  created_at:                   Date,
  updated_at:                   Date
}
```
*Note:* Field is `project_name` (not `name`). `threshold_petty` / `threshold_ovh` are alert thresholds for cash-in-hand warnings.

## 3.3 `code_master`
> Previously misnamed `categories` in older spec versions.

```
{
  _id:              ObjectId,
  organisation_id:  String (nullable — system codes may be org-agnostic),
  category_name:    String (nullable),
  code:             String (nullable),
  code_short:       String (legacy alias for `code`, default: ""),
  code_description: String (legacy alias for `category_name`, default: ""),
  budget_type:      String  -- 'commitment' | 'fund_transfer',
  active_status:    Boolean (default: true),
  created_at:       Date,
  updated_at:       Date
}
```
*Rule:* `budget_type = 'commitment'` → tracked in `work_orders` / `payment_certificates`.
`budget_type = 'fund_transfer'` → tracked in `fund_allocations` / `cash_transactions`.

## 3.4 `vendors`
```
{
  _id:              ObjectId,
  organisation_id:  String,
  name:             String,
  gstin:            String (nullable),
  contact_person:   String (nullable),
  phone:            String (nullable),
  email:            String (nullable),
  address:          String (nullable),
  active_status:    Boolean (default: true),
  created_at:       Date,
  updated_at:       Date
}
```
Index: `(organisation_id, active_status)`.

## 3.5 `global_settings`
> One document per organisation. Fields are flat (not nested).

```
{
  _id:                 ObjectId,
  organisation_id:     String (unique),
  name:                String (company name, default: ""),
  address:             String (default: ""),
  email:               String (default: ""),
  phone:               String (default: ""),
  gst_number:          String (default: ""),
  pan_number:          String (default: ""),
  cgst_percentage:     Decimal128 (0–100, default: 9.0),
  sgst_percentage:     Decimal128 (0–100, default: 9.0),
  retention_percentage: Decimal128 (0–100, default: 5.0),
  wo_prefix:           String (default: "WO"),
  pc_prefix:           String (default: "PC"),
  invoice_prefix:      String (default: "INV"),
  terms_and_conditions: String (default: "Standard terms and conditions apply."),
  currency:            String (default: "INR"),
  currency_symbol:     String (default: "₹"),
  client_permissions: {
    can_view_dpr:        Boolean (default: true),
    can_view_financials: Boolean (default: false),
    can_view_reports:    Boolean (default: true)
  },
  updated_at:          Date
}
```
*Note:* `wo_prefix` and `pc_prefix` are used to format `WO-{seq}` / `PC-{seq}` reference numbers via the `sequences` collection.

---

# 4. FINANCIAL COLLECTIONS

## 4.1 `project_category_budgets`
```
{
  _id:              ObjectId,
  project_id:       String,
  category_id:      String (ref: code_master._id),
  original_budget:  Decimal128 (>= 0),
  committed_amount: Decimal128 (default: 0.0, >= 0),
  remaining_budget: Decimal128 (default: 0.0, >= 0),
  description:      String (nullable),
  version:          Int (optimistic lock),
  created_at:       Date,
  updated_at:       Date
}
```
*Rule:* `original_budget` cannot be reduced below `committed_amount`.
*Rule:* `remaining_budget = original_budget − committed_amount`.
*Unique index:* `(project_id, category_id)`.

## 4.2 `work_orders`
```
{
  _id:               ObjectId,
  organisation_id:   String (nullable),
  project_id:        String,
  category_id:       String (ref: code_master._id),
  vendor_id:         String (nullable, ref: vendors._id),
  wo_ref:            String (unique, format: "{wo_prefix}-{seq}"),
  subtotal:          Decimal128 (>= 0),
  discount:          Decimal128 (>= 0),
  total_before_tax:  Decimal128 (>= 0),
  cgst:              Decimal128 (>= 0),
  sgst:              Decimal128 (>= 0),
  grand_total:       Decimal128 (>= 0),
  retention_percent: Decimal128 (0–100),
  retention_amount:  Decimal128 (>= 0),
  total_payable:     Decimal128 (>= 0),
  actual_payable:    Decimal128 (>= 0),
  status:            String  -- 'Draft' | 'Pending' | 'Completed' | 'Closed' | 'Cancelled',
  line_items: [{
    sr_no:       Int,
    description: String,
    qty:         Decimal128,
    rate:        Decimal128,
    total:       Decimal128
  }],
  version:           Int (optimistic lock),
  created_at:        Date,
  updated_at:        Date
}
```
*Financial formula:*
- `total_before_tax = subtotal − discount`
- `cgst = total_before_tax × cgst%`
- `sgst = total_before_tax × sgst%`
- `grand_total = total_before_tax + cgst + sgst`
- `retention_amount = grand_total × retention_percent`
- `total_payable = grand_total − retention_amount`
- `actual_payable = total_payable` (net after retention)

*Indexes:* `(project_id, category_id)`, `(wo_ref)` unique, `(project_id, status)`.

*Lifecycle:* On WO creation → `committed_amount` in `project_category_budgets` is increased by `grand_total`. On WO cancellation → `committed_amount` is decreased.

## 4.3 `payment_certificates`
```
{
  _id:               ObjectId,
  organisation_id:   String (nullable),
  project_id:        String,
  work_order_id:     String (nullable, ref: work_orders._id),
  category_id:       String (nullable, ref: code_master._id),
  vendor_id:         String (nullable, ref: vendors._id),
  pc_ref:            String (format: "{pc_prefix}-{seq}"),
  subtotal:          Decimal128 (>= 0),
  retention_percent: Decimal128 (0–100),
  retention_amount:  Decimal128 (>= 0),
  total_payable:     Decimal128 (>= 0),
  cgst:              Decimal128 (>= 0),
  sgst:              Decimal128 (>= 0),
  grand_total:       Decimal128 (>= 0),
  gst_amount:        Decimal128 (>= 0),
  fund_request:      Boolean (default: false),
  status:            String  -- 'Draft' | 'Pending' | 'Completed' | 'Closed' | 'Cancelled',
  line_items: [{
    sr_no:         Int,
    scope_of_work: String,
    qty:           Decimal128,
    rate:          Decimal128,
    unit:          String,
    total:         Decimal128
  }],
  idempotency_key:   String (nullable, unique),
  version:           Int,
  -- Legacy / OCR-created PC fields:
  vendor_name:       String (nullable),
  invoice_number:    String (nullable),
  date:              String (nullable),
  amount:            Decimal128 (nullable),
  total_amount:      Decimal128 (nullable),
  ocr_id:            String (nullable),
  created_at:        Date
}
```
*Note:* PC `line_items` use `scope_of_work` (not `description` like WO line items) and include a `unit` field.
*Note:* `fund_request: true` indicates this PC is a fund-draw against petty/OVH allocation.
*Indexes:* `(project_id, category_id)`, `(project_id, work_order_id)`.

## 4.4 `financial_state` (Derived / Computed)
```
{
  _id:                    ObjectId,
  project_id:             String,
  code_id:                String (ref: code_master._id),
  original_budget:        Decimal128 (default: 0.0),
  committed_value:        Decimal128 (default: 0.0),
  certified_value:        Decimal128 (default: 0.0),
  balance_budget_remaining: Decimal128 (default: 0.0),
  over_commit_flag:       Boolean (default: false),
  last_updated:           Date,
  version:                Int
}
```
*Rule:* This is a read-optimised materialised view, recomputed by `FinancialRecalculationService`. Do not use as source-of-truth for financial calculations — always recompute from `work_orders` and `payment_certificates`.

---

# 5. LIQUIDITY & LEDGER COLLECTIONS

## 5.1 `fund_allocations`
```
{
  _id:                  ObjectId,
  project_id:           String,
  category_id:          String (ref: code_master._id, budget_type='fund_transfer'),
  allocation_original:  Decimal128  -- category budget set when project created,
  allocation_received:  Decimal128  -- total money received from client to date,
  allocation_remaining: Decimal128  -- allocation_original − allocation_received,
  cash_in_hand:         Decimal128  -- allocation_received − total_expenses,
  total_expenses:       Decimal128  -- SUM of all DEBIT cash_transactions for this category,
  last_pc_closed_date:  Date (nullable)  -- timer resets ONLY on PC CLOSE,
  version:              Int,
  created_at:           Date
}
```
*Rule:* `cash_in_hand` can go negative (warning-only, not blocked).
*Rule:* `last_pc_closed_date` is used to compute the 30-day fund-request timer.
*Unique index:* `(project_id, category_id)`.

## 5.2 `cash_transactions`
```
{
  _id:           ObjectId,
  project_id:    String,
  category_id:   String (ref: code_master._id),
  amount:        Decimal128 (>= 0),
  type:          String  -- 'DEBIT' | 'CREDIT',
  purpose:       String (nullable),
  bill_reference: String (nullable),
  image_url:     String (nullable),
  created_by:    String (nullable, ref: users._id as string),
  created_at:    Date
}
```
Index: `(project_id, category_id)`.

## 5.3 `vendor_ledger` (Immutable / Append-Only)
```
{
  _id:         ObjectId,
  vendor_id:   String (ref: vendors._id),
  project_id:  String,
  ref_id:      String  -- WO or PC _id as string,
  entry_type:  String  -- 'PC_CERTIFIED' | 'PAYMENT_MADE' | 'RETENTION_HELD',
  amount:      Decimal128,
  created_at:  Date
}
```
*Rule:* No updates or deletes. Each financial event appends a new entry.
Index: `(vendor_id, project_id)`.

## 5.4 `site_overheads`
```
{
  _id:             ObjectId,
  organisation_id: String (nullable),
  project_id:      String,
  amount:          Decimal128 (>= 0),
  purpose:         String,
  created_by:      String (nullable, ref: users._id as string),
  created_at:      Date
}
```

---

# 6. SITE OPERATIONS COLLECTIONS

## 6.1 `dprs` (Daily Progress Reports)
> Collection name is `dprs` (not `daily_progress_reports`).

```
{
  _id:              ObjectId,
  project_id:       String,
  created_by:       String (ref: users._id as string),
  date:             Date,
  notes:            String,
  photos:           [String]  -- URLs,
  status:           String  -- 'DRAFT' | 'PENDING_APPROVAL' | 'APPROVED' | 'REJECTED',
  approved_by:      String (nullable, ref: users._id as string),
  approved_at:      Date (nullable),
  rejected_by:      String (nullable, ref: users._id as string),
  rejected_at:      Date (nullable),
  rejection_reason: String (nullable),
  created_at:       Date
}
```

**DPR State Machine:**
```
DRAFT → PENDING_APPROVAL
PENDING_APPROVAL → APPROVED (terminal)
PENDING_APPROVAL → REJECTED
REJECTED → DRAFT (resubmission allowed)
```

## 6.2 `attendance`
> Collection name is `attendance` (not `worker_attendance`).

```
{
  _id:               ObjectId,
  organisation_id:   String,
  project_id:        String,
  supervisor_id:     String (ref: users._id as string),
  date:              Date,
  selfie_url:        String (nullable),
  gps_lat:           Float (nullable),
  gps_lng:           Float (nullable),
  check_in_time:     Date,
  verified_by_admin: Boolean (default: false),
  verified_at:       Date (nullable),
  verified_user_id:  String (nullable)
}
```

## 6.3 `workers_daily_logs`
```
{
  _id:              ObjectId,
  organisation_id:  String,
  project_id:       String,
  date:             String (ISO date string),
  supervisor_id:    String,
  supervisor_name:  String,
  entries: [{              -- vendor-supplied workers
    vendor_id:       String (nullable),
    vendor_name:     String,
    workers_count:   Int,
    skill_type:      String,
    rate_per_worker: Decimal128,
    remarks:         String (nullable)
  }],
  workers: [{              -- directly employed workers
    worker_name:   String,
    skill_type:    String,
    hours_worked:  Decimal128 (default: 8.0),
    rate_per_hour: Decimal128,
    remarks:       String (nullable)
  }],
  total_workers:    Int,
  total_hours:      Decimal128,
  weather:          String (nullable),
  site_conditions:  String (nullable),
  remarks:          String (nullable),
  status:           String  -- 'draft' | 'submitted',
  created_at:       Date,
  updated_at:       Date
}
```

## 6.4 `voice_logs`
```
{
  _id:              ObjectId,
  project_id:       String,
  supervisor_id:    String,
  audio_url:        String,
  transcribed_text: String (nullable),
  created_at:       Date
}
```

---

# 7. AUDIT & IDEMPOTENCY COLLECTIONS

## 7.1 `audit_logs` (Immutable)
```
{
  _id:             ObjectId,
  organisation_id: String,
  module_name:     String  -- 'FINANCIAL' | 'SITE_OPERATIONS' | 'PROJECT' | etc.,
  entity_type:     String  -- e.g. 'WORK_ORDER' | 'PAYMENT_CERTIFICATE' | 'DPR',
  entity_id:       String,
  action_type:     String  -- 'CREATE' | 'UPDATE' | 'DELETE' | 'APPROVE' | 'CANCEL' | etc.,
  user_id:         String,
  project_id:      String (nullable),
  old_value:       Object (nullable, full JSON snapshot of prior state),
  new_value:       Object (nullable, full JSON snapshot of new state),
  created_at:      Date
}
```
*Rule:* Immutable. No updates or deletes.
*Indexes:* `(entity_type, entity_id)`, `(created_at, -1)`.

## 7.2 `operation_logs` (Idempotency)
```
{
  _id:              ObjectId,
  operation_key:    String (unique),
  entity_type:      String,
  response_payload: Object (nullable, cached response for replay),
  created_at:       Date
}
```
*Rule:* `operation_key` is checked before any non-idempotent financial write. If key already exists, the cached `response_payload` is returned.
*Unique index:* `(operation_key)`.

---

# 8. SYSTEM COLLECTIONS

## 8.1 `notifications`
```
{
  _id:              ObjectId,
  organisation_id:  String,
  recipient_role:   String (nullable)  -- 'Admin' | 'Supervisor' | 'Other',
  recipient_user_id: String (nullable),
  title:            String,
  message:          String,
  notification_type: String  -- 'info' | 'warning' | 'error' | 'success',
  priority:         String  -- 'normal' | 'high' | 'urgent',
  reference_type:   String (nullable)  -- e.g. 'WORK_ORDER' | 'DPR',
  reference_id:     String (nullable),
  project_id:       String (nullable),
  project_name:     String (nullable),
  sender_id:        String (nullable),
  sender_name:      String (nullable),
  is_read:          Boolean (default: false),
  read_at:          Date (nullable),
  created_at:       Date
}
```

## 8.2 `sequences`
```
{
  _id:  String  -- e.g. "wo_seq_{organisation_id}" | "pc_seq_{organisation_id}",
  seq:  Int (auto-incremented via $inc, atomic)
}
```
*Rule:* Atomically incremented inside a transaction during WO/PC creation to generate unique sequential reference numbers. The `_id` is a string, not ObjectId.

## 8.3 `background_jobs`
```
{
  _id:             ObjectId,
  job_type:        String  -- 'FINANCIAL_INTEGRITY' | 'MEDIA_PURGE' | 'AUDIO_PURGE' | 'PDF_PURGE' | 'DRIVE_RETRY' | 'COMPRESSION_RETRY',
  params:          Object,
  organisation_id: String,
  status:          String  -- 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'RETRYING',
  scheduled_by:    String (default: "SYSTEM"),
  scheduled_at:    Date,
  run_at:          Date,
  started_at:      Date (nullable),
  completed_at:    Date (nullable),
  retry_count:     Int (default: 0, max: 5),
  error_message:   String (nullable),
  result:          Object (nullable)
}
```
*Rule:* Jobs are non-blocking, idempotent, and retry with exponential backoff (base: 60 seconds).

---

# 9. DATABASE INDEXES

| Collection | Index Keys | Options |
|---|---|---|
| `project_category_budgets` | `(project_id, category_id)` | unique |
| `work_orders` | `(project_id, category_id)` | |
| `work_orders` | `(wo_ref)` | unique |
| `work_orders` | `(project_id, status)` | |
| `payment_certificates` | `(project_id, category_id)` | |
| `payment_certificates` | `(project_id, work_order_id)` | |
| `cash_transactions` | `(project_id, category_id)` | |
| `vendor_ledger` | `(vendor_id, project_id)` | |
| `operation_logs` | `(operation_key)` | unique |
| `vendors` | `(organisation_id, active_status)` | |
| `fund_allocations` | `(project_id, category_id)` | unique |
| `audit_logs` | `(entity_type, entity_id)` | |
| `audit_logs` | `(created_at, -1)` | |

---

# 10. MULTI-DOCUMENT TRANSACTION REQUIREMENTS

All mutations to these collection groups **must** use a Motor session with a transaction:

| Operation | Collections Mutated |
|---|---|
| Create Work Order | `work_orders`, `project_category_budgets`, `vendor_ledger`, `operation_logs`, `sequences` |
| Update Work Order | `work_orders`, `project_category_budgets` |
| Cancel Work Order | `work_orders`, `project_category_budgets` |
| Create Payment Certificate | `payment_certificates`, `vendor_ledger`, `operation_logs`, `sequences`, optionally `fund_allocations` |
| Close Payment Certificate | `payment_certificates`, `fund_allocations`, `vendor_ledger` |
| Budget reallocation | `project_category_budgets`, `projects` |
| Cash CREDIT (fund draw) | `fund_allocations`, `cash_transactions` |
| Cash DEBIT (expense) | `fund_allocations`, `cash_transactions` |

---

# 11. FINANCIAL MODEL RULES

1. **Commitment Model:** `committed_amount` in `project_category_budgets` increases when a WO is created (at `grand_total`) and decreases on cancellation.

2. **Warning-only over-budget:** System allows creation of WOs/PCs that exceed remaining budget. An `over_commit_flag` is set in `financial_state` but the operation is not blocked.

3. **Negative cash-in-hand:** `fund_allocations.cash_in_hand` may go negative. No hard block — warning notification is issued when below zero or below project `threshold_petty`/`threshold_ovh`.

4. **Retention:** Applied per-WO and per-PC independently. `retention_amount = grand_total × retention_percent / 100`.

5. **GST:** Project-level defaults (`project_cgst_percentage`, `project_sgst_percentage`) flow into WOs/PCs. Global org defaults in `global_settings` are fallback.

6. **Sequence numbers:** `wo_ref` = `"{wo_prefix}-{zero_padded_seq}"`. Prefix from `global_settings`. Sequence from `sequences` collection atomically.

7. **Idempotency:** All WO/PC creation calls accept an optional `idempotency_key`. If the key exists in `operation_logs`, the cached response is returned without re-executing.

8. **Derived financial state:** `financial_state` is a materialised view computed by `FinancialRecalculationService`. It is NOT the authoritative source — always recompute from `work_orders` and `payment_certificates` for critical decisions.

---

# 12. ROLE-BASED ACCESS CONTROL

| Role | Description |
|---|---|
| `Admin` | Full access to all screens and financial operations |
| `Supervisor` | Site operations (DPR, attendance, voice logs) via mobile; read-only on financials per `screen_permissions` |
| `Other` / `Client` | Read-only; access controlled by `global_settings.client_permissions` |

Additional per-user controls:
- `screen_permissions: [String]` — granular screen-level access list
- `dpr_generation_permission: Boolean` — explicit DPR creation permission
- `assigned_projects: [String]` — Supervisors can only access listed projects

---

# FINAL GUARANTEE

This schema enforces strict financial paradigms using MongoDB best practices. Multi-document transactions are explicitly required for all mutations involving `project_category_budgets`, `work_orders`, `payment_certificates`, `fund_allocations`, and `vendor_ledger` to prevent concurrency race conditions. Audit logs are immutable and vendor ledger is append-only.

---
**End of Authoritative Backend Schema — Version 3.0**
*Reconciled against: `apps/api/models.py`, `apps/api/server.py`, `apps/api/auth.py`, `apps/api/core/database.py`, `apps/api/core/indexes.py`, `apps/api/core/background_job_engine.py`, `apps/api/site_operations_routes.py`, `apps/api/work_order_service.py`, `apps/api/payment_certificate_service.py`*
