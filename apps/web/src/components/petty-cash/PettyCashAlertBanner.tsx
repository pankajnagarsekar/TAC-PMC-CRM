"use client";

import React from "react";
import useSWR from "swr";
import Link from "next/link";
import { AlertTriangle, ArrowRight } from "lucide-react";
import { fetcher } from "@/lib/api";

interface PettyCashAlertBannerProps {
  projectId: string;
  projectName: string;
}

export default function PettyCashAlertBanner({
  projectId,
  projectName,
}: PettyCashAlertBannerProps) {
  const { data, error, isLoading } = useSWR<any>(
    projectId ? `/api/v1/cash/summary/${projectId}` : null,
    fetcher,
    {
      refreshInterval: 10000, // refresh every 10 seconds to detect updates instantly
    }
  );

  if (isLoading || error || !data || !data.categories) {
    return null;
  }

  // Scan categories for any category containing "petty" in its name that is breached
  const breachedCategory = data.categories.find(
    (cat: any) =>
      cat.category_name?.toLowerCase().includes("petty") &&
      cat.threshold_breached
  );

  if (!breachedCategory) {
    return null;
  }

  const formatINR = (value: number) => {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 2,
    }).format(value);
  };

  const cashInHand = breachedCategory.cash_in_hand;
  const threshold = breachedCategory.threshold;

  return (
    <div className="relative overflow-hidden rounded-[2rem] border border-amber-500/30 dark:border-amber-400/20 bg-gradient-to-r from-amber-500/10 via-amber-500/5 to-transparent backdrop-blur-md p-4 sm:p-5 shadow-[0_8px_32px_0_rgba(245,158,11,0.08)] animate-in fade-in slide-in-from-top-4 duration-500 shrink-0">
      {/* Glow Effects */}
      <div className="absolute -left-16 -top-16 w-32 h-32 bg-amber-500/20 rounded-full blur-[40px] pointer-events-none" />
      <div className="absolute right-12 -bottom-16 w-24 h-24 bg-amber-600/10 rounded-full blur-[30px] pointer-events-none" />

      <div className="relative flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-start gap-4">
          <div className="relative flex-shrink-0 mt-0.5 sm:mt-0">
            {/* Pulsing indicator */}
            <span className="absolute -top-1 -right-1 flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-amber-500"></span>
            </span>
            <div className="w-10 h-10 rounded-2xl bg-amber-500/20 flex items-center justify-center text-amber-600 dark:text-amber-400 border border-amber-500/30">
              <AlertTriangle size={20} className="animate-pulse" />
            </div>
          </div>

          <div className="space-y-1">
            <h4 className="text-xs font-black text-amber-700 dark:text-amber-400 uppercase tracking-widest leading-none flex items-center gap-1.5">
              <span>Security Threshold Breach</span>
            </h4>
            <p className="text-sm font-bold text-slate-800 dark:text-amber-100/90 tracking-tight leading-relaxed">
              Petty Cash Alert — <span className="font-extrabold text-slate-900 dark:text-white">{projectName}</span>: Cash in hand (<span className="text-amber-600 dark:text-amber-400 font-extrabold">{formatINR(cashInHand)}</span>) is at or below threshold (<span className="font-extrabold">{formatINR(threshold)}</span>). Raise a new Petty Cash PC immediately.
            </p>
          </div>
        </div>

        <div className="flex-shrink-0 self-end sm:self-auto pl-14 sm:pl-0">
          <Link
            href={`/admin/payment-certificates/new?tab=internal&type=petty-cash`}
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-amber-500 to-amber-600 dark:from-amber-400 dark:to-amber-500 hover:from-amber-600 hover:to-amber-700 dark:hover:from-amber-500 dark:hover:to-amber-600 text-slate-950 hover:text-black font-extrabold text-xs uppercase tracking-widest rounded-xl transition-all shadow-[0_4px_20px_0_rgba(245,158,11,0.25)] hover:shadow-[0_4px_24px_0_rgba(245,158,11,0.4)] active:scale-[0.98] border border-amber-400/30 dark:border-amber-300/30 group"
          >
            <span>Raise PC</span>
            <ArrowRight size={14} className="group-hover:translate-x-1 transition-transform" />
          </Link>
        </div>
      </div>
    </div>
  );
}
