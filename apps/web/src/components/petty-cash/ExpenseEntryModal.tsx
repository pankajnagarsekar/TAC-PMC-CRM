"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import {
  X,
  Upload,
  Loader2,
  CheckCircle,
  AlertCircle,
  AlertTriangle,
} from "lucide-react";
import api from "@/lib/api";
import Image from "next/image";

interface ExpenseEntryModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  projectId: string;
}

interface Category {
  _id: string;
  category_name: string;
}

interface OcrResult {
  ocr_id: string;
  confidence_score: number;
  extracted_amount: number | null;
  extracted_invoice_number: string | null;
}

export default function ExpenseEntryModal({
  isOpen,
  onClose,
  onSuccess,
  projectId,
}: ExpenseEntryModalProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [categories, setCategories] = useState<Category[]>([]);
  const [isLoadingCategories, setIsLoadingCategories] = useState(false);
  const [formData, setFormData] = useState({
    category_id: "",
    amount: "",
    purpose: "",
    bill_reference: "",
  });
  const [idempotencyKey, setIdempotencyKey] = useState("");

  // OCR state
  const [ocrResult, setOcrResult] = useState<OcrResult | null>(null);
  const [isScanning, setIsScanning] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // 3.3.9: Warning state from API response
  const [saveWarnings, setSaveWarnings] = useState<string[]>([]);

  const fetchCategories = useCallback(async () => {
    setIsLoadingCategories(true);
    try {
      // Using the fund-allocations endpoint which already filters to fund_transfer categories
      const response = await api.get(
        `/api/v1/cash/allocations?project_id=${projectId}`,
      );
      const allocations = response.data.items || [];

      // Extract unique categories and filter by user requirement (Petty Cash/OVH only)
      const uniqueCategories: Category[] = [];
      const seen = new Set();
      for (const alloc of allocations) {
        const name = alloc.category_name || "";
        const isMatch = name.toLowerCase().includes("petty cash") ||
          name.toLowerCase().includes("ovh") ||
          name.toLowerCase().includes("overhead");

        if (isMatch && !seen.has(alloc.category_id)) {
          seen.add(alloc.category_id);
          uniqueCategories.push({
            _id: alloc.category_id,
            category_name: alloc.category_name,
          });
        }
      }
      setCategories(uniqueCategories);
    } catch (error) {
      console.error("Failed to fetch categories:", error);
    } finally {
      setIsLoadingCategories(false);
    }
  }, [projectId]);

  useEffect(() => {
    if (isOpen && projectId) {
      // Generate UUID for idempotency key
      setIdempotencyKey(crypto.randomUUID());

      // Fetch fund transfer categories
      fetchCategories();
    }
  }, [isOpen, projectId, fetchCategories]);

  // Auto-select first category if available
  useEffect(() => {
    if (categories.length > 0 && !formData.category_id) {
      setFormData((prev) => ({
        ...prev,
        category_id: categories[0]._id,
      }));
    }
  }, [categories, formData.category_id]);

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;


    // Create preview URL
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);

    // Auto-trigger OCR scan
    await runOcr(file);
  };

  const runOcr = async (file: File) => {
    setIsScanning(true);
    setOcrResult(null);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await api.post(
        `/api/v1/ai/ocr?project_id=${projectId}`,
        formData,
        {
          headers: {
            "Content-Type": "multipart/form-data",
          },
        },
      );

      const ocrData = response.data;
      setOcrResult({
        ocr_id: ocrData.ocr_id,
        confidence_score: ocrData.confidence_score || 0,
        extracted_amount: ocrData.extracted_amount || null,
        extracted_invoice_number: ocrData.extracted_invoice_number || null,
      });

      // Auto-fill amount if extracted
      if (ocrData.extracted_amount) {
        setFormData((prev) => ({
          ...prev,
          amount: String(ocrData.extracted_amount),
        }));
      }

      // Auto-fill bill reference if extracted
      if (ocrData.extracted_invoice_number) {
        setFormData((prev) => ({
          ...prev,
          bill_reference: ocrData.extracted_invoice_number,
        }));
      }
    } catch (error) {
      console.error("OCR scan failed:", error);
    } finally {
      setIsScanning(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      const response = await api.post(
        `/api/v1/petty-cash/transaction`,
        {
          project_id: projectId,
          category_id: formData.category_id,
          amount: parseFloat(formData.amount),
          type: "DEBIT",
          description: `[${formData.bill_reference}] ${formData.purpose}`,
          // Fix Bug #29: Don't send blob URLs to backend
          image_url: null,
        },
        {
          headers: {
            "Idempotency-Key": idempotencyKey,
          },
        },
      );

      // 3.3.9: Capture warnings from API response
      const warnings = response.data?.warnings || [];
      setSaveWarnings(warnings);

      if (warnings.length > 0) {
        // Show warnings but still allow close - warnings are not blocking
        // User can acknowledge and close
        return;
      }

      onSuccess();
      onClose();
      resetForm();
    } catch (err: unknown) {
      console.error("Failed to create expense:", err);
      const error = err as { response?: { data?: { detail?: string } } };
      alert(error.response?.data?.detail || "Failed to create expense");
    } finally {
      setIsLoading(false);
    }
  };

  const resetForm = () => {
    setFormData({
      category_id: "",
      amount: "",
      purpose: "",
      bill_reference: "",
    });
    setOcrResult(null);
    setSaveWarnings([]);
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
      setPreviewUrl(null);
    }
  };

  const handleClose = () => {
    resetForm();
    onClose();
  };

  const getConfidenceColor = (score: number) => {
    if (score >= 0.8) return "text-emerald-400";
    if (score >= 0.5) return "text-amber-400";
    return "text-red-400";
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={handleClose}
      />

      {/* Modal */}
      <div className="relative bg-white dark:bg-slate-900 border border-zinc-200 dark:border-slate-800 rounded-xl w-full max-w-lg mx-4 shadow-2xl animate-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-zinc-200 dark:border-slate-800">
          <h2 className="text-xl font-semibold text-zinc-900 dark:text-white">Record Expense</h2>
          <button
            onClick={handleClose}
            className="text-zinc-500 dark:text-slate-400 hover:text-orange-500 transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {/* Category Selector */}
          <div>
            <label className="block text-sm font-medium text-zinc-700 dark:text-slate-300 mb-2">
              Category
            </label>
            {isLoadingCategories ? (
              <div className="flex items-center gap-2 text-zinc-500 dark:text-slate-400 font-mono text-[10px] uppercase tracking-widest">
                <Loader2 size={16} className="animate-spin" />
                Loading categories...
              </div>
            ) : (
              <select
                value={formData.category_id}
                onChange={(e) =>
                  setFormData({ ...formData, category_id: e.target.value })
                }
                required
                className="w-full bg-zinc-50 dark:bg-slate-950 border border-zinc-200 dark:border-slate-800 rounded-lg px-4 py-2.5 text-zinc-900 dark:text-white focus:outline-none focus:border-amber-500 transition-colors"
              >
                <option value="">Select category</option>
                {categories.map((cat) => (
                  <option key={cat._id} value={cat._id}>
                    {cat.category_name}
                  </option>
                ))}
              </select>
            )}
          </div>

          {/* Amount */}
          <div>
            <label className="block text-sm font-medium text-zinc-700 dark:text-slate-300 mb-2">
              Amount (₹)
            </label>
            <div className="relative">
              <IndianRupeeIcon className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
              <input
                type="number"
                step="0.01"
                min="0"
                value={formData.amount}
                onChange={(e) =>
                  setFormData({ ...formData, amount: e.target.value })
                }
                required
                placeholder="0.00"
                className="w-full bg-zinc-50 dark:bg-slate-950 border border-zinc-200 dark:border-slate-800 rounded-lg pl-10 pr-4 py-2.5 text-zinc-900 dark:text-white placeholder-zinc-400 dark:placeholder-slate-500 focus:outline-none focus:border-amber-500 transition-colors font-mono"
              />
            </div>
          </div>

          {/* Bill Image Upload with OCR */}
          <div>
            <label className="block text-sm font-medium text-zinc-700 dark:text-slate-300 mb-2">
              Bill Image (Optional)
            </label>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*,.pdf"
              onChange={handleFileSelect}
              className="hidden"
            />

            {isScanning ? (
              <div className="border-2 border-dashed border-amber-500/50 bg-amber-500/5 rounded-lg p-6 text-center">
                <Loader2 className="w-8 h-8 text-amber-500 mx-auto mb-2 animate-spin" />
                <p className="text-sm text-amber-400">Scanning document...</p>
                <p className="text-xs text-zinc-500 dark:text-slate-500 mt-1">
                  Extracting amount and invoice details
                </p>
              </div>
            ) : previewUrl ? (
              <div className="space-y-3">
                <div className="relative border-2 border-zinc-200 dark:border-slate-700 rounded-lg overflow-hidden">
                  <div className="relative w-full h-48 bg-zinc-50 dark:bg-slate-950">
                    <Image
                      src={previewUrl}
                      alt="Bill preview"
                      fill
                      className="object-contain"
                    />
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      setPreviewUrl(null);
                      setOcrResult(null);
                      if (fileInputRef.current) {
                        fileInputRef.current.value = "";
                      }
                    }}
                    className="absolute top-2 right-2 bg-zinc-900/80 dark:bg-slate-900/80 text-white p-1 rounded-full hover:bg-rose-500 transition-colors"
                  >
                    <X size={16} />
                  </button>
                </div>

                {/* OCR Result */}
                {ocrResult && (
                  <div className="bg-zinc-50 dark:bg-slate-800 rounded-lg p-3 flex items-center justify-between border border-zinc-200 dark:border-slate-700/50">
                    <div className="flex items-center gap-2">
                      {ocrResult.confidence_score >= 0.5 ? (
                        <CheckCircle size={16} className="text-emerald-500" />
                      ) : (
                        <AlertCircle size={16} className="text-amber-500" />
                      )}
                      <span className="text-[10px] uppercase font-black tracking-widest text-zinc-500 dark:text-slate-300">
                        OCR Confidence:{" "}
                        <span
                          className={getConfidenceColor(
                            ocrResult.confidence_score,
                          ) + " font-mono"}
                        >
                          {Math.round(ocrResult.confidence_score * 100)}%
                        </span>
                      </span>
                    </div>
                    {ocrResult.extracted_amount && (
                      <span className="text-[11px] font-bold text-zinc-900 dark:text-white font-mono">
                        Amount: ₹{ocrResult.extracted_amount}
                      </span>
                    )}
                  </div>
                )}
              </div>
            ) : (
              <div
                onClick={() => fileInputRef.current?.click()}
                className="border-2 border-dashed border-zinc-200 dark:border-slate-700 rounded-lg p-6 text-center hover:border-amber-500/50 transition-colors cursor-pointer group"
              >
                <Upload className="w-8 h-8 text-zinc-400 dark:text-slate-500 mx-auto mb-2 group-hover:text-amber-500 transition-colors" />
                <p className="text-sm text-zinc-500 dark:text-slate-400 font-semibold">
                  Drop file here or click to upload
                </p>
                <p className="text-[10px] text-zinc-400 dark:text-slate-500 mt-1 uppercase tracking-widest">
                  PNG, JPG, PDF up to 10MB
                </p>
              </div>
            )}
          </div>

          {/* Purpose */}
          <div>
            <label className="block text-sm font-medium text-zinc-700 dark:text-slate-300 mb-2">
              Purpose
            </label>
            <input
              type="text"
              value={formData.purpose}
              onChange={(e) =>
                setFormData({ ...formData, purpose: e.target.value })
              }
              required
              placeholder="What was this expense for?"
              className="w-full bg-zinc-50 dark:bg-slate-950 border border-zinc-200 dark:border-slate-800 rounded-lg px-4 py-2.5 text-zinc-900 dark:text-white placeholder-zinc-400 dark:placeholder-slate-500 focus:outline-none focus:border-amber-500 transition-colors"
            />
          </div>

          {/* Bill Reference */}
          <div>
            <label className="block text-sm font-medium text-zinc-700 dark:text-slate-300 mb-2">
              Bill Reference
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={formData.bill_reference}
                onChange={(e) =>
                  setFormData({ ...formData, bill_reference: e.target.value })
                }
                placeholder="Invoice/Bill number"
                className="flex-1 bg-zinc-50 dark:bg-slate-950 border border-zinc-200 dark:border-slate-800 rounded-lg px-4 py-2.5 text-zinc-900 dark:text-white placeholder-zinc-400 dark:placeholder-slate-500 focus:outline-none focus:border-amber-500 transition-colors font-mono"
              />
            </div>
          </div>

          {/* 3.3.9: Show threshold/negative warnings after expense save */}
          {saveWarnings.length > 0 && (
            <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-4 space-y-2">
              <div className="flex items-center gap-2 text-amber-400">
                <AlertTriangle size={18} />
                <span className="font-medium">Warning</span>
              </div>
              <ul className="text-sm text-amber-200 space-y-1">
                {saveWarnings.includes("negative_cash") && (
                  <li>
                    • This expense brings cash to negative. Site balance is now
                    below ₹0.
                  </li>
                )}
                {saveWarnings.includes("threshold_breach") && (
                  <li>• This expense brings cash below the threshold limit.</li>
                )}
              </ul>
              <p className="text-xs text-amber-300/70 pt-2">
                Expense was saved successfully. Consider creating a Payment
                Certificate to replenish funds.
              </p>
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={handleClose}
              className="flex-1 bg-zinc-100 dark:bg-slate-800 hover:bg-zinc-200 dark:hover:bg-slate-700 text-zinc-600 dark:text-slate-300 font-medium py-2.5 rounded-lg transition-colors border border-zinc-200 dark:border-transparent"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading || isLoadingCategories}
              className="flex-1 bg-amber-500 hover:bg-amber-600 disabled:bg-amber-500/50 disabled:cursor-not-allowed text-white font-bold py-2.5 rounded-lg transition-colors flex items-center justify-center gap-2 shadow-lg shadow-amber-500/20"
            >
              {isLoading ? (
                <>
                  <Loader2 size={18} className="animate-spin" />
                  Saving...
                </>
              ) : (
                "Save Expense"
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// Simple Indian Rupee icon component
function IndianRupeeIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <line x1="12" y1="1" x2="12" y2="23" />
      <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
    </svg>
  );
}
