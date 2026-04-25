'use client';

import React from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend, LineChart, Line } from 'recharts';

export type ChartType = 'bar' | 'line';

export interface ChartDataItem {
  name: string;
  [key: string]: string | number;
}

export interface FinancialChartProps {
  data: ChartDataItem[];
  type?: ChartType;
  /** Data keys to display as bars/lines */
  dataKeys: { key: string; color: string; label: string }[];
  /** Chart title */
  title?: string;
  height?: number;
  className?: string;
  /** Format Y axis as currency */
  formatCurrency?: boolean;
}

import { formatINRShort, formatCurrencySafe } from '@/lib/formatters';

import { useTheme } from 'next-themes';

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{
    name: string;
    value: number | string;
    color: string;
    payload: Record<string, unknown>;
  }>;
  label?: string;
}

const CustomTooltip = ({ active, payload, label }: CustomTooltipProps) => {
  if (!active || !payload || !payload.length) return null;
  return (
    <div className="rounded-lg px-4 py-3 shadow-2xl bg-white dark:bg-slate-900 border border-zinc-200 dark:border-slate-800 min-w-[200px] max-w-[320px]">
      <p className="text-xs text-slate-500 dark:text-slate-400 mb-2 font-bold uppercase tracking-wider whitespace-normal leading-relaxed">{label}</p>
      {payload.map((p, i) => (
        <p key={i} className="text-sm font-semibold flex justify-between gap-4" style={{ color: p.color }}>
          <span className="opacity-70 font-black">{p.name}:</span>
          <span>{typeof p.value === 'number' ? formatCurrencySafe(p.value) : p.value}</span>
        </p>
      ))}
    </div>
  );
};

export default function FinancialChart({
  data,
  type = 'bar',
  dataKeys,
  title,
  height = 300,
  className = '',
  formatCurrency = true,
}: FinancialChartProps) {
  const { theme } = useTheme();
  const isDark = theme === 'dark';
  const gridColor = isDark ? 'rgba(255,255,255,0.05)' : 'rgba(80, 95, 122, 0.1)';
  const textColor = isDark ? '#64748b' : '#505f7a';
  const yTickFormatter = formatCurrency ? formatINRShort : (v: number) => String(v);

  return (
    <div className={`w-full h-full overflow-x-auto custom-scrollbar ${className}`}>
      {title && (
        <h3 className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-4">{title}</h3>
      )}
      <div style={{ minWidth: data.length * 60 }}>
        <ResponsiveContainer width="100%" height={height}>
          {type === 'bar' ? (
            <BarChart data={data} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
              <XAxis
                dataKey="name"
                tick={{ fill: textColor, fontSize: 9, fontWeight: 700 }}
                axisLine={{ stroke: gridColor }}
                angle={-45}
                textAnchor="end"
                height={110}
                interval={0}
                padding={{ left: 20, right: 20 }}
              />
              <YAxis tick={{ fill: textColor, fontSize: 11 }} tickFormatter={yTickFormatter} axisLine={{ stroke: gridColor }} />
              <Tooltip content={<CustomTooltip />} />
              <Legend
                wrapperStyle={{ fontSize: 11, color: textColor }}
                iconType="square"
                iconSize={10}
              />
              {dataKeys.map(({ key, color, label }) => (
                <Bar key={key} dataKey={key} name={label} fill={color} radius={[4, 4, 0, 0]} maxBarSize={40} />
              ))}
            </BarChart>
          ) : (
            <LineChart data={data} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
              <XAxis
                dataKey="name"
                tick={{ fill: textColor, fontSize: 9, fontWeight: 700 }}
                axisLine={{ stroke: gridColor }}
                angle={-45}
                textAnchor="end"
                height={110}
                interval={0}
                padding={{ left: 20, right: 20 }}
              />
              <YAxis tick={{ fill: textColor, fontSize: 11 }} tickFormatter={yTickFormatter} axisLine={{ stroke: gridColor }} />
              <Tooltip content={<CustomTooltip />} />
              <Legend wrapperStyle={{ fontSize: 11, color: textColor }} />
              {dataKeys.map(({ key, color, label }) => (
                <Line key={key} type="monotone" dataKey={key} name={label} stroke={color} strokeWidth={2} dot={{ r: 3 }} />
              ))}
            </LineChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  );
}
