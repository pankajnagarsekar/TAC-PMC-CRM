"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { CheckSquare, ArrowLeft, Loader2, Save, AlertCircle } from "lucide-react";
import api from "@/lib/api";
import { useProjectStore } from "@/store/projectStore";
import AssigneeComboBox from "@/components/tasks/AssigneeComboBox";
import { useToast } from "@/hooks/use-toast";
import { useUnsavedChanges } from "@/hooks/use-unsaved-changes";
import { StyledDateInput } from "@/components/ui/StyledDateInput";

export default function NewTaskPage() {
  const router = useRouter();
  const { activeProject } = useProjectStore();
  const { toast } = useToast();

  const [isLoading, setIsLoading] = useState(false);
  const [isDirty, setIsDirty] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  
  const [formData, setFormData] = useState({
    task_description: "",
    assigned_to_user_id: "",
    assigned_to_name: "",
    assigned_to_type: "",
    deadline: "",
    priority: "Medium",
    notes: "",
  });

  // Guard against unsaved changes
  useUnsavedChanges(isDirty);

  const validate = () => {
    const newErrors: Record<string, string> = {};
    
    if (!formData.task_description.trim()) {
      newErrors.task_description = "Description is required";
    } else if (formData.task_description.length < 5) {
      newErrors.task_description = "Description must be at least 5 characters";
    }

    if (!formData.assigned_to_user_id && !formData.assigned_to_name) {
      newErrors.assignee = "Please select an assignee";
    }

    if (!formData.priority) {
      newErrors.priority = "Priority is required";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeProject) return;

    if (!validate()) {
      toast({
        title: "Validation Error",
        description: "Please fix the highlighted fields before submitting.",
        variant: "destructive",
      });
      return;
    }

    setIsLoading(true);
    try {
      const projectId = activeProject.project_id || activeProject._id;

      const payload: Record<string, unknown> = {
        project_id: projectId,
        task_description: formData.task_description.trim(),
        assigned_to_name: formData.assigned_to_name || "Unassigned",
        assigned_to_type: formData.assigned_to_type || "external",
        priority: formData.priority,
      };
      if (formData.assigned_to_user_id) payload.assigned_to_user_id = formData.assigned_to_user_id;
      if (formData.deadline) payload.deadline = formData.deadline;
      if (formData.notes) payload.notes = formData.notes.trim();

      await api.post("/api/v1/tasks/", payload);

      setIsDirty(false); // Reset dirty state before navigation
      toast({
        title: "Task Created",
        description: "The task has been successfully scheduled.",
      });
      router.push("/admin/tasks");
    } catch (err: unknown) {
      console.error(err);
      const error = err as { response?: { data?: { detail?: string | string[] } } };
      let errorMsg = "An error occurred while creating the task.";
      
      if (error?.response?.data?.detail) {
        if (Array.isArray(error.response.data.detail)) {
          errorMsg = error.response.data.detail[0];
        } else {
          errorMsg = error.response.data.detail;
        }
      }

      toast({
        title: "Submission Failed",
        description: errorMsg,
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  if (!activeProject) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] bg-slate-900 border border-slate-800 rounded-xl animate-in fade-in zoom-in duration-500">
        <div className="w-16 h-16 rounded-2xl bg-slate-800/50 flex items-center justify-center mb-6 ring-1 ring-slate-700">
          <CheckSquare className="w-8 h-8 text-slate-500" />
        </div>
        <h3 className="text-xl font-bold text-white mb-2">No Project Selected</h3>
        <p className="text-slate-400 max-w-xs text-center px-4">
          Strategic context is missing. Please select a project from the top navigation to continue.
        </p>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-700">
      <div className="flex items-center gap-4">
        <button
          onClick={() => router.push("/admin/tasks")}
          className="p-2.5 hover:bg-slate-800 text-slate-400 hover:text-white rounded-xl transition-all border border-transparent hover:border-slate-700"
        >
          <ArrowLeft size={20} />
        </button>
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Create New Task</h1>
          <p className="text-slate-400 text-sm mt-1 flex items-center gap-2">
            Allocation for <span className="text-blue-400 font-semibold uppercase tracking-wider text-[10px] bg-blue-500/10 px-2 py-0.5 rounded-full border border-blue-500/20">{activeProject.project_name}</span>
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="bg-slate-900 border border-slate-800 rounded-2xl p-8 space-y-8 xl:col-span-2 shadow-[0_20px_50px_rgba(0,0,0,0.4)] relative overflow-hidden group">
        <div className="absolute top-0 left-0 w-1 h-full bg-blue-600/50" />
        
        <div className="space-y-6">
          <div className="space-y-2">
            <label className="flex justify-between text-[11px] font-black uppercase tracking-widest text-slate-500">
              <span>Task Description</span>
              <span className="text-rose-500 font-bold">* Required</span>
            </label>
            <textarea
              rows={3}
              value={formData.task_description}
              onChange={(e) => {
                setIsDirty(true);
                setFormData({ ...formData, task_description: e.target.value });
                if (errors.task_description) setErrors({ ...errors, task_description: "" });
              }}
              className={`w-full bg-slate-950 border ${errors.task_description ? "border-rose-500/50 ring-1 ring-rose-500/10" : "border-slate-800"} rounded-xl px-4 py-3 text-white focus:outline-none focus:border-blue-500/50 focus:ring-4 focus:ring-blue-500/10 transition-all resize-none placeholder:text-slate-700`}
              placeholder="Define the scope of work..."
            />
            {errors.task_description && (
              <p className="flex items-center gap-1.5 text-rose-500 text-[10px] font-bold uppercase tracking-tight">
                <AlertCircle size={12} /> {errors.task_description}
              </p>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div className="space-y-2">
              <label className="flex justify-between text-[11px] font-black uppercase tracking-widest text-slate-500">
                <span>Assignee</span>
                <span className="text-rose-500 font-bold">*</span>
              </label>
              <AssigneeComboBox
                value={formData.assigned_to_user_id}
                onChange={(id, name, type) => {
                  setIsDirty(true);
                  setFormData({
                    ...formData,
                    assigned_to_user_id: id,
                    assigned_to_name: name,
                    assigned_to_type: type
                  });
                  if (errors.assignee) setErrors({ ...errors, assignee: "" });
                }}
              />
              {errors.assignee && (
                <p className="flex items-center gap-1.5 text-rose-500 text-[10px] font-bold uppercase tracking-tight">
                  <AlertCircle size={12} /> {errors.assignee}
                </p>
              )}
            </div>

            <div className="space-y-2">
              <label className="block text-[11px] font-black uppercase tracking-widest text-slate-500">
                Deadline
              </label>
              <StyledDateInput
                value={formData.deadline}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => {
                  setIsDirty(true);
                  setFormData({ ...formData, deadline: e.target.value });
                }}
                className="bg-slate-950 border-slate-800 focus:border-blue-500/50"
                hideIcon
              />
              {formData.deadline && new Date(formData.deadline) < new Date(new Date().toDateString()) && (
                <p className="mt-1 text-[10px] font-bold text-amber-500 uppercase tracking-tight flex items-center gap-1">
                  <AlertCircle size={12} /> Deadline is in the past
                </p>
              )}
            </div>

            <div className="space-y-2">
              <label className="block text-[11px] font-black uppercase tracking-widest text-slate-500">
                Priority <span className="text-rose-500 font-bold">*</span>
              </label>
              <select
                required
                value={formData.priority}
                onChange={(e) => {
                  setIsDirty(true);
                  setFormData({ ...formData, priority: e.target.value });
                }}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-white focus:outline-none focus:border-blue-500/50 focus:ring-4 focus:ring-blue-500/10 transition-all appearance-none"
              >
                <option value="Low">Low Priority</option>
                <option value="Medium">Medium Priority</option>
                <option value="High">High Priority</option>
              </select>
            </div>
          </div>

          <div className="space-y-2">
            <label className="block text-[11px] font-black uppercase tracking-widest text-slate-500">
              Internal Notes / Context
            </label>
            <textarea
              rows={2}
              value={formData.notes}
              onChange={(e) => {
                setIsDirty(true);
                setFormData({ ...formData, notes: e.target.value });
              }}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-blue-500/50 focus:ring-4 focus:ring-blue-500/10 transition-all resize-none placeholder:text-slate-700"
              placeholder="Any additional orchestration details..."
            />
          </div>
        </div>

        <div className="flex justify-end items-center gap-6 pt-8 border-t border-slate-800">
          <button
            type="button"
            onClick={() => router.back()}
            className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-500 hover:text-white transition-colors"
          >
            Discard Draft
          </button>
          <button
            type="submit"
            disabled={isLoading}
            className="flex items-center gap-3 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white px-8 py-3.5 rounded-xl text-xs font-black uppercase tracking-[0.2em] transition-all shadow-[0_10px_20px_rgba(37,99,235,0.2)] hover:shadow-[0_15px_30px_rgba(37,99,235,0.4)] active:scale-95 group/btn"
          >
            {isLoading ? (
              <Loader2 size={16} className="animate-spin" />
            ) : (
              <Save size={16} className="group-hover/btn:translate-y-[-1px] transition-transform" />
            )}
            Persist Task
          </button>
        </div>
      </form>
    </div>
  );
}
