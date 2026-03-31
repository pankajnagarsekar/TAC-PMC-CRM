"use client";

import React, { useState, useEffect } from "react";
import { Play, FileText, Mic, Clock, ChevronRight } from "lucide-react";
import { useProjectStore } from "@/store/projectStore";
import api from "@/lib/api";
import AudioPlayer from "./AudioPlayer";

interface VoiceLog {
  _id: string;
  project_id: string;
  supervisor_id?: string;
  supervisor_name?: string;
  audio_url?: string;
  transcribed_text?: string;
  duration?: string;
  status?: string;
  created_at: string;
}

export default function VoiceLogsTab() {
  const { activeProject } = useProjectStore();
  const [logs, setLogs] = useState<VoiceLog[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedLog, setSelectedLog] = useState<VoiceLog | null>(null);

  useEffect(() => {
    if (activeProject) {
      fetchVoiceLogs();
    }
  }, [activeProject]);

  const fetchVoiceLogs = async () => {
    if (!activeProject?.project_id) return;
    try {
      setLoading(true);
      const response = await api.get(
        `/api/v1/projects/${activeProject.project_id}/voice-logs`,
      );
      setLogs(response.data);
    } catch (error) {
      console.error("Error fetching voice logs:", error);
      setLogs([]);
    } finally {
      setLoading(false);
    }
  };

  const formatDateTime = (dateStr: string) => {
    if (!dateStr) return "N/A";
    return new Intl.DateTimeFormat("en-GB", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(dateStr));
  };

  const formatFullDate = (dateStr: string) => {
    if (!dateStr) return "N/A";
    return new Intl.DateTimeFormat("en-GB", {
      dateStyle: "full",
      timeStyle: "short",
    }).format(new Date(dateStr));
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 animate-in slide-in-from-bottom-4 duration-500">
      {/* List Panel */}
      <div className="lg:col-span-4 space-y-3 max-h-[650px] overflow-y-auto pr-2 custom-scrollbar">
        {loading ? (
          <div className="flex items-center justify-center p-12">
            <div className="w-6 h-6 border-2 border-orange-500 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : (
          logs.map((log) => (
            <div
              key={log._id}
              className={`group cursor-pointer p-4 rounded-2xl border transition-all relative ${selectedLog?._id === log._id
                ? "bg-orange-500/10 border-orange-500/30 shadow-lg dark:shadow-orange-950/20"
                : "bg-white dark:bg-slate-900/50 border-zinc-200 dark:border-slate-800 hover:border-orange-200 dark:hover:border-slate-700 hover:bg-zinc-50 dark:hover:bg-slate-900/80"
                }`}
              onClick={() => setSelectedLog(log)}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="p-2.5 rounded-xl bg-zinc-100 dark:bg-slate-950 border border-zinc-200 dark:border-slate-800 text-orange-600 dark:text-orange-500 group-hover:scale-110 transition-transform">
                  <Mic size={18} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className={`text-sm font-semibold truncate ${selectedLog?._id === log._id ? "text-orange-600 dark:text-white" : "text-zinc-900 dark:text-white"}`}>
                    {formatDateTime(log.created_at)}
                  </p>
                  <div className="flex items-center gap-3 mt-1">
                    <span className="flex items-center gap-1 text-[9px] text-zinc-500 dark:text-slate-500 font-black uppercase tracking-wider">
                      <Clock size={10} /> {log.duration || "--:--"}
                    </span>
                    <span className="text-[9px] px-1.5 py-0.5 rounded bg-zinc-100 dark:bg-slate-950 text-zinc-500 dark:text-slate-400 border border-zinc-200 dark:border-slate-800 uppercase font-bold">
                      {log.status || "Ready"}
                    </span>
                  </div>
                  <p className="text-[11px] text-zinc-500 dark:text-slate-500 mt-2 line-clamp-2 italic leading-relaxed font-medium">
                    "{log.transcribed_text || "No transcription available..."}"
                  </p>
                </div>
                <ChevronRight
                  size={14}
                  className={`mt-1 transition-transform ${selectedLog?._id === log._id ? "text-orange-600 dark:text-orange-500 translate-x-1" : "text-zinc-300 dark:text-slate-700 group-hover:text-zinc-400 dark:group-hover:text-slate-500"}`}
                />
              </div>
              {selectedLog?._id === log._id && (
                <div className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-8 bg-orange-600 dark:bg-orange-500 rounded-r-full" />
              )}
            </div>
          ))
        )}
        {!loading && logs.length === 0 && (
          <div className="text-center p-12 text-zinc-400 dark:text-slate-500 bg-zinc-50 dark:bg-slate-900/30 border border-dashed border-zinc-200 dark:border-slate-800 rounded-3xl">
            <Mic className="h-8 w-8 mx-auto mb-3 opacity-20" />
            <p className="text-sm font-bold uppercase tracking-widest text-[10px]">No site recordings found</p>
          </div>
        )}
      </div>

      {/* Detail Panel */}
      <div className="lg:col-span-8">
        {selectedLog ? (
          <div className="bg-white dark:bg-slate-900/50 border border-zinc-200 dark:border-slate-800 rounded-3xl p-6 lg:p-8 space-y-8 animate-in fade-in duration-300 shadow-xl dark:shadow-none">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-zinc-100 dark:border-slate-800/50 pb-6">
              <div className="flex items-center gap-4">
                <div className="p-4 rounded-2xl bg-orange-600/10 text-orange-600 dark:text-orange-500 shadow-inner">
                  <Mic size={32} />
                </div>
                <div>
                  <h3 className="text-xl font-bold text-zinc-900 dark:text-white tracking-tight">
                    Supervisor Recording
                  </h3>
                  <p className="text-sm text-zinc-500 dark:text-slate-500 font-medium">
                    {formatFullDate(selectedLog.created_at)}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-4 text-xs font-semibold text-zinc-500 dark:text-slate-400">
                {selectedLog.supervisor_name && (
                  <span className="px-3 py-1 rounded-full bg-orange-600/5 dark:bg-orange-500/10 border border-orange-600/20 dark:border-orange-500/20 text-orange-600 dark:text-orange-400 uppercase tracking-widest text-[9px] font-black">
                    {selectedLog.supervisor_name}
                  </span>
                )}
                <span className="px-3 py-1 rounded-full bg-zinc-100 dark:bg-slate-950 border border-zinc-200 dark:border-slate-800 uppercase tracking-widest text-[9px] font-black">
                  ID: {selectedLog.supervisor_id?.slice(-6) || "N/A"}
                </span>
              </div>
            </div>

            <div className="py-2">
              <AudioPlayer src={selectedLog.audio_url || ""} />
            </div>

            <div className="space-y-4">
              <div className="flex items-center gap-2 text-[10px] font-black text-zinc-400 dark:text-slate-300 uppercase tracking-[0.2em]">
                <FileText className="h-4 w-4 text-orange-600 dark:text-orange-500" />
                <span>AI Automated Transcription</span>
              </div>
              <div className="p-6 rounded-3xl bg-zinc-50 dark:bg-slate-950/80 border border-zinc-100 dark:border-slate-800 text-sm leading-relaxed text-zinc-800 dark:text-slate-300 whitespace-pre-wrap min-h-[250px] shadow-inner font-medium">
                {selectedLog.transcribed_text ? (
                  <span className="relative">
                    <span className="text-orange-600/10 dark:text-orange-500/20 text-4xl font-serif absolute -top-4 -left-2">
                      "
                    </span>
                    {selectedLog.transcribed_text}
                    <span className="text-orange-600/10 dark:text-orange-500/20 text-4xl font-serif absolute -bottom-8 -right-2">
                      "
                    </span>
                  </span>
                ) : (
                  <div className="flex flex-col items-center justify-center py-12 text-zinc-400 dark:text-slate-600">
                    <p className="font-bold uppercase tracking-widest text-[10px]">Transcription not available for this recording.</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center p-24 text-zinc-400 dark:text-slate-600 border-2 border-dashed border-zinc-200 dark:border-slate-800 rounded-[3rem] h-full bg-zinc-50/50 dark:bg-slate-900/10 transition-colors">
            <div className="w-16 h-16 rounded-full bg-zinc-100 dark:bg-slate-900/50 flex items-center justify-center mb-4 text-zinc-300 dark:text-slate-700">
              <Mic size={32} />
            </div>
            <p className="font-black uppercase tracking-[0.1em] text-sm text-zinc-500 dark:text-slate-400">Select a recording</p>
            <p className="text-[10px] uppercase tracking-widest mt-1 opacity-60">
              to view details and transcription
            </p>
          </div>
        )}
      </div>

      <style jsx>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 4px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: transparent;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: var(--scrollbar-thumb, #e2e8f0);
          border-radius: 10px;
        }
        .dark .custom-scrollbar::-webkit-scrollbar-thumb {
          background: #1e293b;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: #cbd5e1;
        }
        .dark .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: #334155;
        }
      `}</style>
    </div>
  );
}
