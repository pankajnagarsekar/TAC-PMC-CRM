"use client";

import React, { useMemo } from "react";
import { format, parseISO } from "date-fns";
import { Activity, AlertCircle } from "lucide-react";

interface HeatmapDay {
  date: string;
  utilization_percent: number;
  project_ids: string[];
}

interface ResourceStats {
  resource_id: string;
  resource_name: string;
  daily_utilization: HeatmapDay[];
  total_availability_hours: number;
}

export default function ResourceHeatmap({ data }: { data: ResourceStats[] }) {
  // 1. Get unique days for header
  const days = useMemo(() => {
    if (!data.length) return [];
    return data[0].daily_utilization.map(d => d.date);
  }, [data]);

  const getCellColor = (percent: number) => {
    if (percent === 0) return "bg-slate-900 border-white/5 opacity-20";
    if (percent <= 50) return "bg-emerald-500/20 border-emerald-500/30 text-emerald-400";
    if (percent <= 80) return "bg-sky-500/20 border-sky-500/30 text-sky-400";
    if (percent <= 100) return "bg-amber-500/20 border-amber-500/30 text-amber-400";
    return "bg-rose-500/30 border-rose-500/50 text-rose-400 animate-pulse"; // Over-allocation
  };

  return (
    <div className="bg-slate-950 border border-white/5 rounded-[28px] p-8 shadow-2xl overflow-hidden">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h3 className="text-sm font-black uppercase tracking-[0.2em] text-white/45 flex items-center gap-2">
            <Activity className="w-4 h-4" /> Global Resource Heatmap
          </h3>
          <p className="mt-1 text-[10px] uppercase tracking-[0.18em] text-slate-500">
            Daily utilization tracking across all active projects
          </p>
        </div>
      </div>

      <div className="overflow-x-auto custom-scrollbar">
        <table className="w-full">
          <thead>
            <tr>
              <th className="sticky left-0 bg-slate-950 z-20 w-48 text-left py-2 text-[10px] font-black uppercase tracking-[0.2em] text-slate-500">
                Resource
              </th>
              {days.map(d => (
                <th key={d} className="min-w-[40px] px-1 py-2 text-center text-[10px] font-black uppercase tracking-[0.1em] text-slate-500 border-l border-white/5">
                  {format(parseISO(d), "dd")}
                  <div className="text-[8px] font-normal">{format(parseISO(d), "MMM")}</div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {data.map(r => (
              <tr key={r.resource_id} className="group">
                <td className="sticky left-0 bg-slate-950 z-20 py-4 pr-4">
                  <div className="flex flex-col">
                    <span className="text-xs font-bold text-white group-hover:text-sky-400 transition-colors truncate">
                      {r.resource_name}
                    </span>
                    <span className="text-[9px] font-mono text-slate-600">
                      {r.resource_id.slice(-6)}
                    </span>
                  </div>
                </td>
                {r.daily_utilization.map(d => (
                  <td key={d.date} className="px-0.5 py-2 border-l border-white/[0.03]">
                    <div
                      className={`h-8 rounded-lg border flex items-center justify-center text-[9px] font-bold transition-all duration-300 hover:scale-110 hover:z-10 ${getCellColor(d.utilization_percent)}`}
                      title={`${d.date}: ${d.utilization_percent}% (${d.project_ids.length} projects)`}
                    >
                      {d.utilization_percent > 100 && <AlertCircle className="w-2 h-2 mr-0.5" />}
                      {d.utilization_percent > 0 ? `${d.utilization_percent}%` : ""}
                    </div>
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Legend */}
      <div className="mt-8 flex items-center flex-wrap gap-4 border-t border-white/5 pt-4 text-[9px] font-black uppercase tracking-widest text-slate-500">
        <div className="flex items-center gap-1.5">
          <div className="w-3 h-3 rounded bg-emerald-500/20 border border-emerald-500/30" />
          <span>Low Load</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-3 h-3 rounded bg-sky-500/20 border border-sky-500/30" />
          <span>Optimum</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-3 h-3 rounded bg-amber-500/20 border border-amber-500/30" />
          <span>Full Cap</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-3 h-3 rounded bg-rose-500/30 border border-rose-500/50 animate-pulse" />
          <span className="text-rose-400">Over-allocated</span>
        </div>
      </div>
    </div>
  );
};
