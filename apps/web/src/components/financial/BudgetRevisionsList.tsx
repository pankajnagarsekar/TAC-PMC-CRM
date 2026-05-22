"use client";

import React, { useState } from "react";
import useSWR from "swr";
import { fetcher, budgetRevisionApi } from "@/lib/api";
import { useAuthStore } from "@/store/authStore";
import {
  FileText,
  AlertCircle,
  Check,
  X,
  Send,
  Loader2,
  Calendar,
  User,
  ArrowRight,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import { toast } from "sonner";
import { formatCurrency } from "@/lib/financial";
import { BudgetRevision, DerivedFinancialState } from "@/types/api";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "@tac-pmc/ui";

interface BudgetRevisionsListProps {
  projectId: string;
  categories: DerivedFinancialState[];
  onRefresh: () => void;
}

export default function BudgetRevisionsList({
  projectId,
  categories,
  onRefresh,
}: BudgetRevisionsListProps) {
  const { user, isAdmin } = useAuthStore();
  const showAdminActions = isAdmin();

  const {
    data: revisions,
    error,
    mutate,
    isLoading,
  } = useSWR<BudgetRevision[]>(
    `/api/v1/budgets/revisions/project/${projectId}`,
    fetcher
  );

  // Rejection modal states
  const [rejectingRevision, setRejectingRevision] = useState<BudgetRevision | null>(null);
  const [rejectionComment, setRejectionComment] = useState("");
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const getCategoryDetails = (catId: string) => {
    const cat = categories.find((c) => c.category_id === catId);
    return cat
      ? { code: cat.category_code, name: cat.category_name }
      : { code: catId.substring(0, 5), name: "Unknown Category" };
  };

  const handleDownload = async (revisionId: string, documentName: string) => {
    if (!revisionId) return;
    toast.info("Downloading file...");
    try {
      await budgetRevisionApi.downloadAttachment(revisionId, documentName);
    } catch (err: any) {
      toast.error("Download Failed", {
        description: err.response?.data?.detail || "Could not retrieve the attachment from storage.",
      });
    }
  };

  const handleSubmit = async (revisionId: string) => {
    setActionLoading(revisionId);
    try {
      await budgetRevisionApi.submit(revisionId);
      toast.success("Variation Order Submitted", {
        description: "The budget revision request is now under admin review.",
      });
      mutate();
      onRefresh();
    } catch (err: any) {
      toast.error("Failed to Submit", {
        description: err.response?.data?.detail || "An error occurred.",
      });
    } finally {
      setActionLoading(null);
    }
  };

  const handleApprove = async (revisionId: string) => {
    setActionLoading(revisionId);
    try {
      await budgetRevisionApi.approve(revisionId);
      toast.success("Variation Order Approved", {
        description: "The budget revision has been finalized and category budgets updated.",
      });
      mutate();
      onRefresh();
    } catch (err: any) {
      toast.error("Approval Failed", {
        description: err.response?.data?.detail || "An error occurred during approval.",
      });
    } finally {
      setActionLoading(null);
    }
  };

  const handleOpenRejectModal = (revision: BudgetRevision) => {
    setRejectingRevision(revision);
    setRejectionComment("");
  };

  const handleReject = async () => {
    if (!rejectingRevision || !rejectingRevision.id && !rejectingRevision._id) return;
    const revisionId = (rejectingRevision.id || rejectingRevision._id) as string;

    if (rejectionComment.trim().length < 5) {
      toast.error("Validation Error", {
        description: "Please provide a rejection comment (min 5 characters).",
      });
      return;
    }

    setActionLoading(revisionId);
    try {
      await budgetRevisionApi.reject(revisionId, {
        expected_version: rejectingRevision.version || 1,
        comment: rejectionComment.trim(),
      });
      toast.success("Variation Order Rejected", {
        description: "The budget revision request was rejected.",
      });
      setRejectingRevision(null);
      mutate();
      onRefresh();
    } catch (err: any) {
      toast.error("Rejection Failed", {
        description: err.response?.data?.detail || "An error occurred.",
      });
    } finally {
      setActionLoading(null);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "DRAFT":
        return (
          <span className="px-2.5 py-1 rounded-full text-[10px] font-black uppercase tracking-wider bg-zinc-100 dark:bg-zinc-800 text-zinc-500 dark:text-zinc-400 border border-zinc-200 dark:border-zinc-700 shadow-sm">
            Draft
          </span>
        );
      case "SUBMITTED":
        return (
          <span className="px-2.5 py-1 rounded-full text-[10px] font-black uppercase tracking-wider bg-amber-500/10 text-amber-600 dark:text-amber-500 border border-amber-500/20 shadow-sm">
            Submitted
          </span>
        );
      case "APPROVED":
        return (
          <span className="px-2.5 py-1 rounded-full text-[10px] font-black uppercase tracking-wider bg-emerald-500/10 text-emerald-600 dark:text-emerald-500 border border-emerald-500/20 shadow-sm">
            Approved
          </span>
        );
      case "REJECTED":
        return (
          <span className="px-2.5 py-1 rounded-full text-[10px] font-black uppercase tracking-wider bg-rose-500/10 text-rose-600 dark:text-rose-500 border border-rose-500/20 shadow-sm">
            Rejected
          </span>
        );
      default:
        return (
          <span className="px-2.5 py-1 rounded-full text-[10px] font-black uppercase tracking-wider bg-zinc-100 dark:bg-zinc-800 text-zinc-500 dark:text-zinc-400 border border-zinc-200 dark:border-zinc-700 shadow-sm">
            {status}
          </span>
        );
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-8 bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-900 rounded-3xl min-h-[200px]">
        <Loader2 className="w-6 h-6 text-orange-600 dark:text-orange-500 animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 bg-rose-500/5 border border-rose-500/10 rounded-3xl text-rose-600 dark:text-rose-400 text-sm flex items-start gap-3">
        <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
        <div>
          <h4 className="font-bold">Failed to load budget revisions</h4>
          <p className="text-xs text-rose-500/70 mt-1">
            There was a problem communicating with the financial ledger. Please try again later.
          </p>
        </div>
      </div>
    );
  }

  const revisionsList = revisions || [];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold text-zinc-900 dark:text-white flex items-center gap-2">
            Variation Order (VO) Registry
            <span className="text-[10px] bg-zinc-100 dark:bg-zinc-800 px-2 py-0.5 rounded font-mono text-zinc-500 dark:text-zinc-400 font-bold border border-zinc-200 dark:border-transparent">
              {revisionsList.length} LOGGED
            </span>
          </h2>
          <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1">
            Formal audit trail of all project budget revision requests and approval actions.
          </p>
        </div>
      </div>

      <div className="bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-900 rounded-3xl overflow-hidden shadow-sm">
        {revisionsList.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
            <div className="w-12 h-12 rounded-full bg-zinc-50 dark:bg-zinc-900 border border-zinc-100 dark:border-zinc-800 flex items-center justify-center mb-3">
              <FileText className="text-zinc-400 dark:text-zinc-500 w-5 h-5" />
            </div>
            <h3 className="text-sm font-bold text-zinc-700 dark:text-zinc-300">No Revisions Logged</h3>
            <p className="text-xs text-zinc-400 dark:text-zinc-500 mt-1 max-w-sm">
              All budget edits go through a Variation Order workflow. Use the table actions to raise a new request.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-zinc-100 dark:border-zinc-900 bg-zinc-50/50 dark:bg-zinc-900/30">
                  <th className="p-4 text-xs font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400 w-1/5">
                    Category
                  </th>
                  <th className="p-4 text-xs font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">
                    Proposed Change
                  </th>
                  <th className="p-4 text-xs font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400 w-1/4">
                    Reason / Details
                  </th>
                  <th className="p-4 text-xs font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">
                    Supporting Doc
                  </th>
                  <th className="p-4 text-xs font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">
                    Requested By
                  </th>
                  <th className="p-4 text-xs font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400 text-center">
                    Status
                  </th>
                  <th className="p-4 text-xs font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400 text-right">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100 dark:divide-zinc-900 text-sm">
                {revisionsList.map((rev) => {
                  const revId = (rev.id || rev._id) as string;
                  const cat = getCategoryDetails(rev.category_id);
                  const isOwner = user?.user_id === rev.created_by;
                  const isLoadingAction = actionLoading === revId;

                  return (
                    <tr
                      key={revId}
                      className="group hover:bg-zinc-50/30 dark:hover:bg-zinc-900/10 transition-colors"
                    >
                      {/* Category */}
                      <td className="p-4">
                        <div className="flex flex-col justify-center">
                          <span className="font-semibold text-zinc-900 dark:text-white leading-tight">
                            {cat.name}
                          </span>
                          <span className="text-[10px] font-mono text-zinc-400 dark:text-zinc-500 uppercase tracking-widest mt-0.5">
                            {cat.code}
                          </span>
                        </div>
                      </td>

                      {/* Proposed Change */}
                      <td className="p-4">
                        <div className="flex items-center gap-2">
                          <div className="flex flex-col">
                            <span className="text-xs text-zinc-400 font-mono">
                              ₹{formatCurrency(rev.old_budget)}
                            </span>
                            <div className="flex items-center gap-1 mt-0.5">
                              <ArrowRight className="w-3 h-3 text-zinc-400" />
                              <span className="font-mono font-bold text-zinc-800 dark:text-zinc-200">
                                ₹{formatCurrency(rev.new_budget)}
                              </span>
                            </div>
                          </div>
                          <div className="ml-2">
                            {rev.revision_amount > 0 ? (
                              <span className="flex items-center gap-0.5 text-xs font-bold text-red-600 dark:text-red-400 bg-red-500/5 px-2 py-0.5 rounded-lg border border-red-500/10 font-mono">
                                <TrendingUp size={12} />
                                +₹{formatCurrency(rev.revision_amount)}
                              </span>
                            ) : (
                              <span className="flex items-center gap-0.5 text-xs font-bold text-emerald-600 dark:text-emerald-400 bg-emerald-500/5 px-2 py-0.5 rounded-lg border border-emerald-500/10 font-mono">
                                <TrendingDown size={12} />
                                -₹{formatCurrency(Math.abs(rev.revision_amount))}
                              </span>
                            )}
                          </div>
                        </div>
                      </td>

                      {/* Reason / Details */}
                      <td className="p-4">
                        <div className="space-y-1">
                          <p className="text-zinc-700 dark:text-zinc-300 text-xs line-clamp-2">
                            {rev.reason}
                          </p>
                          {rev.status === "REJECTED" && (rev as any).approved_by && (
                            <div className="mt-1.5 p-2 bg-rose-500/5 border border-rose-500/15 rounded-lg text-[11px] text-rose-600 dark:text-rose-400 animate-in fade-in duration-200">
                              <span className="font-semibold uppercase tracking-wider block text-[9px] mb-0.5">
                                Rejection Comment:
                              </span>
                              {(rev as any).comment || "No reason specified."}
                            </div>
                          )}
                        </div>
                      </td>

                      {/* Supporting Doc */}
                      <td className="p-4">
                        {rev.document_url && rev.document_name ? (
                          <button
                            onClick={() => handleDownload(revId, rev.document_name!)}
                            className="flex items-center gap-1.5 text-xs text-orange-600 dark:text-orange-500 hover:text-orange-700 dark:hover:text-orange-400 hover:underline font-medium focus:outline-none transition-colors"
                          >
                            <FileText size={14} className="shrink-0" />
                            <span className="truncate max-w-[120px]" title={rev.document_name}>
                              {rev.document_name}
                            </span>
                          </button>
                        ) : (
                          <span className="text-xs text-zinc-400 italic">No Document</span>
                        )}
                      </td>

                      {/* Requested By */}
                      <td className="p-4">
                        <div className="flex flex-col gap-0.5 text-xs text-zinc-500">
                          <span className="flex items-center gap-1 font-medium text-zinc-700 dark:text-zinc-300">
                            <User size={12} />
                            {rev.created_by}
                          </span>
                          <span className="flex items-center gap-1 text-[10px] text-zinc-400">
                            <Calendar size={10} />
                            {new Date(rev.created_at).toLocaleDateString("en-IN", {
                              day: "numeric",
                              month: "short",
                              year: "numeric",
                            })}
                          </span>
                        </div>
                      </td>

                      {/* Status */}
                      <td className="p-4 text-center">{getStatusBadge(rev.status)}</td>

                      {/* Actions */}
                      <td className="p-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          {isLoadingAction && (
                            <Loader2 className="w-4 h-4 text-orange-500 animate-spin shrink-0" />
                          )}

                          {rev.status === "DRAFT" && (isOwner || showAdminActions) && (
                            <button
                              disabled={isLoadingAction}
                              onClick={() => handleSubmit(revId)}
                              className="flex items-center gap-1 px-3 py-1.5 bg-orange-600 dark:bg-orange-500 hover:bg-orange-700 dark:hover:bg-orange-600 text-white rounded-xl text-xs font-bold transition-all border border-transparent shadow-sm disabled:opacity-50"
                            >
                              <Send size={12} /> Submit
                            </button>
                          )}

                          {rev.status === "SUBMITTED" && showAdminActions && (
                            <>
                              <button
                                disabled={isLoadingAction}
                                onClick={() => handleApprove(revId)}
                                className="flex items-center justify-center p-1.5 bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 dark:text-emerald-500 hover:bg-emerald-500/20 rounded-lg transition-all"
                                title="Approve Revision"
                              >
                                <Check size={14} />
                              </button>
                              <button
                                disabled={isLoadingAction}
                                onClick={() => handleOpenRejectModal(rev)}
                                className="flex items-center justify-center p-1.5 bg-rose-500/10 border border-rose-500/20 text-rose-600 dark:text-rose-500 hover:bg-rose-500/20 rounded-lg transition-all"
                                title="Reject Revision"
                              >
                                <X size={14} />
                              </button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Reject Reason Modal */}
      <Dialog open={!!rejectingRevision} onOpenChange={(open) => !open && setRejectingRevision(null)}>
        <DialogContent className="bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-900 text-zinc-900 dark:text-white max-w-md rounded-2xl p-6 shadow-2xl">
          <DialogHeader className="mb-4">
            <DialogTitle className="text-lg font-bold flex items-center gap-2 text-rose-600">
              <AlertCircle size={20} />
              Reject Variation Order
            </DialogTitle>
            <DialogDescription className="text-zinc-500 dark:text-zinc-400 text-xs mt-1">
              Provide a mandatory rejection reason so the requestor understands why it was not approved.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-zinc-400 mb-1 uppercase tracking-wider">
                Rejection Reason (min 5 chars)
              </label>
              <textarea
                value={rejectionComment}
                onChange={(e) => setRejectionComment(e.target.value)}
                placeholder="Specify details, budget discrepancies, or clarifications required..."
                className="w-full bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl px-4 py-2.5 text-zinc-900 dark:text-white text-sm focus:outline-none focus:border-rose-500/50 transition-colors placeholder:text-zinc-400 dark:placeholder:text-zinc-600 h-28 resize-none"
              />
            </div>
          </div>

          <DialogFooter className="mt-6 flex gap-2 justify-end">
            <button
              onClick={() => setRejectingRevision(null)}
              className="px-4 py-2 bg-zinc-100 dark:bg-zinc-900 hover:bg-zinc-200 dark:hover:bg-zinc-800 text-zinc-700 dark:text-zinc-300 rounded-xl text-xs font-bold transition-all border border-zinc-200 dark:border-zinc-800"
            >
              Cancel
            </button>
            <button
              onClick={handleReject}
              disabled={rejectionComment.trim().length < 5}
              className="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white rounded-xl text-xs font-bold transition-all disabled:opacity-50"
            >
              Confirm Reject
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
