import { Task } from "@/types/api";
import TaskCard from "./TaskCard";

interface TaskKanbanBoardProps {
  tasks: Task[];
}

export default function TaskKanbanBoard({ tasks }: TaskKanbanBoardProps) {
  const statuses = ["Open", "In Progress", "Review", "Completed", "Closed"];

  return (
    <div className="flex gap-4 overflow-x-auto pb-4 custom-scrollbar min-h-[60vh] snap-x">
      {statuses.map((status) => {
        const statusTasks = tasks.filter((t) => t.status === status);
        return (
          <div
            key={status}
            className="flex-1 min-w-[280px] max-w-[320px] bg-slate-900 border border-slate-800 rounded-xl p-3 flex flex-col gap-3 snap-center shadow-lg"
          >
            <div className="flex justify-between items-center px-2 py-1 sticky top-0 bg-slate-900 z-10 border-b border-slate-800 pb-3">
              <h3 className="font-bold text-slate-300 text-sm uppercase tracking-wider flex items-center gap-2">
                <div
                  className={`w-2 h-2 rounded-full ${
                    status === "Open"
                      ? "bg-slate-400"
                      : status === "In Progress"
                        ? "bg-blue-400"
                        : status === "Review"
                          ? "bg-amber-400"
                          : status === "Completed"
                            ? "bg-emerald-400"
                            : "bg-emerald-800"
                  }`}
                />
                {status}
              </h3>
              <span className="text-[10px] font-bold bg-slate-800 border border-slate-700 text-slate-400 px-2.5 py-0.5 rounded-full">
                {statusTasks.length}
              </span>
            </div>
            
            <div className="flex flex-col gap-3 flex-1 overflow-y-auto custom-scrollbar pr-1">
              {statusTasks.length > 0 ? (
                statusTasks.map((task) => (
                  <TaskCard key={task._id} task={task} />
                ))
              ) : (
                <div className="flex flex-col text-center items-center justify-center p-6 border-2 border-dashed border-slate-800 rounded-lg text-slate-500 my-auto bg-slate-900/50">
                  <span className="text-xs font-medium">No Tasks</span>
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
