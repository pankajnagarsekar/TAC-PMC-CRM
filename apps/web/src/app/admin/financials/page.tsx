"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useProjectStore } from "@/store/projectStore";
import { Loader2, AlertCircle } from "lucide-react";

export default function FinancialsRedirectPage() {
    const router = useRouter();
    const { activeProject } = useProjectStore();

    useEffect(() => {
        if (activeProject) {
            const id = activeProject.project_id || activeProject._id;
            router.replace(`/admin/projects/${id}`);
        }
    }, [activeProject, router]);

    if (!activeProject) {
        return (
            <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-6 animate-in fade-in duration-700">
                <div className="relative">
                    <div className="absolute inset-0 bg-orange-500/20 blur-3xl rounded-full" />
                    <div className="relative p-6 bg-white dark:bg-slate-900 border border-zinc-200 dark:border-slate-800 rounded-3xl shadow-2xl">
                        <AlertCircle className="w-12 h-12 text-orange-500" />
                    </div>
                </div>

                <div className="text-center space-y-2 max-w-md">
                    <h1 className="text-2xl font-bold text-zinc-900 dark:text-white">Active Project Required</h1>
                    <p className="text-zinc-500 dark:text-slate-400 text-sm">
                        To view detailed financial intelligence, please select a project from the sidebar or dashboard first.
                    </p>
                </div>

                <button
                    onClick={() => router.push("/admin/dashboard")}
                    className="px-6 py-2.5 bg-orange-600 hover:bg-orange-500 text-white rounded-xl text-sm font-bold transition-all shadow-lg shadow-orange-900/20"
                >
                    Return to Dashboard
                </button>
            </div>
        );
    }

    return (
        <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
            <Loader2 className="w-8 h-8 animate-spin text-orange-500" />
            <p className="text-zinc-500 dark:text-slate-400 text-sm font-medium animate-pulse">
                Initializing Financial Intelligence Module...
            </p>
        </div>
    );
}
