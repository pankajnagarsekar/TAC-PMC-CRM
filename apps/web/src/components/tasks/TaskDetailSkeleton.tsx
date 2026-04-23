"use client";

import React from "react";
import { GlassCard } from "@/components/ui/GlassCard";

export default function TaskDetailSkeleton() {
    return (
        <div className="space-y-6 animate-pulse bg-black min-h-screen p-6">
            {/* Header Skeleton */}
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-slate-800 pb-6">
                <div className="flex items-center gap-4">
                    <div className="w-10 h-10 rounded-full bg-slate-900 border border-slate-800" />
                    <div className="space-y-2">
                        <div className="h-4 w-32 bg-slate-800 rounded" />
                        <div className="h-8 w-64 bg-slate-800 rounded" />
                    </div>
                </div>
                <div className="flex items-center gap-3">
                    <div className="h-10 w-32 bg-slate-800 rounded-lg" />
                    <div className="h-10 w-10 bg-slate-800 rounded-lg" />
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Main Info */}
                <div className="lg:col-span-2 space-y-6">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {[1, 2, 3, 4].map((i) => (
                            <GlassCard key={i} className="p-5 border-slate-800 bg-slate-900/50">
                                <div className="h-3 w-20 bg-slate-800 rounded mb-4" />
                                <div className="flex items-center gap-3">
                                    <div className="h-10 w-10 rounded-full bg-slate-800" />
                                    <div className="space-y-1 flex-1">
                                        <div className="h-5 w-3/4 bg-slate-800 rounded" />
                                        <div className="h-3 w-1/2 bg-slate-800 rounded" />
                                    </div>
                                </div>
                            </GlassCard>
                        ))}
                    </div>

                    <GlassCard className="p-8 border-slate-800 bg-slate-900/50">
                        <div className="h-6 w-48 bg-slate-800 rounded mb-6" />
                        <div className="space-y-3">
                            <div className="h-4 w-full bg-slate-800 rounded" />
                            <div className="h-4 w-full bg-slate-800 rounded" />
                            <div className="h-4 w-3/4 bg-slate-800 rounded" />
                        </div>
                        <div className="mt-8 pt-8 border-t border-slate-800/50 grid grid-cols-2 gap-8">
                            <div className="space-y-2">
                                <div className="h-3 w-16 bg-slate-800 rounded" />
                                <div className="h-4 w-32 bg-slate-800 rounded" />
                            </div>
                            <div className="space-y-2">
                                <div className="h-3 w-16 bg-slate-800 rounded" />
                                <div className="h-4 w-32 bg-slate-800 rounded" />
                            </div>
                        </div>
                    </GlassCard>
                </div>

                {/* Sidebar */}
                <div className="space-y-6">
                    <GlassCard className="p-6 border-slate-800 bg-slate-900/50">
                        <div className="h-4 w-32 bg-slate-800 rounded mb-4" />
                        <div className="space-y-4">
                            <div className="h-20 w-full bg-slate-800 rounded-xl" />
                            <div className="h-4 w-full bg-slate-800 rounded" />
                            <div className="h-4 w-2/3 bg-slate-800 rounded" />
                        </div>
                    </GlassCard>

                    <GlassCard className="p-6 border-slate-800 bg-slate-900/50">
                        <div className="h-4 w-32 bg-slate-800 rounded mb-4" />
                        <div className="space-y-3">
                            <div className="h-12 w-full bg-slate-800 rounded-lg" />
                            <div className="h-12 w-full bg-slate-800 rounded-lg" />
                        </div>
                    </GlassCard>
                </div>
            </div>
        </div>
    );
}
