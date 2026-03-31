"use client";

import { useState, useMemo, useCallback, useEffect } from "react";
import { useRouter } from "next/navigation";
import useSWR from "swr";
import {
  ArrowLeft,
  Save,
  AlertTriangle,
  Plus,
  Trash2,
  Loader2,
} from "lucide-react";
import api, { fetcher } from "@/lib/api";
import { useRequestLock } from "@/lib/requestLock";
import { idempotency } from "@/lib/idempotency";
import FinancialGrid, { RowValidation } from "@/components/ui/FinancialGrid";
import { useProjectStore } from "@/store/projectStore";
import { Vendor, CodeMaster, WorkOrder } from "@/types/api";
import { formatCurrency } from "@tac-pmc/ui";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@tac-pmc/ui";
import { ColDef } from "ag-grid-community";

interface LineItem {
  sr_no: number;
  description: string;
  qty: number;
  rate: number;
  total: number;
}

export default function NewWorkOrderPage() {
  const router = useRouter();
  const { activeProject } = useProjectStore();

  const [formData, setFormData] = useState({
    category_id: "",
    vendor_id: "",
    description: "",
    terms: "",
    discount: 0,
    cgst: 9, // Example default, ideally from Settings
    sgst: 9,
    retention_percent: 5,
  });

  const [lineItems, setLineItems] = useState<LineItem[]>([
    { sr_no: 1, description: "", qty: 0, rate: 0, total: 0 },
  ]);

  const [isSaving, setIsSaving] = useState(false);
  const [idempotencyKey, setIdempotencyKey] = useState("");
  const [isGridValid, setIsGridValid] = useState(true);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [deleteRowIndex, setDeleteRowIndex] = useState<number | null>(null);
  const [showOverBudgetWarning, setShowOverBudgetWarning] = useState(false);
  const { executeWithLock: executeWorkOrderSaveWithLock } = useRequestLock({
    operationId: "WORK_ORDER_SAVE",
    timeoutMs: 30000,
  });

  // Initialize Idempotency Key
  useEffect(() => {
    setIdempotencyKey(idempotency.get("WO_CREATE"));
  }, []);

  const { data: vendors } = useSWR<Vendor[]>("/api/v1/vendors/", fetcher);
  const { data: categories } = useSWR<CodeMaster[]>(
    "/api/v1/settings/codes?active_only=true",
    fetcher,
  );

  // Calculations
  const subtotal = lineItems.reduce((sum, item) => sum + (item.total || 0), 0);
  const discount = formData.discount;
  const totalBeforeTax = subtotal - discount;
  const cgstAmount = totalBeforeTax * (formData.cgst / 100);
  const sgstAmount = totalBeforeTax * (formData.sgst / 100);
  const grandTotal = totalBeforeTax + cgstAmount + sgstAmount;
  const retentionAmount = grandTotal * (formData.retention_percent / 100);
  const totalPayable = grandTotal - retentionAmount;

  // Grid Definitions
  const columnDefs: ColDef<any>[] = useMemo(
    () => [
      {
        field: "description",
        headerName: "Description",
        flex: 2,
        editable: true,
      },
      {
        field: "qty",
        headerName: "Qty",
        flex: 1,
        type: "numericColumn",
        valueParser: (p: any) => Number(p.newValue) || 0,
      },
      {
        field: "rate",
        headerName: "Rate (₹)",
        flex: 1,
        type: "numericColumn",
        valueParser: (p: any) => Number(p.newValue) || 0,
        valueFormatter: (p: any) => formatCurrency(p.value),
      },
      {
        field: "total",
        headerName: "Total (₹)",
        flex: 1,
        editable: false,
        type: "numericColumn",
        valueFormatter: (p: any) => formatCurrency(p.value),
        cellClass: "bg-slate-800/50 font-bold",
      },
      {
        headerName: "",
        field: "actions",
        width: 60,
        editable: false,
        pinned: "right",
        cellRenderer: (params: any) => (
          <button
            onClick={() => removeLineItem(params.node.rowIndex)}
            className="text-red-500 hover:text-red-400 p-1 flex items-center justify-center w-full h-full"
          >
            <Trash2 size={14} />
          </button>
        ),
      },
    ],
    [],
  );

  const addLineItem = () => {
    setLineItems([
      ...lineItems,
      {
        sr_no: lineItems.length + 1,
        description: "",
        qty: 0,
        rate: 0,
        total: 0,
      },
    ]);
  };

  const removeLineItem = (index: number) => {
    setDeleteRowIndex(index);
  };

  const confirmDeleteRow = () => {
    if (deleteRowIndex === null) return;
    if (lineItems.length === 1) {
      setDeleteRowIndex(null);
      return;
    }
    const newItems = [...lineItems];
    newItems.splice(deleteRowIndex, 1);
    setLineItems(newItems.map((item, i) => ({ ...item, sr_no: i + 1 })));
    setDeleteRowIndex(null);
  };

  const onCellValueChanged = (event: any) => {
    if (event.colDef.field === "qty" || event.colDef.field === "rate") {
      const data = event.data;
      data.total = (data.qty || 0) * (data.rate || 0);
      event.api.applyTransaction({ update: [data] });

      // Update React state to trigger subtotal recalculation
      const updatedItems: LineItem[] = [];
      event.api.forEachNode((node: any) => updatedItems.push(node.data));
      setLineItems(updatedItems);
    }
  };

  const validateRow = useCallback((data: LineItem): RowValidation => {
    const errors = [];
    if (!data.description) errors.push("Description is required");
    if (data.qty <= 0) errors.push("Quantity must be > 0");
    if (data.rate < 0) errors.push("Rate must be >= 0");
    if (data.total <= 0 && data.qty > 0 && data.rate > 0)
      errors.push("Total must be > 0");

    return {
      rowIndex: data.sr_no - 1,
      valid: errors.length === 0,
      errors,
    };
  }, []);

  const handleSave = async () => {
    if (!activeProject) return alert("No active project selected.");
    if (!formData.category_id) return alert("Please select a Category.");
    if (!formData.vendor_id) return alert("Please select a Vendor.");
    if (!isGridValid) return alert("Please fix grid validation errors.");

    setIsSaving(true);
    setFieldErrors({});

    try {
      const payload = {
        ...formData,
        project_id: activeProject.project_id || activeProject._id,
        line_items: lineItems,
      };

      const response = await executeWorkOrderSaveWithLock(async () => {
        return await api.post<WorkOrder>(
          `/api/v1/work-orders/${activeProject._id || activeProject.project_id}`,
          payload,
          {
            headers: { "Idempotency-Key": idempotencyKey },
          },
        );
      });

      const responseData = response?.data as any;

      if (responseData?._warning === "over_budget") {
        setShowOverBudgetWarning(true);
        return;
      }

      if (responseData?._id) {
        router.push(`/admin/work-orders/${responseData._id}`);
      } else {
        alert("Work Order created but missing ID. Redirecting...");
        router.push("/admin/work-orders");
      }
    } catch (error: any) {
      const detail = error.response?.data?.detail;
      if (detail?.errors) {
        const newErrors: Record<string, string> = {};
        detail.errors.forEach((e: any) => {
          newErrors[e.field] = e.message;
        });
        setFieldErrors(newErrors);
        alert("Please correct the highlighted errors.");
      } else {
        alert(detail || "Failed to save Work Order");
      }
      // Regenerate key on failure so user can try again safely
      setIdempotencyKey(idempotency.get("WO_CREATE"));
    } finally {
      setIsSaving(false);
    }
  };

  if (!activeProject) {
    return (
      <div className="flex flex-col items-center justify-center h-64">
        <AlertTriangle className="w-12 h-12 text-amber-500 mb-4" />
        <h2 className="text-xl font-bold text-white">No Project Selected</h2>
        <p className="text-slate-400">
          Please select a project from the top navigation to create a Work
          Order.
        </p>
        <button
          onClick={() => router.back()}
          className="mt-4 text-orange-500 hover:text-orange-400"
        >
          Go Back
        </button>
      </div>
    );
  }

  // Filter categories to only Commitment ones
  const commitmentCategories =
    categories?.filter((c) => c.budget_type !== "fund_transfer") || [];

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-24 animate-in fade-in duration-500">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={() => router.back()}
            className="text-slate-400 hover:text-white transition-colors"
          >
            <ArrowLeft size={20} />
          </button>
          <div>
            <h1 className="text-2xl font-bold text-white">Create Work Order</h1>
            <p className="text-slate-400 text-sm">
              Project: {activeProject.project_name}
            </p>
          </div>
        </div>
        <button
          onClick={handleSave}
          disabled={
            isSaving ||
            !isGridValid ||
            !formData.category_id ||
            !formData.vendor_id
          }
          className="admin-only bg-orange-500 hover:bg-orange-600 disabled:opacity-50 text-white px-6 py-2.5 rounded-xl font-bold flex items-center gap-2 transition-all shadow-lg shadow-orange-500/20"
        >
          {isSaving ? (
            <Loader2 size={18} className="animate-spin" />
          ) : (
            <Save size={18} />
          )}
          {isSaving ? "Saving..." : "Save & Lock Commitment"}
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Core Details */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-4 shadow-xl">
          <h2 className="text-sm font-bold text-slate-400 uppercase tracking-widest border-b border-slate-800 pb-2">
            Master Information
          </h2>

          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1 uppercase tracking-wider">
              Category (Commitment)
            </label>
            <select
              value={formData.category_id}
              onChange={(e) =>
                setFormData({ ...formData, category_id: e.target.value })
              }
              className={`w-full bg-slate-950 border ${fieldErrors.category_id ? "border-red-500" : "border-slate-800"} rounded-lg px-3 py-2 text-white focus:outline-none focus:border-orange-500`}
            >
              <option value="">Select a category...</option>
              {commitmentCategories.map((c) => (
                <option key={c._id} value={c._id}>
                  {c.category_name} ({c.code})
                </option>
              ))}
            </select>
            {fieldErrors.category_id && (
              <p className="text-[10px] text-red-500 mt-1 uppercase font-bold">
                {fieldErrors.category_id}
              </p>
            )}
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1 uppercase tracking-wider">
              Vendor
            </label>
            <select
              value={formData.vendor_id}
              onChange={(e) =>
                setFormData({ ...formData, vendor_id: e.target.value })
              }
              className={`w-full bg-slate-950 border ${fieldErrors.vendor_id ? "border-red-500" : "border-slate-800"} rounded-lg px-3 py-2 text-white focus:outline-none focus:border-orange-500`}
            >
              <option value="">Select a vendor...</option>
              {vendors?.map((v) => (
                <option key={v._id} value={v._id}>
                  {v.name} ({v.gstin || "No GSTIN"})
                </option>
              ))}
            </select>
            {fieldErrors.vendor_id && (
              <p className="text-[10px] text-red-500 mt-1 uppercase font-bold">
                {fieldErrors.vendor_id}
              </p>
            )}
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1 uppercase tracking-wider">
              Description of Work
            </label>
            <textarea
              value={formData.description}
              onChange={(e) =>
                setFormData({ ...formData, description: e.target.value })
              }
              rows={3}
              placeholder="e.g., Supply of Ready Mix Concrete for Foundation..."
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white placeholder-slate-600 focus:outline-none focus:border-orange-500 resize-none"
            />
          </div>
        </div>

        {/* Financial Preview */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-4 shadow-xl">
          <h2 className="text-sm font-bold text-slate-400 uppercase tracking-widest border-b border-slate-800 pb-2">
            Financial Preview
          </h2>

          <div className="space-y-2 text-sm">
            <div className="flex justify-between text-slate-400">
              <span>Subtotal:</span>
              <span className="font-mono text-white">
                {formatCurrency(subtotal)}
              </span>
            </div>

            <div className="flex justify-between items-center text-slate-400">
              <span>Discount:</span>
              <div className="flex items-center gap-2">
                <span className="text-slate-500">₹</span>
                <input
                  type="number"
                  value={formData.discount || ""}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      discount: parseFloat(e.target.value) || 0,
                    })
                  }
                  className="w-24 bg-slate-950 border border-slate-800 rounded px-2 py-1 text-right text-white"
                />
              </div>
            </div>

            <div className="flex justify-between text-slate-400 pt-2 border-t border-slate-800/50">
              <span>Total Before Tax:</span>
              <span className="font-mono text-white">
                {formatCurrency(totalBeforeTax)}
              </span>
            </div>

            <div className="flex justify-between text-slate-400">
              <span>CGST ({formData.cgst}%):</span>
              <span className="font-mono text-white">
                {formatCurrency(cgstAmount)}
              </span>
            </div>

            <div className="flex justify-between text-slate-400">
              <span>SGST ({formData.sgst}%):</span>
              <span className="font-mono text-white">
                {formatCurrency(sgstAmount)}
              </span>
            </div>

            <div className="flex justify-between items-center text-orange-500 font-bold pt-2 border-t border-slate-800/50 text-lg">
              <span>Grand Total:</span>
              <span className="font-mono">{formatCurrency(grandTotal)}</span>
            </div>

            <div className="flex justify-between items-center text-slate-400 pt-4">
              <span>Retention (%):</span>
              <input
                type="number"
                value={formData.retention_percent}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    retention_percent: parseFloat(e.target.value) || 0,
                  })
                }
                className="w-16 bg-slate-950 border border-slate-800 rounded px-2 py-1 text-right text-white"
              />
            </div>

            <div className="flex justify-between text-slate-500 text-xs">
              <span>Retention Amount:</span>
              <span className="font-mono">
                -{formatCurrency(retentionAmount)}
              </span>
            </div>

            <div className="flex justify-between items-center text-emerald-500 font-bold pt-2 border-t border-slate-800/50">
              <span>Net Payable (After Retention):</span>
              <span className="font-mono text-lg">
                {formatCurrency(totalPayable)}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Grid */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl relative">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-sm font-bold text-slate-400 uppercase tracking-widest flex items-center gap-2">
            Bill of Quantities
            {!isGridValid && (
              <AlertTriangle size={14} className="text-red-500" />
            )}
          </h2>
          <button
            onClick={addLineItem}
            className="flex items-center gap-1.5 text-xs text-orange-500 hover:text-orange-400 font-bold bg-orange-500/10 px-3 py-1.5 rounded-lg transition-colors border border-orange-500/20"
          >
            <Plus size={14} /> Add Row
          </button>
        </div>

        <FinancialGrid
          rowData={lineItems}
          columnDefs={columnDefs}
          onCellValueChanged={onCellValueChanged}
          validateRow={validateRow}
          onValidationChange={(valid) => setIsGridValid(valid)}
          height="300px"
        />
      </div>

      {/* Delete Row Confirmation Dialog */}
      <Dialog
        open={deleteRowIndex !== null}
        onOpenChange={() => setDeleteRowIndex(null)}
      >
        <DialogContent className="bg-slate-950 border-slate-900 text-white max-w-md rounded-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-3 text-xl font-bold">
              <AlertTriangle className="text-amber-500" size={24} />
              Delete Row
            </DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <p className="text-slate-300">
              Are you sure you want to delete this line item? This action cannot
              be undone.
            </p>
          </div>
          <DialogFooter className="flex gap-3">
            <button
              onClick={() => setDeleteRowIndex(null)}
              className="flex-1 px-4 py-2 border border-slate-700 text-slate-300 rounded-xl hover:bg-slate-900 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={confirmDeleteRow}
              className="flex-1 px-4 py-2 bg-red-600 hover:bg-red-500 text-white rounded-xl font-medium transition-colors"
            >
              Delete Row
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Over Budget Warning Dialog */}
      <Dialog
        open={showOverBudgetWarning}
        onOpenChange={setShowOverBudgetWarning}
      >
        <DialogContent className="bg-slate-950 border-slate-900 text-white max-w-md rounded-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-3 text-xl font-bold">
              <AlertTriangle className="text-amber-500" size={24} />
              Budget Warning
            </DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <p className="text-slate-300">
              This Work Order exceeds the allocated category budget. Do you want
              to proceed anyway?
            </p>
            <div className="mt-4 p-3 bg-amber-500/10 border border-amber-500/20 rounded-xl">
              <p className="text-amber-500 text-sm">
                The WO will be saved but flagged for management review.
              </p>
            </div>
          </div>
          <DialogFooter className="flex gap-3">
            <button
              onClick={() => setShowOverBudgetWarning(false)}
              className="flex-1 px-4 py-2 border border-slate-700 text-slate-300 rounded-xl hover:bg-slate-900 transition-colors"
            >
              Review Details
            </button>
            <button
              onClick={() => {
                setShowOverBudgetWarning(false);
                router.push(`/admin/work-orders`);
              }}
              className="flex-1 px-4 py-2 bg-amber-600 hover:bg-amber-500 text-white rounded-xl font-medium transition-colors"
            >
              Save Anyway
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
