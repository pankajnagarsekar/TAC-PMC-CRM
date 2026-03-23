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
} from "lucide-react";
import { fetcher } from "@/lib/api";
import { DerivedFinancialState, VendorPayable, CashSummaryResponse, WorkOrder } from "@/types/api";
import { useProjectStore } from "@/store/projectStore";
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

export default function AdminDashboard() {
  const { activeProject } = useProjectStore();

  const { data: financials, error: financialsError, isLoading, mutate: retryFinancials } = useSWR<DerivedFinancialState[]>(
    activeProject
      ? `/api/v2/projects/${activeProject.project_id}/financials`
      : null,
    fetcher,
  );

  const { data: vendorPayables } = useSWR<VendorPayable[]>(
    activeProject ? `/api/projects/${activeProject.project_id}/vendor-payables` : null,
    fetcher
  );

  const { data: cashSummary } = useSWR<CashSummaryResponse>(
    activeProject ? `/api/projects/${activeProject.project_id}/cash-summary` : null,
    fetcher
  );

  const { data: woResponse } = useSWR<{items: WorkOrder[]; next_cursor: string | null}>(
    activeProject ? `/api/work-orders?project_id=${activeProject.project_id}&limit=500` : null,
    fetcher
  );

  const chartData = React.useMemo(() => {
    if (!financials) return [];
    return financials.slice(0, 8).map(f => ({
      name: f.category_id.substring(0, 10),
      budget: normalizeFinancial(f.original_budget),
      committed: normalizeFinancial(f.committed_value)
    }));
  }, [financials]);

  if (!activeProject) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="empty-state-luxury max-w-sm text-center">
          <div className="empty-state-luxury-icon mb-4">
            <LayoutGrid size={32} />
          </div>
          <h3 className="empty-state-luxury-title">No Project Selected</h3>
          <p className="empty-state-luxury-desc">Select an active operational project from the sidebar to initialize financial intelligence.</p>
        </div>
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

  // Aggregate metrics
  const totalBudget = financials?.reduce((sum, f) => sum + (normalizeFinancial(f.original_budget)), 0) ?? 0;
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
  const woOpen = workOrders.filter(w => ['Pending','Draft'].includes(w.status)).length;
  const woClosed = workOrders.filter(w => ['Closed','Completed'].includes(w.status)).length;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 pb-20">
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
                <p className="text-xl font-bold">4</p>
              </div>
              <div>
                <p className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-0.5">Active</p>
                <p className="text-xl font-bold text-primary">2</p>
              </div>
            </div>

            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <AlertTriangle size={14} className="text-rose-500" />
                <span className="text-[10px] font-bold text-rose-500 uppercase tracking-tight">Overdue Milestones</span>
              </div>
              <span className="text-sm font-black text-rose-500">1</span>
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
                <TrendingDown size={12} className="text-rose-500" />
                <span className="text-xs font-black">-4.2%</span>
              </div>
            </div>
            <div>
              <p className="text-[9px] font-bold text-zinc-500 uppercase tracking-widest mb-0.5">Critical Path</p>
              <span className="text-xs font-black text-indigo-500">DELAYED</span>
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
            <span className="px-2 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 text-[8px] font-black uppercase text-zinc-500">12 Pending</span>
          </div>

          <div className="space-y-2">
            {[
              { id: 'RFI #104', label: 'Review Structural Changes', priority: 'High', color: 'text-rose-500' },
              { id: 'PAY #02', label: 'Approve Payment App', priority: 'Financial', color: 'text-primary' },
              { id: 'SITE', label: 'Weekly Safety Walkthrough', priority: 'Routine', color: 'text-zinc-500' }
            ].map(task => (
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
              <p className="text-4xl font-black leading-none tracking-tighter">28</p>
              <p className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest mt-2">Open Tasks</p>
            </div>
            <div className="pb-1">
              <p className="text-2xl font-black text-zinc-400 tracking-tighter underline decoration-primary/20 decoration-2 underline-offset-4">142</p>
              <p className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest mt-1">Resolved</p>
            </div>
          </div>

          <div className="space-y-4">
            <div className="flex items-center justify-between text-[10px] font-bold uppercase tracking-widest">
              <span className="text-zinc-500">Compliance Rate</span>
              <span className="text-emerald-500">94.2%</span>
            </div>
            <div className="h-2 w-full bg-muted/20 rounded-full overflow-hidden border border-muted/30">
              <div className="h-full bg-emerald-500 w-[94%] shadow-[0_0_10px_rgba(16,185,129,0.2)]" />
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
            {[
              { label: 'Foundations & Piling', progress: 100 },
              { label: 'Structural Steel', progress: 65 },
              { label: 'MEP Rough-in', progress: 5 }
            ].map(item => (
              <div key={item.label} className="space-y-2">
                <div className="flex justify-between items-center text-[10px] font-bold uppercase tracking-wider">
                  <span className="text-zinc-500">{item.label}</span>
                  <span className="text-primary">{item.progress}%</span>
                </div>
                <div className="h-2 w-full bg-muted/20 rounded-full overflow-hidden border border-muted/30">
                  <div className="h-full bg-primary transition-all duration-1000" style={{ width: `${item.progress}%` }} />
                </div>
              </div>
            ))}
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
            {[
              { label: 'Structural Works', budget: 100, actual: 82 },
              { label: 'Electrical & HV', budget: 100, actual: 14 },
              { label: 'Plumbing & HVAC', budget: 100, actual: 6 }
            ].map(item => (
              <div key={item.label} className="space-y-2">
                <div className="flex justify-between items-center text-[10px] font-bold uppercase tracking-wider">
                  <span className="text-zinc-500">{item.label}</span>
                  <span className="text-zinc-400 italic">{(item.actual)}% Spent</span>
                </div>
                <div className="h-2 w-full bg-muted/20 rounded-full overflow-hidden border border-muted/30 flex">
                  <div className="h-full bg-primary" style={{ width: `${item.actual}%` }} />
                  <div className="h-full bg-muted/40" style={{ width: `${item.budget - item.actual}%` }} />
                </div>
              </div>
            ))}
          </div>
        </GlassCard>
      </div>
    </div>
  );
}
