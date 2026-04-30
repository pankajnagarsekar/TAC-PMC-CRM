import { useState, useEffect } from "react";
import { Task } from "@/types/api";
import TaskCard from "./TaskCard";
import { DragDropContext, Droppable, Draggable, DropResult } from "@hello-pangea/dnd";
import api from "@/lib/api";
import { toast } from "sonner";
import { Loader2, AlertCircle } from "lucide-react";

interface TaskKanbanBoardProps {
  tasks: Task[];
  onTaskUpdate?: (updatedTask: Task) => void;
}

// Authoritative statuses from index.ts
const KANBAN_STATUSES = ["Open", "In Progress", "Review", "Completed", "Closed"] as const;

export default function TaskKanbanBoard({ tasks = [], onTaskUpdate }: TaskKanbanBoardProps) {
  const [mounted, setMounted] = useState(false);
  const [isUpdating, setIsUpdating] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const onDragEnd = async (result: DropResult) => {
    const { destination, source, draggableId } = result;

    if (!destination) return;

    if (
      destination.droppableId === source.droppableId &&
      destination.index === source.index
    ) {
      return;
    }

    const task = tasks.find((t) => t._id === draggableId || t.id === draggableId);
    if (!task) return;

    const newStatus = destination.droppableId as Task["status"];
    const oldStatus = task.status;

    // Optimistic update
    const updatedTask = { ...task, status: newStatus };
    if (onTaskUpdate) {
      onTaskUpdate(updatedTask);
    }

    setIsUpdating(true);
    try {
      const res = await api.patch(`/api/v1/tasks/${task._id || task.id}/status`, {
        status: newStatus,
      });

      if (res.data && onTaskUpdate) {
        onTaskUpdate(res.data);
      }
      toast.success(`Task moved to ${newStatus}`);
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      console.error("Failed to update task status", error);
      
      // Rollback on error
      if (onTaskUpdate) {
        onTaskUpdate({ ...task, status: oldStatus });
      }
      const errorMsg = error.response?.data?.detail || "Failed to update status";
      toast.error(typeof errorMsg === "string" ? errorMsg : "Failed to update status");
    } finally {
      setIsUpdating(false);
    }
  };

  if (!mounted) {
    return (
      <div className="flex gap-4 overflow-x-auto pb-4 custom-scrollbar h-[calc(100vh-280px)] min-h-[500px] snap-x animate-pulse">
        {KANBAN_STATUSES.map((status) => (
          <div key={status} className="flex-1 min-w-[280px] max-w-[320px] bg-slate-900/50 border border-slate-800/50 rounded-xl p-3" />
        ))}
      </div>
    );
  }

  // Safety check to prevent blank screen if tasks is somehow not an array
  if (!Array.isArray(tasks)) {
    return (
      <div className="flex flex-col items-center justify-center p-12 border border-slate-800 rounded-xl bg-slate-900/50 text-center">
        <AlertCircle className="w-12 h-12 text-rose-500 mb-4" />
        <h3 className="text-xl font-bold text-white">Data Load Error</h3>
        <p className="text-slate-400 mt-2">The task data received is in an invalid format.</p>
      </div>
    );
  }

  return (
    <DragDropContext onDragEnd={onDragEnd}>
      <div className="flex gap-4 overflow-x-auto pb-4 custom-scrollbar h-[calc(100vh-280px)] min-h-[500px] snap-x relative">
        {isUpdating && (
          <div className="absolute inset-0 bg-slate-950/20 backdrop-blur-[1px] z-50 flex items-center justify-center pointer-events-none rounded-xl">
             <div className="bg-slate-900 border border-slate-800 px-4 py-2 rounded-full shadow-2xl flex items-center gap-2">
                <Loader2 size={14} className="animate-spin text-blue-500" />
                <span className="text-[10px] font-black uppercase tracking-widest text-white">Syncing Status...</span>
             </div>
          </div>
        )}

        {KANBAN_STATUSES.map((status) => {
          const statusTasks = tasks.filter((t) => (t.status || "Open") === status);
          
          return (
            <div
              key={status}
              className="flex-1 min-w-[280px] max-w-[320px] bg-slate-900 border border-slate-800 rounded-xl p-3 flex flex-col gap-3 snap-center shadow-lg transition-all"
            >
              <div className="flex justify-between items-center px-2 py-1 sticky top-0 bg-slate-900 z-10 border-b border-slate-800 pb-3">
                <h3 className="font-bold text-slate-300 text-sm uppercase tracking-wider flex items-center gap-2">
                  <div
                    className={`w-2 h-2 rounded-full shadow-[0_0_8px_rgba(0,0,0,0.5)] ${status === "Open"
                      ? "bg-slate-400"
                      : status === "In Progress"
                        ? "bg-blue-400 shadow-blue-400/20"
                        : status === "Review"
                          ? "bg-amber-400 shadow-amber-400/20"
                          : status === "Completed"
                            ? "bg-emerald-400 shadow-emerald-400/20"
                            : "bg-emerald-800"
                      }`}
                  />
                  {status}
                </h3>
                <span className="text-[10px] font-black bg-slate-800 border border-slate-700 text-slate-400 px-2.5 py-0.5 rounded-full">
                  {statusTasks.length}
                </span>
              </div>

              <Droppable droppableId={status}>
                {(provided, snapshot) => (
                  <div
                    ref={provided.innerRef}
                    {...provided.droppableProps}
                    className={`flex flex-col gap-3 flex-1 overflow-y-auto custom-scrollbar pr-1 min-h-[150px] transition-all rounded-lg ${snapshot.isDraggingOver ? "bg-slate-800/30 ring-1 ring-blue-500/20" : ""
                      }`}
                  >
                    {statusTasks.length > 0 ? (
                      statusTasks.map((task, index) => {
                        const taskId = task._id || task.id || `temp-${index}`;
                        return (
                          <Draggable key={taskId} draggableId={taskId} index={index}>
                            {(provided, snapshot) => (
                              <div
                                ref={provided.innerRef}
                                {...provided.draggableProps}
                                {...provided.dragHandleProps}
                                className={`${snapshot.isDragging ? "z-50 rotate-2 scale-105" : ""} transition-transform duration-200`}
                                style={{
                                  ...provided.draggableProps.style,
                                }}
                              >
                                <TaskCard task={task} />
                              </div>
                            )}
                          </Draggable>
                        );
                      })
                    ) : (
                      <div className="flex flex-col text-center items-center justify-center p-6 border-2 border-dashed border-slate-800 rounded-xl text-slate-500 my-auto bg-slate-900/20">
                        <span className="text-[10px] font-black uppercase tracking-tighter opacity-40">No Tasks</span>
                      </div>
                    )}
                    {provided.placeholder}
                  </div>
                )}
              </Droppable>
            </div>
          );
        })}
      </div>
    </DragDropContext>
  );
}
