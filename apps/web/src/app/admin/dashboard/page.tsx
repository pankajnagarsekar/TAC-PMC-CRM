"use client";
import React from "react";
import useSWR from "swr";
import Link from "next/link";
import {
  TrendingUp,
  Wallet,
  FileText,
  CheckCircle2,
  AlertTriangle,
  ArrowUpRight,
  TrendingDown,
  LayoutGrid,
  ExternalLink,
  Search,
  ChevronRight,
  Building2,
  Loader2,
  FolderOpen,
} from "lucide-react";
import { fetcher } from "@/lib/api";
import { Project, DerivedFinancialState, VendorPayable, CashSummaryResponse, WorkOrder } from "@/types/api";
import { useProjectStore } from "@/store/projectStore";
import { useAuthStore } from "@/store/authStore";
import { AISummaryCard } from "@/components/dashboard/AISummaryCard";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import NetworkErrorRetry from "@/components/ui/NetworkErrorRetry";
import { formatCurrencySafe, formatPercentSafe, normalizeFinancial } from "@/lib/formatters";
import FinancialChart from "@/components/ui/FinancialChart";

import { GlassCard } from "@/components/ui/GlassCard";
import {
  Camera,
  Clock,
  Calendar,
  ListTodo,
  History,
  GanttChartSquare,
  BarChart4
} from "lucide-react";

interface DashboardStats {
  project_id: string;
  overview: {
    total_phases: number;
    active_items: number;
    overdue_milestones: number;
    master_budget: number;
    total_committed: number;
  };
  schedule_status: {
    variance: number;
    critical_path_status: string;
  };
  task_log: {
    open_tasks: number;
    resolved_tasks: number;
    compliance_rate: number;
  };
  task_manager: Array<{
    id: string;
    label: string;
    priority: string;
    color: string;
  }>;
}

export default function AdminDashboard() {
  const { activeProject, setActiveProject } = useProjectStore();
  const { user } = useAuthStore();
  const [projectSearch, setProjectSearch] = React.useState("");

  const { data: projects, error: projectsError, isLoading: projectsLoading } = useSWR<Project[]>(
    user ? "/api/projects" : null,
    fetcher
  );

  const filteredProjects = React.useMemo(() => {
    if (!projects) return [];
    const q = projectSearch.toLowerCase();
    return projects.filter(
      (p) =>
        p.project_name.toLowerCase().includes(q) ||
        (p.project_code || "").toLowerCase().includes(q)
    );
  }, [projectSearch, projects]);

  const { data: financials, error: financialsError, isLoading, mutate: retryFinancials } = useSWR<DerivedFinancialState[]>(
    activeProject
      ? `/api/v1/projects/${activeProject.project_id}/financials`
      : null,
    fetcher,
  );

  const { data: vendorPayables } = useSWR<VendorPayable[]>(
    activeProject ? `/api/v1/projects/${activeProject.project_id}/vendor-payables` : null,
    fetcher
  );

  const { data: cashSummary } = useSWR<CashSummaryResponse>(
    activeProject ? `/api/v1/cash/summary/${activeProject.project_id}` : null,
    fetcher
  );

  const { data: woResponse } = useSWR<{ items: WorkOrder[]; next_cursor: string | null }>(
    activeProject ? `/api/v1/work-orders?project_id=${activeProject.project_id}&limit=500` : null,
    fetcher
  );

  const { data: stats } = useSWR<DashboardStats>(
    activeProject ? `/api/v1/projects/${activeProject.project_id}/dashboard-stats` : null,
    fetcher
  );

  const chartData = React.useMemo(() => {
    if (!financials) return [];
    return financials.slice(0, 8).map(f => ({
      name: f.category_name || f.category_code || f.category_id.substring(0, 6),
      budget: normalizeFinancial(f.original_budget),
      committed: normalizeFinancial(f.committed_value)
    }));
  }, [financials]);

  const totalBudget = React.useMemo(() => {
    if (stats?.overview.master_budget) return stats.overview.master_budget;
    if (activeProject?.master_original_budget) return activeProject.master_original_budget;
    return (financials ?? []).reduce((sum, f) => sum + normalizeFinancial(f.original_budget), 0);
  }, [financials, activeProject, stats]);

  if (!activeProject) {
    return (
      <div className="space-y-8 animate-in fade-in duration-700">
        <div className="max-w-4xl mx-auto text-center space-y-4">
          <h1 className="text-4xl font-black tracking-tight text-white uppercase">
            Operational Intelligence
          </h1>
          <p className="text-zinc-500 font-medium">
            Select a strategic project from the registry below to initialize the dashboard and begin financial monitoring.
          </p>
        </div>

        <GlassCard className="max-w-4xl mx-auto">
          <div className="relative mb-6">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-zinc-500" size={18} />
            <input
              type="text"
              placeholder="Search projects by name or code..."
              className="w-full bg-zinc-950/50 border border-white/5 rounded-2xl pl-12 pr-4 py-4 text-white outline-none focus:border-primary/40 transition-all shadow-inner"
              value={projectSearch}
              onChange={(e) => setProjectSearch(e.target.value)}
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {projectsLoading ? (
              Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="h-24 bg-white/5 rounded-2xl animate-pulse" />
              ))
            ) : filteredProjects.length > 0 ? (
              filteredProjects.map((project) => (
                <button
                  key={project.project_id || project._id}
                  onClick={() => setActiveProject(project)}
                  className="flex items-center gap-4 p-4 rounded-2xl bg-white/5 border border-white/5 hover:bg-white/10 hover:border-primary/20 transition-all text-left group active:scale-[0.98]"
                >
                  <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center text-primary border border-primary/20 group-hover:bg-primary group-hover:text-black transition-colors">
                    <LayoutGrid size={24} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h4 className="font-bold text-white truncate">{project.project_name}</h4>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-[10px] font-mono text-zinc-500 tracking-wider">
                        {project.project_code || "NO-CODE"}
                      </span>
                      <span className="w-1 h-1 rounded-full bg-zinc-700" />
                      <span className="text-[10px] font-bold text-emerald-500 uppercase tracking-widest">
                        {project.status}
                      </span>
                    </div>
                  </div>
                  <ChevronRight size={18} className="text-zinc-600 group-hover:text-primary transition-colors" />
                </button>
              ))
            ) : (
              <div className="col-span-full py-12 text-center space-y-4 opacity-50">
                <Building2 size={48} className="mx-auto text-zinc-700" />
                <p className="text-sm font-bold uppercase tracking-widest text-zinc-500">No projects found</p>
              </div>
            )}
          </div>
        </GlassCard>
      </div>
    );
  }

  if (isLoading && !financials) {
    return (
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 animate-pulse p-2">
        <div className="space-y-8">
          <div className="h-64 bg-zinc-200/20 dark:bg-zinc-800/20 rounded-[2rem]" />
          <div className="h-96 bg-zinc-200/20 dark:bg-zinc-800/20 rounded-[2rem]" />
        </div>
        <div className="space-y-8">
          <div className="h-[500px] bg-zinc-200/20 dark:bg-zinc-800/20 rounded-[2rem]" />
          <div className="h-64 bg-zinc-200/20 dark:bg-zinc-800/20 rounded-[2rem]" />
        </div>
        <div className="space-y-8">
          <div className="h-[300px] bg-zinc-200/20 dark:bg-zinc-800/20 rounded-[2rem]" />
          <div className="h-[400px] bg-zinc-200/20 dark:bg-zinc-800/20 rounded-[2rem]" />
        </div>
      </div>
    );
  }

  const totalCommitted = financials?.reduce((sum, f) => sum + (normalizeFinancial(f.committed_value)), 0) ?? 0;
  const totalCertified = financials?.reduce((sum, f) => sum + (normalizeFinancial(f.certified_value)), 0) ?? 0;
  const totalRemaining = financials?.reduce((sum, f) => sum + (normalizeFinancial(f.balance_budget_remaining)), 0) ?? 0;

  // Additional metrics for dashboard
  const totalVendorPayable = vendorPayables?.reduce((s, v) => s + v.net_payable, 0) ?? 0;
  const overBudgetCategories = financials?.filter(f => f.over_commit_flag) ?? [];
  const pettyCash = cashSummary?.categories.find(c => c.category_name.toLowerCase().includes('petty'));
  const ovhCash = cashSummary?.categories.find(c =>
    c.category_name.toLowerCase().includes('ovh') || c.category_name.toLowerCase().includes('overhead')
  );
  const workOrders = woResponse?.items ?? [];
  const woOpen = workOrders.filter(w => ['Pending', 'Draft'].includes(w.status)).length;
  const woClosed = workOrders.filter(w => ['Closed', 'Completed'].includes(w.status)).length;

  return (
    <div className="space-y-8 pb-20">
      {/* Top Project Context Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white/5 border border-white/5 p-4 rounded-[2rem] backdrop-blur-md">
        <div className="flex items-center gap-4 pl-2">
          <div className="w-12 h-12 rounded-2xl bg-primary/10 flex items-center justify-center text-primary border border-primary/20">
            <FolderOpen size={24} />
          </div>
          <div>
            <h3 className="text-sm font-black text-primary uppercase tracking-widest leading-none mb-1">Active Context</h3>
            <p className="text-xl font-bold text-white tracking-tight">{activeProject.project_name}</p>
          </div>
        </div>
        <div className="flex items-center gap-3 pr-2">
          <div className="text-right hidden sm:block">
            <p className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest leading-none mb-1">Operational ID</p>
            <p className="text-xs font-mono text-zinc-400">{activeProject.project_code || 'N/A'}</p>
          </div>
          <button
            onClick={() => useProjectStore.getState().clearProject()}
            className="px-4 py-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl text-[10px] font-black uppercase tracking-widest text-white transition-all active:scale-95"
          >
            Switch Project
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Column 1: Overview & Vision */}
        <div className="space-y-6">
          <GlassCard className="border-primary/20">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center text-primary border border-primary/20">
                <LayoutGrid size={20} />
              </div>
              <h2 className="text-lg font-bold tracking-tight uppercase">Project Overview</h2>
            </div>

            <div className="space-y-6">
              <div>
                <p className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-1">Portfolio Value</p>
                <p className="text-3xl font-black">{formatCurrencySafe(totalBudget)}</p>
              </div>

              <div className="grid grid-cols-2 gap-4 pb-4 border-b border-muted">
                <div>
                  <p className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-0.5">Total Phases</p>
                  <p className="text-xl font-bold">{stats?.overview.total_phases ?? '-'}</p>
                </div>
                <div>
                  <p className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-0.5">Active Items</p>
                  <p className="text-xl font-bold text-primary">{stats?.overview.active_items ?? '-'}</p>
                </div>
              </div>

              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <AlertTriangle size={14} className="text-rose-500" />
                  <span className="text-[10px] font-bold text-rose-500 uppercase tracking-tight">Overdue Milestones</span>
                </div>
                <span className="text-sm font-black text-rose-500">{stats?.overview.overdue_milestones ?? 0}</span>
              </div>
            </div>
          </GlassCard>

          {activeProject && <AISummaryCard projectId={activeProject.project_id} />}

          <GlassCard className="group overflow-hidden p-0 h-[450px] border-none shadow-2xl">
            <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent z-10" />
            <div className="absolute top-4 left-4 z-20 flex items-center gap-2 bg-rose-600/90 text-white px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest animate-pulse">
              <span className="w-1.5 h-1.5 rounded-full bg-white" />
              LIVE SITE FEED
            </div>
            <img
              src="https://images.unsplash.com/photo-1541888946425-d81bb19480c5?auto=format&fit=crop&q=80&w=1000"
              alt="Site Feed"
              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700"
            />
            <div className="absolute bottom-4 left-4 right-4 z-20">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-xs font-bold text-white uppercase tracking-wider">Site Camera #04</h3>
                <Camera size={14} className="text-white/60" />
              </div>
              <div className="h-0.5 w-full bg-white/20 rounded-full mb-2">
                <div className="h-full bg-primary w-2/3 rounded-full" />
              </div>
              <div className="flex items-center justify-center gap-3 text-white/70">
                <Clock size={12} />
                <span className="text-[9px] font-mono">REC: 12:45:12</span>
              </div>
            </div>
          </GlassCard>
        </div>

        {/* Column 2: Operations & Tasks */}
        <div className="space-y-6">
          <GlassCard className="border-indigo-500/5 shadow-xl">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-indigo-500/5 flex items-center justify-center text-indigo-400 border border-indigo-500/10">
                  <Calendar size={16} />
                </div>
                <h2 className="text-xs font-bold tracking-tight uppercase">Construction Schedule</h2>
              </div>
              <TrendingUp size={16} className="text-emerald-500/80" />
            </div>

            <div className="h-[240px] w-full">
              <FinancialChart
                title=""
                data={chartData}
                dataKeys={[{ key: 'budget', color: '#775a19', label: 'Planned' }, { key: 'committed', color: '#505f7a', label: 'Actual' }]}
                height={240}
              />
            </div>
            <div className="mt-4 pt-4 border-t border-muted flex gap-8">
              <div>
                <p className="text-[9px] font-bold text-zinc-500 uppercase tracking-widest mb-0.5">S-Curve Variance</p>
                <div className="flex items-center gap-1.5">
                  {(stats?.schedule_status.variance ?? 0) >= 0 ? (
                    <TrendingUp size={12} className="text-emerald-500" />
                  ) : (
                    <TrendingDown size={12} className="text-rose-500" />
                  )}
                  <span className="text-xs font-black">{stats?.schedule_status.variance ?? 0}%</span>
                </div>
              </div>
              <div>
                <p className="text-[9px] font-bold text-zinc-500 uppercase tracking-widest mb-0.5">Critical Path</p>
                <span className={`text-xs font-black ${stats?.schedule_status.critical_path_status === 'DELAYED' ? 'text-rose-500' : 'text-emerald-500'}`}>
                  {stats?.schedule_status.critical_path_status ?? 'ON TRACK'}
                </span>
              </div>
            </div>
          </GlassCard>

          <GlassCard className="shadow-lg">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-orange-500/5 flex items-center justify-center text-orange-400 border border-orange-500/10">
                  <ListTodo size={16} />
                </div>
                <h2 className="text-xs font-bold tracking-tight uppercase">Task Manager</h2>
              </div>
              <span className="px-2 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 text-[8px] font-black uppercase text-zinc-500">{stats?.task_log.open_tasks ?? 0} Pending</span>
            </div>

            <div className="space-y-2">
              {(stats?.task_manager ?? []).map(task => (
                <div key={task.id} className="p-2.5 rounded-xl bg-muted/30 border border-white/40 dark:border-white/5 hover:border-primary/20 transition-all flex items-center justify-between group">
                  <div className="flex flex-col gap-0.5">
                    <span className="text-[9px] font-black text-zinc-400 tracking-tighter uppercase">{task.id}</span>
                    <span className="text-xs font-bold group-hover:text-primary transition-colors">{task.label}</span>
                  </div>
                  <span className={`text-[9px] font-bold uppercase tracking-tight ${task.color}`}>{task.priority}</span>
                </div>
              ))}
            </div>

            <button className="w-full mt-4 py-2 rounded-lg border border-muted text-[10px] font-bold uppercase tracking-widest hover:bg-muted/50 transition-all">
              View All Action Items
            </button>
          </GlassCard>
        </div>

        {/* Column 3: Logistics & Finance */}
        <div className="space-y-6">
          <GlassCard className="shadow-lg">
            <div className="flex items-center gap-3 mb-8">
              <div className="w-10 h-10 rounded-xl bg-emerald-500/5 flex items-center justify-center text-emerald-500 border border-emerald-500/10">
                <History size={20} />
              </div>
              <h2 className="text-sm font-bold tracking-tight uppercase">Project Wide Task Log</h2>
            </div>

            <div className="flex items-end gap-10 mb-6 pb-6 border-b border-muted">
              <div>
                <p className="text-4xl font-black leading-none tracking-tighter">{stats?.task_log.open_tasks ?? 0}</p>
                <p className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest mt-2">Open Tasks</p>
              </div>
              <div className="pb-1">
                <p className="text-2xl font-black text-zinc-400 tracking-tighter underline decoration-primary/20 decoration-2 underline-offset-4">{stats?.task_log.resolved_tasks ?? 0}</p>
                <p className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest mt-1">Resolved</p>
              </div>
            </div>

            <div className="space-y-4">
              <div className="flex items-center justify-between text-[10px] font-bold uppercase tracking-widest">
                <span className="text-zinc-500">Compliance Rate</span>
                <span className="text-emerald-500">{stats?.task_log.compliance_rate ?? 0}%</span>
              </div>
              <div className="h-2 w-full bg-muted/20 rounded-full overflow-hidden border border-muted/30">
                <div className="h-full bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.2)] transition-all duration-1000" style={{ width: `${stats?.task_log.compliance_rate ?? 0}%` }} />
              </div>
            </div>
          </GlassCard>

          <GlassCard className="border-indigo-500/5 shadow-xl">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-xl bg-indigo-500/5 flex items-center justify-center text-indigo-400 border border-indigo-500/10">
                <GanttChartSquare size={20} />
              </div>
              <h2 className="text-sm font-bold tracking-tight uppercase">Project Schedule & Gantt</h2>
            </div>

            <div className="space-y-6">
              {(financials ?? []).slice(0, 3).map(f => {
                const progress = f.original_budget >
                  0 ? Math.min(100, Math.round((normalizeFinancial(f.certified_value) / normalizeFinancial(f.original_budget)) * 100))
                  : 0;
                return (
                  <div key={f.category_id} className="space-y-2">
                    <div className="flex justify-between items-center text-[10px] font-bold uppercase tracking-wider">
                      <span className="text-zinc-500">{f.category_name || f.category_id.substring(0, 8)}</span>
                      <span className="text-primary">{progress}%</span>
                    </div>
                    <div className="h-2 w-full bg-muted/20 rounded-full overflow-hidden border border-muted/30">
                      <div
                        className="h-full bg-primary transition-all duration-500"
                        style={{ width: `${Math.max(1, progress)}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </GlassCard>

          <GlassCard className="border-primary/5 shadow-xl">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-xl bg-primary/5 flex items-center justify-center text-primary border border-primary/10">
                <BarChart4 size={20} />
              </div>
              <h2 className="text-sm font-bold tracking-tight uppercase">Project Budget & Utilization</h2>
            </div>

            <div className="space-y-6">
              {(financials ?? []).sort((a, b) => (normalizeFinancial(b.original_budget) - normalizeFinancial(a.original_budget))).slice(0, 3).map(f => {
                const actual = normalizeFinancial(f.committed_value);
                const budget = normalizeFinancial(f.original_budget);
                const spentPercent = f.original_budget > 0
                  ? Math.round((normalizeFinancial(f.committed_value) / normalizeFinancial(f.original_budget)) * 100)
                  : 0;
                return (
                  <div key={f.category_id} className="space-y-2">
                    <div className="flex justify-between items-center text-[10px] font-bold uppercase tracking-wider">
                      <span className="text-zinc-500">{f.category_name || f.category_id}</span>
                      <span className="text-zinc-400 italic">{spentPercent}% Spent</span>
                    </div>
                    <div className="h-2 w-full bg-muted/20 rounded-full overflow-hidden border border-muted/30 flex">
                      <div className="h-full bg-primary" style={{ width: `${spentPercent}%` }} />
                      <div className="h-full bg-muted/40" style={{ width: `${100 - spentPercent}%` }} />
                    </div>
                  </div>
                );
              })}
            </div>
          </GlassCard>
        </div>
      </div>
    </div>
  );
}
