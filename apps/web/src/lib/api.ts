import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";
import { errorLogger } from "./errorLogger";
import type {
  ScheduleCalculationResponse,
  ScheduleChangeRequest,
} from "@/types/schedule.types";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

// ──────────────────────────────────────────────────────────────────────────
// Axios instance — all requests go through here
// ──────────────────────────────────────────────────────────────────────────
const api = axios.create({
  baseURL: BACKEND_URL,
  headers: { "Content-Type": "application/json" },
  timeout: 15000,
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
          if (state?.activeProject?._id) {
            config.headers["X-Project-Id"] = state.activeProject._id;
          } else if (state?.activeProject?.project_id) {
            config.headers["X-Project-Id"] = state.activeProject.project_id;
          }
        }
      } catch (e) {
        errorLogger.error("Failed to parse project storage", { error: e });
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
    if (response.data && response.data.data !== undefined && 'status' in response.data) {
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

        const res = await axios.post(`${BACKEND_URL}/api/v1/auth/refresh`, {
          refresh_token: refreshToken,
        });

        const { access_token, refresh_token } = res.data;
        localStorage.setItem("access_token", access_token);
        localStorage.setItem("refresh_token", refresh_token);

        // Update session cookie for middleware (30 days max-age)
        if (typeof window !== 'undefined') {
          document.cookie = `crm_token=${access_token}; path=/; max-age=2592000; SameSite=Lax`;
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

// ──────────────────────────────────────────────────────────────────────────
// SWR Fetcher — used across all useSWR hooks
// ──────────────────────────────────────────────────────────────────────────
export const fetcher = (url: string) => api.get(url).then((r) => r.data);

// ──────────────────────────────────────────────────────────────────────────
// Scheduler Service
// ──────────────────────────────────────────────────────────────────────────
export const schedulerApi = {
  calculate: (projectId: string, tasks: any[], projectStart: string) =>
    api.post(`/api/v1/projects/${projectId}/calculate`, { tasks, project_start: projectStart }).then(res => res.data),

  calculateChange: (
    projectId: string,
    changeRequest: ScheduleChangeRequest,
    idempotencyKey: string
  ): Promise<ScheduleCalculationResponse> =>
    api
      .post(`/api/v2/scheduler/${projectId}/calculate`, changeRequest, {
        headers: {
          "Content-Type": "application/json",
          "Idempotency-Key": idempotencyKey,
        },
      })
      .then((res) => res.data),

  save: (projectId: string, tasks: any[], projectStart: string, totalCost: number) =>
    api.post(`/api/v1/projects/${projectId}/save`, {
      tasks,
      project_start: projectStart,
      total_cost: totalCost
    }).then(res => res.data),

  load: (projectId: string) =>
    api.get(`/api/v1/projects/${projectId}/load`).then(res => res.data),

  exportPdf: (projectId: string) =>
    api.post(`/api/v1/projects/${projectId}/export/pdf`).then(res => res.data),

  downloadPdf: (projectId: string) =>
    api.get(`/api/projects/${projectId}/export/download`, {
      responseType: "blob"
    }),

  getExportStatus: (projectId: string) =>
    api.get(`/api/projects/${projectId}/export/status`).then(res => res.data),

  importMpp: (projectId: string, formData: FormData) =>
    api.post(`/api/projects/${projectId}/import`, formData, {
      headers: { "Content-Type": "multipart/form-data" }
    }).then(res => res.data),

  getCashFlow: (projectId: string) =>
    api.post(`/api/v1/projects/${projectId}/report/cash-flow`).then(res => res.data),

  lockBaseline: (projectId: string, label: string, idempotencyKey: string) =>
    api.post(`/api/v1/projects/${projectId}/baseline/lock`, { project_id: projectId, label, idempotency_key: idempotencyKey }).then(res => res.data),

  compareBaselines: (projectId: string, baselineA: number, baselineB?: number) =>
    api.get(`/api/v1/projects/${projectId}/baseline/compare`, { params: { baseline_a: baselineA, baseline_b: baselineB } }).then(res => res.data),

  migrateLegacyData: (projectId: string, dryRun: boolean = true) =>
    api.post(`/api/v2/scheduler/${projectId}/migrate`, null, { params: { dry_run: dryRun } }).then(res => res.data),
};

export const portfolioApi = {
  getSummary: () => api.get("/api/v2/portfolio/summary").then(res => res.data),
  getResourceHeatmap: () => api.get("/api/v2/portfolio/resource-heatmap").then(res => res.data),
  getMilestones: () => api.get("/api/v2/portfolio/milestones").then(res => res.data),
};
