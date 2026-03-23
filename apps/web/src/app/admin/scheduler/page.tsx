"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import { useProjectStore } from "@/store/projectStore";
import { schedulerApi } from "@/lib/api";
import { AlertTriangle, Play, Save, FileDown, CheckCircle, Info, Plus, Upload, CalendarDays } from "lucide-react";
import { toast } from "sonner";
import SchedulerGrid from "@/components/scheduler/SchedulerGrid";
import GanttChart from "@/components/scheduler/GanttChart";
import { Button } from "@/components/ui/button";

export default function ProjectSchedulerPage() {
    const { activeProject } = useProjectStore();
    const [tasks, setTasks] = useState<any[]>([]);
    const [projectStart, setProjectStart] = useState("01-01-26");
    const [loading, setLoading] = useState(false);
    const [calculating, setCalculating] = useState(false);
    const [verification, setVerification] = useState<any>(null);
    const [exporting, setExporting] = useState(false);
    const [importing, setImporting] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);

    // 1. Initial Load
    useEffect(() => {
        if (activeProject?.project_id) {
            loadSchedule();
        }
    }, [activeProject?.project_id]);

    const loadSchedule = async () => {
        if (!activeProject) return;
        setLoading(true);
        try {
            const res = await schedulerApi.load(activeProject.project_id);
            if (res.tasks && res.tasks.length > 0) {
                setTasks(res.tasks);
                if (res.project_start) setProjectStart(res.project_start);
            } else {
                // Default mock if none exists
                setTasks([
                    { id: "T1", name: "Site Mobilization", duration: 5, start: "01-01-26", finish: "06-01-26", predecessors: [], cost: 50000, percentComplete: 0, actualStart: null, actualFinish: null },
                    { id: "T2", name: "Excavation", duration: 10, start: "", finish: "", predecessors: ["T1"], cost: 200000, percentComplete: 0, actualStart: null, actualFinish: null }
                ]);
            }
        } catch (e) {
            toast.error("Failed to load schedule");
        } finally {
            setLoading(false);
        }
    };

    // 2. Orchestration trigger (Calculate)
    const handleCalculate = async () => {
        if (!activeProject) return;
        setCalculating(true);
        try {
            const res = await schedulerApi.calculate(activeProject.project_id, tasks, projectStart);
            setTasks(res.tasks);
            setVerification(res.verification);
            toast.success("Schedule calculated using Layer 3 engine");

            if (res.verification && !res.verification.is_aligned) {
                toast.warning(`Budget Mismatch: Scheduled ₹${(res.total_scheduled_cost ?? 0).toLocaleString('en-IN')} exceeds Work Orders ₹${(res.verification.baseline ?? 0).toLocaleString('en-IN')}`);
            }
        } catch (e: any) {
            const reviewErrors = e.response?.data?.detail?.review_errors;
            if (reviewErrors) {
                reviewErrors.forEach((err: string) => toast.error(`Intelligence Review: ${err}`));
            } else {
                toast.error("Calculation failed. Check logs in .tmp/execution_logs/");
            }
        } finally {
            setCalculating(false);
        }
    };

    // 3. Save State
    const handleSave = async () => {
        if (!activeProject) return;
        try {
            const totalCost = tasks.reduce((sum, t) => sum + (parseFloat(t.cost) || 0), 0);
            await schedulerApi.save(activeProject.project_id, tasks, projectStart, totalCost);
            toast.success("Schedule state persisted to MongoDB");
        } catch (e) {
            toast.error("Save failed");
        }
    };

    // 5. Add Task
    const handleAddTask = () => {
        // Generate ID based on max existing ID, not array length (prevents duplicates after delete)
        const maxId = tasks.length === 0 ? 0 : Math.max(...tasks.map(t => {
            const match = t.id.match(/T(\d+)/);
            return match ? parseInt(match[1]) : 0;
        }));
        const newId = `T${maxId + 1}`;
        const newTask = {
            id: newId,
            name: "New Task",
            duration: 1,
            start: tasks.length > 0 ? "" : projectStart,
            finish: "",
            predecessors: [],
            cost: 0,
            percentComplete: 0,
            actualStart: null,
            actualFinish: null,
            baselineStart: null,
            baselineFinish: null,
            isMilestone: false
        };
        setTasks([...tasks, newTask]);
        toast.info(`Added task ${newId}`);
    };

    // 6. Import Schedule (MPP/XML/PDF)
    const handleImportSchedule = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file || !activeProject) return;

        setImporting(true);
        const formData = new FormData();
        formData.append("file", file);

        try {
            // Using a dynamic endpoint for import
            const res = await schedulerApi.importMpp(activeProject.project_id, formData);
            if (res.tasks) {
                setTasks(res.tasks);
                if (res.project_start) setProjectStart(res.project_start);
                toast.success(`Imported ${res.tasks.length} tasks from ${file.name}`);
                if (res.warning) {
                    toast.info(res.warning);
                }
            }
        } catch (e) {
            toast.error("Failed to import schedule file. Ensure the file is valid and backend support is active.");
        } finally {
            setImporting(false);
            if (fileInputRef.current) fileInputRef.current.value = "";
        }
    };

    // 4. Export trigger
    const handleExport = async () => {
        if (!activeProject) return;
        setExporting(true);
        try {
            await schedulerApi.exportPdf(activeProject.project_id);
            toast.info("PDF Export triggered via Headless Browser Pattern");
            // In a real app we'd poll status
        } catch (e) {
            toast.error("Export failed");
        } finally {
            setExporting(false);
        }
    };

    if (!activeProject) {
        return (
            <div className="flex items-center justify-center min-h-[500px]">
                <div className="empty-state-luxury max-w-sm">
                    <div className="empty-state-luxury-icon">
                        <CalendarDays size={32} />
                    </div>
                    <h3 className="empty-state-luxury-title">No Project Context</h3>
                    <p className="empty-state-luxury-desc">Select an operational project to access the Scheduler and path calculation engine.</p>
                </div>
            </div>
        );
    }

    return (
        <div className="max-w-[1600px] mx-auto space-y-8 pb-20 animate-in fade-in duration-700">
            {/* Header & Controls */}
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6 glass-panel-luxury p-8 rounded-[36px] border border-white/5 shadow-xl">
                <div>
                    <h1 className="text-3xl font-black text-white tracking-tight leading-none italic uppercase">Project Scheduler</h1>
                    <p className="text-slate-500 text-[10px] font-bold uppercase tracking-[0.3em] mt-3">MSP-Style Timeline & Financial Forecaster</p>
                </div>

                <div className="flex items-center gap-3">
                    <div className="bg-slate-950/50 border border-white/5 px-4 py-2 rounded-2xl flex items-center gap-3">
                        <span className="text-[10px] font-black text-slate-500 uppercase">Starts</span>
                        <input
                            value={projectStart}
                            onChange={(e) => setProjectStart(e.target.value)}
                            className="bg-transparent text-white text-xs font-bold outline-none w-20 border-b border-transparent focus:border-accent transition-all"
                        />
                    </div>

                    <input
                        type="file"
                        ref={fileInputRef}
                        className="hidden"
                        accept=".mpp,.xml,.pdf"
                        onChange={handleImportSchedule}
                    />

                    <Button
                        onClick={handleAddTask}
                        variant="secondary"
                        className="rounded-2xl bg-white/5 border-white/10 text-white font-bold hover:bg-white/10"
                    >
                        <Plus size={16} /> Add Task
                    </Button>

                    <Button
                        onClick={() => fileInputRef.current?.click()}
                        variant="outline"
                        disabled={importing}
                        className="rounded-2xl bg-white/5 border-white/10 text-white font-bold hover:bg-white/10"
                        title="Import schedule from XML (MSPDI), MPP, or PDF file"
                    >
                        <Upload size={16} className={`${importing ? 'animate-bounce' : ''}`} />
                        {importing ? 'Importing...' : 'Import Schedule'}
                    </Button>

                    <Button
                        onClick={handleCalculate}
                        disabled={calculating}
                        className="rounded-2xl bg-accent hover:opacity-90 px-6 font-bold"
                    >
                        <Play size={16} className={`${calculating ? 'animate-spin' : ''}`} />
                        {calculating ? 'Calculating Path...' : 'Calculate CPM'}
                    </Button>

                    <Button onClick={handleSave} variant="outline" className="rounded-2xl bg-white/5 border-white/10 text-white font-bold">
                        <Save size={16} /> Save
                    </Button>

                    <Button onClick={handleExport} variant="outline" disabled={exporting} className="rounded-2xl bg-white/5 border-white/10 text-white font-bold hover:bg-white/10">
                        <FileDown size={16} /> Export PDF
                    </Button>
                </div>
            </div>

            {/* Main Layout */}
            <div className="grid grid-cols-1 gap-8">
                {/* Interactive Grid */}
                <div className="space-y-4">
                    <div className="flex items-center justify-between px-2">
                        <h2 className="text-xs font-black uppercase tracking-[0.2em] text-white/40">Baseline Construction Grid</h2>
                        {verification && (
                            <div className={`flex items-center gap-2 text-[10px] font-black uppercase tracking-widest px-3 py-1 rounded-full border ${verification.is_aligned ? 'text-emerald-400 bg-emerald-400/5 border-emerald-400/20' : 'text-rose-400 bg-rose-400/5 border-rose-400/20'}`}>
                                {verification.is_aligned ? <CheckCircle size={12} /> : <AlertTriangle size={12} />}
                                Financial Alignment: {verification.is_aligned ? 'Verified' : `Delta ₹${(verification.difference ?? 0).toLocaleString('en-IN')}`}
                            </div>
                        )}
                    </div>
                    <SchedulerGrid tasks={tasks} onTasksChange={setTasks} />
                </div>

                {/* Gantt Visualization */}
                <div className="space-y-4">
                    <h2 className="text-xs font-black uppercase tracking-[0.2em] text-white/40">Gantt Visual Flow</h2>
                    <GanttChart tasks={tasks.filter(t => t.start && t.finish)} />
                </div>
            </div>

            {/* Self-Annealing Status (Layer 1 Directive Info) */}
            <div className="glass-panel-luxury p-6 rounded-3xl border border-white/5 flex items-center gap-6">
                <div className="p-3 rounded-2xl bg-orange-500/10 text-orange-500">
                    <Info size={24} />
                </div>
                <div>
                    <p className="text-white text-xs font-bold uppercase tracking-widest">Active SOP Directives</p>
                    <p className="text-slate-500 text-[10px] mt-1">6-Day Work Weeks enforced. Finish-to-Start (FS) links only. Cross-referenced with issued Work Orders.</p>
                </div>
            </div>
        </div>
    );
}
