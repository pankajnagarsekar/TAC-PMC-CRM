import React from 'react';
import { GlassCard } from '@/components/ui/GlassCard';
import { cn } from '@/lib/utils';
import { GripVertical } from 'lucide-react';

interface DashboardWidgetProps extends React.HTMLAttributes<HTMLDivElement> {
  id: string;
  title: string;
  subtitle?: string;
  icon?: React.ReactNode;
  colSpan?: 1 | 2;
  minHeight?: string;       // Default: '400px'
  maxHeight?: string;       // Default: '600px'
  headerAction?: React.ReactNode;
  children: React.ReactNode;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  dragHandleProps?: Record<string, any> | null; // For hello-pangea/dnd drag handles
  isDragging?: boolean;
}

export function DashboardWidget({
  id,
  title,
  subtitle,
  icon,
  colSpan = 1,
  minHeight = '400px',
  maxHeight = '600px',
  headerAction,
  children,
  dragHandleProps,
  isDragging = false,
  className,
  ...props
}: DashboardWidgetProps) {
  return (
    <GlassCard
      id={id}
      className={cn(
        "flex flex-col overflow-hidden border border-border shadow-xl h-full w-full !p-0 transition-shadow transition-transform duration-200",
        isDragging && "dashboard-widget-dragging z-50",
        colSpan === 2 ? "col-span-1 md:col-span-2" : "col-span-1",
        className
      )}
      style={{
        minHeight,
        maxHeight,
        ...props.style,
      }}
      {...props}
    >
      <div className="p-6 md:p-8 h-full flex flex-col">
        {/* Header Block */}
        <div className="flex items-center justify-between mb-5 shrink-0 select-none">
          <div className="flex items-center gap-3">
            {/* Grip Handle for Drag & Drop */}
            {dragHandleProps && (
              <div
                {...dragHandleProps}
                className="p-1 rounded hover:bg-slate-500/10 text-slate-400 hover:text-slate-200 cursor-grab active:cursor-grabbing transition-colors shrink-0 focus:outline-none"
                aria-label={`Drag to reorder ${title}`}
              >
                <GripVertical size={14} className="opacity-60 hover:opacity-100" />
              </div>
            )}

            {/* Icon Wrapper */}
            {icon && (
              <div className="size-8 rounded-lg bg-primary/5 flex items-center justify-center text-primary border border-primary/10 shrink-0">
                {icon}
              </div>
            )}

            {/* Title & Subtitle */}
            <div>
              <h2 className="text-xs font-bold tracking-tight uppercase flex items-center gap-1.5 text-slate-900 dark:text-white">
                {title}
              </h2>
              {subtitle && (
                <p className="text-[8px] text-slate-500 dark:text-zinc-400 uppercase tracking-widest mt-0.5">
                  {subtitle}
                </p>
              )}
            </div>
          </div>

          {/* Optional Action Buttons/Links in Header */}
          {headerAction && (
            <div className="flex items-center gap-3 shrink-0">
              {headerAction}
            </div>
          )}
        </div>

        {/* Content Area */}
        <div className="flex-1 min-h-0 overflow-y-auto custom-scrollbar">
          {children}
        </div>
      </div>
    </GlassCard>
  );
}
