"use client";

import React, { useState, useEffect, useCallback, use } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  CheckSquare,
  Clock,
  User,
  Calendar,
  Tag,
  Loader2,
  ChevronRight,
  AlertCircle,
  FileText,
  Sparkles,
  RefreshCw,
  MoreVertical,
  CheckCircle,
  Play,
  ClipboardList,
  Eye,
  CheckSquare as DoneIcon,
  XCircle,
  ArrowRight
} from "lucide-react";
import api from "@/lib/api";
import { Task } from "@/types/api";
import { formatDate } from "@tac-pmc/ui";
import { useProjectStore } from "@/store/projectStore";
import TaskChangeLog from "@/components/tasks/TaskChangeLog";
import TaskAISummary from "@/components/tasks/TaskAISummary";
import ConfirmDialog from "@/components/ui/ConfirmDialog";

interface TaskPageProps {
  params: Promise<{ id: string }>;
}

export default function TaskDetailsPage({ params }: TaskPageProps) {
  const { id: taskId } = use(params);
  const router = useRouter();
  const { activeProject } = useProjectStore();

  const [task, setTask] = useState<Task | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isUpdating, setIsUpdating] = useState(false);
  const [showCloseConfirm, setShowCloseConfirm] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchTask = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await api.get<Task>(`/api/v1/tasks/${taskId}`);
      setTask(res.data);
      setError(null);
    } catch (err) {
      console.error("Failed to fetch task", err);
      setError("Task not found or permission denied.");
    } finally {
      setIsLoading(false);
    }
  }, [taskId]);

  useEffect(() => {
    fetchTask();
  }, [fetchTask]);

  const updateStatus = async (newStatus: string) => {
    if (newStatus === "Closed" && !showCloseConfirm) {
      setShowCloseConfirm(true);
      return;
    }

    setIsUpdating(true);
    try {
      const res = await api.patch<Task>(`/api/v1/tasks/${taskId}/status`, { status: newStatus });
      setTask(res.data);
      setShowCloseConfirm(false);
    } catch (err) {
      console.error("Failed to update status", err);
    } finally {
      setIsUpdating(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen bg-black">
        <Loader2 className="animate-spin text-blue-500" size={32} />
      </div>
    );
  }

  if (error || !task) {
    return (
      <div className="flex flex-col items-center justify-center h-screen bg-black p-4">
        <AlertCircle className="text-red-500 mb-4" size={48} />
        <h2 className="text-2xl font-bold text-white mb-2">Error</h2>
        <p className="text-slate-400 mb-6">{error || "Task not found."}</p>
        <button
          onClick={() => router.push("/admin/tasks")}
          className="bg-slate-900 border border-slate-800 text-white px-6 py-2 rounded-lg font-bold hover:bg-slate-800 transition-colors"
        >
          Back to Tasks
        </button>
      </div>
    );
  }

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case "High": return "text-red-400 bg-red-400/10 border-red-400/20";
      case "Medium": return "text-amber-400 bg-amber-400/10 border-amber-400/20";
      default: return "text-slate-400 bg-slate-400/10 border-slate-400/20";
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "Open": return "text-slate-400 bg-slate-400/10 border-slate-400/20";
      case "In Progress": return "text-blue-400 bg-blue-400/10 border-blue-400/20";
      case "Review": return "text-amber-400 bg-amber-400/10 border-amber-400/20";
      case "Completed": return "text-emerald-400 bg-emerald-400/10 border-emerald-400/20";
      case "Closed": return "text-emerald-600 bg-emerald-900/20 border-emerald-900/30";
      default: return "text-slate-400 bg-slate-400/10 border-slate-400/20";
    }
  };

  const renderTransitionButtons = () => {
    const status = task.status;
    const buttons = [];

    if (status === "Open") {
      buttons.push(
        <button key="start" onClick={() => updateStatus("In Progress")} className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg font-bold hover:bg-blue-700 transition-colors">
          <Play size={16} /> Start Working
        </button>
      );
      buttons.push(
        <button key="close" onClick={() => updateStatus("Closed")} className="flex items-center gap-2 bg-slate-800 text-slate-300 px-4 py-2 rounded-lg font-bold hover:bg-slate-700 transition-colors">
          <XCircle size={16} /> Close Task
        </button>
      );
    } else if (status === "In Progress") {
      buttons.push(
        <button key="review" onClick={() => updateStatus("Review")} className="flex items-center gap-2 bg-amber-600 text-white px-4 py-2 rounded-lg font-bold hover:bg-amber-700 transition-colors">
          <ClipboardList size={16} /> Submit for Review
        </button>
      );
      buttons.push(
        <button key="pause" onClick={() => updateStatus("Open")} className="flex items-center gap-2 bg-slate-800 text-slate-300 px-4 py-2 rounded-lg font-bold hover:bg-slate-700 transition-colors">
          <ArrowLeft size={16} /> Move to Open
        </button>
      );
      buttons.push(
        <button key="close" onClick={() => updateStatus("Closed")} className="flex items-center gap-2 bg-slate-800 text-slate-300 px-4 py-2 rounded-lg font-bold hover:bg-slate-700 transition-colors">
          <XCircle size={16} /> Close Task
        </button>
      );
    } else if (status === "Review") {
      buttons.push(
        <button key="approve" onClick={() => updateStatus("Completed")} className="flex items-center gap-2 bg-emerald-600 text-white px-4 py-2 rounded-lg font-bold hover:bg-emerald-700 transition-colors">
          <CheckCircle size={16} /> Approve & Complete
        </button>
      );
      buttons.push(
        <button key="reject" onClick={() => updateStatus("In Progress")} className="flex items-center gap-2 bg-red-600 text-white px-4 py-2 rounded-lg font-bold hover:bg-red-700 transition-colors">
          <ArrowLeft size={16} /> Request Changes
        </button>
      );
    } else if (status === "Completed") {
      buttons.push(
        <button key="close" onClick={() => updateStatus("Closed")} className="flex items-center gap-2 bg-emerald-900 text-emerald-400 border border-emerald-800 px-4 py-2 rounded-lg font-bold hover:bg-emerald-800 transition-colors">
          <DoneIcon size={16} /> Finalize & Close
        </button>
      );
    }

    return buttons;
  };

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500 bg-black min-h-screen p-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-slate-800 pb-6">
        <div className="flex items-center gap-4">
          <button
            onClick={() => router.back()}
            className="w-10 h-10 rounded-full bg-slate-900 border border-slate-800 flex items-center justify-center text-slate-400 hover:text-white hover:border-slate-700 transition-all"
          >
            <ArrowLeft size={20} />
          </button>
          <div>
            <div className="flex items-center gap-3 text-xs font-bold text-slate-500 uppercase tracking-widest mb-1">
              <span>Task Detail</span>
              <ChevronRight size={12} />
              <span className="text-blue-500">#{taskId.substring(0, 8)}</span>
            </div>
            <h1 className="text-3xl font-black text-white tracking-tight">
              {task.task_description}
            </h1>
          </div>
        </div>

        <div className="flex items-center gap-3 w-full sm:w-auto">
          {isUpdating ? (
            <div className="px-4 py-2 flex items-center gap-2 text-slate-400 text-sm">
              <Loader2 className="animate-spin" size={16} /> Updating...
            </div>
          ) : (
            renderTransitionButtons()
          )}
          <button className="w-10 h-10 rounded-lg bg-slate-900 border border-slate-800 flex items-center justify-center text-slate-400 hover:text-white transition-colors">
            <MoreVertical size={20} />
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Info */}
        <div className="lg:col-span-2 space-y-6">
          {/* Metadata Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-2xl relative overflow-hidden group">
              <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity">
                <Tag size={64} className="text-white" />
              </div>
              <h4 className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-4 flex items-center gap-2">
                <Tag size={12} className="text-blue-500" /> Classification
              </h4>
              <div className="flex items-center gap-4">
                <div className={`px-3 py-1 rounded-full text-xs font-black uppercase border ${getStatusColor(task.status)}`}>
                  {task.status}
                </div>
                <div className={`px-3 py-1 rounded-full text-xs font-black uppercase border ${getPriorityColor(task.priority)}`}>
                  {task.priority} Priority
                </div>
              </div>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-2xl relative overflow-hidden group">
              <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity">
                <Calendar size={64} className="text-white" />
              </div>
              <h4 className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-4 flex items-center gap-2">
                <Calendar size={12} className="text-emerald-500" /> Timeline
              </h4>
              <div className="space-y-1">
                <div className="text-white font-bold text-lg">
                  {task.deadline ? formatDate(task.deadline) : "No deadline set"}
                </div>
                <div className="text-slate-500 text-xs">
                  Target completion date
                </div>
              </div>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-2xl relative overflow-hidden group">
              <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity">
                <User size={64} className="text-white" />
              </div>
              <h4 className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-4 flex items-center gap-2">
                <User size={12} className="text-purple-500" /> Assigned To
              </h4>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-slate-800 border border-white/10 flex items-center justify-center font-bold text-slate-300 text-sm">
                  {task.assigned_to_name?.[0] || "?"}
                </div>
                <div className="space-y-0.5">
                  <div className="text-white font-bold">
                    {task.assigned_to_name || "Unassigned"}
                  </div>
                  <div className="text-slate-500 text-xs uppercase tracking-tighter font-bold font-mono">
                    ID: {task.assigned_to_user_id || "N/A"}
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-2xl relative overflow-hidden group">
              <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity">
                <ClipboardList size={64} className="text-white" />
              </div>
              <h4 className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-4 flex items-center gap-2">
                <ClipboardList size={12} className="text-amber-500" /> Project Context
              </h4>
              <div className="space-y-1">
                <div className="text-white font-bold text-lg truncate">
                  {activeProject?.project_name || "Project CRM"}
                </div>
                <div className="text-slate-500 text-xs truncate">
                  {activeProject?.location || "Main Site"}
                </div>
              </div>
            </div>
          </div>

          {/* Description & Content */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 shadow-2xl">
            <h3 className="text-lg font-bold text-white flex items-center gap-2 mb-6">
              <FileText className="text-blue-500" size={20} />
              Full Description
            </h3>
            <div className="prose prose-invert max-w-none">
              <p className="text-slate-300 leading-relaxed text-lg font-light leading-snug">
                {task.task_description}
              </p>
              <div className="mt-8 pt-8 border-t border-slate-800/50">
                <div className="grid grid-cols-2 gap-8">
                  <div>
                    <h5 className="text-[10px] font-bold text-slate-500 uppercase tracking-[0.2em] mb-2">Created On</h5>
                    <p className="text-slate-200 text-sm font-mono">{formatDate(task.created_at)}</p>
                  </div>
                  <div>
                    <h5 className="text-[10px] font-bold text-slate-500 uppercase tracking-[0.2em] mb-2">Last Updated</h5>
                    <p className="text-slate-200 text-sm font-mono">{formatDate(task.updated_at)}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 shadow-2xl">
            <TaskChangeLog logs={task.audit_log || []} />
          </div>
        </div>

        {/* Sidebar Info */}
        <div className="space-y-6">
          <TaskAISummary projectId={activeProject?.project_id || activeProject?._id || ""} />

          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl">
            <h3 className="text-sm font-bold text-white mb-4 flex items-center gap-2">
              <Eye className="text-slate-400" size={16} /> Fast Actions
            </h3>
            <div className="space-y-3">
              <button
                className="w-full bg-slate-950 hover:bg-slate-800 border border-slate-800 py-3 rounded-lg text-xs font-bold text-slate-300 transition-all flex items-center justify-center gap-2"
              >
                <FileText size={14} /> Attachment Upload
              </button>
              <button
                className="w-full bg-slate-950 hover:bg-slate-800 border border-slate-800 py-3 rounded-lg text-xs font-bold text-slate-300 transition-all flex items-center justify-center gap-2"
              >
                <MoreVertical size={14} /> Send Email Follow-up
              </button>
            </div>
          </div>
        </div>
      </div>

      <ConfirmDialog
        isOpen={showCloseConfirm}
        onClose={() => setShowCloseConfirm(false)}
        onConfirm={() => updateStatus("Closed")}
        title="Finalize & Close Task"
        description="Are you sure you want to close this task? This will mark it as permanently archived and freeze its timeline impact. This action is intended for fully verified milestones."
        confirmText="Finalize & Close"
        isLoading={isUpdating}
        variant="warning"
      />
    </div>
  );
}
