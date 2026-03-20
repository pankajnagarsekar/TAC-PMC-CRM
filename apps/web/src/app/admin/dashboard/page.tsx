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
  CreditCard,
  Users,
  HardHat,
  Clock,
  PieChart as PieChartIcon,
  BarChart as BarChartIcon,
} from "lucide-react";
import { fetcher } from "@/lib/api";
import { DerivedFinancialState } from "@/types/api";
import { formatCurrency } from "@tac-pmc/ui";
import { useProjectStore } from "@/store/projectStore";
import KPICard from "@/components/ui/KPICard";
import { DonutChart, BarChart } from "@tremor/react";
import NetworkErrorRetry from "@/components/ui/NetworkErrorRetry";

export default function AdminDashboard() {
  const { activeProject } = useProjectStore();

  const { data: financials, error: financialsError, isLoading, mutate: retryFinancials } = useSWR<DerivedFinancialState[]>(
    activeProject
      ? `/api/v2/projects/${activeProject.project_id}/financials`
      : null,
    fetcher,
  );

  const { data: vendorPayables } = useSWR<
    { vendor_id: string; vendor_name: string; total_payable: number }[]
  >(
    activeProject
      ? `/api/v2/projects/${activeProject.project_id}/vendor-payables`
      : null,
    fetcher,
  );

  const { data: cashSummary } = useSWR<{
    categories: {
      category_id: string;
      category_name: string;
      cash_in_hand: number;
      allocation_remaining: number;
      allocation_total: number;
      threshold: number;
      days_since_last_pc_close: number | null;
      is_negative: boolean;
      is_below_threshold: boolean;
    }[];
    summary: {
      total_cash_in_hand: number;
      days_since_last_pc_close: number;
    };
  }>(
    activeProject
      ? `/api/v2/projects/${activeProject.project_id}/cash-summary`
      : null,
    fetcher,
  );

  const { data: workOrders } = useSWR<
    { _id: string; status: string; category_id: string }[]
  >(
    activeProject
      ? `/api/v2/projects/${activeProject.project_id}/work-orders`
      : null,
    fetcher,
  );

  if (!activeProject) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-200px)]">
        <div className="text-center p-12 rounded-[40px] bg-slate-900/40 border border-white/5 backdrop-blur-2xl">
          <div
            className="w-20 h-20 rounded-[28px] mx-auto mb-6 flex items-center justify-center shadow-2xl"
            style={{
              background:
                "linear-gradient(135deg, rgba(249,115,22,0.2) 0%, rgba(249,115,22,0.1) 100%)",
              border: "1px solid rgba(249,115,22,0.3)",
            }}
          >
            <AlertTriangle size={32} className="text-orange-500" />
          </div>
          <h3 className="text-white font-black text-2xl mb-3 tracking-tight">
            No Project Selected
          </h3>
          <p className="text-slate-400 text-sm font-medium max-w-[240px] mx-auto leading-relaxed">
            Please select a target project from the sidebar to initialize your
            dashboard.
          </p>
        </div>
      </div>
    );
  }

  if (isLoading && !financials) {
    return (
      <div className="p-6 space-y-10 animate-pulse">
        <div className="flex justify-between items-center">
          <div className="space-y-4">
            <div className="h-10 w-64 bg-slate-800 rounded-2xl" />
            <div className="h-4 w-48 bg-slate-800/50 rounded-lg" />
          </div>
          <div className="h-12 w-40 bg-slate-800 rounded-xl" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="h-32 bg-slate-800/40 rounded-[2.5rem] border border-white/5" />
          ))}
        </div>
        <div className="h-[400px] bg-slate-800/20 rounded-[3rem] border border-white/5" />
      </div>
    );
  }

  if (financialsError) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-200px)]">
        <NetworkErrorRetry
          message="System Intelligence Offline. Reconnecting..."
          onRetry={() => retryFinancials()}
        />
      </div>
    );
  }

  // Aggregate from financials
  const totalBudget =
    financials?.reduce((sum, f) => sum + (f.original_budget || 0), 0) ?? 0;
  const totalCommitted =
    financials?.reduce((sum, f) => sum + (f.committed_value || 0), 0) ?? 0;
  const totalCertified =
    financials?.reduce((sum, f) => sum + (f.certified_value || 0), 0) ?? 0;
  const totalRemaining =
    financials?.reduce(
      (sum, f) => sum + (f.balance_budget_remaining || 0),
      0,
    ) ?? 0;
  const overCommitCount =
    financials?.filter((f) => f.over_commit_flag).length ?? 0;

  // Vendor payables total
  const totalVendorPayables =
    vendorPayables?.reduce((sum, v) => sum + (v.total_payable || 0), 0) ?? 0;

  // Cash summary data
  const pettyCashData = cashSummary?.categories?.find((c) =>
    c.category_name?.toLowerCase().includes("petty"),
  );
  const ovhCashData = cashSummary?.categories?.find(
    (c) =>
      c.category_name?.toLowerCase().includes("ovh") ||
      c.category_name?.toLowerCase().includes("overhead"),
  );

  // WO status distribution for chart
  const woStatusCounts =
    workOrders?.reduce(
      (acc, wo) => {
        const status = wo.status || "Unknown";
        acc[status] = (acc[status] || 0) + 1;
        return acc;
      },
      {} as Record<string, number>,
    ) ?? {};

  const woStatusData = Object.entries(woStatusCounts).map(([name, value]) => ({
    name,
    value,
  }));

  // Over-budget alerts list (5.4.7)
  const overBudgetCategories =
    financials?.filter((f) => f.over_commit_flag) ?? [];

  // Quick Links Configuration
  const quickLinks = [
    {
      href: "/admin/projects/" + (activeProject.project_id || ""),
      icon: TrendingUp,
      label: "Project Overview",
      color: "#3b82f6",
    },
    {
      href: "/admin/work-orders",
      icon: FileText,
      label: "Work Orders",
      color: "#8b5cf6",
    },
    {
      href: "/admin/payment-certificates",
      icon: CreditCard,
      label: "Certificates",
      color: "#10b981",
    },
    {
      href: "/admin/petty-cash",
      icon: Wallet,
      label: "Petty Cash",
      color: "#f59e0b",
    },
    {
      href: "/admin/users",
      icon: Users,
      label: "Team",
      color: "#ec4899",
    },
    {
      href: "/admin/reports",
      icon: BarChartIcon,
      label: "Analysis",
      color: "#6366f1",
    },
  ];

  return (
    <div className="max-w-[1600px] mx-auto space-y-12 pb-20 animate-in fade-in duration-700">
      {/* KPI Section */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <KPICard
          label="Total Approved Budget"
          value={formatCurrency(totalBudget)}
          icon={<TrendingUp size={22} />}
          status="neutral"
          trend="+5.2%"
          trendUp={true}
          subtitle="Lifetime projected expenditure"
        />
        <KPICard
          label="Total Committed"
          value={formatCurrency(totalCommitted)}
          icon={<FileText size={22} />}
          status="positive"
          trend="82%"
          trendUp={true}
          subtitle={`${financials?.length || 0} active categories`}
        />
        <KPICard
          label="Total Certified"
          value={formatCurrency(totalCertified)}
          icon={<CheckCircle2 size={22} />}
          status="positive"
          trend={`${((totalCertified / totalCommitted) * 100 || 0).toFixed(1)}%`}
          trendUp={true}
          subtitle="Work complete (billed)"
        />
        <KPICard
          label="Unallocated Balance"
          value={formatCurrency(totalRemaining)}
          icon={<Wallet size={22} />}
          status={totalRemaining < 0 ? "negative" : "warning"}
          trend={
            overCommitCount > 0 ? `${overCommitCount} Overruns` : "Healthy"
          }
          trendUp={totalRemaining >= 0}
          subtitle="Remaining budget headroom"
        />
      </div>

      {/* Additional KPIs - Vendor Payables, Petty Cash, OVH (5.4.3, 5.4.4, 5.4.5) */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <KPICard
          label="Vendor Payables"
          value={formatCurrency(totalVendorPayables)}
          icon={<Users size={22} />}
          status={totalVendorPayables > 0 ? "negative" : "positive"}
          trend={totalVendorPayables > 0 ? "Outstanding" : "Clear"}
          trendUp={totalVendorPayables === 0}
          subtitle="Total outstanding payments"
        />
        <KPICard
          label="Petty Cash"
          value={formatCurrency(pettyCashData?.cash_in_hand ?? 0)}
          icon={<Wallet size={22} />}
          status={
            pettyCashData?.is_negative
              ? "negative"
              : pettyCashData?.is_below_threshold
                ? "warning"
                : "positive"
          }
          trend={
            pettyCashData?.is_below_threshold ? "Below Threshold" : "Healthy"
          }
          trendUp={
            !pettyCashData?.is_negative && !pettyCashData?.is_below_threshold
          }
          subtitle="Cash in hand"
        />
        <KPICard
          label="OVH Cash"
          value={formatCurrency(ovhCashData?.cash_in_hand ?? 0)}
          icon={<Wallet size={22} />}
          status={
            ovhCashData?.is_negative
              ? "negative"
              : ovhCashData?.is_below_threshold
                ? "warning"
                : "positive"
          }
          trend={
            ovhCashData?.is_below_threshold ? "Below Threshold" : "Healthy"
          }
          trendUp={
            !ovhCashData?.is_negative && !ovhCashData?.is_below_threshold
          }
          subtitle="Cash in hand"
        />
      </div>

      {/* Main Analysis Section */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
        {/* Left: Utilization Matrix */}
        <div className="xl:col-span-2 space-y-8">
          <div className="glass-panel-luxury p-10 rounded-[40px] border border-white/5 shadow-2xl relative overflow-hidden group">
            <div className="flex items-center justify-between mb-10">
              <div>
                <h3 className="text-white font-black tracking-tight uppercase text-xs">
                  Budget Utilization Ledger
                </h3>
                <p className="text-slate-500 text-[10px] font-bold uppercase tracking-widest mt-0.5">
                  Detailed category performance metrics
                </p>
              </div>
              <Link
                href={`/admin/projects/${activeProject.project_id || ""}`}
                className="bg-white/5 hover:bg-white/10 text-white px-6 py-3 rounded-2xl text-[10px] font-black uppercase tracking-[0.2em] transition-all flex items-center gap-3 active:scale-95 border border-white/5"
              >
                Full Analysis <ArrowUpRight size={14} />
              </Link>
            </div>

            <div className="space-y-10">
              {financials?.slice(0, 5).map((f) => {
                const pct =
                  f.original_budget > 0
                    ? Math.min(
                      100,
                      (f.committed_value / f.original_budget) * 100,
                    )
                    : 0;
                const isOver = f.over_commit_flag;
                return (
                  <div key={f.category_id} className="space-y-4 group/item">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        <div
                          className={`w-3 h-3 rounded-full shadow-lg transition-transform group-hover/item:scale-125 ${isOver ? "bg-rose-500 shadow-rose-500/40 animate-pulse" : "bg-slate-700"}`}
                        />
                        <span className="text-white font-black text-sm tracking-tight">
                          {f.category_id}
                        </span>
                        <span className="hidden sm:inline-block text-[10px] text-white/20 font-black uppercase tracking-widest opacity-0 group-hover/item:opacity-100 transition-opacity">
                          PMC-00{financials.indexOf(f) + 1}
                        </span>
                      </div>
                      <div className="flex items-center gap-6 text-xs font-mono">
                        <div className="text-right">
                          <span className="text-white font-black">
                            {formatCurrency(f.committed_value)}
                          </span>
                          <span className="text-white/20 mx-2 text-[10px]">
                            /
                          </span>
                          <span className="text-slate-500 font-bold">
                            {formatCurrency(f.original_budget)}
                          </span>
                        </div>
                        <div
                          className={`min-w-[70px] text-center px-3 py-1.5 rounded-xl text-[10px] font-black uppercase tracking-tighter ${isOver ? "bg-rose-500 text-white shadow-lg shadow-rose-500/20" : "bg-white/5 text-white/60 border border-white/5"}`}
                        >
                          {pct.toFixed(1)}%
                        </div>
                      </div>
                    </div>
                    <div className="h-3 bg-black/40 rounded-full overflow-hidden p-[2px] border border-white/5 shadow-inner">
                      <div
                        className="h-full rounded-full transition-all duration-1000 ease-out"
                        style={{
                          width: `${pct}%`,
                          background: isOver
                            ? "linear-gradient(90deg, #f43f5e 0%, #e11d48 100%)"
                            : pct > 80
                              ? "linear-gradient(90deg, #f59e0b 0%, #d97706 100%)"
                              : "linear-gradient(90deg, #3b82f6 0%, #2563eb 100%)",
                          boxShadow: isOver
                            ? "0 0 15px rgba(244,63,94,0.5)"
                            : "none",
                        }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Right: Allocation Overview */}
        <div className="space-y-8">
          <div className="glass-panel-luxury p-10 rounded-[40px] border border-white/5 h-full flex flex-col">
            <div>
              <h3 className="text-white font-black tracking-tight uppercase text-xs">
                Allocation Structure
              </h3>
              <p className="text-slate-500 text-[10px] font-bold uppercase tracking-widest mt-0.5">
                Top Category Distribution
              </p>
            </div>

            <div className="flex-1 flex items-center justify-center py-10">
              <DonutChart
                data={
                  financials?.slice(0, 5).map((f) => ({
                    name: f.category_id,
                    value: f.original_budget,
                  })) || []
                }
                category="value"
                index="name"
                colors={["blue", "violet", "emerald", "amber", "rose"]}
                className="h-64"
                showAnimation={true}
              />
            </div>

            <div className="space-y-4 pt-6 border-t border-white/5 uppercase">
              <div className="flex justify-between items-center text-[10px] font-bold">
                <span className="text-slate-500">Project Status</span>
                <span className="text-emerald-400 bg-emerald-400/10 px-2 py-0.5 rounded-lg border border-emerald-400/20">
                  Operational
                </span>
              </div>
              <div className="flex justify-between items-center text-[10px] font-bold">
                <span className="text-slate-500">Critical Alerts</span>
                <span
                  className={
                    overCommitCount > 0 ? "text-rose-400" : "text-slate-400"
                  }
                >
                  {overCommitCount} Issues Detected
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Budget vs Committed Bar Chart (5.4.8) */}
      <div className="glass-panel-luxury p-10 rounded-[40px] border border-white/5">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h3 className="text-white font-black tracking-tight uppercase text-xs">
              Budget vs Committed
            </h3>
            <p className="text-slate-500 text-[10px] font-bold uppercase tracking-widest mt-0.5">
              Original budget vs committed amounts per category
            </p>
          </div>
        </div>
        <div className="h-80">
          <BarChart
            className="h-full"
            data={
              financials?.slice(0, 8).map((f) => ({
                name: f.category_id,
                Budget: f.original_budget,
                Committed: f.committed_value,
              })) || []
            }
            index="name"
            categories={["Budget", "Committed"]}
            colors={["blue", "emerald"]}
            yAxisWidth={60}
            showAnimation={true}
          />
        </div>
      </div>

      {/* 15-Day Countdown Widgets (5.4.6) */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Petty Cash Countdown */}
        <div
          className="glass-panel-luxury p-8 rounded-[40px] border border-white/5 flex items-center justify-between"
          style={{
            borderColor:
              (pettyCashData?.days_since_last_pc_close ?? 0) >= 15
                ? "rgba(239,68,68,0.3)"
                : (pettyCashData?.days_since_last_pc_close ?? 0) >= 11
                  ? "rgba(245,158,11,0.3)"
                  : "rgba(255,255,255,0.05)",
          }}
        >
          <div className="flex items-center gap-6">
            <div
              className="w-16 h-16 rounded-[24px] flex items-center justify-center"
              style={{
                background:
                  (pettyCashData?.days_since_last_pc_close ?? 0) >= 15
                    ? "rgba(239,68,68,0.1)"
                    : (pettyCashData?.days_since_last_pc_close ?? 0) >= 11
                      ? "rgba(245,158,11,0.1)"
                      : "rgba(34,197,94,0.1)",
              }}
            >
              <Clock
                size={32}
                style={{
                  color:
                    (pettyCashData?.days_since_last_pc_close ?? 0) >= 15
                      ? "#ef4444"
                      : (pettyCashData?.days_since_last_pc_close ?? 0) >= 11
                        ? "#f59e0b"
                        : "#22c55e",
                }}
              />
            </div>
            <div>
              <p className="text-slate-500 text-[10px] font-bold uppercase tracking-widest">
                Petty Cash
              </p>
              <p className="text-white text-3xl font-black tracking-tight">
                {pettyCashData?.days_since_last_pc_close != null
                  ? `${pettyCashData.days_since_last_pc_close}`
                  : "None"}{" "}
                <span className="text-lg font-medium text-slate-500">days</span>
              </p>
              <p className="text-slate-600 text-[10px] font-medium uppercase tracking-wider">
                since last PC close
              </p>
            </div>
          </div>
          <div
            className={`px-4 py-2 rounded-xl text-[10px] font-black uppercase tracking-wider ${(pettyCashData?.days_since_last_pc_close ?? 0) >= 15
              ? "bg-rose-500 text-white"
              : (pettyCashData?.days_since_last_pc_close ?? 0) >= 11
                ? "bg-amber-500 text-white"
                : "bg-emerald-500/10 text-emerald-500 border border-emerald-500/20"
              }`}
          >
            {(pettyCashData?.days_since_last_pc_close ?? 0) >= 15
              ? "Overdue"
              : (pettyCashData?.days_since_last_pc_close ?? 0) >= 11
                ? "Warning"
                : "OK"}
          </div>
        </div>

        {/* OVH Cash Countdown */}
        <div
          className="glass-panel-luxury p-8 rounded-[40px] border border-white/5 flex items-center justify-between"
          style={{
            borderColor:
              (ovhCashData?.days_since_last_pc_close ?? 0) >= 15
                ? "rgba(239,68,68,0.3)"
                : (ovhCashData?.days_since_last_pc_close ?? 0) >= 11
                  ? "rgba(245,158,11,0.3)"
                  : "rgba(255,255,255,0.05)",
          }}
        >
          <div className="flex items-center gap-6">
            <div
              className="w-16 h-16 rounded-[24px] flex items-center justify-center"
              style={{
                background:
                  (ovhCashData?.days_since_last_pc_close ?? 0) >= 15
                    ? "rgba(239,68,68,0.1)"
                    : (ovhCashData?.days_since_last_pc_close ?? 0) >= 11
                      ? "rgba(245,158,11,0.1)"
                      : "rgba(34,197,94,0.1)",
              }}
            >
              <Clock
                size={32}
                style={{
                  color:
                    (ovhCashData?.days_since_last_pc_close ?? 0) >= 15
                      ? "#ef4444"
                      : (ovhCashData?.days_since_last_pc_close ?? 0) >= 11
                        ? "#f59e0b"
                        : "#22c55e",
                }}
              />
            </div>
            <div>
              <p className="text-slate-500 text-[10px] font-bold uppercase tracking-widest">
                OVH Cash
              </p>
              <p className="text-white text-3xl font-black tracking-tight">
                {ovhCashData?.days_since_last_pc_close != null
                  ? `${ovhCashData.days_since_last_pc_close}`
                  : "None"}{" "}
                <span className="text-lg font-medium text-slate-500">days</span>
              </p>
              <p className="text-slate-600 text-[10px] font-medium uppercase tracking-wider">
                since last PC close
              </p>
            </div>
          </div>
          <div
            className={`px-4 py-2 rounded-xl text-[10px] font-black uppercase tracking-wider ${(ovhCashData?.days_since_last_pc_close ?? 0) >= 15
              ? "bg-rose-500 text-white"
              : (ovhCashData?.days_since_last_pc_close ?? 0) >= 11
                ? "bg-amber-500 text-white"
                : "bg-emerald-500/10 text-emerald-500 border border-emerald-500/20"
              }`}
          >
            {(ovhCashData?.days_since_last_pc_close ?? 0) >= 15
              ? "Overdue"
              : (ovhCashData?.days_since_last_pc_close ?? 0) >= 11
                ? "Warning"
                : "OK"}
          </div>
        </div>
      </div>

      {/* WO Status Distribution Chart (5.4.9) */}
      {workOrders && workOrders.length > 0 && (
        <div className="glass-panel-luxury p-10 rounded-[40px] border border-white/5">
          <div className="flex items-center justify-between mb-8">
            <div>
              <h3 className="text-white font-black tracking-tight uppercase text-xs">
                WO Status Distribution
              </h3>
              <p className="text-slate-500 text-[10px] font-bold uppercase tracking-widest mt-0.5">
                Work order pipeline breakdown
              </p>
            </div>
          </div>
          <div className="h-64 flex items-center justify-center">
            <DonutChart
              data={woStatusData}
              category="value"
              index="name"
              colors={["emerald", "amber", "blue", "slate", "rose", "purple"]}
              className="h-full"
              showAnimation={true}
            />
          </div>
        </div>
      )}

      {/* Over-Budget Alerts List (5.4.7) */}
      {overBudgetCategories.length > 0 && (
        <div className="glass-panel-luxury p-10 rounded-[40px] border border-rose-500/20">
          <div className="flex items-center gap-4 mb-8">
            <div className="p-3 rounded-xl bg-rose-500/10">
              <AlertTriangle size={24} className="text-rose-500" />
            </div>
            <div>
              <h3 className="text-white font-black tracking-tight uppercase text-xs">
                Over-Budget Alerts
              </h3>
              <p className="text-slate-500 text-[10px] font-bold uppercase tracking-widest mt-0.5">
                Categories exceeding original budget
              </p>
            </div>
          </div>
          <div className="space-y-4">
            {overBudgetCategories.map((f) => {
              const overAmount =
                (f.committed_value || 0) - (f.original_budget || 0);
              return (
                <div
                  key={f.category_id}
                  className="flex items-center justify-between p-4 rounded-2xl bg-rose-500/5 border border-rose-500/10"
                >
                  <div className="flex items-center gap-4">
                    <div className="w-2 h-2 rounded-full bg-rose-500 shadow-lg shadow-rose-500/50" />
                    <div>
                      <p className="text-white font-bold">{f.category_id}</p>
                      <p className="text-slate-500 text-xs">
                        Committed: {formatCurrency(f.committed_value)} / Budget:{" "}
                        {formatCurrency(f.original_budget)}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-rose-500 font-black text-lg">
                      +{formatCurrency(overAmount)}
                    </p>
                    <p className="text-slate-500 text-[10px] font-bold uppercase tracking-wider">
                      Over Budget
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Strategic Hub */}
      <div>
        <div className="flex items-center justify-between mb-8">
          <h3 className="text-white/40 text-[10px] font-black uppercase tracking-[0.4em]">
            Strategic Resource Hub
          </h3>
          <div className="h-px flex-1 bg-white/5 ml-8" />
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-6">
          {quickLinks.map(({ href, icon: Icon, label, color }) => (
            <Link
              key={href}
              href={href}
              className="group relative flex flex-col items-center gap-5 p-8 rounded-[36px] transition-all bg-slate-900/40 border border-white/5 hover:border-white/20 hover:bg-slate-900/60 hover:-translate-y-2 shadow-xl hover:shadow-2xl overflow-hidden"
            >
              <div
                className="absolute inset-x-0 bottom-0 h-1 transition-all duration-500 opacity-0 group-hover:opacity-100"
                style={{
                  background: color,
                  boxShadow: `0 -10px 20px -5px ${color}`,
                }}
              />
              <div
                className="w-16 h-16 rounded-[24px] flex items-center justify-center transition-all duration-500 group-hover:scale-110 shadow-inner group-hover:rotate-[5deg]"
                style={{
                  background: `linear-gradient(135deg, ${color}20 0%, ${color}10 100%)`,
                  border: `1px solid ${color}30`,
                }}
              >
                <Icon size={28} style={{ color }} />
              </div>
              <span className="text-slate-500 text-[10px] font-black uppercase tracking-[0.2em] text-center group-hover:text-white group-hover:tracking-[0.3em] transition-all duration-500">
                {label}
              </span>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
