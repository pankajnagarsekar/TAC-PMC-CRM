"use client";

import React, { useState, useEffect, useMemo, useCallback } from "react";
import FinancialGrid from "@/components/ui/FinancialGrid";
import { useProjectStore } from "@/store/projectStore";
import api from "@/lib/api";
import {
  ExternalLink,
  Calendar,
  MapPin,
  X,
  CheckCircle2,
} from "lucide-react";
import { ColDef, ICellRendererParams } from "ag-grid-community";
import Image from "next/image";
import { useToast } from "@/hooks/use-toast";

interface AttendanceLog {
  _id: string;
  user_name?: string;
  check_in_time: string;
  selfie?: string;
  location?: { latitude: number; longitude: number; lat?: number; lng?: number };
  verified_by_admin: boolean;
}

export default function AttendanceTab() {
  const { activeProject } = useProjectStore();
  const { toast } = useToast();
  const [logs, setLogs] = useState<AttendanceLog[]>([]);
  const [loading, setLoading] = useState(false);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [selectedImage, setSelectedImage] = useState<string | null>(null);

  const fetchAttendance = useCallback(async () => {
    if (!activeProject?.project_id) return;
    try {
      setLoading(true);
      const params = new URLSearchParams();
      if (startDate) params.append("start_date", startDate);
      if (endDate) params.append("end_date", endDate);

      const response = await api.get(
        `/api/v1/projects/${activeProject.project_id}/attendance?${params.toString()}`,
      );
      setLogs(response.data);
    } catch (error) {
      console.error("Error fetching attendance:", error);
      setLogs([]);
    } finally {
      setLoading(false);
    }
  }, [activeProject, startDate, endDate]);

  useEffect(() => {
    if (activeProject?.project_id) {
      fetchAttendance();
    }
  }, [activeProject, fetchAttendance]);

  const handleVerify = useCallback(async (logId: string) => {
    try {
      await api.patch(`/api/v1/attendance/${logId}/verify`);
      toast({ title: "Success", description: "Attendance verified" });
      fetchAttendance();
    } catch {
      toast({
        title: "Error",
        description: "Verification failed",
        variant: "destructive",
      });
    }
  }, [fetchAttendance, toast]);

  const formatDate = useCallback((dateStr: string) => {
    if (!dateStr) return "N/A";
    return new Intl.DateTimeFormat("en-GB", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    }).format(new Date(dateStr));
  }, []);

  const formatTime = useCallback((dateStr: string) => {
    if (!dateStr) return "--:--";
    return new Intl.DateTimeFormat("en-GB", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    }).format(new Date(dateStr));
  }, []);

  const columnDefs: ColDef[] = useMemo(
    () => [
      {
        headerName: "Worker Name",
        field: "user_name",
        flex: 1.2,
        cellRenderer: (params: ICellRendererParams<AttendanceLog>) => (
          <span className="font-semibold text-zinc-900 dark:text-white">
            {params.value || "Field Staff"}
          </span>
        ),
      },
      {
        headerName: "Date",
        field: "check_in_time",
        flex: 1,
        cellRenderer: (params: ICellRendererParams<AttendanceLog>) => (
          <span className="text-zinc-500 dark:text-slate-400">{formatDate(params.value)}</span>
        ),
      },
      {
        headerName: "Check-in Time",
        field: "check_in_time",
        flex: 1,
        cellRenderer: (params: ICellRendererParams<AttendanceLog>) => (
          <span className="text-zinc-400 dark:text-slate-500 font-mono text-xs">
            {formatTime(params.value)}
          </span>
        ),
      },
      {
        headerName: "Selfie",
        field: "selfie",
        width: 80,
        cellRenderer: (params: ICellRendererParams<AttendanceLog>) =>
          params.value ? (
            <div className="flex items-center justify-center h-full">
              <Image
                src={params.value}
                alt="Selfie"
                width={32}
                height={32}
                unoptimized
                className="h-8 w-8 rounded-full border border-zinc-200 dark:border-slate-700 cursor-pointer hover:scale-110 transition-transform object-cover"
                onClick={() => setSelectedImage(params.value)}
              />
            </div>
          ) : (
            <span className="text-zinc-300 dark:text-slate-700 text-[10px]">No Photo</span>
          ),
      },
      {
        headerName: "GPS",
        field: "location",
        flex: 0.8,
        cellRenderer: (params: ICellRendererParams<AttendanceLog>) => {
          const loc = params.value as AttendanceLog["location"];
          const lat = loc?.latitude || loc?.lat;
          const lng = loc?.longitude || loc?.lng;
          return (
            <div className="flex items-center space-x-2">
              {lat ? (
                <a
                  href={`https://www.google.com/maps?q=${lat},${lng}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center text-orange-600 dark:text-orange-500 hover:text-orange-500 dark:hover:text-orange-400 text-xs font-medium"
                >
                  Maps <ExternalLink className="ml-1 h-3 w-3" />
                </a>
              ) : (
                <span className="text-zinc-300 dark:text-slate-700 text-xs">-</span>
              )}
            </div>
          );
        },
      },
      {
        headerName: "Verified",
        field: "verified_by_admin",
        width: 100,
        cellRenderer: (params: ICellRendererParams<AttendanceLog>) => (
          <div className="flex justify-center items-center h-full">
            {params.value ? (
              <div className="flex items-center gap-1 text-emerald-600 dark:text-emerald-500 text-[10px] font-bold uppercase">
                <CheckCircle2 size={14} /> Verified
              </div>
            ) : (
              <button
                onClick={() => params.data?._id && handleVerify(params.data._id)}
                className="text-[10px] bg-zinc-100 dark:bg-slate-800 hover:bg-zinc-200 dark:hover:bg-slate-700 text-zinc-600 dark:text-slate-300 px-2 py-1 rounded-md border border-zinc-200 dark:border-slate-700 transition-colors uppercase font-bold"
              >
                Verify Now
              </button>
            )}
          </div>
        ),
      },
    ],
    [formatDate, formatTime, handleVerify],
  );

  const handleExport = async (format: "excel" | "pdf") => {
    if (!activeProject?.project_id) return;
    try {
      const params = new URLSearchParams();
      if (startDate) params.append("start_date", startDate);
      if (endDate) params.append("end_date", endDate);
      params.append("project_id", activeProject.project_id);

      const endpoint = format === "excel" ? "export" : "export-pdf";
      const response = await api.get(`/api/v1/attendance/${endpoint}?${params.toString()}`, {
        responseType: "blob",
      });

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `Attendance-${activeProject.project_id}.${format === "excel" ? "xlsx" : "pdf"}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      toast({ title: "Success", description: "Export downloaded" });
    } catch {
      toast({ title: "Error", description: "Export failed", variant: "destructive" });
    }
  };

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-col md:flex-row gap-4 bg-zinc-50 dark:bg-slate-900/50 p-4 rounded-2xl border border-zinc-200 dark:border-slate-800/50 transition-colors">
        <div className="flex items-center gap-2 bg-white dark:bg-slate-950 border border-zinc-200 dark:border-slate-800 rounded-xl px-3 py-1.5 flex-1 max-w-sm transition-colors">
          <Calendar size={14} className="text-zinc-400 dark:text-slate-500" />
          <input
            type="date"
            className="bg-transparent text-sm text-zinc-600 dark:text-slate-300 outline-none w-full cursor-pointer"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
          />
          <span className="text-zinc-300 dark:text-slate-600">-</span>
          <input
            type="date"
            className="bg-transparent text-sm text-zinc-600 dark:text-slate-300 outline-none w-full cursor-pointer"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
          />
        </div>

        <div className="flex gap-2">
          <button
            onClick={() => handleExport("excel")}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 dark:text-emerald-400 rounded-xl text-xs font-bold hover:bg-emerald-500/20 transition-colors"
          >
            Excel
          </button>
          <button
            onClick={() => handleExport("pdf")}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-rose-500/10 border border-rose-500/20 text-rose-600 dark:text-rose-400 rounded-xl text-xs font-bold hover:bg-rose-500/20 transition-colors"
          >
            PDF
          </button>
        </div>

        <p className="text-xs text-zinc-500 dark:text-slate-500 flex items-center italic md:ml-auto">
          <MapPin size={12} className="mr-1 text-orange-500" /> All data is GPS verified from mobile app.
        </p>
      </div>

      <div className="h-[500px]">
        <FinancialGrid<AttendanceLog>
          columnDefs={columnDefs}
          rowData={logs}
          loading={loading}
        />
      </div>

      {/* Lightbox */}
      {selectedImage && (
        <div
          className="fixed inset-0 z-[100] flex items-center justify-center bg-black/90 p-4 animate-in fade-in duration-200 border-none"
          onClick={() => setSelectedImage(null)}
        >
          <button className="absolute top-4 right-4 text-white hover:text-orange-500 transition-colors">
            <X size={32} />
          </button>
          <div
            className="relative max-w-2xl w-full bg-white dark:bg-slate-900 rounded-2xl overflow-hidden shadow-2xl border border-zinc-200 dark:border-slate-800"
            onClick={(e) => e.stopPropagation()}
          >
            <Image
              src={selectedImage}
              alt="Large View"
              width={800}
              height={600}
              unoptimized
              className="w-full h-auto max-h-[80vh] object-contain"
            />
            <div className="p-4 bg-zinc-50 dark:bg-slate-950 border-t border-zinc-200 dark:border-slate-800 text-center">
              <p className="text-zinc-500 dark:text-slate-400 text-sm font-medium uppercase tracking-widest text-[10px]">
                Site Personnel Verification Selfie
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
