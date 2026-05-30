'use client';

import React from "react";
import useSWR from "swr";
import { fetcher } from "@/lib/api";
import { Sparkles, Loader2, AlertCircle, RefreshCw, Brain, BarChart3 } from "lucide-react";
import ReactMarkdown from 'react-markdown';
import { sanitizeAIText } from "@/lib/formatters";
import { GlassCard } from "@/components/ui/GlassCard";
import { cn } from "@/lib/utils";

interface TaskAISummaryProps {
  projectId: string;
  embedded?: boolean;
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

interface TaskAISummaryContentProps {
  data: AISummaryData | undefined;
  isLoading: boolean;
  error: unknown;
  fetchSummary: () => Promise<void>;
  embedded: boolean;
}

function TaskAISummaryContent({
  data,
  isLoading,
  error,
  fetchSummary,
  embedded,
}: TaskAISummaryContentProps) {
  if (isLoading) {
    return (
      <div className={cn(
        "flex flex-col items-center justify-center gap-3 py-12",
        !embedded && "bg-slate-900 border border-slate-800 rounded-xl p-6"
      )}>
        <Loader2 className="animate-spin text-sky-500" size={24} />
        <p className="text-slate-400 text-sm">Generating AI Insights…</p>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className={cn(
        "flex items-center gap-4 min-h-[200px] py-4",
        !embedded && "border border-red-500/10 p-6 rounded-xl bg-red-500/5"
      )}>
        <AlertCircle className="text-rose-500 flex-shrink-0" size={24} />
        <div className="flex-1">
          <h3 className="text-xs font-bold text-rose-400 uppercase tracking-widest mb-1">Synthesis Failure</h3>
          <p className="text-slate-400 text-[10px] leading-relaxed mb-3">
            Unable to analyze task data at this time. Please ensure tasks have valid dates and try again.
          </p>
          <button
            type="button"
            onClick={fetchSummary}
            className="px-3 py-1.5 rounded-lg border border-rose-500/20 bg-rose-500/5 text-rose-400 text-[10px] font-bold uppercase tracking-widest hover:bg-rose-500/10 transition-all flex items-center gap-2"
          >
            <RefreshCw size={10} /> Retry Analysis
          </button>
        </div>
      </div>
    );
  }

  if (!data || !data.metrics || !data.metrics.total) {
    return (
      <div className={cn(
        "flex flex-col items-center justify-center text-center gap-3 min-h-[200px] py-8",
        !embedded && "border border-indigo-500/5 p-6 rounded-xl bg-indigo-500/5"
      )}>
        <Sparkles className="text-indigo-500/20" size={32} />
        <div>
          <p className="text-slate-400 text-[10px] font-bold uppercase tracking-[0.2em]">Ready for Insights</p>
          <p className="text-slate-500 text-[9px] mt-1 max-w-[200px]">AI-powered task analysis will appear here once tasks are added to the project.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full relative group">
      {/* Background Brain Icon (standalone only) */}
      {!embedded && (
        <div className="absolute -top-4 -right-4 p-8 opacity-5 group-hover:opacity-10 transition-opacity pointer-events-none">
          <Brain className="text-sky-500" size={120} />
        </div>
      )}

      {/* Embedded Actions / Sub-header bar */}
      <div className="flex items-center justify-between mb-4 shrink-0 select-none">
        <span className="inline-flex items-center px-2 py-0.5 rounded text-[8px] font-bold uppercase tracking-wider bg-sky-500/10 text-sky-400 border border-sky-500/20">
          EXECUTION LEVEL
        </span>
        <button
          type="button"
          onClick={fetchSummary}
          disabled={isLoading}
          className="p-1 rounded bg-sky-500/5 text-sky-400 hover:bg-sky-500/15 border border-sky-500/20 transition-colors disabled:opacity-40"
          title="Regenerate Insights"
        >
          <RefreshCw size={10} className={isLoading ? "animate-spin" : ""} />
        </button>
      </div>

      {/* Grid Metrics */}
      <div className="grid grid-cols-3 gap-3 mb-5 shrink-0">
        <div className="bg-slate-950/40 border border-white/5 p-3 rounded-xl">
          <span className="text-[8px] text-slate-500 uppercase block font-bold tracking-widest mb-1">Total</span>
          <span className="text-xl font-bold text-white tracking-tighter">{data.metrics.total}</span>
        </div>
        <div className="bg-slate-950/40 border border-white/5 p-3 rounded-xl">
          <span className="text-[8px] text-sky-500 uppercase block font-bold tracking-widest mb-1">Open</span>
          <span className="text-xl font-bold text-white tracking-tighter">{data.metrics.open}</span>
        </div>
        <div className="bg-slate-950/40 border border-white/5 p-3 rounded-xl">
          <span className="text-[8px] text-emerald-500 uppercase block font-bold tracking-widest mb-1">Done</span>
          <span className="text-xl font-bold text-emerald-400 tracking-tighter">{data.metrics.completed}</span>
        </div>
      </div>

      {/* Markdown Text Area */}
      <div className="flex-1 min-h-0 overflow-y-auto custom-scrollbar bg-slate-950/30 border border-white/5 rounded-xl p-4 prose prose-sm dark:prose-invert max-w-none max-h-[160px] pr-2">
        <ReactMarkdown
          components={{
            p: ({ children, ...props }: React.ComponentPropsWithoutRef<'p'>) => <p className="text-[11px] text-slate-300 leading-relaxed font-medium mb-2 last:mb-0" {...props}>{children}</p>,
            strong: ({ children, ...props }: React.ComponentPropsWithoutRef<'span'>) => <span className="font-extrabold text-sky-400" {...props}>{children}</span>,
          }}
        >
          {sanitizeAIText(data.summary_text) || "Synthesizing project velocity and task distribution metrics…"}
        </ReactMarkdown>
      </div>

      {/* Alert / Footer */}
      {data.metrics.overdue > 0 && (
        <div className="mt-4 flex items-center gap-2 bg-rose-500/5 border border-rose-500/10 p-2 rounded-lg shrink-0">
          <AlertCircle className="text-rose-400" size={12} />
          <span className="text-[10px] font-bold text-rose-400 uppercase tracking-widest">
            {data.metrics.overdue} Tasks Overdue
          </span>
        </div>
      )}

      {!embedded && (
        <div className="mt-6 pt-4 border-t border-white/5 flex items-center justify-between shrink-0">
          <span className="text-[8px] font-bold text-slate-600 uppercase tracking-widest">Powered by TAC-AI Core</span>
        </div>
      )}
    </div>
  );
}

export default function TaskAISummary({ projectId, embedded = false }: TaskAISummaryProps) {
  const summaryKey = projectId ? `/api/v1/tasks/ai-summary?project_id=${projectId}` : null;
  const { data, error, isLoading, mutate } = useSWR<AISummaryData>(
    summaryKey,
    fetcher,
    {
      revalidateOnFocus: false,
      revalidateIfStale: false,
      shouldRetryOnError: false,
    }
  );

  const [isRefreshing, setIsRefreshing] = React.useState(false);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      await mutate();
    } catch (err) {
      console.error("AI Summary refresh failed", err);
    } finally {
      setIsRefreshing(false);
    }
  };

  if (embedded) {
    return (
      <TaskAISummaryContent
        data={data}
        isLoading={isLoading || isRefreshing}
        error={error}
        fetchSummary={handleRefresh}
        embedded={embedded}
      />
    );
  }

  return (
    <GlassCard className="border-sky-500/10 relative overflow-hidden group min-h-[200px]">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="size-9 rounded-xl bg-sky-500/10 flex items-center justify-center text-sky-400 border border-sky-500/20">
            <BarChart3 size={18} />
          </div>
          <div>
            <h3 className="text-xs font-bold text-foreground uppercase tracking-tight">AI Progress Insights</h3>
            <p className="text-[9px] text-muted-foreground uppercase tracking-widest mt-0.5 font-medium">Task-Level Analytics</p>
          </div>
        </div>

        <button
          type="button"
          onClick={handleRefresh}
          className="p-1.5 rounded-lg border border-sky-500/20 bg-sky-500/5 text-sky-400 hover:bg-sky-500/15 transition-colors"
          title="Regenerate Insights"
        >
          <RefreshCw size={13} className={isLoading || isRefreshing ? "animate-spin" : ""} />
        </button>
      </div>

      <TaskAISummaryContent
        data={data}
        isLoading={isLoading || isRefreshing}
        error={error}
        fetchSummary={handleRefresh}
        embedded={embedded}
      />
    </GlassCard>
  );
}


