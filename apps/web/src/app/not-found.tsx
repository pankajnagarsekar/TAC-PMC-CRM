"use client";

import Link from "next/link";
import { MoveLeft, LayoutGrid, Ghost } from "lucide-react";

export default function NotFound() {
    return (
        <div className="min-h-screen bg-[#020617] flex items-center justify-center p-6 font-sans">
            <div className="relative max-w-lg w-full text-center space-y-10 animate-in fade-in zoom-in duration-700">

                {/* Background Glow */}
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-orange-600/10 rounded-full blur-[120px] -z-10" />

                <div className="space-y-4">
                    <div className="inline-flex p-4 bg-orange-500/10 border border-orange-500/20 rounded-3xl mb-4">
                        <Ghost size={48} className="text-orange-500 animate-bounce" />
                    </div>
                    <h1 className="text-8xl font-black text-white tracking-tighter">404</h1>
                    <h2 className="text-2xl font-bold text-slate-200">Asset Not Located</h2>
                    <p className="text-slate-500 max-w-sm mx-auto">
                        The coordinates you requested do not exist in the TAC-PMC-CRM registry. It may have been moved or decommissioned.
                    </p>
                </div>

                <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                    <Link
                        href="/admin/dashboard"
                        className="w-full sm:w-auto px-8 py-4 bg-orange-600 hover:bg-orange-500 text-white rounded-2xl font-black text-xs uppercase tracking-[0.2em] transition-all shadow-xl shadow-orange-900/20 active:scale-95 flex items-center justify-center gap-3 border border-white/10"
                    >
                        <LayoutGrid size={16} />
                        Return to Command
                    </Link>
                    <button
                        onClick={() => window.history.back()}
                        className="w-full sm:w-auto px-8 py-4 bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-white rounded-2xl font-black text-xs uppercase tracking-[0.2em] transition-all border border-white/5 active:scale-95 flex items-center justify-center gap-3"
                    >
                        <MoveLeft size={16} />
                        Previous Sector
                    </button>
                </div>

                <div className="pt-10">
                    <div className="inline-flex items-center gap-2 px-3 py-1 bg-white/5 border border-white/5 rounded-full">
                        <div className="w-1.5 h-1.5 rounded-full bg-orange-500 animate-pulse" />
                        <span className="text-[10px] font-black text-slate-600 uppercase tracking-widest leading-none">System Integrity Nominal</span>
                    </div>
                </div>
            </div>
        </div>
    );
}
