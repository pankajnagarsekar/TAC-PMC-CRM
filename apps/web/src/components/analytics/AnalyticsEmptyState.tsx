"use client";

import React from "react";
import { Info, ArrowRight } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";

interface AnalyticsEmptyStateProps {
  title?: string;
  description?: string;
  actionText?: string;
  actionTab?: string;
}

export default function AnalyticsEmptyState({
  title = "No baseline data found",
  description = "This analysis requires baseline schedule dates or costs to be initialized. Set baselines in the Grid view to activate tracking.",
  actionText = "Go to Grid View",
  actionTab = "grid"
}: AnalyticsEmptyStateProps) {
  const router = useRouter();
  const searchParams = useSearchParams();

  const handleAction = () => {
    const params = new URLSearchParams(searchParams.toString());
    params.set("tab", actionTab);
    router.replace(`?${params.toString()}`);
  };

  return (
    <div className="flex flex-col items-center justify-center p-8 text-center min-h-[300px] border border-dashed border-slate-200 dark:border-white/10 rounded-2xl bg-slate-50/50 dark:bg-white/[0.01]">
      <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-orange-500/10 text-orange-500 shadow-lg shadow-orange-500/10">
        <Info size={20} />
      </div>
      <h4 className="text-xs font-black uppercase tracking-wider text-slate-900 dark:text-white">{title}</h4>
      <p className="mt-2 text-[10px] font-medium text-slate-500 dark:text-slate-400 max-w-sm leading-normal">
        {description}
      </p>
      {actionText && (
        <button
          onClick={handleAction}
          className="mt-6 flex items-center gap-1.5 px-4 py-2 bg-orange-600 hover:bg-orange-500 text-white rounded-xl text-[10px] font-black uppercase tracking-widest transition-all shadow-md shadow-orange-500/10 active:scale-95"
        >
          <span>{actionText}</span>
          <ArrowRight size={10} />
        </button>
      )}
    </div>
  );
}
