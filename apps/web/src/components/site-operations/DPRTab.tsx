"use client";

import React, { useState, useEffect, useMemo } from "react";
import FinancialGrid from "@/components/ui/FinancialGrid";
import { useRouter } from "next/navigation";
import { useProjectStore } from "@/store/projectStore";
import api from "@/lib/api";
import { Search, Calendar, Filter, ExternalLink } from "lucide-react";
import { ColDef } from "ag-grid-community";

export default function DPRTab() {
  const router = useRouter();
  const { activeProject } = useProjectStore();
  const [dprs, setDprs] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");

  useEffect(() => {
    if (activeProject?.project_id) {
      fetchDPRs();
    }
  }, [activeProject, statusFilter, startDate, endDate]);

  const fetchDPRs = async () => {
    if (!activeProject?.project_id) return;

    const timeoutId = setTimeout(() => {
      if (loading) {
        setLoading(false);
        setError("Report connection timed out. Please refresh.");
      }
    }, 10000);

    try {
      setLoading(true);
      setError(null);
      const url = `/api/v1/projects/${activeProject.project_id}/dprs`;
      const params = new URLSearchParams();
      if (statusFilter !== "all") params.append("status_filter", statusFilter);
      if (startDate) params.append("start_date", startDate);
      if (endDate) params.append("end_date", endDate);

      const response = await api.get(`${url}?${params.toString()}`);
      setDprs(response.data);
    } catch (err: any) {
      console.error("Error fetching DPRs:", err);
      setError(err.response?.data?.detail || "Failed to retrieve project reports.");
    } finally {
      clearTimeout(timeoutId);
      setLoading(false);
    }
  };

  const formatDate = (dateStr: string) => {
    if (!dateStr) return "N/A";
    return new Intl.DateTimeFormat("en-GB", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    }).format(new Date(dateStr));
  };

  const columnDefs: ColDef[] = useMemo(
    () => [
      {
        headerName: "Date",
        field: "date",
        flex: 1,
        cellRenderer: (params: any) => (
          <span className="text-zinc-900 dark:text-zinc-300 font-medium">
            {formatDate(params.value)}
          </span>
        ),
      },
      {
        headerName: "Supervisor",
        field: "supervisor_name",
        flex: 1,
        cellRenderer: (params: any) => (
          <span className="text-zinc-500 dark:text-slate-400">{params.value || "Unknown"}</span>
        ),
      },
      {
        headerName: "Status",
        field: "status",
        flex: 1,
        cellRenderer: (params: any) => {
          const val = (params.value || "DRAFT").toUpperCase();
          const colors: Record<string, string> = {
            APPROVED:
              "bg-emerald-500/10 text-emerald-600 dark:text-emerald-500 border-emerald-500/20",
            REJECTED: "bg-rose-500/10 text-rose-600 dark:text-rose-500 border-rose-500/20",
            PENDING_APPROVAL:
              "bg-amber-500/10 text-amber-600 dark:text-amber-500 border-amber-500/20",
            DRAFT: "bg-zinc-500/10 text-zinc-600 dark:text-slate-500 border-zinc-500/20",
          };
          return (
            <span
              className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider border ${colors[val] || colors.DRAFT}`}
            >
              {val.replace(/_/g, " ")}
            </span>
          );
        },
      },
      {
        headerName: "Notes Preview",
        field: "progress_notes",
        flex: 2,
        cellRenderer: (params: any) => (
          <span className="text-xs text-zinc-500 dark:text-slate-500 truncate block">
            {params.value || "No notes recorded..."}
          </span>
        ),
      },
      {
        headerName: "Media",
        field: "photos",
        flex: 0.5,
        cellRenderer: (params: any) => (
          <span className={`text-xs font-mono ${params.value?.length ? 'text-orange-600 dark:text-orange-400' : 'text-zinc-400 dark:text-slate-700'}`}>
            [{params.value?.length || 0}]
          </span>
        ),
      },
      {
        headerName: "Action",
        width: 100,
        cellRenderer: (params: any) => (
          <button
            onClick={() =>
              router.push(`/admin/site-operations/dprs/${params.data._id}`)
            }
            className="text-orange-600 dark:text-orange-500 hover:text-orange-500 dark:hover:text-orange-400 text-xs font-semibold flex items-center gap-1 transition-colors"
          >
            Details <ExternalLink size={12} />
          </button>
        ),
      },
    ],
    [router],
  );

  return (
    <div className="space-y-4">
      {/* Search & Filters */}
      <div className="flex flex-col md:flex-row gap-4 bg-zinc-50 dark:bg-slate-900/50 p-4 rounded-2xl border border-zinc-200 dark:border-slate-800/50 transition-colors">
        <div className="relative flex-1">
          <Search
            className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400 dark:text-slate-500"
            size={16}
          />
          <input
            type="text"
            placeholder="Search notes..."
            className="w-full bg-white dark:bg-slate-950 border border-zinc-200 dark:border-slate-800 rounded-xl pl-9 pr-4 py-2 text-sm text-zinc-900 dark:text-white focus:outline-none focus:border-orange-500/50 transition-colors"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        <div className="flex flex-wrap gap-2 items-center">
          <div className="flex items-center gap-2 bg-white dark:bg-slate-950 border border-zinc-200 dark:border-slate-800 rounded-xl px-3 py-1.5 transition-colors">
            <Filter size={14} className="text-zinc-400 dark:text-slate-500" />
            <select
              className="bg-transparent text-sm text-zinc-600 dark:text-slate-300 outline-none cursor-pointer"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="all">All Status</option>
              <option value="DRAFT">Draft</option>
              <option value="PENDING_APPROVAL">Pending Approval</option>
              <option value="APPROVED">Approved</option>
              <option value="REJECTED">Rejected</option>
            </select>
          </div>

          <div className="flex items-center gap-2 bg-white dark:bg-slate-950 border border-zinc-200 dark:border-slate-800 rounded-xl px-3 py-1.5 transition-colors">
            <Calendar size={14} className="text-zinc-400 dark:text-slate-500" />
            <input
              type="date"
              className="bg-transparent text-sm text-zinc-600 dark:text-slate-300 outline-none select-none cursor-pointer"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
            />
            <span className="text-zinc-300 dark:text-slate-600">-</span>
            <input
              type="date"
              className="bg-transparent text-sm text-zinc-600 dark:text-slate-300 outline-none select-none cursor-pointer"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
            />
          </div>
        </div>
      </div>

      <div className="h-[500px] relative">
        {error && (
          <div className="absolute inset-x-0 -top-2 flex justify-center z-10">
            <div className="bg-rose-500/10 border border-rose-500/20 text-rose-600 dark:text-rose-500 text-[10px] px-3 py-1 rounded-full font-bold uppercase tracking-tighter backdrop-blur-md">
              {error}
            </div>
          </div>
        )}
        <FinancialGrid<any>
          columnDefs={columnDefs}
          rowData={dprs}
          loading={loading}
          quickFilterText={searchTerm}
        />
      </div>
    </div>
  );
}
