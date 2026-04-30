"use client";

import React, { useState, useEffect } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { X, Calendar, Clock, Plus, Trash2, AlertCircle } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { GlassCard } from "@/components/ui/GlassCard";
import { schedulerApi } from "@/lib/api";
import { ProjectCalendar, CalendarException } from "@/types/api";

interface CalendarSettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  projectId: string;
}

export default function CalendarSettingsModal({ isOpen, onClose, projectId }: CalendarSettingsModalProps) {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [calendar, setCalendar] = useState<ProjectCalendar | null>(null);

  useEffect(() => {
    if (isOpen && projectId) {
      loadCalendar();
    }
  }, [isOpen, projectId]);

  const loadCalendar = async () => {
    setLoading(true);
    try {
      const data = await schedulerApi.getCalendar(projectId);
      setCalendar(data);
    } catch (err) {
      console.error("Failed to load calendar:", err);
      // Don't toast here as it might be a new project without a calendar (fallback handled by API)
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!calendar) return;
    setSaving(true);
    try {
      await schedulerApi.updateCalendar(projectId, calendar);
      toast.success("Calendar settings updated. Schedule recalculation triggered.");
      onClose();
      // Reload page or trigger store refresh? 
      // The updateCalendar call on backend already triggers recalculation and saves to DB.
      // We should ideally reload the schedule in the store.
      window.location.reload(); 
    } catch (err) {
      console.error("Failed to update calendar:", err);
      toast.error("Failed to update calendar settings");
    } finally {
      setSaving(false);
    }
  };

  const toggleDay = (day: number) => {
    if (!calendar) return;
    const workingDays = [...calendar.working_days];
    if (workingDays.includes(day)) {
      setCalendar({ ...calendar, working_days: workingDays.filter(d => d !== day) });
    } else {
      setCalendar({ ...calendar, working_days: [...workingDays, day].sort() });
    }
  };

  const addException = () => {
    if (!calendar) return;
    const newException: CalendarException = {
      start_date: new Date().toISOString().split('T')[0],
      end_date: new Date().toISOString().split('T')[0],
      exception_type: "holiday",
      reason: "Public Holiday"
    };
    setCalendar({ ...calendar, exceptions: [...calendar.exceptions, newException] });
  };

  const removeException = (index: number) => {
    if (!calendar) return;
    const exceptions = [...calendar.exceptions];
    exceptions.splice(index, 1);
    setCalendar({ ...calendar, exceptions });
  };

  const updateException = (index: number, field: keyof CalendarException, value: string) => {
    if (!calendar) return;
    const exceptions = [...calendar.exceptions];
    exceptions[index] = { ...exceptions[index], [field]: value };
    setCalendar({ ...calendar, exceptions });
  };

  if (!isOpen) return null;

  const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

  return (
    <Dialog.Root open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-slate-950/60 backdrop-blur-md animate-in fade-in duration-300" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 w-full max-w-2xl -translate-x-1/2 -translate-y-1/2 p-4 outline-none animate-in zoom-in-95 fade-in duration-300">
          <GlassCard className="flex max-h-[92vh] flex-col overflow-hidden border-white/10 shadow-2xl p-0">
            <div className="flex shrink-0 items-center justify-between border-b border-white/10 p-6 bg-slate-900/90 backdrop-blur-xl sticky top-0 z-20">
              <div className="flex items-center gap-4">
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-orange-500/20 text-orange-500 shadow-lg shadow-orange-500/10">
                  <Calendar size={24} />
                </div>
                <div>
                  <Dialog.Title className="text-xl font-black uppercase tracking-tight text-white">Project Calendar</Dialog.Title>
                  <p className="text-xs font-bold uppercase tracking-widest text-slate-400">Configure working days and shift hours</p>
                </div>
              </div>
              <Dialog.Close asChild>
                <button className="rounded-xl p-2 text-slate-400 hover:bg-white/5 hover:text-white transition-all duration-300 hover:rotate-90">
                  <X size={20} />
                </button>
              </Dialog.Close>
            </div>

            <div className="flex-1 overflow-y-auto p-8 space-y-8 custom-scrollbar">
              {loading ? (
                <div className="flex h-40 items-center justify-center animate-pulse">
                  <p className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-500">Syncing calendar data...</p>
                </div>
              ) : calendar && (
                <>
                  {/* Working Days */}
                  <section>
                    <h3 className="mb-4 flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.2em] text-slate-500">
                      Standard Working Week
                    </h3>
                    <div className="flex justify-between gap-2">
                      {days.map((day, idx) => {
                        const isWorking = calendar.working_days.includes(idx);
                        return (
                          <button
                            key={day}
                            onClick={() => toggleDay(idx)}
                            className={`flex h-14 flex-1 flex-col items-center justify-center rounded-2xl border transition-all duration-300 ${
                              isWorking
                                ? "border-orange-500/50 bg-orange-500/10 text-white shadow-lg shadow-orange-500/10"
                                : "border-white/5 bg-white/[0.02] text-slate-500 hover:border-white/10 hover:bg-white/[0.05]"
                            }`}
                          >
                            <span className="text-[10px] font-black uppercase tracking-tighter">{day}</span>
                            <div className={`mt-2 h-1.5 w-1.5 rounded-full ${isWorking ? "bg-orange-500 animate-pulse" : "bg-slate-700"}`} />
                          </button>
                        );
                      })}
                    </div>
                  </section>

                  {/* Shift Hours */}
                  <section className="grid grid-cols-2 gap-8">
                    <div>
                      <h3 className="mb-4 flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.2em] text-slate-500">
                        <Clock size={12} /> Standard Shift
                      </h3>
                      <div className="flex items-center gap-3">
                        <input
                          type="time"
                          value={calendar.shift_start}
                          onChange={(e) => setCalendar({ ...calendar!, shift_start: e.target.value })}
                          className="w-full rounded-xl border border-white/5 bg-white/[0.03] p-3 text-sm font-bold text-white outline-none focus:border-orange-500/50 transition-colors"
                        />
                        <span className="text-slate-600">to</span>
                        <input
                          type="time"
                          value={calendar.shift_end}
                          onChange={(e) => setCalendar({ ...calendar!, shift_end: e.target.value })}
                          className="w-full rounded-xl border border-white/5 bg-white/[0.03] p-3 text-sm font-bold text-white outline-none focus:border-orange-500/50 transition-colors"
                        />
                      </div>
                    </div>
                    <div>
                      <h3 className="mb-4 flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.2em] text-slate-500">
                        Lunch Break
                      </h3>
                      <div className="flex items-center gap-3">
                        <input
                          type="time"
                          value={calendar.lunch_start}
                          onChange={(e) => setCalendar({ ...calendar!, lunch_start: e.target.value })}
                          className="w-full rounded-xl border border-white/5 bg-white/[0.03] p-3 text-sm font-bold text-white outline-none focus:border-orange-500/50 transition-colors"
                        />
                        <span className="text-slate-600">to</span>
                        <input
                          type="time"
                          value={calendar.lunch_end}
                          onChange={(e) => setCalendar({ ...calendar!, lunch_end: e.target.value })}
                          className="w-full rounded-xl border border-white/5 bg-white/[0.03] p-3 text-sm font-bold text-white outline-none focus:border-orange-500/50 transition-colors"
                        />
                      </div>
                    </div>
                  </section>

                  {/* Exceptions */}
                  <section>
                    <div className="mb-4 flex items-center justify-between">
                      <h3 className="flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.2em] text-slate-500">
                        Holidays & Exceptions
                      </h3>
                      <button
                        onClick={addException}
                        className="flex items-center gap-1.5 rounded-lg bg-orange-500/10 px-3 py-1.5 text-[10px] font-black uppercase tracking-widest text-orange-500 hover:bg-orange-500/20 transition-colors"
                      >
                        <Plus size={12} /> Add Holiday
                      </button>
                    </div>
                    
                    <div className="space-y-3">
                      {calendar.exceptions.length === 0 ? (
                        <div className="rounded-2xl border border-dashed border-white/5 bg-white/[0.01] p-8 text-center">
                          <p className="text-xs font-bold text-slate-500">No holidays or exceptions defined.</p>
                        </div>
                      ) : (
                        calendar.exceptions.map((ex, idx) => (
                          <div key={idx} className="flex items-center gap-3 rounded-2xl border border-white/5 bg-white/[0.02] p-4 group hover:bg-white/[0.04] transition-colors">
                            <input
                              type="date"
                              value={ex.start_date}
                              onChange={(e) => updateException(idx, "start_date", e.target.value)}
                              className="flex-1 rounded-lg border border-white/5 bg-slate-900/50 p-2 text-xs font-bold text-white outline-none focus:border-orange-500/30"
                            />
                            <span className="text-slate-600 text-xs">to</span>
                            <input
                              type="date"
                              value={ex.end_date}
                              onChange={(e) => updateException(idx, "end_date", e.target.value)}
                              className="flex-1 rounded-lg border border-white/5 bg-slate-900/50 p-2 text-xs font-bold text-white outline-none focus:border-orange-500/30"
                            />
                            <input
                              type="text"
                              value={ex.reason}
                              placeholder="Reason"
                              onChange={(e) => updateException(idx, "reason", e.target.value)}
                              className="flex-[2] rounded-lg border border-white/5 bg-slate-900/50 p-2 text-xs font-bold text-white outline-none focus:border-orange-500/30"
                            />
                            <button
                              onClick={() => removeException(idx)}
                              className="p-2 text-slate-500 hover:text-rose-500 transition-colors"
                            >
                              <Trash2 size={16} />
                            </button>
                          </div>
                        ))
                      )}
                    </div>
                  </section>
                </>
              )}
            </div>

            <div className="flex shrink-0 items-center justify-between border-t border-white/5 p-6 bg-slate-900/50">
              <div className="flex items-center gap-3 text-orange-400">
                <AlertCircle size={14} />
                <span className="text-[10px] font-bold uppercase tracking-wider">Recalculation will be triggered upon save</span>
              </div>
              <div className="flex gap-4">
                <Button variant="ghost" onClick={onClose} className="text-slate-400 hover:text-white uppercase font-black tracking-widest text-[10px]">
                  Cancel
                </Button>
                <Button
                  onClick={handleSave}
                  disabled={saving || loading}
                  className="rounded-xl bg-orange-600 px-8 font-black uppercase tracking-widest text-white shadow-xl shadow-orange-600/20"
                >
                  {saving ? "Processing..." : "Apply Changes"}
                </Button>
              </div>
            </div>
          </GlassCard>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
