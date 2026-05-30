"use client";
import React from "react";
import useSWR from "swr";
import { fetcher } from "@/lib/api";
import api from "@/lib/api";
import { GlassCard } from "@/components/ui/GlassCard";
import { AISummary } from "@/types/api";
import { Brain, RefreshCw, Clock, AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";
import ReactMarkdown from 'react-markdown';
import { sanitizeAIText } from "@/lib/formatters";

interface AISummaryCardProps {
  projectId: string;
  embedded?: boolean;
}

const formatGeneratedAt = (iso: string) => {
  try {
    const d = new Date(iso);
    return d.toLocaleString("en-IN", {
      day: "numeric",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
};

interface AISummaryContentProps {
  isLoading: boolean;
  error: unknown;
  summary: AISummary | undefined;
  isRefreshing: boolean;
  refreshError: string | null;
  handleRefresh: () => Promise<void>;
  isMock: boolean;
}

function AISummaryContent({
  isLoading,
  error,
  summary,
  isRefreshing,
  refreshError,
  handleRefresh,
  isMock,
}: AISummaryContentProps) {
  return (
    <div className="flex flex-col h-full">
      {/* Embedded Actions / Sub-header bar */}
      <div className="flex items-center justify-between mb-4 shrink-0 select-none">
        <span className="inline-flex items-center px-2 py-0.5 rounded text-[8px] font-bold uppercase tracking-wider bg-orange-500/10 text-orange-400 border border-orange-500/20">
          PROJECT LEVEL
        </span>
        <div className="flex items-center gap-3">
          {summary?.generated_at && (
            <span className="text-[9px] text-muted-foreground flex items-center gap-1 font-medium">
              <Clock size={9} />
              {formatGeneratedAt(summary.generated_at)}
            </span>
          )}
          <button
            type="button"
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="p-1 rounded bg-orange-500/5 text-orange-400 hover:bg-orange-500/15 border border-orange-500/20 transition-colors disabled:opacity-40"
            title="Regenerate AI summary"
          >
            <RefreshCw size={10} className={isRefreshing ? "animate-spin" : ""} />
          </button>
        </div>
      </div>

      {/* Content body */}
      {isLoading && (
        <div className="space-y-2 animate-pulse py-2">
          <div className="h-3 bg-muted/40 rounded w-full" />
          <div className="h-3 bg-muted/40 rounded w-5/6" />
          <div className="h-3 bg-muted/40 rounded w-4/6" />
        </div>
      )}

      {!isLoading && !!error && !summary && (
        <div className="text-center py-8">
          <p className="text-[10px] text-muted-foreground tracking-widest mb-3">
            Your AI project brief will appear here.
          </p>
          <button
            type="button"
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="text-[10px] font-bold uppercase tracking-widest text-orange-400 hover:text-orange-300 transition-colors disabled:opacity-40"
          >
            {isRefreshing ? "Generating..." : "Generate Now"}
          </button>
        </div>
      )}

      {!isLoading && summary && (
        <div className="flex-1 flex flex-col justify-between">
          <div>
            {isMock && (
              <div className="flex items-center gap-1.5 text-[9px] text-amber-500 bg-amber-500/5 border border-amber-500/10 rounded-lg px-2 py-1 mb-3">
                <AlertTriangle size={10} />
                <span className="font-bold uppercase tracking-wider">
                  Mock mode: configure OPENAI_API_KEY for AI summaries
                </span>
              </div>
            )}
            <div className="prose prose-sm dark:prose-invert max-w-none text-[11px] leading-relaxed text-foreground/80 font-medium max-h-[200px] overflow-y-auto custom-scrollbar pr-1">
              <ReactMarkdown
                components={{
                  p: (props) => <p className="mb-2 last:mb-0" {...props} />,
                  strong: (props) => <span className="font-black text-orange-400" {...props} />,
                  ul: (props) => <ul className="list-disc pl-4 mb-2 space-y-1" {...props} />,
                  li: (props) => <li {...props} />,
                }}
              >
                {sanitizeAIText(summary.summary_text)}
              </ReactMarkdown>
            </div>
          </div>

          {/* Mini stats snapshot */}
          {summary.report_data && (
            <div className="grid grid-cols-3 gap-2 mt-4 pt-4 border-t border-border/40 shrink-0">
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
        </div>
      )}

      {refreshError && (
        <p className="mt-2 text-[9px] text-rose-400 font-medium shrink-0">{refreshError}</p>
      )}
    </div>
  );
}

export function AISummaryCard({ projectId, embedded = false }: AISummaryCardProps) {
  const summaryKey = `/api/v1/reports/${projectId}/ai-summary`;
  const { data: summary, error, isLoading, mutate } = useSWR<AISummary>(
    projectId ? summaryKey : null,
    fetcher,
    {
      revalidateOnFocus: false,
      revalidateIfStale: false,
      shouldRetryOnError: false, // Prevent request storms on API errors
    }
  );

  const [isRefreshing, setIsRefreshing] = React.useState(false);
  const [refreshError, setRefreshError] = React.useState<string | null>(null);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    setRefreshError(null);
    try {
      await api.post(`/api/v1/reports/${projectId}/ai-summary/refresh`);
      await mutate();
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      // Never expose internal error details to users — log for debugging only
      console.error("[AISummaryCard] Refresh failed:", error.response?.data?.detail);
      setRefreshError("AI summary temporarily unavailable. Please try again later.");
    } finally {
      setIsRefreshing(false);
    }
  };

  const isMock = summary?.model === "mock";

  if (embedded) {
    return (
      <AISummaryContent
        isLoading={isLoading}
        error={error}
        summary={summary}
        isRefreshing={isRefreshing}
        refreshError={refreshError}
        handleRefresh={handleRefresh}
        isMock={isMock}
      />
    );
  }

  return (
    <GlassCard
      className={cn(
        "border-orange-500/10 shadow-xl",
        "relative overflow-hidden"
      )}
    >
      {/* Header (Standalone layout) */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="size-9 rounded-xl bg-orange-500/10 flex items-center justify-center text-orange-400 border border-orange-500/20">
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
          type="button"
          onClick={handleRefresh}
          disabled={isRefreshing}
          className="p-1.5 rounded-lg border border-orange-500/20 bg-orange-500/5 text-orange-400 hover:bg-orange-500/15 transition-colors disabled:opacity-40"
          title="Regenerate AI summary"
        >
          <RefreshCw size={13} className={isRefreshing ? "animate-spin" : ""} />
        </button>
      </div>

      <AISummaryContent
        isLoading={isLoading}
        error={error}
        summary={summary}
        isRefreshing={isRefreshing}
        refreshError={refreshError}
        handleRefresh={handleRefresh}
        isMock={isMock}
      />
    </GlassCard>
  );
}
