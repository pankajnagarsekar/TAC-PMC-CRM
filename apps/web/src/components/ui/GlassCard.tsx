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
                "rounded-[2rem] p-6 transition-all duration-300",
                variant === 'glass' && "bg-[var(--glass-background)] backdrop-blur-[var(--glass-blur)] border border-[var(--glass-border)] shadow-[var(--glass-shadow)]",
                variant === 'dark' && "bg-card border border-border shadow-2xl",
                variant === 'light' && "bg-white border border-border shadow-lg",
                className
            )}
            {...props}
        >
            {children}
        </div>
    );
}
