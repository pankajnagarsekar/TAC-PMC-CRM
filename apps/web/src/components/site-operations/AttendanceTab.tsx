"use client";

import React, { useState, useEffect, useMemo } from "react";
import FinancialGrid from "@/components/ui/FinancialGrid";
import { useProjectStore } from "@/store/projectStore";
import api from "@/lib/api";
import {
  ExternalLink,
  Calendar,
  MapPin,
  Search,
  X,
  CheckCircle2,
} from "lucide-react";
import { ColDef } from "ag-grid-community";
import { useToast } from "@/hooks/use-toast";

export default function AttendanceTab() {
  const { activeProject } = useProjectStore();
  const { toast } = useToast();
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [selectedImage, setSelectedImage] = useState<string | null>(null);

  useEffect(() => {
    if (activeProject?.project_id) {
      fetchAttendance();
    }
  }, [activeProject, startDate, endDate]);

  const fetchAttendance = async () => {
    if (!activeProject?.project_id) return;
    try {
      setLoading(true);
      const params = new URLSearchParams();
      if (startDate) params.append("start_date", startDate);
      if (endDate) params.append("end_date", endDate);

      const response = await api.get(
        `/api/projects/${activeProject.project_id}/attendance?${params.toString()}`,
      );
      setLogs(response.data);
    } catch (error) {
      console.error("Error fetching attendance:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleVerify = async (logId: string) => {
    try {
      await api.patch(`/api/attendance/${logId}/verify`);
      toast({ title: "Success", description: "Attendance verified" });
      fetchAttendance();
    } catch (error) {
      toast({
        title: "Error",
        description: "Verification failed",
        variant: "destructive",
      });
    }
  };

  const formatDate = (dateStr: string) => {
    if (!dateStr) return "N/A";
    return new Intl.DateTimeFormat("en-GB", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    }).format(new Date(dateStr));
  };

  const formatTime = (dateStr: string) => {
    if (!dateStr) return "--:--";
    return new Intl.DateTimeFormat("en-GB", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    }).format(new Date(dateStr));
  };

  const columnDefs: ColDef[] = useMemo(
    () => [
      {
        headerName: "Worker Name",
        field: "user_name",
        flex: 1.2,
        cellRenderer: (params: any) => (
          <span className="font-semibold text-white">
            {params.value || "Field Staff"}
          </span>
        ),
      },
      {
        headerName: "Date",
        field: "check_in_time",
        flex: 1,
        cellRenderer: (params: any) => (
          <span className="text-slate-400">{formatDate(params.value)}</span>
        ),
      },
      {
        headerName: "Check-in Time",
        field: "check_in_time",
        flex: 1,
        cellRenderer: (params: any) => (
          <span className="text-slate-500 font-mono text-xs">
            {formatTime(params.value)}
          </span>
        ),
      },
      {
        headerName: "Selfie",
        field: "selfie",
        width: 80,
        cellRenderer: (params: any) =>
          params.value ? (
            <div className="flex items-center justify-center h-full">
              <img
                src={params.value}
                alt="Selfie"
                className="h-8 w-8 rounded-full border border-slate-700 cursor-pointer hover:scale-110 transition-transform object-cover"
                onClick={() => setSelectedImage(params.value)}
              />
            </div>
          ) : (
            <span className="text-slate-700 text-[10px]">No Photo</span>
          ),
      },
      {
        headerName: "GPS",
        field: "location",
        flex: 0.8,
        cellRenderer: (params: any) => {
          const loc = params.value;
          const lat = loc?.latitude || loc?.lat;
          const lng = loc?.longitude || loc?.lng;
          return (
            <div className="flex items-center space-x-2">
              {lat ? (
                <a
                  href={`https://www.google.com/maps?q=${lat},${lng}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center text-orange-500 hover:text-orange-400 text-xs font-medium"
                >
                  Maps <ExternalLink className="ml-1 h-3 w-3" />
                </a>
              ) : (
                <span className="text-slate-700 text-xs">-</span>
              )}
            </div>
          );
        },
      },
      {
        headerName: "Verified",
        field: "verified_by_admin",
        width: 100,
        cellRenderer: (params: any) => (
          <div className="flex justify-center items-center h-full">
            {params.value ? (
              <div className="flex items-center gap-1 text-emerald-500 text-[10px] font-bold uppercase">
                <CheckCircle2 size={14} /> Verified
              </div>
            ) : (
              <button
                onClick={() => handleVerify(params.data._id)}
                className="text-[10px] bg-slate-800 hover:bg-slate-700 text-slate-300 px-2 py-1 rounded-md border border-slate-700 transition-colors uppercase font-bold"
              >
                Verify Now
              </button>
            )}
          </div>
        ),
      },
    ],
    [],
  );

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-col md:flex-row gap-4 bg-slate-900/50 p-4 rounded-2xl border border-slate-800/50">
        <div className="flex items-center gap-2 bg-slate-950 border border-slate-800 rounded-xl px-3 py-1.5 flex-1 max-w-sm">
          <Calendar size={14} className="text-slate-500" />
          <input
            type="date"
            className="bg-transparent text-sm text-slate-300 outline-none w-full"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
          />
          <span className="text-slate-600">-</span>
          <input
            type="date"
            className="bg-transparent text-sm text-slate-300 outline-none w-full"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
          />
        </div>
        <p className="text-xs text-slate-500 flex items-center italic">
          <MapPin size={12} className="mr-1" /> All data is GPS verified from
          mobile app.
        </p>
      </div>

      <div className="h-[500px]">
        <FinancialGrid<any>
          columnDefs={columnDefs}
          rowData={logs}
          loading={loading}
        />
      </div>

      {/* Lightbox */}
      {selectedImage && (
        <div
          className="fixed inset-0 z-[100] flex items-center justify-center bg-black/90 p-4 animate-in fade-in duration-200"
          onClick={() => setSelectedImage(null)}
        >
          <button className="absolute top-4 right-4 text-white hover:text-orange-500 transition-colors">
            <X size={32} />
          </button>
          <div
            className="relative max-w-2xl w-full bg-slate-900 rounded-2xl overflow-hidden border border-slate-800 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <img
              src={selectedImage}
              alt="Large View"
              className="w-full h-auto max-h-[80vh] object-contain"
            />
            <div className="p-4 bg-slate-950 border-t border-slate-800 text-center">
              <p className="text-slate-400 text-sm font-medium">
                Site Personnel Verification Selfie
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
