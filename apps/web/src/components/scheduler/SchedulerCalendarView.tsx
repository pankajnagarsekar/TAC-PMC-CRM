"use client";

import React, { useState, useMemo } from "react";
import { format, startOfMonth, endOfMonth, startOfWeek, endOfWeek, eachDayOfInterval, isSameMonth, addMonths, subMonths, isToday } from "date-fns";
import { ChevronLeft, ChevronRight, Settings, AlertCircle, Calendar as CalendarIcon } from "lucide-react";
import { useScheduleStore } from "@/store/useScheduleStore";
import { GlassCard } from "@/components/ui/GlassCard";
import { Button } from "@/components/ui/button";

export default function SchedulerCalendarView({ onOpenSettings }: { onOpenSettings: () => void }) {
  const [currentDate, setCurrentDate] = useState(new Date());
  const projectCalendar = useScheduleStore((state) => state.projectCalendar);
  const taskMap = useScheduleStore((state) => state.taskMap);

  const monthStart = startOfMonth(currentDate);
  const monthEnd = endOfMonth(monthStart);
  const startDate = startOfWeek(monthStart);
  const endDate = endOfWeek(monthEnd);

  const calendarDays = useMemo(() => eachDayOfInterval({ start: startDate, end: endDate }), [startDate, endDate]);

  const tasksByDay = useMemo(() => {
    const map = new Map<string, any[]>();
    Object.values(taskMap).forEach(task => {
      if (!task.scheduled_start) return;
      const dateKey = task.scheduled_start; // Simple start-date mapping for now
      if (!map.has(dateKey)) map.set(dateKey, []);
      map.get(dateKey)?.push(task);
    });
    return map;
  }, [taskMap]);

  const nextMonth = () => setCurrentDate(addMonths(currentDate, 1));
  const prevMonth = () => setCurrentDate(subMonths(currentDate, 1));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-orange-500/10 text-orange-500 border border-orange-500/20">
            <CalendarIcon size={24} />
          </div>
          <div>
            <h2 className="text-xl font-black uppercase tracking-tight text-slate-900 dark:text-white">
              {format(currentDate, "MMMM yyyy")}
            </h2>
            <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">
              Project Working Calendar & Milestones
            </p>
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
          
          <Button 
            onClick={onOpenSettings}
            className="h-10 rounded-xl border border-orange-500/30 bg-orange-500/10 text-orange-600 dark:text-orange-400 hover:bg-orange-500/20 font-bold uppercase tracking-widest text-[10px]"
          >
            <Settings size={14} className="mr-2" />
            Calendar Settings
          </Button>
        </div>
      </div>

      <GlassCard className="overflow-hidden border-slate-200 dark:border-white/5 bg-white/50 dark:bg-slate-950/50 backdrop-blur-xl">
        <div className="grid grid-cols-7 border-b border-slate-200 dark:border-white/5 bg-slate-50/50 dark:bg-white/[0.02]">
          {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map(day => (
            <div key={day} className="py-3 text-center text-[10px] font-black uppercase tracking-[0.2em] text-slate-500">
              {day}
            </div>
          ))}
        </div>

        <div className="grid grid-cols-7 auto-rows-[120px]">
          {calendarDays.map((day, i) => {
            const dateKey = format(day, "yyyy-MM-dd");
            const dayTasks = tasksByDay.get(dateKey) || [];
            const isSelectedMonth = isSameMonth(day, monthStart);
            const isTodayDate = isToday(day);
            
            const exception = projectCalendar?.exceptions.find(ex => dateKey >= ex.start_date && dateKey <= ex.end_date);
            const isNonWorking = projectCalendar && !projectCalendar.working_days.includes(day.getDay());

            return (
              <div 
                key={i} 
                className={`relative border-b border-r border-slate-200 dark:border-white/5 p-2 transition-colors ${
                  !isSelectedMonth ? 'bg-slate-50/50 dark:bg-black/20 opacity-40' : 
                  exception || isNonWorking ? 'bg-rose-500/[0.02] dark:bg-rose-500/[0.04]' : 
                  'hover:bg-slate-100/50 dark:hover:bg-white/[0.02]'
                }`}
              >
                <div className="flex items-start justify-between">
                  <span className={`text-[11px] font-black ${isTodayDate ? 'flex h-6 w-6 items-center justify-center rounded-full bg-orange-600 text-white shadow-lg shadow-orange-500/40' : isSelectedMonth ? 'text-slate-900 dark:text-white' : 'text-slate-400'}`}>
                    {format(day, "d")}
                  </span>
                  
                  {exception && (
                    <div className="rounded-full bg-rose-500/10 p-1 text-rose-500" title={exception.reason}>
                      <AlertCircle size={10} />
                    </div>
                  )}
                </div>

                <div className="mt-2 space-y-1 overflow-hidden">
                  {dayTasks.slice(0, 3).map(task => (
                    <div 
                      key={task.task_id} 
                      className={`truncate rounded-sm px-1.5 py-0.5 text-[8px] font-bold uppercase tracking-wider ${
                        task.is_critical ? 'bg-rose-500/20 text-rose-600 border-l-2 border-rose-500' : 
                        task.is_milestone ? 'bg-slate-900 dark:bg-white text-white dark:text-slate-900' :
                        'bg-sky-500/10 text-sky-600 border-l-2 border-sky-400'
                      }`}
                    >
                      {task.task_name}
                    </div>
                  ))}
                  {dayTasks.length > 3 && (
                    <div className="text-[7px] font-black text-slate-500 uppercase tracking-widest pl-1">
                      + {dayTasks.length - 3} more
                    </div>
                  )}
                </div>

                {isNonWorking && isSelectedMonth && !exception && (
                  <div className="absolute inset-0 pointer-events-none bg-[repeating-linear-gradient(45deg,transparent,transparent_10px,rgba(0,0,0,0.02)_10px,rgba(0,0,0,0.02)_20px)] dark:bg-[repeating-linear-gradient(45deg,transparent,transparent_10px,rgba(255,255,255,0.02)_10px,rgba(255,255,255,0.02)_20px)]" />
                )}
              </div>
            );
          })}
        </div>
      </GlassCard>

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
    </div>
  );
}
