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

function formatINRShort(value: number): string {
  if (value >= 10000000) return `₹${(value / 10000000).toFixed(1)}Cr`;
  if (value >= 100000) return `₹${(value / 100000).toFixed(1)}L`;
  if (value >= 1000) return `₹${(value / 1000).toFixed(0)}K`;
  return `₹${value}`;
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload) return null;
  return (
    <div className="rounded-lg px-3 py-2 shadow-xl" style={{ background: '#1e293b', border: '1px solid #334155' }}>
      <p className="text-xs text-slate-400 mb-1 font-medium">{label}</p>
      {payload.map((p: any, i: number) => (
        <p key={i} className="text-sm font-semibold" style={{ color: p.color }}>
          {p.name}: {new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(p.value)}
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
  const yTickFormatter = formatCurrency ? formatINRShort : (v: number) => String(v);

  return (
    <div className={`rounded-xl p-4 ${className}`} style={{ background: '#1e293b', border: '1px solid #334155' }}>
      {title && (
        <h3 className="text-sm font-semibold text-slate-300 mb-4">{title}</h3>
      )}
      <ResponsiveContainer width="100%" height={height}>
        {type === 'bar' ? (
          <BarChart data={data} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={{ stroke: '#334155' }} />
            <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} tickFormatter={yTickFormatter} axisLine={{ stroke: '#334155' }} />
            <Tooltip content={<CustomTooltip />} />
            <Legend
              wrapperStyle={{ fontSize: 11, color: '#94a3b8' }}
              iconType="square"
              iconSize={10}
            />
            {dataKeys.map(({ key, color, label }) => (
              <Bar key={key} dataKey={key} name={label} fill={color} radius={[4, 4, 0, 0]} maxBarSize={40} />
            ))}
          </BarChart>
        ) : (
          <LineChart data={data} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={{ stroke: '#334155' }} />
            <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} tickFormatter={yTickFormatter} axisLine={{ stroke: '#334155' }} />
            <Tooltip content={<CustomTooltip />} />
            <Legend wrapperStyle={{ fontSize: 11, color: '#94a3b8' }} />
            {dataKeys.map(({ key, color, label }) => (
              <Line key={key} type="monotone" dataKey={key} name={label} stroke={color} strokeWidth={2} dot={{ r: 3 }} />
            ))}
          </LineChart>
        )}
      </ResponsiveContainer>
    </div>
  );
}
