'use client';

import React from 'react';

export type KPIStatus = 'positive' | 'negative' | 'warning' | 'neutral';

export interface KPICardProps {
  label: string;
  value: string | number;
  /** Optional subtitle/description */
  subtitle?: string;
  /** Status affects card accent color: green/red/amber/gray */
  status?: KPIStatus;
  /** Trend value, e.g. "+12.3%" */
  trend?: string;
  /** True = trend is upward */
  trendUp?: boolean;
  /** Icon component */
  icon?: React.ReactNode;
  /** Additional CSS class */
  className?: string;
}

const STATUS_COLORS: Record<KPIStatus, { accent: string; bg: string; text: string }> = {
  positive: { accent: '#22c55e', bg: 'rgba(34,197,94,0.08)', text: '#22c55e' },
  negative: { accent: '#ef4444', bg: 'rgba(239,68,68,0.08)', text: '#ef4444' },
  warning:  { accent: '#f59e0b', bg: 'rgba(245,158,11,0.08)', text: '#f59e0b' },
  neutral:  { accent: '#6366f1', bg: 'rgba(99,102,241,0.08)', text: '#6366f1' },
};

export default function KPICard({
  label,
  value,
  subtitle,
  status = 'neutral',
  trend,
  trendUp,
  icon,
  className = '',
}: KPICardProps) {
  const colors = STATUS_COLORS[status];

  return (
    <div
      className={`rounded-xl p-4 transition-all hover:scale-[1.02] ${className}`}
      style={{
        background: '#1e293b',
        border: `1px solid ${colors.accent}22`,
      }}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-1">
            {label}
          </p>
          <p className="text-2xl font-bold text-white truncate" style={{ color: colors.text }}>
            {value}
          </p>
          {subtitle && (
            <p className="text-xs text-slate-500 mt-1 truncate">{subtitle}</p>
          )}
        </div>
        {icon && (
          <div
            className="w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 ml-3"
            style={{ background: colors.bg }}
          >
            {icon}
          </div>
        )}
      </div>

      {trend && (
        <div className="flex items-center gap-1 mt-3">
          <span
            className="text-xs font-semibold"
            style={{ color: trendUp ? '#22c55e' : '#ef4444' }}
          >
            {trendUp ? '↑' : '↓'} {trend}
          </span>
          <span className="text-xs text-slate-500">vs last period</span>
        </div>
      )}
    </div>
  );
}
