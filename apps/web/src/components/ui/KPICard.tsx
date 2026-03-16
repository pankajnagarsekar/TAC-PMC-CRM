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
  positive: { accent: '#10b981', bg: 'rgba(16,185,129,0.1)', text: '#34d399', shadow: 'rgba(16,185,129,0.2)' },
  negative: { accent: '#ef4444', bg: 'rgba(239,68,68,0.1)', text: '#f87171', shadow: 'rgba(239,68,68,0.2)' },
  warning:  { accent: '#f59e0b', bg: 'rgba(245,158,11,0.1)', text: '#fbbf24', shadow: 'rgba(245,158,11,0.2)' },
  neutral:  { accent: '#8b5cf6', bg: 'rgba(139,92,246,0.1)', text: '#a78bfa', shadow: 'rgba(139,92,246,0.2)' },
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
      className={`glass-panel-luxury rounded-2xl p-5 border border-white/5 transition-all duration-300 hover:scale-[1.03] active:scale-[0.98] group relative overflow-hidden ${className}`}
    >
      {/* Dynamic background glow */}
      <div 
        className="absolute -right-4 -top-4 w-24 h-24 rounded-full blur-[40px] opacity-10 transition-opacity duration-300 group-hover:opacity-20"
        style={{ backgroundColor: config.accent }}
      />
      
      <div className="flex items-start justify-between relative z-10">
        <div className="flex-1 min-w-0">
          <p className="text-[10px] font-bold text-slate-500 uppercase tracking-[0.15em] mb-2">
            {label}
          </p>
          <p className="text-3xl font-black text-white tracking-tight leading-none group-hover:text-accent transition-colors">
            {value}
          </p>
          {subtitle && (
            <p className="text-xs font-medium text-slate-400 mt-2 truncate max-w-full opacity-70">
              {subtitle}
            </p>
          )}
        </div>
        
        {icon && (
          <div
            className="w-11 h-11 rounded-2xl flex items-center justify-center flex-shrink-0 ml-4 border border-white/10 shadow-inner transition-all duration-300 group-hover:shadow-lg group-hover:scale-110"
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
        <div className="flex items-center gap-2 mt-5 pt-4 border-t border-white/5 relative z-10">
          <div 
            className={`flex items-center gap-0.5 px-2 py-0.5 rounded-full text-[10px] font-bold ${
              trendUp ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'
            }`}
          >
            {trendUp ? '↑' : '↓'} {trend}
          </div>
          <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">vs prev</span>
        </div>
      )}
    </div>
  );
}
