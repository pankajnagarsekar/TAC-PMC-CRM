'use client';

import { useMemo } from 'react';
import useSWR from 'swr';
import { Loader2, FileText, ChevronRight } from 'lucide-react';
import { ColDef } from 'ag-grid-community';
import { fetcher } from '@/lib/api';
import FinancialGrid from '@/components/ui/FinancialGrid';
import { formatCurrency, formatDate, getStatusColor } from '@tac-pmc/ui';
import Link from 'next/link';

interface LinkedWorkOrdersProps {
    projectId: string;
}

export default function LinkedWorkOrders({ projectId }: LinkedWorkOrdersProps) {
    const { data: wosData, isLoading } = useSWR(
        projectId ? `/api/projects/${projectId}/work-orders` : null,
        fetcher
    );

    const columnDefs: ColDef<any>[] = useMemo(() => [
        {
            field: 'wo_ref',
            headerName: 'WO Ref',
            flex: 1,
            cellClass: 'font-mono text-indigo-500 font-bold'
        },
        {
            field: 'status',
            headerName: 'Status',
            flex: 0.8,
            cellRenderer: (p: any) => (
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${getStatusColor(p.value)}`}>
                    {p.value}
                </span>
            )
        },
        {
            field: 'vendor_name',
            headerName: 'Vendor',
            flex: 1.5
        },
        {
            field: 'grand_total',
            headerName: 'Value (₹)',
            flex: 1,
            valueFormatter: (p: any) => formatCurrency(p.value)
        },
        {
            field: 'created_at',
            headerName: 'Date',
            flex: 1,
            valueFormatter: (p: any) => formatDate(p.value)
        },
        {
            headerName: '',
            width: 50,
            cellRenderer: (p: any) => (
                <Link href={`/admin/work-orders/${p.data._id}`} className="p-1 hover:bg-zinc-100 dark:hover:bg-slate-800 rounded transition-colors block">
                    <ChevronRight size={16} className="text-zinc-400" />
                </Link>
            )
        }
    ], []);

    if (isLoading) return <div className="p-4 flex justify-center"><Loader2 className="animate-spin text-indigo-500" /></div>;

    const wos = wosData?.items || wosData || [];

    if (!Array.isArray(wos) || wos.length === 0) return null;

    return (
        <div className="bg-white dark:bg-slate-950 border border-zinc-200 dark:border-slate-800 rounded-3xl p-6 shadow-sm mt-6">
            <h2 className="text-sm font-bold text-zinc-400 dark:text-slate-500 uppercase font-black tracking-[0.2em] mb-4 flex items-center gap-2">
                <FileText size={16} className="text-indigo-500" /> Linked Work Orders
            </h2>

            <FinancialGrid
                rowData={wos}
                columnDefs={columnDefs}
                editable={false}
                showSrNo={true}
                height="300px"
            />
        </div>
    );
}
