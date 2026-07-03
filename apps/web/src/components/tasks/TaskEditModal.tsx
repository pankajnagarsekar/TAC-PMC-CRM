'use client';

import { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@tac-pmc/ui';
import { Task } from '@/types/api';
import api from '@/lib/api';
import AssigneeComboBox from './AssigneeComboBox';
import { StyledDateInput } from '../ui/StyledDateInput';
import { Loader2, AlertCircle } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

interface TaskEditModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  task: Task;
}

export default function TaskEditModal({ isOpen, onClose, onSuccess, task }: TaskEditModalProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { toast } = useToast();

  const [formData, setFormData] = useState({
    task_description: "",
    assigned_to_user_id: "",
    assigned_to_name: "",
    assigned_to_type: "",
    deadline: "",
    priority: "Medium",
    notes: "",
    status: "Open"
  });

  useEffect(() => {
    setError(null);
    if (task) {
      setFormData({
        task_description: task.task_description || "",
        assigned_to_user_id: task.assigned_to_user_id || "",
        assigned_to_name: task.assigned_to_name || "",
        assigned_to_type: task.assigned_to_type || "external",
        deadline: task.deadline ? new Date(task.deadline).toISOString().split('T')[0] : "",
        priority: task.priority || "Medium",
        notes: task.notes || "",
        status: task.status || "Open"
      });
    }
  }, [task, isOpen]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!formData.task_description.trim()) {
      setError("Task description is required");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const payload: Record<string, any> = {
        task_description: formData.task_description.trim(),
        assigned_to_name: formData.assigned_to_name || "Unassigned",
        assigned_to_type: formData.assigned_to_type || "external",
        priority: formData.priority,
        status: formData.status,
        notes: formData.notes.trim()
      };
      
      if (formData.assigned_to_user_id) {
        payload.assigned_to_user_id = formData.assigned_to_user_id;
      } else {
        payload.assigned_to_user_id = null;
      }
      
      if (formData.deadline) {
        payload.deadline = formData.deadline;
      } else {
        payload.deadline = null;
      }

      const taskId = task.id || task._id;
      await api.patch(`/api/v1/tasks/${taskId}`, payload);
      
      toast({
        title: "Task Updated",
        description: "Task changes have been saved successfully.",
      });
      onSuccess();
      onClose();
    } catch (err: unknown) {
      console.error(err);
      const errorRes = err as { response?: { data?: { detail?: string | string[] } } };
      let errorMsg = "Failed to update the task.";
      if (errorRes?.response?.data?.detail) {
        errorMsg = Array.isArray(errorRes.response.data.detail)
          ? errorRes.response.data.detail[0]
          : errorRes.response.data.detail;
      }
      setError(errorMsg);
    } finally {
      setLoading(false);
    }
  }

  const labelStyle = "block text-[11px] font-black uppercase tracking-widest text-slate-500 mb-1.5";

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="bg-slate-950 border border-white/10 text-white max-w-lg rounded-[2rem] p-0 overflow-hidden shadow-2xl backdrop-blur-2xl">
        <DialogHeader className="p-6 border-b border-white/5 bg-white/[0.02]">
          <DialogTitle className="text-xl font-bold bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">
            Edit Task Details
          </DialogTitle>
          <p className="text-slate-500 text-xs mt-1">
            Update scope, assignments, timeline, and classification.
          </p>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          {error && (
            <div className="p-3 bg-rose-500/10 border border-rose-500/20 rounded-xl text-rose-500 text-xs font-medium flex items-center gap-2">
              <AlertCircle size={14} />
              {error}
            </div>
          )}

          <div className="space-y-4">
            <div>
              <label className={labelStyle}>Task Description <span className="text-rose-500">*</span></label>
              <textarea
                required
                rows={2}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-blue-500/50 focus:ring-4 focus:ring-blue-500/10 transition-all resize-none placeholder:text-slate-700 text-sm"
                placeholder="Define the scope of work..."
                value={formData.task_description}
                onChange={(e) => setFormData({ ...formData, task_description: e.target.value })}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className={labelStyle}>Assignee</label>
                <AssigneeComboBox
                  value={formData.assigned_to_user_id}
                  onChange={(id, name, type) => {
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
                <label className={labelStyle}>Deadline</label>
                <StyledDateInput
                  value={formData.deadline}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => {
                    setFormData({ ...formData, deadline: e.target.value });
                  }}
                  className="bg-slate-950 border-slate-800 focus:border-blue-500/50"
                  hideIcon
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className={labelStyle}>Priority <span className="text-rose-500">*</span></label>
                <select
                  required
                  value={formData.priority}
                  onChange={(e) => setFormData({ ...formData, priority: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-white focus:outline-none focus:border-blue-500/50 focus:ring-4 focus:ring-blue-500/10 transition-all appearance-none text-sm cursor-pointer"
                >
                  <option value="Low">Low</option>
                  <option value="Medium">Medium</option>
                  <option value="High">High</option>
                </select>
              </div>

              <div>
                <label className={labelStyle}>Status <span className="text-rose-500">*</span></label>
                <select
                  required
                  value={formData.status}
                  onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-white focus:outline-none focus:border-blue-500/50 focus:ring-4 focus:ring-blue-500/10 transition-all appearance-none text-sm cursor-pointer"
                >
                  <option value="Open">Open</option>
                  <option value="In Progress">In Progress</option>
                  <option value="Review">Review</option>
                  <option value="Completed">Completed</option>
                  <option value="Closed">Closed</option>
                </select>
              </div>
            </div>

            <div>
              <label className={labelStyle}>Notes / Context</label>
              <textarea
                rows={2}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-blue-500/50 focus:ring-4 focus:ring-blue-500/10 transition-all resize-none placeholder:text-slate-700 text-sm"
                placeholder="Additional instructions..."
                value={formData.notes}
                onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              />
            </div>
          </div>

          <DialogFooter className="border-t border-white/5 pt-4 flex gap-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-3 bg-white/5 border border-white/5 text-slate-400 font-bold rounded-xl hover:bg-white/10 transition-all uppercase text-[10px] tracking-widest"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 px-4 py-3 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white font-black rounded-xl transition-all shadow-lg shadow-blue-900/20 uppercase text-[10px] tracking-widest flex items-center justify-center gap-2"
            >
              {loading && <Loader2 size={12} className="animate-spin" />}
              Save Changes
            </button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
