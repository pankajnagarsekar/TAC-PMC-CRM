"use client";

import React, { useMemo } from "react";
import FinancialGrid from "../ui/FinancialGrid";
import { ColDef } from "ag-grid-community";
import { formatINR } from "../ui/FinancialGrid";
import { Trash2 } from "lucide-react";
import { Button } from "../ui/button";

interface SchedulerGridProps {
    tasks: any[];
    onTasksChange: (tasks: any[]) => void;
    readOnly?: boolean;
}

export default function SchedulerGrid({ tasks, onTasksChange, readOnly = false }: SchedulerGridProps) {
    const columnDefs: ColDef[] = useMemo(() => [
        {
            field: "id",
            headerName: "ID",
            width: 80,
            editable: !readOnly,
            cellStyle: { fontWeight: 700, color: "#f97316" }
        },
        {
            field: "name",
            headerName: "Task Name",
            flex: 1,
            minWidth: 200,
            editable: !readOnly
        },
        {
            field: "duration",
            headerName: "Dur (Days)",
            width: 100,
            type: "numericColumn",
            editable: !readOnly
        },
        {
            field: "start",
            headerName: "Start",
            width: 120,
            editable: !readOnly,
            tooltipValueGetter: () => "Format: DD-MM-YY"
        },
        {
            field: "finish",
            headerName: "Finish",
            width: 120,
            editable: false,
            cellClass: "bg-slate-800/20 font-medium text-slate-300"
        },
        {
            field: "actualStart",
            headerName: "Actual Start",
            width: 120,
            editable: !readOnly,
            tooltipValueGetter: () => "Format: DD-MM-YY or leave blank"
        },
        {
            field: "actualFinish",
            headerName: "Actual Finish",
            width: 120,
            editable: !readOnly,
            tooltipValueGetter: () => "Format: DD-MM-YY or leave blank"
        },
        {
            field: "percentComplete",
            headerName: "% Complete",
            width: 110,
            type: "numericColumn",
            editable: !readOnly,
            valueFormatter: (params) => params.value ? `${params.value}%` : "0%"
        },
        {
            field: "predecessors",
            headerName: "Predecessors",
            width: 150,
            editable: !readOnly,
            valueFormatter: (params) => params.value?.join(", ") || ""
        },
        {
            field: "cost",
            headerName: "Estimated Cost",
            width: 150,
            type: "numericColumn",
            editable: !readOnly,
            valueFormatter: (params) => formatINR(params.value)
        },
        {
            field: "is_critical",
            headerName: "Critical",
            width: 100,
            cellRenderer: (params: any) => params.value ? (
                <span className="px-2 py-0.5 rounded-full text-[10px] bg-red-500/10 text-red-500 border border-red-500/20 font-bold uppercase tracking-wider">Yes</span>
            ) : null
        },
        {
            headerName: "",
            width: 50,
            pinned: "right",
            cellRenderer: (params: any) => (
                <button
                    onClick={() => handleDelete(params.node.rowIndex)}
                    className="p-1 hover:bg-red-500/10 text-slate-500 hover:text-red-500 transition-colors rounded"
                >
                    <Trash2 size={14} />
                </button>
            ),
            editable: false,
            sortable: false,
            filter: false
        }
    ], [readOnly, tasks]);

    const handleCellValueChanged = (event: any) => {
        const updatedTasks = [...tasks];
        updatedTasks[event.node.rowIndex] = event.data;
        onTasksChange(updatedTasks);
    };

    const handleDelete = (index: number) => {
        const updatedTasks = tasks.filter((_, i) => i !== index);
        onTasksChange(updatedTasks);
    };

    return (
        <div className="space-y-4">
            <FinancialGrid
                rowData={tasks}
                columnDefs={columnDefs}
                onCellValueChanged={handleCellValueChanged}
                height="500px"
                editable={!readOnly}
                showSrNo={true}
            />
            <div className="flex gap-4 text-[10px] text-slate-500 uppercase tracking-widest font-medium px-2 flex-wrap">
                <div className="flex items-center gap-1.5">
                    <div className="w-2 h-2 rounded-full bg-orange-500" />
                    <span>Calculated by CPM</span>
                </div>
                <div className="flex items-center gap-1.5">
                    <div className="w-2 h-2 rounded-full bg-red-500" />
                    <span>Critical Path</span>
                </div>
                <div className="flex items-center gap-1.5">
                    <div className="w-2 h-2 rounded-full bg-blue-500" />
                    <span>From Import (XML/PDF)</span>
                </div>
            </div>
        </div>
    );
}
