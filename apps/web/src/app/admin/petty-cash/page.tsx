'use client';

import { useState } from 'react';
import useSWR from 'swr';
import { Wallet, Search, ArrowRight, Loader2, IndianRupee, AlertTriangle } from 'lucide-react';
import Link from 'next/link';

import api, { fetcher } from '@/lib/api';
import { useProjectStore } from '@/store/projectStore';
import { FundAllocation } from '@/types/api';
import { formatCurrency } from '@tac-pmc/ui';

export default function PettyCashDashboard() {
  const { activeProject } = useProjectStore();
  const [searchTerm, setSearchTerm] = useState('');

  const { data, error, isLoading } = useSWR<{ items: FundAllocation[] }>(
    activeProject ? `/api/projects/${activeProject.project_id}/fund-allocations` : null,
    fetcher
  );

  const { data: summary, isLoading: summaryLoading } = useSWR<any>(
    activeProject ? `/api/projects/${activeProject.project_id}/cash-summary` : null,
    fetcher
  );

  const allocations = data?.items || [];
  const filteredAllocations = allocations.filter(a => 
      a.category_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      a.category_id.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const totalRemaining = summary?.cash_in_hand ?? allocations.reduce((sum, a) => sum + (a.allocation_remaining || 0), 0);
  const isNegative = totalRemaining < 0;

  if (!activeProject) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-400">
        <p>Please select a project to view Liquidity Allocations.</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-500/10 border border-red-500/20 text-red-500 p-4 rounded-xl">
        Failed to load fund allocations. {error.message}
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <Wallet className="text-amber-500" />
            Petty Cash & Site Overheads
          </h1>
          <p className="text-slate-400 text-sm mt-1">Manage live site spending ceilings injected from Payment Certificates.</p>
        </div>
      </div>

      {/* Warning Banners */}
      {summary?.flags?.is_negative && (
        <div className="bg-red-500/10 border border-red-500/20 text-red-500 p-4 rounded-xl flex items-center gap-3 animate-in slide-in-from-top duration-500">
           <AlertTriangle size={20} className="animate-pulse" />
           <div>
             <p className="text-sm font-bold">Critical: Negative Liquidity</p>
             <p className="text-xs opacity-80">Site balance is below ₹0. Immediate fund injection required to normalize operations.</p>
           </div>
        </div>
      )}
      {!summary?.flags?.is_negative && summary?.flags?.is_below_threshold && (
        <div className="bg-amber-500/10 border border-amber-500/20 text-amber-500 p-4 rounded-xl flex items-center gap-3 animate-in slide-in-from-top duration-500">
           <AlertTriangle size={20} />
           <div>
             <p className="text-sm font-bold">Low Liquidity Warning</p>
             <p className="text-xs opacity-80">Site funds are below the threshold. Consider closing pending Fund Transfer PCs.</p>
           </div>
        </div>
      )}

      {/* Global Stats */}
      <div className={`bg-slate-900 border ${isNegative ? 'border-red-900/50' : 'border-slate-800'} rounded-xl p-6 shadow-xl relative overflow-hidden transition-colors duration-500`}>
         <div className="absolute top-0 right-0 p-8 opacity-5">
             <IndianRupee size={150} />
         </div>
         <p className="text-slate-400 text-sm uppercase tracking-widest font-bold mb-2">Total Site Liquidity</p>
         {isLoading || summaryLoading ? (
             <Loader2 className="w-6 h-6 text-amber-500 animate-spin mt-2" />
         ) : (
             <p className={`text-4xl font-mono font-bold ${isNegative ? 'text-red-500' : 'text-emerald-400'}`}>
                {formatCurrency(totalRemaining)}
             </p>
         )}
         {summary?.days_since_last_pc_close !== null && (
            <p className="text-[10px] text-slate-500 uppercase tracking-widest mt-4 font-bold">
              Last replenishment: <span className="text-slate-300">{summary?.days_since_last_pc_close} days ago</span>
            </p>
         )}
      </div>

      {/* Search & Action */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col md:flex-row gap-4 items-center justify-between">
        <div className="relative w-full md:w-96">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
          <input
            type="text"
            placeholder="Search Categories..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-10 pr-4 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-amber-500/50"
          />
        </div>
      </div>

      {/* Allocation Grids */}
      {isLoading ? (
        <div className="flex justify-center p-12">
          <Loader2 className="w-8 h-8 text-amber-500 animate-spin" />
        </div>
      ) : filteredAllocations.length === 0 ? (
        <div className="text-center py-12 bg-slate-900/50 rounded-xl border border-slate-800 border-dashed">
          <Wallet className="w-12 h-12 text-slate-600 mx-auto mb-3" />
          <h3 className="text-lg font-medium text-white mb-1">No Active Allocations</h3>
          <p className="text-slate-400 text-sm">
            Fund allocations are generated when a Fund Transfer Payment Certificate is approved and closed. No liquid funds are currently sitting on site.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredAllocations.map(alloc => {
            const usagePercent = alloc.allocation_total > 0 
                ? ((alloc.allocation_total - alloc.allocation_remaining) / alloc.allocation_total) * 100 
                : 0;
            
            return (
              <Link 
                href={`/admin/petty-cash/${alloc.category_id}`} 
                key={alloc._id}
                className="block bg-slate-900 border border-slate-800 hover:border-amber-500/50 transition-all duration-300 rounded-xl p-5 group"
              >
                <div className="flex justify-between items-start mb-4">
                   <h3 className="text-white font-medium text-lg leading-tight">
                       {alloc.category_name || "Unknown Category"}
                   </h3>
                   <ArrowRight className="text-slate-600 group-hover:text-amber-500 transition-colors" size={20} />
                </div>
                
                <p className="text-xs text-slate-500 font-mono mb-6">Code: {alloc.category_id}</p>
                
                <div className="space-y-4">
                   <div>
                       <div className="flex justify-between text-xs mb-2">
                           <span className="text-slate-400">Remaining</span>
                           <span className="text-white font-mono font-bold">{formatCurrency(alloc.allocation_remaining)}</span>
                       </div>
                       <div className="w-full bg-slate-950 rounded-full h-2">
                           <div 
                             className={`h-2 rounded-full ${usagePercent > 90 ? 'bg-red-500' : usagePercent > 70 ? 'bg-amber-500' : 'bg-emerald-500'}`}
                             style={{ width: `${Math.min(100, usagePercent)}%` }}
                           />
                       </div>
                   </div>
                   
                   <div className="flex justify-between items-center text-xs">
                       <span className="text-slate-500">Limits Set: <span className="text-slate-300 font-mono">{formatCurrency(alloc.allocation_total)}</span></span>
                   </div>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
