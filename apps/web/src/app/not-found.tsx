"use client";
import Link from "next/link";
import { MoveLeft, LayoutGrid, Ghost, Compass } from "lucide-react";

export default function NotFound() {
    return (
        <div className="min-h-screen bg-[#020617] flex items-center justify-center p-6 relative overflow-hidden">
            {/* Background Orbs */}
            <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-indigo-600/10 rounded-full blur-[120px] -z-10" />
            <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-orange-600/10 rounded-full blur-[120px] -z-10" />

            <div className="max-w-2xl w-full text-center space-y-12 animate-in fade-in zoom-in duration-1000">
                <div className="relative inline-block">
                    <div className="p-6 bg-slate-900/40 border border-white/5 rounded-[2.5rem] backdrop-blur-xl shadow-2xl relative z-10">
                        <Compass size={64} className="text-orange-500 animate-[spin_10s_linear_infinite]" />
                    </div>
                    <div className="absolute inset-0 bg-orange-500/20 rounded-[2.5rem] blur-2xl -z-10 animate-pulse" />
                </div>

                <div className="space-y-4">
                    <div className="flex flex-col items-center">
                        <span className="text-[10px] font-black text-orange-500 uppercase tracking-[0.4em] mb-4">Error Code // 404</span>
                        <h1 className="text-[120px] font-black text-white tracking-tighter leading-none select-none">LOST</h1>
                    </div>
                    <h2 className="text-2xl font-bold text-slate-200 tracking-tight">Coordinates Not Found In Registry</h2>
                    <p className="text-slate-500 max-w-md mx-auto text-sm leading-relaxed">
                        The architectural sector you are attempting to access does not exist in the current project scope. It may have been decommissioned or moved to a restricted clearance level.
                    </p>
                </div>

                <div className="flex flex-col sm:flex-row items-center justify-center gap-6">
                    <Link
                        href="/admin/dashboard"
                        className="w-full sm:w-auto px-10 py-4 bg-orange-600 hover:bg-orange-500 text-white rounded-2xl font-black text-xs uppercase tracking-[0.2em] transition-all shadow-2xl shadow-orange-900/40 active:scale-95 flex items-center justify-center gap-3 border border-white/10 group"
                    >
                        <LayoutGrid size={16} className="group-hover:rotate-90 transition-transform duration-500" />
                        Command Center
                    </Link>
                    <button
                        onClick={() => window.history.back()}
                        className="w-full sm:w-auto px-10 py-4 bg-slate-900/80 hover:bg-slate-800 text-slate-400 hover:text-white rounded-2xl font-black text-xs uppercase tracking-[0.2em] transition-all border border-white/5 backdrop-blur-md active:scale-95 flex items-center justify-center gap-3 group"
                    >
                        <MoveLeft size={16} className="group-hover:-translate-x-1 transition-transform" />
                        Previous Sector
                    </button>
                </div>

                <div className="pt-16">
                    <div className="inline-flex items-center gap-3 px-4 py-1.5 bg-white/5 border border-white/5 rounded-full backdrop-blur-sm">
                        <div className="flex gap-1">
                            <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                            <div className="w-1.5 h-1.5 rounded-full bg-emerald-500/50" />
                            <div className="w-1.5 h-1.5 rounded-full bg-emerald-500/20" />
                        </div>
                        <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest leading-none">Security Clearance: AUTHENTICATED</span>
                    </div>
                </div>
            </div>
        </div>
    );
}

