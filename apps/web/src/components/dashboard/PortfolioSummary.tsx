"use client";

import React from "react";
import {
    Tooltip,
    ResponsiveContainer,
    Cell,
    PieChart,
    Pie
} from "recharts";
import {
    LayoutDashboard,
    Activity,
    Timer,
    AlertTriangle,
    Briefcase
} from "lucide-react";

interface PortfolioData {
    organisation_id: string;
    total_projects: number;
    total_baseline_value: number;
    total_work_order_value: number;
    total_payment_value: number;
    status_distribution: {
        active: number;
        planning: number;
        other: number;
    };
    critical_milestones: Array<{
        project_id: string;
        task_name: string;
        finish_date: string;
        is_critical: boolean;
    }>;
}

export const PortfolioSummary: React.FC<{ data: PortfolioData }> = ({ data }) => {
    const pieData = [
        { name: "Active", value: data.status_distribution.active, color: "#10b981" },
        { name: "Planning", value: data.status_distribution.planning, color: "#3b82f6" },
        { name: "Other", value: data.status_distribution.other, color: "#6b7280" },
    ];

    const formatCurrency = (val: number) => {
        return new Intl.NumberFormat("en-IN", {
            style: "currency",
            currency: "INR",
            maximumFractionDigits: 0,
        }).format(val);
    };

    const woPercent = data.total_baseline_value > 0
        ? Math.round((data.total_work_order_value / data.total_baseline_value) * 100)
        : 0;

    const payPercent = data.total_work_order_value > 0
        ? Math.round((data.total_payment_value / data.total_work_order_value) * 100)
        : 0;

    return (
        <div className="space-y-6">
            {/* KPI Header */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <KPICard
                    title="Total Projects"
                    value={data.total_projects.toString()}
                    icon={<Briefcase className="w-5 h-5 text-blue-500" />}
                    description="Portfolio tracks"
                />
                <KPICard
                    title="Baseline Value"
                    value={formatCurrency(data.total_baseline_value)}
                    icon={<LayoutDashboard className="w-5 h-5 text-emerald-500" />}
                    description="Budgeted total"
                />
                <KPICard
                    title="Awarded (WO)"
                    value={formatCurrency(data.total_work_order_value)}
                    icon={<Activity className="w-5 h-5 text-sky-500" />}
                    description={`${woPercent}% of baseline`}
                />
                <KPICard
                    title="Disbursed (PC)"
                    value={formatCurrency(data.total_payment_value)}
                    icon={<Timer className="w-5 h-5 text-indigo-500" />}
                    description={`${payPercent}% of awarded`}
                />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Project Mix */}
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-2xl">
                    <h3 className="text-slate-200 font-semibold mb-6 flex items-center gap-2">
                        <LayoutDashboard className="w-4 h-4" /> Project Mix
                    </h3>
                    <div className="h-[250px] w-full">
                        <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                                <Pie
                                    data={pieData}
                                    cx="50%"
                                    cy="50%"
                                    innerRadius={60}
                                    outerRadius={80}
                                    paddingAngle={5}
                                    dataKey="value"
                                >
                                    {pieData.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={entry.color} />
                                    ))}
                                </Pie>
                                <Tooltip
                                    contentStyle={{ backgroundColor: "#0f172a", border: "1px solid #1e293b" }}
                                    itemStyle={{ color: "#f8fafc" }}
                                />
                            </PieChart>
                        </ResponsiveContainer>
                    </div>
                    <div className="mt-4 flex justify-around text-xs text-slate-400">
                        {pieData.map(d => (
                            <div key={d.name} className="flex items-center gap-2">
                                <div className="w-2 h-2 rounded-full" style={{ backgroundColor: d.color }} />
                                {d.name} ({d.value})
                            </div>
                        ))}
                    </div>
                </div>

                {/* Critical Milestones */}
                <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-2xl overflow-hidden">
                    <h3 className="text-slate-200 font-semibold mb-6 flex items-center gap-2">
                        <Timer className="w-4 h-4" /> Portfolio Milestone Watchlist
                    </h3>
                    <div className="overflow-x-auto">
                        <table className="w-full text-left">
                            <thead>
                                <tr className="text-xs font-medium text-slate-500 uppercase tracking-wider border-b border-slate-800">
                                    <th className="pb-3 px-2">Project</th>
                                    <th className="pb-3 px-2">Milestone Name</th>
                                    <th className="pb-3 px-2 text-right">Target Date</th>
                                    <th className="pb-3 px-2 text-right">Status</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-800">
                                {data.critical_milestones.map((m, i) => (
                                    <tr key={i} className="hover:bg-slate-800/50 transition-colors group">
                                        <td className="py-4 px-2 text-sm text-slate-400 font-mono">{m.project_id.toString().slice(-6)}</td>
                                        <td className="py-4 px-2 text-sm text-slate-200 font-medium">{m.task_name}</td>
                                        <td className="py-4 px-2 text-sm text-slate-400 text-right">{m.finish_date}</td>
                                        <td className="py-4 px-2 text-right">
                                            {m.is_critical ? (
                                                <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-500/10 text-rose-500 border border-rose-500/20">
                                                    <AlertTriangle className="w-3 h-3" /> CRITICAL
                                                </span>
                                            ) : (
                                                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-800 text-slate-400">
                                                    STABLE
                                                </span>
                                            )}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    );
};

interface KPICardProps {
    title: string;
    value: string;
    icon: React.ReactNode;
    description: string;
}

const KPICard = ({ title, value, icon, description }: KPICardProps) => (
    <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl shadow-lg group hover:border-slate-700 transition-all duration-300">
        <div className="flex justify-between items-start mb-2">
            <div className="p-2 bg-slate-800 rounded-lg group-hover:bg-slate-800 transition-colors">
                {icon}
            </div>
            <span className="text-[10px] text-slate-500 font-bold tracking-widest uppercase">{title}</span>
        </div>
        <div className="text-2xl font-bold text-white mb-1">{value}</div>
        <p className="text-xs text-slate-500">{description}</p>
    </div>
);
