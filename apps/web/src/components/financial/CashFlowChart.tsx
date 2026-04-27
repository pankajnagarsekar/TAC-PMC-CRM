"use client";

import React, { useMemo } from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { format, parse } from 'date-fns';
import { GlassCard } from '@/components/ui/GlassCard';

interface DailyBreakdown {
  date: string;
  opening: number;
  closing: number;
  transactions_count: number;
}

interface CashFlowStatement {
  project_id: string;
  from_date: string;
  to_date: string;
  opening_balance: number;
  closing_balance: number;
  daily_breakdown: DailyBreakdown[];
}

interface CashFlowChartProps {
  cashFlow: CashFlowStatement;
}

export default function CashFlowChart({ cashFlow }: CashFlowChartProps) {
  // Format data for Recharts
  const chartData = useMemo(() => {
    return cashFlow.daily_breakdown.map((day) => ({
      date: day.date,
      displayDate: format(parse(day.date, 'yyyy-MM-dd', new Date()), 'MM/dd'),
      opening: day.opening,
      closing: day.closing,
      txnCount: day.transactions_count,
    }));
  }, [cashFlow.daily_breakdown]);

  const formatCurrency = (value: number) =>
    `₹${(value / 1000).toFixed(1)}k`;

  interface CustomTooltipProps {
    active?: boolean;
    payload?: Array<{
      payload: {
        displayDate: string;
        opening: number;
        closing: number;
        txnCount: number;
      };
    }>;
  }

  const CustomTooltip = ({ active, payload }: CustomTooltipProps) => {
    if (active && payload && payload.length > 0) {
      const data = payload[0].payload;
      return (
        <div className="bg-gray-800 border border-gray-700 rounded p-3">
          <p className="text-gray-300 text-sm">{data.displayDate}</p>
          <p className="text-teal-400">Opening: {formatCurrency(data.opening)}</p>
          <p className="text-blue-400">Closing: {formatCurrency(data.closing)}</p>
          <p className="text-gray-400 text-xs">Transactions: {data.txnCount}</p>
        </div>
      );
    }
    return null;
  };

  return (
    <GlassCard className="p-6">
      <div className="space-y-4">
        <h2 className="text-2xl font-bold text-white">Cash Flow Trend</h2>
        <p className="text-gray-400 text-sm">
          Period: {format(parse(cashFlow.from_date, 'yyyy-MM-dd', new Date()), 'MMM dd, yyyy')} to{' '}
          {format(parse(cashFlow.to_date, 'yyyy-MM-dd', new Date()), 'MMM dd, yyyy')}
        </p>

        <div className="bg-gray-900 rounded-lg p-4">
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart
              data={chartData}
              margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
            >
              <defs>
                <linearGradient id="colorCash" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#14b8a6" stopOpacity={0.8} />
                  <stop offset="95%" stopColor="#14b8a6" stopOpacity={0.1} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis
                dataKey="displayDate"
                stroke="#9ca3af"
                style={{ fontSize: '12px' }}
              />
              <YAxis stroke="#9ca3af" style={{ fontSize: '12px' }} />
              <Tooltip content={<CustomTooltip />} />
              <Legend
                wrapperStyle={{ color: '#d1d5db' }}
                formatter={(value) => {
                  const labels: { [key: string]: string } = {
                    opening: 'Opening Balance',
                    closing: 'Closing Balance',
                  };
                  return labels[value] || value;
                }}
              />
              <Area
                type="monotone"
                dataKey="closing"
                stroke="#14b8a6"
                fillOpacity={1}
                fill="url(#colorCash)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div className="grid grid-cols-2 gap-4 mt-6">
          <div className="bg-gray-800 rounded p-4">
            <p className="text-gray-400 text-sm">Opening Balance</p>
            <p className="text-xl font-bold text-teal-400">
              {formatCurrency(cashFlow.opening_balance)}
            </p>
          </div>
          <div className="bg-gray-800 rounded p-4">
            <p className="text-gray-400 text-sm">Closing Balance</p>
            <p className="text-xl font-bold text-blue-400">
              {formatCurrency(cashFlow.closing_balance)}
            </p>
          </div>
        </div>
      </div>
    </GlassCard>
  );
}
