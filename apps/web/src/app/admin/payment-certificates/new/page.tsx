"use client";

import { useState, useCallback, useMemo, useEffect } from "react";
import { useRouter } from "next/navigation";
import useSWR from "swr";
import {
  ArrowLeft,
  Save,
  AlertTriangle,
  Building2,
  FileText,
} from "lucide-react";
import Link from "next/link";
import type {
  ColDef,
  ValueSetterParams,
  CellValueChangedEvent,
  ICellRendererParams,
} from "ag-grid-community";

import api, { fetcher } from "@/lib/api";
import { calculatePCFinancials, financialRound } from "@/lib/financial";
import { useRequestLock } from "@/lib/requestLock";
import { idempotency } from "@/lib/idempotency";
import { useProjectStore } from "@/store/projectStore";
import FinancialGrid from "@/components/ui/FinancialGrid";
import { formatCurrency } from "@tac-pmc/ui";
import { CodeMaster, WorkOrder } from "@/types/api";
import { v4 as uuidv4 } from "uuid";
import { useUnsavedChanges } from "@/hooks/use-unsaved-changes";
import { useToast } from "@/hooks/use-toast";

// Need a specific interface for PC line items, different from WO
interface PCLineItem {
  id: string; // purely for ag-grid row ID
  sr_no: number;
  scope_of_work: string;
  unit: string;
  qty: number;
  rate: number;
  total: number;
}

export default function NewPaymentCertificatePage() {
  const router = useRouter();
  const { activeProject } = useProjectStore();
  const { toast } = useToast();

  // States
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isDirty, setIsDirty] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [idempotencyKey, setIdempotencyKey] = useState<string>("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  // Guard against unsaved changes
  useUnsavedChanges(isDirty);

  const [isWoLinked, setIsWoLinked] = useState(true);
  const [selectedWoId, setSelectedWoId] = useState<string>("");
  const [selectedCategoryId, setSelectedCategoryId] = useState<string>("");

  const [lineItems, setLineItems] = useState<PCLineItem[]>([]);
  const [retentionPercent, setRetentionPercent] = useState<number>(5);
  const [filterCategoryId, setFilterCategoryId] = useState<string>("");

  // SWR Hooks
  const { data: woResponse } = useSWR(
    activeProject
      ? `/api/v1/work-orders/?project_id=${activeProject.project_id || activeProject._id}`
      : null,
    fetcher,
  );
  const workOrders: WorkOrder[] = useMemo(() => {
    const rawItems = Array.isArray(woResponse) ? woResponse : (woResponse?.items || []);
    let filtered = rawItems.filter((wo: WorkOrder) => wo.status !== "Cancelled");

    if (isWoLinked && filterCategoryId) {
      filtered = filtered.filter((wo: WorkOrder) => wo.category_id === filterCategoryId);
    }

    return filtered;
  }, [woResponse, filterCategoryId, isWoLinked]);

  const { data: woSummary } = useSWR(
    isWoLinked && selectedWoId
      ? `/api/v1/payments/wo-summary/${selectedWoId}`
      : null,
    fetcher,
  );

  const { data: categories } = useSWR<CodeMaster[]>(
    "/api/v1/settings/codes?active_only=true",
    fetcher,
  );
  const fundCategories =
    categories?.filter((c) => c.budget_type === "fund_transfer") || [];

  // Generate idempotency layer on mount
  useEffect(() => {
    idempotency.clear("PC_CREATE");
    setIdempotencyKey(idempotency.generate());
  }, []);

  // Sync Category when WO selected
  useEffect(() => {
    if (isWoLinked && selectedWoId) {
      const wo = workOrders.find((w) => w._id === selectedWoId);
      if (wo) setSelectedCategoryId(wo.category_id);
    }
  }, [isWoLinked, selectedWoId, workOrders]);

  // Calculations Preview
  const { subtotal, retentionAmount, totalPayable, actualPayable, cgstRate, sgstRate, cgstAmount, sgstAmount } =
    useMemo(() => {
      const p = activeProject;
      const cgstPct = p?.project_cgst_percentage ?? 9;
      const sgstPct = p?.project_sgst_percentage ?? 9;

      const rawSub = lineItems.reduce(
        (sum, item) => sum + (Number(item.total) || 0),
        0,
      );

      const fin = calculatePCFinancials(rawSub, retentionPercent, cgstPct, sgstPct);

      return {
        subtotal: fin.subtotal,
        retentionAmount: fin.retentionAmount,
        totalAfterRetention: fin.totalAfterRetention,
        gst: fin.gstAmount,
        totalPayable: fin.grandTotal,
        actualPayable: fin.actualPayable,
        cgstRate: cgstPct,
        sgstRate: sgstPct,
        cgstAmount: fin.cgst,
        sgstAmount: fin.sgst
      };
    }, [lineItems, retentionPercent, activeProject]);

  const isOverCertified = useMemo(() => {
    if (!isWoLinked || !woSummary) return false;
    // Tolerance for minor rounding differences (0.01)
    return totalPayable > (woSummary.remaining_balance + 0.01);
  }, [isWoLinked, woSummary, totalPayable]);

  const { executeWithLock: executePcCreateWithLock } = useRequestLock({
    operationId: "PC_CREATE",
    timeoutMs: 30000,
  });

  const handleSave = async () => {
    if (!activeProject) return;
    if (isWoLinked && !selectedWoId) {
      toast({ title: "Validation Error", description: "Please map to an active Work Order", variant: "destructive" });
      return;
    }
    if (!isWoLinked && !selectedCategoryId) {
      toast({ title: "Validation Error", description: "Fund Requests mandate an active internal category target", variant: "destructive" });
      return;
    }
    if (lineItems.length === 0) {
      toast({ title: "Validation Error", description: "Add at least one line item describing the scope of work", variant: "destructive" });
      return;
    }
    if (isOverCertified && woSummary) {
      toast({ title: "Financial Guard", description: `This certificate (₹${formatCurrency(totalPayable)}) exceeds the remaining Work Order balance (₹${formatCurrency(woSummary.remaining_balance)}).`, variant: "destructive" });
      return;
    }

    try {
      setIsSubmitting(true);
      setError(null);
      setFieldErrors({});

      const wo = isWoLinked ? workOrders.find(w => w._id === selectedWoId) : null;

      const projectId = activeProject.project_id || activeProject._id;
      const payload = {
        project_id: projectId,
        work_order_id: isWoLinked ? selectedWoId : null,
        category_id: !isWoLinked ? selectedCategoryId : (wo?.category_id || undefined),
        vendor_id: wo?.vendor_id || null,
        fund_request: !isWoLinked,
        pc_type: isWoLinked ? "WO_LINKED" : "PETTY_OVH",
        retention_percent: retentionPercent,
        bill_reference: (document.getElementById("bill_reference") as HTMLInputElement)?.value || "",
        bill_date: (document.getElementById("bill_date") as HTMLInputElement)?.value || null,
        tax_invoice_number: (document.getElementById("tax_invoice_number") as HTMLInputElement)?.value || "",
        pmc_comments: (document.getElementById("pmc_comments") as HTMLTextAreaElement)?.value || "",
        service_engineer_name: (document.getElementById("service_engineer_name") as HTMLInputElement)?.value || "",
        line_items: lineItems.map((item, index) => {
          const qty = Math.max(0, Number(item.qty) || 0);
          const rate = Math.max(0, Number(item.rate) || 0);
          return {
            sr_no: index + 1,
            scope_of_work: item.scope_of_work,
            unit: item.unit,
            qty: qty,
            rate: rate,
            total: financialRound(qty * rate),
          };
        }),
        cgst: cgstAmount,
        sgst: sgstAmount,
        idempotency_key: idempotencyKey,
      };


      const res = await executePcCreateWithLock(async () => {
        return await api.post(
          `/api/v1/payments/${projectId}`,
          payload,
          {
            headers: { "Idempotency-Key": idempotencyKey },
          },
        );
      });

      if (!res) {
        setError("Request is already in progress. Please wait.");
        setIsSubmitting(false);
        return;
      }

      setIsDirty(false); // Reset dirty state before navigation
      toast({ title: "Success", description: "Payment Certificate created successfully." });
      router.push(`/admin/payment-certificates/${res.data._id}`);
      router.refresh();
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { detail?: string | { errors?: { field: string; message: string }[] } } } };
      const detail = axiosError.response?.data?.detail;
      const serverError = (axiosError.response?.data as { error?: { message?: string } })?.error;

      if (detail && typeof detail === "object" && "errors" in detail && Array.isArray(detail.errors)) {
        const fieldErrorsObj: Record<string, string> = {};
        detail.errors.forEach((e) => {
          fieldErrorsObj[e.field] = e.message;
        });
        setFieldErrors(fieldErrorsObj);
        toast({ title: "Validation Failed", description: "Please check the highlighted fields.", variant: "destructive" });
      } else {
        const errorMsg = (typeof detail === "string" ? detail : null) ||
          (serverError?.message) ||
          (err as Error).message ||
          "Failed to submit Payment Certificate";
        
        toast({ title: "Submission Failed", description: errorMsg, variant: "destructive" });
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  // AG Grid Hooks
  const columnDefs: ColDef<PCLineItem>[] = [
    {
      field: "sr_no",
      headerName: "Sr No",
      width: 80,
      editable: false,
      valueGetter: (params) => {
        const rowIndex = params.node?.rowIndex;
        return (rowIndex !== undefined && rowIndex !== null) ? rowIndex + 1 : "";
      },
    },
    {
      field: "scope_of_work",
      headerName: "Scope of Work",
      flex: 2,
      editable: true,
      cellEditor: "agLargeTextCellEditor",
      cellEditorPopup: true,
    },
    {
      field: "unit",
      headerName: "Unit (e.g. sqft)",
      width: 120,
      editable: true,
    },
    {
      field: "qty",
      headerName: "Quantity",
      width: 120,
      editable: true,
      type: "numericColumn",
      valueSetter: (params: ValueSetterParams<PCLineItem, number>) => {
        params.data.qty = Number(params.newValue) || 0;
        params.data.total = params.data.qty * params.data.rate;
        return true;
      },
    },
    {
      field: "rate",
      headerName: "Rate (₹)",
      width: 150,
      editable: true,
      type: "numericColumn",
      valueSetter: (params: ValueSetterParams<PCLineItem, number>) => {
        params.data.rate = Number(params.newValue) || 0;
        params.data.total = params.data.qty * params.data.rate;
        return true;
      },
    },
    {
      field: "total",
      headerName: "Total (₹)",
      width: 150,
      editable: false,
      type: "numericColumn",
      valueFormatter: (params) => formatCurrency(params.value || 0),
    },
    {
      headerName: "",
      width: 80,
      cellRenderer: (params: ICellRendererParams<PCLineItem>) => (
        <button
          onClick={() => {
            const rowIndex = params.node?.rowIndex;
            if (rowIndex === undefined || rowIndex === null) return;
            const updated = [...lineItems];
            updated.splice(rowIndex, 1);
            setLineItems(updated);
          }}
          className="admin-only text-red-500 hover:text-red-400 p-1"
          tabIndex={-1}
        >
          Delete
        </button>
      ),
    },
  ];

  const handleAddRow = () => {
    setIsDirty(true);
    setLineItems([
      ...lineItems,
      {
        id: uuidv4(),
        sr_no: 0,
        scope_of_work: "",
        unit: "nos",
        qty: 0,
        rate: 0,
        total: 0,
      },
    ]);
  };

  const handleCellValueChanged = useCallback(
    (event: CellValueChangedEvent<PCLineItem>) => {
      setIsDirty(true);
      setLineItems((prev) => {
        const updated = [...prev];
        const index = updated.findIndex((i) => i.id === event.data.id);
        if (index >= 0) {
          updated[index] = { ...event.data };
        }
        return updated;
      });
    },
    [],
  );

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-12 animate-in fade-in duration-500">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link
            href="/admin/payment-certificates"
            className="p-2 hover:bg-slate-800 rounded-lg transition-colors text-slate-400 hover:text-white"
          >
            <ArrowLeft size={20} />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-white">
              Create Payment Certificate
            </h1>
            <p className="text-slate-400 text-sm">
              Issue new payout request for {activeProject?.project_name}
            </p>
          </div>
        </div>
        <button
          onClick={handleSave}
          disabled={isSubmitting || !activeProject || isOverCertified}
          className="admin-only flex items-center gap-2 bg-emerald-500 hover:bg-emerald-600 disabled:opacity-50 disabled:cursor-not-allowed text-white px-6 py-2 rounded-lg font-medium transition-colors shadow-lg shadow-emerald-500/20"
        >
          {isSubmitting ? (
            <div className="w-5 h-5 border-2 border-white/20 border-t-white rounded-full animate-spin" />
          ) : (
            <Save size={18} />
          )}
          Create Certificate
        </button>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-4 rounded-xl flex items-start gap-3">
          <AlertTriangle className="shrink-0 mt-0.5" size={18} />
          <div>
            <h4 className="font-semibold text-sm">Submission Failed</h4>
            <p className="text-xs opacity-90 mt-1">{error}</p>
          </div>
        </div>
      )}

      {/* Main Form Bounds */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
        {/* Top Controls Tab */}
        <div className="p-6 border-b border-slate-800/50 bg-slate-900/50">
          <div className="flex gap-4 mb-6 p-1 bg-slate-950 rounded-lg w-fit border border-slate-800">
            <button
              onClick={() => {
                setIsDirty(true);
                setIsWoLinked(true);
                setSelectedCategoryId("");
                setError(null);
                setFieldErrors({});
              }}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${isWoLinked ? "bg-slate-800 text-emerald-400 shadow-sm" : "text-slate-400 hover:text-slate-300"}`}
            >
              <span className="flex items-center gap-2">
                <Building2 size={16} /> WO-Linked Payment
              </span>
            </button>
            <button
              onClick={() => {
                setIsDirty(true);
                setIsWoLinked(false);
                setSelectedWoId("");
                setError(null);
                setFieldErrors({});
              }}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${!isWoLinked ? "bg-slate-800 text-amber-400 shadow-sm" : "text-slate-400 hover:text-slate-300"}`}
            >
              <span className="flex items-center gap-2">
                <FileText size={16} /> Internal Fund Request
              </span>
            </button>
          </div>

          <div className="grid grid-cols-2 gap-6">
            {isWoLinked ? (
              <>
                <div className="space-y-2">
                  <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Filter by Category (Optional)
                  </label>
                  <select
                    value={filterCategoryId}
                    onChange={(e) => {
                      setIsDirty(true);
                      setFilterCategoryId(e.target.value);
                      setSelectedWoId(""); // Reset WO when filter changes
                    }}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-emerald-500"
                  >
                    <option value="">All Categories</option>
                    {categories?.map((c) => (
                      <option key={c._id || c.code_id} value={c._id || c.code_id}>
                        {c.category_name} ({c.code})
                      </option>
                    ))}
                  </select>
                </div>

                <div className="space-y-2">
                  <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Select Work Order Link
                  </label>
                  <select
                    value={selectedWoId}
                    onChange={(e) => {
                      setIsDirty(true);
                      setSelectedWoId(e.target.value);
                    }}
                    className={`w-full bg-slate-950 border ${fieldErrors.work_order_id ? "border-red-500" : "border-slate-800"} rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-emerald-500`}
                  >
                    <option value="">Select a WO...</option>
                    {workOrders.map((wo: WorkOrder) => (
                      <option key={wo._id} value={wo._id}>
                        {wo.wo_ref} (Cat:{" "}
                        {
                          categories?.find((c) => (c._id || c.code_id) === wo.category_id)
                            ?.category_name
                        }
                        )
                      </option>
                    ))}
                  </select>
                  {fieldErrors.work_order_id && (
                    <p className="text-[10px] text-red-500 mt-1 uppercase font-bold">
                      {fieldErrors.work_order_id}
                    </p>
                  )}

                  {isWoLinked && woSummary && (
                    <div className="mt-3 p-3 bg-slate-950/50 border border-slate-800 rounded-lg space-y-2 animate-in slide-in-from-top-1 duration-300">
                      <div className="flex justify-between items-center text-[10px] uppercase tracking-wider font-bold">
                        <span className="text-slate-500">Authorized WO Total</span>
                        <span className="text-slate-300 font-mono">{formatCurrency(woSummary.total_authorized)}</span>
                      </div>
                      <div className="flex justify-between items-center text-[10px] uppercase tracking-wider font-bold">
                        <span className="text-slate-500">Previously Certified</span>
                        <span className="text-emerald-500/80 font-mono">{formatCurrency(woSummary.total_certified_to_date)}</span>
                      </div>
                      <div className="flex justify-between items-center text-xs font-bold border-t border-slate-800 pt-2">
                        <span className="text-slate-400">Available Balance</span>
                        <span className={`${isOverCertified ? "text-red-400" : "text-emerald-400"} font-mono`}>
                          {formatCurrency(woSummary.remaining_balance)}
                        </span>
                      </div>
                      {isOverCertified && (
                        <div className="flex items-center gap-2 text-[10px] text-red-400 font-bold bg-red-400/5 p-2 rounded border border-red-400/10 mt-2">
                          <AlertTriangle size={12} />
                          <span>EXCEEDS REMAINING BALANCE BY {formatCurrency(totalPayable - woSummary.remaining_balance)}</span>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </>
            ) : (
              <div className="space-y-2">
                <label className="text-xs font-semibold text-amber-400 uppercase tracking-wider">
                  Fund Request Category (Petty/OVH)
                </label>
                <select
                  value={selectedCategoryId}
                  onChange={(e) => {
                    setIsDirty(true);
                    setSelectedCategoryId(e.target.value);
                  }}
                  className={`w-full bg-amber-500/5 border ${fieldErrors.category_id ? "border-red-500" : "border-amber-500/20"} rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-amber-500`}
                >
                  <option value="">Select a Fund-enabled Category...</option>
                  {fundCategories.map((c) => (
                    <option key={c._id} value={c._id}>
                      {c.code} - {c.category_name}
                    </option>
                  ))}
                </select>
                {fieldErrors.category_id && (
                  <p className="text-[10px] text-red-500 mt-1 uppercase font-bold">
                    {fieldErrors.category_id}
                  </p>
                )}
              </div>
            )}

            <div className="space-y-2">
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Retention Hold %
              </label>
              <div className="relative">
                <input
                  type="number"
                  min={0}
                  value={retentionPercent}
                  onChange={(e) => {
                    setIsDirty(true);
                    setRetentionPercent(Math.max(0, Math.min(100, Number(e.target.value))));
                  }}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-4 pr-8 py-2.5 text-white focus:outline-none focus:border-emerald-500"
                />

                <span className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-500">
                  %
                </span>
              </div>
            </div>
          </div>

          {/* New Mandatory PC Fields */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-6 pt-6 border-t border-slate-800/50">
            <div className="space-y-2">
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Bill Reference (Vendor)
              </label>
              <input
                id="bill_reference"
                type="text"
                placeholder="e.g. VEND/24/001"
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-emerald-500"
              />
            </div>
            <div className="space-y-2">
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Bill Date
              </label>
              <input
                id="bill_date"
                type="date"
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-emerald-500"
              />
            </div>
            <div className="space-y-2">
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Tax Invoice No
              </label>
              <input
                id="tax_invoice_number"
                type="text"
                placeholder="e.g. GST-9988-1"
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-emerald-500"
              />
            </div>
            <div className="space-y-2 md:col-span-2">
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                PMC Comments / Notes
              </label>
              <textarea
                id="pmc_comments"
                rows={2}
                placeholder="Internal verification notes..."
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-emerald-500 resize-none"
              />
            </div>
            <div className="space-y-2">
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Service Engineer
              </label>
              <input
                id="service_engineer_name"
                type="text"
                placeholder="Name of checking engineer"
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-emerald-500"
              />
            </div>
          </div>
        </div>

        {/* Grid Space */}
        <div className="p-6">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-sm font-bold text-white uppercase tracking-wider">
              Scope of Work Calculation
            </h3>
            <button
              onClick={handleAddRow}
              className="text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 px-3 py-1.5 rounded transition-colors"
            >
              + Add Row
            </button>
          </div>

          <div className="h-[400px]">
            <FinancialGrid
              rowData={lineItems}
              columnDefs={columnDefs}
              onCellValueChanged={handleCellValueChanged}
              getRowId={(params) => params.data.id}
            />
          </div>
        </div>

        {/* Footer Summaries */}
        <div className="p-6 bg-slate-950/50 border-t border-slate-800">
          <div className="max-w-xs ml-auto space-y-3">
            <div className="flex justify-between text-sm">
              <span className="text-slate-400">Gross Subtotal</span>
              <span className="text-white font-mono">
                {formatCurrency(subtotal)}
              </span>
            </div>

            <div className="flex justify-between text-sm text-slate-500">
              <span>CGST ({cgstRate}%)</span>
              <span className="font-mono">{formatCurrency(cgstAmount)}</span>
            </div>

            <div className="flex justify-between text-sm text-slate-500">
              <span>SGST ({sgstRate}%)</span>
              <span className="font-mono">{formatCurrency(sgstAmount)}</span>
            </div>

            <div className="flex justify-between text-sm font-semibold text-white border-t border-slate-800 pt-2">
              <span>Grand Total</span>
              <span className="font-mono">
                {formatCurrency(totalPayable)}
              </span>
            </div>

            <div className="flex justify-between text-sm text-amber-500/80">
              <span>Retention Held ({retentionPercent}%)</span>
              <span className="font-mono">
                -{formatCurrency(retentionAmount)}
              </span>
            </div>

            <div className="flex justify-between text-lg font-bold text-emerald-400 border-t border-emerald-500/20 pt-3">
              <span>Net Payable</span>
              <span className="font-mono">{formatCurrency(actualPayable)}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
