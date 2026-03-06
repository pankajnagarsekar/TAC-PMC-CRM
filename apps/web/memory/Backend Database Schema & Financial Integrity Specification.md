# Backend Database Schema & Financial Integrity Specification

## CRM Financial Management System -- Version 2.0 (MongoDB Edition)

**Document 5 of 6 -- Single Source of Truth** **Generated On:** 04 March 2026

------------------------------------------------------------------------

# 1. Core Engineering Standards

Database: MongoDB 5.0+\
Transaction Level: Multi-Document ACID Sessions\
Monetary Type: `Decimal128` (BSON) ONLY\
Primary Keys: `ObjectId` (`_id`)\
All financial writes: Atomic, idempotent, audited

System supports Commitment Model, Liquidity Model, Warning-only over-budget, Negative cash-in-hand, and per-project financial isolation.

------------------------------------------------------------------------

# 2. MASTER COLLECTIONS

## 2.1 `clients`
`{ _id: ObjectId, name: String, address: String, phone: String, email: String, gstin: String, created_at: Date, updated_at: Date }`

## 2.2 `projects`
`{ _id: ObjectId, client_id: ObjectId, name: String, project_code: String (Unique), master_original_budget: Decimal128, master_remaining_budget: Decimal128, threshold_petty: Decimal128, threshold_ovh: Decimal128, version: Int, created_at: Date }`

## 2.3 `categories` (Application-wide)
`{ _id: ObjectId, code: String (Unique), name: String, is_locked: Boolean, created_at: Date }`

## 2.4 `global_settings`
`{ _id: ObjectId, company_name: String, gst_defaults: { cgst: Decimal128, sgst: Decimal128 }, default_terms: String, client_permissions: { can_view_dpr: Boolean, can_view_financials: Boolean, can_view_reports: Boolean }, updated_at: Date }`

------------------------------------------------------------------------

# 3. FINANCIAL COLLECTIONS

## 3.1 `project_category_budgets`
`{ _id: ObjectId, project_id: ObjectId, category_id: ObjectId, original_budget: Decimal128, committed_amount: Decimal128 (Default 0), remaining_budget: Decimal128, version: Int }`
*Rule:* `original_budget` cannot be reduced below `committed_amount`.

## 3.2 `work_orders`
`{ _id: ObjectId, project_id: ObjectId, category_id: ObjectId, vendor_id: ObjectId, wo_ref: String (Unique), subtotal: Decimal128, discount: Decimal128, total_before_tax: Decimal128, cgst: Decimal128, sgst: Decimal128, grand_total: Decimal128, retention_percent: Decimal128, retention_amount: Decimal128, total_payable: Decimal128, actual_payable: Decimal128, status: String ('Draft','Pending','Completed','Closed','Cancelled'), line_items: [ { sr_no, description, qty: Decimal128, rate: Decimal128, total: Decimal128 } ], version: Int, created_at: Date }`

## 3.3 `payment_certificates`
`{ _id: ObjectId, project_id: ObjectId, work_order_id: ObjectId (Nullable), category_id: ObjectId, vendor_id: ObjectId (Nullable), pc_ref: String, subtotal: Decimal128, retention_percent: Decimal128, retention_amount: Decimal128, cgst: Decimal128, sgst: Decimal128, grand_total: Decimal128, status: String, line_items: [...], idempotency_key: String (Unique), version: Int, created_at: Date }`

------------------------------------------------------------------------

# 4. LIQUIDITY & LEDGER COLLECTIONS

## 4.1 `fund_allocations` (Petty/OVH)
`{ _id: ObjectId, project_id: ObjectId, category_id: ObjectId, allocation_original: Decimal128, allocation_received: Decimal128, allocation_remaining: Decimal128, last_pc_closed_date: Date, version: Int }`

## 4.2 `cash_transactions` (Combined Petty & OVH)
`{ _id: ObjectId, project_id: ObjectId, category_id: ObjectId, amount: Decimal128, type: String ('DEBIT', 'CREDIT'), bill_reference: String, image_url: String, created_at: Date }`

## 4.3 `vendor_ledger` (Immutable)
`{ _id: ObjectId, vendor_id: ObjectId, project_id: ObjectId, ref_id: ObjectId (WO/PC ID), entry_type: String ('PC_CERTIFIED', 'PAYMENT_MADE', 'RETENTION_HELD'), amount: Decimal128, created_at: Date }`

------------------------------------------------------------------------

# 5. SITE OPERATIONS COLLECTIONS (Mobile Parity)

## 5.1 `daily_progress_reports` (DPR)
`{ _id: ObjectId, project_id: ObjectId, supervisor_id: ObjectId, date: Date, notes: String, photos: [String], status: String ('DRAFT', 'APPROVED'), approved_by: ObjectId (Nullable), created_at: Date }`

## 5.2 `worker_attendance`
`{ _id: ObjectId, project_id: ObjectId, supervisor_id: ObjectId, date: Date, selfie_url: String, gps_lat: Float, gps_lng: Float, check_in_time: Date, verified_by_admin: Boolean }`

## 5.3 `voice_logs`
`{ _id: ObjectId, project_id: ObjectId, supervisor_id: ObjectId, audio_url: String, transcribed_text: String, created_at: Date }`

------------------------------------------------------------------------

# 6. SYSTEM AUDIT & IDEMPOTENCY

## 6.1 `audit_logs` (Immutable)
`{ _id: ObjectId, entity_name: String, entity_id: ObjectId, previous_state: Object, new_state: Object, action_type: String, user_id: ObjectId, created_at: Date }`

## 6.2 `operation_logs` (Idempotency)
`{ _id: ObjectId, operation_key: String (Unique), entity_type: String, created_at: Date }`

------------------------------------------------------------------------

# FINAL GUARANTEE
This schema enforces strict financial paradigms using MongoDB best practices. Multi-document transactions are explicitly required for all mutations involving `project_category_budgets`, `work_orders`, `payment_certificates`, and `fund_allocations` to prevent concurrency race conditions.

------------------------------------------------------------------------
**End of Authoritative Backend Schema -- Version 2.0**