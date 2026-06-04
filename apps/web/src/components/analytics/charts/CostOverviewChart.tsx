"use client";

import React, { useMemo, useRef } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import useSWR from "swr";
import { fetcher } from "@/lib/api";
import { ScheduleTask } from "@/types/schedule.types";
import { useAnalyticsStore } from "@/store/useAnalyticsStore";
import { formatINRShort } from "@/lib/formatters";
import AnalyticsExportBar from "../AnalyticsExportBar";
import { getFilteredTasks } from "@/lib/analyticsComputeEngine";

interface CostOverviewChartProps {
  tasks: ScheduleTask[];
  financials?: any[];
  projectId?: string;
}

const formatCurrency = (value: number) => formatINRShort(value);

export default function CostOverviewChart({ tasks, financials, projectId }: CostOverviewChartProps) {
  const filters = useAnalyticsStore((state) => state.filters);
  const chartRef = useRef<HTMLDivElement>(null);

  // Fetch payment certificates using SWR
  const { data: paymentsData } = useSWR<any>(
    projectId ? `/api/v1/payments/${projectId}` : null,
    fetcher
  );

  const filteredTasks = useMemo(() => {
    return getFilteredTasks(tasks, filters);
  }, [tasks, filters]);

  const chartData = useMemo(() => {
    // Extract paid payment certificates
    const pcs = paymentsData?.items || paymentsData || [];
    const paidPcs = Array.isArray(pcs) ? pcs.filter((pc: any) => pc.status?.toLowerCase() === 'paid') : [];
    const totalPaidAmount = paidPcs.reduce((sum: number, pc: any) => sum + Number(pc.payment_amount ?? pc.grand_total ?? 0), 0);
    // 1. If we have rich backend financial records, use them
    if (financials && financials.length > 0) {
      const totalCertified = financials.reduce((sum, f) => sum + (f.certified_value || 0), 0);
      return financials.map((f) => {
        const budget = f.original_budget || 0;
        const committed = f.committed_value || 0;
        const certified = f.certified_value || 0;
        const forecast = committed + Math.max(0, budget - committed);
        
        let paid = 0;
        if (totalCertified > 0) {
          paid = Math.round(totalPaidAmount * (certified / totalCertified));
        } else {
          const totalCommitted = financials.reduce((sum, fi) => sum + (fi.committed_value || 0), 0);
          if (totalCommitted > 0) {
            paid = Math.round(totalPaidAmount * (committed / totalCommitted));
          } else {
            paid = Math.round(totalPaidAmount / financials.length);
          }
        }

        return {
          name: f.category_name || f.category_code || "Misc",
          "Approved Budget": budget,
          "Committed (WOs)": committed,
          "Certified (PCs)": certified,
          "Paid Cost": paid,
          "Forecast Final Cost": forecast,
        };
      });
    }

    // 2. Fall back to task-level rollup by WBS code
    const categoriesMap: Record<string, { name: string; budget: number; committed: number; certified: number; paid: number; forecast: number }> = {};
    
    filteredTasks.forEach((task) => {
      const code = task.wbs_code?.split('.')[0] || 'Misc';
      const name = code === 'C' ? 'Construction' :
                   code === 'P' ? 'Contracting' :
                   code === 'D' ? 'Design/Engineering' :
                   code === 'S' ? 'Site Ops' :
                   code === 'I' ? 'Interiors' : code;

      if (!categoriesMap[name]) {
        categoriesMap[name] = { name, budget: 0, committed: 0, certified: 0, paid: 0, forecast: 0 };
      }
      
      categoriesMap[name].budget += Number(task.baseline_cost ?? 0);
      categoriesMap[name].committed += Number(task.wo_value ?? 0);
      categoriesMap[name].certified += Number(task.payment_value ?? 0);
    });

    const totalCertified = Object.values(categoriesMap).reduce((sum, c) => sum + c.certified, 0);

    return Object.values(categoriesMap)
      .map((c) => {
        const forecast = c.committed + Math.max(0, c.budget - c.committed);
        let paid = 0;
        if (totalCertified > 0) {
          paid = Math.round(totalPaidAmount * (c.certified / totalCertified));
        } else {
          const totalCommitted = Object.values(categoriesMap).reduce((sum, cat) => sum + cat.committed, 0);
          if (totalCommitted > 0) {
            paid = Math.round(totalPaidAmount * (c.committed / totalCommitted));
          } else {
            paid = Math.round(totalPaidAmount / Object.keys(categoriesMap).length);
          }
        }

        return {
          name: c.name,
          "Approved Budget": c.budget,
          "Committed (WOs)": c.committed,
          "Certified (PCs)": c.certified,
          "Paid Cost": paid,
          "Forecast Final Cost": forecast,
        };
      })
      .filter(c => c["Approved Budget"] > 0 || c["Committed (WOs)"] > 0 || c["Certified (PCs)"] > 0);
  }, [filteredTasks, financials, paymentsData]);

  return (
    <div ref={chartRef} className="space-y-6 h-full w-full">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-xs font-black uppercase tracking-[0.2em] text-slate-900 dark:text-white/45">Cost Overview</h3>
          <p className="mt-1 text-[10px] uppercase tracking-[0.18em] text-slate-500">
            Planned Cost vs Committed Value vs Certified Value vs Paid Cost vs Forecast Final Cost
          </p>
        </div>
        {chartData.length > 0 && (
          <AnalyticsExportBar
            chartRef={chartRef}
            chartData={chartData}
            columns={["name", "Approved Budget", "Committed (WOs)", "Certified (PCs)", "Paid Cost", "Forecast Final Cost"]}
            title="Cost Overview"
            fileName="Cost_Overview"
          />
        )}
      </div>

      <div className="h-[340px] w-full min-w-0">
        {chartData.length > 0 ? (
          <ResponsiveContainer width="100%" height="100%" debounce={100}>
            <BarChart
              data={chartData}
              margin={{ top: 20, right: 30, left: 10, bottom: 20 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="currentColor" className="text-slate-200 dark:text-white/[0.03]" vertical={false} />
              <XAxis
                dataKey="name"
                tick={{ fill: "#64748b", fontSize: 9, fontWeight: 600 }}
                axisLine={false}
                tickLine={false}
                dy={10}
              />
              <YAxis
                tick={{ fill: "#64748b", fontSize: 9 }}
                axisLine={false}
                tickLine={false}
                tickFormatter={formatCurrency}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "rgba(15, 23, 42, 0.9)",
                  border: "1px solid rgba(255, 255, 255, 0.1)",
                  borderRadius: "12px",
                  fontSize: "11px",
                  color: "#fff",
                  boxShadow: "0 20px 25px -5px rgb(0 0 0 / 0.1)"
                }}
                formatter={(value: any, name: any) => [formatCurrency(Number(value || 0)), name]}
              />
              <Legend
                verticalAlign="top"
                height={36}
                content={({ payload }) => (
                  <div className="flex justify-end gap-4 text-[10px] font-black uppercase tracking-wider text-slate-500 flex-wrap">
                    {payload?.map((entry: any, index) => (
                      <div key={index} className="flex items-center gap-1.5">
                        <div className="h-1.5 w-3 rounded-full" style={{ backgroundColor: entry.color }} />
                        <span>{entry.value}</span>
                      </div>
                    ))}
                  </div>
                )}
              />
              <Bar dataKey="Approved Budget" name="Approved Budget" fill="#775a19" radius={[4, 4, 0, 0]} maxBarSize={20} />
              <Bar dataKey="Committed (WOs)" name="Committed (WOs)" fill="#505f7a" radius={[4, 4, 0, 0]} maxBarSize={20} />
              <Bar dataKey="Certified (PCs)" name="Certified (PCs)" fill="#10b981" radius={[4, 4, 0, 0]} maxBarSize={20} />
              <Bar dataKey="Paid Cost" name="Paid Cost" fill="#0284c7" radius={[4, 4, 0, 0]} maxBarSize={20} />
              <Bar dataKey="Forecast Final Cost" name="Forecast Final Cost" fill="#c084fc" radius={[4, 4, 0, 0]} maxBarSize={20} />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex h-full items-center justify-center text-slate-400">
            No cost data available. Initialise baseline costs or work orders to enable this analysis.
          </div>
        )}
      </div>
    </div>
  );
}
