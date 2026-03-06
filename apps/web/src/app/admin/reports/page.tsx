"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useProjectStore } from "@/store/projectStore";
import api from "@/lib/api";
import { Download, Calendar, Filter, RotateCcw, Loader2 } from "lucide-react";
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

const REPORT_OPTIONS: { value: ReportType; label: string; description: string }[] = [
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

  const [selectedReport, setSelectedReport] = useState<ReportType>("project_summary");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [reportData, setReportData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isExporting, setIsExporting] = useState<"excel" | "pdf" | null>(null);

  // Redirect if no project selected
  useEffect(() => {
    if (!activeProject?.project_id) {
      router.push("/admin/dashboard");
    }
  }, [activeProject, router]);

  const generateReport = async () => {
    if (!activeProject?.project_id) return;

    try {
      setIsLoading(true);
      let url = `/api/projects/${activeProject.project_id}/reports/${selectedReport}`;
      const params = new URLSearchParams();

      if (startDate) params.append("start_date", startDate);
      if (endDate) params.append("end_date", endDate);

      const response = await api.get(
        `${url}${params.toString() ? `?${params.toString()}` : ""}`
      );
      setReportData(response.data);
    } catch (error) {
      console.error("Report generation failed:", error);
      toast({
        title: "Error",
        description: "Failed to generate report",
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
      let url = `/api/projects/${activeProject.project_id}/reports/${selectedReport}/export/${format}`;
      const params = new URLSearchParams();

      if (startDate) params.append("start_date", startDate);
      if (endDate) params.append("end_date", endDate);

      const response = await api.get(
        `${url}${params.toString() ? `?${params.toString()}` : ""}`,
        { responseType: "arraybuffer" }
      );

      const contentType = (response.headers?.["content-type"] || "") as string;
      if (contentType.includes("application/json")) {
        const payload = JSON.parse(new TextDecoder().decode(response.data));
        if (payload?.job_id) {
          let attempts = 0;
          while (attempts < 60) {
            await new Promise((resolve) => setTimeout(resolve, 2000));
            const statusRes = await api.get(`/api/jobs/${payload.job_id}`);
            if (statusRes.data?.ready || statusRes.data?.status === "SUCCESS" || statusRes.data?.status === "COMPLETED") {
              break;
            }
            attempts += 1;
          }

          const syncParam = params.toString() ? `&${params.toString()}` : "";
          const syncResponse = await api.get(`${url}?sync=true${syncParam}`, { responseType: "blob" });
          const syncBlob = new Blob([syncResponse.data]);
          const syncUrl = window.URL.createObjectURL(syncBlob);
          const syncLink = document.createElement("a");
          syncLink.href = syncUrl;
          syncLink.download = `${selectedReport}_${new Date().toISOString().split("T")[0]}.${
            format === "excel" ? "xlsx" : "pdf"
          }`;
          document.body.appendChild(syncLink);
          syncLink.click();
          window.URL.revokeObjectURL(syncUrl);
          document.body.removeChild(syncLink);

          toast({
            title: "Success",
            description: `Report exported as ${format.toUpperCase()}`,
          });
          return;
        }
      }

      // Download file
      const blob = new Blob([response.data]);
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = downloadUrl;
      link.download = `${selectedReport}_${new Date().toISOString().split("T")[0]}.${
        format === "excel" ? "xlsx" : "pdf"
      }`;
      document.body.appendChild(link);
      link.click();
      window.URL.revokeObjectURL(downloadUrl);
      document.body.removeChild(link);

      toast({
        title: "Success",
        description: `Report exported as ${format.toUpperCase()}`,
      });
    } catch (error) {
      console.error("Export failed:", error);
      toast({
        title: "Error",
        description: `Failed to export as ${format.toUpperCase()}`,
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
            headerName: "WO Value (₹)",
            field: "2",
            flex: 1,
            cellStyle: { textAlign: "right" },
            cellRenderer: (p: any) => (typeof p.value === "number" ? p.value.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : p.value),
          },
          {
            headerName: "% Progress",
            field: "3",
            flex: 0.7,
            cellRenderer: (p: any) => (typeof p.value === "number" ? (p.value * 100).toFixed(1) + "%" : p.value),
          },
          {
            headerName: "Payment Value (₹)",
            field: "4",
            flex: 1,
            cellStyle: { textAlign: "right" },
            cellRenderer: (p: any) => (typeof p.value === "number" ? p.value.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : p.value),
          },
          { headerName: "Deadline", field: "5", flex: 0.8 },
          {
            headerName: "Difference (₹)",
            field: "6",
            flex: 1,
            cellStyle: { textAlign: "right" },
            cellRenderer: (p: any) => (typeof p.value === "number" ? p.value.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : p.value),
          },
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
            cellRenderer: (p: any) => (typeof p.value === "number" ? p.value.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : p.value),
          },
          {
            headerName: "Retention (₹)",
            field: "4",
            flex: 1,
            cellStyle: { textAlign: "right" },
            cellRenderer: (p: any) => (typeof p.value === "number" ? p.value.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : p.value),
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
            cellRenderer: (p: any) => (typeof p.value === "number" ? p.value.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : p.value),
          },
          { headerName: "PC Date", field: "4", flex: 0.8 },
          {
            headerName: "Payment (₹)",
            field: "5",
            flex: 1,
            cellStyle: { textAlign: "right" },
            cellRenderer: (p: any) => (typeof p.value === "number" ? p.value.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : p.value),
          },
          { headerName: "Payment Date", field: "6", flex: 0.8 },
        ];
      case "petty_cash_tracker":
        return [
          { headerName: "Date", field: "0", flex: 0.8 },
          { headerName: "PC Ref", field: "1", flex: 1 },
          {
            headerName: "PC Value (₹)",
            field: "2",
            flex: 1,
            cellStyle: { textAlign: "right" },
            cellRenderer: (p: any) => (typeof p.value === "number" ? p.value.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : p.value),
          },
          { headerName: "Bill / Invoice", field: "3", flex: 1.5 },
        ];
      case "csa_report":
        return [
          { headerName: "CODE", field: "0", flex: 0.5 },
          { headerName: "WO Ref", field: "1", flex: 1 },
          { headerName: "Description", field: "2", flex: 2 },
          { headerName: "Qty", field: "3", flex: 0.5 },
          { headerName: "Received Date", field: "4", flex: 0.8 },
        ];
      case "weekly_progress":
      case "15_days_progress":
      case "monthly_progress":
        return [
          { headerName: "CODE", field: "0", flex: 0.5 },
          { headerName: "WO Reference", field: "1", flex: 1 },
          { headerName: "Vendor", field: "2", flex: 1.2 },
          {
            headerName: "% Completed",
            field: "3",
            flex: 0.8,
            cellRenderer: (p: any) => (typeof p.value === "number" ? (p.value * 100).toFixed(1) + "%" : p.value),
          },
          { headerName: "Comments", field: "4", flex: 1.5 },
        ];
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
    <div className="space-y-6 p-6 animate-in fade-in duration-500">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white tracking-tight">Financial Reports</h1>
        <p className="text-slate-400 text-sm mt-1">Generate and export financial reports with filters</p>
      </div>

      {/* Report Selector & Filters */}
      <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Report Type Selector */}
          <div className="space-y-2">
            <label className="text-sm font-bold text-slate-300 uppercase tracking-widest">
              Report Type
            </label>
            <select
              value={selectedReport}
              onChange={(e) => {
                setSelectedReport(e.target.value as ReportType);
                setReportData(null);
              }}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-white focus:outline-none focus:border-orange-500/50 transition-colors"
            >
              {REPORT_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label} - {option.description}
                </option>
              ))}
            </select>
          </div>

          {/* Date Range */}
          <div className="space-y-2">
            <label className="text-sm font-bold text-slate-300 uppercase tracking-widest">
              Date Range (Optional)
            </label>
            <div className="flex gap-2 items-end">
              <div className="flex-1">
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2.5 text-white text-sm focus:outline-none focus:border-orange-500/50 transition-colors"
                  placeholder="Start date"
                />
              </div>
              <span className="text-slate-600 text-sm font-semibold">to</span>
              <div className="flex-1">
                <input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2.5 text-white text-sm focus:outline-none focus:border-orange-500/50 transition-colors"
                  placeholder="End date"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-3 pt-2">
          <button
            onClick={generateReport}
            disabled={isLoading}
            className="px-6 py-2.5 bg-orange-600 text-white text-sm font-bold rounded-xl hover:bg-orange-500 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {isLoading ? (
              <>
                <Loader2 size={16} className="animate-spin" /> Generating...
              </>
            ) : (
              <>
                <Filter size={16} /> Generate Report
              </>
            )}
          </button>

          <button
            onClick={resetFilters}
            className="px-6 py-2.5 border border-slate-700 text-slate-300 text-sm font-bold rounded-xl hover:bg-slate-800 transition-all flex items-center gap-2"
          >
            <RotateCcw size={16} /> Reset
          </button>
        </div>
      </div>

      {/* Report Data Display */}
      {reportData && (
        <div className="space-y-4">
          {/* Report Title & Summary */}
          <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6">
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
              <div>
                <h2 className="text-xl font-bold text-white">{reportData.title}</h2>
                <p className="text-slate-400 text-sm mt-1">
                  {reportData.rows?.length || 0} records • Generated{" "}
                  {new Date(reportData.metadata?.generated_at).toLocaleString()}
                </p>
              </div>

              {/* Export Buttons */}
              <div className="flex gap-2">
                <button
                  onClick={() => handleExport("excel")}
                  disabled={isExporting === "excel"}
                  className="px-4 py-2.5 bg-green-600 text-white text-sm font-bold rounded-xl hover:bg-green-500 transition-all disabled:opacity-50 flex items-center gap-2"
                >
                  {isExporting === "excel" ? (
                    <>
                      <Loader2 size={14} className="animate-spin" />
                    </>
                  ) : (
                    <>
                      <Download size={14} /> Excel
                    </>
                  )}
                </button>
                <button
                  onClick={() => handleExport("pdf")}
                  disabled={isExporting === "pdf"}
                  className="px-4 py-2.5 bg-red-600 text-white text-sm font-bold rounded-xl hover:bg-red-500 transition-all disabled:opacity-50 flex items-center gap-2"
                >
                  {isExporting === "pdf" ? (
                    <>
                      <Loader2 size={14} className="animate-spin" />
                    </>
                  ) : (
                    <>
                      <Download size={14} /> PDF
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Totals Summary */}
            {reportData.totals && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6 pt-6 border-t border-slate-800">
                {Object.entries(reportData.totals).map(([key, value]) => (
                  <div key={key}>
                    <p className="text-slate-500 text-xs uppercase tracking-widest font-semibold">
                      {key.replace(/_/g, " ")}
                    </p>
                    <p className="text-white text-lg font-bold mt-1">
                      ₹{typeof value === "number" ? value.toFixed(2) : value}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Data Grid */}
          <div className="bg-slate-900/50 border border-slate-800 rounded-2xl overflow-hidden">
            <FinancialGrid columnDefs={getColumnDefs()} rowData={rowData} />
          </div>
        </div>
      )}

      {/* No Report Message */}
      {!reportData && !isLoading && (
        <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-12 text-center">
          <div className="text-slate-500">
            <p className="text-sm font-medium">Select a report and click "Generate Report" to view data</p>
          </div>
        </div>
      )}
    </div>
  );
}
