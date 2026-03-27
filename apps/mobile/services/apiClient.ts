// API CLIENT WRAPPER
// Centralized API client with JWT injection, error handling, typed responses

import { Platform } from 'react-native';
import {
  LoginRequest,
  LoginResponse,
  User,
  Project,
  CreateProjectRequest,
  Code,
  CreateCodeRequest,
  BudgetPerCode,
  CreateBudgetRequest,
  UpdateBudgetRequest,
  FinancialState,
  DerivedFinancialState,
  Vendor,
  CreateVendorRequest,
  WorkOrder,
  CreateWorkOrderRequest,
  ReviseWorkOrderRequest,
  PaymentCertificate,
  CreatePaymentCertificateRequest,
  RevisePaymentCertificateRequest,
  Payment,
  CreatePaymentRequest,
  RetentionRelease,
  CreateRetentionReleaseRequest,
  ProgressEntry,
  CreateProgressRequest,
  PlannedProgress,
  CreatePlannedProgressRequest,
  DelayAnalysis,
  Attendance,
  CreateAttendanceRequest,
  Issue,
  CreateIssueRequest,
  UpdateIssueRequest,
  VoiceLog,
  CreateVoiceLogRequest,
  PettyCash,
  CreatePettyCashRequest,
  CSA,
  CreateCSARequest,
  DPR,
  GenerateDPRRequest,
  Image,
  CreateImageRequest,
  TimelineEvent,
  Snapshot,
  Alert,
  AdminDashboardData,
  SupervisorDashboardData,
  OCRResult,
  OCRRequest,
  AuditLog,
  ApiErrorResponse,
} from '../types/api';

// ============================================
// CONFIGURATION
// ============================================
const BASE_URL =
  process.env.EXPO_PUBLIC_BACKEND_URL ||
  process.env.EXPO_PUBLIC_API_URL ||
  'http://localhost:8000';

const TOKEN_KEYS = {
  ACCESS: 'access_token',
  REFRESH: 'refresh_token',
  USER: 'user_data',
} as const;

let SecureStore: any = null;
if (Platform.OS !== 'web') {
  try {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    SecureStore = require('expo-secure-store');
  } catch (e) {
    console.warn('Failed to load expo-secure-store:', e);
  }
}

// ============================================
// AUTH TOKEN HELPERS (Web-safe)
// ============================================
export const getAuthToken = async (): Promise<string | null> => {
  if (Platform.OS === 'web') {
    return localStorage.getItem('access_token');
  }
  try {
    return SecureStore ? await SecureStore.getItemAsync('access_token') : null;
  } catch {
    return null;
  }
};

export const setAuthToken = async (token: string): Promise<void> => {
  if (Platform.OS === 'web') {
    localStorage.setItem('access_token', token);
    return;
  }
  try {
    if (SecureStore) await SecureStore.setItemAsync('access_token', token);
  } catch { }
};

export const clearAuthToken = async (): Promise<void> => {
  if (Platform.OS === 'web') {
    localStorage.removeItem('access_token');
    return;
  }
  try {
    if (SecureStore) await SecureStore.deleteItemAsync('access_token');
  } catch { }
};

// ============================================
// STORAGE ABSTRACTION
// ============================================
const storage = {
  async get(key: string): Promise<string | null> {
    if (Platform.OS === 'web') {
      return localStorage.getItem(key);
    }
    return SecureStore ? SecureStore.getItemAsync(key) : null;
  },
  async set(key: string, value: string): Promise<void> {
    if (Platform.OS === 'web') {
      localStorage.setItem(key, value);
      return;
    }
    if (SecureStore) return SecureStore.setItemAsync(key, value);
  },
  async remove(key: string): Promise<void> {
    if (Platform.OS === 'web') {
      localStorage.removeItem(key);
      return;
    }
    if (SecureStore) return SecureStore.deleteItemAsync(key);
  },
};

// ============================================
// ERROR CLASS
// ============================================
export class ApiError extends Error {
  status: number;
  data: ApiErrorResponse;

  constructor(message: string, status: number, data?: ApiErrorResponse) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data || { detail: message };
  }
}

// ============================================
// CORE FETCH WRAPPER
// ============================================
async function request<T>(
  endpoint: string,
  options: RequestInit = {},
  requiresAuth = true
): Promise<T> {
  const url = `${BASE_URL}${endpoint}`;

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };

  // Inject JWT token
  if (requiresAuth) {
    const token = await storage.get(TOKEN_KEYS.ACCESS);
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
  }

  const response = await fetch(url, { ...options, headers });

  // Handle 401 - attempt token refresh
  if (response.status === 401 && requiresAuth) {
    const refreshed = await attemptTokenRefresh();
    if (refreshed) {
      const newToken = await storage.get(TOKEN_KEYS.ACCESS);
      headers['Authorization'] = `Bearer ${newToken}`;
      const retryResponse = await fetch(url, { ...options, headers });

      if (!retryResponse.ok) {
        const error = await retryResponse.json().catch(() => ({ detail: 'Request failed' }));
        throw new ApiError(error.detail, retryResponse.status, error);
      }
      const retryData = await retryResponse.json();
      if (retryData && retryData.data !== undefined && 'success' in retryData) {
        return retryData.data as T;
      }
      return retryData;
    } else {
      await clearTokens();
      throw new ApiError('Session expired', 401);
    }
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }));
    throw new ApiError(error.detail || 'Request failed', response.status, error);
  }

  if (response.status === 204) {
    return {} as T;
  }

  const data = await response.json();
  // Automatically unwrap GenericResponse envelope from DDD v1/v2 routes
  if (data && data.data !== undefined && 'success' in data) {
    return data.data as T;
  }
  return data;
}

// ============================================
// GENERIC API CLIENT HELPER
// ============================================
export const apiClient = {
  get: <T>(endpoint: string): Promise<T> => request<T>(endpoint),
  post: <T>(endpoint: string, body?: object): Promise<T> => request<T>(endpoint, {
    method: 'POST',
    body: body ? JSON.stringify(body) : undefined,
  }),
  put: <T>(endpoint: string, body?: object): Promise<T> => request<T>(endpoint, {
    method: 'PUT',
    body: body ? JSON.stringify(body) : undefined,
  }),
  delete: <T>(endpoint: string): Promise<T> => request<T>(endpoint, { method: 'DELETE' }),
};

let refreshTokenPromise: Promise<boolean> | null = null;

async function attemptTokenRefresh(): Promise<boolean> {
  if (refreshTokenPromise) {
    return refreshTokenPromise;
  }

  refreshTokenPromise = (async () => {
    try {
      const refreshToken = await storage.get(TOKEN_KEYS.REFRESH);
      if (!refreshToken) return false;

      const response = await fetch(`${BASE_URL}/api/v1/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (!response.ok) return false;

      const data: LoginResponse = await response.json();
      await storage.set(TOKEN_KEYS.ACCESS, data.access_token);
      await storage.set(TOKEN_KEYS.REFRESH, data.refresh_token);
      await storage.set(TOKEN_KEYS.USER, JSON.stringify(data.user));
      return true;
    } catch {
      return false;
    } finally {
      refreshTokenPromise = null;
    }
  })();

  return refreshTokenPromise;
}

async function clearTokens(): Promise<void> {
  await storage.remove(TOKEN_KEYS.ACCESS);
  await storage.remove(TOKEN_KEYS.REFRESH);
  await storage.remove(TOKEN_KEYS.USER);
}

// ============================================
// AUTH API
// ============================================
export const authApi = {
  async login(credentials: LoginRequest): Promise<LoginResponse> {
    const data = await request<LoginResponse>('/api/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify(credentials),
    }, false);
    await storage.set(TOKEN_KEYS.ACCESS, data.access_token);
    await storage.set(TOKEN_KEYS.REFRESH, data.refresh_token);
    await storage.set(TOKEN_KEYS.USER, JSON.stringify(data.user));
    return data;
  },
  async logout(): Promise<void> {
    try {
      // Revoke refresh tokens server-side
      await request('/api/v1/auth/logout', { method: 'POST' });
    } catch (error) {
      // Still clear local tokens even if server call fails
      console.error('Server logout failed:', error);
    }
    await clearTokens();
  },
  async getCurrentUser(): Promise<User | null> {
    const userData = await storage.get(TOKEN_KEYS.USER);
    return userData ? JSON.parse(userData) : null;
  },
  async isAuthenticated(): Promise<boolean> {
    const token = await storage.get(TOKEN_KEYS.ACCESS);
    return !!token;
  },
  async getToken(): Promise<string | null> {
    return storage.get(TOKEN_KEYS.ACCESS);
  },
  async checkCanLogout(): Promise<{ can_logout: boolean; reason?: string; message?: string; has_draft?: boolean }> {
    try {
      return await request<{ can_logout: boolean; reason?: string; message?: string; has_draft?: boolean }>('/api/v1/auth/can-logout');
    } catch (error) {
      // Fail-safe behavior to avoid locking users in app due transient API errors
      console.error('Failed to check logout status:', error);
      return { can_logout: true };
    }
  },
};

// ============================================
// PROJECTS API
// ============================================
export const projectsApi = {
  getAll: (): Promise<Project[]> => request('/api/v1/projects'),
  getById: (id: string): Promise<Project> => request(`/api/v1/projects/${id}`),
  create: (data: CreateProjectRequest): Promise<Project> => request('/api/v1/projects', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: string, data: Partial<CreateProjectRequest>): Promise<Project> => request(`/api/v1/projects/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
};

// ============================================
// CODES API
// ============================================
export const codesApi = {
  getAll: (activeOnly = true): Promise<Code[]> => request(`/api/v1/codes?active_only=${activeOnly}`),
  getById: (id: string): Promise<Code> => request(`/api/v1/codes/${id}`),
  create: (data: CreateCodeRequest): Promise<Code> => request('/api/v1/codes', { method: 'POST', body: JSON.stringify(data) }),
};

// ============================================
// BUDGETS API
// ============================================
export const budgetsApi = {
  getAll: (projectId?: string): Promise<BudgetPerCode[]> => request(`/api/v1/budgets${projectId ? `?project_id=${projectId}` : ''}`),
  getById: (id: string): Promise<BudgetPerCode> => request(`/api/v1/budgets/${id}`),
  create: (data: CreateBudgetRequest): Promise<BudgetPerCode> => request('/api/v1/budgets', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: string, data: UpdateBudgetRequest): Promise<BudgetPerCode> => request(`/api/v1/budgets/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
};

// ============================================
// FINANCIAL STATE API
// ============================================
export const financialApi = {
  getState: (projectId: string, codeId?: string): Promise<FinancialState[]> => {
    const params = new URLSearchParams({ project_id: projectId });
    if (codeId) params.append('code_id', codeId);
    return request(`/api/v1/financial-state?${params}`);
  },
  getProjectFinancials: (projectId: string): Promise<DerivedFinancialState[]> =>
    request(`/api/v1/projects/${projectId}/financials`),
};

// ============================================
// VENDORS API
// ============================================
export const vendorsApi = {
  getAll: (activeOnly = true): Promise<Vendor[]> => request(`/api/v1/vendors?active_only=${activeOnly}`),
  getById: (id: string): Promise<Vendor> => request(`/api/v1/vendors/${id}`),
  create: (data: CreateVendorRequest): Promise<Vendor> => request('/api/v1/vendors', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: string, data: Partial<CreateVendorRequest>): Promise<Vendor> => request(`/api/v1/vendors/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  delete: (id: string): Promise<void> => request(`/api/v1/vendors/${id}`, { method: 'DELETE' }),
};

// ============================================
// WORK ORDERS API
// ============================================
export const workOrdersApi = {
  getAll: (projectId?: string, status?: string): Promise<WorkOrder[]> => {
    const params = new URLSearchParams();
    if (projectId) params.append('project_id', projectId);
    if (status) params.append('status_filter', status);
    return request(`/api/v1/work-orders?${params}`);
  },
  getById: (id: string): Promise<WorkOrder> => request(`/api/v1/work-orders/${id}`),
  create: (data: CreateWorkOrderRequest): Promise<WorkOrder> => request('/api/v1/work-orders', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: string, data: CreateWorkOrderRequest): Promise<WorkOrder> => request(`/api/v1/work-orders/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  delete: (id: string): Promise<void> => request(`/api/v1/work-orders/${id}`, { method: 'DELETE' }),
  issue: (id: string): Promise<WorkOrder> => request(`/api/v1/work-orders/${id}/issue`, { method: 'POST' }),
  cancel: (id: string): Promise<void> => request(`/api/v1/work-orders/${id}/cancel`, { method: 'POST' }),
  revise: (id: string, data: ReviseWorkOrderRequest): Promise<WorkOrder> => request(`/api/v1/work-orders/${id}/revise`, { method: 'POST', body: JSON.stringify(data) }),
  getTransitions: (id: string): Promise<{ allowed_transitions: string[] }> => request(`/api/v1/work-orders/${id}/transitions`),
};

// ============================================
// PAYMENT CERTIFICATES API
// ============================================
export const paymentCertificatesApi = {
  getAll: (projectId?: string, status?: string): Promise<PaymentCertificate[]> => {
    const params = new URLSearchParams();
    if (projectId) params.append('project_id', projectId);
    if (status) params.append('status_filter', status);
    return request(`/api/v1/payments/${projectId}?${params}`); // Map to list_payment_certificates
  },
  getById: (id: string): Promise<PaymentCertificate> => request(`/api/v1/payments/${id}`),
  create: (data: CreatePaymentCertificateRequest): Promise<PaymentCertificate> => request('/api/v1/payments/', { method: 'POST', body: JSON.stringify(data) }),
  certify: (id: string, invoiceNumber?: string): Promise<PaymentCertificate> => request(`/api/v1/payments/${id}/close`, { method: 'POST' }), // Map to close_payment_certificate
  revise: (id: string, data: RevisePaymentCertificateRequest): Promise<PaymentCertificate> => request(`/api/v1/payments/${id}/revise`, { method: 'POST', body: JSON.stringify(data) }),
};

// ============================================
// PAYMENTS API
// ============================================
export const paymentsApi = {
  getByPC: (pcId: string): Promise<Payment[]> => request(`/api/v1/payments?pc_id=${pcId}`),
  create: (data: CreatePaymentRequest): Promise<Payment> => request('/api/v1/payments', { method: 'POST', body: JSON.stringify(data) }),
};

// ============================================
// RETENTION RELEASES API
// ============================================
export const retentionApi = {
  getAll: (projectId: string): Promise<RetentionRelease[]> => request(`/api/v1/retention-releases?project_id=${projectId}`),
  create: (data: CreateRetentionReleaseRequest): Promise<RetentionRelease> => request('/api/v1/retention-releases', { method: 'POST', body: JSON.stringify(data) }),
};

// ============================================
// PROGRESS API
// ============================================
export const progressApi = {
  getAll: (projectId: string, codeId?: string): Promise<ProgressEntry[]> => {
    const params = new URLSearchParams({ project_id: projectId });
    if (codeId) params.append('code_id', codeId);
    return request(`/api/v1/progress?${params}`);
  },
  create: (data: CreateProgressRequest): Promise<ProgressEntry> => request('/api/v1/progress', { method: 'POST', body: JSON.stringify(data) }),
  getLatest: (projectId: string, codeId: string): Promise<ProgressEntry> => request(`/api/v1/progress/latest?project_id=${projectId}&code_id=${codeId}`),
};

// ============================================
// PLANNED PROGRESS API
// ============================================
export const plannedProgressApi = {
  getAll: (projectId: string, codeId?: string): Promise<PlannedProgress[]> => {
    const params = new URLSearchParams({ project_id: projectId });
    if (codeId) params.append('code_id', codeId);
    return request(`/api/v1/planned-progress?${params}`);
  },
  create: (data: CreatePlannedProgressRequest): Promise<PlannedProgress> => request('/api/v1/planned-progress', { method: 'POST', body: JSON.stringify(data) }),
};

// ============================================
// DELAY ANALYSIS API
// ============================================
export const delayApi = {
  analyze: (projectId: string, codeId?: string): Promise<DelayAnalysis[]> => {
    const params = new URLSearchParams({ project_id: projectId });
    if (codeId) params.append('code_id', codeId);
    return request(`/api/v1/delay-analysis?${params}`);
  },
};

// ============================================
// ATTENDANCE API
// ============================================
export const attendanceApi = {
  getAll: (projectId: string, supervisorId?: string): Promise<Attendance[]> => {
    return request(`/api/v1/site/projects/${projectId}/attendance`);
  },
  checkIn: (data: CreateAttendanceRequest): Promise<Attendance> => request('/api/v1/attendance', { method: 'POST', body: JSON.stringify(data) }), // Check if this also needs /site/
  getToday: (projectId: string, supervisorId: string): Promise<Attendance | null> => request(`/api/v1/attendance/today?project_id=${projectId}&supervisor_id=${supervisorId}`),
};

// ============================================
// ISSUES API
// ============================================
export const issuesApi = {
  getAll: (projectId: string, status?: string): Promise<Issue[]> => {
    const params = new URLSearchParams({ project_id: projectId });
    if (status) params.append('status', status);
    return request(`/api/v1/issues?${params}`);
  },
  getById: (id: string): Promise<Issue> => request(`/api/v1/issues/${id}`),
  create: (data: CreateIssueRequest): Promise<Issue> => request('/api/v1/issues', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: string, data: UpdateIssueRequest): Promise<Issue> => request(`/api/v1/issues/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
};

// ============================================
// VOICE LOGS API
// ============================================
export const voiceLogsApi = {
  getAll: (projectId: string): Promise<VoiceLog[]> => request(`/api/v1/site/projects/${projectId}/voice-logs`),
  create: (data: CreateVoiceLogRequest): Promise<VoiceLog> => request('/api/v1/voice-logs', { method: 'POST', body: JSON.stringify(data) }),
};

// ============================================
// PETTY CASH API
// ============================================
export const pettyCashApi = {
  getAll: (projectId: string, status?: string): Promise<PettyCash[]> => {
    const params = new URLSearchParams({ project_id: projectId });
    if (status) params.append('status', status);
    return request(`/api/v1/petty-cash?${params}`);
  },
  create: (data: CreatePettyCashRequest): Promise<PettyCash> => request('/api/v1/petty-cash', { method: 'POST', body: JSON.stringify(data) }),
  approve: (id: string): Promise<PettyCash> => request(`/api/v1/petty-cash/${id}/approve`, { method: 'POST' }),
  reject: (id: string, reason?: string): Promise<PettyCash> => request(`/api/v1/petty-cash/${id}/reject`, { method: 'POST', body: JSON.stringify({ reason }) }),
};

// ============================================
// HARDENED CASH API (Phase 7 Parity)
// ============================================

/**
 * A single financial category as returned by the server's cash-summary endpoint.
 * All balance flags (`is_negative`, `threshold_breached`) are computed exclusively
 * server-side and must never be derived or overridden on the client.
 */
export interface CashCategory {
  category_id: string;
  category_name: string;
  cash_in_hand: number;
  allocation_total: number;
  /** True when this category's cash-in-hand balance falls below zero. Server-computed. */
  is_negative: boolean;
  /** True when this category has breached the configured threshold. Server-computed. */
  threshold_breached: boolean;
}

/**
 * Full response envelope for `cashApi.getSummary`.
 * Conforms strictly to the v2 nested category schema returned by `GET /api/projects/:id/cash-summary`.
 */
export interface CashSummaryResponse {
  categories: CashCategory[];
  summary: {
    total_cash_in_hand: number;
  };
}

/**
 * A single cash transaction as returned by the server.
 */
export interface CashTransaction {
  transaction_id: string;
  project_id: string;
  category_id: string;
  description: string;
  amount: number;
  transaction_date: string;
  created_by: string;
  created_at: string;
}

export const cashApi = {
  /**
   * Fetches the cash position summary for a project, broken down by server-computed categories.
   *
   * @param projectId - The project to query.
   * @returns A `CashSummaryResponse` with a `categories` array and aggregate `summary`.
   */
  getSummary: (projectId: string): Promise<CashSummaryResponse> =>
    request(`/api/v1/cash/summary/${projectId}`),

  listTransactions: (projectId: string, params?: { category_id?: string; cursor?: string; limit?: number }): Promise<{
    items: CashTransaction[];
    next_cursor: string | null;
  }> => {
    const query = new URLSearchParams();
    if (params?.category_id) query.append('category_id', params.category_id);
    if (params?.cursor) query.append('cursor', params.cursor);
    if (params?.limit) query.append('limit', String(params.limit));
    return request(`/api/v1/cash/transactions?${query}`);
  },

  /**
   * POSTs a raw cash transaction entry to the server.
   *
   * @param projectId - The project context for the transaction.
   * @param data - Raw entry payload (description, amount, category_id, attachments, etc.).
   * @param idempotencyKey - A unique key (UUID v4 recommended) to prevent duplicate submissions.
   *
   * @security warning: "Client-side math is strictly forbidden. This method must only be used to POST raw entry data; balances are calculated server-side."
   */
  createTransaction: (projectId: string, data: any, idempotencyKey: string): Promise<CashTransaction> => {
    return request(`/api/v1/cash/transactions`, {
      method: 'POST',
      headers: { 'Idempotency-Key': idempotencyKey },
      body: JSON.stringify(data),
    });
  },
};

// ============================================
// CSA API
// ============================================
export const csaApi = {
  getAll: (projectId: string): Promise<CSA[]> => request(`/api/csa?project_id=${projectId}`),
  create: (data: CreateCSARequest): Promise<CSA> => request('/api/csa', { method: 'POST', body: JSON.stringify(data) }),
};

// ============================================
// DPR API
// ============================================
export const dprApi = {
  getAll: (projectId: string): Promise<DPR[]> => request(`/api/v1/site/projects/${projectId}/dprs`),
  generate: (data: GenerateDPRRequest): Promise<DPR> => request('/api/v1/dpr/generate', { method: 'POST', body: JSON.stringify(data) }),
  getById: (id: string): Promise<DPR> => request(`/api/v1/site/dprs/${id}`),
};

// ============================================
// IMAGES API
// ============================================
export const imagesApi = {
  getAll: (projectId: string, codeId?: string): Promise<Image[]> => {
    const params = new URLSearchParams({ project_id: projectId });
    if (codeId) params.append('code_id', codeId);
    return request(`/api/images?${params}`);
  },
  upload: (data: CreateImageRequest): Promise<Image> => request('/api/images', { method: 'POST', body: JSON.stringify(data) }),
  getToday: (projectId: string, supervisorId: string): Promise<Image[]> => request(`/api/images/today?project_id=${projectId}&supervisor_id=${supervisorId}`),
};

// ============================================
// TIMELINE API
// ============================================
export const timelineApi = {
  getAll: (projectId: string, limit = 50): Promise<TimelineEvent[]> => request(`/api/timeline?project_id=${projectId}&limit=${limit}`),
};

// ============================================
// SNAPSHOTS API
// ============================================
export const snapshotsApi = {
  getAll: (projectId: string, type?: string): Promise<Snapshot[]> => {
    const params = new URLSearchParams({ project_id: projectId });
    if (type) params.append('type', type);
    return request(`/api/snapshots?${params}`);
  },
  getById: (id: string): Promise<Snapshot> => request(`/api/snapshots/${id}`),
};

// ============================================
// ALERTS API
// ============================================
export const alertsApi = {
  getAll: (projectId?: string, resolved = false): Promise<Alert[]> => {
    const params = new URLSearchParams({ resolved: String(resolved) });
    if (projectId) params.append('project_id', projectId);
    return request(`/api/alerts?${params}`);
  },
  resolve: (id: string): Promise<Alert> => request(`/api/alerts/${id}/resolve`, { method: 'POST' }),
};

// ============================================
// DASHBOARD API
// ============================================
export const dashboardApi = {
  getAdminDashboard: (projectId?: string): Promise<AdminDashboardData> =>
    request(`/api/v1/projects/${projectId}/dashboard-stats`),
  getSupervisorDashboard: (projectId: string): Promise<SupervisorDashboardData> => request(`/api/dashboard/supervisor?project_id=${projectId}`),
};

// ============================================
// OCR API
// ============================================
export const ocrApi = {
  scanInvoice: (data: OCRRequest): Promise<OCRResult> => request('/api/v1/ai/ocr', { method: 'POST', body: JSON.stringify(data) }),
};

// ============================================
// USERS API
// ============================================
export const usersApi = {
  getAll: (): Promise<User[]> => request('/api/v1/users'),
  getById: (id: string): Promise<User> => request(`/api/v1/users/${id}`),
};

// ============================================
// AUDIT LOGS API
// ============================================
export const auditLogsApi = {
  getAll: (entityType?: string, entityId?: string, limit = 100): Promise<AuditLog[]> => {
    const params = new URLSearchParams({ limit: String(limit) });
    if (entityType) params.append('entity_type', entityType);
    if (entityId) params.append('entity_id', entityId);
    return request(`/api/audit-logs?${params}`);
  },
};

// ============================================
// SETTINGS API
// ============================================
export interface GlobalSettings {
  dpr_enforcement_enabled?: boolean;
  default_retention_percentage?: number;
  default_cgst_percentage?: number;
  default_sgst_percentage?: number;
  [key: string]: unknown; // allow extension without losing type safety
}

export const settingsApi = {
  getGlobalSettings: (): Promise<GlobalSettings> => request('/api/v1/settings'),
  updateGlobalSettings: (data: Partial<GlobalSettings>): Promise<GlobalSettings> =>
    request('/api/v1/settings', { method: 'PUT', body: JSON.stringify(data) }),
};

// ============================================
// REPORTING API
// ============================================
export interface ReportData {
  [key: string]: unknown;
}

export const reportingApi = {
  getReportData: (projectId: string, reportType: string, params?: { start_date?: string; end_date?: string }): Promise<ReportData> => {
    const query = new URLSearchParams();
    if (params?.start_date) query.append('start_date', params.start_date);
    if (params?.end_date) query.append('end_date', params.end_date);
    return request(`/api/projects/${projectId}/reports/${reportType}?${query}`);
  },
  getExportUrl: (projectId: string, reportType: string, format: 'excel' | 'pdf', params?: { start_date?: string; end_date?: string }): string => {
    const query = new URLSearchParams();
    if (params?.start_date) query.append('start_date', params.start_date);
    if (params?.end_date) query.append('end_date', params.end_date);
    return `${BASE_URL}/api/projects/${projectId}/reports/${reportType}/export/${format}?${query}`;
  }
};

// ============================================
// DEFAULT EXPORT
// ============================================
export default {
  auth: authApi,
  projects: projectsApi,
  codes: codesApi,
  budgets: budgetsApi,
  financial: financialApi,
  vendors: vendorsApi,
  workOrders: workOrdersApi,
  paymentCertificates: paymentCertificatesApi,
  payments: paymentsApi,
  retention: retentionApi,
  progress: progressApi,
  plannedProgress: plannedProgressApi,
  delay: delayApi,
  attendance: attendanceApi,
  issues: issuesApi,
  voiceLogs: voiceLogsApi,
  pettyCash: pettyCashApi,
  csa: csaApi,
  dpr: dprApi,
  images: imagesApi,
  timeline: timelineApi,
  snapshots: snapshotsApi,
  alerts: alertsApi,
  dashboard: dashboardApi,
  ocr: ocrApi,
  users: usersApi,
  auditLogs: auditLogsApi,
  cash: cashApi,
  settings: settingsApi,
  reporting: reportingApi,
};
