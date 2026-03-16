"use client";

import { useState, useEffect } from "react";
import useSWR from "swr";
import {
  Wallet,
  Search,
  ArrowRight,
  Loader2,
  IndianRupee,
  AlertTriangle,
  Coins,
  Building2,
  Plus,
  Receipt,
} from "lucide-react";
import Link from "next/link";

import api, { fetcher } from "@/lib/api";
import { useProjectStore } from "@/store/projectStore";
import { FundAllocation } from "@/types/api";
import { formatCurrency } from "@tac-pmc/ui";
import ExpenseEntryModal from "@/components/petty-cash/ExpenseEntryModal";

const isPettyCashCategory = (name: string | undefined, id: string): boolean => {
  if (!name) return false;
  const lower = name.toLowerCase();
  return (
    lower.includes("petty") ||
    lower.includes("cash") ||
    lower.includes("p-cash")
  );
};

const isOVHCategory = (name: string | undefined, id: string): boolean => {
  if (!name) return false;
  const lower = name.toLowerCase();
  return (
    lower.includes("ovh") ||
    lower.includes("overhead") ||
    lower.includes("site overhead") ||
    lower.includes("oh")
  );
};

export default function PettyCashDashboard() {
  const { activeProject } = useProjectStore();
  const [searchTerm, setSearchTerm] = useState("");
  const [now, setNow] = useState<Date>(new Date());
  const [showExpenseModal, setShowExpenseModal] = useState(false);
  const [showNegativeCashModal, setShowNegativeCashModal] = useState(false);

  // 3.3.4: Client-side 60-second timer recalculation
  useEffect(() => {
    const interval = setInterval(() => {
      setNow(new Date());
    }, 60000);
    return () => clearInterval(interval);
  }, []);

  const { data, error, isLoading, mutate } = useSWR<{
    items: FundAllocation[];
  }>(
    activeProject
      ? `/api/projects/${activeProject.project_id}/fund-allocations`
      : null,
    fetcher,
  );

  const {
    data: summary,
    isLoading: summaryLoading,
    mutate: mutateSummary,
  } = useSWR<any>(
    activeProject
      ? `/api/projects/${activeProject.project_id}/cash-summary`
      : null,
    fetcher,
  );

  // 3.3.10: Fetch transaction history
  const {
    data: transactionsData,
    isLoading: transactionsLoading,
    mutate: mutateTransactions,
  } = useSWR<{ items: any[] }>(
    activeProject
      ? `/api/projects/${activeProject.project_id}/cash-transactions?limit=50`
      : null,
    fetcher,
  );

  // Force refresh every 60 seconds
  useEffect(() => {
    if (!activeProject) return;
    const interval = setInterval(() => {
      mutate();
      mutateSummary();
      mutateTransactions();
    }, 60000);
    return () => clearInterval(interval);
  }, [activeProject, mutate, mutateSummary, mutateTransactions]);

  const allocations = data?.items || [];
  const categories = summary?.categories || [];

  // 3.3.2: Use categories from summary if available, otherwise use fund allocations
  const hasCategoriesData = categories.length > 0;

  // Get totals from categories or allocations
  const pettyCashCategories = hasCategoriesData
    ? categories.filter((c: any) =>
        isPettyCashCategory(c.category_name, c.category_id),
      )
    : allocations.filter((a) =>
        isPettyCashCategory(a.category_name, a.category_id),
      );

  const ovhCategories = hasCategoriesData
    ? categories.filter((c: any) =>
        isOVHCategory(c.category_name, c.category_id),
      )
    : allocations.filter((a) => isOVHCategory(a.category_name, a.category_id));

  // 3.3.2: Separate Petty Cash and OVH allocations
  const pettyCashAllocations = allocations.filter((a) =>
    isPettyCashCategory(a.category_name, a.category_id),
  );
  const ovhAllocations = allocations.filter((a) =>
    isOVHCategory(a.category_name, a.category_id),
  );
  const otherAllocations = allocations.filter(
    (a) =>
      !isPettyCashCategory(a.category_name, a.category_id) &&
      !isOVHCategory(a.category_name, a.category_id),
  );

  const filteredAllocations = allocations.filter(
    (a) =>
      a.category_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      a.category_id.toLowerCase().includes(searchTerm.toLowerCase()),
  );

  const totalRemaining =
    summary?.summary?.total_cash_in_hand ??
    allocations.reduce((sum, a) => sum + (a.allocation_remaining || 0), 0);

  // Get overall flags from categories
  const allCategories = summary?.categories || [];
  const isNegative = totalRemaining < 0;
  const isBelowThreshold = allCategories.some((c: any) => c.threshold_breached);

  // Calculate totals from categories if available
  const pettyCashTotal =
    allCategories.length > 0
      ? allCategories
          .filter((c: any) =>
            isPettyCashCategory(c.category_name, c.category_id),
          )
          .reduce((sum: number, c: any) => sum + (c.cash_in_hand || 0), 0)
      : allocations
          .filter((a) => isPettyCashCategory(a.category_name, a.category_id))
          .reduce((sum, a) => sum + (a.allocation_remaining || 0), 0);

  const ovhTotal =
    allCategories.length > 0
      ? allCategories
          .filter((c: any) => isOVHCategory(c.category_name, c.category_id))
          .reduce((sum: number, c: any) => sum + (c.cash_in_hand || 0), 0)
      : allocations
          .filter((a) => isOVHCategory(a.category_name, a.category_id))
          .reduce((sum, a) => sum + (a.allocation_remaining || 0), 0);

  const isPettyCashNegative = pettyCashTotal < 0;
  const isOVHNegative = ovhTotal < 0;

  // 3.3.2: Check if below threshold (but not negative) for amber coloring
  const isPettyCashBelowThreshold =
    !isPettyCashNegative &&
    pettyCashCategories.some((c: any) => c.threshold_breached);
  const isOVHBelowThreshold =
    !isOVHNegative && ovhCategories.some((c: any) => c.threshold_breached);

  // Calculate days since last PC close with live updates
  const getDaysSince = (
    days: number | null,
  ): { value: number; color: string } => {
    if (days === null) return { value: 0, color: "text-slate-400" };
    if (days <= 10) return { value: days, color: "text-emerald-400" };
    if (days <= 14) return { value: days, color: "text-amber-400" };
    return { value: days, color: "text-red-400" };
  };

  const daysInfo = getDaysSince(
    summary?.summary?.days_since_last_pc_close ?? null,
  );

  if (!activeProject) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-400">
        <p>Please select a project to view Liquidity Allocations.</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-500/10 border border-red-500/20 text-red-500 p-4 rounded-xl">
        Failed to load fund allocations. {error.message}
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <Wallet className="text-amber-500" />
            Petty Cash & Site Overheads
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Manage live site spending ceilings injected from Payment
            Certificates.
          </p>
        </div>
        <button
          onClick={() => setShowExpenseModal(true)}
          className="flex items-center gap-2 bg-amber-500 hover:bg-amber-600 text-slate-900 font-semibold px-4 py-2 rounded-lg transition-colors"
        >
          <Plus size={18} />
          Add Expense
        </button>
      </div>

      {/* 3.3.6: Negative cash warning with tooltip/modal */}
      {isNegative && (
        <div
          onClick={() => setShowNegativeCashModal(true)}
          className="bg-red-500/10 border border-red-500/20 text-red-500 p-4 rounded-xl flex items-center gap-3 animate-in slide-in-from-top duration-500 cursor-pointer hover:bg-red-500/20 transition-colors"
        >
          <AlertTriangle size={20} className="animate-pulse" />
          <div>
            <p className="text-sm font-bold">Critical: Negative Liquidity</p>
            <p className="text-xs opacity-80">
              Site balance is below ₹0. Click for details.
            </p>
          </div>
        </div>
      )}
      {/* 3.3.5: Threshold alert banner with "Create PC" quick-link button */}
      {!isNegative && isBelowThreshold && (
        <div className="bg-amber-500/10 border border-amber-500/20 text-amber-500 p-4 rounded-xl flex items-center justify-between animate-in slide-in-from-top duration-500">
          <div className="flex items-center gap-3">
            <AlertTriangle size={20} />
            <div>
              <p className="text-sm font-bold">Low Liquidity Warning</p>
              <p className="text-xs opacity-80">
                Site funds are below the threshold. Consider closing pending
                Fund Transfer PCs.
              </p>
            </div>
          </div>
          <Link
            href="/admin/payment-certificates/new?mode=fund-request"
            className="flex items-center gap-2 bg-amber-500 hover:bg-amber-600 text-slate-900 font-semibold px-4 py-2 rounded-lg transition-colors text-sm whitespace-nowrap"
          >
            Create PC
            <ArrowRight size={16} />
          </Link>
        </div>
      )}

      {/* 3.3.2: Separate KPI Cards for Petty Cash and OVH */}
      {hasCategoriesData ||
      pettyCashAllocations.length > 0 ||
      ovhAllocations.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Petty Cash Card */}
          <div
            className={`bg-slate-900 border ${
              isPettyCashNegative
                ? "border-red-900/50"
                : isPettyCashBelowThreshold
                  ? "border-amber-500/50"
                  : "border-slate-800"
            } rounded-xl p-6 shadow-xl relative overflow-hidden transition-colors duration-500`}
          >
            <div className="absolute top-0 right-0 p-6 opacity-5">
              <Coins size={100} />
            </div>
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-amber-500/20 rounded-lg">
                <Coins className="text-amber-500" size={20} />
              </div>
              <div>
                <p className="text-slate-400 text-sm uppercase tracking-widest font-bold">
                  Petty Cash
                </p>
                {pettyCashCategories.length > 0 && (
                  <p className="text-[10px] text-slate-500">
                    {pettyCashCategories.length} category(ies)
                  </p>
                )}
              </div>
            </div>
            {isLoading || summaryLoading ? (
              <Loader2 className="w-6 h-6 text-amber-500 animate-spin" />
            ) : (
              <p
                className={`text-3xl font-mono font-bold ${
                  isPettyCashNegative
                    ? "text-red-500"
                    : isPettyCashBelowThreshold
                      ? "text-amber-500"
                      : "text-emerald-400"
                }`}
              >
                {formatCurrency(pettyCashTotal)}
              </p>
            )}
            {isPettyCashNegative && (
              <div className="flex items-center gap-1 text-[10px] font-bold uppercase text-red-500 mt-2 tracking-tighter">
                <AlertTriangle size={12} className="animate-pulse" /> Overdrawn
              </div>
            )}
            {isPettyCashBelowThreshold && !isPettyCashNegative && (
              <div className="flex items-center gap-1 text-[10px] font-bold uppercase text-amber-500 mt-2 tracking-tighter">
                <AlertTriangle size={12} /> Below Threshold
              </div>
            )}
          </div>

          {/* OVH Card */}
          <div
            className={`bg-slate-900 border ${
              isOVHNegative
                ? "border-red-900/50"
                : isOVHBelowThreshold
                  ? "border-amber-500/50"
                  : "border-slate-800"
            } rounded-xl p-6 shadow-xl relative overflow-hidden transition-colors duration-500`}
          >
            <div className="absolute top-0 right-0 p-6 opacity-5">
              <Building2 size={100} />
            </div>
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-blue-500/20 rounded-lg">
                <Building2 className="text-blue-500" size={20} />
              </div>
              <div>
                <p className="text-slate-400 text-sm uppercase tracking-widest font-bold">
                  Site Overheads
                </p>
                {ovhCategories.length > 0 && (
                  <p className="text-[10px] text-slate-500">
                    {ovhCategories.length} category(ies)
                  </p>
                )}
              </div>
            </div>
            {isLoading || summaryLoading ? (
              <Loader2 className="w-6 h-6 text-blue-500 animate-spin" />
            ) : (
              <p
                className={`text-3xl font-mono font-bold ${
                  isOVHNegative
                    ? "text-red-500"
                    : isOVHBelowThreshold
                      ? "text-amber-500"
                      : "text-emerald-400"
                }`}
              >
                {formatCurrency(ovhTotal)}
              </p>
            )}
            {isOVHNegative && (
              <div className="flex items-center gap-1 text-[10px] font-bold uppercase text-red-500 mt-2 tracking-tighter">
                <AlertTriangle size={12} className="animate-pulse" /> Overdrawn
              </div>
            )}
            {isOVHBelowThreshold && !isOVHNegative && (
              <div className="flex items-center gap-1 text-[10px] font-bold uppercase text-amber-500 mt-2 tracking-tighter">
                <AlertTriangle size={12} /> Below Threshold
              </div>
            )}
          </div>
        </div>
      ) : (
        /* Fallback: Single Total Card */
        <div
          className={`bg-slate-900 border ${isNegative ? "border-red-900/50" : "border-slate-800"} rounded-xl p-6 shadow-xl relative overflow-hidden transition-colors duration-500`}
        >
          <div className="absolute top-0 right-0 p-8 opacity-5">
            <IndianRupee size={150} />
          </div>
          <p className="text-slate-400 text-sm uppercase tracking-widest font-bold mb-2">
            Total Site Liquidity
          </p>
          {isLoading || summaryLoading ? (
            <Loader2 className="w-6 h-6 text-amber-500 animate-spin mt-2" />
          ) : (
            <p
              className={`text-4xl font-mono font-bold ${isNegative ? "text-red-500" : "text-emerald-400"}`}
            >
              {formatCurrency(totalRemaining)}
            </p>
          )}
        </div>
      )}

      {/* 3.3.3: Per-category 15-Day Countdown Timers */}
      {hasCategoriesData && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {categories
            .filter(
              (c: any) =>
                isPettyCashCategory(c.category_name, c.category_id) ||
                isOVHCategory(c.category_name, c.category_id),
            )
            .map((cat: any) => {
              const days = cat.days_since_last_pc_close;
              const catDaysInfo = getDaysSince(days);
              const isPetty = isPettyCashCategory(
                cat.category_name,
                cat.category_id,
              );

              return (
                <div
                  key={cat.category_id}
                  className="bg-slate-900 border border-slate-800 rounded-xl p-4"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      {isPetty ? (
                        <Coins className="text-amber-500" size={18} />
                      ) : (
                        <Building2 className="text-blue-500" size={18} />
                      )}
                      <p className="text-slate-400 text-xs uppercase tracking-widest font-bold">
                        {cat.category_name} - Days Since Replenishment
                      </p>
                    </div>
                    <div
                      className={`px-3 py-1 rounded-full text-xs font-bold uppercase ${
                        catDaysInfo.value <= 10
                          ? "bg-emerald-500/20 text-emerald-400"
                          : catDaysInfo.value <= 14
                            ? "bg-amber-500/20 text-amber-400"
                            : "bg-red-500/20 text-red-400"
                      }`}
                    >
                      {catDaysInfo.value <= 10
                        ? "Normal"
                        : catDaysInfo.value <= 14
                          ? "Warning"
                          : "Critical"}
                    </div>
                  </div>
                  <div className="mt-3">
                    <p
                      className={`text-3xl font-mono font-bold ${catDaysInfo.color}`}
                    >
                      {days !== null ? `${days} days` : "N/A"}
                    </p>
                  </div>
                </div>
              );
            })}
        </div>
      )}

      {/* Global Stats */}
      <div
        className={`bg-slate-900 border ${isNegative ? "border-red-900/50" : "border-slate-800"} rounded-xl p-6 shadow-xl relative overflow-hidden transition-colors duration-500`}
      >
        <div className="absolute top-0 right-0 p-8 opacity-5">
          <IndianRupee size={150} />
        </div>
        <p className="text-slate-400 text-sm uppercase tracking-widest font-bold mb-2">
          Total Site Liquidity
        </p>
        {isLoading || summaryLoading ? (
          <Loader2 className="w-6 h-6 text-amber-500 animate-spin mt-2" />
        ) : (
          <p
            className={`text-4xl font-mono font-bold ${isNegative ? "text-red-500" : "text-emerald-400"}`}
          >
            {formatCurrency(totalRemaining)}
          </p>
        )}
        {summary?.summary?.days_since_last_pc_close !== undefined && (
          <p className="text-[10px] text-slate-500 uppercase tracking-widest mt-4 font-bold">
            Last replenishment:{" "}
            <span className="text-slate-300">
              {summary?.summary?.days_since_last_pc_close} days ago
            </span>
          </p>
        )}
      </div>

      {/* Search & Action */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col md:flex-row gap-4 items-center justify-between">
        <div className="relative w-full md:w-96">
          <Search
            className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500"
            size={18}
          />
          <input
            type="text"
            placeholder="Search Categories..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-10 pr-4 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-amber-500/50"
          />
        </div>
      </div>

      {/* Allocation Grids */}
      {isLoading ? (
        <div className="flex justify-center p-12">
          <Loader2 className="w-8 h-8 text-amber-500 animate-spin" />
        </div>
      ) : filteredAllocations.length === 0 ? (
        <div className="text-center py-12 bg-slate-900/50 rounded-xl border border-slate-800 border-dashed">
          <Wallet className="w-12 h-12 text-slate-600 mx-auto mb-3" />
          <h3 className="text-lg font-medium text-white mb-1">
            No Active Allocations
          </h3>
          <p className="text-slate-400 text-sm">
            Fund allocations are generated when a Fund Transfer Payment
            Certificate is approved and closed. No liquid funds are currently
            sitting on site.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredAllocations.map((alloc) => {
            const usagePercent =
              alloc.allocation_total > 0
                ? ((alloc.allocation_total - alloc.allocation_remaining) /
                    alloc.allocation_total) *
                  100
                : 0;

            return (
              <Link
                href={`/admin/petty-cash/${alloc.category_id}`}
                key={alloc._id}
                className="block bg-slate-900 border border-slate-800 hover:border-amber-500/50 transition-all duration-300 rounded-xl p-5 group"
              >
                <div className="flex justify-between items-start mb-4">
                  <h3 className="text-white font-medium text-lg leading-tight">
                    {alloc.category_name || "Unknown Category"}
                  </h3>
                  <ArrowRight
                    className="text-slate-600 group-hover:text-amber-500 transition-colors"
                    size={20}
                  />
                </div>

                <p className="text-xs text-slate-500 font-mono mb-6">
                  Code: {alloc.category_id}
                </p>

                <div className="space-y-4">
                  <div>
                    <div className="flex justify-between text-xs mb-2">
                      <span className="text-slate-400">Remaining</span>
                      <span className="text-white font-mono font-bold">
                        {formatCurrency(alloc.allocation_remaining)}
                      </span>
                    </div>
                    <div className="w-full bg-slate-950 rounded-full h-2">
                      <div
                        className={`h-2 rounded-full ${usagePercent > 90 ? "bg-red-500" : usagePercent > 70 ? "bg-amber-500" : "bg-emerald-500"}`}
                        style={{ width: `${Math.min(100, usagePercent)}%` }}
                      />
                    </div>
                  </div>

                  <div className="flex justify-between items-center text-xs">
                    <span className="text-slate-500">
                      Limits Set:{" "}
                      <span className="text-slate-300 font-mono">
                        {formatCurrency(alloc.allocation_total)}
                      </span>
                    </span>
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      )}

      {/* 3.3.10: Transaction History Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
        <div className="flex items-center gap-3 mb-6">
          <Receipt className="text-amber-500" size={20} />
          <h2 className="text-lg font-semibold text-white">
            Transaction History
          </h2>
        </div>

        <div className="overflow-x-auto">
          {transactionsLoading ? (
            <div className="flex justify-center py-8">
              <Loader2 className="w-6 h-6 text-amber-500 animate-spin" />
            </div>
          ) : transactionsData?.items?.length === 0 ? (
            <div className="py-8 text-center text-slate-500">
              <Receipt className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p className="text-sm">No transactions yet</p>
            </div>
          ) : (
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-800">
                  <th className="text-left text-xs font-bold text-slate-400 uppercase tracking-wider py-3 px-4">
                    Date
                  </th>
                  <th className="text-left text-xs font-bold text-slate-400 uppercase tracking-wider py-3 px-4">
                    Category
                  </th>
                  <th className="text-left text-xs font-bold text-slate-400 uppercase tracking-wider py-3 px-4">
                    Purpose
                  </th>
                  <th className="text-left text-xs font-bold text-slate-400 uppercase tracking-wider py-3 px-4">
                    Bill Ref
                  </th>
                  <th className="text-right text-xs font-bold text-slate-400 uppercase tracking-wider py-3 px-4">
                    Type
                  </th>
                  <th className="text-right text-xs font-bold text-slate-400 uppercase tracking-wider py-3 px-4">
                    Amount
                  </th>
                  <th className="text-right text-xs font-bold text-slate-400 uppercase tracking-wider py-3 px-4">
                    Running Balance
                  </th>
                </tr>
              </thead>
              <tbody>
                {transactionsData?.items?.map((txn: any, index: number) => {
                  // 3.3.10: Compute running balance
                  // Sort by date ascending to calculate cumulative balance
                  const sortedTxns = [...(transactionsData?.items || [])].sort(
                    (a, b) =>
                      new Date(a.created_at).getTime() -
                      new Date(b.created_at).getTime(),
                  );
                  let runningBalance = 0;
                  for (let i = 0; i <= index; i++) {
                    const t = sortedTxns[i];
                    const amt = t.amount || 0;
                    if (t.type === "CREDIT") {
                      runningBalance += amt;
                    } else {
                      runningBalance -= amt;
                    }
                  }
                  const currentTxnBalance = runningBalance;

                  return (
                    <tr
                      key={txn._id || index}
                      className="border-b border-slate-800/50 hover:bg-slate-800/30"
                    >
                      <td className="py-3 px-4 text-sm text-slate-300">
                        {txn.created_at
                          ? new Date(txn.created_at).toLocaleDateString(
                              "en-IN",
                              {
                                day: "2-digit",
                                month: "short",
                                year: "numeric",
                              },
                            )
                          : "-"}
                      </td>
                      <td className="py-3 px-4 text-sm text-slate-300">
                        {txn.category_id?.slice(0, 8) || "-"}...
                      </td>
                      <td className="py-3 px-4 text-sm text-slate-300">
                        {txn.purpose || "-"}
                      </td>
                      <td className="py-3 px-4 text-sm text-slate-400 font-mono">
                        {txn.bill_reference || "-"}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <span
                          className={`text-xs font-medium px-2 py-1 rounded ${
                            txn.type === "CREDIT"
                              ? "bg-emerald-500/20 text-emerald-400"
                              : "bg-red-500/20 text-red-400"
                          }`}
                        >
                          {txn.type || "DEBIT"}
                        </span>
                      </td>
                      <td
                        className={`py-3 px-4 text-right font-mono ${
                          txn.type === "CREDIT"
                            ? "text-emerald-400"
                            : "text-red-400"
                        }`}
                      >
                        {txn.type === "CREDIT" ? "+" : "-"}
                        {formatCurrency(txn.amount || 0)}
                      </td>
                      <td
                        className={`py-3 px-4 text-right font-mono ${
                          currentTxnBalance < 0
                            ? "text-red-400"
                            : "text-emerald-400"
                        }`}
                      >
                        {formatCurrency(currentTxnBalance)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* 3.3.7: Expense Entry Modal */}
      {activeProject && (
        <ExpenseEntryModal
          isOpen={showExpenseModal}
          onClose={() => setShowExpenseModal(false)}
          onSuccess={() => {
            mutate();
            mutateSummary();
            mutateTransactions();
          }}
          projectId={activeProject.project_id}
        />
      )}

      {/* 3.3.6: Negative Cash Modal explaining the negative state */}
      {showNegativeCashModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={() => setShowNegativeCashModal(false)}
          />
          <div className="relative bg-slate-900 border border-red-500/30 rounded-xl w-full max-w-md mx-4 shadow-2xl animate-in zoom-in-95 duration-200">
            <div className="p-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="p-3 bg-red-500/20 rounded-full">
                  <AlertTriangle className="text-red-500" size={24} />
                </div>
                <h3 className="text-xl font-semibold text-white">
                  Negative Cash Status
                </h3>
              </div>

              <div className="space-y-4 text-slate-300">
                <p>
                  Your{" "}
                  <strong className="text-red-400">
                    Site Liquidity is negative
                  </strong>{" "}
                  — total expenses exceed funds received from Payment
                  Certificates.
                </p>

                <div className="bg-slate-800 rounded-lg p-4 space-y-2">
                  <p className="text-sm font-medium text-slate-400">
                    What this means:
                  </p>
                  <ul className="text-sm space-y-1">
                    <li>• Expenses have exceeded available funds</li>
                    <li>• Operations are being funded from other sources</li>
                    <li>• Immediate action required to normalize</li>
                  </ul>
                </div>

                <div className="bg-slate-800 rounded-lg p-4 space-y-2">
                  <p className="text-sm font-medium text-slate-400">
                    Recommended Actions:
                  </p>
                  <ul className="text-sm space-y-1">
                    <li>
                      • Close pending Fund Transfer PCs to replenish funds
                    </li>
                    <li>
                      • Create new Payment Certificates for immediate injection
                    </li>
                    <li>• Review and reduce upcoming expenses</li>
                  </ul>
                </div>
              </div>

              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => setShowNegativeCashModal(false)}
                  className="flex-1 bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium py-2.5 rounded-lg transition-colors"
                >
                  Close
                </button>
                <Link
                  href="/admin/payment-certificates/new?mode=fund-request"
                  onClick={() => setShowNegativeCashModal(false)}
                  className="flex-1 bg-red-500 hover:bg-red-600 text-white font-semibold py-2.5 rounded-lg transition-colors text-center"
                >
                  Create PC
                </Link>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
