"use client";

import React from 'react';
import useSWR from 'swr';
import { useProjectStore } from '@/store/projectStore';
import { fetcher } from '@/lib/api';
import BudgetTracker from '@/components/financial/BudgetTracker';
import CashFlowChart from '@/components/financial/CashFlowChart';
import PaymentApprovalQueue from '@/components/financial/PaymentApprovalQueue';
import MasterDataManager from '@/components/financial/MasterDataManager';

export default function FinancialDashboard() {
  const activeProject = useProjectStore((state) => state.activeProject);
  const projectId = activeProject?.project_id;

  // Default date range: last 30 days
  const today = new Date();
  const thirtyDaysAgo = new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000);
  const fromDate = thirtyDaysAgo.toISOString().split('T')[0];
  const toDate = today.toISOString().split('T')[0];

  // Fetch budgets
  const { data: budgetsData, isLoading: budgetsLoading, error: budgetsError } = useSWR(
    projectId ? `/api/v1/budgets?project_id=${projectId}&limit=100` : null,
    fetcher,
    {
      revalidateOnFocus: false,
      dedupingInterval: 60000,
    }
  );

  // Fetch cash flow statement
  const { data: cashFlowData, isLoading: cashFlowLoading, error: cashFlowError } = useSWR(
    projectId
      ? `/api/v1/cash/statement/${projectId}?from_date=${fromDate}&to_date=${toDate}`
      : null,
    fetcher,
    {
      revalidateOnFocus: false,
      dedupingInterval: 60000,
    }
  );

  // Fetch pending approvals
  const {
    data: pendingApprovalsData,
    isLoading: approvalsLoading,
    error: approvalsError,
  } = useSWR(
    projectId ? `/api/v1/payments/${projectId}/pending-approval` : null,
    fetcher,
    {
      revalidateOnFocus: false,
      dedupingInterval: 60000,
    }
  );

  // Fetch financial codes (master data)
  const { data: codesData, isLoading: codesLoading, error: codesError } = useSWR(
    '/api/v1/settings/codes',
    fetcher,
    {
      revalidateOnFocus: false,
      dedupingInterval: 60000,
    }
  );

  const isLoading = budgetsLoading || cashFlowLoading || approvalsLoading || codesLoading;
  const hasError = budgetsError || cashFlowError || approvalsError || codesError;

  // Handle approve action
  const handleApprovePayment = async (id: string) => {
    const payment = pendingApprovalsData?.find((p: { _id?: string, id?: string, version?: number }) => (p._id || p.id) === id);
    const version = payment?.version || 1;
    try {
      await fetch(`/api/v1/payments/${id}/approve?expected_version=${version}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
        },
      });
      // Refresh pending approvals
      window.location.reload();
    } catch (err) {
      console.error('Error approving payment:', err);
    }
  };

  // Handle reject action
  const handleRejectPayment = async (id: string, reason: string) => {
    const payment = pendingApprovalsData?.find((p: { _id?: string, id?: string, version?: number }) => (p._id || p.id) === id);
    const version = payment?.version || 1;
    try {
      await fetch(
        `/api/v1/payments/${id}/reject?reason=${encodeURIComponent(reason)}&expected_version=${version}`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
          },
        }
      );
      window.location.reload();
    } catch (err) {
      console.error('Error rejecting payment:', err);
    }
  };

  // Handle add code
  const handleAddCode = async (codeData: unknown) => {
    try {
      await fetch('/api/v1/settings/codes', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
        },
        body: JSON.stringify(codeData),
      });
      window.location.reload();
    } catch (err) {
      console.error('Error adding code:', err);
    }
  };

  // Handle update code
  const handleUpdateCode = async (id: string, codeData: unknown) => {
    try {
      await fetch(`/api/v1/settings/codes/${id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
        },
        body: JSON.stringify(codeData),
      });
      window.location.reload();
    } catch (err) {
      console.error('Error updating code:', err);
    }
  };

  // Handle delete code
  const handleDeleteCode = async (id: string) => {
    try {
      await fetch(`/api/v1/settings/codes/${id}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
        },
      });
      window.location.reload();
    } catch (err) {
      console.error('Error deleting code:', err);
    }
  };

  if (!projectId) {
    return (
      <div className="p-6 text-center">
        <p className="text-gray-400">Select a project to view financial dashboard</p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="p-6 text-center">
        <p className="text-gray-400">Loading financial data...</p>
      </div>
    );
  }

  if (hasError) {
    return (
      <div className="p-6 text-center">
        <p className="text-red-400">Error loading financial dashboard. Please try again.</p>
      </div>
    );
  }

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-white mb-2">Financial Dashboard</h1>
          <p className="text-gray-400">
            {activeProject?.project_name || 'Project'} • Overview and Management
          </p>
        </div>

        {/* 2-column layout on lg, 1-column on mobile */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column: Budget + Cash Flow */}
          <div className="lg:col-span-2 space-y-6">
            <BudgetTracker budgets={budgetsData || []} />
            {cashFlowData && <CashFlowChart cashFlow={cashFlowData} />}
          </div>

          {/* Right Column: Approvals + Master Data */}
          <div className="space-y-6">
            <PaymentApprovalQueue
              approvals={pendingApprovalsData || []}
              onApprove={handleApprovePayment}
              onReject={handleRejectPayment}
            />
            <MasterDataManager
              codes={codesData || []}
              onAdd={handleAddCode}
              onUpdate={handleUpdateCode}
              onDelete={handleDeleteCode}
            />
          </div>
        </div>
      </div>
    </main>
  );
}
