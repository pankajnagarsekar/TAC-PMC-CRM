"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { CheckSquare, ArrowLeft, Loader2, Save } from "lucide-react";
import api from "@/lib/api";
import { useProjectStore } from "@/store/projectStore";
import AssigneeComboBox from "@/components/tasks/AssigneeComboBox";
import { useToast } from "@/hooks/use-toast";

import { useUnsavedChanges } from "@/hooks/use-unsaved-changes";

export default function NewTaskPage() {
  const router = useRouter();
  const { activeProject } = useProjectStore();
  const { toast } = useToast();

  const [isLoading, setIsLoading] = useState(false);
  const [isDirty, setIsDirty] = useState(false);
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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeProject) return;

    setIsLoading(true);
    try {
      const projectId = activeProject.project_id || activeProject._id;

      const payload: Record<string, unknown> = {
        project_id: projectId,
        task_description: formData.task_description,
        assigned_to_name: formData.assigned_to_name || "Unassigned",
        assigned_to_type: formData.assigned_to_type || "external",
        priority: formData.priority,
      };
      if (formData.assigned_to_user_id) payload.assigned_to_user_id = formData.assigned_to_user_id;
      if (formData.deadline) payload.deadline = formData.deadline;
      if (formData.notes) payload.notes = formData.notes;

      await api.post("/api/v1/tasks/", payload);

      setIsDirty(false); // Reset dirty state before navigation
      toast({
        title: "Task Created",
        description: "The task has been successfully scheduled.",
      });
      router.push("/admin/tasks");
    } catch (error: any) {
      console.error(error);
      toast({
        title: "Failed to create task",
        description: error?.response?.data?.detail || "An error occurred",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  if (!activeProject) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] bg-slate-900 border border-slate-800 rounded-xl">
        <CheckSquare className="w-12 h-12 text-slate-600 mb-4" />
        <h3 className="text-xl font-bold text-white mb-2">No Project Selected</h3>
        <p className="text-slate-400">Please select a project to create tasks.</p>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6 animate-in fade-in duration-500">
      <div className="flex items-center gap-4">
        <button
          onClick={() => router.push("/admin/tasks")}
          className="p-2 hover:bg-slate-800 text-slate-400 hover:text-white rounded-lg transition-colors"
        >
          <ArrowLeft size={20} />
        </button>
        <div>
          <h1 className="text-2xl font-bold text-white">Create New Task</h1>
          <p className="text-slate-400 text-sm mt-1">
            Project: <span className="text-blue-400 font-medium">{activeProject.project_name}</span>
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-6 xl:col-span-2 shadow-xl">
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-400 mb-1">
              Description <span className="text-red-500">*</span>
            </label>
            <textarea
              required
              rows={3}
              value={formData.task_description}
              onChange={(e) => {
                setIsDirty(true);
                setFormData({ ...formData, task_description: e.target.value });
              }}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-blue-500 resize-none"
              placeholder="What needs to be done?"
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-400 mb-1">
                Assignee
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
                }}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-400 mb-1">
                Deadline
              </label>
              <input
                type="date"
                value={formData.deadline}
                onChange={(e) => {
                  setIsDirty(true);
                  setFormData({ ...formData, deadline: e.target.value });
                }}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-blue-500"
              />
              {formData.deadline && new Date(formData.deadline) < new Date(new Date().toDateString()) && (
                <p className="mt-1 text-xs text-amber-400">Warning: deadline is in the past</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-400 mb-1">
                Priority
              </label>
              <select
                value={formData.priority}
                onChange={(e) => {
                  setIsDirty(true);
                  setFormData({ ...formData, priority: e.target.value });
                }}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-blue-500 appearance-none"
              >
                <option value="Low">Low</option>
                <option value="Medium">Medium</option>
                <option value="High">High</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-400 mb-1">
              Notes / Context (Optional)
            </label>
            <textarea
              rows={2}
              value={formData.notes}
              onChange={(e) => {
                setIsDirty(true);
                setFormData({ ...formData, notes: e.target.value });
              }}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-blue-500 resize-none"
              placeholder="Any additional details..."
            />
          </div>
        </div>

        <div className="flex justify-end gap-3 pt-4 border-t border-slate-800">
          <button
            type="button"
            onClick={() => router.back()}
            className="px-4 py-2 text-slate-300 hover:text-white transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={isLoading || !formData.task_description}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white px-6 py-2 rounded-lg font-bold transition-colors"
          >
            {isLoading ? <Loader2 size={18} className="animate-spin" /> : <Save size={18} />}
            Create Task
          </button>
        </div>
      </form>
    </div>
  );
}
