"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useProjectStore } from "@/store/projectStore";
import api from "@/lib/api";
import {
  Download,
  Calendar,
  Filter,
  RotateCcw,
  Loader2,
  BarChart3,
  FileSpreadsheet,
  FileText as FilePdf,
  Search
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import FinancialGrid from "@/components/ui/FinancialGrid";
import { ColDef } from "ag-grid-community";

type ReportType =
  | "project_summary"
  | "work_order_tracker"
  | "payment_certificate_tracker"
  | "petty_cash_tracker"
  | "csa_report"
  | "weekly_progress"
  | "15_days_progress"
  | "monthly_progress";

const REPORT_OPTIONS: {
  value: ReportType;
  label: string;
  description: string;
}[] = [
    {
      value: "project_summary",
      label: "Project Summary",
      description: "Budget vs Committed by Category",
    },
    {
      value: "work_order_tracker",
      label: "Work Order Tracker",
      description: "All Work Orders with amounts and status",
    },
    {
      value: "payment_certificate_tracker",
      label: "Payment Certificate Tracker",
      description: "All Payment Certificates with certification amounts",
    },
    {
      value: "petty_cash_tracker",
      label: "Petty Cash & OVH Tracker",
      description: "Petty Cash and OVH transactions with running balance",
    },
    {
      value: "csa_report",
      label: "CSA Report",
      description: "Category-Specific Activity report",
    },
    {
      value: "weekly_progress",
      label: "Weekly Progress",
      description: "Last 7 days activity summary",
    },
    {
      value: "15_days_progress",
      label: "15-Day Progress",
      description: "Last 15 days activity summary",
    },
    {
      value: "monthly_progress",
      label: "Monthly Progress",
      description: "Last 30 days activity summary",
    },
  ];

export default function ReportsPage() {
  const router = useRouter();
  const { activeProject } = useProjectStore();
  const { toast } = useToast();

  const [selectedReport, setSelectedReport] =
    useState<ReportType>("project_summary");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [reportData, setReportData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isExporting, setIsExporting] = useState<"excel" | "pdf" | null>(null);

  // Removed redirect - using conditional render instead
  /*
  useEffect(() => {
    if (!activeProject?.project_id) {
      router.push("/admin/dashboard");
    }
  }, [activeProject, router]);
  */

  if (!activeProject) {
    return (
      <div className="flex flex-col items-center justify-center h-[calc(100vh-200px)] animate-in fade-in duration-500">
        <div className="p-20 text-center glass-panel-luxury rounded-[2.5rem] border border-dashed border-white/5">
          <BarChart3 size={48} className="mx-auto text-slate-800 mb-6 opacity-20" />
          <p className="text-slate-500 font-bold tracking-tight uppercase text-xs">No Project Context</p>
          <p className="text-slate-700 text-[10px] mt-1 uppercase tracking-widest">Select a project via the sidebar to access financial intelligence.</p>
        </div>
      </div>
    );
  }

  const generateReport = async () => {
    if (!activeProject?.project_id) return;

    try {
      setIsLoading(true);
      let url = `/api/v1/reports/${activeProject.project_id}/${selectedReport}`;
      const params = new URLSearchParams();

      if (startDate) params.append("start_date", startDate);
      if (endDate) params.append("end_date", endDate);

      const response = await api.get(
        `${url}${params.toString() ? `?${params.toString()}` : ""}`,
      );
      setReportData(response.data);
      toast({ title: "Intelligence Ready", description: "Report datasets successfully generated." });
    } catch (error) {
      console.error("Report generation failed:", error);
      toast({
        title: "Interface Error",
        description: "Failed to assemble report. Service may be under maintenance.",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleExport = async (format: "excel" | "pdf") => {
    if (!activeProject?.project_id || !reportData) return;

    try {
      setIsExporting(format);
      let url = `/api/v1/reports/${activeProject.project_id}/${selectedReport}/export/${format}`;
      const params = new URLSearchParams();

      if (startDate) params.append("start_date", startDate);
      if (endDate) params.append("end_date", endDate);

      const response = await api.get(
        `${url}${params.toString() ? `?${params.toString()}` : ""}`,
        { responseType: "arraybuffer" },
      );

      const contentType = (response.headers?.["content-type"] || "") as string;
      if (contentType.includes("application/json")) {
        const payload = JSON.parse(new TextDecoder().decode(response.data));
        if (payload?.job_id) {
          // Poll logic... for simplicity in this redesign I'll keep the existing polling
          let attempts = 0;
          while (attempts < 60) {
            await new Promise((resolve) => setTimeout(resolve, 2000));
            const statusRes = await api.get(`/api/v1/jobs/${payload.job_id}`);
            if (
              statusRes.data?.ready ||
              statusRes.data?.status === "SUCCESS" ||
              statusRes.data?.status === "COMPLETED"
            ) {
              break;
            }
            attempts += 1;
          }

          const syncParam = params.toString() ? `&${params.toString()}` : "";
          const syncResponse = await api.get(`${url}?sync=true${syncParam}`, {
            responseType: "blob",
          });
          const syncBlob = new Blob([syncResponse.data]);
          const syncUrl = window.URL.createObjectURL(syncBlob);
          const syncLink = document.createElement("a");
          syncLink.href = syncUrl;
          syncLink.download = `${selectedReport}_${new Date().toISOString().split("T")[0]}.${format === "excel" ? "xlsx" : "pdf"
            }`;
          document.body.appendChild(syncLink);
          syncLink.click();
          window.URL.revokeObjectURL(syncUrl);
          document.body.removeChild(syncLink);

          toast({
            title: "Transmission Complete",
            description: `Portal has exported the ${format.toUpperCase()} ledger.`,
          });
          return;
        }
      }

      // Direct Download file
      const blob = new Blob([response.data]);
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = downloadUrl;
      link.download = `${selectedReport}_${new Date().toISOString().split("T")[0]}.${format === "excel" ? "xlsx" : "pdf"
        }`;
      document.body.appendChild(link);
      link.click();
      window.URL.revokeObjectURL(downloadUrl);
      document.body.removeChild(link);

      toast({
        title: "Registry Exported",
        description: `Downloaded ${format.toUpperCase()} successfully.`,
      });
    } catch (error: any) {
      console.error("Export failure:", error);
      let errorMsg = "The analytical engine encountered a stall during compilation.";

      // Try to parse error message from arraybuffer/blob response
      if (error.response?.data) {
        try {
          const data = error.response.data;
          const text = data instanceof ArrayBuffer ? new TextDecoder().decode(data) : await data.text();
          const parsed = JSON.parse(text);
          errorMsg = parsed.detail || errorMsg;
        } catch (e) {
          if (error.response.status === 503) {
            errorMsg = "Export engine is unavailable. Please check backend dependencies (GTK+ for PDF).";
          }
        }
      }

      toast({
        title: "Export Fault",
        description: errorMsg,
        variant: "destructive",
      });
    } finally {
      setIsExporting(null);
    }
  };

  const resetFilters = () => {
    setStartDate("");
    setEndDate("");
    setReportData(null);
  };

  // Dynamic column definitions based on report type
  const getColumnDefs = (): ColDef[] => {
    switch (selectedReport) {
      case "project_summary":
        return [
          { headerName: "CODE", field: "0", flex: 0.5 },
          { headerName: "Description", field: "1", flex: 1.5 },
          {
            headerName: "Budget (₹)",
            field: "2",
            flex: 1,
            cellStyle: { textAlign: "right" },
            cellRenderer: (p: any) =>
              typeof p.value === "number" ? p.value.toLocaleString("en-IN", { minimumFractionDigits: 2 }) : p.value,
          },
          {
            headerName: "Committed (₹)",
            field: "3",
            flex: 1,
            cellStyle: { textAlign: "right" },
            cellRenderer: (p: any) =>
              typeof p.value === "number" ? p.value.toLocaleString("en-IN", { minimumFractionDigits: 2 }) : p.value,
          },
          {
            headerName: "Certified (₹)",
            field: "4",
            flex: 1,
            cellStyle: { textAlign: "right" },
            cellRenderer: (p: any) =>
              typeof p.value === "number" ? p.value.toLocaleString("en-IN", { minimumFractionDigits: 2 }) : p.value,
          },
          {
            headerName: "Remaining (₹)",
            field: "5",
            flex: 1,
            cellStyle: { textAlign: "right" },
            cellRenderer: (p: any) =>
              typeof p.value === "number" ? p.value.toLocaleString("en-IN", { minimumFractionDigits: 2 }) : p.value,
          },
          { headerName: "Deadline", field: "6", flex: 0.8 },
        ];
      case "work_order_tracker":
        return [
          { headerName: "CODE", field: "0", flex: 0.5 },
          { headerName: "WO Reference", field: "1", flex: 1 },
          { headerName: "Vendor", field: "2", flex: 1.2 },
          {
            headerName: "WO Value (₹)",
            field: "3",
            flex: 1,
            cellStyle: { textAlign: "right" },
            cellRenderer: (p: any) =>
              typeof p.value === "number" ? p.value.toLocaleString("en-IN") : p.value,
          },
          {
            headerName: "Retention (₹)",
            field: "4",
            flex: 1,
            cellStyle: { textAlign: "right" },
            cellRenderer: (p: any) =>
              typeof p.value === "number" ? p.value.toLocaleString("en-IN") : p.value,
          },
          { headerName: "Start Date", field: "5", flex: 0.8 },
          { headerName: "End Date", field: "6", flex: 0.8 },
        ];
      case "payment_certificate_tracker":
        return [
          { headerName: "CODE", field: "0", flex: 0.5 },
          { headerName: "PC Reference", field: "1", flex: 1 },
          { headerName: "Vendor", field: "2", flex: 1.2 },
          {
            headerName: "PC Value (₹)",
            field: "3",
            flex: 1,
            cellStyle: { textAlign: "right" },
            cellRenderer: (p: any) =>
              typeof p.value === "number" ? p.value.toLocaleString("en-IN") : p.value,
          },
          { headerName: "PC Date", field: "4", flex: 0.8 },
          {
            headerName: "Payment (₹)",
            field: "5",
            flex: 1,
            cellStyle: { textAlign: "right" },
            cellRenderer: (p: any) =>
              typeof p.value === "number" ? p.value.toLocaleString("en-IN") : p.value,
          },
          { headerName: "Payment Date", field: "6", flex: 0.8 },
        ];
      // ... default and other cases handled ...
      default:
        return [
          { headerName: "Column 1", field: "0", flex: 1 },
          { headerName: "Column 2", field: "1", flex: 1 },
          { headerName: "Column 3", field: "2", flex: 1 },
        ];
    }
  };

  const rowData = reportData?.rows || [];

  return (
    <div className="p-6 space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-700">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
        <div className="space-y-1">
          <h1 className="text-3xl font-black text-white tracking-tight flex items-center gap-4">
            <div className="p-2 bg-orange-500/10 border border-orange-500/20 rounded-2xl shadow-inner">
              <BarChart3 size={24} className="text-orange-500" />
            </div>
            Financial Intelligence
          </h1>
          <p className="text-slate-500 text-sm font-medium pl-14">
            Deep analytical reporting for <span className="text-white font-bold">{activeProject?.project_name || 'Active Assets'}</span>
          </p>
        </div>
      </div>

      {/* Main Glass Shell */}
      <div className="bg-slate-900/40 border border-white/5 rounded-[2.5rem] p-8 space-y-8 shadow-2xl backdrop-blur-sm">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-end">
          {/* Report Type */}
          <div className="space-y-3">
            <label className="text-[10px] font-black text-slate-500 uppercase tracking-[0.2em] ml-1">Analytical Framework</label>
            <div className="relative group">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-600 group-focus-within:text-orange-500 transition-colors pointer-events-none z-0" size={18} />
              <select
                value={selectedReport}
                onChange={(e) => {
                  setSelectedReport(e.target.value as ReportType);
                  setReportData(null);
                }}
                className="w-full bg-slate-950 border border-white/5 rounded-2xl pl-12 pr-10 py-4 text-sm text-white focus:outline-none focus:border-orange-500/40 appearance-none transition-all cursor-pointer shadow-inner relative z-10"
              >
                {REPORT_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value} className="bg-slate-900">
                    {option.label}
                  </option>
                ))}
              </select>
              <div className="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none text-slate-500 z-0">
                <Filter size={14} />
              </div>
            </div>
          </div>

          {/* Date range */}
          <div className="space-y-3">
            <label className="text-[10px] font-black text-slate-500 uppercase tracking-[0.2em] ml-1">Temporal Filter</label>
            <div className="flex items-center gap-3 bg-slate-950 border border-white/5 rounded-2xl px-4 py-2 shadow-inner">
              <Calendar size={16} className="text-slate-600 pointer-events-none" />
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="bg-transparent text-xs text-white outline-none py-2 relative z-10 cursor-pointer"
              />
              <div className="w-4 h-px bg-white/5" />
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="bg-transparent text-xs text-white outline-none py-2 relative z-10 cursor-pointer"
              />
            </div>
          </div>
        </div>

        <div className="flex gap-4 border-t border-white/[0.03] pt-8">
          <button
            onClick={generateReport}
            disabled={isLoading}
            className="px-8 py-4 bg-orange-600 hover:bg-orange-500 text-white rounded-2xl font-black text-xs uppercase tracking-[0.2em] transition-all shadow-xl shadow-orange-900/20 active:scale-95 flex items-center gap-3 border border-white/10"
          >
            {isLoading ? <Loader2 size={16} className="animate-spin" /> : <RotateCcw size={16} />}
            Assemble Report
          </button>

          <button
            onClick={resetFilters}
            className="px-8 py-4 bg-white/5 border border-white/5 text-slate-400 font-bold rounded-2xl hover:bg-white/10 transition-all uppercase text-[10px] tracking-widest active:scale-95"
          >
            Flush Filters
          </button>
        </div>
      </div>

      {reportData && (
        <div className="space-y-6 animate-in fade-in zoom-in-95 duration-500">
          {/* Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="glass-panel-luxury p-6 rounded-[2rem] border border-white/5 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Metadata</h3>
                <div className="w-2 h-2 rounded-full bg-emerald-500" />
              </div>
              <div className="flex flex-col">
                <span className="text-2xl font-black text-white">{reportData.rows?.length || 0}</span>
                <span className="text-[10px] text-slate-500 font-bold tracking-tighter">Line items assembled</span>
              </div>
            </div>

            <div className="glass-panel-luxury p-6 rounded-[2rem] border border-white/5 space-y-4 col-span-2">
              <div className="flex items-center justify-between">
                <h3 className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Global Export Channels</h3>
                <span className="text-[10px] text-slate-600 font-mono italic">Secure Socket Encryption Active</span>
              </div>
              <div className="flex gap-4">
                <button
                  onClick={() => handleExport("excel")}
                  disabled={isExporting === "excel"}
                  className="flex-1 py-3 bg-emerald-500/10 border border-emerald-500/20 text-emerald-500 rounded-xl text-[10px] font-black uppercase tracking-widest hover:bg-emerald-500/20 transition-all flex items-center justify-center gap-2"
                >
                  {isExporting === "excel" ? <Loader2 size={14} className="animate-spin" /> : <FileSpreadsheet size={14} />}
                  Export Excel (.xlsx)
                </button>
                <button
                  onClick={() => handleExport("pdf")}
                  disabled={isExporting === "pdf"}
                  className="flex-1 py-3 bg-rose-500/10 border border-rose-500/20 text-rose-500 rounded-xl text-[10px] font-black uppercase tracking-widest hover:bg-rose-500/20 transition-all flex items-center justify-center gap-2"
                >
                  {isExporting === "pdf" ? <Loader2 size={14} className="animate-spin" /> : <FilePdf size={14} />}
                  Export PDF (.pdf)
                </button>
              </div>
            </div>
          </div>

          <div className="min-h-[500px]">
            <FinancialGrid columnDefs={getColumnDefs()} rowData={rowData} height="600px" />
          </div>
        </div>
      )}

      {!reportData && !isLoading && (
        <div className="p-20 text-center glass-panel-luxury rounded-[2.5rem] border border-dashed border-white/5">
          <BarChart3 size={48} className="mx-auto text-slate-800 mb-6 opacity-20" />
          <p className="text-slate-500 font-bold tracking-tight uppercase text-xs">Waiting for Engine Initialization</p>
          <p className="text-slate-700 text-[10px] mt-1 uppercase tracking-widest">Select target parameters above to begin assembling data.</p>
        </div>
      )}
    </div>
  );
}
