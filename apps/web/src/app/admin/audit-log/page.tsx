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
  FileText,
  Calendar,
  Eye,
  X
} from "lucide-react";
import api from "@/lib/api";
import { exportToCSV } from "@/lib/utils";

interface AuditLogEntry {
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
  return (
    <React.Suspense fallback={<div className="h-20 animate-pulse bg-slate-900 rounded-xl m-6" />}>
      <AuditLogContent />
    </React.Suspense>
  );
}

function AuditLogContent() {
  const searchParams = useSearchParams();
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [selectedLog, setSelectedLog] = useState<AuditLogEntry | null>(null);
  const [filters, setFilters] = useState<AuditLogFilters>({
    entity_type: searchParams.get("entity_type") || "",
    entity_id: searchParams.get("entity_id") || "",
    project_id: searchParams.get("project_id") || "",
    action_type: "",
    start_date: "",
    end_date: "",
  });
  const [showFilters, setShowFilters] = useState(false);

  const fetchLogs = React.useCallback(async (pageNum: number = 1, append: boolean = false) => {
    try {
      setLoading(true);

      const params = new URLSearchParams();
      params.append("limit", "50");
      params.append("page", pageNum.toString());

      if (filters.entity_type)
        params.append("entity_type", filters.entity_type);
      if (filters.entity_id) params.append("entity_id", filters.entity_id);
      if (filters.project_id) params.append("project_id", filters.project_id);
      if (filters.action_type)
        params.append("action_type", filters.action_type);

      const response = await api.get(`/api/v1/audit/logs?${params.toString()}`);
      const data = response.data;

      setLogs((prev) => (append ? [...prev, ...data] : data));
      setHasMore(data.length === 50);
    } catch {
      // Log error internally if needed
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    fetchLogs(page, false);
  }, [
    page,
    fetchLogs
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
        return "bg-emerald-500/10 text-emerald-500 border-emerald-500/20";
      case "UPDATE":
        return "bg-blue-500/10 text-blue-500 border-blue-500/20";
      case "DELETE":
        return "bg-rose-500/10 text-rose-500 border-rose-500/20";
      case "CLOSE":
        return "bg-purple-500/10 text-purple-500 border-purple-500/20";
      case "APPROVE":
        return "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
      case "REJECT":
        return "bg-orange-500/10 text-orange-500 border-orange-500/20";
      default:
        return "bg-slate-500/10 text-slate-400 border-slate-500/20";
    }
  };

  const exportLogs = () => {
    exportToCSV(logs as unknown as Record<string, unknown>[], "audit_ledger");
  };

  return (
    <div className="p-6 space-y-6 animate-in fade-in duration-500">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <History className="text-blue-500" />
            Audit Ledger
          </h1>
          <p className="text-slate-500 text-sm mt-1">
            System-wide activity tracking for security and financial integrity.
          </p>
        </div>

        <div className="flex gap-3">
          <button
            onClick={() => fetchLogs(page, false)}
            className="p-2.5 bg-slate-900 border border-slate-800 text-slate-400 hover:text-white rounded-xl transition-all"
          >
            <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={exportLogs}
            className="flex items-center gap-2 px-4 py-2.5 text-sm font-bold text-white bg-slate-800 hover:bg-slate-700 rounded-xl transition-all border border-white/5"
          >
            <Download className="w-4 h-4" />
            Export Data
          </button>
        </div>
      </div>

      {/* Filters Container */}
      <div className="bg-slate-900/40 border border-white/5 rounded-[2rem] overflow-hidden">
        <div className="p-5 border-b border-white/5 flex items-center justify-between">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`flex items-center gap-2 font-bold text-xs uppercase tracking-widest px-4 py-2 rounded-xl transition-all ${showFilters ? 'bg-orange-500 text-white shadow-lg shadow-orange-500/20' : 'bg-white/5 text-slate-400'}`}
          >
            <Filter className="w-4 h-4" />
            {showFilters ? 'Hide Filters' : 'Show Filters'}
          </button>

          <div className="hidden md:flex gap-4">
            <div className="flex items-center gap-2 text-[10px] font-black text-slate-500 uppercase tracking-tighter">
              <div className="w-1.5 h-1.5 rounded-full bg-blue-500" />
              Live Monitoring Active
            </div>
          </div>
        </div>

        {showFilters && (
          <div className="p-6 grid grid-cols-1 md:grid-cols-4 gap-6 bg-slate-950/20">
            <div className="space-y-2">
              <label className="block text-[10px] font-black text-slate-500 uppercase tracking-widest">
                Entity Type
              </label>
              <select
                value={filters.entity_type}
                onChange={(e) =>
                  handleFilterChange("entity_type", e.target.value)
                }
                className="w-full px-4 py-2.5 bg-slate-950 border border-slate-800 text-white rounded-xl text-sm focus:outline-none focus:border-blue-500/50"
              >
                {ENTITY_TYPES.map((type) => (
                  <option key={type.value} value={type.value}>
                    {type.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-2">
              <label className="block text-[10px] font-black text-slate-500 uppercase tracking-widest">
                Action Type
              </label>
              <select
                value={filters.action_type}
                onChange={(e) =>
                  handleFilterChange("action_type", e.target.value)
                }
                className="w-full px-4 py-2.5 bg-slate-950 border border-slate-800 text-white rounded-xl text-sm focus:outline-none focus:border-blue-500/50"
              >
                {ACTION_TYPES.map((type) => (
                  <option key={type.value} value={type.value}>
                    {type.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-2">
              <label className="block text-[10px] font-black text-slate-500 uppercase tracking-widest">
                Identifier ID
              </label>
              <input
                type="text"
                value={filters.entity_id}
                onChange={(e) =>
                  handleFilterChange("entity_id", e.target.value)
                }
                placeholder="ID Search..."
                className="w-full px-4 py-2.5 bg-slate-950 border border-slate-800 text-white rounded-xl text-sm focus:outline-none focus:border-blue-500/50 placeholder:text-slate-700"
              />
            </div>

            <div className="flex items-end gap-3">
              <button
                onClick={clearFilters}
                className="flex-1 px-4 py-2.5 text-xs font-bold text-slate-400 bg-white/5 hover:bg-white/10 rounded-xl transition-all border border-white/5"
              >
                Reset
              </button>
            </div>
          </div>
        )}

        {/* Table Data */}
        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr className="bg-slate-950/40 border-b border-white/5">
                <th className="px-6 py-4 text-left text-[10px] font-black text-slate-500 uppercase tracking-[0.2em]">Timestamp</th>
                <th className="px-6 py-4 text-left text-[10px] font-black text-slate-500 uppercase tracking-[0.2em]">Action</th>
                <th className="px-6 py-4 text-left text-[10px] font-black text-slate-500 uppercase tracking-[0.2em]">Entity</th>
                <th className="px-6 py-4 text-left text-[10px] font-black text-slate-500 uppercase tracking-[0.2em]">User</th>
                <th className="px-6 py-4 text-left text-[10px] font-black text-slate-500 uppercase tracking-[0.2em]">Project</th>
                <th className="px-6 py-4 text-center text-[10px] font-black text-slate-500 uppercase tracking-[0.2em]">inspect</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.02]">
              {logs.map((log) => (
                <tr
                  key={log.log_id}
                  className="hover:bg-white/[0.01] transition-colors group"
                >
                  <td className="px-6 py-4 whitespace-nowrap text-xs text-slate-400 font-mono">
                    {formatDate(log.created_at)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span
                      className={`inline-flex px-2.5 py-1 text-[10px] font-black rounded-lg border leading-none transition-all group-hover:scale-105 ${getActionColor(
                        log.action_type,
                      )}`}
                    >
                      {log.action_type}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center gap-2">
                      <FileText className="w-4 h-4 text-slate-600" />
                      <div className="flex flex-col">
                        <span className="text-xs text-white font-bold">{log.entity_type}</span>
                        <span className="text-[10px] text-slate-600 font-mono">#{log.entity_id.slice(-8)}</span>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center gap-2 text-xs text-slate-300">
                      <div className="w-5 h-5 rounded-full bg-slate-800 flex items-center justify-center text-[10px] font-black text-slate-500">
                        {(log.user_name || "U").charAt(0)}
                      </div>
                      <span>{log.user_name || log.user_id.slice(-8)}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-xs text-slate-400">
                    {log.project_id ? (
                      <div className="flex items-center gap-2">
                        <Calendar className="w-3 h-3 text-slate-600" />
                        <span className="max-w-[150px] truncate">
                          {log.project_name || log.project_id.slice(-8)}
                        </span>
                      </div>
                    ) : (
                      <span className="text-slate-700">—</span>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-center">
                    <button
                      onClick={() => setSelectedLog(log)}
                      className="p-2 text-slate-500 hover:text-blue-500 hover:bg-blue-500/10 rounded-lg transition-all active:scale-90"
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
          <div className="p-20 text-center text-slate-600">
            <History className="w-12 h-12 mx-auto mb-4 opacity-20" />
            <p className="text-lg font-bold text-slate-500">No History Records</p>
            <p className="text-sm">Try adjusting your filters to find specific activity.</p>
          </div>
        )}

        {/* Pagination & Footer */}
        <div className="px-6 py-4 bg-slate-950/40 border-t border-white/5 flex items-center justify-between">
          <p className="text-[10px] font-black text-slate-600 uppercase tracking-widest">
            {logs.length} Entry Results
          </p>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="p-2 text-slate-500 hover:text-white bg-white/5 rounded-xl disabled:opacity-30 disabled:cursor-not-allowed transition-all"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="text-xs font-bold text-white px-3 py-1 bg-white/5 rounded-lg border border-white/5">
              {page}
            </span>
            <button
              onClick={() => setPage((p) => p + 1)}
              disabled={!hasMore}
              className="p-2 text-slate-500 hover:text-white bg-white/5 rounded-xl disabled:opacity-30 disabled:cursor-not-allowed transition-all"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Luxury Modal for Details */}
      {selectedLog && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-4 z-[100] animate-in fade-in duration-300">
          <div className="bg-slate-900 border border-white/10 rounded-[3rem] shadow-2xl max-w-2xl w-full overflow-hidden flex flex-col max-h-[85vh]">
            <div className="p-8 border-b border-white/5 flex items-center justify-between bg-gradient-to-br from-white/[0.02] to-transparent">
              <div>
                <h2 className="text-2xl font-black text-white tracking-tight">Audit Details</h2>
                <p className="text-slate-500 text-xs font-bold uppercase tracking-widest mt-1">Log ID: {selectedLog.log_id}</p>
              </div>
              <button
                onClick={() => setSelectedLog(null)}
                className="p-3 text-slate-500 hover:text-white hover:bg-white/5 rounded-2xl transition-all"
              >
                <X className="w-6 h-6" />
              </button>
            </div>

            <div className="p-8 overflow-y-auto space-y-10 custom-scrollbar">
              <div className="grid grid-cols-2 gap-8">
                <div className="space-y-1.5">
                  <label className="text-[10px] font-black text-slate-500 uppercase tracking-[0.2em]">Execution Time</label>
                  <p className="text-sm text-white font-mono">{formatDate(selectedLog.created_at)}</p>
                </div>
                <div className="space-y-1.5">
                  <label className="text-[10px] font-black text-slate-500 uppercase tracking-[0.2em]">Action Classification</label>
                  <div>
                    <span className={`inline-flex px-3 py-1 text-[10px] font-black rounded-lg border ${getActionColor(selectedLog.action_type)}`}>
                      {selectedLog.action_type}
                    </span>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-8 pt-8 border-t border-white/5">
                <div className="space-y-1.5">
                  <label className="text-[10px] font-black text-slate-500 uppercase tracking-[0.2em]">Affected Entity</label>
                  <p className="text-sm text-white font-black">{selectedLog.entity_type}</p>
                </div>
                <div className="space-y-1.5">
                  <label className="text-[10px] font-black text-slate-500 uppercase tracking-[0.2em]">System Module</label>
                  <p className="text-sm text-white font-medium">{selectedLog.module_name || 'Global'}</p>
                </div>
              </div>

              <div className="space-y-4">
                <label className="text-[10px] font-black text-slate-500 uppercase tracking-[0.2em] block">Data Payload Change</label>

                {selectedLog.previous_state && (
                  <div className="rounded-2xl bg-black/40 border border-white/5 p-5 space-y-3">
                    <p className="text-[9px] font-bold text-slate-600 uppercase tracking-widest">Previous State</p>
                    <pre className="text-[11px] text-slate-400 font-mono overflow-x-auto whitespace-pre-wrap leading-relaxed">
                      {JSON.stringify(selectedLog.previous_state, null, 2)}
                    </pre>
                  </div>
                )}

                {selectedLog.new_value && (
                  <div className="rounded-2xl bg-orange-500/[0.03] border border-orange-500/10 p-5 space-y-3">
                    <p className="text-[9px] font-bold text-orange-500/50 uppercase tracking-widest">New Values Applied</p>
                    <pre className="text-[11px] text-orange-200/70 font-mono overflow-x-auto whitespace-pre-wrap leading-relaxed">
                      {JSON.stringify(selectedLog.new_value, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            </div>

            <div className="p-8 border-t border-white/5 bg-slate-950/20">
              <button
                onClick={() => setSelectedLog(null)}
                className="w-full py-4 text-sm font-black text-slate-200 bg-white/5 hover:bg-white/10 rounded-2xl transition-all uppercase tracking-[0.2em]"
              >
                Acknowledge & Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
