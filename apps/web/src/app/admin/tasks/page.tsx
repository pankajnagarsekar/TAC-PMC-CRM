"use client";

import { useState, useCallback, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Plus, Search, CheckSquare, Loader2, LayoutGrid, List as ListIcon } from "lucide-react";
import api from "@/lib/api";
import { Task } from "@/types/api";
import { useProjectStore } from "@/store/projectStore";
import NetworkErrorRetry from "@/components/ui/NetworkErrorRetry";
import TaskKanbanBoard from "@/components/tasks/TaskKanbanBoard";
import PastTasksTable from "@/components/tasks/PastTasksTable";

export default function TasksPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const currentTab = searchParams.get("tab") || "list";
  const { activeProject } = useProjectStore();
  const [searchTerm, setSearchTerm] = useState("");

  const [items, setItems] = useState<Task[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);

  const fetchTasks = useCallback(async () => {
    if (!activeProject) return;

    setIsLoading(true);
    try {
      const projectId = activeProject.project_id || activeProject._id;
      const url = `/api/v1/tasks/?project_id=${projectId}`;
      const res = await api.get<Task[]>(url);
      setItems(res.data || []);
      setFetchError(null);
    } catch (err) {
      console.error("Failed to fetch Tasks", err);
      setFetchError("Failed to load tasks.");
    } finally {
      setIsLoading(false);
    }
  }, [activeProject]);

  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  const filteredItems = items.filter((task) => {
    const term = searchTerm.toLowerCase();
    return (
      task.task_description?.toLowerCase().includes(term) ||
      task.assigned_to_name?.toLowerCase().includes(term) ||
      task.status?.toLowerCase().includes(term)
    );
  });

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <CheckSquare className="text-blue-500" />
            Tasks
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Manage project tasks, track progress and assign team members.
            {activeProject
              ? ` Showing records for ${activeProject.project_name}.`
              : " Select a project."}
          </p>
        </div>

        <div className="flex items-center gap-3 w-full sm:w-auto">
           <div className="flex bg-slate-900 border border-slate-800 rounded-lg p-1 mr-2">
            <button
              onClick={() => router.push("/admin/tasks?tab=list")}
              className={`p-1.5 rounded flex items-center gap-2 text-sm transition-colors ${currentTab === "list" ? "bg-slate-800 text-white" : "text-slate-400 hover:text-white"}`}
            >
              <ListIcon size={16} /> <span className="hidden sm:inline">List</span>
            </button>
            <button
              onClick={() => router.push("/admin/tasks?tab=board")}
              className={`p-1.5 rounded flex items-center gap-2 text-sm transition-colors ${currentTab === "board" ? "bg-slate-800 text-white" : "text-slate-400 hover:text-white"}`}
            >
              <LayoutGrid size={16} /> <span className="hidden sm:inline">Board</span>
            </button>
          </div>

          <div className="relative flex-1 sm:w-64">
            <Search
              className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500"
              size={18}
            />
            <input
              type="text"
              placeholder="Search tasks..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full bg-slate-900 border border-slate-800 rounded-lg pl-10 pr-4 py-2 text-sm text-foreground focus:outline-none focus:border-blue-500"
            />
          </div>

          <button
            disabled={!activeProject}
            onClick={() => router.push("/admin/tasks/new")}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white px-4 py-2 rounded-lg text-sm font-bold transition-colors whitespace-nowrap"
          >
            <Plus size={18} /> New Task
          </button>
        </div>
      </div>

      {fetchError ? (
        <NetworkErrorRetry
          message={fetchError}
          onRetry={() => { setFetchError(null); fetchTasks(); }}
        />
      ) : !activeProject ? (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center shadow-xl">
          <CheckSquare className="w-12 h-12 text-slate-600 mx-auto mb-4" />
          <h3 className="text-xl font-bold text-white mb-2">
            No Project Selected
          </h3>
          <p className="text-slate-400">
            Please select an active project from the top navigation context.
          </p>
        </div>
      ) : isLoading ? (
        <div className="flex items-center justify-center h-64 border border-slate-800 rounded-xl bg-slate-900/50">
          <Loader2 className="animate-spin h-8 w-8 text-blue-500" />
        </div>
      ) : filteredItems.length === 0 ? (
        <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-12 text-center">
          <h3 className="text-lg font-semibold text-white mb-2">
            No Tasks Found
          </h3>
          <p className="text-slate-400">
            Create tasks to start managing work.
          </p>
        </div>
      ) : currentTab === "board" ? (
        <TaskKanbanBoard tasks={filteredItems} />
      ) : (
        <PastTasksTable tasks={filteredItems} />
      )}
    </div>
  );
}
