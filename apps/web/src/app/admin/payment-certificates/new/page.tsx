"use client";

import { useState, useCallback, useMemo, useEffect } from "react";
import { useRouter } from "next/navigation";
import useSWR from "swr";
import { v4 as uuidv4 } from "uuid";
import {
  ArrowLeft,
  Save,
  AlertTriangle,
  Building2,
  FileText,
} from "lucide-react";
import Link from "next/link";
import {
  ColDef,
  ValueSetterParams,
  CellValueChangedEvent,
  ICellRendererParams,
} from "ag-grid-community";

import api, { fetcher } from "@/lib/api";
import { useProjectStore } from "@/store/projectStore";
import FinancialGrid from "@/components/ui/FinancialGrid";
import { formatCurrency } from "@tac-pmc/ui";
import { CodeMaster, WorkOrder } from "@/types/api";

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

  // States
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [idempotencyKey, setIdempotencyKey] = useState<string>("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  const [isWoLinked, setIsWoLinked] = useState(true);
  const [selectedWoId, setSelectedWoId] = useState<string>("");
  const [selectedCategoryId, setSelectedCategoryId] = useState<string>("");

  const [lineItems, setLineItems] = useState<PCLineItem[]>([]);
  const [retentionPercent, setRetentionPercent] = useState<number>(5);

  // SWR Hooks
  const { data: woResponse } = useSWR(
    activeProject
      ? `/api/projects/${activeProject.project_id}/work-orders`
      : null,
    fetcher,
  );
  const workOrders: WorkOrder[] =
    woResponse?.items?.filter((wo: WorkOrder) => wo.status !== "Cancelled") ||
    [];

  const { data: categories } = useSWR<CodeMaster[]>(
    "/api/codes?active_only=true",
    fetcher,
  );
  const fundCategories =
    categories?.filter((c) => c.budget_type === "fund_transfer") || [];

  // Generate idempotency layer on mount
  useEffect(() => {
    setIdempotencyKey(uuidv4());
  }, []);

  // Sync Category when WO selected
  useEffect(() => {
    if (isWoLinked && selectedWoId) {
      const wo = workOrders.find((w) => w._id === selectedWoId);
      if (wo) setSelectedCategoryId(wo.category_id);
    }
  }, [isWoLinked, selectedWoId, workOrders]);

  // Calculations Preview
  const { subtotal, retentionAmount, gst, grandTotal, totalPayable } =
    useMemo(() => {
      const rawSub = lineItems.reduce(
        (sum, item) => sum + (Number(item.total) || 0),
        0,
      );
      const reten = rawSub * (retentionPercent / 100);
      const gstTotal = rawSub * 0.18; // 9% CGST + 9% SGST implied locally
      const grand = rawSub + gstTotal;
      const payable = grand - reten;

      return {
        subtotal: rawSub,
        retentionAmount: reten,
        gst: gstTotal,
        grandTotal: grand,
        totalPayable: payable,
      };
    }, [lineItems, retentionPercent]);

  const handleSave = async () => {
    if (!activeProject) return;
    if (isWoLinked && !selectedWoId) {
      setError("Please map to an active Work Order");
      return;
    }
    if (!isWoLinked && !selectedCategoryId) {
      setError("Fund Requests mandate an active internal category target");
      return;
    }
    if (lineItems.length === 0) {
      setError("Add at least one line item describing the scope of work");
      return;
    }

    try {
      setIsSubmitting(true);
      setError(null);
      setFieldErrors({});

      const payload = {
        work_order_id: isWoLinked ? selectedWoId : null,
        category_id: !isWoLinked ? selectedCategoryId : undefined,
        retention_percent: retentionPercent,
        line_items: lineItems.map((item, index) => ({
          sr_no: index + 1,
          scope_of_work: item.scope_of_work,
          unit: item.unit,
          qty: Number(item.qty),
          rate: Number(item.rate),
        })),
      };

      const res = await api.post(
        `/api/projects/${activeProject.project_id}/payment-certificates`,
        payload,
        {
          headers: { "Idempotency-Key": idempotencyKey },
        },
      );

      router.push(`/admin/payment-certificates/${res.data._id}`);
      router.refresh();
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      if (detail?.errors) {
        const newErrors: Record<string, string> = {};
        detail.errors.forEach((e: any) => {
          newErrors[e.field] = e.message;
        });
        setFieldErrors(newErrors);
        setError("Please correct the highlighted errors.");
      } else {
        setError(
          detail || err.message || "Failed to submit Payment Certificate",
        );
      }
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
      valueGetter: (params) =>
        params.node && params.node.rowIndex !== null
          ? params.node.rowIndex + 1
          : "",
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
            const updated = [...lineItems];
            updated.splice(params.node!.rowIndex!, 1);
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
          disabled={isSubmitting || !activeProject}
          className="admin-only flex items-center gap-2 bg-emerald-500 hover:bg-emerald-600 disabled:opacity-50 disabled:cursor-not-allowed text-white px-6 py-2 rounded-lg font-medium transition-colors shadow-lg shadow-emerald-500/20"
        >
          {isSubmitting ? (
            <div className="w-5 h-5 border-2 border-white/20 border-t-white rounded-full animate-spin" />
          ) : (
            <Save size={18} />
          )}
          Generate Token
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
                setIsWoLinked(true);
                setSelectedCategoryId("");
              }}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${isWoLinked ? "bg-slate-800 text-emerald-400 shadow-sm" : "text-slate-400 hover:text-slate-300"}`}
            >
              <span className="flex items-center gap-2">
                <Building2 size={16} /> WO-Linked Payment
              </span>
            </button>
            <button
              onClick={() => {
                setIsWoLinked(false);
                setSelectedWoId("");
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
              <div className="space-y-2">
                <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Select Work Order Link
                </label>
                <select
                  value={selectedWoId}
                  onChange={(e) => setSelectedWoId(e.target.value)}
                  className={`w-full bg-slate-950 border ${fieldErrors.work_order_id ? "border-red-500" : "border-slate-800"} rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-emerald-500`}
                >
                  <option value="">Select a WO...</option>
                  {workOrders.map((wo: WorkOrder) => (
                    <option key={wo._id} value={wo._id}>
                      {wo.wo_ref} (Cat:{" "}
                      {
                        categories?.find((c) => c._id === wo.category_id)
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
              </div>
            ) : (
              <div className="space-y-2">
                <label className="text-xs font-semibold text-amber-400 uppercase tracking-wider">
                  Fund Request Category (Petty/OVH)
                </label>
                <select
                  value={selectedCategoryId}
                  onChange={(e) => setSelectedCategoryId(e.target.value)}
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
                  value={retentionPercent}
                  onChange={(e) => setRetentionPercent(Number(e.target.value))}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-4 pr-8 py-2.5 text-white focus:outline-none focus:border-emerald-500"
                />
                <span className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-500">
                  %
                </span>
              </div>
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
              <span className="text-slate-400">Subtotal</span>
              <span className="text-white font-mono">
                {formatCurrency(subtotal)}
              </span>
            </div>

            {isWoLinked && (
              <div className="flex justify-between text-sm text-amber-500/80">
                <span>Retention Held ({retentionPercent}%)</span>
                <span className="font-mono">
                  -{formatCurrency(retentionAmount)}
                </span>
              </div>
            )}

            <div className="flex justify-between text-sm text-slate-500 border-t border-slate-800 pt-2 top-padding-2 mt-2">
              <span>Estimated GST (18%)</span>
              <span className="font-mono">{formatCurrency(gst)}</span>
            </div>

            <div className="flex justify-between text-lg font-bold text-emerald-400 border-t border-slate-800 pt-3">
              <span>Total Payable</span>
              <span className="font-mono">{formatCurrency(totalPayable)}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
