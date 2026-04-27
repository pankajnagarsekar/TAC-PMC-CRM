'use client';

import { useMemo } from "react";
import { useRouter } from "next/navigation";
import { Task } from "@/types/api";
import { formatDate } from "@tac-pmc/ui";
import FinancialGrid from "@/components/ui/FinancialGrid";
import { ColDef, ICellRendererParams, ValueFormatterParams } from "ag-grid-community";

interface PastTasksTableProps {
  tasks: Task[];
}

export default function PastTasksTable({ tasks }: PastTasksTableProps) {
  const router = useRouter();

  const columnDefs: ColDef<Task>[] = useMemo(
    () => [

      {
        field: "sr_no",
        headerName: "NO.",
        width: 80,
        sortable: true,
        cellRenderer: (p: ICellRendererParams<Task>) => (
          <span className="text-slate-500 font-mono text-xs">#{p.value}</span>
        ),
      },
      {
        field: "task_description",
        headerName: "Description",
        flex: 1,
        minWidth: 200,
        cellRenderer: (p: ICellRendererParams<Task>) => (
          <div
            onClick={() => p.data?._id && router.push(`/admin/tasks/${p.data._id}`)}
            className="font-medium text-white hover:text-blue-400 hover:underline cursor-pointer transition-colors"
          >
            {p.value}
          </div>
        ),
      },
      {
        field: "assigned_to_name",
        headerName: "Assignee",
        width: 150,
      },
      {
        field: "deadline",
        headerName: "Deadline",
        width: 130,
        valueFormatter: (p: ValueFormatterParams<Task>) => (p.value ? formatDate(p.value) : "N/A"),
      },
      {
        field: "priority",
        headerName: "Priority",
        width: 110,
        cellRenderer: (p: ICellRendererParams<Task>) => {
          const priority = p.value;
          const colors: Record<string, string> = {
            Low: "bg-slate-500/10 text-slate-400 border-slate-500/20",
            Medium: "bg-amber-500/10 text-amber-400 border-amber-500/20",
            High: "bg-red-500/10 text-red-400 border-red-500/20",
          };
          return (
            <div className="flex items-center h-full">
              <span
                className={`px-2.5 py-0.5 rounded font-bold text-[10px] uppercase border ${colors[priority] || colors["Low"]}`}
              >
                {priority}
              </span>
            </div>
          );
        },
      },
      {
        field: "status",
        headerName: "Status",
        width: 130,
        cellRenderer: (p: ICellRendererParams<Task>) => {
          const status = p.value;
          const colors: Record<string, string> = {
            Open: "bg-slate-500/10 text-slate-400 border-slate-500/20",
            "In Progress": "bg-blue-500/10 text-blue-400 border-blue-500/20",
            Review: "bg-amber-500/10 text-amber-500 border-amber-500/20",
            Completed: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
            Closed: "bg-emerald-900/40 text-emerald-600 border-emerald-900/30",
          };
          return (
            <div className="flex items-center h-full">
              <span
                className={`px-2.5 py-0.5 rounded font-bold text-[10px] uppercase border ${colors[status] || colors["Open"]}`}
              >
                {status}
              </span>
            </div>
          );
        },
      },
    ],
    [router]
  );

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
      <FinancialGrid
        rowData={tasks}
        columnDefs={columnDefs}
        height="500px"
      />
    </div>
  );
}
