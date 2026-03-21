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

const STATUS_CONFIG: Record<KPIStatus, { accent: string; bg: string; text: string; shadow: string }> = {
  positive: { accent: 'hsl(var(--kpi-positive-text))', bg: 'var(--kpi-positive-bg)', text: 'hsl(var(--kpi-positive-text))', shadow: 'var(--kpi-positive-shadow)' },
  negative: { accent: 'hsl(var(--kpi-negative-text))', bg: 'var(--kpi-negative-bg)', text: 'hsl(var(--kpi-negative-text))', shadow: 'var(--kpi-negative-shadow)' },
  warning: { accent: 'hsl(var(--kpi-warning-text))', bg: 'var(--kpi-warning-bg)', text: 'hsl(var(--kpi-warning-text))', shadow: 'var(--kpi-warning-shadow)' },
  neutral: { accent: 'hsl(var(--kpi-neutral-text))', bg: 'var(--kpi-neutral-bg)', text: 'hsl(var(--kpi-neutral-text))', shadow: 'var(--kpi-neutral-shadow)' },
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
  const config = STATUS_CONFIG[status];

  return (
    <div
      className={`glass-panel-luxury rounded-2xl p-5 border border-kpi-border/30 transition-all duration-300 hover:scale-[1.03] active:scale-[0.98] group relative overflow-hidden bg-kpi ${className}`}
    >
      {/* Dynamic background glow */}
      <div
        className="absolute -right-4 -top-4 w-24 h-24 rounded-full blur-[40px] opacity-10 transition-opacity duration-300 group-hover:opacity-20"
        style={{ backgroundColor: config.accent }}
      />

      <div className="flex items-start justify-between relative z-10">
        <div className="flex-1 min-w-0">
          <p className="text-[10px] font-bold text-foreground/50 uppercase tracking-[0.15em] mb-2">
            {label}
          </p>
          <p className="text-3xl font-black text-foreground tracking-tight leading-none group-hover:text-accent transition-colors">
            {value}
          </p>
          {subtitle && (
            <p className="text-xs font-medium text-foreground/40 mt-2 truncate max-w-full opacity-70">
              {subtitle}
            </p>
          )}
        </div>

        {icon && (
          <div
            className="w-11 h-11 rounded-2xl flex items-center justify-center flex-shrink-0 ml-4 border border-foreground/10 shadow-inner transition-all duration-300 group-hover:shadow-lg group-hover:scale-110"
            style={{
              background: `linear-gradient(135deg, ${config.bg}, transparent)`,
              boxShadow: `0 0 15px ${config.shadow}`
            }}
          >
            <div style={{ color: config.text }}>
              {icon}
            </div>
          </div>
        )}
      </div>

      {trend && (
        <div className="flex items-center gap-2 mt-5 pt-4 border-t border-foreground/5 relative z-10">
          <div
            className={`flex items-center gap-0.5 px-2 py-0.5 rounded-full text-[10px] font-bold ${trendUp ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400' : 'bg-rose-500/10 text-rose-600 dark:text-rose-400'
              }`}
          >
            {trendUp ? '↑' : '↓'} {trend}
          </div>
          <span className="text-[10px] font-bold text-foreground/40 uppercase tracking-wider">vs prev</span>
        </div>
      )}
    </div>
  );
}
