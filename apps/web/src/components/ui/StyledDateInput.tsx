"use client";

import React from "react";
import { Calendar } from "lucide-react";
import { cn } from "@/lib/utils";

interface StyledDateInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
    label?: string;
    containerClassName?: string;
    hideIcon?: boolean;
}

export function StyledDateInput({
    label,
    className,
    containerClassName,
    hideIcon = false,
    ...props
}: StyledDateInputProps) {
    return (
        <div className={cn("flex flex-col gap-1.5", containerClassName)}>
            {label && (
                <label className="text-[10px] font-black uppercase tracking-widest text-zinc-500 dark:text-slate-500 ml-1">
                    {label}
                </label>
            )}
            <div className="group relative flex items-center">
                {!hideIcon && (
                    <Calendar
                        size={14}
                        className="absolute left-3 text-zinc-400 dark:text-slate-500 group-focus-within:text-orange-500 transition-colors pointer-events-none z-10"
                    />
                )}
                <input
                    type="date"
                    className={cn(
                        "w-full bg-white dark:bg-slate-950 border border-zinc-200 dark:border-slate-800 rounded-xl px-3 py-2 text-sm text-zinc-900 dark:text-white focus:outline-none focus:border-orange-500/50 transition-all cursor-pointer",
                        !hideIcon && "pl-9",
                        "appearance-none", // Remove default styles
                        className
                    )}
                    {...props}
                />
                <style jsx>{`
          input[type="date"]::-webkit-calendar-picker-indicator {
            background: transparent;
            bottom: 0;
            color: transparent;
            cursor: pointer;
            height: auto;
            left: 0;
            position: absolute;
            right: 0;
            top: 0;
            width: auto;
          }
        `}</style>
            </div>
        </div>
    );
}
