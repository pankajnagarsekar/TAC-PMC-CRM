"use client";

import React, { useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import {
  History,
  Filter,
  Download,
  ChevronLeft,
  ChevronRight,
  RefreshCw,
  User,
  FileText,
  Calendar,
  Eye,
} from "lucide-react";

interface AuditLog {
  log_id: string;
  organisation_id: string;
  module_name: string;
  entity_type: string;
  entity_id: string;
  action_type: "CREATE" | "UPDATE" | "DELETE" | "CLOSE" | "APPROVE" | "REJECT";
  user_id: string;
  user_name?: string;
  project_id?: string;
  project_name?: string;
  previous_state?: Record<string, unknown>;
  new_value?: Record<string, unknown>;
  created_at: string;
}

interface AuditLogFilters {
  entity_type?: string;
  entity_id?: string;
  project_id?: string;
  action_type?: string;
  start_date?: string;
  end_date?: string;
}

const ENTITY_TYPES = [
  { value: "", label: "All Types" },
  { value: "CLIENT", label: "Client" },
  { value: "PROJECT", label: "Project" },
  { value: "WORK_ORDER", label: "Work Order" },
  { value: "PAYMENT_CERTIFICATE", label: "Payment Certificate" },
  { value: "VENDOR", label: "Vendor" },
  { value: "CASH_TRANSACTION", label: "Cash Transaction" },
  { value: "BUDGET", label: "Budget" },
  { value: "SITE_OVERHEAD", label: "Site Overhead" },
  { value: "USER", label: "User" },
];

const ACTION_TYPES = [
  { value: "", label: "All Actions" },
  { value: "CREATE", label: "Create" },
  { value: "UPDATE", label: "Update" },
  { value: "DELETE", label: "Delete" },
  { value: "CLOSE", label: "Close" },
  { value: "APPROVE", label: "Approve" },
  { value: "REJECT", label: "Reject" },
];

export default function AuditLogPage() {
  const searchParams = useSearchParams();
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null);
  const [filters, setFilters] = useState<AuditLogFilters>({
    entity_type: searchParams.get("entity_type") || "",
    entity_id: searchParams.get("entity_id") || "",
    project_id: searchParams.get("project_id") || "",
    action_type: "",
    start_date: "",
    end_date: "",
  });
  const [showFilters, setShowFilters] = useState(false);

  const fetchLogs = async (pageNum: number = 1, append: boolean = false) => {
    try {
      setLoading(true);
      setError(null);

      const params = new URLSearchParams();
      params.append("limit", "50");

      if (filters.entity_type)
        params.append("entity_type", filters.entity_type);
      if (filters.entity_id) params.append("entity_id", filters.entity_id);
      if (filters.project_id) params.append("project_id", filters.project_id);
      if (filters.action_type)
        params.append("action_type", filters.action_type);

      const response = await fetch(`/api/audit-logs?${params.toString()}`);

      if (!response.ok) {
        throw new Error("Failed to fetch audit logs");
      }

      const data = await response.json();
      setLogs(append ? [...logs, ...data] : data);
      setHasMore(data.length === 50);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs(1, false);
  }, [
    filters.entity_type,
    filters.entity_id,
    filters.project_id,
    filters.action_type,
  ]);

  const handleFilterChange = (key: keyof AuditLogFilters, value: string) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
    setPage(1);
  };

  const clearFilters = () => {
    setFilters({
      entity_type: "",
      entity_id: "",
      project_id: "",
      action_type: "",
      start_date: "",
      end_date: "",
    });
    setPage(1);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const getActionColor = (action: string) => {
    switch (action) {
      case "CREATE":
        return "bg-green-100 text-green-800";
      case "UPDATE":
        return "bg-blue-100 text-blue-800";
      case "DELETE":
        return "bg-red-100 text-red-800";
      case "CLOSE":
        return "bg-purple-100 text-purple-800";
      case "APPROVE":
        return "bg-emerald-100 text-emerald-800";
      case "REJECT":
        return "bg-orange-100 text-orange-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  const exportLogs = () => {
    const dataStr = JSON.stringify(logs, null, 2);
    const blob = new Blob([dataStr], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `audit-logs-${new Date().toISOString().split("T")[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <History className="w-6 h-6 text-blue-600" />
          <h1 className="text-2xl font-bold text-gray-900">Audit Log</h1>
        </div>
        <p className="text-gray-600">
          Track all changes to financial records, projects, and system data
        </p>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 mb-6">
        <div className="p-4 border-b border-gray-200 flex items-center justify-between">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className="flex items-center gap-2 text-gray-700 hover:text-gray-900"
          >
            <Filter className="w-4 h-4" />
            <span className="font-medium">Filters</span>
          </button>
          <div className="flex items-center gap-2">
            <button
              onClick={() => fetchLogs(1, false)}
              className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg"
              title="Refresh"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
            <button
              onClick={exportLogs}
              className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg"
            >
              <Download className="w-4 h-4" />
              Export
            </button>
          </div>
        </div>

        {showFilters && (
          <div className="p-4 grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Entity Type
              </label>
              <select
                value={filters.entity_type}
                onChange={(e) =>
                  handleFilterChange("entity_type", e.target.value)
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                {ENTITY_TYPES.map((type) => (
                  <option key={type.value} value={type.value}>
                    {type.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Action
              </label>
              <select
                value={filters.action_type}
                onChange={(e) =>
                  handleFilterChange("action_type", e.target.value)
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                {ACTION_TYPES.map((type) => (
                  <option key={type.value} value={type.value}>
                    {type.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Entity ID
              </label>
              <input
                type="text"
                value={filters.entity_id}
                onChange={(e) =>
                  handleFilterChange("entity_id", e.target.value)
                }
                placeholder="Filter by ID..."
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Project ID
              </label>
              <input
                type="text"
                value={filters.project_id}
                onChange={(e) =>
                  handleFilterChange("project_id", e.target.value)
                }
                placeholder="Filter by project..."
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            <div className="flex items-end">
              <button
                onClick={clearFilters}
                className="w-full px-4 py-2 text-sm font-medium text-gray-600 bg-gray-100 hover:bg-gray-200 rounded-lg"
              >
                Clear Filters
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
          {error}
        </div>
      )}

      {/* Logs Table */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Timestamp
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Action
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Entity
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Module
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  User
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Project
                </th>
                <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Details
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {logs.map((log) => (
                <tr
                  key={log.log_id}
                  className="hover:bg-gray-50 transition-colors"
                >
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                    {formatDate(log.created_at)}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <span
                      className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getActionColor(
                        log.action_type,
                      )}`}
                    >
                      {log.action_type}
                    </span>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                    <div className="flex items-center gap-2">
                      <FileText className="w-4 h-4 text-gray-400" />
                      <span>{log.entity_type}</span>
                      <span className="text-gray-400 text-xs">
                        ({log.entity_id.slice(-8)})
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                    {log.module_name}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                    <div className="flex items-center gap-2">
                      <User className="w-4 h-4 text-gray-400" />
                      <span>{log.user_name || log.user_id.slice(-8)}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                    {log.project_id ? (
                      <div className="flex items-center gap-2">
                        <Calendar className="w-4 h-4 text-gray-400" />
                        <span>
                          {log.project_name || log.project_id.slice(-8)}
                        </span>
                      </div>
                    ) : (
                      <span className="text-gray-400">-</span>
                    )}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-center">
                    <button
                      onClick={() => setSelectedLog(log)}
                      className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                      title="View Details"
                    >
                      <Eye className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {logs.length === 0 && !loading && (
          <div className="p-8 text-center text-gray-500">
            <History className="w-12 h-12 mx-auto mb-4 text-gray-300" />
            <p className="text-lg font-medium">No audit logs found</p>
            <p className="text-sm">Try adjusting your filters</p>
          </div>
        )}

        {loading && (
          <div className="p-8 text-center">
            <div className="animate-spin w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full mx-auto mb-4" />
            <p className="text-gray-500">Loading audit logs...</p>
          </div>
        )}

        {/* Pagination */}
        {logs.length > 0 && (
          <div className="px-4 py-3 border-t border-gray-200 flex items-center justify-between">
            <p className="text-sm text-gray-600">Showing {logs.length} logs</p>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="text-sm text-gray-600">Page {page}</span>
              <button
                onClick={() => setPage((p) => p + 1)}
                disabled={!hasMore}
                className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Detail Modal */}
      {selectedLog && (
        <div
          className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50"
          onClick={() => setSelectedLog(null)}
        >
          <div
            className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-4 border-b border-gray-200 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900">
                Audit Log Details
              </h2>
              <button
                onClick={() => setSelectedLog(null)}
                className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg"
              >
                ×
              </button>
            </div>

            <div className="p-4 overflow-y-auto max-h-[60vh]">
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs font-medium text-gray-500 uppercase">
                      Timestamp
                    </label>
                    <p className="text-sm text-gray-900">
                      {formatDate(selectedLog.created_at)}
                    </p>
                  </div>
                  <div>
                    <label className="text-xs font-medium text-gray-500 uppercase">
                      Action
                    </label>
                    <span
                      className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getActionColor(
                        selectedLog.action_type,
                      )}`}
                    >
                      {selectedLog.action_type}
                    </span>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs font-medium text-gray-500 uppercase">
                      Entity Type
                    </label>
                    <p className="text-sm text-gray-900">
                      {selectedLog.entity_type}
                    </p>
                  </div>
                  <div>
                    <label className="text-xs font-medium text-gray-500 uppercase">
                      Entity ID
                    </label>
                    <p className="text-sm text-gray-900 font-mono">
                      {selectedLog.entity_id}
                    </p>
                  </div>
                </div>

                <div>
                  <label className="text-xs font-medium text-gray-500 uppercase">
                    Module
                  </label>
                  <p className="text-sm text-gray-900">
                    {selectedLog.module_name}
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs font-medium text-gray-500 uppercase">
                      User ID
                    </label>
                    <p className="text-sm text-gray-900 font-mono">
                      {selectedLog.user_id}
                    </p>
                  </div>
                  {selectedLog.user_name && (
                    <div>
                      <label className="text-xs font-medium text-gray-500 uppercase">
                        User Name
                      </label>
                      <p className="text-sm text-gray-900">
                        {selectedLog.user_name}
                      </p>
                    </div>
                  )}
                </div>

                {selectedLog.project_id && (
                  <div>
                    <label className="text-xs font-medium text-gray-500 uppercase">
                      Project
                    </label>
                    <p className="text-sm text-gray-900">
                      {selectedLog.project_name || selectedLog.project_id}
                    </p>
                  </div>
                )}

                {selectedLog.previous_state && (
                  <div>
                    <label className="text-xs font-medium text-gray-500 uppercase">
                      Previous State
                    </label>
                    <pre className="mt-1 p-3 bg-gray-50 rounded-lg text-xs text-gray-700 overflow-auto max-h-40">
                      {JSON.stringify(selectedLog.previous_state, null, 2)}
                    </pre>
                  </div>
                )}

                {selectedLog.new_value && (
                  <div>
                    <label className="text-xs font-medium text-gray-500 uppercase">
                      New Value
                    </label>
                    <pre className="mt-1 p-3 bg-gray-50 rounded-lg text-xs text-gray-700 overflow-auto max-h-40">
                      {JSON.stringify(selectedLog.new_value, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            </div>

            <div className="p-4 border-t border-gray-200 flex justify-end">
              <button
                onClick={() => setSelectedLog(null)}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
