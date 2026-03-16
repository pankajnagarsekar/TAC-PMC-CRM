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
  const [loading, setLoading] = useState(true);
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
    try {
      setLoading(true);
      let url = `/api/projects/${activeProject.project_id}/dprs`;
      const params = new URLSearchParams();
      if (statusFilter !== "all") params.append("status_filter", statusFilter);
      if (startDate) params.append("start_date", startDate);
      if (endDate) params.append("end_date", endDate);

      const response = await api.get(`${url}?${params.toString()}`);
      setDprs(response.data);
    } catch (error) {
      console.error("Error fetching DPRs:", error);
    } finally {
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
          <span className="text-slate-300 font-medium">
            {formatDate(params.value)}
          </span>
        ),
      },
      {
        headerName: "Supervisor",
        field: "supervisor_name",
        flex: 1,
        cellRenderer: (params: any) => (
          <span className="text-slate-400">{params.value || "Unknown"}</span>
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
              "bg-emerald-500/10 text-emerald-500 border-emerald-500/20",
            REJECTED: "bg-rose-500/10 text-rose-500 border-rose-500/20",
            PENDING_APPROVAL:
              "bg-amber-500/10 text-amber-500 border-amber-500/20",
            DRAFT: "bg-slate-500/10 text-slate-500 border-slate-500/20",
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
          <span className="text-xs text-slate-500 truncate block">
            {params.value || "No notes..."}
          </span>
        ),
      },
      {
        headerName: "Photos",
        field: "photos",
        flex: 0.5,
        cellRenderer: (params: any) => (
          <span className="text-slate-400 font-mono text-xs">
            {params.value?.length || 0}
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
            className="text-orange-500 hover:text-orange-400 text-xs font-semibold flex items-center gap-1"
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
      <div className="flex flex-col md:flex-row gap-4 bg-slate-900/50 p-4 rounded-2xl border border-slate-800/50">
        <div className="relative flex-1">
          <Search
            className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500"
            size={16}
          />
          <input
            type="text"
            placeholder="Search notes..."
            className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-9 pr-4 py-2 text-sm text-white focus:outline-none focus:border-orange-500/50 transition-colors"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        <div className="flex flex-wrap gap-2 items-center">
          <div className="flex items-center gap-2 bg-slate-950 border border-slate-800 rounded-xl px-3 py-1.5">
            <Filter size={14} className="text-slate-500" />
            <select
              className="bg-transparent text-sm text-slate-300 outline-none"
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

          <div className="flex items-center gap-2 bg-slate-950 border border-slate-800 rounded-xl px-3 py-1.5">
            <Calendar size={14} className="text-slate-500" />
            <input
              type="date"
              className="bg-transparent text-sm text-slate-300 outline-none"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
            />
            <span className="text-slate-600">-</span>
            <input
              type="date"
              className="bg-transparent text-sm text-slate-300 outline-none"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
            />
          </div>
        </div>
      </div>

      <div className="h-[500px]">
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
