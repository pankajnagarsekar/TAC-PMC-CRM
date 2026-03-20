"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import useSWR from "swr";
import { ColDef } from "ag-grid-community";
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
  LayoutGrid
} from "lucide-react";
import api, { fetcher } from "@/lib/api";
import { Project } from "@/types/api";
import ProjectModal from "@/components/projects/ProjectModal";
import FinancialGrid from "@/components/ui/FinancialGrid";

export default function ProjectsPage() {
  const {
    data: projects,
    mutate,
    isLoading,
    error
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
        headerName: "Project Identity",
        field: "project_name",
        flex: 2.5,
        cellRenderer: (params: any) => (
          <div className="flex items-center gap-3 py-2">
            <div className="w-9 h-9 rounded-xl bg-orange-500/10 flex items-center justify-center text-orange-500 border border-orange-500/20 shadow-inner">
              <LayoutGrid size={18} />
            </div>
            <div className="flex flex-col">
              <span className="font-bold text-white leading-tight">
                {params.value}
              </span>
              <span className="text-[10px] text-slate-500 font-mono mt-0.5 tracking-wider">
                {params.data.project_code || "NO-CODE"}
              </span>
            </div>
          </div>
        ),
      },
      {
        headerName: "Stakeholder",
        field: "client_name",
        flex: 1.5,
        cellRenderer: (params: any) => (
          <div className="flex items-center gap-2 text-slate-300">
            <Building size={14} className="text-slate-500" />
            <span className="font-medium text-xs">{params.value || "Internal"}</span>
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
              {params.value || params.data.city || "Remote"}
            </span>
          </div>
        ),
      },
      {
        headerName: "Operational Status",
        field: "status",
        width: 150,
        cellRenderer: (params: any) => {
          const status = params.value?.toLowerCase() || 'pending';
          return (
            <div className="flex items-center h-full">
              <span
                className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[10px] font-black uppercase tracking-widest border ${status === "active"
                    ? "bg-emerald-500/10 text-emerald-500 border-emerald-500/20 shadow-[0_0_12px_rgba(16,185,129,0.05)]"
                    : status === "completed"
                      ? "bg-blue-500/10 text-blue-500 border-blue-500/20"
                      : "bg-slate-500/10 text-slate-500 border-slate-500/20"
                  }`}
              >
                {status === "active" ? (
                  <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                ) : (
                  <div className="w-1.5 h-1.5 rounded-full bg-slate-500" />
                )}
                {status}
              </span>
            </div>
          );
        }
      },
      {
        headerName: "Actions",
        field: "_id",
        width: 140,
        cellClass: "admin-only",
        cellRenderer: (params: any) => (
          <div className="flex items-center justify-end h-full gap-1 px-1">
            <button
              onClick={() => handleEdit(params.data)}
              className="p-2 hover:bg-white/5 rounded-lg text-slate-400 hover:text-white transition-all active:scale-90"
              title="Edit Profile"
            >
              <Edit2 size={15} />
            </button>
            <button
              onClick={() => handleInitializeBudgets(params.value)}
              disabled={!!initLoading}
              className="p-2 hover:bg-emerald-500/10 rounded-lg text-slate-400 hover:text-emerald-500 transition-all active:scale-90 disabled:opacity-50"
              title="Compute Budgets"
            >
              {initLoading === params.value ? (
                <Loader2 size={15} className="animate-spin" />
              ) : (
                <Wallet size={15} />
              )}
            </button>
            <Link
              href={`/admin/projects/${params.data._id}`}
              className="p-2 hover:bg-orange-500/10 rounded-lg text-slate-400 hover:text-orange-500 transition-all active:scale-90"
              title="Enterprise View"
            >
              <ExternalLink size={15} />
            </Link>
          </div>
        ),
      },
    ],
    [initLoading],
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
      !confirm("System will initialize base-level budgets for all cost codes. Proceed?")
    )
      return;
    setInitLoading(projectId);
    try {
      await api.post(`/api/v2/projects/${projectId}/initialize-budgets`);
      alert("Project financial structure initialized.");
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to initialize financials.");
    } finally {
      setInitLoading(null);
    }
  }

  return (
    <div className="p-6 space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-700">
      {/* Header Container */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
        <div className="space-y-1">
          <h1 className="text-3xl font-black text-white tracking-tight flex items-center gap-4">
            <div className="p-2 bg-orange-500/10 border border-orange-500/20 rounded-2xl shadow-inner">
              <Layout size={24} className="text-orange-500" />
            </div>
            Portfolio Control
          </h1>
          <p className="text-slate-500 text-sm font-medium pl-14">
            Monitoring <span className="text-orange-500/80 font-bold">{projects?.length || 0}</span> strategic assets across the organization.
          </p>
        </div>

        <button
          onClick={handleAddNew}
          className="admin-only bg-orange-600 hover:bg-orange-500 text-white px-6 py-3 rounded-[1.2rem] font-black text-xs uppercase tracking-[0.15em] flex items-center justify-center gap-3 transition-all shadow-xl shadow-orange-900/20 active:scale-95 border border-white/10"
        >
          <Plus size={18} strokeWidth={3} />
          Create New Asset
        </button>
      </div>

      {/* Main Glass Shell */}
      <div className="bg-slate-900/40 border border-white/5 rounded-[2.5rem] p-6 space-y-6 shadow-2xl backdrop-blur-sm overflow-hidden">
        {/* Visual Controls */}
        <div className="flex flex-col md:flex-row gap-4 items-center justify-between">
          <div className="relative w-full md:w-96 group">
            <Search
              className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 group-focus-within:text-orange-500 transition-colors"
              size={18}
            />
            <input
              type="text"
              placeholder="Search project registry..."
              className="w-full bg-slate-950/80 border border-white/5 rounded-2xl pl-12 pr-4 py-3 text-sm text-white focus:outline-none focus:border-orange-500/40 transition-all placeholder:text-slate-700"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>

          <div className="flex items-center gap-8 px-6 py-2 bg-slate-950/40 rounded-2xl border border-white/5">
            <div className="flex items-center gap-3 group">
              <div className="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.4)]" />
              <div className="flex flex-col">
                <span className="text-[10px] text-slate-500 font-black uppercase tracking-widest leading-none">Active</span>
                <span className="text-xs text-white font-bold">{projects?.filter((p) => p.status === "active").length || 0}</span>
              </div>
            </div>
            <div className="w-px h-6 bg-white/5" />
            <div className="flex items-center gap-3">
              <div className="w-2 h-2 rounded-full bg-orange-500/50" />
              <div className="flex flex-col">
                <span className="text-[10px] text-slate-500 font-black uppercase tracking-widest leading-none">Global</span>
                <span className="text-xs text-white font-bold">{projects?.length || 0} Assets</span>
              </div>
            </div>
          </div>
        </div>

        {/* Intelligence Grid */}
        <div className="relative min-h-[500px]">
          {error ? (
            <div className="absolute inset-0 flex items-center justify-center bg-rose-500/5 border border-rose-500/20 rounded-[2rem]">
              <div className="text-center space-y-4">
                <XCircle className="w-12 h-12 text-rose-500 mx-auto opacity-50" />
                <p className="text-rose-200 font-bold">Registry Access Failure</p>
                <button onClick={() => mutate()} className="text-[10px] font-black uppercase tracking-widest text-white bg-rose-600 px-4 py-2 rounded-xl">Retry Connection</button>
              </div>
            </div>
          ) : (
            <FinancialGrid<Project>
              rowData={projects || []}
              columnDefs={columnDefs}
              loading={isLoading}
              height="calc(100vh - 380px)"
              quickFilterText={searchTerm}
            />
          )}
        </div>
      </div>

      <ProjectModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSuccess={() => mutate()}
        project={selectedProject}
      />
    </div>
  );
}
