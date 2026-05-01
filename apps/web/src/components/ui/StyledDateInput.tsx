"use client";

import React, { useState, useEffect } from "react";
import { Calendar } from "lucide-react";
import { cn } from "@/lib/utils";

interface StyledDateInputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'onChange'> {
    label?: string;
    containerClassName?: string;
    hideIcon?: boolean;
    onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void;
}

export function StyledDateInput({
    label,
    className,
    containerClassName,
    hideIcon = false,
    value,
    onChange,
    ...props
}: StyledDateInputProps) {
    // Internal state to handle display format (dd-mm-yyyy) while parent uses yyyy-mm-dd
    const [displayValue, setDisplayValue] = useState("");
    const [isInvalid, setIsInvalid] = useState(false);

    // Sync from parent (yyyy-mm-dd -> dd-mm-yyyy)
    useEffect(() => {
        if (!value || typeof value !== "string") {
            setDisplayValue("");
            return;
        }

        // If it's already in yyyy-mm-dd format, convert for display
        if (/^\d{4}-\d{2}-\d{2}/.test(value)) {
            const [y, m, d] = value.split("-");
            setDisplayValue(`${d}-${m}-${y}`);
        } else {
            setDisplayValue(value);
        }
    }, [value]);

    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const val = e.target.value;
        setDisplayValue(val);

        // Validate dd-mm-yyyy
        const dateRegex = /^(\d{1,2})-(\d{1,2})-(\d{4})$/;
        const match = val.match(dateRegex);

        if (match) {
            const [_, d, m, y] = match;
            const isoValue = `${y}-${m.padStart(2, '0')}-${d.padStart(2, '0')}`;
            setIsInvalid(false);

            if (onChange) {
                // Create a synthetic event
                const syntheticEvent = {
                    ...e,
                    target: {
                        ...e.target,
                        value: isoValue,
                        name: props.name || ""
                    }
                } as React.ChangeEvent<HTMLInputElement>;
                onChange(syntheticEvent);
            }
        } else if (val === "") {
            setIsInvalid(false);
            if (onChange) onChange(e);
        } else {
            // Keep as is but mark as invalid for UI
            setIsInvalid(true);
        }
    };

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
                        className={cn(
                            "absolute left-3 transition-colors pointer-events-none z-10",
                            isInvalid ? "text-red-500" : "text-zinc-400 dark:text-slate-500 group-focus-within:text-orange-500"
                        )}
                    />
                )}
                <input
                    type="text"
                    value={displayValue}
                    onChange={handleInputChange}
                    placeholder="dd-mm-yyyy"
                    className={cn(
                        "w-full bg-white dark:bg-slate-950 border rounded-xl px-3 py-2 text-sm text-zinc-900 dark:text-white focus:outline-none transition-all",
                        isInvalid 
                            ? "border-red-500/50 bg-red-500/5 focus:border-red-500" 
                            : "border-zinc-200 dark:border-slate-800 focus:border-orange-500/50",
                        !hideIcon && "pl-9",
                        className
                    )}
                    {...props}
                />
                {isInvalid && (
                    <span className="absolute right-3 text-[9px] font-bold text-red-500 uppercase tracking-tighter">
                        Invalid Format
                    </span>
                )}
            </div>
        </div>
    );
}
