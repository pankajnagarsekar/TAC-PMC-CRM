"use client";

import { useEffect } from "react";
import { AlertTriangle, RefreshCcw, ArrowLeft } from "lucide-react";
import { useRouter } from "next/navigation";

export default function TasksError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const router = useRouter();

  useEffect(() => {
    console.error("[Tasks] Unhandled error:", error);
  }, [error]);

  return (
    <div className="flex flex-col items-center justify-center h-[60vh] gap-6">
      <div className="flex items-center justify-center w-16 h-16 rounded-2xl bg-red-500/10 border border-red-500/20 text-red-500">
        <AlertTriangle size={32} />
      </div>
      <div className="text-center">
        <h2 className="text-xl font-bold text-white mb-2">Task Error</h2>
        <p className="text-slate-400 text-sm max-w-md">
          {error.message || "An unexpected error occurred in the Tasks module."}
        </p>
      </div>
      <div className="flex gap-3">
        <button
          onClick={() => router.push("/admin/tasks")}
          className="flex items-center gap-2 px-4 py-2 text-slate-300 hover:text-white border border-slate-700 hover:border-slate-500 rounded-lg transition-colors text-sm"
        >
          <ArrowLeft size={16} />
          Back to Tasks
        </button>
        <button
          onClick={reset}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors text-sm font-bold"
        >
          <RefreshCcw size={16} />
          Try Again
        </button>
      </div>
    </div>
  );
}
