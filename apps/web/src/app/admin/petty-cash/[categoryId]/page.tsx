"use client";

import { useState, useRef } from "react";
import useSWR from "swr";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  Plus,
  Receipt,
  Loader2,
  IndianRupee,
  AlertTriangle,
  Upload,
  Scan,
  Sparkles,
} from "lucide-react";
import Link from "next/link";
import { v4 as uuidv4 } from "uuid";

import api, { fetcher } from "@/lib/api";
import { useProjectStore } from "@/store/projectStore";
import { CashTransaction, FundAllocation } from "@/types/api";
import {
  formatCurrency,
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@tac-pmc/ui";

export default function CategoryLedgerPage() {
  const params = useParams();
  const router = useRouter();
  const categoryId = params.categoryId as string;
  const { activeProject } = useProjectStore();

  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formData, setFormData] = useState({
    amount: "",
    purpose: "",
    vendor_name: "",
    bill_reference: "",
  });

  const fileInputRef = useRef<HTMLInputElement>(null);
  const [ocrLoading, setOcrLoading] = useState(false);
  const [ocrConfidence, setOcrConfidence] = useState<number | null>(null);
  const [idempotencyKey, setIdempotencyKey] = useState("");

  // Generate key on mount
  useState(() => {
    setIdempotencyKey(uuidv4());
  });

  const handleOCR = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !activeProject) return;

    setOcrLoading(true);
    setOcrConfidence(null);
    const formData = new FormData();
    formData.append("file", file);
    formData.append("project_id", activeProject.project_id);

    try {
      const res = await api.post("/api/v1/ai/ocr", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      const result = res.data;
      setFormData((prev: any) => ({
        ...prev,
        amount: result.extracted_amount?.toString() || prev.amount,
        vendor_name: result.extracted_vendor_name || prev.vendor_name,
        bill_reference: result.extracted_invoice_number || prev.bill_reference,
      }));
      setOcrConfidence(result.confidence_score);
    } catch (err) {
      console.error("OCR failed:", err);
    } finally {
      setOcrLoading(false);
    }
  };

  // Fetch Allocations to find the specific category details
  const { data: allocData } = useSWR<{ items: FundAllocation[] }>(
    activeProject
      ? `/api/projects/${activeProject.project_id}/fund-allocations`
      : null,
    fetcher,
  );

  const currentAllocation = allocData?.items.find(
    (a: FundAllocation) => a.category_id === categoryId,
  );
  const isNegative = (currentAllocation?.allocation_remaining || 0) < 0;

  // Fetch Transaction Ledger
  const {
    data: txData,
    isLoading: txLoading,
    mutate: mutateTx,
  } = useSWR<{ items: CashTransaction[] }>(
    activeProject
      ? `/api/projects/${activeProject.project_id}/cash-transactions?category_id=${categoryId}`
      : null,
    fetcher,
  );

  const transactions = txData?.items || [];

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeProject) return;
    setIsSubmitting(true);
    try {
      await api.post(
        `/api/projects/${activeProject.project_id}/cash-transactions`,
        {
          project_id: activeProject.project_id,
          category_id: categoryId,
          amount: parseFloat(formData.amount),
          type: "DEBIT",
          purpose: formData.purpose,
          vendor_name: formData.vendor_name,
          bill_reference: formData.bill_reference,
        },
        {
          headers: { "Idempotency-Key": idempotencyKey },
        },
      );
      setIsAddModalOpen(false);
      setFormData({
        amount: "",
        purpose: "",
        vendor_name: "",
        bill_reference: "",
      });
      setIdempotencyKey(uuidv4()); // Success, new key for next
      mutateTx();
      // Optionally mutate global site allocations via SWR global mutate if configured
    } catch (error) {
      console.error("Failed to log expense:", error);
      alert(
        "Failed to log expense. Be sure it does not exceed the remaining allocation.",
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!activeProject) return null;

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link
          href="/admin/petty-cash"
          className="p-2 hover:bg-slate-800 rounded-lg text-slate-400 hover:text-white transition-colors"
        >
          <ArrowLeft size={20} />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            {currentAllocation?.category_name || categoryId} Ledger
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Transaction history and cash dispersion for this category.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div
          className={`bg-slate-900 border ${isNegative ? "border-red-900/50 shadow-red-900/5" : "border-slate-800"} rounded-xl p-6 relative overflow-hidden transition-all duration-500`}
        >
          <p className="text-slate-400 text-sm uppercase tracking-widest font-bold mb-2">
            Available Puddle
          </p>
          <p
            className={`text-4xl font-mono font-bold ${isNegative ? "text-red-500" : "text-emerald-400"}`}
          >
            {currentAllocation
              ? formatCurrency(currentAllocation.allocation_remaining)
              : "..."}
          </p>
          {isNegative && (
            <div className="flex items-center gap-1 text-[10px] font-bold uppercase text-red-500 mt-2 tracking-tighter">
              <AlertTriangle size={12} className="animate-pulse" /> Overdrawn -
              Site Overdraft Active
            </div>
          )}
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 flex flex-col justify-center items-start">
          <button
            onClick={() => setIsAddModalOpen(true)}
            className="admin-only w-full h-full min-h-[80px] bg-amber-500 hover:bg-amber-600 text-black rounded-xl border-none text-lg font-bold shadow-lg shadow-amber-500/20 flex items-center justify-center transition-colors"
          >
            <Plus className="mr-2" /> Log Site Expense
          </button>
        </div>
      </div>

      {/* Ledger Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
        <div className="p-4 border-b border-slate-800 flex justify-between items-center bg-slate-950/50">
          <h2 className="text-lg font-medium text-white flex items-center gap-2">
            <Receipt size={18} className="text-slate-400" />
            Transaction History
          </h2>
        </div>

        <div className="overflow-x-auto">
          {txLoading ? (
            <div className="p-8 text-center flex flex-col items-center justify-center text-slate-500">
              <Loader2 className="w-8 h-8 animate-spin mb-4 text-amber-500" />
              <p>Loading ledger...</p>
            </div>
          ) : transactions.length === 0 ? (
            <div className="p-12 text-center text-slate-500">
              <Receipt size={48} className="mx-auto mb-4 opacity-20" />
              <p>No transactions recorded for this category yet.</p>
            </div>
          ) : (
            <table className="w-full text-sm text-left">
              <thead className="text-xs text-slate-400 uppercase bg-slate-900/80 border-b border-slate-800">
                <tr>
                  <th className="px-6 py-4 font-medium">Date</th>
                  <th className="px-6 py-4 font-medium">Type</th>
                  <th className="px-6 py-4 font-medium">Purpose / Reference</th>
                  <th className="px-6 py-4 font-medium">Vendor</th>
                  <th className="px-6 py-4 font-medium text-right">Amount</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/50">
                {transactions.map((tx: CashTransaction) => (
                  <tr
                    key={tx._id}
                    className="hover:bg-slate-800/30 transition-colors"
                  >
                    <td className="px-6 py-4 text-slate-300">
                      {new Date(tx.created_at || "").toLocaleDateString(
                        "en-IN",
                        {
                          day: "2-digit",
                          month: "short",
                          year: "numeric",
                          hour: "2-digit",
                          minute: "2-digit",
                        },
                      )}
                    </td>
                    <td className="px-6 py-4">
                      {tx.type === "CREDIT" ? (
                        <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                          + INJECTION
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-500/10 text-red-400 border border-red-500/20">
                          - EXPENSE
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <p className="text-white font-medium">
                        {tx.purpose || "-"}
                      </p>
                      {tx.bill_reference && (
                        <p className="text-xs text-slate-500 mt-1">
                          Ref: {tx.bill_reference}
                        </p>
                      )}
                    </td>
                    <td className="px-6 py-4 text-slate-300">
                      {tx.vendor_name || "-"}
                    </td>
                    <td
                      className={`px-6 py-4 font-mono font-bold text-right ${tx.type === "CREDIT" ? "text-emerald-400" : "text-white"}`}
                    >
                      {tx.type === "CREDIT" ? "+" : "-"}
                      {formatCurrency(tx.amount)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      <Dialog
        open={isAddModalOpen}
        onOpenChange={() => setIsAddModalOpen(false)}
      >
        <DialogContent className="bg-slate-950 border-slate-900 text-white max-w-lg rounded-2xl p-0 overflow-hidden shadow-2xl">
          <DialogHeader className="p-6 border-b border-slate-900 bg-slate-950/50">
            <div className="flex items-center justify-between">
              <DialogTitle className="text-xl font-bold bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">
                Log Site Expense
              </DialogTitle>
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={ocrLoading}
                className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-orange-500/10 border border-orange-500/20 text-orange-500 text-xs font-bold hover:bg-orange-500/20 transition-all disabled:opacity-50"
              >
                {ocrLoading ? (
                  <Loader2 size={14} className="animate-spin" />
                ) : (
                  <Scan size={14} />
                )}
                {ocrLoading ? "Scanning..." : "AI Scan Receipt"}
              </button>
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleOCR}
                className="hidden"
                accept="image/*,application/pdf"
              />
            </div>
          </DialogHeader>

          <form onSubmit={onSubmit} className="p-6 space-y-4">
            {ocrConfidence !== null && (
              <div className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-500 p-3 rounded-xl flex items-center justify-between animate-in slide-in-from-top-2 duration-300">
                <div className="flex items-center gap-2">
                  <Sparkles size={16} />
                  <span className="text-xs font-bold uppercase tracking-wider">
                    AI Extracted Successfully
                  </span>
                </div>
                <span className="text-[10px] font-mono opacity-80">
                  {Math.round(ocrConfidence * 100)}% Confidence
                </span>
              </div>
            )}
            <div>
              <label className="block text-xs font-semibold text-slate-400 mb-1.5 uppercase tracking-wider px-1">
                Amount (₹) *
              </label>
              <input
                type="number"
                step="0.01"
                required
                placeholder="0.00"
                value={formData.amount}
                onChange={(e) =>
                  setFormData({ ...formData, amount: e.target.value })
                }
                className="w-full bg-slate-900 border border-slate-800 rounded-xl px-4 py-3 text-white text-sm focus:outline-none focus:border-amber-500/50 transition-colors placeholder:text-slate-600"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-400 mb-1.5 uppercase tracking-wider px-1">
                Purpose / Description *
              </label>
              <input
                type="text"
                required
                placeholder="Material purchase, labor..."
                value={formData.purpose}
                onChange={(e) =>
                  setFormData({ ...formData, purpose: e.target.value })
                }
                className="w-full bg-slate-900 border border-slate-800 rounded-xl px-4 py-3 text-white text-sm focus:outline-none focus:border-amber-500/50 transition-colors placeholder:text-slate-600"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1.5 uppercase tracking-wider px-1">
                  Vendor (Optional)
                </label>
                <input
                  type="text"
                  placeholder="Cash recipient"
                  value={formData.vendor_name}
                  onChange={(e) =>
                    setFormData({ ...formData, vendor_name: e.target.value })
                  }
                  className="w-full bg-slate-900 border border-slate-800 rounded-xl px-4 py-3 text-white text-sm focus:outline-none focus:border-amber-500/50 transition-colors placeholder:text-slate-600"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1.5 uppercase tracking-wider px-1">
                  Ref (Optional)
                </label>
                <input
                  type="text"
                  placeholder="Bill #1234"
                  value={formData.bill_reference}
                  onChange={(e) =>
                    setFormData({ ...formData, bill_reference: e.target.value })
                  }
                  className="w-full bg-slate-900 border border-slate-800 rounded-xl px-4 py-3 text-white text-sm focus:outline-none focus:border-amber-500/50 transition-colors placeholder:text-slate-600"
                />
              </div>
            </div>

            <div
              className={`bg-amber-500/10 border border-amber-500/20 text-amber-500 text-sm p-4 rounded-xl mt-4 ${isNegative ? "bg-red-500/10 border-red-500/20 text-red-500" : ""}`}
            >
              <strong>Note:</strong> Logging an expense will linearly deduct
              from the{" "}
              <code
                className={`mx-1 px-1.5 py-0.5 rounded font-mono ${isNegative ? "bg-red-500/20" : "bg-amber-500/20"}`}
              >
                {formatCurrency(currentAllocation?.allocation_remaining || 0)}
              </code>{" "}
              available in this category.
              {isNegative && (
                <p className="mt-1 text-xs opacity-80 font-semibold">
                  Proceeding will further increase the site overdraft.
                </p>
              )}
            </div>

            <DialogFooter className="pt-4 flex gap-3 sm:gap-0 mt-6">
              <button
                type="button"
                className="flex-1 sm:flex-none border border-slate-800 text-slate-400 hover:bg-slate-900 px-4 py-2 rounded-xl text-sm font-medium transition-all"
                onClick={() => setIsAddModalOpen(false)}
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isSubmitting}
                className="admin-only flex-1 sm:flex-none bg-amber-500 hover:bg-amber-600 text-black px-4 py-2 rounded-xl text-sm font-bold shadow-lg shadow-amber-500/20 disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {isSubmitting ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  "Log Expense"
                )}
              </button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
