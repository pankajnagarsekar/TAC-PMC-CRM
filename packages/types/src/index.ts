// =============================================================================
// API Type Contracts — TAC-PMC CRM
// Single source of truth for all API request/response shapes
// =============================================================================

// ──────────────────────────────────────────────────────────────────────────
// AUTH
// ──────────────────────────────────────────────────────────────────────────
export interface LoginRequest {
  email: string;
  password: string;
}

export interface UserResponse {
  user_id: string;
  organisation_id: string;
  name: string;
  email: string;
  role: "Admin" | "Supervisor" | "Client";
  active_status: boolean;
  dpr_generation_permission: boolean;
  assigned_projects: string[];
  screen_permissions: string[];
  created_at: string;
  updated_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  user: UserResponse;
}

// ──────────────────────────────────────────────────────────────────────────
// CLIENTS
// ──────────────────────────────────────────────────────────────────────────
export interface Client {
  _id?: string;
  organisation_id: string;
  client_name: string;
  client_email?: string;
  client_phone?: string;
  client_address?: string;
  gst_number?: string;
  active_status: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface ClientCreate {
  client_name: string;
  client_email?: string;
  client_phone?: string;
  client_address?: string;
  gst_number?: string;
}

export interface ClientUpdate {
  client_name?: string;
  client_email?: string;
  client_phone?: string;
  client_address?: string;
  gst_number?: string;
  active_status?: boolean;
}

// ──────────────────────────────────────────────────────────────────────────
// PROJECTS
// ──────────────────────────────────────────────────────────────────────────
export interface Project {
  _id?: string;
  project_id: string;
  organisation_id: string;
  project_name: string;
  client_id?: string;
  client_name?: string;
  project_code?: string;
  status: string;
  address?: string;
  city?: string;
  state?: string;
  project_retention_percentage: number;
  project_cgst_percentage: number;
  project_sgst_percentage: number;
  completion_percentage?: number;
  // Financial fields per DB Schema §2.2
  master_original_budget?: number;
  master_remaining_budget?: number;
  threshold_petty?: number;
  threshold_ovh?: number;
  version?: number;
  created_at?: string;
  updated_at?: string;
}

export interface ProjectCreate {
  project_name: string;
  client_id: string;
  project_code?: string;
  status?: string;
  address?: string;
  city?: string;
  state?: string;
  project_retention_percentage?: number;
  project_cgst_percentage?: number;
  project_sgst_percentage?: number;
  completion_percentage?: number;
  threshold_petty?: number;
  threshold_ovh?: number;
}

// ──────────────────────────────────────────────────────────────────────────
// CATEGORIES / CODE MASTER
// ──────────────────────────────────────────────────────────────────────────
export interface CodeMaster {
  code_id?: string;
  _id?: string;
  organisation_id?: string;
  category_name: string;
  code: string;
  budget_type?: "commitment" | "fund_transfer";
  description?: string;
  active_status?: boolean;
  created_at?: string;
  updated_at?: string;
}

// ──────────────────────────────────────────────────────────────────────────
// PROJECT BUDGETS
// ──────────────────────────────────────────────────────────────────────────
export interface ProjectBudget {
  _id?: string;
  project_id: string;
  code_id: string;
  original_budget: number;
  description?: string;
  created_at?: string;
  updated_at?: string;
}

/** Spec-aligned budget per DB Schema §3.1 */
export interface ProjectCategoryBudget {
  _id?: string;
  project_id: string;
  category_id: string;
  original_budget: number;
  committed_amount: number;
  remaining_budget: number;
  version?: number;
}

export interface DerivedFinancialState {
  _id?: string;
  project_id: string;
  category_id: string;
  original_budget: number;
  committed_value: number;
  certified_value: number;
  balance_budget_remaining: number;
  over_commit_flag: boolean;
  last_updated?: string;
}

// ──────────────────────────────────────────────────────────────────────────
// WORK ORDERS
// ──────────────────────────────────────────────────────────────────────────
export interface WOLineItem {
  sr_no: number;
  description: string;
  qty: number;
  rate: number;
  total: number;
}

export interface WorkOrder {
  _id?: string;
  work_order_id?: string;
  project_id: string;
  category_id: string;
  vendor_id?: string;
  wo_ref: string;
  description?: string;
  terms?: string;
  subtotal: number;
  discount: number;
  total_before_tax: number;
  cgst: number;
  sgst: number;
  grand_total: number;
  retention_percent: number;
  retention_amount: number;
  total_payable: number;
  actual_payable: number;
  status: "Draft" | "Pending" | "Completed" | "Closed" | "Cancelled";
  line_items: WOLineItem[];
  version?: number;
  created_at?: string;
  updated_at?: string;
}

// ──────────────────────────────────────────────────────────────────────────
// PAYMENT CERTIFICATES
// ──────────────────────────────────────────────────────────────────────────
export interface PCLineItem {
  sr_no: number;
  scope_of_work: string;
  rate: number;
  qty: number;
  unit: string;
  total: number;
}

export interface PaymentCertificate {
  _id?: string;
  pc_id?: string;
  project_id: string;
  work_order_id?: string;
  category_id: string;
  vendor_id?: string;
  pc_ref: string;
  subtotal: number;
  retention_percent: number;
  retention_amount: number;
  total_payable?: number;
  cgst: number;
  sgst: number;
  grand_total: number;
  status: "Draft" | "Pending" | "Completed" | "Closed" | "Cancelled";
  fund_request?: boolean;
  line_items: PCLineItem[];
  idempotency_key?: string;
  version?: number;
  created_at?: string;
}

// ──────────────────────────────────────────────────────────────────────────
// VENDORS
// ──────────────────────────────────────────────────────────────────────────
export interface Vendor {
  _id?: string;
  organisation_id: string;
  name: string;
  gstin?: string;
  contact_person?: string;
  phone?: string;
  email?: string;
  address?: string;
  active_status: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface VendorCreate {
  name: string;
  gstin?: string;
  contact_person?: string;
  phone?: string;
  email?: string;
  address?: string;
}

export interface VendorUpdate {
  name?: string;
  gstin?: string;
  contact_person?: string;
  phone?: string;
  email?: string;
  address?: string;
  active_status?: boolean;
}

// ──────────────────────────────────────────────────────────────────────────
// PETTY CASH / OVH
// ──────────────────────────────────────────────────────────────────────────
export interface FundAllocation {
  _id?: string;
  project_id: string;
  category_id: string;
  category_name?: string;
  allocation_total: number;
  allocation_remaining: number;
  last_replenished?: string;
  version?: number;
  created_at?: string;
}

export interface CashTransaction {
  _id?: string;
  project_id: string;
  category_id: string;
  amount: number;
  type: "DEBIT" | "CREDIT";
  purpose?: string;
  bill_reference?: string;
  receipt_photo?: string;
  vendor_name?: string;
  created_by: string;
  created_at?: string;
}

/** Vendor ledger entry per DB Schema §4.3 — immutable/append-only */
export interface VendorLedgerEntry {
  _id?: string;
  vendor_id: string;
  project_id: string;
  ref_id: string;
  entry_type: "PC_CERTIFIED" | "PAYMENT_MADE" | "RETENTION_HELD";
  amount: number;
  created_at?: string;
}

// ──────────────────────────────────────────────────────────────────────────
// SITE OPERATIONS
// ──────────────────────────────────────────────────────────────────────────
export interface DPR {
  _id?: string;
  dpr_id?: string;
  project_id: string;
  supervisor_id?: string;
  created_by: string;
  date: string;
  notes: string;
  photos: string[];
  status: "DRAFT" | "PENDING_APPROVAL" | "APPROVED" | "REJECTED";
  approved_by?: string;
  approved_at?: string;
  rejected_by?: string;
  rejected_at?: string;
  rejection_reason?: string;
  created_at?: string;
}

export interface WorkerAttendance {
  _id?: string;
  project_id: string;
  supervisor_id: string;
  date: string;
  selfie_url: string;
  gps_lat: number;
  gps_lng: number;
  check_in_time: string;
  verified_by_admin: boolean;
}

/** Voice log per DB Schema §5.3 */
export interface VoiceLog {
  _id?: string;
  project_id: string;
  supervisor_id: string;
  audio_url: string;
  transcribed_text?: string;
  created_at?: string;
}

// ──────────────────────────────────────────────────────────────────────────
// GLOBAL SETTINGS
// ──────────────────────────────────────────────────────────────────────────
export interface GlobalSettings {
  _id?: string;
  organisation_id: string;
  name: string;
  address: string;
  email: string;
  phone: string;
  gst_number: string;
  pan_number: string;
  cgst_percentage: number;
  sgst_percentage: number;
  wo_prefix: string;
  pc_prefix: string;
  invoice_prefix: string;
  terms_and_conditions: string;
  currency: string;
  currency_symbol: string;
  // Client permission matrix
  client_permissions?: {
    can_view_dpr: boolean;
    can_view_financials: boolean;
    can_view_reports: boolean;
  };
  updated_at?: string;
}

// ──────────────────────────────────────────────────────────────────────────
// USERS
// ──────────────────────────────────────────────────────────────────────────
export interface UserCreate {
  email: string;
  password: string;
  name: string;
  role?: string;
  dpr_generation_permission?: boolean;
}

export interface UserUpdate {
  name?: string;
  role?: string;
  active_status?: boolean;
  dpr_generation_permission?: boolean;
  assigned_projects?: string[];
}

// ──────────────────────────────────────────────────────────────────────────
// AUDIT & IDEMPOTENCY
// ──────────────────────────────────────────────────────────────────────────

/** Audit log per DB Schema §6.1 — immutable/append-only */
export interface AuditLog {
  _id?: string;
  entity_name: string;
  entity_id: string;
  previous_state?: Record<string, unknown>;
  new_state?: Record<string, unknown>;
  action_type: string;
  user_id: string;
  created_at?: string;
}

/** Operation log per DB Schema §6.2 — idempotency tracking */
export interface OperationLog {
  _id?: string;
  operation_key: string;
  entity_type: string;
  created_at?: string;
}

// ──────────────────────────────────────────────────────────────────────────
// COMMON
// ──────────────────────────────────────────────────────────────────────────
export interface ApiError {
  detail: string;
  status?: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
}
