"use client";

import React, { useMemo } from "react";
import useSWR from "swr";
import { useProjectStore } from "@/store/projectStore";
import { fetcher } from "@/lib/api";
import { ProjectOverview } from "@/components/dashboard/ProjectOverview";
import { ScheduleHealthChart } from "@/components/dashboard/ScheduleHealthChart";
import ResourceUtilization from "@/components/dashboard/ResourceUtilization";
import BudgetTrend from "@/components/dashboard/BudgetTrend";
import TaskTimeline from "@/components/dashboard/TaskTimeline";
import { AISummaryCard } from "@/components/dashboard/AISummaryCard";

interface ScheduleHealthMetrics {
  days_remaining: number;
  tasks_at_risk: number;
  critical_path_days: number;
  status: "green" | "yellow" | "red";
}

interface ResourceMetrics {
  name: string;
  allocated_percent: number;
  available_hours: number;
  allocated_hours: number;
  overallocated: boolean;
}

interface RoleMetrics {
  role: string;
  total_allocated_percent: number;
  resource_count: number;
  overallocated_resources: number;
}

interface DayMetric {
  date: string;
  value: number;
}

interface ProjectDashboardData {
  project_id: string;
  project_name: string;
  schedule: ScheduleHealthMetrics;
  resources: {
    by_resource?: ResourceMetrics[];
    by_role?: RoleMetrics[];
  };
  financial: {
    budget_total: number;
    budget_spent: number;
    budget_remaining: number;
    burn_rate_daily: number;
  };
  timeline: {
    daily_completion: DayMetric[];
    utilization_trend?: DayMetric[];
  };
  updated_at: string;
}

export default function DashboardPage() {
  const activeProject = useProjectStore((state: any) => state.activeProject);

  const {
    data: dashboardData,
    error,
    isLoading,
  } = useSWR<ProjectDashboardData>(
    activeProject ? `/api/v1/reporting/${activeProject.project_id}/dashboard` : null,
    fetcher,
    {
      revalidateOnFocus: false,
      dedupingInterval: 60000, // 1 minute
    }
  );

  const budgetUtilizationPct = useMemo(
    () =>
      dashboardData && dashboardData.financial.budget_total > 0
        ? (dashboardData.financial.budget_spent / dashboardData.financial.budget_total) * 100
        : 0,
    [dashboardData]
  );

  const financialStatus = useMemo(() => {
    if (!dashboardData) return "green";
    if (budgetUtilizationPct > 100) return "red";
    if (budgetUtilizationPct > 80) return "yellow";
    return "green";
  }, [dashboardData, budgetUtilizationPct]);

  if (!activeProject) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 p-8">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-center py-20 text-center">
            <div className="space-y-4">
              <h1 className="text-2xl font-bold text-white">No Project Selected</h1>
              <p className="text-slate-400">Select a project from the sidebar to view the dashboard.</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 p-8">
      <div className="max-w-7xl mx-auto space-y-8">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold text-white mb-1">Dashboard</h1>
          <p className="text-slate-400 text-sm">
            {dashboardData?.project_name || activeProject.project_name}
          </p>
        </div>

        {/* Loading State */}
        {isLoading && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {[...Array(4)].map((_, i) => (
              <div
                key={i}
                className="bg-slate-800/50 border border-white/5 rounded-lg h-64 animate-pulse"
              />
            ))}
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-red-400 text-sm">
            Failed to load dashboard data. Please try again.
          </div>
        )}

        {/* Dashboard Grid */}
        {dashboardData && !isLoading && (
          <div className="space-y-8">
            {/* Row 1: Overview + Schedule Health */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-1">
                <ProjectOverview
                  projectName={dashboardData.project_name}
                  metrics={{
                    days_remaining: dashboardData.schedule.days_remaining,
                    tasks_at_risk: dashboardData.schedule.tasks_at_risk,
                    budget_utilization_pct: budgetUtilizationPct,
                    burn_rate_daily: dashboardData.financial.burn_rate_daily,
                    schedule_status: dashboardData.schedule.status,
                    financial_status: financialStatus,
                  }}
                />
              </div>
              <div className="lg:col-span-2">
                <ScheduleHealthChart
                  daysRemaining={dashboardData.schedule.days_remaining}
                  tasksAtRisk={dashboardData.schedule.tasks_at_risk}
                  criticalPathDays={dashboardData.schedule.critical_path_days}
                />
              </div>
            </div>

            {/* Row 1.5: AI Summary */}
            <div>
              <AISummaryCard projectId={activeProject.project_id} />
            </div>

            {/* Row 2: Budget Trend + Task Timeline */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <BudgetTrend
                data={dashboardData.timeline.daily_completion}
                budget_total={dashboardData.financial.budget_total}
                title="Budget Burn Rate"
              />
              <TaskTimeline
                daily_completion={dashboardData.timeline.daily_completion}
                utilization_trend={dashboardData.timeline.utilization_trend}
                title="Task Completion Timeline"
              />
            </div>

            {/* Row 3: Resource Utilization */}
            <ResourceUtilization
              by_resource={dashboardData.resources.by_resource}
              by_role={dashboardData.resources.by_role}
              title="Resource Allocation & Utilization"
            />

            {/* Footer: Last Updated */}
            <div className="text-xs text-slate-500 text-center">
              Last updated: {new Date(dashboardData.updated_at).toLocaleString()}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
