'use client';

import React, { useState, useEffect } from "react";
import { Sparkles, Loader2, AlertCircle, RefreshCw } from "lucide-react";
import api from "@/lib/api";

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

  const fetchSummary = async () => {
    setIsLoading(true);
    try {
      const res = await api.get<AISummaryData>(`/api/v1/tasks/ai-summary?project_id=${projectId}`);
      // res.data will be the object returned by GeneralResponse.data
      setData(res.data);
      setError(null);
    } catch (err) {
      console.error("AI Summary fetch failed", err);
      setError("Unable to generate AI summary.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (projectId) fetchSummary();
  }, [projectId]);

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
      <div className="bg-slate-900 border border-red-900/30 rounded-xl p-6 flex items-center gap-4">
        <AlertCircle className="text-red-500 flex-shrink-0" size={24} />
        <div className="flex-1">
          <p className="text-red-400 text-sm">{error}</p>
          <button 
            onClick={fetchSummary}
            className="text-xs text-blue-500 hover:underline mt-1 flex items-center gap-1"
          >
            <RefreshCw size={10} /> Try again
          </button>
        </div>
      </div>
    );
  }

  if (!data || !data.metrics) return null;

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl relative overflow-hidden group">
      <div className="absolute top-0 right-0 p-3 opacity-20 group-hover:opacity-40 transition-opacity">
        <Sparkles className="text-blue-500" size={48} />
      </div>

      <div className="flex items-center gap-3 mb-4">
        <div className="w-8 h-8 rounded-lg bg-blue-600/20 flex items-center justify-center">
          <Sparkles className="text-blue-500" size={18} />
        </div>
        <h3 className="text-lg font-bold text-white tracking-tight">AI Progress Insights</h3>
      </div>

      <div className="flex flex-wrap gap-4 mb-6">
        <div className="bg-slate-950 border border-slate-800 px-3 py-1.5 rounded-lg">
          <span className="text-[10px] text-slate-500 uppercase block font-bold leading-none">Total</span>
          <span className="text-lg font-bold text-white leading-none">{data.metrics.total}</span>
        </div>
        <div className="bg-slate-950 border border-slate-800 px-3 py-1.5 rounded-lg">
          <span className="text-[10px] text-blue-500 uppercase block font-bold leading-none">Open</span>
          <span className="text-lg font-bold text-white leading-none">{data.metrics.open}</span>
        </div>
        <div className="bg-slate-950 border border-slate-800 px-3 py-1.5 rounded-lg">
          <span className="text-[10px] text-emerald-500 uppercase block font-bold leading-none">Done</span>
          <span className="text-lg font-bold text-white leading-none tracking-tight">{data.metrics.completed}</span>
        </div>
      </div>

      <div className="bg-slate-950/50 border border-slate-800/50 rounded-lg p-4">
        <p className="text-sm text-slate-300 leading-relaxed italic">
          "{data.summary_text || "The project is currently proceeding as scheduled with early-stage milestones met."}"
        </p>
      </div>

      <div className="mt-4 pt-4 border-t border-slate-800 flex items-center justify-between">
        <span className="text-[10px] font-bold text-slate-600 uppercase">Powered by TAC-AI Agent</span>
        <button 
          onClick={fetchSummary}
          className="text-xs font-bold text-slate-500 hover:text-white transition-colors flex items-center gap-1"
        >
          <RefreshCw size={12} /> Regenerate
        </button>
      </div>
    </div>
  );
}

