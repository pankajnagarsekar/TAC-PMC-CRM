"use client";

import { useMemo, useState, useCallback, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import useSWR from "swr";
import {
  ArrowLeft,
  Loader2,
  Edit3,
  XCircle,
  CheckCircle,
  FileText,
  Save,
  X,
  Download,
} from "lucide-react";
import { ColDef } from "ag-grid-community";
import api, { fetcher } from "@/lib/api";
import FinancialGrid from "@/components/ui/FinancialGrid";
import VersionConflictModal from "@/components/ui/VersionConflictModal";
import { WorkOrder, Project, Vendor, CodeMaster } from "@/types/api";
import { formatCurrency, formatDate } from "@tac-pmc/ui";
import LinkedCertificates from "@/components/work-orders/LinkedCertificates";

interface LineItem {
  sr_no: number;
  description: string;
  qty: number;
  rate: number;
  total: number;
}

export default function WorkOrderDetailPage() {
  const params = useParams();
  const router = useRouter();
  const woId = params.id as string;

  const [isConflictOpen, setIsConflictOpen] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [editState, setEditState] = useState({
    category_id: "",
    vendor_id: "",
    description: "",
    discount: 0,
    retention_percent: 0,
  });
  const [editLineItems, setEditLineItems] = useState<LineItem[]>([]);

  const {
    data: wo,
    mutate: mutateWO,
    isLoading,
  } = useSWR<WorkOrder>(`/api/work-orders/${woId}`, fetcher);

  const { data: project } = useSWR<Project>(
    wo ? `/api/projects/${wo.project_id}` : null,
    fetcher,
  );

  const { data: vendors } = useSWR<Vendor[]>("/api/vendors", fetcher);
  const { data: categories } = useSWR<CodeMaster[]>(
    "/api/codes?active_only=true",
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

  // Seed edit state when starting edit mode
  const handleStartEdit = useCallback(() => {
    if (!wo) return;
    setEditState({
      category_id: wo.category_id || "",
      vendor_id: wo.vendor_id || "",
      description: wo.description || "",
      discount: wo.discount || 0,
      retention_percent: wo.retention_percent || 0,
    });
    setEditLineItems((wo.line_items || []) as LineItem[]);
    setIsEditing(true);
  }, [wo]);

  // Calculate financials for edit mode
  const editFinancials = useMemo(() => {
    const subtotal = editLineItems.reduce((sum, item) => sum + (item.total || 0), 0);
    const discount = editState.discount || 0;
    const totalBeforeTax = subtotal - discount;
    const cgstRate = (wo?.cgst || 9) / 100;
    const sgstRate = (wo?.sgst || 9) / 100;
    const cgst = totalBeforeTax * cgstRate;
    const sgst = totalBeforeTax * sgstRate;
    const grandTotal = totalBeforeTax + cgst + sgst;
    const retentionAmount = grandTotal * ((editState.retention_percent || 0) / 100);
    const totalPayable = grandTotal - retentionAmount;

    return {
      subtotal,
      discount,
      totalBeforeTax,
      cgst,
      sgst,
      grandTotal,
      retentionAmount,
      totalPayable,
    };
  }, [editLineItems, editState, wo?.cgst, wo?.sgst]);

  // Save work order edits
  const handleSave = useCallback(async () => {
    if (!wo) return;
    setIsSaving(true);
    try {
      await api.put(`/api/work-orders/${woId}`, {
        category_id: editState.category_id || undefined,
        vendor_id: editState.vendor_id || undefined,
        description: editState.description || undefined,
        line_items: editLineItems,
        discount: editState.discount,
        retention_percent: editState.retention_percent,
        expected_version: wo.version,
      });
      await mutateWO();
      setIsEditing(false);
    } catch (err: any) {
      if (err.response?.status === 409) {
        setIsConflictOpen(true);
      } else {
        alert(err.response?.data?.detail || "Failed to save work order");
      }
    } finally {
      setIsSaving(false);
    }
  }, [wo, woId, editState, editLineItems, mutateWO]);

  const handleCancel = useCallback(() => {
    setIsEditing(false);
  }, []);

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

  const handleExportPDF = async () => {
    if (!wo) return;
    try {
      const response = await api.get(`/api/work-orders/${woId}/export`, {
        responseType: "blob",
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `WorkOrder-${wo.wo_ref}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      alert("Failed to export PDF");
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
                className={`px-3 py-1 rounded-full text-[10px] font-bold uppercase ${wo.status === "Draft"
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
          {isEditing ? (
            <>
              <button
                onClick={handleSave}
                disabled={isSaving}
                className="admin-only flex items-center gap-1.5 px-4 py-2 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-lg text-xs font-bold hover:bg-emerald-500/20 transition-colors disabled:opacity-50"
              >
                {isSaving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />} Save
              </button>
              <button
                onClick={handleCancel}
                className="flex items-center gap-1.5 px-4 py-2 bg-slate-700/50 border border-slate-600/50 text-slate-300 rounded-lg text-xs font-bold hover:bg-slate-700 transition-colors"
              >
                <X size={14} /> Cancel
              </button>
            </>
          ) : (
            <>
              {!isClosed && (
                <button
                  onClick={handleStartEdit}
                  className="admin-only flex items-center gap-1.5 px-4 py-2 bg-amber-500/10 border border-amber-500/20 text-amber-400 rounded-lg text-xs font-bold hover:bg-amber-500/20 transition-colors"
                >
                  <Edit3 size={14} /> Edit
                </button>
              )}
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
                onClick={handleExportPDF}
                className="flex items-center gap-1.5 px-4 py-2 bg-slate-800 border border-slate-700 text-slate-300 rounded-lg text-xs font-bold hover:bg-slate-700 transition-colors"
              >
                <Download size={14} /> Download PDF
              </button>
            </>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Core Details */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-6 shadow-xl">
          <h2 className="text-sm font-bold text-slate-400 uppercase tracking-widest border-b border-slate-800 pb-2">
            Information {isEditing && <span className="text-amber-400">(Editing)</span>}
          </h2>

          <div className="space-y-4">
            <div>
              <span className="block text-[10px] uppercase tracking-widest text-slate-500 mb-1">
                Category
              </span>
              {isEditing ? (
                <select
                  value={editState.category_id}
                  onChange={(e) => setEditState({ ...editState, category_id: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-700 text-white p-3 rounded-lg focus:outline-none focus:border-amber-500"
                >
                  <option value="">Select Category</option>
                  {categories?.map((cat) => (
                    <option key={cat._id} value={cat._id}>
                      {cat.description}
                    </option>
                  ))}
                </select>
              ) : (
                <div className="text-white font-medium bg-slate-950 p-3 rounded-lg border border-slate-800/50">
                  {categories?.find((c) => c._id === wo.category_id)?.category_name || wo.category_id}
                </div>
              )}
            </div>

            <div>
              <span className="block text-[10px] uppercase tracking-widest text-slate-500 mb-1">
                Vendor
              </span>
              {isEditing ? (
                <select
                  value={editState.vendor_id}
                  onChange={(e) => setEditState({ ...editState, vendor_id: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-700 text-white p-3 rounded-lg focus:outline-none focus:border-amber-500"
                >
                  <option value="">Select Vendor</option>
                  {vendors?.map((vendor) => (
                    <option key={vendor._id} value={vendor._id}>
                      {vendor.name}
                    </option>
                  ))}
                </select>
              ) : (
                <div className="text-white font-medium bg-slate-950 p-3 rounded-lg border border-slate-800/50">
                  {vendors?.find((v) => v._id === wo.vendor_id)?.name || wo.vendor_id}
                </div>
              )}
            </div>

            <div>
              <span className="block text-[10px] uppercase tracking-widest text-slate-500 mb-1">
                Description of Work
              </span>
              {isEditing ? (
                <textarea
                  value={editState.description}
                  onChange={(e) => setEditState({ ...editState, description: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-700 text-white p-3 rounded-lg focus:outline-none focus:border-amber-500 min-h-24"
                />
              ) : (
                <div className="text-white text-sm bg-slate-950 p-3 rounded-lg border border-slate-800/50 min-h-24">
                  {wo.description || "No description provided."}
                </div>
              )}
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
            Financial Breakdown {isEditing && <span className="text-amber-400">(Live)</span>}
          </h2>

          <div className="space-y-3 text-sm">
            <div className="flex justify-between text-slate-400 p-2">
              <span>Subtotal:</span>
              <span className="font-mono text-white">
                {formatCurrency(isEditing ? editFinancials.subtotal : wo.subtotal || 0)}
              </span>
            </div>

            <div className="flex justify-between text-slate-400 p-2">
              <span>Discount:</span>
              {isEditing ? (
                <input
                  type="number"
                  value={editState.discount}
                  onChange={(e) => setEditState({ ...editState, discount: parseFloat(e.target.value) || 0 })}
                  className="w-32 bg-slate-950 border border-slate-700 text-white p-1 rounded text-right focus:outline-none focus:border-amber-500"
                />
              ) : (
                <span className="font-mono text-white">
                  -{formatCurrency(wo.discount || 0)}
                </span>
              )}
            </div>

            <div className="flex justify-between text-slate-400 p-2 bg-slate-800/20 rounded">
              <span className="font-medium">Total Before Tax:</span>
              <span className="font-mono text-white font-medium">
                {formatCurrency(isEditing ? editFinancials.totalBeforeTax : wo.total_before_tax || 0)}
              </span>
            </div>

            <div className="flex justify-between text-slate-500 px-2 py-1">
              <span>CGST:</span>
              <span className="font-mono text-slate-300">
                {formatCurrency(isEditing ? editFinancials.cgst : wo.cgst || 0)}
              </span>
            </div>

            <div className="flex justify-between text-slate-500 px-2 py-1">
              <span>SGST:</span>
              <span className="font-mono text-slate-300">
                {formatCurrency(isEditing ? editFinancials.sgst : wo.sgst || 0)}
              </span>
            </div>

            <div className="flex justify-between items-center text-orange-500 font-bold p-3 bg-orange-500/5 rounded-lg border border-orange-500/10 mt-2">
              <span>Grand Total:</span>
              <span className="font-mono text-lg">
                {formatCurrency(isEditing ? editFinancials.grandTotal : wo.grand_total || 0)}
              </span>
            </div>

            <div className="flex justify-between text-slate-400 px-2 py-1 mt-4 border-t border-slate-800/50 pt-4">
              <span>Retention:</span>
              {isEditing ? (
                <div className="flex gap-2">
                  <input
                    type="number"
                    value={editState.retention_percent}
                    onChange={(e) => setEditState({ ...editState, retention_percent: parseFloat(e.target.value) || 0 })}
                    className="w-16 bg-slate-950 border border-slate-700 text-white p-1 rounded text-right focus:outline-none focus:border-amber-500"
                  />
                  <span className="text-white">% = -{formatCurrency(editFinancials.retentionAmount)}</span>
                </div>
              ) : (
                <span className="font-mono">
                  -{formatCurrency(wo.retention_amount || 0)}
                </span>
              )}
            </div>

            <div className="flex justify-between items-center text-emerald-500 font-bold p-3 bg-emerald-500/5 rounded-lg border border-emerald-500/10 mb-2">
              <span>Total Payable:</span>
              <span className="font-mono text-lg">
                {formatCurrency(isEditing ? editFinancials.totalPayable : wo.total_payable || 0)}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Grid */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl relative">
        <h2 className="text-sm font-bold text-slate-400 uppercase tracking-widest mb-4 flex items-center gap-2">
          <FileText size={16} /> Bill of Quantities {!isEditing && "(Read-Only)"}
        </h2>

        <FinancialGrid
          rowData={isEditing ? editLineItems : wo.line_items || []}
          columnDefs={columnDefs}
          editable={isEditing}
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
