"use client";
import React from "react";
import useSWR from "swr";
import { fetcher } from "@/lib/api";
import api from "@/lib/api";
import { GlassCard } from "@/components/ui/GlassCard";
import { AISummary } from "@/types/api";
import { Brain, RefreshCw, Clock, AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";

interface AISummaryCardProps {
  projectId: string;
}

export function AISummaryCard({ projectId }: AISummaryCardProps) {
  const summaryKey = `/api/projects/${projectId}/ai-summary`;
  const { data: summary, error, isLoading, mutate } = useSWR<AISummary>(
    projectId ? summaryKey : null,
    fetcher,
    {
      revalidateOnFocus: false,
      revalidateIfStale: false,
    }
  );

  const [isRefreshing, setIsRefreshing] = React.useState(false);
  const [refreshError, setRefreshError] = React.useState<string | null>(null);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    setRefreshError(null);
    try {
      await api.post(`/api/projects/${projectId}/ai-summary/refresh`);
      await mutate();
    } catch (err: any) {
      setRefreshError(
        err.response?.data?.detail || "Failed to generate summary. Check API connection."
      );
    } finally {
      setIsRefreshing(false);
    }
  };

  const formatGeneratedAt = (iso: string) => {
    try {
      const d = new Date(iso);
      return d.toLocaleString("en-IN", {
        day: "numeric",
        month: "short",
        hour: "2-digit",
        minute: "2-digit",
        timeZoneName: "short",
      });
    } catch {
      return iso;
    }
  };

  const isMock = summary?.model === "mock";

  return (
    <GlassCard
      className={cn(
        "border-orange-500/10 shadow-xl",
        "relative overflow-hidden"
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-orange-500/10 flex items-center justify-center text-orange-400 border border-orange-500/20">
            <Brain size={18} />
          </div>
          <div>
            <h2 className="text-xs font-bold tracking-tight uppercase text-foreground">
              AI Project Brief
            </h2>
            {summary?.generated_at && (
              <p className="text-[9px] text-muted-foreground flex items-center gap-1 mt-0.5">
                <Clock size={9} />
                {formatGeneratedAt(summary.generated_at)}
              </p>
            )}
          </div>
        </div>
        <button
          onClick={handleRefresh}
          disabled={isRefreshing}
          className="p-1.5 rounded-lg border border-orange-500/20 bg-orange-500/5 text-orange-400 hover:bg-orange-500/15 transition-colors disabled:opacity-40"
          title="Regenerate AI summary"
        >
          <RefreshCw size={13} className={isRefreshing ? "animate-spin" : ""} />
        </button>
      </div>

      {/* Content */}
      {isLoading && (
        <div className="space-y-2 animate-pulse">
          <div className="h-3 bg-muted/40 rounded w-full" />
          <div className="h-3 bg-muted/40 rounded w-5/6" />
          <div className="h-3 bg-muted/40 rounded w-4/6" />
        </div>
      )}

      {!isLoading && error && !summary && (
        <div className="text-center py-4">
          <p className="text-[10px] text-muted-foreground uppercase tracking-widest mb-3">
            No summary generated yet
          </p>
          <button
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="text-[10px] font-bold uppercase tracking-widest text-orange-400 hover:text-orange-300 transition-colors disabled:opacity-40"
          >
            {isRefreshing ? "Generating..." : "Generate Now"}
          </button>
        </div>
      )}

      {!isLoading && summary && (
        <>
          {isMock && (
            <div className="flex items-center gap-1.5 text-[9px] text-amber-500 bg-amber-500/5 border border-amber-500/10 rounded-lg px-2 py-1 mb-3">
              <AlertTriangle size={10} />
              <span className="font-bold uppercase tracking-wider">
                Mock mode — configure OPENAI_API_KEY for AI summaries
              </span>
            </div>
          )}
          <p className="text-[11px] leading-relaxed text-foreground/80 font-medium">
            {summary.summary_text}
          </p>

          {/* Mini stats snapshot */}
          {summary.report_data && (
            <div className="grid grid-cols-3 gap-2 mt-4 pt-4 border-t border-muted">
              <div className="text-center">
                <p className="text-[10px] font-black text-orange-400">
                  {summary.report_data.wo_open}
                </p>
                <p className="text-[8px] text-muted-foreground uppercase tracking-widest">
                  Open WOs
                </p>
              </div>
              <div className="text-center">
                <p className="text-[10px] font-black text-emerald-400">
                  {summary.report_data.pc_closed}
                </p>
                <p className="text-[8px] text-muted-foreground uppercase tracking-widest">
                  Certified PCs
                </p>
              </div>
              <div className="text-center">
                <p
                  className={cn(
                    "text-[10px] font-black",
                    summary.report_data.over_budget_categories.length > 0
                      ? "text-rose-400"
                      : "text-emerald-400"
                  )}
                >
                  {summary.report_data.over_budget_categories.length}
                </p>
                <p className="text-[8px] text-muted-foreground uppercase tracking-widest">
                  Over Budget
                </p>
              </div>
            </div>
          )}
        </>
      )}

      {refreshError && (
        <p className="mt-2 text-[9px] text-rose-400 font-medium">{refreshError}</p>
      )}
    </GlassCard>
  );
}
