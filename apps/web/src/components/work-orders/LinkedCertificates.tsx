'use client';

import { useMemo } from 'react';
import useSWR from 'swr';
import { Loader2, CheckCircle, ChevronRight } from 'lucide-react';
import { ColDef } from 'ag-grid-community';
import { fetcher } from '@/lib/api';
import FinancialGrid from '@/components/ui/FinancialGrid';
import { formatCurrency, formatDate, getStatusColor } from '@tac-pmc/ui';
import Link from 'next/link';

interface LinkedCertificatesProps {
  projectId: string;
  workOrderId?: string;
}

export default function LinkedCertificates({ projectId, workOrderId }: LinkedCertificatesProps) {
  const url = workOrderId
    ? `/api/v1/payments/${projectId}?work_order_id=${workOrderId}`
    : `/api/v1/payments/${projectId}`;

  const { data: pcsData, isLoading } = useSWR(projectId ? url : null, fetcher);

  const columnDefs: ColDef<any>[] = useMemo(() => [
    {
      field: 'pc_ref',
      headerName: 'PC Ref',
      flex: 1,
      cellClass: 'font-mono text-orange-500 font-bold'
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
      field: 'grand_total',
      headerName: 'Certified (₹)',
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
        <Link href={`/admin/payment-certificates/${p.data._id}`} className="p-1 hover:bg-zinc-100 dark:hover:bg-slate-800 rounded transition-colors block">
          <ChevronRight size={16} className="text-zinc-400" />
        </Link>
      )
    }
  ], []);

  if (isLoading) return <div className="p-4 flex justify-center"><Loader2 className="animate-spin text-orange-500" /></div>;

  const pcs = pcsData?.items || pcsData || [];

  if (!Array.isArray(pcs) || pcs.length === 0) return null;

  return (
    <div className="bg-white dark:bg-slate-950 border border-zinc-200 dark:border-slate-800 rounded-3xl p-6 shadow-sm mt-6">
      <h2 className="text-sm font-bold text-zinc-400 dark:text-slate-500 uppercase font-black tracking-[0.2em] mb-4 flex items-center gap-2">
        <CheckCircle size={16} className="text-orange-500" /> Linked Payment Certificates
      </h2>

      <FinancialGrid
        rowData={pcs}
        columnDefs={columnDefs}
        editable={false}
        showSrNo={true}
        height="300px"
      />
    </div>
  );
}
