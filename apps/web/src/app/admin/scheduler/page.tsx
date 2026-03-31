"use client";

import React, { useEffect, useRef, useState } from "react";
import { AlertTriangle, FileDown, Info, Plus, RefreshCw, Upload, CalendarDays, Database } from "lucide-react";
import { toast } from "sonner";

import { useProjectStore } from "@/store/projectStore";
import { useScheduleStore } from "@/store/useScheduleStore";
import { schedulerApi } from "@/lib/api";
import SchedulerGrid from "@/components/scheduler/SchedulerGrid";
import GanttChart from "@/components/scheduler/GanttChart";
import KanbanBoard from "@/components/scheduler/KanbanBoard";
import TaskDrawer from "@/components/scheduler/TaskDrawer";
import KPICards from "@/components/dashboard/KPICards";
import SCurveChart from "@/components/dashboard/SCurveChart";
import CashFlowChart from "@/components/dashboard/CashFlowChart";
import ResourceHeatmap from "@/components/dashboard/ResourceHeatmap";
import { AISummaryCard } from "@/components/dashboard/AISummaryCard";
import { Button } from "@/components/ui/button";

export default function ProjectSchedulerPage() {
  const { activeProject } = useProjectStore();
  const loadSchedule = useScheduleStore((state) => state.loadSchedule);
  const createDraftTask = useScheduleStore((state) => state.createDraftTask);
  const pendingCalculation = useScheduleStore((state) => state.pendingCalculation);
  const calculationError = useScheduleStore((state) => state.calculationError);
  const systemState = useScheduleStore((state) => state.systemState);
  const taskCount = useScheduleStore((state) => Object.keys(state.taskMap).length);
  const [loading, setLoading] = useState(false);
  const [importing, setImporting] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [migrating, setMigrating] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!activeProject?.project_id) return;

    let cancelled = false;
    setLoading(true);

    schedulerApi
      .load(activeProject.project_id)
      .then((response) => {
        if (cancelled) return;
        loadSchedule(response);
      })
      .catch(() => {
        if (!cancelled) {
          toast.error("Failed to load schedule");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [activeProject?.project_id, loadSchedule]);

  const handleAddTask = () => {
    if (!activeProject?.project_id) return;
    const task = createDraftTask(activeProject.project_id);
    toast.info(`Added ${task.task_id}`);
  };

  const handleReload = async () => {
    if (!activeProject?.project_id) return;
    setLoading(true);
    try {
      const response = await schedulerApi.load(activeProject.project_id);
      loadSchedule(response);
      toast.success("Schedule refreshed from server");
    } catch {
      toast.error("Failed to refresh schedule");
    } finally {
      setLoading(false);
    }
  };

  const handleImportSchedule = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file || !activeProject?.project_id) return;

    setImporting(true);
    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await schedulerApi.importMpp(activeProject.project_id, formData);
      if (response?.tasks) {
        loadSchedule(response);
        toast.success(`Imported ${response.tasks.length} tasks from ${file.name}`);
      }
      if (response?.warning) {
        toast.info(response.warning);
      }
    } catch {
      toast.error("Failed to import schedule file");
    } finally {
      setImporting(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleExport = async () => {
    if (!activeProject?.project_id) return;
    setExporting(true);
    try {
      await schedulerApi.exportPdf(activeProject.project_id);
      const pdfBlob = await schedulerApi.downloadPdf(activeProject.project_id);
      const blobUrl = window.URL.createObjectURL(pdfBlob.data as Blob);
      const link = document.createElement("a");
      link.href = blobUrl;
      link.download = `gantt_${activeProject.project_id}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(blobUrl);
      toast.success("PDF exported");
    } catch {
      toast.error("Failed to export PDF");
    } finally {
      setExporting(false);
    }
  };

  const handleMigrate = async () => {
    if (!activeProject?.project_id) return;

    const confirmMigrate = window.confirm(
      "This will import tasks from legacy 'payment_schedule'. Are you sure? (Dry Run first)"
    );
    if (!confirmMigrate) return;

    setMigrating(true);
    try {
      const report = await schedulerApi.migrateLegacyData(activeProject.project_id, true);
      console.log("Migration Dry Run Report:", report);

      const proceed = window.confirm(
        `Dry Run Result: Found ${report.total_legacy_tasks} tasks. Migrated: ${report.total_migrated}. Variance: ${report.cost_variance}. Proceed with LIVE migration?`
      );

      if (proceed) {
        const finalReport = await schedulerApi.migrateLegacyData(activeProject.project_id, false);
        toast.success(`Successfully migrated ${finalReport.total_migrated} tasks.`);
        handleReload();
      }
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Migration failed");
    } finally {
      setMigrating(false);
    }
  };

  if (!activeProject) {
    return (
      <div className="flex min-h-[500px] items-center justify-center">
        <div className="empty-state-luxury max-w-sm">
          <div className="empty-state-luxury-icon">
            <CalendarDays size={32} />
          </div>
          <h3 className="empty-state-luxury-title">No Project Context</h3>
          <p className="empty-state-luxury-desc">
            Select an operational project to open the scheduler canvas.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-[1800px] space-y-8 pb-20 animate-in fade-in duration-700">
      <div className="rounded-[36px] border border-white/5 bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 p-8 shadow-2xl">
        <div className="flex flex-col gap-6 xl:flex-row xl:items-center xl:justify-between">
          <div className="space-y-3">
            <h1 className="text-3xl font-black italic uppercase tracking-tight text-white">
              Project Scheduler
            </h1>
            <p className="max-w-2xl text-[10px] font-bold uppercase tracking-[0.3em] text-slate-500">
              Phase 3 canvas driven entirely by the shared Zustand store
            </p>
            <div className="flex flex-wrap items-center gap-2 text-[10px] font-black uppercase tracking-[0.18em] text-slate-400">
              <span className="rounded-full border border-white/5 bg-white/[0.03] px-2 py-1">
                {taskCount.toLocaleString("en-US")} tasks
              </span>
              <span className="rounded-full border border-white/5 bg-white/[0.03] px-2 py-1">
                {systemState ?? "draft"} state
              </span>
              {pendingCalculation && (
                <span className="rounded-full border border-amber-400/20 bg-amber-500/10 px-2 py-1 text-amber-300">
                  Recalculating
                </span>
              )}
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <Button
              onClick={handleAddTask}
              variant="secondary"
              className="rounded-2xl border border-white/10 bg-white/5 font-bold text-white hover:bg-white/10"
            >
              <Plus size={16} /> Add Task
            </Button>

            <input
              type="file"
              ref={fileInputRef}
              className="hidden"
              accept=".mpp,.xml,.pdf"
              onChange={handleImportSchedule}
            />

            <Button
              onClick={() => fileInputRef.current?.click()}
              variant="outline"
              disabled={importing}
              className="rounded-2xl border border-white/10 bg-white/5 font-bold text-white hover:bg-white/10"
            >
              <Upload size={16} className={importing ? "animate-bounce" : ""} />
              {importing ? "Importing..." : "Import"}
            </Button>

            <Button
              onClick={handleReload}
              disabled={loading}
              variant="outline"
              className="rounded-2xl border border-white/10 bg-white/5 font-bold text-white hover:bg-white/10"
            >
              <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
              {loading ? "Loading..." : "Reload"}
            </Button>

            <Button
              onClick={handleExport}
              disabled={exporting}
              variant="outline"
              className="rounded-2xl border border-white/10 bg-white/5 font-bold text-white hover:bg-white/10"
            >
              <FileDown size={16} />
              {exporting ? "Exporting..." : "Export PDF"}
            </Button>

            <Button
              onClick={handleMigrate}
              disabled={migrating || taskCount > 0}
              variant="outline"
              className="rounded-2xl border border-amber-500/20 bg-amber-500/10 font-bold text-amber-200 hover:bg-amber-500/20"
            >
              <Database size={16} className={migrating ? "animate-pulse" : ""} />
              {migrating ? "Migrating..." : "Migrate Legacy"}
            </Button>
          </div>
        </div>

        {calculationError && (
          <div className="mt-6 flex items-center gap-3 rounded-2xl border border-rose-400/20 bg-rose-500/10 px-4 py-3 text-rose-200">
            <AlertTriangle size={16} />
            <p className="text-xs font-semibold">{calculationError}</p>
          </div>
        )}
      </div>

      <KPICards />

      <div className="grid gap-8 xl:grid-cols-[minmax(0,1fr)_420px]">
        <div className="space-y-8">
          <SchedulerGrid />
          <GanttChart />
          <KanbanBoard />
        </div>

        <div className="space-y-8">
          <TaskDrawer />
          {activeProject?.project_id && <AISummaryCard projectId={activeProject.project_id} />}
          <SCurveChart />
        </div>
      </div>

      <div className="grid gap-8 xl:grid-cols-2">
        <CashFlowChart />
        <ResourceHeatmap data={[]} />
      </div>

      <div className="flex items-center gap-6 rounded-3xl border border-white/5 bg-white/[0.03] p-6">
        <div className="rounded-2xl bg-orange-500/10 p-3 text-orange-400">
          <Info size={24} />
        </div>
        <div>
          <p className="text-xs font-bold uppercase tracking-widest text-white">
            Active Scheduler Directives
          </p>
          <p className="mt-1 text-[10px] uppercase tracking-[0.18em] text-slate-500">
            Shared store is the source of truth. Grid, Gantt, Kanban, drawer, and analytics all re-render from the same state tree.
          </p>
        </div>
      </div>
    </div>
  );
}
