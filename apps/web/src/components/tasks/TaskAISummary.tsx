'use client';

import React, { useState, useEffect, useCallback } from "react";
import { Sparkles, Loader2, AlertCircle, RefreshCw, Brain } from "lucide-react";
import api from "@/lib/api";
import ReactMarkdown from 'react-markdown';
import { GlassCard } from "@/components/ui/GlassCard";

interface TaskAISummaryProps {
  projectId: string;
}

interface AISummaryData {
  summary_text: string;
  metrics: {
    total: number;
    open: number;
    overdue: number;
    completed: number;
    status_distribution: Record<string, number>;
    top_assignees: Record<string, number>;
  };
}

export default function TaskAISummary({ projectId }: TaskAISummaryProps) {
  const [data, setData] = useState<AISummaryData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSummary = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await api.get<AISummaryData>(`/api/v1/tasks/ai-summary?project_id=${projectId}`);
      // res.data will be the object returned by GeneralResponse.data
      setData(res.data);
      setError(null);
    } catch (err: unknown) {
      console.error("AI Summary fetch failed", err);
      setError("Unable to generate AI summary.");
    } finally {
      setIsLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    if (projectId) fetchSummary();
  }, [projectId, fetchSummary]);

  if (isLoading) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 flex flex-col items-center justify-center gap-3">
        <Loader2 className="animate-spin text-blue-500" size={24} />
        <p className="text-slate-400 text-sm">Generating AI Insights...</p>
      </div>
    );
  }

  if (error) {
    return (
      <GlassCard className="border-red-500/10 p-6 flex items-center gap-4 min-h-[200px]">
        <AlertCircle className="text-rose-500 flex-shrink-0" size={24} />
        <div className="flex-1">
          <h3 className="text-xs font-bold text-rose-400 uppercase tracking-widest mb-1">Synthesis Failure</h3>
          <p className="text-slate-400 text-[10px] leading-relaxed mb-3">
            Unable to analyze task data at this time. Please ensure tasks have valid dates and try again.
          </p>
          <button
            onClick={fetchSummary}
            className="px-3 py-1.5 rounded-lg border border-rose-500/20 bg-rose-500/5 text-rose-400 text-[10px] font-bold uppercase tracking-widest hover:bg-rose-500/10 transition-all flex items-center gap-2"
          >
            <RefreshCw size={10} /> Retry Analysis
          </button>
        </div>
      </GlassCard>
    );
  }

  if (!data || !data.metrics || !data.metrics.total) {
    return (
      <GlassCard className="border-indigo-500/5 p-6 flex flex-col items-center justify-center text-center gap-3 min-h-[200px]">
        <Sparkles className="text-indigo-500/20" size={32} />
        <div>
          <p className="text-slate-400 text-[10px] font-bold uppercase tracking-[0.2em]">Ready for Insights</p>
          <p className="text-slate-500 text-[9px] mt-1 max-w-[200px]">AI-powered task analysis will appear here once tasks are added to the project.</p>
        </div>
      </GlassCard>
    );
  }

  return (
    <GlassCard className="border-blue-500/10 relative overflow-hidden group min-h-[200px]">
      <div className="absolute -top-4 -right-4 p-8 opacity-5 group-hover:opacity-10 transition-opacity">
        <Brain className="text-blue-500" size={120} />
      </div>

      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-blue-500/10 flex items-center justify-center text-blue-400 border border-blue-500/20">
            <Sparkles size={18} />
          </div>
          <div>
            <h3 className="text-xs font-bold text-foreground uppercase tracking-tight">AI Progress Insights</h3>
            <p className="text-[9px] text-muted-foreground uppercase tracking-widest mt-0.5 font-medium">Task-Level Analytics</p>
          </div>
        </div>

        <button
          onClick={fetchSummary}
          className="p-1.5 rounded-lg border border-blue-500/20 bg-blue-500/5 text-blue-400 hover:bg-blue-500/15 transition-colors"
          title="Regenerate Insights"
        >
          <RefreshCw size={13} className={isLoading ? "animate-spin" : ""} />
        </button>
      </div>

      <div className="grid grid-cols-3 gap-3 mb-6">
        <div className="bg-slate-950/40 border border-white/5 p-3 rounded-xl">
          <span className="text-[8px] text-slate-500 uppercase block font-bold tracking-widest mb-1">Total</span>
          <span className="text-xl font-bold text-white tracking-tighter">{data.metrics.total}</span>
        </div>
        <div className="bg-slate-950/40 border border-white/5 p-3 rounded-xl">
          <span className="text-[8px] text-blue-500 uppercase block font-bold tracking-widest mb-1">Open</span>
          <span className="text-xl font-bold text-white tracking-tighter">{data.metrics.open}</span>
        </div>
        <div className="bg-slate-950/40 border border-white/5 p-3 rounded-xl">
          <span className="text-[8px] text-emerald-500 uppercase block font-bold tracking-widest mb-1">Done</span>
          <span className="text-xl font-bold text-emerald-400 tracking-tighter">{data.metrics.completed}</span>
        </div>
      </div>

      <div className="bg-slate-950/30 border border-white/5 rounded-xl p-4 prose prose-sm dark:prose-invert max-w-none">
        <ReactMarkdown
          components={{
            p: ({ children, ...props }: React.ComponentPropsWithoutRef<'p'>) => <p className="text-[11px] text-slate-300 leading-relaxed font-medium mb-2 last:mb-0" {...props}>{children}</p>,
            strong: ({ children, ...props }: React.ComponentPropsWithoutRef<'span'>) => <span className="font-extrabold text-blue-400" {...props}>{children}</span>,
          }}
        >
          {(data.summary_text || "").replace(/\\n/g, '\n') || "Synthesizing project velocity and task distribution metrics..."}
        </ReactMarkdown>
      </div>

      {data.metrics.overdue > 0 && (
        <div className="mt-4 flex items-center gap-2 bg-rose-500/5 border border-rose-500/10 p-2 rounded-lg">
          <AlertCircle className="text-rose-400" size={12} />
          <span className="text-[10px] font-bold text-rose-400 uppercase tracking-widest">
            {data.metrics.overdue} Tasks Overdue
          </span>
        </div>
      )}

      <div className="mt-6 pt-4 border-t border-white/5 flex items-center justify-between">
        <span className="text-[8px] font-bold text-slate-600 uppercase tracking-widest">Powered by TAC-AI Core</span>
      </div>
    </GlassCard>
  );
}

