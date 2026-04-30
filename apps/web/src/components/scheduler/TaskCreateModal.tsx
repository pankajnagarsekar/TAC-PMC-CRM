"use client";

import React, { useState } from "react";
import { X, FileText } from "lucide-react";
import { Dialog, DialogContent, DialogTitle, DialogFooter } from "@tac-pmc/ui";

import { useScheduleStore } from "@/store/useScheduleStore";
import { StyledDateInput } from "@/components/ui/StyledDateInput";
import { toast } from "sonner";

interface TaskCreateModalProps {
  isOpen: boolean;
  onClose: () => void;
  projectId: string;
}

export function TaskCreateModal({ isOpen, onClose, projectId }: TaskCreateModalProps) {
  const [taskName, setTaskName] = useState("");
  const [scheduledStart, setScheduledStart] = useState("");
  const [scheduledDuration, setScheduledDuration] = useState<number>(1);
  const [taskMode, setTaskMode] = useState<"Auto" | "Manual">("Manual");

  const createDraftTask = useScheduleStore((state) => state.createDraftTask);
  const openTaskModal = useScheduleStore((state) => state.openTaskModal);

  const handleCreate = () => {
    if (!taskName.trim()) {
      toast.error("Task name is required");
      return;
    }

    // This creates the task in the store and persists it via queueCalculation
    const newTask = createDraftTask(projectId, {
      task_name: taskName,
      scheduled_start: scheduledStart || null,
      scheduled_duration: scheduledDuration,
      task_mode: taskMode,
    });

    toast.success("Task created successfully");
    onClose();
    
    // Reset local state
    setTaskName("");
    setScheduledStart("");
    setScheduledDuration(1);
    setTaskMode("Manual");

    // Open details modal
    openTaskModal(newTask.task_id);
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-md bg-white dark:bg-slate-950 border border-zinc-200 dark:border-slate-800 text-zinc-900 dark:text-white p-0 overflow-hidden rounded-[24px]">
        <div className="p-6 space-y-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-full bg-orange-500/10">
                <FileText className="text-orange-500" size={24} />
              </div>
              <DialogTitle className="text-xl font-black tracking-tight uppercase">
                Initialize Task
              </DialogTitle>
            </div>
            <button
              onClick={onClose}
              className="text-slate-400 hover:text-slate-900 dark:hover:text-white transition-colors"
            >
              <X size={20} />
            </button>
          </div>

          <div className="space-y-4 pt-2">
            <label className="space-y-1.5 block">
              <span className="block text-[10px] font-black uppercase tracking-[0.18em] text-slate-500">
                Task Definition *
              </span>
              <input
                value={taskName}
                onChange={(e) => setTaskName(e.target.value)}
                placeholder="Enter task name..."
                className="w-full rounded-xl border border-slate-200 dark:border-white/5 bg-slate-100 dark:bg-white/[0.03] px-3 py-2 text-sm font-medium text-slate-900 dark:text-white outline-none focus:border-orange-400/40 transition-all"
                autoFocus
              />
            </label>

            <div className="grid grid-cols-2 gap-4">
              <label className="space-y-1.5 block">
                <span className="block text-[10px] font-black uppercase tracking-[0.18em] text-slate-500">
                  Execution Mode
                </span>
                <select
                  value={taskMode}
                  onChange={(e) => setTaskMode(e.target.value as "Auto" | "Manual")}
                  className="w-full rounded-xl border border-slate-200 dark:border-white/5 bg-slate-100 dark:bg-white/[0.03] px-3 py-2 text-sm font-medium text-slate-900 dark:text-white outline-none focus:border-orange-400/40 transition-all"
                >
                  <option value="Manual">Manual</option>
                  <option value="Auto">Auto (CPM)</option>
                </select>
              </label>
              
              <label className="space-y-1.5 block">
                <span className="block text-[10px] font-black uppercase tracking-[0.18em] text-slate-500">
                  Duration (Days)
                </span>
                <input
                  type="number"
                  min={1}
                  value={scheduledDuration}
                  onChange={(e) => setScheduledDuration(Number(e.target.value) || 1)}
                  className="w-full rounded-xl border border-slate-200 dark:border-white/5 bg-slate-100 dark:bg-white/[0.03] px-3 py-2 text-sm font-medium text-slate-900 dark:text-white outline-none focus:border-orange-400/40 transition-all"
                />
              </label>
            </div>

            <label className="space-y-1.5 block">
              <span className="block text-[10px] font-black uppercase tracking-[0.18em] text-slate-500">
                Scheduled Start (Optional)
              </span>
              <StyledDateInput
                value={scheduledStart}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setScheduledStart(e.target.value)}
                hideIcon={false}
              />
            </label>
          </div>
        </div>

        <DialogFooter className="bg-zinc-50 dark:bg-slate-900/50 px-6 py-4 border-t border-zinc-200 dark:border-slate-800 flex items-center justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm font-black uppercase tracking-widest text-zinc-500 dark:text-slate-400 hover:text-zinc-900 dark:hover:text-white transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleCreate}
            className="px-6 py-2 rounded-xl text-sm font-black uppercase tracking-widest text-white bg-orange-600 hover:bg-orange-500 shadow-lg shadow-orange-900/20 transition-all disabled:opacity-50"
          >
            Create Task
          </button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
