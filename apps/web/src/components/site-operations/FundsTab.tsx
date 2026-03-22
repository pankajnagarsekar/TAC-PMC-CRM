"use client";

import { useState, useMemo } from "react";
import useSWR from "swr";
import { Building2, Plus, AlertTriangle, Loader2 } from "lucide-react";
import FinancialGrid from "@/components/ui/FinancialGrid";
import { useProjectStore } from "@/store/projectStore";
import { fetcher } from "@/lib/api";
import ExpenseEntryModal from "@/components/petty-cash/ExpenseEntryModal";
import { formatCurrency } from "@tac-pmc/ui";
import { ColDef } from "ag-grid-community";

export default function FundsTab() {
    const { activeProject } = useProjectStore();
    const [showAddModal, setShowAddModal] = useState(false);

    const { data, error, isLoading, mutate } = useSWR(
        activeProject ? `/api/projects/${activeProject.project_id || activeProject._id}/cash-transactions` : null,
        fetcher
    );

    const transactions = data?.items || [];

    const columnDefs: ColDef[] = useMemo(() => [
        {
            headerName: "Entry Date",
            field: "created_at",
            flex: 1.2,
            cellRenderer: (params: any) => (
                <span className="text-slate-400 font-mono text-[11px] uppercase tracking-tighter">
                    {params.value ? new Date(params.value).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }) : '-'}
                </span>
            )
        },
        {
            headerName: "Expense Description",
            field: "purpose",
            flex: 2,
            cellClass: "font-semibold text-zinc-900 dark:text-white"
        },
        {
            headerName: "Category",
            field: "category_name",
            flex: 1,
            cellClass: "text-[10px] uppercase font-black tracking-widest text-zinc-500 dark:text-slate-500"
        },
        {
            headerName: "Disbursement",
            field: "amount",
            flex: 1,
            cellRenderer: (params: any) => (
                <span className="font-mono font-bold text-rose-500 dark:text-rose-400">
                    {formatCurrency(params.value || 0)}
                </span>
            )
        },
        {
            headerName: "Originator",
            field: "created_by_name",
            flex: 1.2,
            cellRenderer: (params: any) => (
                <div className="flex items-center gap-2">
                    <div className="w-5 h-5 rounded bg-zinc-100 dark:bg-white/5 border border-zinc-200 dark:border-white/10 flex items-center justify-center text-zinc-500 dark:text-slate-500 text-[9px] font-black uppercase">
                        {params.data.created_by_name?.[0] || 'U'}
                    </div>
                    <span className="text-zinc-500 dark:text-slate-500 text-[10px] uppercase font-black tracking-widest">{params.data.created_by_name || "System"}</span>
                </div>
            )
        }
    ], []);

    const totalOverheads = useMemo(() => {
        return (transactions as any[])?.reduce((sum: number, o: any) => sum + (parseFloat(o.amount) || 0), 0) || 0;
    }, [transactions]);

    if (!activeProject) {
        return (
            <div className="flex flex-col items-center justify-center min-h-[400px]">
                <div className="empty-state-luxury max-w-sm text-center">
                    <div className="empty-state-luxury-icon mb-4 text-zinc-400 dark:text-slate-800">
                        <Building2 size={32} />
                    </div>
                    <h3 className="empty-state-luxury-title text-zinc-900 dark:text-white">No Project Context</h3>
                    <p className="empty-state-luxury-desc text-zinc-500 dark:text-slate-500">Select a project to manage site funds and overheads.</p>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div>
                    <h2 className="text-xl font-bold text-zinc-900 dark:text-white flex items-center gap-3">
                        Site Fund Ledger
                    </h2>
                    <p className="text-zinc-500 dark:text-slate-500 text-xs mt-1">Managed site liquidity and maintenance disbursements.</p>
                </div>

                <div className="flex items-center gap-6">
                    <div className="flex flex-col items-end px-4 py-2 bg-zinc-50 dark:bg-slate-950/50 border border-zinc-200 dark:border-white/5 rounded-2xl">
                        <span className="text-[9px] text-zinc-500 dark:text-slate-500 font-black uppercase tracking-widest">Total Utilization</span>
                        <span className="text-lg font-mono font-black text-zinc-900 dark:text-white">{formatCurrency(totalOverheads)}</span>
                    </div>
                    <button
                        onClick={() => setShowAddModal(true)}
                        className="px-6 py-3 bg-orange-600 hover:bg-orange-500 text-white rounded-2xl text-[10px] font-black uppercase tracking-widest transition-all shadow-xl shadow-orange-900/20 flex items-center gap-3 border border-orange-500/20"
                    >
                        <Plus size={16} strokeWidth={3} /> Add Transaction
                    </button>
                </div>
            </div>

            <div className="bg-white dark:bg-slate-900/40 border border-zinc-200 dark:border-white/5 rounded-[2rem] p-6 shadow-2xl backdrop-blur-md">
                <div className="relative min-h-[400px]">
                    {error ? (
                        <div className="absolute inset-0 flex flex-col items-center justify-center gap-4">
                            <AlertTriangle className="text-rose-500 opacity-20" size={48} />
                            <div className="text-center">
                                <h3 className="text-zinc-900 dark:text-white font-bold">Query Failure</h3>
                                <p className="text-zinc-500 dark:text-slate-500 text-xs mt-1">Failed to retrieve fund records.</p>
                            </div>
                            <button onClick={() => mutate()} className="text-[10px] font-bold text-orange-500 underline uppercase tracking-widest">Retry Connection</button>
                        </div>
                    ) : (
                        <FinancialGrid
                            rowData={transactions || []}
                            columnDefs={columnDefs}
                            loading={isLoading}
                            height="500px"
                        />
                    )}
                </div>
            </div>

            <ExpenseEntryModal
                isOpen={showAddModal}
                onClose={() => setShowAddModal(false)}
                onSuccess={() => mutate()}
                projectId={activeProject.project_id || activeProject._id || ""}
            />
        </div>
    );
}
