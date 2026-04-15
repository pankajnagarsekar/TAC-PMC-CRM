import { Task } from "@/types/api";
import TaskCard from "./TaskCard";
import { DragDropContext, Droppable, Draggable, DropResult } from "@hello-pangea/dnd";
import api from "@/lib/api";
import { toast } from "sonner";

interface TaskKanbanBoardProps {
  tasks: Task[];
  onTaskUpdate?: (updatedTask: Task) => void;
}

export default function TaskKanbanBoard({ tasks, onTaskUpdate }: TaskKanbanBoardProps) {
  const statuses = ["Open", "In Progress", "Review", "Completed", "Closed"];

  const onDragEnd = async (result: DropResult) => {
    const { destination, source, draggableId } = result;

    if (!destination) return;

    if (
      destination.droppableId === source.droppableId &&
      destination.index === source.index
    ) {
      return;
    }

    const task = tasks.find((t) => t._id === draggableId);
    if (!task) return;

    const newStatus = destination.droppableId as Task["status"];
    const oldStatus = task.status;

    // Optimistic update
    const updatedTask = { ...task, status: newStatus };
    if (onTaskUpdate) {
      onTaskUpdate(updatedTask);
    }

    try {
      const res = await api.patch(`/api/v1/tasks/${task._id}/status`, {
        status: newStatus,
      });

      if (res.data && onTaskUpdate) {
        onTaskUpdate(res.data);
      }
      toast.success(`Task moved to ${newStatus}`);
    } catch (error: any) {
      console.error("Failed to update task status", error);
      // Rollback on error
      if (onTaskUpdate) {
        onTaskUpdate({ ...task, status: oldStatus });
      }
      const errorMsg = error.response?.data?.detail || "Failed to update status";
      toast.error(typeof errorMsg === "string" ? errorMsg : "Failed to update status");
    }
  };

  return (
    <DragDropContext onDragEnd={onDragEnd}>
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
                    className={`w-2 h-2 rounded-full ${status === "Open"
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

              <Droppable droppableId={status}>
                {(provided, snapshot) => (
                  <div
                    ref={provided.innerRef}
                    {...provided.droppableProps}
                    className={`flex flex-col gap-3 flex-1 overflow-y-auto custom-scrollbar pr-1 min-h-[150px] transition-colors ${snapshot.isDraggingOver ? "bg-slate-800/30" : ""
                      }`}
                  >
                    {statusTasks.length > 0 ? (
                      statusTasks.map((task, index) => (
                        <Draggable key={task._id} draggableId={task._id!} index={index}>
                          {(provided, snapshot) => (
                            <div
                              ref={provided.innerRef}
                              {...provided.draggableProps}
                              {...provided.dragHandleProps}
                              className={snapshot.isDragging ? "z-50" : ""}
                              style={{
                                ...provided.draggableProps.style,
                              }}
                            >
                              <TaskCard task={task} />
                            </div>
                          )}
                        </Draggable>
                      ))
                    ) : (
                      <div className="flex flex-col text-center items-center justify-center p-6 border-2 border-dashed border-slate-800 rounded-lg text-slate-500 my-auto bg-slate-900/50">
                        <span className="text-xs font-medium">No Tasks</span>
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
