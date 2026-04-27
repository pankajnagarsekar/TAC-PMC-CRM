"use client";

import React, { useMemo } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { format, parseISO } from "date-fns";
import { formatINRShort } from "@/lib/formatters";

interface DayMetric {
  date: string;
  value: number;
}

interface BudgetTrendProps {
  data: DayMetric[];
  budget_total: number;
  title?: string;
}

export default function BudgetTrend({
  data,
  budget_total,
  title = "Budget Trend",
}: BudgetTrendProps) {
  const chartData = useMemo(() => {
    if (!data.length) return [];
    return data.map((item) => ({
      date: format(parseISO(item.date), "MMM dd"),
      spent: item.value,
      budget: budget_total,
      remaining: Math.max(0, budget_total - item.value),
    }));
  }, [data, budget_total]);

  const formatCurrency = (value: number) => formatINRShort(value);

  const lastSpent = data.length > 0 ? data[data.length - 1].value : 0;
  const percentSpent = budget_total ? (lastSpent / budget_total) * 100 : 0;
  const statusColor =
    percentSpent > 100 ? "text-red-500" : percentSpent > 80 ? "text-yellow-500" : "text-green-500";

  return (
    <div className="bg-slate-900/50 border border-white/10 rounded-lg p-6 backdrop-blur">
      <div className="mb-4">
        <h3 className="text-sm font-semibold text-white mb-1">{title}</h3>
        <div className="flex items-baseline gap-2">
          <span className={`text-2xl font-bold ${statusColor}`}>
            {formatCurrency(lastSpent)}
          </span>
          <span className="text-xs text-slate-400">
            of {formatCurrency(budget_total)} ({percentSpent.toFixed(0)}%)
          </span>
        </div>
      </div>

      {chartData.length > 0 ? (
        <ResponsiveContainer width="100%" height={250}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis
              dataKey="date"
              stroke="rgba(255,255,255,0.3)"
              style={{ fontSize: "12px" }}
            />
            <YAxis
              stroke="rgba(255,255,255,0.3)"
              style={{ fontSize: "12px" }}
              tickFormatter={(value: number | string) => formatCurrency(Number(value))}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "rgba(15, 23, 42, 0.95)",
                border: "1px solid rgba(255, 255, 255, 0.1)",
                borderRadius: "8px",
              }}
              // @ts-expect-error - Recharts typing issue with formatter
              formatter={(value: number) => formatCurrency(value)}
              labelFormatter={(label) => `Date: ${label}`}
            />
            <Legend />
            <Line
              type="monotone"
              dataKey="spent"
              stroke="#ef4444"
              strokeWidth={2}
              dot={false}
              name="Amount Spent"
            />
            <Line
              type="monotone"
              dataKey="budget"
              stroke="#8b5cf6"
              strokeWidth={2}
              strokeDasharray="5 5"
              dot={false}
              name="Budget Total"
            />
          </LineChart>
        </ResponsiveContainer>
      ) : (
        <div className="h-64 flex items-center justify-center text-slate-500 text-sm">
          No budget data available
        </div>
      )}
    </div>
  );
}
