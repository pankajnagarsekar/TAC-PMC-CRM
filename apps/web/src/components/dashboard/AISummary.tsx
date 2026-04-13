'use client';

import { useState, useEffect } from 'react';
import { ChevronDown, ChevronUp, RotateCcw } from 'lucide-react';

interface AISummaryProps {
  projectId: string;
  type?: 'schedule' | 'financial' | 'resources';
  title?: string;
  description?: string;
}

export function AISummary({
  projectId,
  type = 'schedule',
  title = 'AI Summary',
  description = 'Executive analysis powered by AI',
}: AISummaryProps) {
  const [isExpanded, setIsExpanded] = useState(true);
  const [text, setText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchSummary = async () => {
    setIsLoading(true);
    setError(null);
    setText('');

    try {
      const response = await fetch(
        `/api/v1/reports/${projectId}/ai-summary/stream/${type}`,
        {
          method: 'GET',
          headers: {
            'Content-Type': 'text/event-stream',
            'X-Project-Id': projectId,
          },
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch summary: ${response.statusText}`);
      }

      if (!response.body) {
        throw new Error('No response body');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Progressive word reveal (stream contains words separated by spaces)
        setText((prev) => prev + buffer);
        buffer = '';
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      console.error('Summary fetch error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchSummary();
  }, [projectId, type]);

  const titleMap: Record<string, string> = {
    schedule: '📅 Schedule Health',
    financial: '💰 Financial Status',
    resources: '👥 Resource Allocation',
  };

  return (
    <div className="rounded-lg border border-teal-500/20 bg-gradient-to-br from-slate-900/40 to-slate-800/20 backdrop-blur-sm p-4 shadow-lg">
      {/* Header */}
      <div className="flex items-center justify-between gap-3 mb-4">
        <div className="flex-1">
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">
            {titleMap[type] || title}
          </h3>
          <p className="text-xs text-slate-400 mt-1">{description}</p>
        </div>
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="p-1.5 hover:bg-teal-500/10 rounded transition-colors"
          aria-label="Toggle"
        >
          {isExpanded ? (
            <ChevronUp className="w-4 h-4 text-teal-400" />
          ) : (
            <ChevronDown className="w-4 h-4 text-teal-400" />
          )}
        </button>
      </div>

      {/* Content */}
      {isExpanded && (
        <div className="space-y-3">
          {isLoading && !text && (
            <div className="flex items-center gap-2 text-sm text-slate-400">
              <div className="animate-spin rounded-full h-4 w-4 border border-teal-500/30 border-t-teal-500" />
              Generating AI summary...
            </div>
          )}

          {error && (
            <div className="text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded px-3 py-2">
              {error}
            </div>
          )}

          {text && (
            <p className="text-sm text-slate-200 leading-relaxed font-light">
              {text}
              {isLoading && <span className="animate-pulse">▌</span>}
            </p>
          )}

          {!isLoading && !text && !error && (
            <p className="text-sm text-slate-400 italic">No summary available</p>
          )}

          {/* Regenerate Button */}
          <button
            onClick={fetchSummary}
            disabled={isLoading}
            className="mt-3 flex items-center gap-2 px-3 py-1.5 text-xs font-medium text-teal-400 hover:text-teal-300 hover:bg-teal-500/10 border border-teal-500/30 hover:border-teal-500/50 rounded transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <RotateCcw className="w-3 h-3" />
            Regenerate
          </button>
        </div>
      )}
    </div>
  );
}
