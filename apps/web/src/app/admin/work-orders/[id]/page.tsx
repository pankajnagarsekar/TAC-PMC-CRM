"use client";

import { useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import useSWR from "swr";
import {
  ArrowLeft,
  Loader2,
  Edit3,
  Printer,
  XCircle,
  CheckCircle,
  FileText,
} from "lucide-react";
import { ColDef } from "ag-grid-community";
import api, { fetcher } from "@/lib/api";
import FinancialGrid from "@/components/ui/FinancialGrid";
import VersionConflictModal from "@/components/ui/VersionConflictModal";
import { WorkOrder, Project } from "@/types/api";
import { formatCurrency, formatDate } from "@tac-pmc/ui";
import LinkedCertificates from "@/components/work-orders/LinkedCertificates";

export default function WorkOrderDetailPage() {
  const params = useParams();
  const router = useRouter();
  const woId = params.id as string;

  const [isConflictOpen, setIsConflictOpen] = useState(false);

  const {
    data: wo,
    mutate: mutateWO,
    isLoading,
  } = useSWR<WorkOrder>(`/api/work-orders/${woId}`, fetcher);

  const { data: project } = useSWR<Project>(
    wo ? `/api/projects/${wo.project_id}` : null,
    fetcher,
  );

  const columnDefs: ColDef<any>[] = useMemo(
    () => [
      { field: "description", headerName: "Description", flex: 2 },
      {
        field: "qty",
        headerName: "Qty",
        flex: 1,
      },
      {
        field: "rate",
        headerName: "Rate (₹)",
        flex: 1,
        valueFormatter: (p: any) => formatCurrency(p.value),
      },
      {
        field: "total",
        headerName: "Total (₹)",
        flex: 1,
        valueFormatter: (p: any) => formatCurrency(p.value),
        cellClass: "bg-slate-800/20 font-bold",
      },
    ],
    [],
  );

  const handleStatusChange = async (newStatus: string) => {
    try {
      await api.patch(
        `/api/work-orders/${woId}/status?status=${newStatus}&expected_version=${wo?.version || 1}`,
      );
      mutateWO();
    } catch (err: any) {
      if (err.response?.status === 409) {
        setIsConflictOpen(true);
      } else {
        alert(err.response?.data?.detail || "Failed to update status");
      }
    }
  };

  const handlePrintPDF = async () => {
    try {
      const response = await api.get(`/api/work-orders/${woId}/export/pdf`, {
        responseType: "blob",
      });
      const blob = new Blob([response.data], { type: "application/pdf" });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `WO_${wo?.wo_ref || woId}.pdf`;
      link.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Failed to export PDF", err);
      alert("Failed to generate PDF");
    }
  };

  if (isLoading || !wo) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 text-orange-500 animate-spin" />
      </div>
    );
  }

  const isClosed = wo.status === "Closed" || wo.status === "Cancelled";

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-24 animate-in fade-in duration-500">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-start gap-4">
          <button
            onClick={() => router.back()}
            className="text-slate-400 hover:text-white transition-colors mt-1"
          >
            <ArrowLeft size={20} />
          </button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-white tracking-widest font-mono text-orange-500">
                {wo.wo_ref}
              </h1>
              <div
                className={`px-3 py-1 rounded-full text-[10px] font-bold uppercase ${
                  wo.status === "Draft"
                    ? "bg-slate-500/10 text-slate-400 border border-slate-500/20"
                    : wo.status === "Pending"
                      ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                      : wo.status === "Completed"
                        ? "bg-blue-500/10 text-blue-400 border border-blue-500/20"
                        : wo.status === "Closed"
                          ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                          : "bg-red-500/10 text-red-400 border border-red-500/20"
                }`}
              >
                {wo.status}
              </div>
            </div>
            <p className="text-slate-400 text-sm mt-1">
              Project:{" "}
              <span className="text-white">
                {project?.project_name || wo.project_id}
              </span>
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {!isClosed && (
            <>
              {wo.status !== "Completed" && (
                <button
                  onClick={() => handleStatusChange("Completed")}
                  className="admin-only flex items-center gap-1.5 px-4 py-2 bg-blue-500/10 border border-blue-500/20 text-blue-400 rounded-lg text-xs font-bold hover:bg-blue-500/20 transition-colors"
                >
                  <CheckCircle size={14} /> Mark Completed
                </button>
              )}
              <button
                onClick={() => handleStatusChange("Cancelled")}
                className="admin-only flex items-center gap-1.5 px-4 py-2 bg-red-500/10 border border-red-500/20 text-red-400 rounded-lg text-xs font-bold hover:bg-red-500/20 transition-colors"
              >
                <XCircle size={14} /> Cancel
              </button>
            </>
          )}

          <button
            onClick={handlePrintPDF}
            className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg text-xs font-bold transition-colors"
          >
            <Printer size={14} /> Print PDF
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Core Details */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-6 shadow-xl">
          <h2 className="text-sm font-bold text-slate-400 uppercase tracking-widest border-b border-slate-800 pb-2">
            Information
          </h2>

          <div className="space-y-4">
            <div>
              <span className="block text-[10px] uppercase tracking-widest text-slate-500 mb-1">
                Vendor Reference
              </span>
              <div className="text-white font-medium bg-slate-950 p-3 rounded-lg border border-slate-800/50">
                {wo.vendor_id}
              </div>
            </div>

            <div>
              <span className="block text-[10px] uppercase tracking-widest text-slate-500 mb-1">
                Description of Work
              </span>
              <div className="text-white text-sm bg-slate-950 p-3 rounded-lg border border-slate-800/50 min-h-24">
                {wo.description || "No description provided."}
              </div>
            </div>

            <div>
              <span className="block text-[10px] uppercase tracking-widest text-slate-500 mb-1">
                Important Dates
              </span>
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800/50">
                  <span className="text-xs text-slate-500 block mb-0.5">
                    Created On
                  </span>
                  <span className="text-white text-sm font-mono">
                    {wo.created_at ? formatDate(wo.created_at) : "N/A"}
                  </span>
                </div>
                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800/50">
                  <span className="text-xs text-slate-500 block mb-0.5">
                    Last Updated
                  </span>
                  <span className="text-white text-sm font-mono">
                    {wo.updated_at ? formatDate(wo.updated_at) : "N/A"}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Financial Detail */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-4 shadow-xl">
          <h2 className="text-sm font-bold text-slate-400 uppercase tracking-widest border-b border-slate-800 pb-2">
            Financial Breakdown
          </h2>

          <div className="space-y-3 text-sm">
            <div className="flex justify-between text-slate-400 p-2">
              <span>Subtotal:</span>
              <span className="font-mono text-white">
                {formatCurrency(wo.subtotal || 0)}
              </span>
            </div>

            <div className="flex justify-between text-slate-400 p-2">
              <span>Discount:</span>
              <span className="font-mono text-white">
                -{formatCurrency(wo.discount || 0)}
              </span>
            </div>

            <div className="flex justify-between text-slate-400 p-2 bg-slate-800/20 rounded">
              <span className="font-medium">Total Before Tax:</span>
              <span className="font-mono text-white font-medium">
                {formatCurrency(wo.total_before_tax || 0)}
              </span>
            </div>

            <div className="flex justify-between text-slate-500 px-2 py-1">
              <span>CGST:</span>
              <span className="font-mono text-slate-300">
                {formatCurrency(wo.cgst || 0)}
              </span>
            </div>

            <div className="flex justify-between text-slate-500 px-2 py-1">
              <span>SGST:</span>
              <span className="font-mono text-slate-300">
                {formatCurrency(wo.sgst || 0)}
              </span>
            </div>

            <div className="flex justify-between items-center text-orange-500 font-bold p-3 bg-orange-500/5 rounded-lg border border-orange-500/10 mt-2">
              <span>Grand Total:</span>
              <span className="font-mono text-lg">
                {formatCurrency(wo.grand_total || 0)}
              </span>
            </div>

            <div className="flex justify-between text-slate-400 px-2 py-1 mt-4 border-t border-slate-800/50 pt-4">
              <span>Retention ({wo.retention_percent}%):</span>
              <span className="font-mono">
                -{formatCurrency(wo.retention_amount || 0)}
              </span>
            </div>

            <div className="flex justify-between items-center text-emerald-500 font-bold p-3 bg-emerald-500/5 rounded-lg border border-emerald-500/10 mb-2">
              <span>Total Payable:</span>
              <span className="font-mono text-lg">
                {formatCurrency(wo.total_payable || 0)}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Grid */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl relative">
        <h2 className="text-sm font-bold text-slate-400 uppercase tracking-widest mb-4 flex items-center gap-2">
          <FileText size={16} /> Bill of Quantities (Read-Only)
        </h2>

        <FinancialGrid
          rowData={wo.line_items || []}
          columnDefs={columnDefs}
          editable={false}
          showSrNo={true}
          height="300px"
        />
      </div>

      <VersionConflictModal
        isOpen={isConflictOpen}
        setIsOpen={setIsConflictOpen}
        onReload={() => mutateWO()}
      />

      <LinkedCertificates projectId={wo.project_id} workOrderId={wo._id} />
    </div>
  );
}
