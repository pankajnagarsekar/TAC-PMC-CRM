"use client";

import { useMemo, useState, useCallback } from "react";
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
  Coins,
} from "lucide-react";
import RetentionReleaseModal from "@/components/work-orders/RetentionReleaseModal";
import { ColDef, ICellRendererParams, ValueFormatterParams, GridApi } from "ag-grid-community";
import api, { fetcher } from "@/lib/api";
import { useRequestLock } from "@/lib/requestLock";
import FinancialGrid from "@/components/ui/FinancialGrid";
import VersionConflictModal from "@/components/ui/VersionConflictModal";
import { WorkOrder, Project, Vendor, CodeMaster } from "@/types/api";
import { formatCurrency, calculateWOFinancials } from "@/lib/financial";
import { formatDate } from "@tac-pmc/ui";
import LinkedCertificates from "@/components/work-orders/LinkedCertificates";
import ConfirmDialog from "@/components/ui/ConfirmDialog";

interface LineItem {
  sr_no: number;
  description: string;
  qty: number;
  rate: number;
  total: number;
  id?: string;
}

export default function WorkOrderDetailPage() {
  const params = useParams();
  const router = useRouter();
  const woId = params.id as string;

  const [isConflictOpen, setIsConflictOpen] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [showCancelConfirm, setShowCancelConfirm] = useState(false);
  const [isReleaseModalOpen, setIsReleaseModalOpen] = useState(false);

  const {
    data: retentionData,
    mutate: mutateRetention,
  } = useSWR(
    `/api/v1/work-orders/${woId}/retention`,
    fetcher
  );

  const {
    data: releaseLogs,
    mutate: mutateReleases,
  } = useSWR<any[]>(
    `/api/v1/work-orders/${woId}/retention/releases`,
    fetcher
  );
  const [editState, setEditState] = useState({
    category_id: "",
    vendor_id: "",
    description: "",
    discount_value: 0,
    discount_type: "value",
    retention_percent: 0,
  });
  const [editLineItems, setEditLineItems] = useState<LineItem[]>([]);

  const { executeWithLock: executeWoUpdateWithLock } = useRequestLock({
    operationId: "WO_UPDATE",
    timeoutMs: 30000,
  });

  const {
    data: wo,
    mutate: mutateWO,
    isLoading,
  } = useSWR<WorkOrder>(`/api/v1/work-orders/${woId}`, fetcher);

  const { data: project } = useSWR<Project>(
    wo ? `/api/v1/projects/${wo.project_id}` : null,
    fetcher,
  );

  const { data: vendors } = useSWR<Vendor[]>("/api/v1/vendors/", fetcher);
  const { data: categories } = useSWR<CodeMaster[]>(
    "/api/v1/settings/codes?active_only=true",
    fetcher,
  );

  const columnDefs: ColDef<LineItem>[] = useMemo(
    () => [
      { field: "description", headerName: "Description", flex: 2, editable: isEditing },
      {
        field: "qty",
        headerName: "Qty",
        flex: 1,
        editable: isEditing,
        type: "numericColumn",
      },
      {
        field: "rate",
        headerName: "Rate (₹)",
        flex: 1,
        editable: isEditing,
        type: "numericColumn",
        valueFormatter: (p: ValueFormatterParams<LineItem>) => formatCurrency(p.value),
      },
      {
        field: "total",
        headerName: "Total (₹)",
        flex: 1,
        editable: false,
        valueFormatter: (p: ValueFormatterParams<LineItem>) => formatCurrency(p.value),
        cellClass: "bg-slate-800/20 font-bold",
      },
    ],
    [isEditing],
  );

  // Handle grid cell changes
  const handleCellValueChanged = useCallback((event: { data: LineItem; colDef: ColDef<LineItem>; api: GridApi<LineItem> }) => {
    const { data, colDef } = event;

    // When qty or rate changes, recalculate total
    if (colDef.field === "qty" || colDef.field === "rate") {
      const qty = parseFloat(data.qty as unknown as string) || 0;
      const rate = parseFloat(data.rate as unknown as string) || 0;
      data.total = qty * rate;
      event.api.applyTransaction({ update: [data] });
    }

    // Refresh totals and state
    const updatedItems: LineItem[] = [];
    event.api.forEachNode((node: { data?: LineItem }) => {
      if (node.data) updatedItems.push(node.data);
    });
    setEditLineItems(updatedItems);
  }, []);

  const addLineItem = () => {
    setEditLineItems(prev => [
      ...prev,
      {
        id: Math.random().toString(36).substr(2, 9),
        sr_no: prev.length + 1,
        description: "",
        qty: 0,
        rate: 0,
        total: 0
      }
    ]);
  };

  const removeLineItem = (rowIndex: number) => {
    setEditLineItems(prev => {
      const next = [...prev];
      next.splice(rowIndex, 1);
      return next.map((item, idx) => ({ ...item, sr_no: idx + 1 }));
    });
  };

  // Seed edit state when starting edit mode
  const handleStartEdit = useCallback(() => {
    if (!wo) return;
    setEditState({
      category_id: wo.category_id || "",
      vendor_id: wo.vendor_id || "",
      description: wo.description || "",
      discount_value: wo.discount_value !== undefined ? wo.discount_value : (wo.discount || 0),
      discount_type: wo.discount_type || "value",
      retention_percent: wo.retention_percent || 0,
    });
    setEditLineItems(JSON.parse(JSON.stringify(wo.line_items || [])) as LineItem[]);
    setIsEditing(true);
  }, [wo]);

  // Calculate financials for edit mode (Authoritative Logic)
  const editFinancials = useMemo(() => {
    const subtotal = editLineItems.reduce((sum, item) => sum + (item.total || 0), 0);
    
    // Determine rates (fallback to 9% if undefined)
    const cgstRate = Number(project?.project_cgst_percentage ?? 9);
    const sgstRate = Number(project?.project_sgst_percentage ?? 9);

    const financials = calculateWOFinancials(
      subtotal,
      editState.discount_value || 0,
      editState.discount_type as "percentage" | "value" || "value",
      editState.retention_percent || 0,
      cgstRate,
      sgstRate
    );

    return {
      ...financials,
      cgstLabel: cgstRate.toFixed(0),
      sgstLabel: sgstRate.toFixed(0),
      totalPayable: financials.actualPayable,
    };
  }, [editLineItems, editState, project]);

  // Save work order edits
  const handleSave = useCallback(async () => {
    if (!wo) return;
    setIsSaving(true);
    try {
      const response = await executeWoUpdateWithLock(async () => {
        return await api.patch(`/api/v1/work-orders/${woId}`, {
          category_id: editState.category_id || undefined,
          vendor_id: editState.vendor_id || undefined,
          description: editState.description || undefined,
          line_items: editLineItems,
          discount: editFinancials.discount, // Send calculated absolute discount
          discount_value: editState.discount_value,
          discount_type: editState.discount_type,
          retention_percent: editState.retention_percent,
          expected_version: wo.version,
        });
      });

      if (!response) {
        alert("Update is already in progress.");
        return;
      }

      await mutateWO();
      setIsEditing(false);
    } catch (err: unknown) {
      const error = err as { response?: { status?: number; data?: { detail?: string } } };
      if (error.response?.status === 409) {
        setIsConflictOpen(true);
      } else {
        alert(error.response?.data?.detail || "Failed to save work order");
      }
    } finally {
      setIsSaving(false);
    }
  }, [wo, woId, editState, editLineItems, mutateWO, executeWoUpdateWithLock, editFinancials.discount]);

  const handleCancel = useCallback(() => {
    setIsEditing(false);
  }, []);

  const handleStatusAction = async (action: string) => {
    if (action === "cancel" && !showCancelConfirm) {
      setShowCancelConfirm(true);
      return;
    }

    try {
      await api.post(
        `/api/v1/work-orders/${woId}/${action}?expected_version=${wo?.version || 1}`,
      );
      setShowCancelConfirm(false);
      mutateWO();
    } catch (err: unknown) {
      const error = err as { response?: { status?: number; data?: { detail?: string } } };
      if (error.response?.status === 409) {
        setIsConflictOpen(true);
      } else {
        alert(error.response?.data?.detail || `Failed to ${action} work order`);
      }
    }
  };

  const handleExportPDF = async () => {
    if (!wo) return;
    try {
      const response = await api.get(`/api/v1/work-orders/${woId}/export/pdf`, {
        responseType: "blob",
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `WorkOrder-${wo.wo_ref}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch {
      alert("Failed to export PDF");
    }
  };

  if (isLoading || !wo) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="size-8 text-orange-500 animate-spin" />
      </div>
    );
  }

  // cgst/sgst fields store the tax AMOUNT; compute rate % from total_before_tax
  const tbt = Number(wo.total_before_tax) || (Number(wo.subtotal || 0) - Number(wo.discount || 0));
  const detailCgst = tbt > 0 ? Math.round((Number(wo.cgst) / tbt) * 100) : 9;
  const detailSgst = tbt > 0 ? Math.round((Number(wo.sgst) / tbt) * 100) : 9;
  const isClosed = wo.status === "Closed" || wo.status === "Cancelled" || wo.status === "Completed";

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-24 animate-in fade-in duration-500">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-start gap-4">
          <button
            type="button"
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
                type="button"
                onClick={handleSave}
                disabled={isSaving}
                className="admin-only flex items-center gap-1.5 px-4 py-2 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-lg text-xs font-bold hover:bg-emerald-500/20 transition-colors disabled:opacity-50"
              >
                {isSaving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />} Save
              </button>
              <button
                type="button"
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
                  type="button"
                  onClick={handleStartEdit}
                  className="admin-only flex items-center gap-1.5 px-4 py-2 bg-amber-500/10 border border-amber-500/20 text-amber-400 rounded-lg text-xs font-bold hover:bg-amber-500/20 transition-colors"
                >
                  <Edit3 size={14} /> Edit
                </button>
              )}
              {!isClosed && (
                <>
                  {wo.status === "Draft" && (
                    <button
                      type="button"
                      onClick={() => handleStatusAction("submit")}
                      className="admin-only flex items-center gap-1.5 px-4 py-2 bg-blue-500/10 border border-blue-500/20 text-blue-400 rounded-lg text-xs font-bold hover:bg-blue-500/20 transition-colors"
                    >
                      <CheckCircle size={14} /> Submit
                    </button>
                  )}

                  {wo.status === "Pending" && (
                    <>
                      <button
                        type="button"
                        onClick={() => handleStatusAction("approve")}
                        className="admin-only flex items-center gap-1.5 px-4 py-2 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-lg text-xs font-bold hover:bg-emerald-500/20 transition-colors"
                      >
                        <CheckCircle size={14} /> Approve
                      </button>
                      <button
                        type="button"
                        onClick={() => handleStatusAction("reject")}
                        className="admin-only flex items-center gap-1.5 px-4 py-2 bg-red-500/10 border border-red-500/20 text-red-400 rounded-lg text-xs font-bold hover:bg-red-500/20 transition-colors"
                      >
                        <XCircle size={14} /> Reject
                      </button>
                    </>
                  )}

                  {wo.status === "Approved" && (
                    <button
                      type="button"
                      onClick={() => handleStatusAction("complete")}
                      className="admin-only flex items-center gap-1.5 px-4 py-2 bg-blue-500/10 border border-blue-500/20 text-blue-400 rounded-lg text-xs font-bold hover:bg-blue-500/20 transition-colors"
                    >
                      <CheckCircle size={14} /> Mark Completed
                    </button>
                  )}

                  {wo.status === "Completed" && (
                    <button
                      type="button"
                      onClick={() => handleStatusAction("close")}
                      className="admin-only flex items-center gap-1.5 px-4 py-2 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-lg text-xs font-bold hover:bg-emerald-500/20 transition-colors"
                    >
                      <CheckCircle size={14} /> Close Work Order
                    </button>
                  )}

                  {wo.status === "Completed" && retentionData && retentionData.current_balance > 0 && (
                    <button
                      type="button"
                      onClick={() => setIsReleaseModalOpen(true)}
                      className="admin-only flex items-center gap-1.5 px-4 py-2 bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-600 hover:to-orange-700 text-white rounded-lg text-xs font-bold border border-amber-400/20 shadow-md transition-all duration-200 hover:scale-[1.03] active:scale-[0.97]"
                    >
                      <Coins size={14} /> Release Retention
                    </button>
                  )}

                  {(wo.status === "Draft" || wo.status === "Pending" || wo.status === "Approved") && (
                    <button
                      type="button"
                      onClick={() => handleStatusAction("cancel")}
                      className="admin-only flex items-center gap-1.5 px-4 py-2 bg-red-500/10 border border-red-500/20 text-red-400 rounded-lg text-xs font-bold hover:bg-red-500/20 transition-colors"
                    >
                      <XCircle size={14} /> Cancel
                    </button>
                  )}
                </>
              )}

              <button
                type="button"
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
                  aria-label="Category"
                  className="w-full bg-slate-950 border border-slate-700 text-white p-3 rounded-lg focus:outline-none focus:border-amber-500"
                >
                  <option value="">Select Category</option>
                  {categories?.map((cat) => (
                    <option key={cat._id} value={cat._id}>
                      {cat.category_name} ({cat.code})
                    </option>
                  ))}
                </select>
              ) : (
                <div className="text-white font-medium bg-slate-950 p-3 rounded-lg border border-slate-800/50">
                  {categories ?
                    (categories.find((c) => c._id === wo.category_id)?.category_name || wo.category_name || "Unknown Category") :
                    (wo.category_name || <Loader2 size={14} className="animate-spin" />)
                  }
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
                  aria-label="Vendor"
                  className="w-full bg-slate-950 border border-slate-700 text-white p-3 rounded-lg focus:outline-none focus:border-amber-500"
                >
                  <option value="">Select Vendor</option>
                  {vendors?.map((vendor) => (
                    <option key={vendor._id || vendor.id} value={vendor._id || vendor.id}>
                      {vendor.name}
                    </option>
                  ))}
                </select>
              ) : (
                <div className="text-white font-medium bg-slate-950 p-3 rounded-lg border border-slate-800/50">
                  {vendors ?
                    (vendors.find((v) => (v._id || v.id) === wo.vendor_id)?.name || wo.vendor_name || "Unknown Vendor") :
                    (wo.vendor_name || <Loader2 size={14} className="animate-spin" />)
                  }
                </div>
              )}
            </div>


            <div>
              <label htmlFor="edit_description" className="block text-[10px] uppercase tracking-widest text-slate-500 mb-1">
                Description of Work
              </label>
              {isEditing ? (
                <textarea
                  id="edit_description"
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

            <div className="flex justify-between items-center text-slate-400 p-2">
              <span>Discount:</span>
              {isEditing ? (
                <div className="flex items-center gap-2 bg-slate-950 border border-slate-700 rounded p-1">
                  <select
                    value={editState.discount_type}
                    onChange={(e) => {
                      const type = e.target.value as "percentage" | "value";
                      setEditState({
                        ...editState,
                        discount_type: type,
                        discount_value: 0,
                      });
                    }}
                    aria-label="Discount Type"
                    className="bg-transparent text-slate-400 text-xs outline-none cursor-pointer pr-1 border-r border-slate-800"
                  >
                    <option value="value" className="bg-slate-950 text-white">₹ Value</option>
                    <option value="percentage" className="bg-slate-950 text-white">% Percent</option>
                  </select>
                  <input
                    type="number"
                    value={editState.discount_value || ""}
                    onChange={(e) => {
                      const val = parseFloat(e.target.value) || 0;
                      const maxLimit = editState.discount_type === "percentage" ? 100 : editFinancials.subtotal;
                      setEditState({
                        ...editState,
                        discount_value: Math.max(0, Math.min(val, maxLimit)),
                      });
                    }}
                    aria-label="Discount Value"
                    className="w-24 bg-transparent text-white text-right focus:outline-none"
                    placeholder="0.00"
                  />
                </div>
              ) : (
                <span className="font-mono text-white">
                  -{formatCurrency(wo.discount || 0)} {wo.discount_type === "percentage" ? `(${wo.discount_value}%)` : ""}
                </span>
              )}
            </div>

            <div className="flex justify-between text-slate-400 p-2 bg-slate-800/20 rounded">
              <span className="font-medium">Total Before Tax:</span>
              <span className="font-mono text-white font-medium">
                {formatCurrency(isEditing ? editFinancials.totalBeforeTax : (wo.total_before_tax || ((wo.subtotal || 0) - (wo.discount || 0))))}
              </span>
            </div>

            <div className="flex justify-between text-slate-500 px-2 py-1">
              <span>CGST ({isEditing ? editFinancials.cgstLabel : detailCgst}%):</span>
              <span className="font-mono text-slate-300">
                {formatCurrency(isEditing ? editFinancials.cgst : (tbt * (detailCgst / 100)))}
              </span>
            </div>

            <div className="flex justify-between text-slate-500 px-2 py-1">
              <span>SGST ({isEditing ? editFinancials.sgstLabel : detailSgst}%):</span>
              <span className="font-mono text-slate-300">
                {formatCurrency(isEditing ? editFinancials.sgst : (tbt * (detailSgst / 100)))}
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
                    aria-label="Retention Percentage"
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

            <div className="flex justify-between items-center text-emerald-500 font-bold p-3 bg-emerald-500/5 rounded-lg border border-orange-500/10 mb-2">
              <span>Total Payable</span>
              <span className="font-mono text-lg">
                {formatCurrency(isEditing ? editFinancials.totalPayable : wo.total_payable || 0)}
              </span>
            </div>

            {retentionData && (
              <div className="border-t border-slate-800/60 pt-4 mt-4 space-y-3">
                <div className="flex justify-between text-slate-400 px-2 py-1">
                  <span>Retention Held (Paid PCs):</span>
                  <span className="font-mono text-white">
                    {formatCurrency(retentionData.total_held)}
                  </span>
                </div>
                <div className="flex justify-between text-slate-400 px-2 py-1">
                  <span>Retention Released:</span>
                  <span className="font-mono text-emerald-400">
                    -{formatCurrency(retentionData.total_released)}
                  </span>
                </div>
                <div className="flex justify-between items-center text-amber-500 font-bold p-3 bg-amber-500/5 rounded-lg border border-amber-500/10 mt-2">
                  <span>Net Retained Balance:</span>
                  <span className="font-mono text-lg text-amber-500">
                    {formatCurrency(retentionData.current_balance)}
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Grid */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl relative">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-sm font-bold text-slate-400 uppercase tracking-widest flex items-center gap-2">
            <FileText size={16} /> Bill of Quantities {!isEditing && "(Read-Only)"}
          </h2>
          {isEditing && (
            <button
              type="button"
              onClick={addLineItem}
              className="text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 px-3 py-1.5 rounded transition-colors"
            >
              + Add Row
            </button>
          )}
        </div>

        <FinancialGrid
          rowData={
            isEditing
              ? editLineItems
              : (wo?.line_items && wo.line_items.length > 0)
                ? wo.line_items
                : ((wo?.subtotal || 0) > 0
                  ? [{
                      sr_no: 1,
                      description: wo?.description || "Work Order Scope Execution",
                      qty: 1,
                      rate: wo?.subtotal || 0,
                      total: wo?.subtotal || 0,
                    }]
                  : [])
          }
          columnDefs={[
            ...columnDefs,
            ...(isEditing ? [{
              headerName: "",
              width: 50,
              pinned: "right" as const,
              cellRenderer: (p: ICellRendererParams<LineItem>) => (
                <button
                  type="button"
                  onClick={() => p.node.rowIndex != null && removeLineItem(p.node.rowIndex)}
                  className="text-red-500 hover:text-red-400 flex items-center justify-center h-full w-full"
                >
                  <X size={14} />
                </button>
              )
            }] : [])
          ]}
          editable={isEditing}
          showSrNo={true}
          height="300px"
          onCellValueChanged={isEditing ? handleCellValueChanged : undefined}
        />
      </div>

      <VersionConflictModal
        isOpen={isConflictOpen}
        setIsOpen={setIsConflictOpen}
        onReload={() => mutateWO()}
      />

      {wo && <LinkedCertificates projectId={wo.project_id} workOrderId={wo._id} />}

      {/* Retention Release History */}
      {releaseLogs && releaseLogs.length > 0 && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl mt-6 space-y-4">
          <h2 className="text-sm font-bold text-slate-400 uppercase tracking-widest flex items-center gap-2 border-b border-slate-800 pb-2">
            <Coins size={16} className="text-orange-500" /> Retention Release History
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left text-slate-400">
              <thead className="text-[10px] text-slate-500 uppercase tracking-wider bg-slate-950 border-b border-slate-800">
                <tr>
                  <th scope="col" className="px-4 py-3">Release Date</th>
                  <th scope="col" className="px-4 py-3">Release Ref</th>
                  <th scope="col" className="px-4 py-3">Notes</th>
                  <th scope="col" className="px-4 py-3 text-right">Amount Released</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {releaseLogs.map((log: any) => (
                  <tr key={log.id} className="hover:bg-slate-800/10">
                    <td className="px-4 py-3.5 font-mono text-white text-xs">
                      {formatDate(log.release_date)}
                    </td>
                    <td className="px-4 py-3.5 font-medium text-slate-200">
                      {log.release_reference}
                    </td>
                    <td className="px-4 py-3.5 text-xs text-slate-400 truncate max-w-xs">
                      {log.notes || "—"}
                    </td>
                    <td className="px-4 py-3.5 text-right font-mono text-emerald-400 font-bold">
                      {formatCurrency(log.amount_released)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <ConfirmDialog
        isOpen={showCancelConfirm}
        onClose={() => setShowCancelConfirm(false)}
        onConfirm={() => handleStatusAction("cancel")}
        title="Cancel Work Order"
        description="Are you sure you want to cancel this work order? This will release all committed funds back to the project budget. This action is permanent and will be logged for auditing."
        confirmText="Cancel Order"
        variant="danger"
      />

      <RetentionReleaseModal
        isOpen={isReleaseModalOpen}
        onClose={() => setIsReleaseModalOpen(false)}
        onSuccess={async () => {
          await mutateRetention();
          await mutateReleases();
          mutateWO();
        }}
        woId={woId}
        totalHeld={retentionData?.total_held || 0}
        currentBalance={retentionData?.current_balance || 0}
      />
    </div>
  );
}
