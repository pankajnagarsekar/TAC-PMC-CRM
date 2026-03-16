"use client";

import { use, useState } from "react";
import { useRouter } from "next/navigation";
import useSWR from "swr";
import Link from "next/link";
import {
  ArrowLeft,
  CheckCircle,
  Lock,
  Building2,
  FileText,
  Printer,
  AlertTriangle,
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@tac-pmc/ui";
import { ColDef } from "ag-grid-community";

import api, { fetcher } from "@/lib/api";
import { useProjectStore } from "@/store/projectStore";
import FinancialGrid from "@/components/ui/FinancialGrid";
import VersionConflictModal from "@/components/ui/VersionConflictModal";
import { formatCurrency, formatDate } from "@tac-pmc/ui";
import { PaymentCertificate, CodeMaster, Vendor, WorkOrder } from "@/types/api";

export default function PaymentCertificateDetail({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const router = useRouter();
  const { id } = use(params);
  const { activeProject } = useProjectStore();

  const [isClosing, setIsClosing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isConflictOpen, setIsConflictOpen] = useState(false);
  const [showCloseDialog, setShowCloseDialog] = useState(false);
  const [closeSuccessSummary, setCloseSuccessSummary] = useState<any>(null);

  // Fetchers
  const {
    data: pc,
    isLoading,
    mutate,
  } = useSWR<PaymentCertificate>(`/api/payment-certificates/${id}`, fetcher);

  const { data: categories } = useSWR<CodeMaster[]>(
    "/api/codes?active_only=true",
    fetcher,
  );
  const { data: vendors } = useSWR<Vendor[]>("/api/vendors", fetcher);
  const { data: woResponse } = useSWR(
    activeProject
      ? `/api/projects/${activeProject.project_id}/work-orders`
      : null,
    fetcher,
  );

  const workOrders: WorkOrder[] = woResponse?.items || [];

  if (isLoading)
    return (
      <div className="text-slate-400 p-8 text-center animate-pulse">
        Loading Certificate Bounds...
      </div>
    );
  if (!pc)
    return (
      <div className="text-red-400 p-8 text-center">
        Certificate Definition Not Found
      </div>
    );

  const getCategoryName = (cid: string) =>
    categories?.find((c) => c._id === cid)?.category_name || cid;
  const getVendorName = (vid: string) =>
    vendors?.find((v) => v._id === vid)?.name || vid;
  const getWoRef = (woid: string) =>
    workOrders.find((w) => w._id === woid)?.wo_ref || woid;

  const handleClose = async () => {
    try {
      setIsClosing(true);
      setError(null);
      const response = await api.patch(
        `/api/payment-certificates/${id}/close?expected_version=${pc.version || 1}`,
      );

      // Capture financial summary from response
      if (response.data.financial_summary) {
        setCloseSuccessSummary(response.data.financial_summary);
      }

      await mutate(); // Refresh the internal cache showing Closed status immediately
    } catch (err: any) {
      if (err.response?.status === 409) {
        setIsConflictOpen(true);
      } else {
        setError(
          err.response?.data?.detail || err.message || "Failed to Close PC.",
        );
      }
    } finally {
      setIsClosing(false);
      setShowCloseDialog(false);
    }
  };

  const handlePrintPDF = async () => {
    try {
      const response = await api.get(
        `/api/payment-certificates/${id}/export/pdf`,
        {
          responseType: "blob",
        },
      );
      const blob = new Blob([response.data], { type: "application/pdf" });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `PC_${pc?.pc_ref || id}.pdf`;
      link.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Failed to export PDF", err);
      alert("Failed to generate PDF");
    }
  };

  const columnDefs: ColDef[] = [
    { field: "sr_no", headerName: "Sr No", width: 80, filter: false },
    {
      field: "scope_of_work",
      headerName: "Scope of Work",
      flex: 2,
      filter: false,
      wrapText: true,
      autoHeight: true,
    },
    { field: "unit", headerName: "Unit", width: 100, filter: false },
    {
      field: "qty",
      headerName: "Quantity",
      width: 120,
      filter: false,
      type: "numericColumn",
    },
    {
      field: "rate",
      headerName: "Rate (₹)",
      width: 150,
      filter: false,
      type: "numericColumn",
      valueFormatter: (p: any) => formatCurrency(p.value),
    },
    {
      field: "total",
      headerName: "Total (₹)",
      width: 150,
      filter: false,
      type: "numericColumn",
      valueFormatter: (p: any) => formatCurrency(p.value),
    },
  ];

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-12 animate-in fade-in duration-500">
      {/* Header Array */}
      <div className="flex justify-between items-start">
        <div className="flex gap-4">
          <Link
            href="/admin/payment-certificates"
            className="p-2 h-fit hover:bg-slate-800 rounded-lg transition-colors text-slate-400 hover:text-white"
          >
            <ArrowLeft size={20} />
          </Link>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-white font-mono">
                {pc.pc_ref}
              </h1>
              <span
                className={`px-2.5 py-1 text-xs font-bold uppercase tracking-widest rounded-full border ${
                  pc.status === "Closed"
                    ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                    : pc.status === "Draft"
                      ? "bg-slate-500/10 text-slate-400 border-slate-500/20"
                      : "bg-amber-500/10 text-amber-400 border-amber-500/20"
                }`}
              >
                {pc.status}
              </span>

              {pc.fund_request ? (
                <span className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-bold text-amber-500 bg-amber-500/5 rounded-full border border-amber-500/20">
                  <FileText size={14} /> Fund Request
                </span>
              ) : (
                <span className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-bold text-blue-400 bg-blue-500/5 rounded-full border border-blue-500/20">
                  <Building2 size={14} /> WO Linked
                </span>
              )}
            </div>
            <p className="text-slate-400 text-sm mt-1">
              Generated on {formatDate(pc.created_at)}
            </p>
          </div>
        </div>

        <div className="flex gap-3">
          <button
            onClick={handlePrintPDF}
            className="flex items-center gap-2 bg-slate-800 hover:bg-slate-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          >
            <Printer size={16} /> Print PDF
          </button>

          {pc.status !== "Closed" && pc.status !== "Cancelled" && (
            <button
              onClick={() => setShowCloseDialog(true)}
              disabled={isClosing}
              className="admin-only flex items-center gap-2 bg-emerald-500 hover:bg-emerald-600 text-white px-4 py-2 rounded-lg font-medium transition-colors shadow-lg disabled:opacity-50"
            >
              {isClosing ? (
                <Lock size={16} className="animate-pulse" />
              ) : (
                <CheckCircle size={16} />
              )}
              Close PC & Commit Ledger
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 text-red-500 p-4 rounded-lg text-sm font-medium">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="md:col-span-2 space-y-6">
          {/* Linked Meta */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl">
            <h2 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-4 border-b border-slate-800 pb-2">
              Target Metadata
            </h2>
            <div className="grid grid-cols-2 gap-6">
              <div>
                <p className="text-xs text-slate-500 mb-1">Category Code</p>
                <p className="text-sm text-white font-medium">
                  {getCategoryName(pc.category_id)}
                </p>
              </div>
              {pc.fund_request ? (
                <div>
                  <p className="text-xs text-slate-500 mb-1">Target Account</p>
                  <p className="text-sm text-white font-medium flex items-center gap-2">
                    <FileText size={16} className="text-amber-500 opacity-80" />
                    Internal Organization Pool
                  </p>
                </div>
              ) : (
                <>
                  <div>
                    <p className="text-xs text-slate-500 mb-1">
                      Linked Work Order
                    </p>
                    <p className="text-sm text-white font-mono font-medium text-emerald-400">
                      {pc.work_order_id
                        ? getWoRef(pc.work_order_id)
                        : "Missing Ref"}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500 mb-1">
                      Assigned Vendor
                    </p>
                    <p className="text-sm text-white font-medium">
                      {pc.vendor_id ? getVendorName(pc.vendor_id) : "Unknown"}
                    </p>
                  </div>
                </>
              )}
            </div>
          </div>

          {/* Grid Block */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
            <div className="p-4 border-b border-slate-800/50 flex justify-between items-center bg-slate-950/50">
              <h2 className="text-sm font-bold text-slate-400 uppercase tracking-wider">
                Line Items Target
              </h2>
              {pc.status === "Closed" && (
                <span className="flex items-center gap-1.5 text-xs text-slate-500">
                  <Lock size={14} /> Read Only
                </span>
              )}
            </div>
            <div className="h-[300px]">
              <FinancialGrid
                rowData={pc.line_items || []}
                columnDefs={columnDefs}
                readOnly={true} // Strictly read only post-commit
                domLayout="normal"
              />
            </div>
          </div>
        </div>

        {/* Financials Readout */}
        <div className="space-y-6">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl sticky top-6">
            <h2 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-6 border-b border-slate-800 pb-2">
              Financial Calculus
            </h2>

            <div className="space-y-4">
              <div className="flex justify-between items-end">
                <span className="text-sm text-slate-400">
                  Subtotal Accumulate
                </span>
                <span className="font-mono text-white tracking-tight">
                  {formatCurrency(pc.subtotal)}
                </span>
              </div>

              {!pc.fund_request && pc.retention_amount > 0 && (
                <div className="flex justify-between items-end text-amber-500/80">
                  <span className="text-sm">Held Retention</span>
                  <span className="font-mono tracking-tight">
                    -{formatCurrency(pc.retention_amount)}
                  </span>
                </div>
              )}

              <div className="flex justify-between items-end text-slate-500">
                <span className="text-sm">CGST Base</span>
                <span className="font-mono tracking-tight">
                  {formatCurrency(pc.cgst)}
                </span>
              </div>
              <div className="flex justify-between items-end text-slate-500 pb-4 border-b border-slate-800">
                <span className="text-sm">SGST Base</span>
                <span className="font-mono tracking-tight">
                  {formatCurrency(pc.sgst)}
                </span>
              </div>

              <div className="flex justify-between items-end pt-2">
                <span className="text-sm text-white font-medium">
                  Grand Execution
                </span>
                <span className="text-xl font-mono text-white font-bold">
                  {formatCurrency(pc.grand_total)}
                </span>
              </div>

              {!pc.fund_request && (
                <div className="flex justify-between items-end pt-2">
                  <span className="text-sm text-emerald-500/80 font-bold uppercase">
                    Total Payable
                  </span>
                  <span className="text-xl font-mono text-emerald-400 font-bold">
                    {formatCurrency(pc.total_payable)}
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
      <VersionConflictModal
        isOpen={isConflictOpen}
        setIsOpen={setIsConflictOpen}
        onReload={() => mutate()}
      />

      {/* Close PC Confirmation Dialog */}
      <Dialog open={showCloseDialog} onOpenChange={setShowCloseDialog}>
        <DialogContent className="bg-slate-950 border-slate-900 text-white max-w-md rounded-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-3 text-xl font-bold">
              <AlertTriangle className="text-amber-500" size={24} />
              Close Payment Certificate
            </DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <p className="text-slate-300">
              Are you absolutely certain you want to Close this Payment
              Certificate? This action will irreversibly update budgets,
              ledgers, and cash positions.
            </p>
            {pc.fund_request && (
              <div className="mt-4 p-3 bg-amber-500/10 border border-amber-500/20 rounded-xl">
                <p className="text-amber-500 text-sm">
                  This is a Fund Request. Closing will inject funds into the
                  petty cash / OVH category.
                </p>
              </div>
            )}
          </div>
          <DialogFooter className="flex gap-3">
            <button
              onClick={() => setShowCloseDialog(false)}
              className="flex-1 px-4 py-2 border border-slate-700 text-slate-300 rounded-xl hover:bg-slate-900 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleClose}
              className="flex-1 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl font-medium transition-colors"
            >
              Yes, Close PC
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Close Success Summary Dialog */}
      <Dialog
        open={!!closeSuccessSummary}
        onOpenChange={() => setCloseSuccessSummary(null)}
      >
        <DialogContent className="bg-slate-950 border-slate-900 text-white max-w-md rounded-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-3 text-xl font-bold">
              <CheckCircle className="text-emerald-500" size={24} />
              Payment Certificate Closed
            </DialogTitle>
          </DialogHeader>
          <div className="py-4 space-y-4">
            <p className="text-slate-300">
              The Payment Certificate has been successfully closed. Updated
              financial positions:
            </p>
            {closeSuccessSummary && (
              <div className="space-y-3">
                {closeSuccessSummary.cash_in_hand !== undefined && (
                  <div className="flex justify-between items-center p-3 bg-slate-900 rounded-xl">
                    <span className="text-slate-400">Cash in Hand</span>
                    <span className="font-mono font-bold text-white">
                      {formatCurrency(closeSuccessSummary.cash_in_hand)}
                    </span>
                  </div>
                )}
                {closeSuccessSummary.allocation_remaining !== undefined && (
                  <div className="flex justify-between items-center p-3 bg-slate-900 rounded-xl">
                    <span className="text-slate-400">Allocation Remaining</span>
                    <span className="font-mono font-bold text-white">
                      {formatCurrency(closeSuccessSummary.allocation_remaining)}
                    </span>
                  </div>
                )}
                {closeSuccessSummary.master_remaining_budget !== undefined && (
                  <div className="flex justify-between items-center p-3 bg-slate-900 rounded-xl">
                    <span className="text-slate-400">Master Remaining</span>
                    <span className="font-mono font-bold text-white">
                      {formatCurrency(
                        closeSuccessSummary.master_remaining_budget,
                      )}
                    </span>
                  </div>
                )}
              </div>
            )}
          </div>
          <DialogFooter>
            <button
              onClick={() => setCloseSuccessSummary(null)}
              className="w-full px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl font-medium transition-colors"
            >
              Done
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
