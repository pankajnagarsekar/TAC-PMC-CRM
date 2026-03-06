'use client';

import { useProjectStore } from '@/store/projectStore';
import { formatCurrency } from '@tac-pmc/ui';
import useSWR from 'swr';
import { fetcher } from '@/lib/api';
import { DerivedFinancialState } from '@/types/api';
import {
  TrendingUp, AlertTriangle, Wallet, HardHat, FileText, CreditCard, ArrowUpRight,
  PieChart as PieChartIcon, BarChart3 as BarChartIcon
} from 'lucide-react';
import Link from 'next/link';
import { DonutChart, BarChart, Card, Title, Text, Flex } from '@tremor/react';

function StatCard({
  title, value, sub, icon: Icon, color, alert
}: {
  title: string;
  value: string;
  sub?: string;
  icon: React.ElementType;
  color: string;
  alert?: boolean;
}) {
  return (
    <div className="rounded-2xl p-5 flex flex-col gap-3"
      style={{ background: '#1e293b', border: `1px solid ${alert ? 'rgba(239,68,68,0.3)' : '#334155'}` }}>
      <div className="flex items-center justify-between">
        <p className="text-slate-400 text-sm font-medium">{title}</p>
        <div className="w-9 h-9 rounded-xl flex items-center justify-center"
          style={{ background: `${color}18` }}>
          <Icon size={18} style={{ color }} />
        </div>
      </div>
      <div>
        <p className={`text-2xl font-bold ${alert ? 'text-red-400' : 'text-white'}`}>{value}</p>
        {sub && <p className="text-slate-500 text-xs mt-1">{sub}</p>}
      </div>
    </div>
  );
}

export default function AdminDashboard() {
  const { activeProject } = useProjectStore();

  const { data: financials } = useSWR<DerivedFinancialState[]>(
    activeProject ? `/api/v2/projects/${activeProject.project_id}/financials` : null,
    fetcher
  );

  if (!activeProject) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="w-16 h-16 rounded-2xl mx-auto mb-4 flex items-center justify-center"
            style={{ background: 'rgba(249,115,22,0.1)' }}>
            <AlertTriangle size={28} style={{ color: '#F97316' }} />
          </div>
          <h3 className="text-white font-semibold text-lg mb-2">No Project Selected</h3>
          <p className="text-slate-400 text-sm">Please select a project to view the dashboard.</p>
        </div>
      </div>
    );
  }

  // Aggregate from financials
  const totalBudget = financials?.reduce((sum, f) => sum + (f.approved_budget_amount || 0), 0) ?? 0;
  const totalCommitted = financials?.reduce((sum, f) => sum + (f.committed_value || 0), 0) ?? 0;
  const totalRemaining = financials?.reduce((sum, f) => sum + (f.balance_budget_remaining || 0), 0) ?? 0;
  const overCommitCount = financials?.filter((f) => f.over_commit_flag).length ?? 0;

  const quickLinks = [
    { href: '/admin/work-orders', icon: FileText, label: 'Work Orders', color: '#3b82f6' },
    { href: '/admin/payment-certificates', icon: CreditCard, label: 'Payments', color: '#8b5cf6' },
    { href: '/admin/petty-cash', icon: Wallet, label: 'Petty Cash / OVH', color: '#f59e0b' },
    { href: '/admin/site-operations', icon: HardHat, label: 'Site Operations', color: '#22c55e' },
  ];

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Dashboard</h1>
        <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-6 mt-1">
          <p className="text-slate-400 text-sm">{activeProject.project_name} — Financial Overview</p>
          <div className="flex items-center gap-3">
            <div className="w-32 h-1.5 bg-slate-800 rounded-full overflow-hidden">
              <div 
                className="h-full bg-orange-500 transition-all duration-1000" 
                style={{ width: `${activeProject.completion_percentage || 0}%` }}
              />
            </div>
            <span className="text-[10px] font-bold text-orange-500 uppercase tracking-wider">
              {activeProject.completion_percentage || 0}% Complete
            </span>
          </div>
        </div>
      </div>

      {/* Over-budget Alert Banner */}
      {overCommitCount > 0 && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-2xl p-4 flex items-center gap-4 animate-in slide-in-from-top-4 duration-500">
          <div className="w-10 h-10 rounded-xl bg-red-500/20 flex items-center justify-center text-red-500 flex-shrink-0">
            <AlertTriangle size={20} />
          </div>
          <div className="flex-1 min-w-0">
            <h4 className="text-red-400 font-bold text-sm">Budget Attention Required</h4>
            <p className="text-red-400/70 text-xs mt-0.5 truncate">
              {overCommitCount} categor{overCommitCount !== 1 ? 'ies' : 'y'} are currently over budget. Review allocation and work orders immediately.
            </p>
          </div>
          <Link href="/admin/projects" className="bg-red-500/20 hover:bg-red-500/30 text-red-400 px-4 py-1.5 rounded-lg text-xs font-bold transition-colors">
            Fix Now
          </Link>
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <StatCard
          title="Master Budget"
          value={formatCurrency(totalBudget)}
          sub="Original allocated budget"
          icon={TrendingUp}
          color="#3b82f6"
        />
        <StatCard
          title="Committed"
          value={formatCurrency(totalCommitted)}
          sub="Total Work Orders raised"
          icon={FileText}
          color="#8b5cf6"
        />
        <StatCard
          title="Remaining"
          value={formatCurrency(totalRemaining)}
          sub="Available budget"
          icon={Wallet}
          color="#22c55e"
          alert={totalRemaining < 0}
        />
        <StatCard
          title="Over-Budget"
          value={`${overCommitCount} categor${overCommitCount !== 1 ? 'ies' : 'y'}`}
          sub="Exceeding original budget"
          icon={AlertTriangle}
          color="#ef4444"
          alert={overCommitCount > 0}
        />
      </div>

      {/* Financial Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Budget Allocation Donut */}
        <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6">
          <div className="flex items-center gap-2 mb-6">
             <div className="p-2 rounded-lg bg-orange-500/10 text-orange-500">
               <PieChartIcon size={20} />
             </div>
             <h3 className="text-white font-bold tracking-tight uppercase text-sm">Budget Commitment by Category</h3>
          </div>
          <div className="h-[300px] flex items-center justify-center">
            <DonutChart
              className="mt-6 h-full"
              data={financials?.map(f => ({ name: f.code_id, value: f.committed_value })) || []}
              category="value"
              index="name"
              colors={['orange', 'blue', 'emerald', 'amber', 'rose', 'indigo']}
              variant="donut"
              showAnimation={true}
              onValueChange={(v) => console.log(v)}
            />
          </div>
        </div>

        {/* Committed vs Paid Bar Chart */}
        <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6">
          <div className="flex items-center gap-2 mb-6">
             <div className="p-2 rounded-lg bg-blue-500/10 text-blue-500">
               <BarChartIcon size={20} />
             </div>
             <h3 className="text-white font-bold tracking-tight uppercase text-sm">Committed vs. Paid (Top Categories)</h3>
          </div>
          <div className="h-[300px]">
            <BarChart
              className="mt-6 h-full"
              data={financials?.slice(0, 6).map(f => ({ 
                name: f.code_id, 
                "Committed": f.committed_value,
                "Budget": f.approved_budget_amount 
              })) || []}
              index="name"
              categories={["Committed", "Budget"]}
              colors={["emerald", "slate"]}
              yAxisWidth={48}
              showAnimation={true}
            />
          </div>
        </div>
      </div>

      {/* Category Breakdown */}
      {financials && financials.length > 0 && (
        <div className="bg-slate-900 border border-slate-800 rounded-3xl overflow-hidden shadow-xl">
          <div className="px-8 py-5 border-b border-slate-800 flex items-center justify-between bg-slate-950/20">
            <h3 className="text-white font-bold tracking-tight uppercase text-sm">Detailed Budget Utilization</h3>
            <Link href="/admin/projects"
              className="text-[10px] font-black uppercase tracking-widest flex items-center gap-1.5 text-orange-500 hover:text-orange-400 transition-colors bg-slate-950 px-3 py-1 rounded-full border border-orange-500/20 shadow-lg shadow-orange-950/10">
              Analysis <ArrowUpRight size={14} />
            </Link>
          </div>
          <div className="p-6 space-y-4">
            {financials.map((f) => {
              const pct = f.approved_budget_amount > 0
                ? Math.min(100, (f.committed_value / f.approved_budget_amount) * 100)
                : 0;
              const isOver = f.over_commit_flag;
              return (
                <div key={f.code_id} className="space-y-2 group">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                       <div className={`w-2 h-2 rounded-full ${isOver ? 'bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.4)]' : 'bg-slate-700'}`} />
                       <span className="text-slate-200 font-bold text-sm">{f.code_id}</span>
                       <span className="text-[10px] text-slate-500 font-medium uppercase tracking-widest">utilization</span>
                    </div>
                    <div className="flex items-center gap-4 text-xs font-mono">
                      <span className="text-slate-400">
                        {formatCurrency(f.committed_value)} <span className="text-slate-700 mx-1">/</span> {formatCurrency(f.approved_budget_amount)}
                      </span>
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-black uppercase tracking-tighter ${isOver ? 'bg-rose-500/20 text-rose-500 border border-rose-500/20' : 'bg-emerald-500/10 text-emerald-500 border border-emerald-500/10'}`}>
                        {pct.toFixed(1)}%
                      </span>
                    </div>
                  </div>
                  <div className="h-1.5 bg-slate-950 rounded-full overflow-hidden border border-slate-800/50 p-[1px]">
                    <div
                      className="h-full rounded-full transition-all duration-1000 shadow-[0_0_12px_rgba(249,115,22,0.15)]"
                      style={{
                        width: `${pct}%`,
                        background: isOver 
                          ? 'linear-gradient(90deg, #f43f5e 0%, #e11d48 100%)' 
                          : pct > 80 
                            ? 'linear-gradient(90deg, #f59e0b 0%, #d97706 100%)' 
                            : 'linear-gradient(90deg, #f97316 0%, #ea580c 100%)',
                      }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Quick Links */}
      <div>
        <h3 className="text-slate-400 text-sm font-medium mb-3">Quick Access</h3>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {quickLinks.map(({ href, icon: Icon, label, color }) => (
            <Link key={href} href={href}
              className="flex flex-col items-center gap-3 p-5 rounded-2xl transition-all group"
              style={{ background: '#1e293b', border: '1px solid #334155' }}
              onMouseEnter={(e) => (e.currentTarget.style.borderColor = color)}
              onMouseLeave={(e) => (e.currentTarget.style.borderColor = '#334155')}
            >
              <div className="w-12 h-12 rounded-2xl flex items-center justify-center transition-all"
                style={{ background: `${color}18` }}>
                <Icon size={22} style={{ color }} />
              </div>
              <span className="text-slate-300 text-sm font-medium text-center">{label}</span>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
