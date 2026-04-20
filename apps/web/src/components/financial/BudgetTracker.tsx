"use client";

import React from 'react';
import { GlassCard } from '@/components/ui/GlassCard';
import { formatINRShort } from '@/lib/formatters';

interface BudgetAllocation {
  code: string;
  budget: number;
  spent: number;
}

interface Budget {
  _id: string;
  project_id: string;
  organisation_id: string;
  total_budget: number;
  allocations: BudgetAllocation[];
  status: string;
  created_at: Date;
  updated_at: Date;
  version: number;
}

interface BudgetTrackerProps {
  budgets: Budget[];
}

export default function BudgetTracker({ budgets }: BudgetTrackerProps) {
  // Filter ACTIVE budgets only
  const activeBudgets = budgets.filter((b) => b.status === 'ACTIVE');

  // Calculate total spent and budget
  const totalBudget = activeBudgets.reduce((sum, b) => sum + b.total_budget, 0);
  const totalSpent = activeBudgets.reduce(
    (sum, b) =>
      sum +
      b.allocations.reduce((allocSum, a) => allocSum + a.spent, 0),
    0
  );

  const percentSpent = totalBudget > 0 ? (totalSpent / totalBudget) * 100 : 0;

  // Get color based on percentage
  const getColor = (percent: number): string => {
    if (percent < 70) return 'bg-green-500';
    if (percent < 90) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  return (
    <GlassCard className="p-6">
      <div className="space-y-6">
        <h2 className="text-2xl font-bold text-white">Budget Summary</h2>

        {activeBudgets.length === 0 ? (
          <p className="text-gray-400">No active budgets</p>
        ) : (
          <>
            {activeBudgets.map((budget) => (
              <div key={budget._id} className="border-b border-gray-700 pb-4">
                <h3 className="text-lg font-semibold text-gray-100 mb-4">
                  Budget {budget._id.slice(0, 8)}
                </h3>
                {budget.allocations.map((alloc) => {
                  const allocPercent = (alloc.spent / alloc.budget) * 100;
                  const remaining = ((alloc.budget - alloc.spent) / alloc.budget) * 100;
                  const colorClass = getColor(allocPercent);

                  return (
                    <div key={alloc.code} className="mb-3">
                      <div className="flex justify-between mb-2">
                        <span className="text-gray-300">{alloc.code}</span>
                        <span className="text-gray-400 text-sm">
                          {formatINRShort(alloc.spent)} / {formatINRShort(alloc.budget)}
                        </span>
                      </div>
                      <div className="w-full bg-gray-700 rounded-full h-2">
                        <div
                          className={`${colorClass} h-2 rounded-full`}
                          style={{ width: `${Math.min(allocPercent, 100)}%` }}
                        />
                      </div>
                      <span className="text-xs text-gray-500">{remaining.toFixed(1)}% remaining</span>
                    </div>
                  );
                })}
              </div>
            ))}

            {/* Total Summary */}
            <div className="mt-6 pt-6 border-t border-gray-700">
              <div className="flex justify-between mb-2">
                <span className="text-gray-300 font-semibold">Total Spent</span>
                <span className="text-white font-bold">
                  {formatINRShort(totalSpent)} / {formatINRShort(totalBudget)}
                </span>
              </div>
              <div className="w-full bg-gray-700 rounded-full h-3">
                <div
                  className={`${getColor(percentSpent)} h-3 rounded-full`}
                  style={{ width: `${Math.min(percentSpent, 100)}%` }}
                />
              </div>
              <div className="text-right mt-2">
                <span className="text-gray-400">
                  {percentSpent.toFixed(1)}% of total budget
                </span>
              </div>
            </div>
          </>
        )}
      </div>
    </GlassCard>
  );
}
