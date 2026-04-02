"use client";
import React from "react";
import useSWR from "swr";
import {
  AlertTriangle,
  LayoutGrid,
  ChevronRight,
  Building2,
  Search,
  Calendar,
  ListTodo,
  History as HistoryIcon,
  GanttChartSquare,
  BarChart4,
  FolderOpen,
  ArrowRight,
  TrendingUp,
} from "lucide-react";
import Link from "next/link";
import { fetcher, schedulerApi } from "@/lib/api";
import { Info, ChevronUp, ChevronDown } from "lucide-react";
import { Project, DerivedFinancialState } from "@/types/api";
import NextImage from "next/image";
import { useProjectStore } from "@/store/projectStore";
import { useScheduleStore } from "@/store/useScheduleStore";
import { AISummaryCard } from "@/components/dashboard/AISummaryCard";
import KPICards from "@/components/dashboard/KPICards";
import ProjectMiniGantt from "@/components/dashboard/ProjectMiniGantt";
import SCurveChart from "@/components/scheduler/SCurveChart";

import { formatCurrencySafe, normalizeFinancial } from "@/lib/formatters";
import { GlassCard } from "@/components/ui/GlassCard";
import { normalizeTaskOrder, parseTaskDate } from "@/components/scheduler/scheduler-utils";
import { addDays, startOfDay, isBefore } from "date-fns";

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
  const [projectSearch, setProjectSearch] = React.useState("");
  const loadSchedule = useScheduleStore((state) => state.loadSchedule);
  const taskMap = useScheduleStore((state) => state.taskMap);
  const taskOrder = useScheduleStore((state) => state.taskOrder);

  const tasks = React.useMemo(() => normalizeTaskOrder(taskMap, taskOrder), [taskMap, taskOrder]);

  const { data: projects, isLoading: projectsLoading } = useSWR<Project[]>(
    "/api/v1/projects/",
    fetcher
  );

  // Hydrate schedule store for widgets if project is active
  React.useEffect(() => {
    if (activeProject?.project_id) {
      schedulerApi.load(activeProject.project_id).then(loadSchedule);
    }
  }, [activeProject?.project_id, loadSchedule]);

  const filteredProjects = React.useMemo(() => {
    if (!projects) return [];
    const q = projectSearch.toLowerCase();
    return projects.filter(
      (p) =>
        p.project_name.toLowerCase().includes(q) ||
        (p.project_code || "").toLowerCase().includes(q)
    );
  }, [projectSearch, projects]);

  const { data: financials, isLoading } = useSWR<DerivedFinancialState[]>(
    activeProject
      ? `/api/v1/projects/${activeProject.project_id}/financials`
      : null,
    fetcher,
  );

  const { data: stats } = useSWR<DashboardStats>(
    activeProject ? `/api/v1/projects/${activeProject.project_id}/dashboard-stats` : null,
    fetcher
  );

  const urgentTasks = React.useMemo(() => {
    const today = startOfDay(new Date());
    const threeDaysLater = addDays(today, 3);

    return tasks.filter(t => {
      const finish = parseTaskDate(t.scheduled_finish);
      if (!finish) return false;

      // Include if:
      // 1. Not completed AND (Overdue OR Finishing soon)
      const isComplete = Number(t.percent_complete ?? 0) >= 100;
      if (isComplete) return false; // Usually don't show completed in "Urgent"

      return isBefore(finish, threeDaysLater);
    }).sort((a, b) => {
      const da = parseTaskDate(a.scheduled_finish)?.getTime() || 0;
      const db = parseTaskDate(b.scheduled_finish)?.getTime() || 0;
      return da - db;
    }).slice(0, 5);
  }, [tasks]);

  const totalBudget = React.useMemo(() => {
    if (stats?.overview.master_budget) return stats.overview.master_budget;
    if (activeProject?.master_original_budget) return activeProject.master_original_budget;
    return (financials ?? []).reduce((sum, f) => sum + normalizeFinancial(f.original_budget), 0);
  }, [financials, activeProject, stats]);

  // --- REARRANGE DRIVEN LAYOUT ---
  const DEFAULT_LAYOUT = ['timeline', 'tasks', 'analytics', 'log', 'scheduler', 'budget'];
  const [layout, setLayout] = React.useState<string[]>(DEFAULT_LAYOUT);

  React.useEffect(() => {
    const saved = localStorage.getItem(`dashboard_layout_${activeProject?.project_id}`);
    if (saved) setLayout(JSON.parse(saved));
  }, [activeProject?.project_id]);

  const moveWidget = (id: string, dir: 'up' | 'down') => {
    const idx = layout.indexOf(id);
    if (idx === -1) return;
    const newIdx = dir === 'up' ? idx - 1 : idx + 1;
    if (newIdx < 0 || newIdx >= layout.length) return;

    const newLayout = [...layout];
    [newLayout[idx], newLayout[newIdx]] = [newLayout[newIdx], newLayout[idx]];
    setLayout(newLayout);
    localStorage.setItem(`dashboard_layout_${activeProject?.project_id}`, JSON.stringify(newLayout));
  };

  const widgets: Record<string, React.ReactNode> = {
    timeline: (
      <GlassCard key="timeline" className="border-indigo-500/5 shadow-xl !p-0 overflow-hidden col-span-1 md:col-span-2 h-[600px]">
        <div className="p-8 h-full flex flex-col">
          <div className="flex items-center justify-between mb-6 shrink-0">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-indigo-500/5 flex items-center justify-center text-indigo-400 border border-indigo-500/10">
                <Calendar size={16} />
              </div>
              <div>
                <h2 className="text-xs font-bold tracking-tight uppercase flex items-center gap-1.5 text-slate-900 dark:text-white">
                  Project Schedule & Gantt
                  <Info size={10} className="text-zinc-500" />
                </h2>
                <p className="text-[8px] text-zinc-500 dark:text-zinc-400 uppercase tracking-widest mt-0.5">Execution Horizon</p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="flex bg-white/5 rounded-lg p-0.5 border border-white/5">
                <button onClick={() => moveWidget('timeline', 'up')} className="p-1 hover:text-primary transition-colors"><ChevronUp size={12} /></button>
                <button onClick={() => moveWidget('timeline', 'down')} className="p-1 hover:text-primary transition-colors"><ChevronDown size={12} /></button>
              </div>
              <Link
                href="/admin/scheduler?tab=gantt"
                className="flex items-center gap-1.5 text-[10px] font-black uppercase tracking-widest text-primary hover:text-primary/80 transition-colors"
              >
                Full Planner <ArrowRight size={12} />
              </Link>
            </div>
          </div>

          <div className="flex-1 min-h-0 border border-white/5 rounded-2xl overflow-hidden">
            <ProjectMiniGantt tasks={tasks} />
          </div>
        </div>
      </GlassCard>
    ),
    tasks: (
      <GlassCard key="tasks" className="shadow-lg">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-orange-500/5 flex items-center justify-center text-orange-400 border border-orange-500/10">
              <ListTodo size={16} />
            </div>
            <div>
              <h2 className="text-xs font-bold tracking-tight uppercase text-slate-900 dark:text-white">Task Manager</h2>
              <p className="text-[8px] text-zinc-500 dark:text-zinc-400 uppercase tracking-widest mt-0.5">Urgent Tactical Actions</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex bg-white/5 rounded-lg p-0.5 border border-white/5">
              <button onClick={() => moveWidget('tasks', 'up')} className="p-1 hover:text-primary transition-colors"><ChevronUp size={12} /></button>
              <button onClick={() => moveWidget('tasks', 'down')} className="p-1 hover:text-primary transition-colors"><ChevronDown size={12} /></button>
            </div>
            <span className="px-2 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 text-[8px] font-black uppercase text-zinc-500">
              {tasks.filter(t => (t.percent_complete ?? 0) < 100).length} Pending
            </span>
          </div>
        </div>

        <div className="space-y-2">
          {urgentTasks.length > 0 ? urgentTasks.map(task => (
            <div key={task.task_id} className="p-2.5 rounded-xl bg-muted/30 border border-white/40 dark:border-white/5 hover:border-primary/20 transition-all flex items-center justify-between group">
              <div className="flex flex-col gap-0.5 min-w-0">
                <span className="text-[9px] font-black text-zinc-400 tracking-tighter uppercase">{task.wbs_code || String(task.task_id).substring(0, 4)}</span>
                <span className="text-xs font-bold group-hover:text-primary transition-colors truncate">{task.task_name}</span>
              </div>
              <div className="text-right shrink-0 ml-4">
                <span className={`text-[9px] font-bold uppercase tracking-tight ${isBefore(parseTaskDate(task.scheduled_finish) || new Date(), startOfDay(new Date())) ? 'text-rose-500' : 'text-amber-500'
                  }`}>
                  {isBefore(parseTaskDate(task.scheduled_finish) || new Date(), startOfDay(new Date())) ? 'OVERDUE' : 'URGENT'}
                </span>
                <p className="text-[8px] text-zinc-500 mt-0.5">{task.scheduled_finish}</p>
              </div>
            </div>
          )) : (
            <div className="py-8 text-center text-zinc-600 text-xs font-medium italic">No immediate tactical actions required.</div>
          )}
        </div>

        <Link href="/admin/scheduler?tab=kanban" className="block w-full mt-4 py-2 rounded-lg border border-slate-200 dark:border-white/10 text-slate-900 dark:text-white text-center text-[10px] font-bold uppercase tracking-widest hover:bg-slate-100 dark:hover:bg-white/5 transition-all">
          View All Action Items
        </Link>
      </GlassCard>
    ),
    analytics: (
      <GlassCard key="analytics" className="shadow-lg flex flex-col h-[500px]">
        <div className="flex items-center justify-between mb-6 shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-sky-500/5 flex items-center justify-center text-sky-400 border border-sky-500/10">
              <TrendingUp size={16} />
            </div>
            <div>
              <h2 className="text-xs font-bold tracking-tight uppercase text-slate-900 dark:text-white">Execution Analytics</h2>
              <p className="text-[8px] text-zinc-500 dark:text-zinc-400 uppercase tracking-widest mt-0.5">S-Curve Variance</p>
            </div>
          </div>
          <div className="flex bg-white/5 rounded-lg p-0.5 border border-white/5">
            <button onClick={() => moveWidget('analytics', 'up')} className="p-1 hover:text-primary transition-colors"><ChevronUp size={12} /></button>
            <button onClick={() => moveWidget('analytics', 'down')} className="p-1 hover:text-primary transition-colors"><ChevronDown size={12} /></button>
          </div>
        </div>
        <div className="flex-1 min-h-0">
          <SCurveChart />
        </div>
        <Link href="/admin/scheduler?tab=analytics" className="block w-full mt-4 py-2 rounded-lg border border-slate-200 dark:border-white/10 text-slate-900 dark:text-white text-center text-[10px] font-bold uppercase tracking-widest hover:bg-slate-100 dark:hover:bg-white/5 transition-all">
          View Full Analysis
        </Link>
      </GlassCard>
    ),
    log: (
      <GlassCard key="log" className="shadow-lg">
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-500/5 flex items-center justify-center text-emerald-500 border border-emerald-500/10">
              <HistoryIcon size={20} />
            </div>
            <div>
              <h2 className="text-sm font-bold tracking-tight uppercase flex items-center gap-1.5 text-slate-900 dark:text-white">
                Task Analytics
                <Info size={10} className="text-zinc-500" />
              </h2>
              <p className="text-[8px] text-zinc-500 dark:text-zinc-400 uppercase tracking-widest mt-0.5">Project Wide Log</p>
            </div>
          </div>
          <div className="flex bg-white/5 rounded-lg p-0.5 border border-white/5">
            <button onClick={() => moveWidget('log', 'up')} className="p-1 hover:text-primary transition-colors"><ChevronUp size={12} /></button>
            <button onClick={() => moveWidget('log', 'down')} className="p-1 hover:text-primary transition-colors"><ChevronDown size={12} /></button>
          </div>
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
        <Link href="/admin/scheduler?tab=analytics" className="block w-full mt-6 py-2 rounded-lg border border-slate-200 dark:border-white/10 text-slate-900 dark:text-white text-center text-[10px] font-bold uppercase tracking-widest hover:bg-slate-100 dark:hover:bg-white/5 transition-all">
          Operational Intelligence Registry
        </Link>
      </GlassCard>
    ),
    scheduler: (
      <GlassCard key="scheduler" className="border-indigo-500/5 shadow-xl flex flex-col h-[500px]">
        <div className="flex items-center justify-between mb-6 shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-500/5 flex items-center justify-center text-indigo-400 border border-indigo-500/10">
              <GanttChartSquare size={20} />
            </div>
            <div>
              <h2 className="text-sm font-bold tracking-tight uppercase flex items-center gap-1.5 text-slate-900 dark:text-white">
                Production Progress
                <Info size={10} className="text-zinc-500" />
              </h2>
              <p className="text-[8px] text-zinc-500 dark:text-zinc-400 uppercase tracking-widest mt-0.5">Task Status Matrix</p>
            </div>
          </div>
          <div className="flex bg-white/5 rounded-lg p-0.5 border border-white/5">
            <button onClick={() => moveWidget('scheduler', 'up')} className="p-1 hover:text-primary transition-colors"><ChevronUp size={12} /></button>
            <button onClick={() => moveWidget('scheduler', 'down')} className="p-1 hover:text-primary transition-colors"><ChevronDown size={12} /></button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto space-y-6 pr-2 custom-scrollbar">
          {tasks.filter(t => t.percent_complete !== undefined).map((task, idx) => {
            const progress = Number(task.percent_complete ?? 0);
            return (
              <div key={task.task_id || `task-${idx}`} className="space-y-2">
                <div className="flex justify-between items-center text-[10px] font-bold uppercase tracking-wider">
                  <div className="flex flex-col min-w-0">
                    <span className="text-zinc-500 truncate pr-2">
                      {task.task_name}
                    </span>
                    <span className="text-[10px] text-zinc-600 font-mono">
                      {task.wbs_code || '---'}
                    </span>
                  </div>
                  <span className="text-primary shrink-0">{progress}%</span>
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
          {tasks.length === 0 && (
            <p className="text-center text-xs text-zinc-600 italic py-4">No tasks found in planner.</p>
          )}
        </div>
        <Link href="/admin/scheduler?tab=grid" className="block w-full mt-4 py-2 shrink-0 rounded-lg border border-muted text-center text-[10px] font-bold uppercase tracking-widest hover:bg-muted/50 transition-all">
          More Details
        </Link>
      </GlassCard>
    ),
    budget: (
      <GlassCard key="budget" className="border-primary/5 shadow-xl flex flex-col h-[500px]">
        <div className="flex items-center justify-between mb-6 shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-primary/5 flex items-center justify-center text-primary border border-primary/10">
              <BarChart4 size={20} />
            </div>
            <div>
              <h2 className="text-sm font-bold tracking-tight uppercase flex items-center gap-1.5 text-slate-900 dark:text-white">
                Budget Utilization
                <Info size={10} className="text-zinc-500" />
              </h2>
              <p className="text-[8px] text-zinc-500 dark:text-zinc-400 uppercase tracking-widest mt-0.5">Financial Absorption</p>
            </div>
          </div>
          <div className="flex bg-white/5 rounded-lg p-0.5 border border-white/5">
            <button onClick={() => moveWidget('budget', 'up')} className="p-1 hover:text-primary transition-colors"><ChevronUp size={12} /></button>
            <button onClick={() => moveWidget('budget', 'down')} className="p-1 hover:text-primary transition-colors"><ChevronDown size={12} /></button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto space-y-6 pr-2 custom-scrollbar">
          {(financials ?? []).sort((a, b) => (normalizeFinancial(b.original_budget) - normalizeFinancial(a.original_budget))).map((f, idx) => {
            const progress = f.original_budget > 0
              ? Math.min(100, Math.round((normalizeFinancial(f.certified_value) / normalizeFinancial(f.original_budget)) * 100))
              : 0;
            return (
              <div key={f.category_id || `util-${idx}`} className="space-y-2">
                <div className="flex justify-between items-center text-[10px] font-bold uppercase tracking-wider">
                  <span className="text-zinc-500 truncate max-w-[200px]">{f.category_name || f.category_id}</span>
                  <span className="text-primary shrink-0">{progress}% Progress</span>
                </div>
                <div className="h-2 w-full bg-muted/20 rounded-full overflow-hidden border border-muted/30">
                  <div className="h-full bg-primary transition-all duration-700" style={{ width: `${progress}%` }} />
                </div>
              </div>
            );
          })}
        </div>
        <Link href={`/admin/projects/${activeProject?.project_id}`} className="block w-full mt-4 py-2 shrink-0 rounded-lg border border-slate-200 dark:border-white/10 text-slate-900 dark:text-white text-center text-[10px] font-bold uppercase tracking-widest hover:bg-slate-100 dark:hover:bg-white/5 transition-all">
          Full Financials
        </Link>
      </GlassCard>
    )
  };

  if (!activeProject) {
    return (
      <div className="space-y-8 animate-in fade-in duration-700">
        <div className="max-w-4xl mx-auto text-center space-y-4">
          <h1 className="text-4xl font-black tracking-tight text-slate-900 dark:text-white uppercase transition-colors">
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

  return (
    <div className="space-y-8 pb-20">
      {/* Top Project Context Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-slate-100 dark:bg-white/5 border border-slate-200 dark:border-white/5 p-4 rounded-[2rem] backdrop-blur-md transition-colors">
        <div className="flex items-center gap-4 pl-2">
          <div className="w-12 h-12 rounded-2xl bg-primary/10 flex items-center justify-center text-primary border border-primary/20">
            <FolderOpen size={24} />
          </div>
          <div>
            <h3 className="text-sm font-black text-primary uppercase tracking-widest leading-none mb-1">Active Context</h3>
            <p className="text-xl font-bold text-slate-900 dark:text-white tracking-tight">{activeProject.project_name}</p>
          </div>
        </div>
        <div className="flex items-center gap-3 pr-2">
          <div className="text-right hidden sm:block">
            <p className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest leading-none mb-1">Operational ID</p>
            <p className="text-xs font-mono text-zinc-400">{activeProject.project_code || 'N/A'}</p>
          </div>
          <button
            onClick={() => useProjectStore.getState().clearProject()}
            className="px-4 py-2 bg-slate-200 hover:bg-slate-300 dark:bg-white/5 dark:hover:bg-white/10 border border-slate-300 dark:border-white/10 rounded-xl text-[10px] font-black uppercase tracking-widest text-slate-900 dark:text-white transition-all active:scale-95"
          >
            Switch Project
          </button>
        </div>
      </div>

      {activeProject && (
        <div className="animate-in fade-in slide-in-from-top-4 duration-1000">
          <KPICards />
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Column 1: Static / Always First (Overview & Feed) */}
        <div className="space-y-6">
          <GlassCard className="border-primary/20">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center text-primary border border-primary/20">
                <LayoutGrid size={20} />
              </div>
              <h2 className="text-lg font-bold tracking-tight uppercase">Project Overview</h2>
            </div>
            {/* Same Overview Content */}
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
              LIVE SITE FEED
            </div>
            <NextImage
              src="https://images.unsplash.com/photo-1541888946425-d81bb19480c5?auto=format&fit=crop&q=80&w=1000"
              alt="Site Feed"
              fill
              className="object-cover group-hover:scale-105 transition-transform duration-700"
              unoptimized
            />
          </GlassCard>
        </div>

        {/* Column 2 & 3: Dynamic Rearrangeable Grid */}
        <div className="lg:col-span-2 grid grid-cols-1 md:grid-cols-2 gap-6 items-start content-start">
          {layout.map(widgetId => widgets[widgetId])}
        </div>
      </div>
    </div>
  );
}
