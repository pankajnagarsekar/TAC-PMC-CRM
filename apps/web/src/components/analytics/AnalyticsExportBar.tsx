"use client";

import React from "react";
import { 
  Camera, 
  FileText, 
  Download 
} from "lucide-react";
import { exportChartAsPNG, exportChartAsPDF, exportChartDataAsCSV } from "@/lib/analyticsExport";

interface AnalyticsExportBarProps {
  chartRef: React.RefObject<HTMLDivElement | null>;
  chartData: any[];
  columns: string[];
  title: string;
  fileName?: string;
}

export default function AnalyticsExportBar({
  chartRef,
  chartData,
  columns,
  title,
  fileName = "Project_Analytics_Report"
}: AnalyticsExportBarProps) {
  
  const handlePNG = () => {
    exportChartAsPNG(chartRef.current, fileName);
  };

  const handlePDF = () => {
    exportChartAsPDF(chartRef.current, title, fileName);
  };

  const handleCSV = () => {
    exportChartDataAsCSV(chartData, columns, fileName);
  };

  return (
    <div className="flex items-center gap-2 border border-slate-200/50 dark:border-white/5 bg-slate-50 dark:bg-white/[0.01] p-1 rounded-xl">
      <button
        type="button"
        onClick={handlePNG}
        title="Export as PNG Image"
        className="p-2 hover:bg-slate-200/60 dark:hover:bg-white/5 rounded-lg text-slate-500 hover:text-slate-900 dark:hover:text-white transition-colors"
      >
        <Camera size={13} />
      </button>

      <button
        type="button"
        onClick={handlePDF}
        title="Export as PDF Document"
        className="p-2 hover:bg-slate-200/60 dark:hover:bg-white/5 rounded-lg text-slate-500 hover:text-slate-900 dark:hover:text-white transition-colors"
      >
        <FileText size={13} />
      </button>

      <button
        type="button"
        onClick={handleCSV}
        title="Export Data as CSV"
        className="p-2 hover:bg-slate-200/60 dark:hover:bg-white/5 rounded-lg text-slate-500 hover:text-slate-900 dark:hover:text-white transition-colors"
      >
        <Download size={13} />
      </button>
    </div>
  );
}
