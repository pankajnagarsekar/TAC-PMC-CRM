"use client";
import React from "react";
import useSWR, { mutate } from "swr";
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
  Camera,
  Brain,
  BarChart3,
} from "lucide-react";
import Link from "next/link";
import { format } from "date-fns";
import { toast } from "sonner";
import { fetcher, schedulerApi } from "@/lib/api";
import { Project, DerivedFinancialState } from "@/types/api";
import { useProjectStore } from "@/store/projectStore";
import { useScheduleStore } from "@/store/useScheduleStore";
import { AISummaryCard } from "@/components/dashboard/AISummaryCard";
import KPICards from "@/components/dashboard/KPICards";
import EVMBaselineModal from "@/components/dashboard/EVMBaselineModal";
import ProjectMiniGantt from "@/components/dashboard/ProjectMiniGantt";
import SCurveChart from "@/components/scheduler/SCurveChart";
import TaskAISummary from "@/components/tasks/TaskAISummary";
import SchedulerCalendarView from "@/components/scheduler/SchedulerCalendarView";
import PettyCashAlertBanner from "@/components/petty-cash/PettyCashAlertBanner";

import { formatCurrencySafe, normalizeFinancial } from "@/lib/formatters";
import { GlassCard } from "@/components/ui/GlassCard";
import { normalizeTaskOrder, parseTaskDate } from "@/components/scheduler/scheduler-utils";
import { addDays, startOfDay, isBefore } from "date-fns";

import { DashboardDndGrid, WidgetDef } from "@/components/dashboard/DashboardDndGrid";
import { useDashboardLayoutStore } from "@/store/useDashboardLayoutStore";

interface DashboardStats {
  project_id: string;
  operational_id?: string;
  overview: {
    total_phases: number;
    active_items: number;
    overdue_milestones: number;
    master_budget: number;
    total_budget: number;
    total_committed: number;
    // EVA Metrics (Constitution §9)
    planned_value?: number;
    earned_value?: number;
    actual_cost?: number;
    cpi?: number;
    spi?: number;
    cost_variance?: number;
    schedule_variance?: number;
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
  const { activeProject, setActiveProject, clearProject } = useProjectStore();
  const [projectSearch, setProjectSearch] = React.useState("");
  const [isEVMModalOpen, setIsEVMModalOpen] = React.useState(false);
  const previousProjectRef = React.useRef<Project | null>(null);
  const loadSchedule = useScheduleStore((state) => state.loadSchedule);
  const clearSchedule = useScheduleStore((state) => state.clear);
  const taskMap = useScheduleStore((state) => state.taskMap);
  const taskOrder = useScheduleStore((state) => state.taskOrder);

  const tasks = React.useMemo(() => normalizeTaskOrder(taskMap, taskOrder), [taskMap, taskOrder]);

  const { data: projects, isLoading: projectsLoading, error: projectsError } = useSWR<Project[]>(
    "/api/v1/projects/",
    fetcher
  );

  // Validate stored project against available projects — clears stale DB references
  React.useEffect(() => {
    if (!projects || projects.length === 0 || !activeProject) return;
    const storedId = activeProject.project_id || activeProject._id;
    const exists = projects.some(
      (p: Project) => p.project_id === storedId || p._id === storedId
    );
    if (!exists) {
      clearProject();
    }
  }, [projects, activeProject, clearProject]);

  // Hydrate schedule store for widgets if project is active
  React.useEffect(() => {
    if (activeProject?.project_id) {
      clearSchedule();
      schedulerApi.load(activeProject.project_id)
        .then((response) => {
          console.log("[Dashboard] Schedule loaded — tasks:", response?.tasks?.length ?? 0, "project_id:", response?.project_id);
          loadSchedule(response);
        })
        .catch((err) => {
          console.error("[Dashboard] Failed to load schedule:", err?.response?.status, err?.message);
        });
    } else {
      clearSchedule();
    }
  }, [activeProject?.project_id, loadSchedule, clearSchedule]);

  // Browser tab title
  React.useEffect(() => {
    document.title = activeProject
      ? `${activeProject.project_name} | Dashboard | TAC-PMC CRM`
      : 'Dashboard | TAC-PMC CRM';
  }, [activeProject]);

  // Handle ESC for project selector cancellation
  React.useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !activeProject && previousProjectRef.current) {
        setActiveProject(previousProjectRef.current);
        previousProjectRef.current = null;
      }
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [activeProject, setActiveProject]);

  const filteredProjects = React.useMemo(() => {
    if (!projects) return [];
    const q = projectSearch.toLowerCase();
    return projects.filter(
      (p) =>
        (!p.project_name.startsWith("E2E") &&
          !p.project_name.toLowerCase().includes("debug project")) &&
        (p.project_name.toLowerCase().includes(q) ||
          (p.project_code || "").toLowerCase().includes(q))
    );
  }, [projectSearch, projects]);

  const { data: financials, isLoading, error: financialError } = useSWR<DerivedFinancialState[]>(
    activeProject
      ? `/api/v1/projects/${activeProject.project_id}/financials`
      : null,
    fetcher,
  );

  const { data: stats, mutate: mutateStats } = useSWR<DashboardStats>(
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
      if (isComplete) return false;

      return isBefore(finish, threeDaysLater);
    }).sort((a, b) => {
      const da = parseTaskDate(a.scheduled_finish)?.getTime() || 0;
      const db = parseTaskDate(b.scheduled_finish)?.getTime() || 0;
      return da - db;
    }).slice(0, 5);
  }, [tasks]);

  const totalBudget = React.useMemo(() => {
    if (stats?.overview?.master_budget) return stats.overview.master_budget;
    if (activeProject?.master_original_budget) return activeProject.master_original_budget;
    return (financials ?? []).reduce((sum, f) => sum + normalizeFinancial(f.original_budget), 0);
  }, [financials, activeProject, stats]);

  // Define widgets record to supply to the DnD Grid wrapper
  const dynamicWidgets = React.useMemo<Record<string, WidgetDef>>(() => {
    if (!activeProject) return {} as Record<string, WidgetDef>;

    const now = new Date();
    const today = startOfDay(now);

    return {
      ai_brief: {
        title: "AI Project Brief",
        subtitle: "Financial & Project Health",
        icon: <Brain size={16} />,
        content: <AISummaryCard projectId={activeProject.project_id} embedded />
      },
      task_ai: {
        title: "AI Progress Insights",
        subtitle: "Task Execution & Assignee Analytics",
        icon: <BarChart3 size={16} />,
        content: <TaskAISummary projectId={activeProject.project_id} embedded />
      },
      timeline: {
        title: "Project Schedule & Gantt",
        subtitle: "Execution Horizon",
        icon: <Calendar size={16} />,
        minHeight: "600px",
        maxHeight: "600px",
        headerAction: (
          <Link
            href="/admin/scheduler?tab=gantt"
            className="flex items-center gap-1.5 text-[10px] font-black uppercase tracking-widest text-primary hover:text-primary/80 transition-colors"
          >
            Full Planner <ArrowRight size={12} />
          </Link>
        ),
        content: (
          <div className="h-full border border-white/5 rounded-2xl overflow-hidden min-h-[460px]">
            <ProjectMiniGantt tasks={tasks} />
          </div>
        )
      },
      tasks: {
        title: "Task Manager",
        subtitle: "Urgent Tactical Actions",
        icon: <ListTodo size={16} />,
        headerAction: (
          <span className="px-2 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 text-[8px] font-black uppercase text-zinc-500">
            {tasks.filter(t => (t.percent_complete ?? 0) < 100).length} Pending
          </span>
        ),
        content: (
          <div className="flex flex-col h-full justify-between">
            <div className="space-y-2">
              {urgentTasks.length > 0 ? urgentTasks.map(task => (
                <div key={task.task_id} className="p-2.5 rounded-xl bg-muted/30 border border-white/40 dark:border-white/5 hover:border-primary/20 transition-all flex items-center justify-between group">
                  <div className="flex flex-col gap-0.5 min-w-0">
                    <span className="text-[9px] font-black text-zinc-400 tracking-tighter uppercase">{task.wbs_code || String(task.task_id).substring(0, 4)}</span>
                    <span className="text-xs font-bold group-hover:text-primary transition-colors truncate">{task.task_name}</span>
                  </div>
                  <div className="text-right shrink-0 ml-4">
                    <span
                      suppressHydrationWarning
                      className={`text-[9px] font-bold uppercase tracking-tight ${isBefore(parseTaskDate(task.scheduled_finish) || now, today) ? 'text-rose-500' : 'text-amber-500'
                      }`}
                    >
                      {isBefore(parseTaskDate(task.scheduled_finish) || now, today) ? 'OVERDUE' : 'URGENT'}
                    </span>
                    <p className="text-[8px] text-zinc-500 mt-0.5">{task.scheduled_finish}</p>
                  </div>
                </div>
              )) : (
                <div className="py-8 text-center text-zinc-600 text-xs font-medium italic">No immediate tactical actions required.</div>
              )}
            </div>
            <Link href="/admin/scheduler?tab=kanban" className="block w-full mt-4 py-2 rounded-lg border border-slate-200 dark:border-white/10 text-slate-900 dark:text-white text-center text-[10px] font-bold uppercase tracking-widest hover:bg-slate-100 dark:hover:bg-white/5 transition-all shrink-0">
              View All Action Items
            </Link>
          </div>
        )
      },
      budget: {
        title: "Budget Utilization",
        subtitle: "Financial Absorption",
        icon: <BarChart4 size={16} />,
        content: (
          <div className="flex flex-col h-full justify-between">
            <div className="space-y-6 pr-2 max-h-[420px] overflow-y-auto custom-scrollbar">
              {(financials ?? []).sort((a, b) => (normalizeFinancial(b.original_budget) - normalizeFinancial(a.original_budget))).map((f, idx) => {
                const progress = f.original_budget > 0
                  ? Math.min(100, Math.round((normalizeFinancial(f.certified_value) / normalizeFinancial(f.original_budget)) * 100))
                  : 0;
                return (
                  <div key={f.category_id || `util-${idx}`} className="space-y-2">
                    <div className="flex justify-between items-center text-[10px] font-bold uppercase tracking-wider">
                      <span className="text-zinc-500 truncate max-w-[200px]">
                        {f.category_name || f.category_id}
                        {f.category_code && ` (${f.category_code})`}
                      </span>
                      <span className="text-primary shrink-0">{progress}% Progress</span>
                    </div>
                    <div className="h-2 w-full bg-muted/20 rounded-full overflow-hidden border border-muted/30">
                      <div className="h-full bg-primary transition-all duration-700" style={{ width: `${Math.max(progress, 2)}%` }} />
                    </div>
                  </div>
                );
              })}
            </div>
            <Link href={`/admin/projects/${activeProject?.project_id}`} className="block w-full mt-4 py-2 shrink-0 rounded-lg border border-slate-200 dark:border-white/10 text-slate-900 dark:text-white text-center text-[10px] font-bold uppercase tracking-widest hover:bg-slate-100 dark:hover:bg-white/5 transition-all">
              Full Financials
            </Link>
          </div>
        )
      },
      calendar: {
        title: "Project Calendar",
        subtitle: "Tactical Schedule",
        icon: <Calendar size={16} />,
        minHeight: "600px",
        maxHeight: "600px",
        headerAction: (
          <Link
            href="/admin/scheduler?tab=calendar"
            className="flex items-center gap-1.5 text-[10px] font-black uppercase tracking-widest text-primary hover:text-primary/80 transition-colors"
          >
            Full Planner <ArrowRight size={12} />
          </Link>
        ),
        content: (
          <div className="h-full border border-white/5 rounded-2xl overflow-hidden bg-slate-950/20 p-4 min-h-[460px]">
            <SchedulerCalendarView
              compact
              hideSettings
              onDateClick={(date) => {
                if (!activeProject) return;
                const dateStr = format(date, 'yyyy-MM-dd');
                const newTask = useScheduleStore.getState().createDraftTask(activeProject.project_id, {
                  scheduled_start: dateStr,
                  task_mode: 'Manual'
                });
                useScheduleStore.getState().openTaskModal(newTask.task_id);
                toast.success(`Task initialized for ${format(date, 'MMM dd')}`);
              }}
            />
          </div>
        )
      },
      log: {
        title: "Task Analytics",
        subtitle: "Project Wide Log",
        icon: <HistoryIcon size={16} />,
        content: (
          <div className="flex flex-col h-full justify-between">
            <div>
              <div className="flex items-end gap-10 mb-6 pb-6 border-b border-border/40">
                <div>
                  <p className="text-4xl font-black leading-none tracking-tighter">{tasks.filter(t => (t.percent_complete ?? 0) < 100).length}</p>
                  <p className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest mt-2">Open Tasks</p>
                </div>
                <div className="pb-1">
                  <p className="text-2xl font-black text-zinc-400 tracking-tighter underline decoration-primary/20 decoration-2 underline-offset-4">{tasks.filter(t => (t.percent_complete ?? 0) >= 100).length}</p>
                  <p className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest mt-1">Resolved</p>
                </div>
              </div>

              <div className="space-y-4">
                <div className="flex items-center justify-between text-[10px] font-bold uppercase tracking-widest">
                  <span className="text-zinc-500">Compliance Rate</span>
                  <span className="text-emerald-500">{tasks.length > 0 ? Math.round(tasks.filter(t => (t.percent_complete ?? 0) >= 100).length / tasks.length * 100) : 0}%</span>
                </div>
                <div className="h-2 w-full bg-muted/20 rounded-full overflow-hidden border border-muted/30">
                  <div
                    className="h-full bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.2)] transition-all duration-1000"
                    style={{ width: `${tasks.length > 0 ? (tasks.filter(t => (t.percent_complete ?? 0) >= 100).length / tasks.length * 100) : 0}%` }}
                  />
                </div>
              </div>
            </div>

            <Link href="/admin/scheduler?tab=analytics" className="block w-full mt-6 py-2 rounded-lg border border-slate-200 dark:border-white/10 text-slate-900 dark:text-white text-center text-[10px] font-bold uppercase tracking-widest hover:bg-slate-100 dark:hover:bg-white/5 transition-all shrink-0">
              Operational Intelligence Registry
            </Link>
          </div>
        )
      },
      scheduler: {
        title: "Production Progress",
        subtitle: "Task Status Matrix",
        icon: <GanttChartSquare size={16} />,
        content: (
          <div className="flex flex-col h-full justify-between">
            <div className="space-y-6 pr-2 max-h-[420px] overflow-y-auto custom-scrollbar">
              {tasks.filter(t => t.percent_complete !== undefined).map((task, idx) => {
                const progress = Number(task.percent_complete ?? 0);
                return (
                  <div key={task.task_id || `task-${idx}`} className="space-y-2">
                    <div className="flex justify-between items-center text-[10px] font-bold uppercase tracking-wider">
                      <div className="flex flex-col min-w-0">
                        <span className="text-zinc-500 truncate pr-2">
                          {task.task_name || (task as Record<string, unknown>).task_description as string || 'Unnamed Task'}
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
          </div>
        )
      },
      site_feed: {
        title: "Live Site Feed",
        subtitle: "Live Site Feed",
        icon: <Camera size={16} />,
        content: (
          <div className="flex flex-col items-center justify-center py-12 text-center gap-y-3 h-full">
            <div className="size-14 rounded-2xl bg-rose-500/10 flex items-center justify-center text-rose-400 border border-rose-500/20">
              <Camera size={24} />
            </div>
            <div>
              <h3 className="text-xs font-bold uppercase tracking-widest text-slate-900 dark:text-white mb-1">
                Live Site Feed
              </h3>
              <p className="text-[10px] text-zinc-500 max-w-[200px] mx-auto">
                Site photos and DPR entries will appear here when submitted via the mobile app.
              </p>
            </div>
            <Link
              href="/admin/site-operations"
              className="text-[10px] font-bold uppercase tracking-widest text-primary hover:text-primary/80 transition-colors"
            >
              View Site Operations →
            </Link>
          </div>
        )
      }
    };
  }, [activeProject, tasks, urgentTasks, financials]);

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
              aria-label="Search projects by name or code"
              placeholder="Search projects by name or code..."
              className="w-full bg-zinc-50 dark:bg-zinc-950/50 border border-zinc-200 dark:border-white/5 rounded-2xl pl-12 pr-4 py-4 text-zinc-900 dark:text-white outline-none focus:border-primary/40 transition-all shadow-inner"
              value={projectSearch}
              onChange={(e) => setProjectSearch(e.target.value)}
            />
            {previousProjectRef.current && (
              <button
                type="button"
                onClick={() => {
                  if (previousProjectRef.current) {
                    setActiveProject(previousProjectRef.current);
                    previousProjectRef.current = null;
                  }
                }}
                className="mt-4 px-4 py-2 text-xs font-bold uppercase tracking-widest text-zinc-500 hover:text-zinc-300 border border-zinc-700 rounded-xl transition-all"
              >
                Cancel: Return to {previousProjectRef.current.project_name}
              </button>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {projectsLoading ? (
              Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="h-24 bg-white/5 rounded-2xl animate-pulse" />
              ))
            ) : filteredProjects.length > 0 ? (
              filteredProjects.map((project) => (
                <button
                  type="button"
                  key={project.project_id || project._id}
                  onClick={() => setActiveProject(project)}
                  className="flex items-center gap-4 p-4 rounded-2xl bg-white/5 border border-white/5 hover:bg-white/10 hover:border-primary/20 transition-all text-left group active:scale-[0.98]"
                >
                  <div className="size-12 rounded-xl bg-primary/10 flex items-center justify-center text-primary border border-primary/20 group-hover:bg-primary group-hover:text-black transition-colors">
                    <LayoutGrid size={24} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h4 className="font-bold text-white truncate">{project.project_name}</h4>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-[10px] font-mono text-zinc-500 tracking-wider">
                        {project.project_code || "NO-CODE"}
                      </span>
                      <span className="size-1 rounded-full bg-zinc-700" />
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

  if ((isLoading || projectsLoading) && !financials && !financialError && !projectsError) {
    return (
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 animate-pulse p-2">
        <div className="col-span-full text-center mb-4">
          <p className="text-xs font-bold uppercase tracking-widest text-zinc-500 animate-pulse">
            Loading project context…
          </p>
        </div>
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
    <div className="space-y-[var(--dashboard-zone-gap)] pb-20">
      {/* ZONE 1: COMMAND STRIP (Context, Alert, KPIs) */}
      <section aria-label="Command Strip" className="space-y-6">
        {/* Project Context Bar */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-slate-100 dark:bg-white/5 border border-slate-200 dark:border-white/5 p-4 rounded-[2rem] backdrop-blur-md transition-colors">
          <div className="flex items-center gap-4 pl-2">
            <div className="size-12 rounded-2xl bg-primary/10 flex items-center justify-center text-primary border border-primary/20">
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
              <p className="text-xs font-mono text-zinc-400">{stats?.operational_id || activeProject.project_code || activeProject.project_id || 'N/A'}</p>
            </div>
            {/* Reset layout to default */}
            <button
              type="button"
              onClick={() => {
                useDashboardLayoutStore.getState().resetToDefault(activeProject.project_id);
                toast.success("Dashboard layout reset to default");
              }}
              className="px-4 py-2 bg-slate-500/10 hover:bg-slate-500/20 border border-slate-500/20 rounded-xl text-[10px] font-black uppercase tracking-widest text-slate-700 dark:text-zinc-300 transition-all active:scale-95"
            >
              Reset Layout
            </button>
            <button
              type="button"
              onClick={() => {
                previousProjectRef.current = activeProject;
                useProjectStore.getState().clearProject();
              }}
              className="px-4 py-2 bg-primary/10 hover:bg-primary/20 dark:bg-white/5 dark:hover:bg-white/10 border border-primary/30 dark:border-white/10 rounded-xl text-[10px] font-black uppercase tracking-widest text-primary dark:text-white transition-all active:scale-95"
            >
              Switch Project
            </button>
          </div>
        </div>

        {activeProject && (
          <PettyCashAlertBanner
            projectId={activeProject.project_id}
            projectName={activeProject.project_name}
          />
        )}

        {activeProject && (
          <div className="animate-in fade-in slide-in-from-top-4 duration-1000">
            <KPICards
              stats={stats?.overview}
              onInitializeBaseline={() => setIsEVMModalOpen(true)}
            />
          </div>
        )}
      </section>

      {/* ZONE 2: GRAPH THEATER (SCurve + Project Overview) */}
      <section aria-label="Graph Theater" className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* S-Curve Chart (2/3 width) */}
        <div className="lg:col-span-2">
          <GlassCard className="shadow-lg flex flex-col h-[500px]">
            <div className="flex items-center justify-between mb-6 shrink-0">
              <div className="flex items-center gap-3">
                <div className="size-8 rounded-lg bg-sky-500/5 flex items-center justify-center text-sky-400 border border-sky-500/10">
                  <TrendingUp size={16} />
                </div>
                <div>
                  <h2 className="text-xs font-bold tracking-tight uppercase text-slate-900 dark:text-white">Execution Analytics</h2>
                  <p className="text-[8px] text-zinc-500 dark:text-zinc-400 uppercase tracking-widest mt-0.5">S-Curve Variance</p>
                </div>
              </div>

              {/* S-Curve Legend */}
              <div className="flex gap-4 items-center pl-4 mr-auto select-none">
                <div className="flex items-center gap-1.5">
                  <div className="h-1.5 w-3 rounded-full bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.4)]" />
                  <span className="text-[10px] font-bold text-slate-500 dark:text-white/30 uppercase tracking-wider">PV</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="h-1.5 w-3 rounded-full bg-sky-500 shadow-[0_0_8px_rgba(56,189,248,0.4)]" />
                  <span className="text-[10px] font-bold text-slate-500 dark:text-white/30 uppercase tracking-wider">EV</span>
                </div>
              </div>

              <Link href="/admin/scheduler?tab=analytics" className="flex items-center gap-1.5 text-[10px] font-black uppercase tracking-widest text-primary hover:text-primary/80 transition-colors">
                View Full Analysis <ArrowRight size={12} />
              </Link>
            </div>
            <div className="flex-1 min-h-0">
              <SCurveChart totalBudget={totalBudget} pure />
            </div>
          </GlassCard>
        </div>

        {/* Project Overview KPIs (1/3 width - promoted position but fixed) */}
        <div className="lg:col-span-1">
          <GlassCard className="border-primary/20 h-[500px] flex flex-col justify-between p-6">
            <div>
              <div className="flex items-center gap-3 mb-8">
                <div className="size-10 rounded-xl bg-primary/10 flex items-center justify-center text-primary border border-primary/20">
                  <LayoutGrid size={20} />
                </div>
                <h2 className="text-xs font-bold tracking-tight uppercase text-slate-900 dark:text-white">Project Overview</h2>
              </div>
              
              <div className="space-y-8">
                <div>
                  <p className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-1">Portfolio Value</p>
                  <p className="text-4xl font-black">{formatCurrencySafe(stats?.overview?.total_budget ?? totalBudget)}</p>
                </div>

                <div className="grid grid-cols-2 gap-4 pb-4 border-b border-border/40">
                  <div>
                    <p className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-0.5">Total Phases</p>
                    <p className="text-xl font-bold">{stats?.overview?.total_phases ?? '-'}</p>
                  </div>
                  <div>
                    <p className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-0.5">Active Items</p>
                    <p className="text-xl font-bold text-primary">{stats?.overview?.active_items ?? '-'}</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="flex items-center justify-between pt-4">
              <div className="flex items-center gap-2">
                <AlertTriangle size={14} className={(stats?.overview?.overdue_milestones ?? 0) > 0 ? "text-rose-500" : "text-emerald-500"} />
                <span className={`text-[10px] font-bold uppercase tracking-tight ${(stats?.overview?.overdue_milestones ?? 0) > 0 ? "text-rose-500" : "text-emerald-500"}`}>Overdue Milestones</span>
              </div>
              <span className={`text-sm font-black ${(stats?.overview?.overdue_milestones ?? 0) > 0 ? "text-rose-500" : "text-emerald-500"}`}>{stats?.overview?.overdue_milestones ?? 0}</span>
            </div>
          </GlassCard>
        </div>
      </section>

      {/* ZONE 3: OPERATIONS GRID (Draggable 2-column list of widgets) */}
      {activeProject && (
        <section aria-label="Operations Grid">
          <DashboardDndGrid
            projectId={activeProject.project_id}
            widgets={dynamicWidgets}
          />
        </section>
      )}

      {activeProject && (
        <EVMBaselineModal
          isOpen={isEVMModalOpen}
          onClose={() => setIsEVMModalOpen(false)}
          onSuccess={async () => {
            // Update state in Zustand store immediately
            setActiveProject({
              ...activeProject,
              is_baseline_initialized: true,
            });
            // Revalidate stats & project list
            await mutateStats();
            await mutate("/api/v1/projects/");
          }}
          project={activeProject}
        />
      )}
    </div>
  );
}
