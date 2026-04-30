"use client";

import React, { useState, useMemo } from "react";
import { format, startOfMonth, endOfMonth, startOfWeek, endOfWeek, eachDayOfInterval, isSameMonth, addMonths, subMonths, isToday } from "date-fns";
import { ChevronLeft, ChevronRight, Settings, AlertCircle, Calendar as CalendarIcon, Plus, X } from "lucide-react";
import { useScheduleStore } from "@/store/useScheduleStore";
import type { ScheduleTask } from "@/types/schedule.types";
import { GlassCard } from "@/components/ui/GlassCard";
import { Button } from "@/components/ui/button";
import * as Dialog from "@radix-ui/react-dialog";

export default function SchedulerCalendarView({ 
  onOpenSettings, 
  onDateClick,
  hideSettings = false,
  compact = false
}: { 
  onOpenSettings?: () => void;
  onDateClick?: (date: Date) => void;
  hideSettings?: boolean;
  compact?: boolean;
}) {
  const [currentDate, setCurrentDate] = useState(new Date());
  const [selectedDay, setSelectedDay] = useState<{ date: Date; tasks: ScheduleTask[] } | null>(null);
  
  const projectCalendar = useScheduleStore((state) => state.projectCalendar);
  const taskMap = useScheduleStore((state) => state.taskMap);

  const monthStart = startOfMonth(currentDate);
  const monthEnd = endOfMonth(monthStart);
  const startDate = startOfWeek(monthStart);
  const endDate = endOfWeek(monthEnd);

  const calendarDays = useMemo(() => eachDayOfInterval({ start: startDate, end: endDate }), [startDate, endDate]);

  const tasksByDay = useMemo(() => {
    const map = new Map<string, ScheduleTask[]>();
    Object.values(taskMap).forEach(task => {
      if (!task.scheduled_start) return;
      const dateKey = typeof task.scheduled_start === 'string' 
        ? task.scheduled_start.split('T')[0] 
        : task.scheduled_start;
      if (!map.has(dateKey)) map.set(dateKey, []);
      map.get(dateKey)?.push(task);
    });
    return map;
  }, [taskMap]);

  const nextMonth = () => setCurrentDate(addMonths(currentDate, 1));
  const prevMonth = () => setCurrentDate(subMonths(currentDate, 1));

  return (
    <div className={compact ? "h-full flex flex-col" : "space-y-6"}>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-4">
          {!compact && (
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-orange-500/10 text-orange-500 border border-orange-500/20">
              <CalendarIcon size={24} />
            </div>
          )}
          <div>
            <h2 className={`${compact ? 'text-sm' : 'text-xl'} font-black uppercase tracking-tight text-slate-900 dark:text-white`}>
              {format(currentDate, "MMMM yyyy")}
            </h2>
            {!compact && (
              <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">
                Project Working Calendar & Milestones
              </p>
            )}
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center rounded-xl bg-slate-100 dark:bg-white/5 border border-slate-200 dark:border-white/10 p-1">
            <Button variant="ghost" size="icon" onClick={prevMonth} className="h-8 w-8 rounded-lg">
              <ChevronLeft size={16} />
            </Button>
            <Button variant="ghost" size="sm" onClick={() => setCurrentDate(new Date())} className="px-3 text-[10px] font-black uppercase">
              Today
            </Button>
            <Button variant="ghost" size="icon" onClick={nextMonth} className="h-8 w-8 rounded-lg">
              <ChevronRight size={16} />
            </Button>
          </div>
          
          {!hideSettings && onOpenSettings && (
            <Button 
              onClick={onOpenSettings}
              className="h-10 rounded-xl border border-orange-500/30 bg-orange-500/10 text-orange-600 dark:text-orange-400 hover:bg-orange-500/20 font-bold uppercase tracking-widest text-[10px]"
            >
              <Settings size={14} className="mr-2" />
              Calendar Settings
            </Button>
          )}
        </div>
      </div>

      <GlassCard className={`border-slate-200 dark:border-white/5 bg-white/50 dark:bg-slate-950/50 backdrop-blur-xl ${compact ? 'flex-1 overflow-hidden' : ''}`}>
        <div className="overflow-x-auto custom-scrollbar">
          <div className={`min-w-[700px] ${compact ? 'h-full flex flex-col' : ''}`}>
            <div className="grid grid-cols-7 border-b border-slate-200 dark:border-white/5 bg-slate-50/50 dark:bg-white/[0.02]">
              {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map(day => (
                <div key={day} className="py-3 text-center text-[10px] font-black uppercase tracking-[0.2em] text-slate-500">
                  {day[0]}
                </div>
              ))}
            </div>

            <div className={`grid grid-cols-7 ${compact ? 'flex-1 auto-rows-fr' : 'auto-rows-[120px]'}`}>
              {calendarDays.map((day, i) => {
                const dateKey = format(day, "yyyy-MM-dd");
                const dayTasks = tasksByDay.get(dateKey) || [];
                const isSelectedMonth = isSameMonth(day, monthStart);
                const isTodayDate = isToday(day);
                
                const exception = projectCalendar?.exceptions.find(ex => dateKey >= ex.start_date && dateKey <= ex.end_date);
                // Correctly map JS getDay() (0=Sun) to projectCalendar indexing if needed, 
                // but usually working_days is [1,2,3,4,5] for Mon-Fri.
                const isNonWorking = projectCalendar && !projectCalendar.working_days.includes(day.getDay());

                const visibleLimit = compact ? 1 : 2;

                return (
                  <div 
                    key={i} 
                    className={`relative border-b border-r border-slate-200 dark:border-white/5 p-2 transition-colors group/day ${
                      onDateClick && isSelectedMonth ? 'cursor-pointer active:scale-[0.98]' : ''
                    } ${
                      !isSelectedMonth ? 'bg-slate-50/50 dark:bg-black/20 opacity-40' : 
                      exception || isNonWorking ? 'bg-rose-500/[0.02] dark:bg-rose-500/[0.04]' : 
                      'hover:bg-slate-100/50 dark:hover:bg-white/[0.02]'
                    }`}
                    onClick={() => {
                      if (isSelectedMonth) onDateClick?.(day);
                    }}
                  >
                    <div className="flex items-start justify-between">
                      <span className={`text-[11px] font-black ${isTodayDate && isSelectedMonth ? 'flex h-6 w-6 items-center justify-center rounded-full bg-orange-600 text-white shadow-lg shadow-orange-500/40' : isSelectedMonth ? 'text-slate-900 dark:text-white' : 'text-slate-400'}`}>
                        {format(day, "d")}
                      </span>
                      
                      {exception ? (
                        <div className="rounded-full bg-rose-500/10 p-1 text-rose-500" title={exception.reason}>
                          <AlertCircle size={10} />
                        </div>
                      ) : onDateClick && isSelectedMonth && (
                        <div className="opacity-0 group-hover/day:opacity-100 transition-opacity">
                          <div className="h-4 w-4 rounded-md bg-orange-500/10 flex items-center justify-center text-orange-500">
                            <Plus size={10} />
                          </div>
                        </div>
                      )}
                    </div>

                    <div className={`mt-2 space-y-1 overflow-hidden ${compact ? 'hidden sm:block' : ''}`}>
                      {dayTasks.slice(0, visibleLimit).map(task => (
                        <div 
                          key={task.task_id} 
                          onClick={(e) => {
                            e.stopPropagation();
                            useScheduleStore.getState().openTaskModal(task.task_id);
                          }}
                          className={`truncate rounded-md px-2 py-1 text-[8px] font-black uppercase tracking-wider cursor-pointer hover:brightness-110 active:scale-95 transition-all shadow-sm ${
                            task.is_critical ? 'bg-rose-500 text-white border border-rose-400/50' : 
                            task.is_milestone ? 'bg-slate-900 dark:bg-white text-white dark:text-slate-900 border border-slate-700' :
                            'bg-sky-500/10 text-sky-600 border border-sky-500/20'
                          }`}
                        >
                          {task.task_name}
                        </div>
                      ))}
                      {dayTasks.length > visibleLimit && (
                        <button 
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedDay({ date: day, tasks: dayTasks });
                          }}
                          className="w-full text-left text-[7px] font-black text-slate-500 hover:text-orange-500 uppercase tracking-widest pl-1 py-1 transition-colors"
                        >
                          + {dayTasks.length - visibleLimit} more items
                        </button>
                      )}
                    </div>

                    {isNonWorking && isSelectedMonth && !exception && (
                      <div className="absolute inset-0 pointer-events-none bg-[repeating-linear-gradient(45deg,transparent,transparent_10px,rgba(0,0,0,0.02)_10px,rgba(0,0,0,0.02)_20px)] dark:bg-[repeating-linear-gradient(45deg,transparent,transparent_10px,rgba(255,255,255,0.02)_10px,rgba(255,255,255,0.02)_20px)]" />
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </GlassCard>

      <Dialog.Root open={!!selectedDay} onOpenChange={(open) => !open && setSelectedDay(null)}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 z-[100] bg-black/60 backdrop-blur-sm animate-in fade-in duration-300" />
          <Dialog.Content className="fixed left-1/2 top-1/2 z-[101] w-full max-w-md -translate-x-1/2 -translate-y-1/2 bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl animate-in zoom-in-95 duration-300">
            <div className="flex items-center justify-between mb-6">
              <div>
                <Dialog.Title className="text-xl font-black uppercase tracking-tight text-white">
                  {selectedDay ? format(selectedDay.date, "MMMM do, yyyy") : ""}
                </Dialog.Title>
                <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500 mt-1">
                  Scheduled Tasks & Milestones
                </p>
              </div>
              <Dialog.Close asChild>
                <button className="p-2 hover:bg-white/5 rounded-xl text-slate-400 hover:text-white transition-colors">
                  <X size={20} />
                </button>
              </Dialog.Close>
            </div>

            <div className="space-y-3 max-h-[60vh] overflow-y-auto pr-2 custom-scrollbar">
              {selectedDay?.tasks.map(task => (
                <div 
                  key={task.task_id}
                  onClick={() => {
                    useScheduleStore.getState().openTaskModal(task.task_id);
                    setSelectedDay(null);
                  }}
                  className={`flex items-center justify-between p-4 rounded-xl border cursor-pointer hover:scale-[1.02] active:scale-[0.98] transition-all ${
                    task.is_critical ? 'bg-rose-500/10 border-rose-500/30 text-rose-500' : 
                    task.is_milestone ? 'bg-white/5 border-white/10 text-white' :
                    'bg-sky-500/10 border-sky-500/30 text-sky-400'
                  }`}
                >
                  <div className="min-w-0 flex-1">
                    <p className="text-xs font-black uppercase tracking-wider truncate">{task.task_name}</p>
                    <p className="text-[9px] font-bold text-slate-500 mt-1 uppercase tracking-[0.2em]">{task.wbs_code || task.task_id}</p>
                  </div>
                  <div className="ml-4 px-2 py-1 rounded bg-black/20 text-[9px] font-black">
                    {task.percent_complete}%
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-8">
               <Button 
                onClick={() => {
                  if (selectedDay) onDateClick?.(selectedDay.date);
                  setSelectedDay(null);
                }}
                className="w-full h-12 rounded-xl bg-orange-600 hover:bg-orange-500 text-white font-black uppercase tracking-widest text-[11px] shadow-lg shadow-orange-500/20"
              >
                <Plus size={16} className="mr-2" />
                Add New Item to this Date
              </Button>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>

      {!compact && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <GlassCard className="p-4 flex items-center gap-4 border-emerald-500/20 bg-emerald-500/5">
            <div className="w-2 h-2 rounded-full bg-emerald-500" />
            <div className="text-[10px] font-black uppercase tracking-widest text-emerald-600">
              {Object.values(taskMap).filter(t => (t.percent_complete || 0) === 100).length} Completed Tasks
            </div>
          </GlassCard>
          <GlassCard className="p-4 flex items-center gap-4 border-rose-500/20 bg-rose-500/5">
            <div className="w-2 h-2 rounded-full bg-rose-500 shadow-[0_0_8px_rgba(239,68,68,0.5)]" />
            <div className="text-[10px] font-black uppercase tracking-widest text-rose-500">
              {Object.values(taskMap).filter(t => t.is_critical && (t.percent_complete || 0) < 100).length} Critical Path Tasks
            </div>
          </GlassCard>
          <GlassCard className="p-4 flex items-center gap-4 border-slate-500/20 bg-slate-500/5">
            <div className="w-2 h-2 rounded-full bg-slate-900 dark:bg-white" />
            <div className="text-[10px] font-black uppercase tracking-widest text-slate-500">
              {Object.values(taskMap).filter(t => !!t.is_milestone).length} Project Milestones
            </div>
          </GlassCard>
        </div>
      )}
    </div>
  );
}
