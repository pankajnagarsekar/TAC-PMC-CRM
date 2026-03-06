'use client';

import React, { useEffect, useState, useCallback } from 'react';
import FinancialGrid from '@/components/ui/FinancialGrid';
import { ColDef } from 'ag-grid-community';
import KPICard from '@/components/ui/KPICard';
import { ShieldCheck, RotateCcw, Search } from 'lucide-react';
import api from '@/lib/api';

export default function AuditLogPage() {
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [quickFilter, setQuickFilter] = useState('');
  const [filters, setFilters] = useState({
    entity_type: '',
    limit: 100
  });

  const fetchLogs = useCallback(async (cursor?: string) => {
    setLoading(true);
    try {
      const activeFilters = { ...filters };
      if (cursor) (activeFilters as any).cursor = cursor;

      const { data } = await api.get('/api/audit-logs/', { params: activeFilters });
      
      if (cursor) {
        setLogs(prev => [...prev, ...data.items]);
      } else {
        setLogs(data.items);
      }
      setNextCursor(data.next_cursor);
    } catch (err) {
      console.error('Failed to fetch audit logs', err);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  const columnDefs: ColDef[] = [
    { 
      field: 'timestamp', 
      headerName: 'Time', 
      valueFormatter: (p) => p.value ? new Date(p.value).toLocaleString() : '', 
      width: 180, 
      sort: 'desc' 
    },
    { field: 'user_id', headerName: 'User ID', width: 220 },
    { 
      field: 'action_type', 
      headerName: 'Action', 
      width: 100, 
      cellStyle: (p: any) => {
        if (p.value === 'CREATE') return { color: '#10b981', fontWeight: 'bold' };
        if (p.value === 'UPDATE') return { color: '#3b82f6', fontWeight: 'bold' };
        if (p.value === 'DELETE') return { color: '#ef4444', fontWeight: 'bold' };
        return undefined;
      }
    },
    { field: 'module_name', headerName: 'Module', width: 160 },
    { field: 'entity_type', headerName: 'Entity', width: 160 },
    { field: 'entity_id', headerName: 'Entity ID', width: 220 },
    { 
      headerName: 'Summary', 
      flex: 1, 
      valueGetter: (p) => {
        const nv = p.data.new_value_json;
        if (!nv) return '';
        return JSON.stringify(nv).substring(0, 100);
      }
    }
  ];

  return (
    <div className="p-6 space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-2">
            <ShieldCheck className="text-orange-500" /> Audit Trail
          </h1>
          <p className="text-slate-400 text-sm">Immutable ledger of all administrative and financial actions</p>
        </div>
        
        <div className="flex items-center gap-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={16} />
            <input 
              type="text"
              placeholder="Quick search..."
              value={quickFilter}
              onChange={(e) => setQuickFilter(e.target.value)}
              className="pl-9 pr-4 py-2 bg-slate-800 border border-slate-700 rounded-xl text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-orange-500/50 w-64"
            />
          </div>
          <button 
            onClick={() => fetchLogs()}
            className="p-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl border border-slate-700 transition-colors"
            title="Refresh logs"
          >
            <RotateCcw size={20} />
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <KPICard 
          label="Recent Events" 
          value={logs.length} 
          icon={<ShieldCheck size={20} className="text-orange-500" />} 
          className="bg-slate-900/50"
        />
        {/* We can add more specific counters here if needed */}
      </div>

      <div className="bg-slate-900/50 backdrop-blur-md border border-slate-800 rounded-2xl overflow-hidden shadow-2xl">
        <FinancialGrid
          rowData={logs}
          columnDefs={columnDefs}
          height="calc(100vh - 320px)"
          readOnly={true}
          loading={loading}
          showSrNo={true}
          editable={false}
          quickFilterText={quickFilter}
        />
      </div>

      {nextCursor && (
        <div className="flex justify-center pb-8">
          <button
            onClick={() => fetchLogs(nextCursor)}
            disabled={loading}
            className="px-8 py-2.5 bg-slate-800 hover:bg-slate-700 text-orange-500 rounded-xl font-bold transition-all border border-orange-500/20 active:scale-95 disabled:opacity-50"
          >
            {loading ? 'Loading...' : 'Load More Records'}
          </button>
        </div>
      )}
    </div>
  );
}
