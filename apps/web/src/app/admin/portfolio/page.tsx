"use client";

import React, { useEffect, useState } from "react";
import { PortfolioSummary } from "@/components/dashboard/PortfolioSummary";
import PortfolioGantt from "@/components/dashboard/PortfolioGantt";
import ResourceHeatmap from "@/components/dashboard/ResourceHeatmap";
import * as Tabs from "@radix-ui/react-tabs";
import { Loader2, RefreshCcw, Activity, AlertTriangle as AlertTriangleIcon } from "lucide-react";
import { portfolioApi } from "@/lib/api";

export default function PortfolioPage() {
    const [data, setData] = useState<any>(null);
    const [milestones, setMilestones] = useState<any[]>([]);
    const [heatmap, setHeatmap] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchPortfolio = async () => {
        setLoading(true);
        try {
            const [summary, ms, hm] = await Promise.all([
                portfolioApi.getSummary(),
                portfolioApi.getMilestones(),
                portfolioApi.getResourceHeatmap()
            ]);
            setData(summary);
            setMilestones(ms);
            setHeatmap(hm);
            setError(null);
        } catch (err: any) {
            setError("Failed to load portfolio statistics.");
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchPortfolio();
    }, []);

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center h-[calc(100vh-200px)] gap-4 text-white">
                <Loader2 className="w-10 h-10 text-emerald-500 animate-spin" />
                <p className="text-slate-400 font-mono text-sm tracking-widest animate-pulse">
                    AGGREGATING ENTERPRISE DATA...
                </p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="p-8 text-center bg-rose-500/10 border border-rose-500/20 rounded-xl max-w-2xl mx-auto mt-20">
                <p className="text-rose-500 font-bold mb-4">{error}</p>
                <button
                    onClick={fetchPortfolio}
                    className="px-4 py-2 bg-rose-500 text-white rounded-lg hover:bg-rose-600 transition-colors flex items-center gap-2 mx-auto"
                >
                    <RefreshCcw className="w-4 h-4" /> Retry Connection
                </button>
            </div>
        );
    }

    return (
        <div className="p-6 lg:p-8 space-y-8 animate-in fade-in duration-500 text-white">
            <header className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div>
                    <h1 className="text-3xl font-bold text-white tracking-tight">Enterprise Portfolio</h1>
                    <p className="text-slate-400 text-sm mt-1">Cross-project visibility and resource optimization engine</p>
                </div>
                <button
                    onClick={fetchPortfolio}
                    className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-all"
                    title="Refresh Data"
                >
                    <RefreshCcw className="w-5 h-5" />
                </button>
            </header>

            <Tabs.Root defaultValue="overview" className="w-full">
                <Tabs.List className="flex gap-2 bg-slate-950 border border-white/5 p-1 rounded-2xl mb-6 w-fit">
                    <Tabs.Trigger value="overview" className="data-[state=active]:bg-white/10 data-[state=active]:text-white rounded-xl px-6 py-2 text-xs font-bold uppercase tracking-widest text-slate-500 transition-all">
                        Executive Summary
                    </Tabs.Trigger>
                    <Tabs.Trigger value="resources" className="data-[state=active]:bg-white/10 data-[state=active]:text-white rounded-xl px-6 py-2 text-xs font-bold uppercase tracking-widest text-slate-500 transition-all">
                        Resource Capacity
                    </Tabs.Trigger>
                    <Tabs.Trigger value="risk" className="data-[state=active]:bg-white/10 data-[state=active]:text-white rounded-xl px-6 py-2 text-xs font-bold uppercase tracking-widest text-slate-500 transition-all">
                        Inter-Project Dependencies
                    </Tabs.Trigger>
                </Tabs.List>

                <Tabs.Content value="overview" className="space-y-8 focus-visible:outline-none">
                    <PortfolioSummary data={data} />
                    <PortfolioGantt milestones={milestones} />
                </Tabs.Content>

                <Tabs.Content value="resources" className="space-y-6 focus-visible:outline-none">
                    <ResourceHeatmap data={heatmap} />
                </Tabs.Content>

                <Tabs.Content value="risk" className="space-y-6 focus-visible:outline-none">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <RiskCard
                            title="Critical Path Exposure"
                            detail="3 projects have milestones with < 2 days slack"
                            severity="HIGH"
                        />
                        <RiskCard
                            title="External Buffers"
                            detail="Centralized procurement delays affecting 4 site mobilizations"
                            severity="MEDIUM"
                        />
                    </div>
                </Tabs.Content>
            </Tabs.Root>
        </div>
    );
}

const RiskCard = ({ title, detail, severity }: any) => (
    <div className="bg-slate-900 border border-slate-800 p-6 rounded-xl relative overflow-hidden group shadow-xl">
        <div className={`absolute top-0 left-0 w-1 h-full ${severity === 'HIGH' ? 'bg-rose-500' : 'bg-amber-500'}`} />
        <h4 className="text-white font-bold mb-2 flex items-center gap-2">
            <AlertTriangleIcon className={`w-4 h-4 ${severity === 'HIGH' ? 'text-rose-500' : 'text-amber-500'}`} />
            {title}
        </h4>
        <p className="text-slate-400 text-sm">{detail}</p>
    </div>
);
