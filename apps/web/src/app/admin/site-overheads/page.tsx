"use client";

import React from "react";
import { Building2, Plus, Filter, Download } from "lucide-react";
import FinancialGrid from "@/components/ui/FinancialGrid";

export default function SiteOverheadsPage() {
    return (
        <div className="p-6 space-y-6 animate-in fade-in duration-500">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div>
                    <h1 className="text-2xl font-bold text-white flex items-center gap-3">
                        <Building2 className="text-orange-500" />
                        Site Overheads
                    </h1>
                    <p className="text-slate-500 text-sm mt-1">Manage site-specific indirect costs and fixed expenses.</p>
                </div>

                <div className="flex gap-3">
                    <button className="px-4 py-2 bg-white/5 border border-white/10 hover:bg-white/10 text-white rounded-xl text-xs font-bold uppercase tracking-widest transition-all flex items-center gap-2">
                        <Filter size={14} /> Filter
                    </button>
                    <button className="px-5 py-2 bg-orange-600 hover:bg-orange-500 text-white rounded-xl text-xs font-bold uppercase tracking-widest transition-all shadow-lg shadow-orange-500/20 flex items-center gap-2">
                        <Plus size={14} /> Add Transaction
                    </button>
                </div>
            </div>

            <div className="bg-slate-950/20 border border-white/5 rounded-[2rem] p-8 h-[600px] flex items-center justify-center">
                <div className="text-center space-y-4">
                    <div className="w-16 h-16 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center mx-auto">
                        <Building2 className="text-slate-500" size={32} />
                    </div>
                    <div>
                        <h3 className="text-white font-bold">No Records Found</h3>
                        <p className="text-slate-500 text-sm">Site overhead transactions will appear here once added.</p>
                    </div>
                </div>
            </div>
        </div>
    );
}
