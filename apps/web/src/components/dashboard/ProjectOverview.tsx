"use client";

import React from "react";
import { TrendingUp, TrendingDown, AlertTriangle, CheckCircle, Clock, IndianRupee } from "lucide-react";
import { GlassCard } from "@/components/ui/GlassCard";
import { formatCurrencySafe } from "@/lib/formatters";

interface KPIMetric {
  label: string;
  value: string | number;
  unit?: string;
  icon: React.ReactNode;
  status: "green" | "yellow" | "red" | "neutral";
  trend?: "up" | "down" | "neutral";
}

interface ProjectOverviewProps {
  projectName: string;
  metrics: {
    days_remaining: number;
    tasks_at_risk: number;
    budget_utilization_pct: number;
    burn_rate_daily: number;
    schedule_status: "green" | "yellow" | "red";
    financial_status: "green" | "yellow" | "red";
  };
}

export const ProjectOverview: React.FC<ProjectOverviewProps> = ({
  projectName,
  metrics,
}) => {
  const kpis: KPIMetric[] = [
    {
      label: "Days Remaining",
      value: metrics.days_remaining,
      unit: "days",
      icon: <Clock className="size-5" />,
      status: metrics.schedule_status,
      trend: metrics.days_remaining > 10 ? "up" : "down",
    },
    {
      label: "Tasks at Risk",
      value: metrics.tasks_at_risk,
      icon: <AlertTriangle className="size-5" />,
      status: metrics.tasks_at_risk === 0 ? "green" : metrics.tasks_at_risk <= 3 ? "yellow" : "red",
    },
    {
      label: "Budget Utilization",
      value: Math.round(Number(metrics.budget_utilization_pct)),
      unit: "%",
      icon: <IndianRupee className="size-5" />,
      status: metrics.financial_status,
    },
    {
      label: "Daily Burn Rate",
      value: formatCurrencySafe(metrics.burn_rate_daily),
      icon: <TrendingDown className="size-5" />,
      status: "neutral" as const,
    },
    {
      label: "Schedule Health",
      value: metrics.schedule_status.toUpperCase(),
      icon: <CheckCircle className="size-5" />,
      status: metrics.schedule_status,
    },
    {
      label: "Financial Health",
      value: metrics.financial_status.toUpperCase(),
      icon: <IndianRupee className="size-5" />,
      status: metrics.financial_status,
    },
  ];

  const getStatusColor = (status: string) => {
    switch (status) {
      case "green":
        return "border-l-4 border-l-emerald-500 bg-emerald-500/5";
      case "yellow":
        return "border-l-4 border-l-amber-500 bg-amber-500/5";
      case "red":
        return "border-l-4 border-l-red-500 bg-red-500/5";
      default:
        return "border-l-4 border-l-slate-500 bg-slate-500/5";
    }
  };

  return (
    <div className="w-full">
      <h2 className="text-xl font-semibold text-slate-900 dark:text-slate-100 mb-6">
        {projectName} Overview
      </h2>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {kpis.map((kpi, idx) => (
          <GlassCard key={idx} className={`${getStatusColor(kpi.status)} p-4`}>
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <p className="text-sm font-medium text-slate-600 dark:text-slate-400 mb-1">
                  {kpi.label}
                </p>
                <div className="flex items-baseline gap-1">
                  <span className="text-2xl font-bold text-slate-900 dark:text-slate-100">
                    {kpi.value}
                  </span>
                  {kpi.unit && (
                    <span className="text-sm text-slate-500 dark:text-slate-500">
                      {kpi.unit}
                    </span>
                  )}
                </div>
              </div>
              <div className={`p-2 rounded-lg ${
                kpi.status === "green" ? "bg-emerald-500/20 text-emerald-600 dark:text-emerald-400" :
                kpi.status === "yellow" ? "bg-amber-500/20 text-amber-600 dark:text-amber-400" :
                kpi.status === "red" ? "bg-red-500/20 text-red-600 dark:text-red-400" :
                "bg-slate-500/20 text-slate-600 dark:text-slate-400"
              }`}>
                {kpi.icon}
              </div>
            </div>
            {kpi.trend && (
              <div className="mt-2 flex items-center gap-1 text-xs">
                {kpi.trend === "up" ? (
                  <TrendingUp className="size-3 text-emerald-600 dark:text-emerald-400" />
                ) : (
                  <TrendingDown className="size-3 text-red-600 dark:text-red-400" />
                )}
                <span className={kpi.trend === "up" ? "text-emerald-600 dark:text-emerald-400" : "text-red-600 dark:text-red-400"}>
                  {kpi.trend === "up" ? "Improving" : "Declining"}
                </span>
              </div>
            )}
          </GlassCard>
        ))}
      </div>
    </div>
  );
};
