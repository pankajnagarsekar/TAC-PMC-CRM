"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import useSWR from "swr";
import { AgGridReact } from "ag-grid-react";
import { ColDef } from "ag-grid-community";
import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-alpine.css";
import {
  Plus,
  Search,
  Edit2,
  Building,
  CheckCircle2,
  XCircle,
  Layout,
  MapPin,
  ExternalLink,
  Wallet,
  Loader2,
} from "lucide-react";
import api, { fetcher } from "@/lib/api";
import { Project } from "@/types/api";
import ProjectModal from "@/components/projects/ProjectModal";

export default function ProjectsPage() {
  const {
    data: projects,
    mutate,
    isLoading,
  } = useSWR<Project[]>("/api/projects", fetcher);
  const [searchTerm, setSearchTerm] = useState("");
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedProject, setSelectedProject] = useState<Project | undefined>(
    undefined,
  );
  const [initLoading, setInitLoading] = useState<string | null>(null);

  const columnDefs: ColDef<Project>[] = useMemo(
    () => [
      {
        headerName: "Project Name",
        field: "project_name",
        flex: 2,
        cellRenderer: (params: any) => (
          <div className="flex items-center gap-3 py-2">
            <div className="w-8 h-8 rounded-lg bg-orange-500/10 flex items-center justify-center text-orange-500">
              <Layout size={16} />
            </div>
            <div className="flex flex-col">
              <span className="font-semibold text-white leading-tight">
                {params.value}
              </span>
              <span className="text-[10px] text-slate-500 font-mono mt-0.5">
                {params.data.project_code || "NO-CODE"}
              </span>
            </div>
          </div>
        ),
      },
      {
        headerName: "Client",
        field: "client_name",
        flex: 1.5,
        cellRenderer: (params: any) => (
          <div className="flex items-center gap-2 text-slate-300">
            <Building size={14} className="text-slate-500" />
            {params.value || "Direct Project"}
          </div>
        ),
      },
      {
        headerName: "Location",
        field: "address",
        flex: 1.5,
        cellRenderer: (params: any) => (
          <div className="flex items-center gap-2 text-slate-400 text-xs">
            <MapPin size={12} className="text-slate-600" />
            <span className="truncate">
              {params.value || params.data.city || "N/A"}
            </span>
          </div>
        ),
      },
      {
        headerName: "Status",
        field: "status",
        width: 130,
        cellRenderer: (params: any) => (
          <div className="flex items-center h-full">
            <span
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold uppercase tracking-wider ${
                params.value === "active"
                  ? "bg-emerald-500/10 text-emerald-500 border border-emerald-500/20"
                  : params.value === "completed"
                    ? "bg-blue-500/10 text-blue-500 border border-blue-500/20"
                    : "bg-slate-500/10 text-slate-500 border border-slate-500/20"
              }`}
            >
              {params.value === "active" ? (
                <CheckCircle2 size={10} />
              ) : (
                <XCircle size={10} />
              )}
              {params.value}
            </span>
          </div>
        ),
      },
      {
        headerName: "",
        field: "_id",
        width: 120,
        cellRenderer: (params: any) => (
          <div className="flex items-center justify-end h-full gap-2 px-2 admin-only">
            <button
              onClick={() => handleEdit(params.data)}
              className="p-2 hover:bg-slate-800 rounded-lg text-slate-400 hover:text-white transition-colors"
              title="Edit Project"
            >
              <Edit2 size={16} />
            </button>
            <button
              onClick={() => handleInitializeBudgets(params.value)}
              disabled={!!initLoading}
              className="p-2 hover:bg-slate-800 rounded-lg text-slate-400 hover:text-emerald-500 transition-colors disabled:opacity-50"
              title="Initialize Budgets"
            >
              {initLoading === params.value ? (
                <Loader2 size={16} className="animate-spin" />
              ) : (
                <Wallet size={16} />
              )}
            </button>
            <Link
              href={`/admin/projects/${params.data._id}`}
              className="p-2 hover:bg-slate-800 rounded-lg text-slate-400 hover:text-orange-500 transition-colors"
              title="View Details"
            >
              <ExternalLink size={16} />
            </Link>
          </div>
        ),
      },
    ],
    [],
  );

  function handleEdit(project: Project) {
    setSelectedProject(project);
    setIsModalOpen(true);
  }

  function handleAddNew() {
    setSelectedProject(undefined);
    setIsModalOpen(true);
  }

  async function handleInitializeBudgets(projectId: string) {
    if (
      !confirm("This will initialize 0.00 budget for all categories. Continue?")
    )
      return;
    setInitLoading(projectId);
    try {
      await api.post(`/api/v2/projects/${projectId}/initialize-budgets`);
      alert("Budgets initialized successfully.");
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to initialize budgets.");
    } finally {
      setInitLoading(null);
    }
  }

  return (
    <div className="p-6 space-y-6 animate-in fade-in duration-500">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <Layout className="text-orange-500" />
            Project Management
          </h1>
          <p className="text-slate-500 text-sm mt-1">
            Initialize projects, track budgets and manage site locations.
          </p>
        </div>

        <button
          onClick={handleAddNew}
          className="admin-only bg-orange-600 hover:bg-orange-500 text-white px-4 py-2.5 rounded-xl font-semibold text-sm flex items-center gap-2 transition-all shadow-lg shadow-orange-900/20 active:scale-95"
        >
          <Plus size={18} />
          New Project
        </button>
      </div>

      {/* Toolbar */}
      <div className="flex flex-col sm:flex-row gap-4 items-center justify-between bg-slate-900/50 p-4 rounded-2xl border border-slate-800/50">
        <div className="relative w-full sm:w-80">
          <Search
            className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500"
            size={18}
          />
          <input
            type="text"
            placeholder="Search projects..."
            className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-10 pr-4 py-2.5 text-sm text-white focus:outline-none focus:border-orange-500/50 transition-colors"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2 text-xs text-slate-500 font-medium">
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            {projects?.filter((p) => p.status === "active").length || 0} Active
          </div>
          <div className="flex items-center gap-2 text-xs text-slate-500 font-medium border-l border-slate-800 pl-6">
            <span className="w-2 h-2 rounded-full bg-orange-500 animate-pulse" />
            {projects?.length || 0} Total Projects
          </div>
        </div>
      </div>

      {/* Grid */}
      <div className="ag-theme-alpine-dark w-full aspect-[2/1] min-h-[500px] border border-slate-800 rounded-2xl overflow-hidden shadow-2xl">
        <AgGridReact
          rowData={projects}
          columnDefs={columnDefs}
          defaultColDef={{
            sortable: true,
            filter: true,
            resizable: true,
          }}
          quickFilterText={searchTerm}
          pagination={true}
          paginationPageSize={10}
          onGridReady={(params) => params.api.sizeColumnsToFit()}
        />
      </div>

      <ProjectModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSuccess={() => mutate()}
        project={selectedProject}
      />

      <style jsx global>{`
        .ag-theme-alpine-dark {
          --ag-background-color: #020617;
          --ag-header-background-color: #0f172a;
          --ag-border-color: #1e293b;
          --ag-secondary-border-color: #1e293b;
          --ag-header-foreground-color: #94a3b8;
          --ag-data-color: #f8fafc;
          --ag-odd-row-background-color: #020617;
          --ag-row-hover-color: rgba(249, 115, 22, 0.05);
          --ag-selected-row-background-color: rgba(249, 115, 22, 0.1);
          --ag-font-family: "Inter", sans-serif;
          --ag-font-size: 13px;
        }
        .ag-header-cell-label {
          justify-content: start;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.05em;
          font-size: 11px;
        }
        .ag-row {
          border-bottom-color: #0f172a !important;
        }
      `}</style>
    </div>
  );
}
