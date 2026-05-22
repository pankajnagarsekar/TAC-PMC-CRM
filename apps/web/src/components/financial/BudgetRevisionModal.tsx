"use client";

import React, { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@tac-pmc/ui";
import { budgetRevisionApi } from "@/lib/api";
import {
  Loader2,
  FileText,
  UploadCloud,
  Trash2,
  AlertCircle,
  TrendingUp,
} from "lucide-react";
import { toast } from "sonner";
import { formatCurrency } from "@/lib/financial";

interface BudgetRevisionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  projectId: string;
  category: {
    category_id: string;
    category_name: string;
    category_code: string;
    original_budget: number;
  } | null;
}

export default function BudgetRevisionModal({
  isOpen,
  onClose,
  onSuccess,
  projectId,
  category,
}: BudgetRevisionModalProps) {
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form states
  const [revisedBudget, setRevisedBudget] = useState("");
  const [reason, setReason] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);

  // Reset form when modal opens/closes or category changes
  useEffect(() => {
    if (isOpen) {
      setRevisedBudget("");
      setReason("");
      setFile(null);
      setError(null);
    }
  }, [isOpen, category]);

  if (!category) return null;

  const currentBudget = category.original_budget;

  // Handlers for Drag & Drop
  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0];
      validateAndSetFile(droppedFile);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      validateAndSetFile(e.target.files[0]);
    }
  };

  const validateAndSetFile = (selectedFile: File) => {
    const allowedExtensions = ["pdf", "png", "jpg", "jpeg"];
    const fileExt = selectedFile.name.split(".").pop()?.toLowerCase();

    if (!fileExt || !allowedExtensions.includes(fileExt)) {
      toast.error("Invalid file type", {
        description: "Only PDF or image documents (PNG, JPG, JPEG) are allowed.",
      });
      return;
    }

    // Limit to 10MB
    if (selectedFile.size > 10 * 1024 * 1024) {
      toast.error("File too large", {
        description: "Supporting document must be smaller than 10MB.",
      });
      return;
    }

    setFile(selectedFile);
    setError(null);
  };

  const removeFile = () => {
    setFile(null);
  };

  const getVariance = () => {
    const revised = parseFloat(revisedBudget);
    if (isNaN(revised)) return 0;
    return revised - currentBudget;
  };

  const handleSubmit = async (submitForApproval: boolean) => {
    if (!revisedBudget || isNaN(parseFloat(revisedBudget)) || parseFloat(revisedBudget) < 0) {
      setError("Please enter a valid revised budget.");
      return;
    }

    if (reason.trim().length < 10) {
      setError("Reason for revision must be at least 10 characters long.");
      return;
    }

    // Mandatory document check for all Variation Order actions (draft or submit)
    if (!file) {
      setError("A supporting document upload is mandatory for raising a Variation Order.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Step 1: Create the budget revision in DRAFT state
      const draft = await budgetRevisionApi.create({
        project_id: projectId,
        category_id: category.category_id,
        new_budget: parseFloat(revisedBudget),
        reason: reason.trim(),
      });

      const draftId = draft.id || draft._id;
      if (!draftId) {
        throw new Error("Failed to retrieve budget revision ID from server.");
      }

      // Step 2: Upload attachment if file exists
      if (file) {
        setUploading(true);
        await budgetRevisionApi.uploadAttachment(draftId, file);
        setUploading(false);
      }

      // Step 3: Submit for approval if requested
      if (submitForApproval) {
        await budgetRevisionApi.submit(draftId);
        toast.success("Variation Order Submitted", {
          description: `Variation Order for category ${category.category_code} submitted successfully for review.`,
        });
      } else {
        toast.success("Draft Saved", {
          description: `Budget revision draft for category ${category.category_code} saved.`,
        });
      }

      onSuccess();
      onClose();
    } catch (err: any) {
      setUploading(false);
      const serverMsg = err.response?.data?.message || err.response?.data?.detail;
      setError(serverMsg || "An error occurred while creating the budget revision.");
      toast.error("Action Failed", {
        description: serverMsg || "Failed to process the budget revision.",
      });
    } finally {
      setLoading(false);
    }
  };

  const inputStyle =
    "w-full bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl px-4 py-2.5 text-zinc-900 dark:text-white text-sm focus:outline-none focus:border-orange-500/50 transition-colors placeholder:text-zinc-400 dark:placeholder:text-zinc-600";
  const labelStyle =
    "block text-xs font-semibold text-zinc-500 dark:text-zinc-400 mb-1.5 uppercase tracking-wider";

  const variance = getVariance();

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-900 text-zinc-900 dark:text-white max-w-lg rounded-2xl p-0 overflow-hidden shadow-2xl">
        <DialogHeader className="p-6 border-b border-zinc-100 dark:border-zinc-900">
          <DialogTitle className="text-xl font-bold text-zinc-900 dark:text-white flex items-center gap-2">
            <TrendingUp className="text-orange-500" size={22} />
            Raise Variation Order
          </DialogTitle>
          <p className="text-zinc-500 dark:text-zinc-400 text-sm mt-1">
            Propose a formal budget revision for Category{" "}
            <span className="font-semibold font-mono text-zinc-800 dark:text-zinc-200">
              {category.category_code} ({category.category_name})
            </span>
            .
          </p>
        </DialogHeader>

        <div className="p-6 space-y-5 max-h-[70vh] overflow-y-auto">
          {error && (
            <div className="p-3.5 bg-red-500/10 border border-red-500/20 rounded-xl text-red-600 dark:text-red-400 text-xs flex items-start gap-2 animate-in fade-in duration-200">
              <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Read-only financial comparison */}
          <div className="grid grid-cols-2 gap-4 p-4 bg-zinc-50 dark:bg-zinc-900/50 border border-zinc-100 dark:border-zinc-900 rounded-xl">
            <div>
              <span className="text-[10px] font-semibold text-zinc-400 dark:text-zinc-500 uppercase tracking-wider block">
                Current Approved Budget
              </span>
              <span className="text-lg font-bold text-zinc-700 dark:text-zinc-300 font-mono">
                ₹{formatCurrency(currentBudget)}
              </span>
            </div>
            <div>
              <span className="text-[10px] font-semibold text-zinc-400 dark:text-zinc-500 uppercase tracking-wider block">
                Proposed Variance
              </span>
              <span
                className={`text-lg font-bold font-mono ${
                  variance > 0
                    ? "text-red-600 dark:text-red-400"
                    : variance < 0
                    ? "text-emerald-600 dark:text-emerald-400"
                    : "text-zinc-500"
                }`}
              >
                {variance > 0 ? "+" : ""}
                ₹{formatCurrency(variance)}
              </span>
            </div>
          </div>

          {/* New Budget Input */}
          <div>
            <label className={labelStyle}>
              Revised Budget Requested (INR) <span className="text-orange-500">*</span>
            </label>
            <div className="relative">
              <span className="absolute left-4 top-2.5 text-zinc-400 dark:text-zinc-500 text-sm font-semibold select-none">
                ₹
              </span>
              <input
                type="number"
                step="0.01"
                required
                className={`${inputStyle} pl-8 font-mono`}
                placeholder="e.g. 5500000.00"
                value={revisedBudget}
                onChange={(e) => {
                  setError(null);
                  setRevisedBudget(e.target.value);
                }}
              />
            </div>
          </div>

          {/* Reason / Reference */}
          <div>
            <label className={labelStyle}>
              Reason / VO Reference <span className="text-orange-500">*</span>
            </label>
            <textarea
              required
              className={`${inputStyle} min-h-[90px] resize-none`}
              placeholder="Provide a detailed reason and references for the budget revision (minimum 10 characters)..."
              value={reason}
              onChange={(e) => {
                setError(null);
                setReason(e.target.value);
              }}
            />
            <p className="text-[10px] text-zinc-400 dark:text-zinc-500 mt-1 px-1">
              Characters: {reason.trim().length} / 10 min
            </p>
          </div>

          {/* Mandatory Supporting Document Dropzone */}
          <div>
            <label className={labelStyle}>
              Supporting Document <span className="text-orange-500">*</span>
            </label>

            {!file ? (
              <div
                className={`border-2 border-dashed rounded-2xl p-6 text-center transition-all duration-200 select-none ${
                  dragActive
                    ? "border-orange-500 bg-orange-500/5 dark:bg-orange-500/10"
                    : "border-zinc-200 dark:border-zinc-800 hover:border-zinc-300 dark:hover:border-zinc-700 bg-zinc-50/50 dark:bg-zinc-900/10"
                }`}
                onDragEnter={handleDrag}
                onDragOver={handleDrag}
                onDragLeave={handleDrag}
                onDrop={handleDrop}
              >
                <input
                  type="file"
                  id="vo-file-upload"
                  className="hidden"
                  accept=".pdf,.png,.jpg,.jpeg"
                  onChange={handleFileChange}
                />
                <label
                  htmlFor="vo-file-upload"
                  className="flex flex-col items-center justify-center cursor-pointer"
                >
                  <UploadCloud className="w-10 h-10 text-zinc-400 dark:text-zinc-600 mb-3" />
                  <span className="text-sm font-semibold text-zinc-700 dark:text-zinc-300 block mb-1">
                    Drag and drop your file here, or{" "}
                    <span className="text-orange-500 hover:underline">browse</span>
                  </span>
                  <span className="text-xs text-zinc-400 dark:text-zinc-500">
                    Only PDF or images (PNG, JPG, JPEG) up to 10MB allowed.
                  </span>
                </label>
              </div>
            ) : (
              <div className="flex items-center justify-between p-4 bg-zinc-50 dark:bg-zinc-900/30 border border-zinc-100 dark:border-zinc-800 rounded-xl animate-in zoom-in-95 duration-200">
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-10 h-10 bg-orange-500/10 dark:bg-orange-500/20 text-orange-600 dark:text-orange-400 rounded-xl flex items-center justify-center shrink-0">
                    <FileText size={20} />
                  </div>
                  <div className="min-w-0">
                    <span className="text-sm font-semibold text-zinc-700 dark:text-zinc-300 block truncate">
                      {file.name}
                    </span>
                    <span className="text-xs text-zinc-400 dark:text-zinc-500">
                      {(file.size / 1024 / 1024).toFixed(2)} MB
                    </span>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={removeFile}
                  className="w-8 h-8 rounded-lg text-zinc-400 hover:text-red-500 hover:bg-zinc-100 dark:hover:bg-zinc-900 flex items-center justify-center transition-all shrink-0"
                  title="Remove document"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            )}
          </div>
        </div>

        <DialogFooter className="p-6 border-t border-zinc-100 dark:border-zinc-900 bg-zinc-50/50 dark:bg-zinc-950/50 flex gap-3 sm:gap-0">
          <button
            type="button"
            onClick={onClose}
            className="flex-1 border border-zinc-200 dark:border-zinc-800 text-zinc-500 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-900 px-4 py-2.5 rounded-xl text-sm font-semibold transition-colors"
          >
            Cancel
          </button>
          
          <button
            type="button"
            onClick={() => handleSubmit(false)}
            disabled={loading || uploading || !revisedBudget || reason.trim().length < 10 || !file}
            className="flex-1 border border-orange-500/20 hover:border-orange-500/40 text-orange-600 dark:text-orange-400 hover:bg-orange-500/5 px-4 py-2.5 rounded-xl text-sm font-semibold transition-colors disabled:opacity-40 flex items-center justify-center gap-2"
          >
            {loading && !uploading && <Loader2 className="w-4 h-4 animate-spin" />}
            Save Draft
          </button>

          <button
            type="button"
            onClick={() => handleSubmit(true)}
            disabled={loading || uploading || !revisedBudget || reason.trim().length < 10 || !file}
            className="flex-1 bg-orange-600 hover:bg-orange-500 text-white px-4 py-2.5 rounded-xl text-sm font-bold transition-all shadow-md shadow-orange-600/10 disabled:opacity-40 flex items-center justify-center gap-2"
          >
            {loading && <Loader2 className="w-4 h-4 animate-spin" />}
            {uploading ? "Uploading..." : "Submit Proposal"}
          </button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
