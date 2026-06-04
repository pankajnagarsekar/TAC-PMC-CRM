"use client";

import React, { useEffect, useMemo, useState, lazy, Suspense } from "react";
import useSWR from "swr";
import { useProjectStore } from "@/store/projectStore";
import { useScheduleStore } from "@/store/useScheduleStore";
import { useAnalyticsStore } from "@/store/useAnalyticsStore";
import { fetcher } from "@/lib/api";
import { normalizeTaskOrder } from "@/components/scheduler/scheduler-utils";

// Sub-components
import AnalyticsKPIRow from "./AnalyticsKPIRow";
import AnalyticsFilterBar from "./AnalyticsFilterBar";
import InsightSummaryPanel from "./InsightSummaryPanel";
import AnalyticsDetailGrid from "./AnalyticsDetailGrid";

// Lazy-loaded charts
const SCurveChart = lazy(() => import("../scheduler/SCurveChart"));
const PlannedVsActualChart = lazy(() => import("./charts/PlannedVsActualChart"));
const TaskStatusDistribution = lazy(() => import("./charts/TaskStatusDistribution"));
const MilestoneTrendChart = lazy(() => import("./charts/MilestoneTrendChart"));
const CriticalTasksChart = lazy(() => import("./charts/CriticalTasksChart"));
const ScheduleVarianceChart = lazy(() => import("./charts/ScheduleVarianceChart"));
const CostOverviewChart = lazy(() => import("./charts/CostOverviewChart"));
const ResourceLoadChart = lazy(() => import("./charts/ResourceLoadChart"));
const DelayTrendChart = lazy(() => import("./charts/DelayTrendChart"));
const CashFlowProjectionChart = lazy(() => import("./charts/CashFlowProjectionChart"));
const EarnedValueSummaryChart = lazy(() => import("./charts/EarnedValueSummaryChart"));
const CompletionForecastChart = lazy(() => import("./charts/CompletionForecastChart"));

export default function AnalyticsContainer() {
  const activeProject = useProjectStore((state) => state.activeProject);
  const taskMap = useScheduleStore((state) => state.taskMap);
  const taskOrder = useScheduleStore((state) => state.taskOrder);
  
  const selectedChart = useAnalyticsStore((state) => state.selectedChart);
  const filters = useAnalyticsStore((state) => state.filters);
  const computedMetrics = useAnalyticsStore((state) => state.computedMetrics);
  const recomputeMetrics = useAnalyticsStore((state) => state.recomputeMetrics);
  const fetchAnalytics = useAnalyticsStore((state) => state.fetchAnalytics);

  const loading = useScheduleStore((state) => state.loading);

  // Fetch financials if active project exists
  const { data: financials } = useSWR(
    activeProject ? `/api/v1/projects/${activeProject.project_id}/financials` : null,
    fetcher
  );

  // Normalize tasks list
  const tasks = useMemo(() => normalizeTaskOrder(taskMap, taskOrder), [taskMap, taskOrder]);

  // Recompute KPIs when tasks, filters or financials change
  useEffect(() => {
    recomputeMetrics(tasks, financials);
  }, [tasks, filters, financials, recomputeMetrics]);

  // Fetch backend analytics metrics if project ID is available
  useEffect(() => {
    if (activeProject?.project_id) {
      fetchAnalytics(activeProject.project_id);
    }
  }, [activeProject?.project_id, fetchAnalytics]);

  // Dynamically render selected chart
  const renderChart = () => {
    switch (selectedChart) {
      case "s_curve":
        return <SCurveChart totalBudget={computedMetrics?.totalTasks} />;
      case "planned_vs_actual":
        return <PlannedVsActualChart tasks={tasks} />;
      case "task_status":
        return <TaskStatusDistribution tasks={tasks} />;
      case "milestone_trend":
        return <MilestoneTrendChart tasks={tasks} />;
      case "critical_tasks":
        return <CriticalTasksChart tasks={tasks} />;
      case "schedule_variance":
        return <ScheduleVarianceChart tasks={tasks} />;
      case "cost_overview":
        return <CostOverviewChart tasks={tasks} financials={financials} projectId={activeProject?.project_id} />;
      case "resource_load":
        return <ResourceLoadChart tasks={tasks} />;
      case "delay_trend":
        return <DelayTrendChart tasks={tasks} />;
      case "cash_flow":
        return <CashFlowProjectionChart tasks={tasks} projectId={activeProject?.project_id} />;
      case "earned_value":
        return <EarnedValueSummaryChart tasks={tasks} />;
      case "completion_forecast":
        return <CompletionForecastChart tasks={tasks} />;
      default:
        return <SCurveChart totalBudget={computedMetrics?.totalTasks} />;
    }
  };

  if (!activeProject) return null;

  return (
    <div className="space-y-6">
      {/* KPI Row */}
      <AnalyticsKPIRow />

      {/* Filter and Switcher Control Bar */}
      <AnalyticsFilterBar />

      {/* Main Content Layout */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Left/Center: Chart Panel */}
        <div className="lg:col-span-2 space-y-6">
          <div className="rounded-[24px] border border-slate-200 dark:border-white/5 bg-white/60 dark:bg-slate-950/60 p-6 shadow-2xl backdrop-blur-xl min-h-[460px]">
            {loading ? (
              <div className="flex h-[400px] w-full items-center justify-center animate-pulse bg-slate-100 dark:bg-white/5 rounded-2xl" />
            ) : (
              <Suspense fallback={
                <div className="flex h-[400px] w-full items-center justify-center">
                  <div className="h-8 w-8 animate-spin rounded-full border-4 border-orange-500 border-t-transparent" />
                </div>
              }>
                {renderChart()}
              </Suspense>
            )}
          </div>
        </div>

        {/* Right: Insights Panel */}
        <div className="lg:col-span-1">
          {loading ? (
            <div className="h-[460px] w-full rounded-[24px] bg-slate-100 dark:bg-white/5 animate-pulse" />
          ) : (
            <InsightSummaryPanel />
          )}
        </div>
      </div>

      {/* Detail Grid */}
      {!loading && <AnalyticsDetailGrid tasks={tasks} financials={financials} />}
    </div>
  );
}
