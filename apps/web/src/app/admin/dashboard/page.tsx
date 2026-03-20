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
import { DerivedFinancialState } from "@/types/api";
import { formatCurrency } from "@tac-pmc/ui";
import { useProjectStore } from "@/store/projectStore";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import NetworkErrorRetry from "@/components/ui/NetworkErrorRetry";

export default function AdminDashboard() {
  const { activeProject } = useProjectStore();

  const { data: financials, error: financialsError, isLoading, mutate: retryFinancials } = useSWR<DerivedFinancialState[]>(
    activeProject
      ? `/api/v2/projects/${activeProject.project_id}/financials`
      : null,
    fetcher,
  );

  if (!activeProject) {
    return (
      <div className="flex flex-col items-center justify-center h-[calc(100vh-200px)] border border-zinc-200 dark:border-zinc-800 rounded-xl bg-zinc-50/50 dark:bg-zinc-900/50">
        <LayoutGrid size={40} className="text-zinc-300 dark:text-zinc-700 mb-4" />
        <h3 className="text-zinc-500 dark:text-zinc-400 font-medium text-sm">No Project Context</h3>
        <p className="text-zinc-400 dark:text-zinc-500 text-xs mt-1">Select a project via the sidebar to view financials.</p>
      </div>
    );
  }

  if (isLoading && !financials) {
    return (
      <div className="space-y-8 animate-pulse">
        <div className="grid grid-cols-4 gap-0 border border-zinc-200 dark:border-zinc-800 divide-x divide-zinc-200 dark:divide-zinc-800">
          {[1, 2, 3, 4].map(i => <div key={i} className="h-24 bg-zinc-50/50 dark:bg-zinc-900/50" />)}
        </div>
        <div className="h-[400px] border border-zinc-200 dark:border-zinc-800 bg-zinc-50/20 dark:bg-zinc-900/20" />
      </div>
    );
  }

  if (financialsError) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-200px)]">
        <NetworkErrorRetry
          message="Intelligence Feed Interrupted"
          onRetry={() => retryFinancials()}
        />
      </div>
    );
  }

  // Aggregate metrics
  const totalBudget = financials?.reduce((sum, f) => sum + (f.original_budget || 0), 0) ?? 0;
  const totalCommitted = financials?.reduce((sum, f) => sum + (f.committed_value || 0), 0) ?? 0;
  const totalCertified = financials?.reduce((sum, f) => sum + (f.certified_value || 0), 0) ?? 0;
  const totalRemaining = financials?.reduce((sum, f) => sum + (f.balance_budget_remaining || 0), 0) ?? 0;

  return (
    <div className="space-y-8 pb-12">
      {/* minimalist KPI Sparks */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 border border-zinc-200 dark:border-zinc-800 divide-y md:divide-y-0 md:divide-x divide-zinc-200 dark:divide-zinc-800 bg-white dark:bg-zinc-950 overflow-hidden">
        <div className="kpi-spark">
          <span className="text-[10px] font-bold uppercase tracking-wider text-zinc-500">Total Budget</span>
          <span className="text-xl font-black text-zinc-900 dark:text-zinc-50">{formatCurrency(totalBudget)}</span>
          <div className="flex items-center gap-1.5 mt-1">
            <span className="pill-status bg-zinc-100 dark:bg-zinc-900 border-zinc-200 dark:border-zinc-800 text-zinc-600 dark:text-zinc-400">Baseline</span>
          </div>
        </div>
        <div className="kpi-spark">
          <span className="text-[10px] font-bold uppercase tracking-wider text-zinc-500">Committed Value</span>
          <span className="text-xl font-black text-zinc-900 dark:text-zinc-50">{formatCurrency(totalCommitted)}</span>
          <div className="flex items-center gap-1.5 mt-1">
            <div className="h-1 flex-1 bg-zinc-100 dark:bg-zinc-900 rounded-full overflow-hidden">
              <div className="h-full bg-indigo-500" style={{ width: `${(totalCommitted / totalBudget) * 100}%` }} />
            </div>
            <span className="text-[10px] font-mono text-zinc-400">{((totalCommitted / totalBudget) * 100).toFixed(0)}%</span>
          </div>
        </div>
        <div className="kpi-spark">
          <span className="text-[10px] font-bold uppercase tracking-wider text-zinc-500">Certified (Billed)</span>
          <span className="text-xl font-black text-zinc-900 dark:text-zinc-50">{formatCurrency(totalCertified)}</span>
          <div className="flex items-center gap-1.5 mt-1">
            <TrendingUp size={12} className="text-emerald-500" />
            <span className="text-[10px] font-bold text-emerald-600 dark:text-emerald-400 uppercase">On Track</span>
          </div>
        </div>
        <div className="kpi-spark">
          <span className="text-[10px] font-bold uppercase tracking-wider text-zinc-500">Allocated Balance</span>
          <span className={`text-xl font-black ${totalRemaining < 0 ? 'text-rose-600' : 'text-zinc-900 dark:text-zinc-50'}`}>
            {formatCurrency(totalRemaining)}
          </span>
          <div className="flex items-center gap-1.5 mt-1">
            {totalRemaining < 0 ? (
              <span className="pill-status bg-rose-500/10 border-rose-500/20 text-rose-600">Over-Budget</span>
            ) : (
              <span className="pill-status bg-emerald-500/10 border-emerald-500/20 text-emerald-600">Healthy</span>
            )}
          </div>
        </div>
      </div>

      {/* Unified Enterprise Data Ledger */}
      <div className="border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 overflow-hidden">
        <div className="px-6 py-4 border-b border-zinc-200 dark:border-zinc-800 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-5 h-5 rounded bg-zinc-900 dark:bg-zinc-50 flex items-center justify-center">
              <FileText size={12} className="text-white dark:text-zinc-900" />
            </div>
            <h3 className="text-[13px] font-bold uppercase tracking-tight text-zinc-900 dark:text-zinc-100">
              Budget Utilization Ledger
            </h3>
          </div>
          <Link
            href={`/admin/projects/${activeProject.project_id || activeProject._id}`}
            className="text-[11px] font-bold uppercase tracking-wider text-indigo-600 hover:text-indigo-700 flex items-center gap-1.5 transition-colors"
          >
            See Detailed Analysis <ExternalLink size={12} />
          </Link>
        </div>

        <Table>
          <TableHeader className="bg-zinc-50/50 dark:bg-zinc-900/50">
            <TableRow>
              <TableHead className="w-[30%]">Category</TableHead>
              <TableHead>Original Budget</TableHead>
              <TableHead>Committed</TableHead>
              <TableHead>Utilization</TableHead>
              <TableHead className="text-right">Balance</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {financials?.map((f) => {
              const utilPct = f.original_budget > 0 ? (f.committed_value / f.original_budget) * 100 : 0;
              return (
                <TableRow key={f.category_id} className="group hover:bg-zinc-50/50 dark:hover:bg-zinc-900/50 border-zinc-200/50 dark:border-zinc-800/50">
                  <TableCell className="font-medium text-zinc-900 dark:text-zinc-100">
                    <div className="flex items-center gap-2">
                      <div className={`w-1.5 h-1.5 rounded-full ${f.over_commit_flag ? 'bg-rose-500 animate-pulse' : 'bg-zinc-300 dark:bg-zinc-700'}`} />
                      {f.category_id}
                    </div>
                  </TableCell>
                  <TableCell className="font-mono text-zinc-500">{formatCurrency(f.original_budget)}</TableCell>
                  <TableCell className="font-mono font-semibold text-zinc-900 dark:text-zinc-200">
                    {formatCurrency(f.committed_value)}
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-3 min-w-[120px]">
                      <div className="h-1.5 flex-1 bg-zinc-100 dark:bg-zinc-900 rounded-full overflow-hidden border border-zinc-200 dark:border-zinc-800">
                        <div
                          className={`h-full transition-all duration-700 ${f.over_commit_flag ? 'bg-rose-500' : 'bg-zinc-900 dark:bg-zinc-100'}`}
                          style={{ width: `${Math.min(100, utilPct)}%` }}
                        />
                      </div>
                      <span className={`text-[10px] font-bold font-mono ${f.over_commit_flag ? 'text-rose-600' : 'text-zinc-500'}`}>
                        {utilPct.toFixed(1)}%
                      </span>
                    </div>
                  </TableCell>
                  <TableCell className="text-right font-mono font-bold">
                    <span className={f.balance_budget_remaining < 0 ? 'text-rose-600' : 'text-zinc-900 dark:text-zinc-100'}>
                      {formatCurrency(f.balance_budget_remaining)}
                    </span>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>

      {/* Strategic Shortcuts */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "Internal Reports", href: "/admin/reports", icon: TrendingUp },
          { label: "Site Operations", href: "/admin/site-operations", icon: CheckCircle2 },
          { label: "Financial Settings", href: "/admin/settings", icon: Wallet },
          { label: "Payment Certificates", href: "/admin/payment-certificates", icon: FileText },
        ].map((item) => (
          <Link
            key={item.label}
            href={item.href}
            className="flex items-center gap-3 p-4 border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 hover:bg-zinc-50 dark:hover:bg-zinc-900 transition-all group"
          >
            <div className="w-8 h-8 rounded bg-zinc-100 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 flex items-center justify-center text-zinc-500 group-hover:text-indigo-600 transition-colors">
              <item.icon size={16} />
            </div>
            <span className="text-[11px] font-bold uppercase tracking-wider text-zinc-900 dark:text-zinc-100">
              {item.label}
            </span>
          </Link>
        ))}
      </div>
    </div>
  );
}
