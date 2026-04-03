import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";
import { errorLogger } from "./errorLogger";
import type {
  ScheduleCalculationResponse,
  ScheduleChangeRequest,
} from "@/types/schedule.types";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

// Production (Render): 25s to account for cold starts
// Development: 15s for faster feedback
const TIMEOUT = 60000; // Increased to 60s for Cloud DB resilience

// ──────────────────────────────────────────────────────────────────────────
// Axios instance — all requests go through here
// ──────────────────────────────────────────────────────────────────────────
const api = axios.create({
  baseURL: BACKEND_URL,
  headers: { "Content-Type": "application/json" },
  timeout: TIMEOUT,
});

// ──────────────────────────────────────────────────────────────────────────
// Request interceptor — attach JWT token automatically
// ──────────────────────────────────────────────────────────────────────────
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    if (typeof window !== "undefined") {
      const token = localStorage.getItem("access_token");
      if (token && config.headers) {
        config.headers.Authorization = `Bearer ${token}`;
      }

      // Inject Active Project ID into headers if present
      try {
        const storedProjectJson = localStorage.getItem("crm-project");
        if (storedProjectJson) {
          const { state } = JSON.parse(storedProjectJson);
          const projId = state?.activeProject?.project_id || state?.activeProject?._id;
          if (projId) {
            config.headers["X-Project-Id"] = String(projId);
          } else if (typeof window !== "undefined") {
            // Fallback: extract project ID from URL if on a project-specific page
            const pathParts = window.location.pathname.split("/");
            const projectsIdx = pathParts.indexOf("projects");
            if (projectsIdx !== -1 && pathParts[projectsIdx + 1]) {
              const urlProjectId = pathParts[projectsIdx + 1];
              config.headers["X-Project-Id"] = urlProjectId;
            }
          }
        }
      } catch (e) {
        errorLogger.error("Failed to parse project storage", { error: e });
      }

      // Inject Nonce for write operations (Point 102)
      if (['post', 'put', 'delete'].includes(config.method?.toLowerCase() || '')) {
        config.headers["X-Request-Nonce"] = `nonce-${Date.now()}-${Math.random().toString(36).substring(2, 11)}`;
      }
    }
    return config;
  },
  (error) => Promise.reject(error),
);

// ──────────────────────────────────────────────────────────────────────────
// Response interceptor — handle token refresh on 401 & unwrap GenericResponse
// ──────────────────────────────────────────────────────────────────────────
api.interceptors.response.use(
  (response) => {
    // Automatically unwrap GenericResponse envelope from DDD v1/v2 routes
    // Better handling for objects with 'success' and 'data' keys to ensure they are correctly unwrapped
    const isEnvelope = response.data &&
      typeof response.data === 'object' &&
      'success' in response.data &&
      'data' in response.data;

    if (isEnvelope && response.data.data !== undefined) {
      return { ...response, data: response.data.data };
    }
    return response;
  },
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean;
    };

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refreshToken = localStorage.getItem("refresh_token");
        if (!refreshToken) {
          clearTokens();
          window.location.href = "/login";
          return Promise.reject(error);
        }

        const refreshRes = await axios.post(`${BACKEND_URL}/api/v1/auth/refresh`, {
          refresh_token: refreshToken,
        });

        // Unwrap GenericResponse manually as we are using the base axios instance
        const { access_token, refresh_token } = refreshRes.data.data || refreshRes.data;
        localStorage.setItem("access_token", access_token);
        localStorage.setItem("refresh_token", refresh_token);

        // Update session cookie for middleware (30 days max-age)
        if (typeof window !== 'undefined') {
          // Use Secure flag in production/https
          const secure = window.location.protocol === 'https:' ? '; Secure' : '';
          document.cookie = `crm_token=${access_token}; path=/; max-age=2592000; SameSite=Lax${secure}`;
        }

        if (originalRequest.headers) {
          originalRequest.headers.Authorization = `Bearer ${access_token}`;
        }
        return api(originalRequest);
      } catch {
        clearTokens();
        window.location.href = "/login";
        return Promise.reject(error);
      }
    }

    return Promise.reject(error);
  },
);

function clearTokens() {
  if (typeof window !== "undefined") {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("user");
  }
}

export default api;

// SWR Fetcher — used across all useSWR hooks
// Fixed CR-19: Extends error object with status code for UI logic
interface ApiError extends Error {
  status?: number;
  info?: unknown;
}

export const fetcher = (url: string) =>
  api.get(url).then((r) => r.data).catch((err) => {
    if (err.response) {
      const error: ApiError = new Error(err.response.data?.message || 'API Error');
      error.status = err.response.status;
      error.info = err.response.data;
      throw error;
    }
    throw err;
  });

// ──────────────────────────────────────────────────────────────────────────
// Scheduler Service
// ──────────────────────────────────────────────────────────────────────────
export const schedulerApi = {
  calculate: (projectId: string, tasks: unknown[], projectStart: string) => {
    if (!projectId || projectId === "" || projectId === "undefined") {
      console.error("SCHEDULER_API: Invalid projectId for calculation", { projectId });
      return Promise.reject(new Error("Valid Project ID is required for calculation"));
    }
    return api.post(`/api/v1/projects/${projectId}/calculate-schedule`, { tasks, project_start: projectStart }).then(res => res.data);
  },

  calculateChange: (
    projectId: string,
    changeRequest: ScheduleChangeRequest,
    idempotencyKey: string
  ): Promise<ScheduleCalculationResponse> => {
    if (!projectId) {
      return Promise.reject(new Error("Project ID is required for schedule calculation"));
    }
    return api
      .post(`/api/v1/scheduler/${projectId}/calculate`, changeRequest, {
        headers: {
          "Content-Type": "application/json",
          "Idempotency-Key": idempotencyKey,
        },
      })
      .then((res) => res.data);
  },

  save: (projectId: string, tasks: unknown[], projectStart: string, totalCost: number) =>
    api.post(`/api/v1/projects/${projectId}/save-schedule`, {
      tasks,
      project_start: projectStart,
      total_cost: totalCost
    }).then(res => res.data),

  deleteTask: (projectId: string, taskId: string) =>
    api.delete(`/api/v1/projects/${projectId}/tasks/${taskId}`).then(res => res.data),

  load: (projectId: string) =>
    api.get(`/api/v1/projects/${projectId}/load-schedule`).then(res => res.data),

  exportPdf: (projectId: string) =>
    api.post(`/api/v1/projects/${projectId}/export/pdf`).then(res => res.data),

  downloadPdf: (projectId: string) =>
    api.get(`/api/v1/projects/${projectId}/export/download`, {
      responseType: "blob"
    }),

  getExportStatus: (projectId: string) =>
    api.get(`/api/v1/projects/${projectId}/export/status`).then(res => res.data),

  importMpp: (projectId: string, formData: FormData) =>
    api.post(`/api/v1/projects/${projectId}/import`, formData, {
      headers: { "Content-Type": "multipart/form-data" }
    }).then(res => res.data),

  getCashFlow: (projectId: string) =>
    api.post(`/api/v1/projects/${projectId}/report/cash-flow`).then(res => res.data),

  lockBaseline: (projectId: string, label: string, idempotencyKey: string) =>
    api.post(`/api/v1/projects/${projectId}/baseline/lock`, { project_id: projectId, label, idempotency_key: idempotencyKey }).then(res => res.data),

  compareBaselines: (projectId: string, baselineA: number, baselineB?: number) =>
    api.get(`/api/v1/projects/${projectId}/baseline/compare`, { params: { baseline_a: baselineA, baseline_b: baselineB } }).then(res => res.data),

  migrateLegacyData: (projectId: string, dryRun: boolean = true) =>
    api.post(`/api/v1/scheduler/${projectId}/migrate`, null, { params: { dry_run: dryRun } }).then(res => res.data),
};

export const portfolioApi = {
  getSummary: () => api.get("/api/v1/portfolio/summary").then(res => res.data),
  getResourceHeatmap: () => api.get("/api/v1/portfolio/resource-heatmap").then(res => res.data),
  getMilestones: () => api.get("/api/v1/portfolio/milestones").then(res => res.data),
};
