'use client';

import { Task } from "@/types/api";
import { useRouter } from "next/navigation";
import { Clock } from "lucide-react";
import { formatDate } from "@tac-pmc/ui";

interface TaskCardProps {
  task: Task;
}

export default function TaskCard({ task }: TaskCardProps) {
  const router = useRouter();

  const handleCardClick = () => {
    router.push(`/admin/tasks/${task._id}`);
  };

  return (
    <div
      onClick={handleCardClick}
      className="bg-slate-800 border border-slate-700 p-3 rounded-lg shadow-sm hover:border-blue-500 hover:shadow-md cursor-pointer transition-all group active:scale-[0.98]"
    >
      <div className="flex justify-between items-start mb-2">
        <div className="text-xs text-slate-400 font-mono">
          TASK-{task.sr_no}
        </div>
        {task.priority === "High" && (
          <span className="px-1.5 py-0.5 bg-red-500/10 text-red-500 border border-red-500/20 text-[10px] rounded uppercase font-bold">
            High
          </span>
        )}
        {task.priority === "Medium" && (
          <span className="px-1.5 py-0.5 bg-amber-500/10 text-amber-500 border border-amber-500/20 text-[10px] rounded uppercase font-bold">
            Med
          </span>
        )}
      </div>

      <h4 className="text-sm font-semibold text-white mb-3 line-clamp-3 leading-snug group-hover:text-blue-400 transition-colors">
        {task.task_description}
      </h4>

      <div className="flex justify-between items-center mt-auto border-t border-slate-700/50 pt-2">
        <div
          className="flex items-center gap-2"
          title={`Assigned to: ${task.assigned_to_name}`}
        >
          <div className="w-6 h-6 rounded-full bg-slate-700 flex items-center justify-center text-[10px] font-bold text-slate-300 uppercase shadow-inner border border-slate-600">
            {task.assigned_to_name ? task.assigned_to_name.slice(0, 2) : "??"}
          </div>
          <span className="text-xs text-slate-400 truncate max-w-[80px]">
            {task.assigned_to_name || "Unassigned"}
          </span>
        </div>

        {task.deadline && (
          <div
            className="flex items-center gap-1 text-[10px] text-slate-400 font-medium"
            title={`Deadline: ${formatDate(task.deadline)}`}
          >
            <Clock size={10} className="text-blue-500" />
            {formatDate(task.deadline)}
          </div>
        )}
      </div>
    </div>
  );
}
