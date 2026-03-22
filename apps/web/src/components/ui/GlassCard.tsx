import React from 'react';
import { cn } from '@/lib/utils';

interface GlassCardProps extends React.HTMLAttributes<HTMLDivElement> {
    children: React.ReactNode;
    variant?: 'light' | 'dark' | 'glass';
}

export function GlassCard({ children, className, variant = 'glass', ...props }: GlassCardProps) {
    return (
        <div
            className={cn(
                "rounded-[var(--radius)] p-5 transition-all duration-300",
                variant === 'glass' && "bg-[var(--glass-background)] backdrop-blur-[var(--glass-blur)] border border-[var(--glass-border)] shadow-[var(--glass-shadow)]",
                variant === 'dark' && "bg-card border border-border shadow-xl",
                variant === 'light' && "bg-white border border-border shadow-sm",
                className
            )}
            {...props}
        >
            {children}
        </div>
    );
}
