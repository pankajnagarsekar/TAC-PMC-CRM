'use client';

import { useState, useCallback, useEffect } from 'react';
import Link from 'next/link';
import { Plus, Search, FileText, Loader2 } from 'lucide-react';
import api, { fetcher } from '@/lib/api';
import useSWR from 'swr';
import { useProjectStore } from '@/store/projectStore';
import { PaymentCertificate, CodeMaster, Vendor } from '@/types/api';
import { formatCurrency, formatDate } from '@tac-pmc/ui';
import FinancialGrid from '@/components/ui/FinancialGrid';
import { ColDef } from 'ag-grid-community';
import NetworkErrorRetry from '@/components/ui/NetworkErrorRetry';

export default function PaymentCertificatesPage() {
  const { activeProject } = useProjectStore();
  const [searchTerm, setSearchTerm] = useState('');

  const [items, setItems] = useState<PaymentCertificate[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [isInitialLoading, setIsInitialLoading] = useState(true);
  const [isMoreLoading, setIsMoreLoading] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);

  // Need mappings for categories / vendors to render readable labels
  const { data: categories } = useSWR<CodeMaster[]>('/api/codes?active_only=true', fetcher);
  const { data: vendors } = useSWR<Vendor[]>('/api/vendors', fetcher);

  const getCategoryName = (id: string) => categories?.find(c => c._id === id)?.category_name || id;
  const getVendorName = (id: string) => vendors?.find(v => v._id === id)?.name || id;

  const fetchPCs = useCallback(async (cursor?: string | null) => {
    if (!activeProject) return;

    if (!cursor) setIsInitialLoading(true);
    else setIsMoreLoading(true);

    try {
      const url = `/api/payment-certificates?project_id=${activeProject.project_id || (activeProject as any)._id}&limit=50${cursor ? `&cursor=${cursor}` : ''}`;
      const res = await api.get<{ items: PaymentCertificate[], next_cursor: string | null }>(url);

      if (!cursor) {
        setItems(res.data.items);
      } else {
        setItems(prev => [...prev, ...res.data.items]);
      }
      setNextCursor(res.data.next_cursor);
    } catch (err) {
      console.error('Failed to fetch PCs', err);
      setFetchError('Failed to load payment certificates.');
    } finally {
      setIsInitialLoading(false);
      setIsMoreLoading(false);
    }
  }, [activeProject]);

  useEffect(() => {
    fetchPCs();
  }, [fetchPCs]);

  const columnDefs: ColDef<PaymentCertificate>[] = [
    {
      field: 'pc_ref',
      headerName: 'Ref ID',
      width: 150,
      cellRenderer: (p: any) => (
        <Link href={`/admin/payment-certificates/${p.data._id}`} className="font-mono text-emerald-400 font-bold hover:underline">
          {p.value}
        </Link>
      )
    },
    {
      field: 'fund_request',
      headerName: 'Type',
      width: 130,
      cellRenderer: (p: any) => p.value ? (
        <span className="text-[10px] uppercase tracking-widest font-bold text-amber-500 bg-amber-500/10 px-2 py-0.5 rounded-full">Fund Request</span>
      ) : (
        <span className="text-[10px] uppercase tracking-widest font-bold text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded-full border border-blue-500/20">WO Linked</span>
      )
    },
    {
      field: 'category_id',
      headerName: 'Category',
      width: 180,
      valueFormatter: (p: any) => getCategoryName(p.value)
    },
    {
      field: 'vendor_id',
      headerName: 'Payee / Target',
      flex: 1,
      minWidth: 200,
      cellRenderer: (p: any) => p.data.fund_request ? (
        <span className="text-slate-500 italic">Internal Trx</span>
      ) : (
        <span className="text-slate-300">{getVendorName(p.value!)}</span>
      )
    },
    {
      field: 'grand_total',
      headerName: 'Grand Total',
      width: 150,
      type: 'numericColumn',
      valueFormatter: (p: any) => formatCurrency(p.value || 0),
      cellClass: 'font-mono font-medium text-white'
    },
    {
      field: 'status',
      headerName: 'Status',
      width: 120,
      cellRenderer: (p: any) => {
        const status = p.value;
        const colors: Record<string, string> = {
          'Draft': 'bg-slate-500/10 text-slate-400 border-slate-500/20',
          'Pending': 'bg-amber-500/10 text-amber-400 border-amber-500/20',
          'Completed': 'bg-blue-500/10 text-blue-400 border-blue-500/20',
          'Closed': 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
          'Cancelled': 'bg-red-500/10 text-red-400 border-red-500/20'
        };
        return (
          <div className="flex items-center h-full">
            <span className={`px-2.5 py-0.5 rounded font-bold text-[10px] uppercase border ${colors[p.value] || colors['Draft']}`}>
              {status}
            </span>
          </div>
        );
      }
    },
    {
      field: 'created_at',
      headerName: 'Date',
      width: 150,
      valueFormatter: (p: any) => p.value ? formatDate(p.value) : '-'
    }
  ];

  const filteredItems = items.filter(pc =>
    pc.pc_ref?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (pc.category_id && getCategoryName(pc.category_id).toLowerCase().includes(searchTerm.toLowerCase()))
  );

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-12 animate-in fade-in duration-500">
      <div className="flex flex-col md:flex-row justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Payment Certificates</h1>
          <p className="text-slate-400 text-sm">
            {activeProject ? `Manage payments and fund requests for ${activeProject.project_name}` : 'Select a project to view limits'}
          </p>
        </div>

        {activeProject && (
          <div className="flex gap-3">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
              <input
                type="text"
                placeholder="Search PCs..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10 pr-4 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-white focus:outline-none focus:border-emerald-500 w-64"
              />
            </div>
            <Link
              href="/admin/payment-certificates/new"
              className="flex items-center gap-2 bg-orange-600 hover:bg-orange-500 text-white px-4 py-2 rounded-lg font-medium transition-colors shadow-lg shadow-orange-500/20 active:scale-95"
            >
              <Plus size={18} />
              Create Certificate
            </Link>
          </div>
        )}
      </div>

      {fetchError ? (
        <NetworkErrorRetry
          message={fetchError}
          onRetry={() => { setFetchError(null); fetchPCs(); }}
        />
      ) : !activeProject ? (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center shadow-xl">
          <FileText className="w-12 h-12 text-slate-600 mx-auto mb-4" />
          <h3 className="text-xl font-bold text-white mb-2">No Project Selected</h3>
          <p className="text-slate-400">Please select an active project from the top navigation context.</p>
        </div>
      ) : isInitialLoading ? (
        <div className="flex items-center justify-center h-64 border border-slate-800 rounded-xl bg-slate-900/50">
          <Loader2 className="animate-spin h-8 w-8 text-emerald-500" />
        </div>
      ) : filteredItems.length === 0 ? (
        <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-12 text-center text-slate-500">
          No matching Payment Certificates found.
        </div>
      ) : (
        <div className="space-y-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
            <FinancialGrid
              rowData={filteredItems}
              columnDefs={columnDefs}
              height="500px"
            />
          </div>

          {nextCursor && (
            <div className="flex justify-center pb-8">
              <button
                onClick={() => fetchPCs(nextCursor)}
                disabled={isMoreLoading}
                className="flex items-center gap-2 px-6 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-full text-sm font-bold transition-all disabled:opacity-50"
              >
                {isMoreLoading && <Loader2 size={14} className="animate-spin" />}
                Load More Records
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
