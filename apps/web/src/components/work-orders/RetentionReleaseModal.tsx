"use client";

import React, { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@tac-pmc/ui";
import api from "@/lib/api";
import { Loader2, Coins, Calendar, FileText, FileSpreadsheet } from "lucide-react";
import { toast } from "sonner";
import { formatCurrency } from "@/lib/financial";

interface RetentionReleaseModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  woId: string;
  totalHeld: number;
  currentBalance: number;
}

export default function RetentionReleaseModal({
  isOpen,
  onClose,
  onSuccess,
  woId,
  totalHeld,
  currentBalance,
}: RetentionReleaseModalProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form states
  const [amountReleased, setAmountReleased] = useState("");
  const [releaseDate, setReleaseDate] = useState("");
  const [releaseReference, setReleaseReference] = useState("");
  const [notes, setNotes] = useState("");

  // Initialize dates and reset form when modal opens
  useEffect(() => {
    if (isOpen) {
      setAmountReleased("");
      setReleaseReference("");
      setNotes("");
      setError(null);
      
      // Default release date to today's date in local YYYY-MM-DD
      const today = new Date();
      const year = today.getFullYear();
      const month = String(today.getMonth() + 1).padStart(2, "0");
      const day = String(today.getDate()).padStart(2, "0");
      setReleaseDate(`${year}-${month}-${day}`);
    }
  }, [isOpen]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const amount = parseFloat(amountReleased);
    if (isNaN(amount) || amount <= 0) {
      setError("Release amount must be greater than zero.");
      return;
    }

    if (amount > currentBalance) {
      setError(`Cannot release more than the current remaining balance of ${formatCurrency(currentBalance)}.`);
      return;
    }

    if (!releaseReference.trim()) {
      setError("Release reference (cheque/NEFT reference) is required.");
      return;
    }

    setLoading(true);

    try {
      // API requires ISO date format
      const isoDate = new Date(releaseDate).toISOString();

      await api.post(`/api/v1/work-orders/${woId}/retention/release`, {
        amount_released: amount,
        release_date: isoDate,
        release_reference: releaseReference.trim(),
        notes: notes.trim() || undefined,
      });

      toast.success("Retention released successfully", {
        description: `Successfully released ${formatCurrency(amount)} to vendor.`,
      });
      
      onSuccess();
      onClose();
    } catch (err: any) {
      console.error("Failed to release retention", err);
      const serverMessage = err.response?.data?.error?.message || err.response?.data?.detail;
      setError(serverMessage || "Failed to submit retention release request. Please try again.");
      toast.error("Retention release failed", {
        description: serverMessage || "An error occurred during submission.",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleFullRelease = () => {
    setAmountReleased(currentBalance.toString());
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-md bg-slate-900 border border-slate-800 text-white rounded-3xl p-6 shadow-2xl overflow-hidden relative">
        {/* Decorative background glow */}
        <div className="absolute -right-10 -top-10 w-32 h-32 bg-amber-500 rounded-full blur-[60px] opacity-10 pointer-events-none" />
        
        <DialogHeader className="border-b border-slate-800/80 pb-4">
          <DialogTitle className="text-xl font-bold tracking-widest uppercase font-mono text-orange-500 flex items-center gap-2">
            <Coins size={20} />
            Release Retention
          </DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSave} className="space-y-5 py-4">
          {error && (
            <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-3 rounded-xl text-xs flex items-start gap-2">
              <span className="font-bold">Error:</span>
              <span>{error}</span>
            </div>
          )}

          {/* Retention Stats Overview */}
          <div className="grid grid-cols-2 gap-4 bg-slate-950 p-4 rounded-2xl border border-slate-800/50">
            <div>
              <span className="block text-[9px] uppercase tracking-widest text-slate-500 mb-0.5">
                Total Held
              </span>
              <span className="text-sm font-semibold font-mono text-slate-300">
                {formatCurrency(totalHeld)}
              </span>
            </div>
            <div>
              <span className="block text-[9px] uppercase tracking-widest text-slate-500 mb-0.5">
                Remaining Balance
              </span>
              <span className="text-sm font-black font-mono text-amber-500">
                {formatCurrency(currentBalance)}
              </span>
            </div>
          </div>

          {/* Input: Amount to Release */}
          <div className="space-y-1.5">
            <div className="flex justify-between items-center">
              <label htmlFor="amount-to-release" className="block text-[10px] uppercase tracking-widest text-slate-400 font-bold">
                Amount to Release (₹)
              </label>
              <button
                type="button"
                onClick={handleFullRelease}
                className="text-[9px] font-bold text-orange-500 hover:text-orange-400 transition-colors uppercase tracking-wider"
              >
                Release Full Balance
              </button>
            </div>
            <div className="relative">
              <input
                id="amount-to-release"
                type="number"
                step="0.01"
                min="0.01"
                max={currentBalance}
                value={amountReleased}
                onChange={(e) => setAmountReleased(e.target.value)}
                placeholder="0.00"
                className="w-full bg-slate-950 border border-slate-700 hover:border-slate-600 focus:border-orange-500 text-white font-mono p-3 pl-10 rounded-xl focus:outline-none transition-all"
                required
              />
              <Coins size={14} className="absolute left-3.5 top-4 text-slate-500" />
            </div>
          </div>

          {/* Input: Release Date */}
          <div className="space-y-1.5">
            <label htmlFor="release-date" className="block text-[10px] uppercase tracking-widest text-slate-400 font-bold">
              Release Date
            </label>
            <div className="relative">
              <input
                id="release-date"
                type="date"
                value={releaseDate}
                onChange={(e) => setReleaseDate(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 hover:border-slate-600 focus:border-orange-500 text-white font-mono p-3 pl-10 rounded-xl focus:outline-none transition-all"
                required
              />
              <Calendar size={14} className="absolute left-3.5 top-4 text-slate-500" />
            </div>
          </div>

          {/* Input: Reference */}
          <div className="space-y-1.5">
            <label htmlFor="release-ref" className="block text-[10px] uppercase tracking-widest text-slate-400 font-bold">
              Release Reference (Mandatory)
            </label>
            <div className="relative">
              <input
                id="release-ref"
                type="text"
                value={releaseReference}
                onChange={(e) => setReleaseReference(e.target.value)}
                placeholder="Cheque # / NEFT Ref / Bank Ref"
                className="w-full bg-slate-950 border border-slate-700 hover:border-slate-600 focus:border-orange-500 text-white p-3 pl-10 rounded-xl focus:outline-none transition-all"
                required
              />
              <FileSpreadsheet size={14} className="absolute left-3.5 top-4 text-slate-500" />
            </div>
          </div>

          {/* Input: Notes */}
          <div className="space-y-1.5">
            <label htmlFor="release-notes" className="block text-[10px] uppercase tracking-widest text-slate-400 font-bold">
              Notes / Remarks (Optional)
            </label>
            <div className="relative">
              <textarea
                id="release-notes"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Details of defects liability resolution or closing comments..."
                className="w-full bg-slate-950 border border-slate-700 hover:border-slate-600 focus:border-orange-500 text-white p-3 pl-10 rounded-xl focus:outline-none transition-all min-h-[80px] max-h-[140px]"
              />
              <FileText size={14} className="absolute left-3.5 top-4 text-slate-500" />
            </div>
          </div>

          <DialogFooter className="border-t border-slate-800/80 pt-4 flex gap-3 justify-end mt-6">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2.5 rounded-xl border border-slate-700 text-slate-300 text-xs font-bold hover:bg-slate-800 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2.5 bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-600 hover:to-orange-700 text-white text-xs font-bold rounded-xl shadow-lg border border-amber-400/20 transition-all flex items-center gap-1.5 disabled:opacity-50"
            >
              {loading ? (
                <>
                  <Loader2 size={12} className="animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <Coins size={12} />
                  Confirm Release
                </>
              )}
            </button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
