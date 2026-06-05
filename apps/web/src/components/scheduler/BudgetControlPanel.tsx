"use client";

import React, { useMemo } from "react";
import useSWR from "swr";
import { useRouter } from "next/navigation";
import { 
  Landmark, 
  Coins, 
  FileText, 
  CreditCard, 
  ArrowRight, 
  TrendingUp, 
  DollarSign, 
  AlertTriangle,
  Wallet,
  CheckSquare
} from "lucide-react";
import { useProjectStore } from "@/store/projectStore";
import { fetcher } from "@/lib/api";
import { ScheduleTask } from "@/types/schedule.types";
import { formatINRShort, formatCurrencySafe } from "@/lib/formatters";
import { GlassCard } from "@/components/ui/GlassCard";
import FinancialChart from "@/components/ui/FinancialChart";

interface BudgetControlPanelProps {
  taskMap: Record<string, ScheduleTask>;
  financials?: any[];
}

export default function BudgetControlPanel({ taskMap, financials }: BudgetControlPanelProps) {
  const router = useRouter();
  const activeProject = useProjectStore((state) => state.activeProject);
  const projectId = activeProject?.project_id;

  // Fetch payment certificates using SWR
  const { data: paymentsData } = useSWR<any>(
    projectId ? `/api/v1/payments/${projectId}` : null,
    fetcher
  );

  // Process data for the table and KPI cards
  const tableData = useMemo(() => {
    // 1. Fetch total paid amount from paid PCs
    const pcs = paymentsData?.items || paymentsData || [];
    const paidPcs = Array.isArray(pcs) ? pcs.filter((pc: any) => pc.status?.toLowerCase() === 'paid') : [];
    const totalPaidAmount = paidPcs.reduce((sum: number, pc: any) => sum + Number(pc.payment_amount ?? pc.grand_total ?? 0), 0);

    // 2. If financials exist, build from them
    if (financials && financials.length > 0) {
      const totalCertified = financials.reduce((sum, f) => sum + (f.certified_value || 0), 0);
      return financials.map((f, idx) => {
        const budget = f.original_budget || 0;
        const committed = f.committed_value || 0;
        const certified = f.certified_value || 0;
        
        let paid = 0;
        if (totalCertified > 0) {
          paid = Math.round(totalPaidAmount * (certified / totalCertified));
        } else {
          const totalCommitted = financials.reduce((sum, fi) => sum + (fi.committed_value || 0), 0);
          if (totalCommitted > 0) {
            paid = Math.round(totalPaidAmount * (committed / totalCommitted));
          } else {
            paid = Math.round(totalPaidAmount / financials.length);
          }
        }
        
        const forecast = committed + Math.max(0, budget - committed);
        const variance = budget - forecast;

        return {
          category_id: f.category_id || f._id || `financial-${idx}`,
          category: f.category_name || "Misc",
          category_code: f.category_code,
          budget,
          committed,
          certified,
          paid,
          forecast,
          variance
        };
      });
    }

    // 3. Fall back to task-level rollup by WBS code
    const categoriesMap: Record<string, { category_id: string; category: string; category_code?: string; budget: number; committed: number; certified: number; paid: number; forecast: number; variance: number }> = {};
    
    Object.values(taskMap).forEach((task) => {
      const code = task.wbs_code?.split('.')[0] || 'Misc';
      const name = code === 'C' ? 'Construction' :
                   code === 'P' ? 'Contracting' :
                   code === 'D' ? 'Design/Engineering' :
                   code === 'S' ? 'Site Ops' :
                   code === 'I' ? 'Interiors' : code;

      if (!categoriesMap[name]) {
        categoriesMap[name] = { 
          category_id: name, 
          category: name, 
          category_code: code !== name ? code : undefined,
          budget: 0, 
          committed: 0, 
          certified: 0, 
          paid: 0, 
          forecast: 0, 
          variance: 0 
        };
      }
      categoriesMap[name].budget += Number(task.baseline_cost ?? 0);
      categoriesMap[name].committed += Number(task.wo_value ?? 0);
      categoriesMap[name].certified += Number(task.payment_value ?? 0);
    });

    const totalCertified = Object.values(categoriesMap).reduce((sum, c) => sum + c.certified, 0);
    const totalCommitted = Object.values(categoriesMap).reduce((sum, cat) => sum + cat.committed, 0);
    const categoriesCount = Object.keys(categoriesMap).length;

    return Object.values(categoriesMap).reduce<any[]>((acc, c) => {
      const forecast = c.committed + Math.max(0, c.budget - c.committed);
      let paid = 0;
      if (totalCertified > 0) {
        paid = Math.round(totalPaidAmount * (c.certified / totalCertified));
      } else {
        if (totalCommitted > 0) {
          paid = Math.round(totalPaidAmount * (c.committed / totalCommitted));
        } else {
          paid = Math.round(totalPaidAmount / categoriesCount);
        }
      }
      const variance = c.budget - forecast;

      if (c.budget > 0 || c.committed > 0 || c.certified > 0) {
        acc.push({
          ...c,
          paid,
          forecast,
          variance
        });
      }
      return acc;
    }, []);
  }, [taskMap, financials, paymentsData]);

  // Aggregate project-wide financial metrics
  const kpis = useMemo(() => {
    const totalBudget = tableData.reduce((sum, item) => sum + item.budget, 0);
    const totalCommitted = tableData.reduce((sum, item) => sum + item.committed, 0);
    const totalCertified = tableData.reduce((sum, item) => sum + item.certified, 0);
    const totalPaid = tableData.reduce((sum, item) => sum + item.paid, 0);
    const remainingBudget = totalBudget - totalCommitted;
    const reconciliationVariance = totalBudget - totalPaid;

    return {
      totalBudget,
      totalCommitted,
      totalCertified,
      totalPaid,
      remainingBudget,
      reconciliationVariance,
    };
  }, [tableData]);

  // Map tableData for Recharts category Planned vs Actual bar chart
  const chartData = useMemo(() => {
    return tableData.map(item => ({
      name: item.category_code ? `${item.category} (${item.category_code})` : item.category,
      budget: item.budget,
      committed: item.committed,
    }));
  }, [tableData]);

  if (!projectId) return null;

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      {/* Top Header Card */}
      <div className="flex flex-col gap-2">
        <h2 className="text-[11px] font-black uppercase tracking-[0.25em] text-orange-500/80">Financial Control & Cost Planning</h2>
        <p className="text-xs text-slate-500 dark:text-slate-400 uppercase tracking-wider font-semibold">
          Unified Project Budgeting, Commitment Auditing, and Payment Verification
        </p>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        {/* Total Budget */}
        <GlassCard className="p-4 border-slate-200 dark:border-white/5 bg-white/40 dark:bg-slate-900/40">
          <div className="flex items-center gap-3">
            <div className="size-8 rounded-lg bg-yellow-500/10 border border-yellow-500/20 flex items-center justify-center text-yellow-500">
              <Landmark size={16} />
            </div>
            <span className="text-[9px] font-black text-slate-400 uppercase tracking-wider">Approved Budget</span>
          </div>
          <p className="text-lg font-black text-slate-900 dark:text-white mt-3 truncate">
            {formatCurrencySafe(kpis.totalBudget)}
          </p>
        </GlassCard>

        {/* Committed Value */}
        <GlassCard className="p-4 border-slate-200 dark:border-white/5 bg-white/40 dark:bg-slate-900/40">
          <div className="flex items-center gap-3">
            <div className="size-8 rounded-lg bg-sky-500/10 border border-sky-500/20 flex items-center justify-center text-sky-400">
              <Coins size={16} />
            </div>
            <span className="text-[9px] font-black text-slate-400 uppercase tracking-wider">Committed (WOs)</span>
          </div>
          <p className="text-lg font-black text-slate-900 dark:text-white mt-3 truncate">
            {formatCurrencySafe(kpis.totalCommitted)}
          </p>
        </GlassCard>

        {/* Certified Value */}
        <GlassCard className="p-4 border-slate-200 dark:border-white/5 bg-white/40 dark:bg-slate-900/40">
          <div className="flex items-center gap-3">
            <div className="size-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
              <CheckSquare size={16} />
            </div>
            <span className="text-[9px] font-black text-slate-400 uppercase tracking-wider">Certified (PCs)</span>
          </div>
          <p className="text-lg font-black text-slate-900 dark:text-white mt-3 truncate">
            {formatCurrencySafe(kpis.totalCertified)}
          </p>
        </GlassCard>

        {/* Paid Cost */}
        <GlassCard className="p-4 border-slate-200 dark:border-white/5 bg-white/40 dark:bg-slate-900/40">
          <div className="flex items-center gap-3">
            <div className="size-8 rounded-lg bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400">
              <CreditCard size={16} />
            </div>
            <span className="text-[9px] font-black text-slate-400 uppercase tracking-wider">Paid Cost</span>
          </div>
          <p className="text-lg font-black text-slate-900 dark:text-white mt-3 truncate">
            {formatCurrencySafe(kpis.totalPaid)}
          </p>
        </GlassCard>

        {/* Remaining Budget */}
        <GlassCard className="p-4 border-slate-200 dark:border-white/5 bg-white/40 dark:bg-slate-900/40">
          <div className="flex items-center gap-3">
            <div className="size-8 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-500">
              <TrendingUp size={16} />
            </div>
            <span className="text-[9px] font-black text-slate-400 uppercase tracking-wider">Remaining (WOs)</span>
          </div>
          <p className={`text-lg font-black mt-3 truncate ${kpis.remainingBudget >= 0 ? "text-emerald-500" : "text-rose-500"}`}>
            {formatCurrencySafe(kpis.remainingBudget)}
          </p>
        </GlassCard>

        {/* Reconciliation Variance */}
        <GlassCard className="p-4 border-slate-200 dark:border-white/5 bg-white/40 dark:bg-slate-900/40">
          <div className="flex items-center gap-3">
            <div className="size-8 rounded-lg bg-orange-500/10 border border-orange-500/20 flex items-center justify-center text-orange-500">
              <DollarSign size={16} />
            </div>
            <span className="text-[9px] font-black text-slate-400 uppercase tracking-wider">Reconciled Var</span>
          </div>
          <p className={`text-lg font-black mt-3 truncate ${kpis.reconciliationVariance >= 0 ? "text-slate-900 dark:text-white" : "text-rose-500"}`}>
            {formatCurrencySafe(kpis.reconciliationVariance)}
          </p>
        </GlassCard>
      </div>

      {/* Main Budget Data Section */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        
        {/* Left/Center: Detailed Budget Breakdown Table */}
        <div className="xl:col-span-2 space-y-6">
          <GlassCard className="border-slate-200 dark:border-white/5 bg-white/60 dark:bg-slate-950/60 p-6 shadow-2xl backdrop-blur-xl">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xs font-black uppercase tracking-[0.2em] text-slate-900 dark:text-white/45">Allocation Breakdown</h3>
              <span className="text-[9px] font-bold text-slate-400 uppercase tracking-widest">Values in INR</span>
            </div>

            {tableData.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-slate-400">
                <AlertTriangle className="mb-2 text-slate-500" size={32} />
                <p className="text-xs font-bold uppercase tracking-widest">No Cost Allocation Found</p>
                <p className="text-[10px] text-slate-500 mt-1 uppercase">Initialize baseline costs on scheduler tasks</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-slate-200 dark:border-white/5 text-slate-400 font-bold uppercase tracking-wider text-[9px]">
                      <th className="pb-3 pl-2">Category</th>
                      <th className="pb-3 text-right">Approved Budget</th>
                      <th className="pb-3 text-right">Committed (WOs)</th>
                      <th className="pb-3 text-right">Certified (PCs)</th>
                      <th className="pb-3 text-right">Paid Cost</th>
                      <th className="pb-3 text-right">Forecast EAC</th>
                      <th className="pb-3 text-right pr-2">Variance</th>
                    </tr>
                  </thead>
                  <tbody>
                    {tableData.map((item) => {
                      const committedPercent = item.budget > 0 ? (item.committed / item.budget) * 100 : 0;
                      return (
                        <tr key={item.category_id || item.category} className="border-b border-slate-100 dark:border-white/[0.02] hover:bg-slate-50 dark:hover:bg-white/[0.01] transition-colors">
                          <td className="py-4 pl-2 font-bold text-slate-900 dark:text-white">
                            <div>{item.category}</div>
                            {item.category_code && (
                              <div className="text-[9px] text-slate-400 font-mono mt-0.5 tracking-wider">{item.category_code}</div>
                            )}
                          </td>
                          <td className="py-4 text-right font-mono font-semibold">{formatINRShort(item.budget)}</td>
                          <td className="py-4 text-right font-mono font-semibold">
                            <div>{formatINRShort(item.committed)}</div>
                            <div className="w-20 bg-slate-200 dark:bg-white/5 rounded-full h-1 mt-1.5 ml-auto overflow-hidden">
                              <div 
                                className={`h-full rounded-full ${committedPercent > 100 ? "bg-rose-500" : "bg-sky-500"}`} 
                                style={{ width: `${Math.min(committedPercent, 100)}%` }}
                              />
                            </div>
                          </td>
                          <td className="py-4 text-right font-mono font-semibold text-emerald-600 dark:text-emerald-400">{formatINRShort(item.certified)}</td>
                          <td className="py-4 text-right font-mono font-semibold text-purple-600 dark:text-purple-400">{formatINRShort(item.paid)}</td>
                          <td className="py-4 text-right font-mono font-semibold text-slate-500 dark:text-slate-400">{formatINRShort(item.forecast)}</td>
                          <td className={`py-4 text-right font-mono font-bold pr-2 ${item.variance >= 0 ? "text-emerald-500" : "text-rose-500"}`}>
                            {item.variance > 0 ? "+" : ""}{formatINRShort(item.variance)}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </GlassCard>
        </div>

        {/* Right Column: Visual Category Chart */}
        <div className="xl:col-span-1">
          <GlassCard className="border-slate-200 dark:border-white/5 bg-white/60 dark:bg-slate-950/60 p-6 shadow-2xl backdrop-blur-xl h-full flex flex-col justify-between">
            <div>
              <h3 className="text-xs font-black uppercase tracking-[0.2em] text-slate-900 dark:text-white/45 mb-4">Planned vs Committed</h3>
              <p className="text-[10px] uppercase tracking-wider text-slate-500 leading-relaxed mb-6">
                Visual Comparison of original budget vs current procurement commits
              </p>
            </div>
            <div className="h-[280px] w-full min-w-0">
              <FinancialChart
                title=""
                data={chartData}
                dataKeys={[
                  { key: 'budget', color: '#775a19', label: 'Planned' },
                  { key: 'committed', color: '#505f7a', label: 'Actual' }
                ]}
                height={260}
              />
            </div>
          </GlassCard>
        </div>
      </div>

      {/* Quick Navigation / Financial Integration Links */}
      <div className="space-y-4">
        <h4 className="text-[9px] font-black uppercase tracking-[0.25em] text-slate-400">Financial Module Routing</h4>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Project Financials Link */}
          <GlassCard className="p-6 border-slate-200 dark:border-white/5 bg-white/40 dark:bg-slate-900/40 hover:border-orange-500/30 transition-all group cursor-pointer" onClick={() => router.push("/admin/financials")}>
            <div className="flex items-start justify-between">
              <div className="space-y-2">
                <div className="size-10 rounded-xl bg-orange-500/10 border border-orange-500/20 flex items-center justify-center text-orange-500">
                  <Wallet size={20} />
                </div>
                <h5 className="text-sm font-black uppercase tracking-wider text-slate-900 dark:text-white">Project Financials</h5>
                <p className="text-[10px] text-slate-500 dark:text-slate-400 uppercase tracking-wide leading-relaxed">
                  Analyze organization-wide cash flow statement, petty cash reconciliation, and ledger approvals.
                </p>
              </div>
              <ArrowRight size={18} className="text-slate-400 group-hover:text-orange-500 transition-colors group-hover:translate-x-1 duration-300" />
            </div>
          </GlassCard>

          {/* Work Orders Link */}
          <GlassCard className="p-6 border-slate-200 dark:border-white/5 bg-white/40 dark:bg-slate-900/40 hover:border-orange-500/30 transition-all group cursor-pointer" onClick={() => router.push("/admin/work-orders")}>
            <div className="flex items-start justify-between">
              <div className="space-y-2">
                <div className="size-10 rounded-xl bg-sky-500/10 border border-sky-500/20 flex items-center justify-center text-sky-400">
                  <FileText size={20} />
                </div>
                <h5 className="text-sm font-black uppercase tracking-wider text-slate-900 dark:text-white">Work Orders</h5>
                <p className="text-[10px] text-slate-500 dark:text-slate-400 uppercase tracking-wide leading-relaxed">
                  Manage vendor agreements, scope allocations, variations, and active contract commitments.
                </p>
              </div>
              <ArrowRight size={18} className="text-slate-400 group-hover:text-sky-500 transition-colors group-hover:translate-x-1 duration-300" />
            </div>
          </GlassCard>

          {/* Payment Certificates Link */}
          <GlassCard className="p-6 border-slate-200 dark:border-white/5 bg-white/40 dark:bg-slate-900/40 hover:border-orange-500/30 transition-all group cursor-pointer" onClick={() => router.push("/admin/payment-certificates")}>
            <div className="flex items-start justify-between">
              <div className="space-y-2">
                <div className="size-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-500">
                  <CreditCard size={20} />
                </div>
                <h5 className="text-sm font-black uppercase tracking-wider text-slate-900 dark:text-white">Payment Certificates</h5>
                <p className="text-[10px] text-slate-500 dark:text-slate-400 uppercase tracking-wide leading-relaxed">
                  Audit certification milestones, verified billing valuations, deductions, and payment releases.
                </p>
              </div>
              <ArrowRight size={18} className="text-slate-400 group-hover:text-emerald-500 transition-colors group-hover:translate-x-1 duration-300" />
            </div>
          </GlassCard>
        </div>
      </div>
    </div>
  );
}
