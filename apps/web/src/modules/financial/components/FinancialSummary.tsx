import React from 'react';
import { formatCurrency } from '@/lib/financial';
import { AlertCircle, TrendingUp } from 'lucide-react';

interface FinancialSummaryProps {
  subtotal: number;
  cgst: number;
  sgst: number;
  cgstRate: number;
  sgstRate: number;
  grandTotal: number;
  retentionAmount: number;
  retentionPercent: number;
  actualPayable: number;
  netPayable?: number;
  discount?: number;
  totalBeforeTax?: number;
  // Overrun warning props
  availableBudget?: number;
  committedTotal?: number;
  previouslyCertified?: number;
}

export const FinancialSummary: React.FC<FinancialSummaryProps> = ({
  subtotal,
  cgst,
  sgst,
  cgstRate,
  sgstRate,
  grandTotal,
  retentionAmount,
  retentionPercent,
  actualPayable,
  netPayable,
  discount,
  totalBeforeTax,
  availableBudget,
  committedTotal,
  previouslyCertified,
}) => {
  const displayPayable = netPayable ?? actualPayable;
  const isOverBudget = availableBudget !== undefined && grandTotal + (previouslyCertified || 0) > availableBudget;
  const isOverCommitted = committedTotal !== undefined && grandTotal + (previouslyCertified || 0) > committedTotal;

  return (
    <div className="space-y-4">
      {/* BUG-008, BUG-014: Overrun Warnings */}
      {(isOverBudget || isOverCommitted) && (
        <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 animate-pulse">
          <div className="flex items-start gap-3">
            <AlertCircle className="text-amber-400 shrink-0 mt-0.5" size={16} />
            <div>
              <p className="text-xs font-bold text-amber-400 uppercase tracking-wider">
                Financial Advisory Alert
              </p>
              <p className="text-[11px] text-amber-200/70 leading-relaxed">
                {isOverBudget && `This certificate will exceed the Category Budget of ₹${formatCurrency(availableBudget || 0)}.`}
                {isOverBudget && isOverCommitted && " "}
                {isOverCommitted && `Total certified will exceed the Work Order commitment of ₹${formatCurrency(committedTotal || 0)}.`}
              </p>
            </div>
          </div>
        </div>
      )}

      <div className="max-w-xs ml-auto space-y-3 p-4 bg-slate-900/40 rounded-xl border border-slate-800/50 shadow-2xl backdrop-blur-sm">
        <div className="flex justify-between text-sm">
          <span className="text-slate-400">Gross Subtotal</span>
          <span className="text-white font-mono">{formatCurrency(subtotal)}</span>
        </div>

        {discount !== undefined && discount > 0 && (
          <div className="flex justify-between text-sm text-rose-400/80">
            <span>Discount Applied</span>
            <span className="font-mono">-{formatCurrency(discount)}</span>
          </div>
        )}

        {totalBeforeTax !== undefined && (
          <div className="flex justify-between text-sm text-slate-300 border-t border-slate-800/50 pt-2">
            <span>Taxable Amount</span>
            <span className="font-mono">{formatCurrency(totalBeforeTax)}</span>
          </div>
        )}

        {/* BUG-007: Split CGST/SGST Labels */}
        <div className="flex justify-between text-[11px] text-slate-500 uppercase tracking-tighter">
          <span>CGST ({cgstRate}%)</span>
          <span className="font-mono">{formatCurrency(cgst)}</span>
        </div>

        <div className="flex justify-between text-[11px] text-slate-500 uppercase tracking-tighter">
          <span>SGST ({sgstRate}%)</span>
          <span className="font-mono">{formatCurrency(sgst)}</span>
        </div>

        <div className="flex justify-between text-sm font-semibold text-white border-t border-slate-800/80 pt-2">
          <span>Grand Total</span>
          <span className="font-mono">{formatCurrency(grandTotal)}</span>
        </div>

        <div className="flex justify-between text-sm text-amber-500/80 italic">
          <span>Retention Held ({retentionPercent}%)</span>
          <span className="font-mono">-{formatCurrency(retentionAmount)}</span>
        </div>

        <div className="flex justify-between items-end border-t border-emerald-500/30 pt-3">
          <div className="flex flex-col">
            <span className="text-[10px] text-emerald-500/50 uppercase font-bold tracking-widest">Payable Net</span>
            <span className="text-xl font-bold text-emerald-400 drop-shadow-[0_0_8px_rgba(52,211,153,0.3)]">
              {formatCurrency(displayPayable)}
            </span>
          </div>
          <TrendingUp className="text-emerald-500/20 mb-1" size={24} />
        </div>
      </div>
    </div>
  );
};
