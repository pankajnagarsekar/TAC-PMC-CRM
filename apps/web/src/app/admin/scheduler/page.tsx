"use client";

import React, { useEffect, useRef, useState } from "react";
import { AlertTriangle, FileDown, Info, Plus, Upload, CalendarDays, Database, Grid3X3, GanttChart as GanttIcon, ListTodo, Landmark, TrendingUp } from "lucide-react";
import { useSearchParams, useRouter } from "next/navigation";
import * as Tabs from "@radix-ui/react-tabs";
import { toast } from "sonner";

import { useProjectStore } from "@/store/projectStore";
import { useScheduleStore } from "@/store/useScheduleStore";
import { useAuthStore } from "@/store/authStore";
import { schedulerApi, fetcher } from "@/lib/api";
import useSWR from "swr";
import { DerivedFinancialState } from "@/types/api";
import SchedulerGrid from "@/components/scheduler/SchedulerGrid";
import GanttChart from "@/components/scheduler/GanttChart";
import KanbanBoard from "@/components/scheduler/KanbanBoard";
import TaskDrawer from "@/components/scheduler/TaskDrawer";
import FinancialChart from "@/components/ui/FinancialChart";
import { Button } from "@/components/ui/button";
import SCurveChart from "@/components/scheduler/SCurveChart";
import { GlassCard } from "@/components/ui/GlassCard";

export default function ProjectSchedulerPage() {
  const { activeProject } = useProjectStore();
  const searchParams = useSearchParams();
  const router = useRouter();
  const currentTab = searchParams.get("tab") || "grid";

  const loadSchedule = useScheduleStore((state) => state.loadSchedule);
  const createDraftTask = useScheduleStore((state) => state.createDraftTask);
  const pendingCalculation = useScheduleStore((state) => state.pendingCalculation);
  const calculationError = useScheduleStore((state) => state.calculationError);
  const taskCount = useScheduleStore((state) => Object.keys(state.taskMap).length);
  const { user } = useAuthStore();

  const [importing, setImporting] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [migrating, setMigrating] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { data: financials } = useSWR(
    activeProject ? `/api/v1/projects/${activeProject.project_id}/financials` : null,
    fetcher
  );

  const isClient = user?.role === "Client";

  useEffect(() => {
    if (activeProject) {
      schedulerApi
        .load(activeProject.project_id)
        .then((data) => {
          loadSchedule(data);
        })
        .catch((err) => {
          console.error("Scheduler load error:", err);
          toast.error("Failed to load project schedule repository.");
        });
    }
  }, [activeProject, loadSchedule]);

  const handleTabChange = (value: string) => {
    const params = new URLSearchParams(searchParams);
    params.set("tab", value);
    router.replace(`?${params.toString()}`);
  };

  const handleAddTask = () => {
    if (!activeProject) return;
    const newTask = createDraftTask(activeProject.project_id);
    toast.success(`Task ${newTask.task_id} created as draft.`);
  };

  const handleImportSchedule = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file || !activeProject) return;

    const formData = new FormData();
    formData.append("file", file);

    setImporting(true);
    try {
      const response = await schedulerApi.importMpp(activeProject.project_id, formData);
      loadSchedule(response);
      toast.success("Schedule imported and calculated successfully.");
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      toast.error(error?.response?.data?.detail || "Import failed.");
    } finally {
      setImporting(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleExport = async () => {
    if (!activeProject) return;
    setExporting(true);
    try {
      // First trigger the background export process
      await schedulerApi.exportPdf(activeProject.project_id);

      // Then download (in this implementation, we combine or use the download endpoint)
      const response = await schedulerApi.downloadPdf(activeProject.project_id);
      const blob = response.data;
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `Schedule_${activeProject.project_id}_${new Date().toISOString()}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      toast.success("Schedule export generated.");
    } catch {
      toast.error("Export failed. Please try again.");
    } finally {
      setExporting(false);
    }
  };

  const handleMigrate = async () => {
    if (!activeProject) return;
    setMigrating(true);
    try {
      const response = await schedulerApi.migrateLegacyData(activeProject.project_id, false);
      loadSchedule(response);
      toast.success("Legacy data migrated into current planner.");
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      toast.error(error?.response?.data?.detail || "Migration failed.");
    } finally {
      setMigrating(false);
    }
  };

  if (!activeProject) {
    return (
      <div className="flex h-[70vh] flex-col items-center justify-center p-8 text-center">
        <GlassCard className="max-w-md p-10 border-orange-500/20">
          <div className="mx-auto mb-6 flex h-20 w-20 items-center justify-center rounded-3xl bg-orange-500/10 text-orange-500 shadow-xl shadow-orange-500/20">
            <Info size={40} />
          </div>
          <h2 className="mb-3 text-2xl font-black uppercase tracking-tight text-white">No Project Selected</h2>
          <p className="text-sm font-medium text-slate-400">Please select a project from the header to view and manage its delivery schedule.</p>
        </GlassCard>
      </div>
    );
  }

  return (
    <div className="px-4 py-6 sm:px-6 lg:px-8">
      <div className="mb-8 flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-center gap-5">
          <div className="flex h-14 w-14 items-center justify-center rounded-[20px] bg-gradient-to-br from-orange-500 to-orange-600 text-white shadow-xl shadow-orange-500/30">
            <CalendarDays size={28} />
          </div>
          <div>
            <h1 className="text-2xl font-black uppercase tracking-tight text-slate-900 dark:text-white sm:text-3xl">Project Planner</h1>
            <div className="mt-1 flex items-center gap-3">
              <span className="flex items-center gap-1.5 rounded-full border border-orange-500/30 bg-orange-500/5 px-2.5 py-0.5 text-[10px] font-black uppercase tracking-widest text-orange-500">
                {activeProject.project_code || "PRJ-00"}
              </span>
              <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-slate-500">
                {activeProject.project_name}
              </span>
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="flex rounded-2xl border border-slate-200 dark:border-white/5 bg-slate-100 dark:bg-slate-950/40 p-1 shadow-inner backdrop-blur-md">
            {[
              { value: "grid", label: "Grid", icon: Grid3X3 },
              { value: "gantt", label: "Gantt", icon: GanttIcon },
              { value: "kanban", label: "Kanban", icon: ListTodo },
              { value: "analytics", label: "Analytics", icon: TrendingUp },
              { value: "budget", label: "Budget", icon: Landmark },
              { value: "export", label: "Export", icon: Upload },
            ].map((tab) => {
              const TabIcon = tab.icon;
              const isActive = currentTab === tab.value;
              return (
                <button
                  key={tab.value}
                  onClick={() => handleTabChange(tab.value)}
                  className={`flex items-center gap-2 rounded-xl px-4 py-2 text-[10px] font-black uppercase tracking-[0.2em] transition-all duration-300 ${isActive
                    ? "bg-orange-600 dark:bg-orange-500 text-white shadow-lg shadow-orange-500/20"
                    : "text-slate-500 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-white/5 hover:text-slate-900 dark:hover:text-white"
                    }`}
                >
                  <TabIcon size={12} />
                  <span className="hidden sm:inline">{tab.label}</span>
                </button>
              );
            })}
          </div>

          <Button
            onClick={handleAddTask}
            disabled={pendingCalculation || isClient}
            className="h-11 rounded-2xl bg-orange-600 dark:bg-orange-500 px-6 font-black uppercase tracking-widest text-white shadow-xl shadow-orange-500/30 transition-transform active:scale-95 disabled:opacity-50"
          >
            <Plus size={18} className="mr-2" />
            Add Task
          </Button>
        </div>
      </div>

      {
        calculationError && (
          <GlassCard className="mb-8 border-rose-500/20 bg-rose-500/5 p-4">
            <div className="flex items-center gap-3 text-rose-500">
              <AlertTriangle size={20} />
              <p className="text-xs font-bold uppercase tracking-widest">{calculationError}</p>
            </div>
          </GlassCard>
        )
      }

      <Tabs.Root value={currentTab} onValueChange={handleTabChange} className="space-y-8">
        <div className="grid grid-cols-1 gap-8 xl:grid-cols-[minmax(0,1fr)_420px]">
          <div className="min-w-0 space-y-8">
            <Tabs.Content value="grid" className="animate-in fade-in slide-in-from-left-4 duration-500 focus:outline-none">
              <SchedulerGrid />
            </Tabs.Content>

            <Tabs.Content value="gantt" className="animate-in fade-in slide-in-from-left-4 duration-500 focus:outline-none">
              <GanttChart />
            </Tabs.Content>

            <Tabs.Content value="kanban" className="animate-in fade-in slide-in-from-left-4 duration-500 focus:outline-none">
              <KanbanBoard />
            </Tabs.Content>

            <Tabs.Content value="analytics" className="animate-in fade-in slide-in-from-left-4 duration-500 focus:outline-none">
              <SCurveChart />
            </Tabs.Content>

            <Tabs.Content value="budget" className="animate-in fade-in slide-in-from-left-4 duration-500 focus:outline-none">
              <div className="max-w-5xl mx-auto space-y-8">
                <h3 className="text-zinc-500 uppercase tracking-widest text-[10px] font-bold px-4">Financial Status — Planned vs Actuals per Category</h3>
                <FinancialChart
                  title=""
                  data={financials?.map((f: DerivedFinancialState) => ({
                    name: f.category_name || f.category_code || 'N/A',
                    budget: f.original_budget,
                    committed: f.committed_value
                  })) || []}
                  dataKeys={[
                    { key: 'budget', color: '#775a19', label: 'Planned' },
                    { key: 'committed', color: '#505f7a', label: 'Actual' }
                  ]}
                  height={500}
                />
              </div>
            </Tabs.Content>

            <Tabs.Content value="export" className="animate-in fade-in slide-in-from-left-4 duration-500 focus:outline-none">
              <div className="max-w-4xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-6">
                <GlassCard className="p-8 space-y-6">
                  <div className="w-12 h-12 rounded-2xl bg-orange-500/10 border border-orange-500/20 flex items-center justify-center text-orange-500">
                    <Upload size={24} />
                  </div>
                  <div>
                    <h4 className="text-lg font-bold text-slate-900 dark:text-white uppercase tracking-tight">Import Data</h4>
                    <p className="text-zinc-500 text-xs mt-1">Upload Microsoft Project (.mpp), XML, or CSV files to seed the schedule.</p>
                  </div>
                  <input
                    type="file"
                    ref={fileInputRef}
                    className="hidden"
                    accept=".mpp,.xml,.pdf"
                    onChange={handleImportSchedule}
                  />
                  <Button
                    onClick={() => fileInputRef.current?.click()}
                    disabled={importing || isClient}
                    className="w-full rounded-xl bg-orange-600 dark:bg-orange-500 text-white font-black uppercase tracking-widest h-12"
                  >
                    {importing ? "Processing..." : "Select File"}
                  </Button>
                </GlassCard>

                <GlassCard className="p-8 space-y-6">
                  <div className="w-12 h-12 rounded-2xl bg-sky-500/10 border border-sky-500/20 flex items-center justify-center text-sky-400">
                    <FileDown size={24} />
                  </div>
                  <div>
                    <h4 className="text-lg font-bold text-slate-900 dark:text-white uppercase tracking-tight">Export PDF</h4>
                    <p className="text-zinc-500 text-xs mt-1">Generate a high-fidelity PDF report of the current Gantt and table state.</p>
                  </div>
                  <Button
                    onClick={handleExport}
                    disabled={exporting}
                    className="w-full rounded-xl bg-slate-100 dark:bg-white/5 border border-slate-200 dark:border-white/10 hover:bg-slate-200 dark:hover:bg-white/10 text-slate-900 dark:text-white font-black uppercase tracking-widest h-12"
                  >
                    {exporting ? "Generating..." : "Download Report"}
                  </Button>
                </GlassCard>

                {!isClient && (
                  <GlassCard className="p-8 space-y-6 md:col-span-2 border-amber-500/20 bg-amber-500/5">
                    <div className="flex items-center gap-6">
                      <div className="w-12 h-12 rounded-2xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-500">
                        <Database size={24} />
                      </div>
                      <div className="flex-1">
                        <h4 className="text-lg font-bold text-amber-600 dark:text-amber-500 uppercase tracking-tight">Legacy Migration</h4>
                        <p className="text-zinc-500 text-xs mt-1">Bridge data from the legacy ERP payment schedule modules into this new unified planner.</p>
                      </div>
                      <button
                        onClick={handleMigrate}
                        disabled={migrating || taskCount > 0}
                        className="rounded-xl border border-amber-500/40 text-amber-600 dark:text-amber-500 hover:bg-amber-500/10 font-bold uppercase tracking-widest h-12 px-8"
                      >
                        {migrating ? "Migrating..." : "Start Migration"}
                      </button>
                    </div>
                  </GlassCard>
                )}
              </div>
            </Tabs.Content>
          </div>

          {(currentTab === "grid" || currentTab === "gantt" || currentTab === "kanban") && (
            <div className="w-[420px] hidden xl:block">
              <TaskDrawer />
            </div>
          )}
        </div>
      </Tabs.Root>
    </div >
  );
}
