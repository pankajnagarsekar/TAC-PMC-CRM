'use client';

import { useState, useCallback, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Plus, Search, FileText, Loader2 } from 'lucide-react';
import api from '@/lib/api';
import { WorkOrder } from '@/types/api';
import { formatCurrency, formatDate } from '@tac-pmc/ui';
import { useProjectStore } from '@/store/projectStore';
import FinancialGrid from '@/components/ui/FinancialGrid';
import { ColDef } from 'ag-grid-community';

export default function WorkOrdersPage() {
  const router = useRouter();
  const { activeProject } = useProjectStore();
  const [searchTerm, setSearchTerm] = useState('');
  
  const [items, setItems] = useState<WorkOrder[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [isInitialLoading, setIsInitialLoading] = useState(true);
  const [isMoreLoading, setIsMoreLoading] = useState(false);

  const fetchWorkOrders = useCallback(async (cursor?: string | null) => {
    if (!activeProject) return;
    
    if (!cursor) setIsInitialLoading(true);
    else setIsMoreLoading(true);
    
    try {
      const url = `/api/work-orders?project_id=${activeProject._id || activeProject.project_id}&limit=50${cursor ? `&cursor=${cursor}` : ''}`;
      const res = await api.get<{ items: WorkOrder[], next_cursor: string | null }>(url);
      
      if (!cursor) {
        setItems(res.data.items);
      } else {
        setItems(prev => [...prev, ...res.data.items]);
      }
      setNextCursor(res.data.next_cursor);
    } catch (err) {
      console.error('Failed to fetch WOs', err);
    } finally {
      setIsInitialLoading(false);
      setIsMoreLoading(false);
    }
  }, [activeProject]);

  useEffect(() => {
    fetchWorkOrders();
  }, [fetchWorkOrders]);

  const columnDefs: ColDef<WorkOrder>[] = [
    { 
        field: 'wo_ref', 
        headerName: 'Ref No.', 
        width: 150, 
        cellRenderer: (p: any) => (
            <button 
                onClick={() => router.push(`/admin/work-orders/${p.data._id}`)}
                className="text-orange-400 font-bold hover:underline font-mono"
            >
                {p.value}
            </button>
        )
    },
    { 
        field: 'created_at', 
        headerName: 'Date', 
        width: 150,
        valueFormatter: (p: any) => p.value ? formatDate(p.value) : 'N/A'
    },
    {
        field: 'description',
        headerName: 'Description',
        flex: 1,
        minWidth: 250
    },
    { 
        field: 'grand_total', 
        headerName: 'Amount', 
        width: 150,
        type: 'numericColumn',
        valueFormatter: (p: any) => formatCurrency(p.value || 0),
        cellClass: 'font-mono text-emerald-400 font-bold'
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
                    <span className={`px-2.5 py-0.5 rounded font-bold text-[10px] uppercase border ${colors[status] || colors['Draft']}`}>
                        {status}
                    </span>
                </div>
            );
        }
    }
  ];

  const filteredItems = items.filter(wo => {
    const term = searchTerm.toLowerCase();
    return (
        wo.wo_ref?.toLowerCase().includes(term) ||
        wo.description?.toLowerCase().includes(term) ||
        wo.status?.toLowerCase().includes(term)
    );
  });

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <FileText className="text-orange-500" />
            Work Orders
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Manage single-category commitment orders.
            {activeProject ? ` Showing records for ${activeProject.project_name}.` : ' Select a project to create.'}
          </p>
        </div>

        <div className="flex items-center gap-3 w-full sm:w-auto">
          <div className="relative flex-1 sm:w-64">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
            <input
              type="text"
              placeholder="Search references..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full bg-slate-900 border border-slate-800 rounded-lg pl-10 pr-4 py-2 text-sm text-white focus:outline-none focus:border-orange-500"
            />
          </div>
          
          <button
            disabled={!activeProject}
            onClick={() => router.push('/admin/work-orders/new')}
            className="flex items-center gap-2 bg-orange-500 hover:bg-orange-600 disabled:opacity-50 text-white px-4 py-2 rounded-lg text-sm font-bold transition-colors whitespace-nowrap"
          >
            <Plus size={18} /> New Work Order
          </button>
        </div>
      </div>

      {!activeProject ? (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center shadow-xl">
          <FileText className="w-12 h-12 text-slate-600 mx-auto mb-4" />
          <h3 className="text-xl font-bold text-white mb-2">No Project Selected</h3>
          <p className="text-slate-400">Please select an active project from the top navigation context.</p>
        </div>
      ) : isInitialLoading ? (
        <div className="flex items-center justify-center h-64 border border-slate-800 rounded-xl bg-slate-900/50">
          <Loader2 className="animate-spin h-8 w-8 text-orange-500" />
        </div>
      ) : filteredItems.length === 0 ? (
        <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-12 text-center">
          <h3 className="text-lg font-semibold text-white mb-2">No Work Orders Found</h3>
          <p className="text-slate-400">Generate standard commitment orders to reserve budget category limits safely.</p>
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
                 onClick={() => fetchWorkOrders(nextCursor)}
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
