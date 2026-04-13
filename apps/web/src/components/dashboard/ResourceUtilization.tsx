"use client";

import React, { useMemo } from "react";
import { AlertCircle, Users } from "lucide-react";

interface ResourceMetrics {
  name: string;
  allocated_percent: number;
  available_hours: number;
  allocated_hours: number;
  overallocated: boolean;
}

interface RoleMetrics {
  role: string;
  total_allocated_percent: number;
  resource_count: number;
  overallocated_resources: number;
}

interface ResourceUtilizationProps {
  by_resource?: ResourceMetrics[];
  by_role?: RoleMetrics[];
  title?: string;
}

export default function ResourceUtilization({
  by_resource = [],
  by_role = [],
  title = "Resource Utilization",
}: ResourceUtilizationProps) {
  const resourceHeatmap = useMemo(
    () =>
      by_resource.map((resource) => ({
        ...resource,
        color: resource.overallocated
          ? "bg-red-500/20 text-red-400 border-red-500/30"
          : resource.allocated_percent > 80
            ? "bg-yellow-500/20 text-yellow-400 border-yellow-500/30"
            : resource.allocated_percent > 50
              ? "bg-blue-500/20 text-blue-400 border-blue-500/30"
              : "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
      })),
    [by_resource]
  );

  const roleHeatmap = useMemo(
    () =>
      by_role.map((role) => ({
        ...role,
        color: role.overallocated_resources > 0
          ? "bg-red-500/20 text-red-400 border-red-500/30"
          : role.total_allocated_percent > 80
            ? "bg-yellow-500/20 text-yellow-400 border-yellow-500/30"
            : "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
      })),
    [by_role]
  );

  const overallocatedCount = resourceHeatmap.filter((r) => r.overallocated).length;

  return (
    <div className="bg-slate-900/50 border border-white/10 rounded-lg p-6 backdrop-blur space-y-6">
      <div>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">
            <Users className="w-4 h-4" />
            {title}
          </h3>
          {overallocatedCount > 0 && (
            <div className="flex items-center gap-2 px-2 py-1 bg-red-500/10 border border-red-500/30 rounded text-xs text-red-400">
              <AlertCircle className="w-3 h-3" />
              {overallocatedCount} over-allocated
            </div>
          )}
        </div>

        {/* By Resource Grid */}
        {resourceHeatmap.length > 0 && (
          <div className="space-y-2 mb-6">
            <p className="text-xs text-slate-400 uppercase tracking-wider">By Resource</p>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {resourceHeatmap.map((resource) => (
                <div
                  key={resource.name}
                  className={`border rounded-lg p-3 transition-all ${resource.color}`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium truncate">{resource.name}</span>
                    <span className="text-xs font-bold whitespace-nowrap ml-2">
                      {resource.allocated_percent.toFixed(0)}%
                    </span>
                  </div>
                  <div className="text-xs opacity-80">
                    {resource.allocated_hours.toFixed(1)}h / {resource.available_hours.toFixed(1)}h
                  </div>
                  {resource.overallocated && (
                    <div className="mt-2 pt-2 border-t border-current/20 text-xs font-semibold">
                      ⚠️ Over capacity
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* By Role Summary */}
        {roleHeatmap.length > 0 && (
          <div className="space-y-2">
            <p className="text-xs text-slate-400 uppercase tracking-wider">By Role</p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {roleHeatmap.map((role) => (
                <div
                  key={role.role}
                  className={`border rounded-lg p-3 transition-all ${role.color}`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium">{role.role}</span>
                    <span className="text-xs font-bold">{role.total_allocated_percent.toFixed(0)}%</span>
                  </div>
                  <div className="text-xs opacity-80">
                    {role.resource_count} people
                    {role.overallocated_resources > 0 && (
                      <span className="ml-2 text-red-400 font-semibold">
                        ({role.overallocated_resources} over-allocated)
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {!resourceHeatmap.length && !roleHeatmap.length && (
          <div className="flex items-center justify-center py-12 text-slate-500 text-sm">
            No resource data available
          </div>
        )}
      </div>

      {/* Legend */}
      <div className="pt-4 border-t border-white/5 text-xs text-slate-400 space-y-1">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-emerald-500/40 border border-emerald-500/60 rounded" />
          <span>0-50% utilization</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-blue-500/40 border border-blue-500/60 rounded" />
          <span>50-80% utilization</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-yellow-500/40 border border-yellow-500/60 rounded" />
          <span>80-100% utilization</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-red-500/40 border border-red-500/60 rounded" />
          <span>&gt; 100% (overallocated)</span>
        </div>
      </div>
    </div>
  );
}
