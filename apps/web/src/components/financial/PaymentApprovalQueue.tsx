"use client";

import React, { useState } from 'react';
import { GlassCard } from '@/components/ui/GlassCard';
import { parse } from 'date-fns';
import ConfirmDialog from '@/components/ui/ConfirmDialog';

interface ApprovalTrail {
  action: string;
  user_id: string;
  timestamp: string;
}

interface PaymentCertificate {
  _id: string;
  vendor_id: string;
  vendor_name: string;
  payment_amount: number;
  status: string;
  created_at: string;
  approval_trail: ApprovalTrail[];
}

interface PaymentApprovalQueueProps {
  approvals: PaymentCertificate[];
  onApprove?: (id: string) => void;
  onReject?: (id: string, reason: string) => void;
}

export default function PaymentApprovalQueue({
  approvals,
  onApprove,
  onReject,
}: PaymentApprovalQueueProps) {
  const [rejectingId, setRejectingId] = useState<string | null>(null);
  const [rejectReason, setRejectReason] = useState('');
  const [approvingId, setApprovingId] = useState<string | null>(null);

  const handleApproveClick = (id: string) => {
    setApprovingId(id);
  };

  const confirmApprove = () => {
    if (approvingId) {
      onApprove?.(approvingId);
      setApprovingId(null);
    }
  };

  const handleRejectClick = (id: string) => {
    setRejectingId(id);
    setRejectReason('');
  };

  const handleRejectSubmit = (id: string) => {
    if (rejectReason.trim()) {
      onReject?.(id, rejectReason);
      setRejectingId(null);
      setRejectReason('');
    }
  };

  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'Submitted':
        return 'bg-blue-900 text-blue-100';
      case 'In Review':
        return 'bg-yellow-900 text-yellow-100';
      case 'Approved':
        return 'bg-green-900 text-green-100';
      case 'Rejected':
        return 'bg-red-900 text-red-100';
      default:
        return 'bg-gray-700 text-gray-100';
    }
  };

  const getDaysPending = (createdAt: string): number => {
    const created = parse(createdAt, "yyyy-MM-dd'T'HH:mm:ss'Z'", new Date());
    const days = Math.floor(
      (new Date().getTime() - created.getTime()) / (1000 * 60 * 60 * 24)
    );
    return Math.max(0, days);
  };

  return (
    <GlassCard className="p-6">
      <div className="space-y-4">
        <h2 className="text-2xl font-bold text-white">Pending Approvals</h2>

        {approvals.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-gray-400">No pending approvals</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-700">
                  <th className="text-left py-3 px-4 text-gray-300">Vendor</th>
                  <th className="text-right py-3 px-4 text-gray-300">Amount</th>
                  <th className="text-center py-3 px-4 text-gray-300">Submitted</th>
                  <th className="text-center py-3 px-4 text-gray-300">Days</th>
                  <th className="text-center py-3 px-4 text-gray-300">Status</th>
                  <th className="text-center py-3 px-4 text-gray-300">Actions</th>
                </tr>
              </thead>
              <tbody>
                {approvals.map((approval) => (
                  <React.Fragment key={approval._id}>
                    <tr className="border-b border-gray-800 hover:bg-gray-900 transition-colors">
                      <td className="py-4 px-4 text-white">{approval.vendor_name}</td>
                      <td className="py-4 px-4 text-right font-semibold text-teal-400">
                        ₹{approval.payment_amount.toLocaleString()}
                      </td>
                      <td className="py-4 px-4 text-center text-gray-400 text-xs">
                        {new Date(approval.created_at).toLocaleDateString()}
                      </td>
                      <td className="py-4 px-4 text-center text-gray-400">
                        {getDaysPending(approval.created_at)}d
                      </td>
                      <td className="py-4 px-4 text-center">
                        <span
                          className={`px-3 py-1 rounded-full text-xs font-semibold ${getStatusColor(
                            approval.status
                          )}`}
                        >
                          {approval.status}
                        </span>
                      </td>
                      <td className="py-4 px-4 text-center space-x-2">
                        <button
                          onClick={() => handleApproveClick(approval._id)}
                          className="px-3 py-1 bg-green-600 hover:bg-green-700 text-white rounded text-xs font-semibold transition"
                        >
                          Approve
                        </button>
                        <button
                          onClick={() => handleRejectClick(approval._id)}
                          className="px-3 py-1 bg-red-600 hover:bg-red-700 text-white rounded text-xs font-semibold transition"
                        >
                          Reject
                        </button>
                      </td>
                    </tr>
                    {rejectingId === approval._id && (
                      <tr className="bg-gray-900 border-b border-gray-800">
                        <td colSpan={6} className="py-4 px-4">
                          <div className="space-y-2">
                            <label className="block text-sm font-semibold text-white">
                              Rejection Reason
                            </label>
                            <textarea
                              value={rejectReason}
                              onChange={(e) => setRejectReason(e.target.value)}
                              placeholder="Enter reason for rejection..."
                              className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white text-sm focus:outline-none focus:border-teal-500"
                              rows={2}
                            />
                            <div className="flex gap-2">
                              <button
                                onClick={() => handleRejectSubmit(approval._id)}
                                className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded text-sm font-semibold transition"
                              >
                                Confirm Reject
                              </button>
                              <button
                                onClick={() => setRejectingId(null)}
                                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded text-sm font-semibold transition"
                              >
                                Cancel
                              </button>
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <ConfirmDialog
        isOpen={!!approvingId}
        onClose={() => setApprovingId(null)}
        onConfirm={confirmApprove}
        title="Approve Payment"
        description="Are you sure you want to approve this payment request? This will update the certificate status to 'Approved' and notify the accounts team."
        confirmText="Approve Payment"
        variant="info"
      />
    </GlassCard>
  );
}
