"use client";

import React, { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import api from "@/lib/api";
import {
  Check,
  X,
  ArrowLeft,
  Image as ImageIcon,
  MapPin,
  Cloudy,
  Users,
  Calendar,
  ArrowRight,
  ShieldCheck,
  MessageSquare,
  FileText,
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";

interface DPRDetail {
  _id: string;
  project_id: string;
  status: string;
  date: string;
  supervisor_id?: string;
  supervisor_name?: string;
  approved_by?: string;
  approved_by_name?: string;
  rejected_by?: string;
  rejected_by_name?: string;
  approved_at?: string;
  rejected_at?: string;
  rejection_reason?: string;
  manpower_count?: number;
  weather_conditions?: string;
  photos?: string[];
  notes?: string;
  progress_notes?: string;
  activities_completed?: string[];
  materials_used?: Record<string, unknown>[];
  equipment_deployed?: Record<string, unknown>[];
  issues_challenges?: string;
  issues_encountered?: string;
  [key: string]: unknown;
}

export default function DPRDetailPage() {
  const { id } = useParams();
  const router = useRouter();
  const { toast } = useToast();
  const [dpr, setDpr] = useState<DPRDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [rejectDialogOpen, setRejectDialogOpen] = useState(false);
  const [rejectionReason, setRejectionReason] = useState("");
  const [selectedImage, setSelectedImage] = useState<string | null>(null);

  useEffect(() => {
    if (id) fetchDPRDetail();
  }, [id]);

  const fetchDPRDetail = async () => {
    try {
      setLoading(true);
      const response = await api.get(`/api/dprs/${id}`);
      setDpr(response.data);
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to load DPR detail",
        variant: "destructive",
      });
      router.push("/admin/site-operations");
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async () => {
    try {
      await api.patch(`/api/dprs/${id}/approve`);
      toast({ title: "Success", description: "DPR Approved" });
      fetchDPRDetail();
    } catch (error) {
      toast({
        title: "Error",
        description: "Approval failed",
        variant: "destructive",
      });
    }
  };

  const handleReject = async () => {
    if (!rejectionReason) {
      toast({
        title: "Error",
        description: "Please provide a reason for rejection",
        variant: "destructive",
      });
      return;
    }
    try {
      await api.patch(
        `/api/dprs/${id}/reject?reason=${encodeURIComponent(rejectionReason)}`,
      );
      toast({ title: "Success", description: "DPR Rejected" });
      setRejectDialogOpen(false);
      fetchDPRDetail();
    } catch (error) {
      toast({
        title: "Error",
        description: "Rejection failed",
        variant: "destructive",
      });
    }
  };

  const formatDate = (dateStr: string) => {
    if (!dateStr) return "N/A";
    return new Intl.DateTimeFormat("en-GB", {
      weekday: "long",
      day: "2-digit",
      month: "long",
      year: "numeric",
    }).format(new Date(dateStr));
  };

  const formatShortDate = (dateStr: string) => {
    if (!dateStr) return "N/A";
    return new Intl.DateTimeFormat("en-GB", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(dateStr));
  };

  if (loading)
    return (
      <div className="flex items-center justify-center p-24">
        <div className="w-8 h-8 border-4 border-orange-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );

  if (!dpr)
    return <div className="p-8 text-center text-slate-500">DPR not found</div>;

  const status = (dpr.status || "DRAFT").toUpperCase();
  const canAction = status !== "APPROVED" && status !== "REJECTED";

  return (
    <div className="p-6 space-y-8 animate-in fade-in duration-500 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-start justify-between gap-6">
        <div className="flex items-start gap-4">
          <button
            onClick={() => router.back()}
            className="mt-1 p-2 rounded-xl bg-slate-900 border border-slate-800 text-slate-400 hover:text-white hover:bg-slate-800 transition-all"
          >
            <ArrowLeft size={18} />
          </button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-3xl font-bold text-white tracking-tight">
                Daily Progress Report
              </h1>
              <span
                className={`px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-widest border ${
                  status === "APPROVED"
                    ? "bg-emerald-500/10 text-emerald-500 border-emerald-500/20"
                    : status === "REJECTED"
                      ? "bg-rose-500/10 text-rose-500 border-rose-500/20"
                      : "bg-amber-500/10 text-amber-500 border-amber-500/20"
                }`}
              >
                {status.replace(/_/g, " ")}
              </span>
            </div>
            <div className="flex items-center gap-4 mt-2 text-slate-500 text-sm font-medium">
              <span className="flex items-center gap-1.5">
                <Calendar size={14} /> {formatDate(dpr.date)}
              </span>
              <span className="w-1 h-1 rounded-full bg-slate-700" />
              <span className="flex items-center gap-1.5 text-orange-500">
                <ShieldCheck size={14} /> ID: {dpr._id?.slice(-8).toUpperCase()}
              </span>
            </div>
          </div>
        </div>

        {canAction && (
          <div className="flex items-center gap-3">
            <button
              onClick={() => setRejectDialogOpen(true)}
              className="admin-only px-5 py-2.5 rounded-xl border border-rose-500/30 text-rose-500 text-sm font-bold hover:bg-rose-500/5 transition-all flex items-center gap-2"
            >
              <X size={16} /> Reject Report
            </button>
            <button
              onClick={handleApprove}
              className="admin-only px-6 py-2.5 rounded-xl bg-emerald-600 text-white text-sm font-bold hover:bg-emerald-500 transition-all shadow-lg shadow-emerald-950/20 flex items-center gap-2"
            >
              <Check size={16} /> Approve DPR
            </button>
          </div>
        )}
      </div>

      {/* Approval Metadata Badge */}
      {(status === "APPROVED" || status === "REJECTED") && (
        <div
          className={`p-4 rounded-2xl border flex flex-col sm:flex-row sm:items-center justify-between gap-4 ${
            status === "APPROVED"
              ? "bg-emerald-500/5 border-emerald-500/20"
              : "bg-rose-500/5 border-rose-500/20"
          }`}
        >
          <div className="flex items-center gap-3">
            <div
              className={`p-2 rounded-lg ${status === "APPROVED" ? "bg-emerald-500/10 text-emerald-500" : "bg-rose-500/10 text-rose-500"}`}
            >
              {status === "APPROVED" ? <Check size={20} /> : <X size={20} />}
            </div>
            <div>
              <p className="text-white text-sm font-bold">
                {status === "APPROVED" ? "Approved" : "Rejected"} by{" "}
                {dpr.approved_by_name ||
                  dpr.rejected_by_name ||
                  dpr.approved_by ||
                  dpr.rejected_by ||
                  "Admin"}
              </p>
              <p className="text-slate-500 text-xs mt-0.5 uppercase tracking-wider font-semibold">
                on{" "}
                {dpr.approved_at
                  ? formatShortDate(dpr.approved_at)
                  : dpr.rejected_at
                    ? formatShortDate(dpr.rejected_at)
                    : "Unknown Date"}
              </p>
            </div>
          </div>
          {dpr.rejection_reason && (
            <div className="flex-1 max-w-md bg-slate-950/50 p-3 rounded-xl border border-rose-500/10 text-rose-500/80 text-xs italic">
              "{dpr.rejection_reason}"
            </div>
          )}
        </div>
      )}

      {/* Main Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
        <div className="bg-slate-900/50 border border-slate-800 p-6 rounded-3xl space-y-2">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-[10px] font-bold uppercase tracking-widest">
              Site Personnel
            </span>
            <Users size={16} className="text-orange-500" />
          </div>
          <div className="text-3xl font-bold text-white">
            {dpr.manpower_count || 0}
          </div>
          <p className="text-xs text-slate-600 font-medium">Workers reported</p>
        </div>
        <div className="bg-slate-900/50 border border-slate-800 p-6 rounded-3xl space-y-2">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-[10px] font-bold uppercase tracking-widest">
              Weather
            </span>
            <Cloudy size={16} className="text-blue-500" />
          </div>
          <div className="text-xl font-bold text-white">
            {dpr.weather_conditions || "Clear"}
          </div>
          <p className="text-xs text-slate-600 font-medium">
            Current conditions
          </p>
        </div>
        <div className="bg-slate-900/50 border border-slate-800 p-6 rounded-3xl space-y-2">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-[10px] font-bold uppercase tracking-widest">
              Documentation
            </span>
            <ImageIcon size={16} className="text-emerald-500" />
          </div>
          <div className="text-3xl font-bold text-white">
            {dpr.photos?.length || 0}
          </div>
          <p className="text-xs text-slate-600 font-medium">
            Verified site images
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Content Section */}
        <div className="space-y-8">
          {/* Notes */}
          <div className="bg-slate-900/50 border border-slate-800 rounded-[2rem] overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-800 bg-slate-950/30 flex items-center gap-2">
              <FileText size={16} className="text-orange-500" />
              <h3 className="text-sm font-bold text-white uppercase tracking-widest">
                Progress Notes
              </h3>
            </div>
            <div className="p-6 text-sm text-slate-300 leading-relaxed min-h-[150px] whitespace-pre-wrap font-medium">
              {dpr.progress_notes ||
                "No general notes provided for this report."}
            </div>
          </div>

          {/* Activities */}
          <div className="bg-slate-900/50 border border-slate-800 rounded-[2rem] overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-800 bg-slate-950/30 flex items-center gap-2">
              <Check size={16} className="text-emerald-500" />
              <h3 className="text-sm font-bold text-white uppercase tracking-widest">
                Activities Completed
              </h3>
            </div>
            <div className="p-6">
              <div className="space-y-3">
                {dpr.activities_completed &&
                dpr.activities_completed.length > 0 ? (
                  dpr.activities_completed.map(
                    (activity: string, i: number) => (
                      <div
                        key={i}
                        className="flex items-start gap-3 p-3 rounded-2xl bg-slate-950/50 border border-slate-800/50"
                      >
                        <div className="mt-0.5 p-1 rounded-full bg-emerald-500/20 text-emerald-500">
                          <Check size={10} />
                        </div>
                        <span className="text-sm text-slate-300 font-medium">
                          {activity}
                        </span>
                      </div>
                    ),
                  )
                ) : (
                  <p className="text-slate-600 text-sm italic py-4 text-center">
                    No activities listed
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* Issues */}
          {dpr.issues_encountered && (
            <div className="bg-rose-500/5 border border-rose-500/20 rounded-[2rem] overflow-hidden">
              <div className="px-6 py-4 border-b border-rose-500/20 bg-rose-500/5 flex items-center gap-2">
                <X size={16} className="text-rose-500" />
                <h3 className="text-sm font-bold text-rose-500 uppercase tracking-widest">
                  Issues Encountered
                </h3>
              </div>
              <div className="p-6 text-sm text-slate-300 italic leading-relaxed">
                "{dpr.issues_encountered}"
              </div>
            </div>
          )}
        </div>

        {/* Media Section */}
        <div className="space-y-4">
          <div className="flex items-center justify-between px-2">
            <h3 className="text-sm font-bold text-white uppercase tracking-widest">
              Site Photo Log
            </h3>
            <span className="text-[10px] bg-slate-800 text-slate-400 px-2 py-0.5 rounded font-black uppercase">
              {dpr.photos?.length || 0} Images
            </span>
          </div>
          <div className="grid grid-cols-2 gap-4">
            {dpr.photos?.map((photo, i) => (
              <div
                key={i}
                className="group relative aspect-[9/16] rounded-3xl overflow-hidden border border-slate-800 bg-slate-950 cursor-zoom-in hover:border-orange-500/50 transition-all shadow-xl"
                onClick={() => setSelectedImage(photo)}
              >
                <img
                  src={photo}
                  alt={`Site view ${i + 1}`}
                  className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-110"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex items-end p-4">
                  <span className="text-[10px] text-white font-bold uppercase tracking-[0.2em]">
                    View Portrait Detail
                  </span>
                </div>
              </div>
            ))}
            {(!dpr.photos || dpr.photos.length === 0) && (
              <div className="col-span-2 py-24 flex flex-col items-center justify-center text-slate-700 bg-slate-900/30 border-2 border-dashed border-slate-800 rounded-[2rem]">
                <ImageIcon className="h-12 w-12 mb-4 opacity-10" />
                <p className="text-sm font-bold uppercase tracking-widest opacity-40">
                  No media available
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Lightbox */}
      {selectedImage && (
        <div
          className="fixed inset-0 z-[100] flex items-center justify-center bg-black/95 p-4 animate-in fade-in duration-300"
          onClick={() => setSelectedImage(null)}
        >
          <button className="absolute top-6 right-6 p-3 rounded-full bg-slate-900/50 text-white hover:text-orange-500 transition-colors">
            <X size={32} />
          </button>
          <div
            className="relative max-h-[90vh] aspect-[9/16] bg-slate-900 rounded-3xl overflow-hidden border border-slate-800 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <img
              src={selectedImage}
              alt="Large Site View"
              className="h-full w-full object-contain"
            />
            <div className="absolute bottom-0 left-0 right-0 p-6 bg-gradient-to-t from-black to-transparent text-center">
              <p className="text-white text-sm font-bold tracking-widest uppercase">
                Verified Site Documentation
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Reject Dialog */}
      {rejectDialogOpen && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4">
          <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-3xl shadow-2xl overflow-hidden">
            <div className="p-6 border-b border-slate-800 flex justify-between items-center">
              <h3 className="text-lg font-bold text-white">Reject Report</h3>
              <button
                onClick={() => setRejectDialogOpen(false)}
                className="text-slate-500 hover:text-white"
              >
                <X size={20} />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <p className="text-sm text-slate-400">
                Please provide a constructive reason for rejecting this report.
                This will be shared with the supervisor.
              </p>
              <textarea
                className="w-full h-32 bg-slate-950 border border-slate-800 rounded-2xl p-4 text-sm text-white focus:outline-none focus:border-rose-500/50 transition-colors resize-none"
                placeholder="e.g. Activity documentation is insufficient, missing evening photos..."
                value={rejectionReason}
                onChange={(e) => setRejectionReason(e.target.value)}
              />
            </div>
            <div className="p-6 bg-slate-950/50 border-t border-slate-800 flex gap-3">
              <button
                onClick={() => setRejectDialogOpen(false)}
                className="flex-1 px-4 py-2.5 rounded-xl border border-slate-800 text-slate-400 text-sm font-bold hover:text-white transition-all"
              >
                Cancel
              </button>
              <button
                onClick={handleReject}
                className="flex-1 px-4 py-2.5 rounded-xl bg-rose-600 text-white text-sm font-bold hover:bg-rose-500 transition-all shadow-lg shadow-rose-950/20"
              >
                Confirm Rejection
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
