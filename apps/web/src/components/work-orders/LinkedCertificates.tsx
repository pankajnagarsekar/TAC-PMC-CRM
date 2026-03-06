'use client';

import { useMemo } from 'react';
import useSWR from 'swr';
import { Loader2, CheckCircle } from 'lucide-react';
import { ColDef } from 'ag-grid-community';
import { fetcher } from '@/lib/api';
import FinancialGrid from '@/components/ui/FinancialGrid';
import { formatCurrency, formatDate } from '@tac-pmc/ui';

interface LinkedCertificatesProps {
  projectId: string;
  workOrderId?: string;
}

export default function LinkedCertificates({ projectId, workOrderId }: LinkedCertificatesProps) {
  const url = workOrderId 
    ? `/api/projects/${projectId}/payment-certificates?work_order_id=${workOrderId}`
    : `/api/projects/${projectId}/payment-certificates`;

  const { data: pcsData, isLoading } = useSWR(projectId ? url : null, fetcher);

  const columnDefs: ColDef<any>[] = useMemo(() => [
    { field: 'pc_ref', headerName: 'PC Ref', flex: 1, cellClass: 'font-mono text-orange-500 font-bold' },
    { field: 'status', headerName: 'Status', flex: 1 },
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
    }
  ], []);

  if (isLoading) return <div className="p-4 flex justify-center"><Loader2 className="animate-spin text-orange-500" /></div>;

  const pcs = pcsData?.items || pcsData || []; // Handle both paginated and list responses

  if (!Array.isArray(pcs) || pcs.length === 0) return null;

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl animate-in fade-in slide-in-from-bottom-4 duration-700 mt-6">
      <h2 className="text-sm font-bold text-slate-400 uppercase tracking-widest mb-4 flex items-center gap-2">
         <CheckCircle size={16}/> Linked Payment Certificates
      </h2>
      
      <FinancialGrid
        rowData={pcs}
        columnDefs={columnDefs}
        editable={false}
        showSrNo={true}
        height="200px"
      />
    </div>
  );
}
