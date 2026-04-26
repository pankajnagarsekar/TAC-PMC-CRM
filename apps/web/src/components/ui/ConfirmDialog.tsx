"use client";

import {
    Dialog,
    DialogContent,
    DialogTitle,
    DialogFooter,
} from "@tac-pmc/ui";
import { AlertCircle, Loader2 } from "lucide-react";

interface ConfirmDialogProps {
    isOpen: boolean;
    onClose: () => void;
    onConfirm: () => void;
    title: string;
    description: string;
    confirmText?: string;
    cancelText?: string;
    isLoading?: boolean;
    variant?: "danger" | "warning" | "info";
}

export default function ConfirmDialog({
    isOpen,
    onClose,
    onConfirm,
    title,
    description,
    confirmText = "Confirm",
    cancelText = "Cancel",
    isLoading = false,
    variant = "info",
}: ConfirmDialogProps) {
    const variantStyles = {
        danger: "bg-rose-600 hover:bg-rose-500 shadow-rose-900/20",
        warning: "bg-amber-600 hover:bg-amber-500 shadow-amber-900/20",
        info: "bg-orange-600 hover:bg-orange-500 shadow-orange-900/20",
    };

    const iconStyles = {
        danger: "text-rose-500",
        warning: "text-amber-500",
        info: "text-orange-500",
    };

    return (
        <Dialog open={isOpen} onOpenChange={onClose}>
            <DialogContent className="max-w-md bg-white dark:bg-slate-950 border border-zinc-200 dark:border-slate-800 text-zinc-900 dark:text-white p-0 overflow-hidden">
                <div className="p-6 space-y-4">
                    <div className="flex items-center gap-3">
                        <div className={`p-2 rounded-full ${variant === 'danger' ? 'bg-rose-500/10' : variant === 'warning' ? 'bg-amber-500/10' : 'bg-orange-500/10'}`}>
                            <AlertCircle className={iconStyles[variant]} size={24} />
                        </div>
                        <DialogTitle className="text-xl font-bold tracking-tight">
                            {title}
                        </DialogTitle>
                    </div>

                    <p className="text-sm text-zinc-500 dark:text-slate-400 leading-relaxed">
                        {description}
                    </p>
                </div>

                <DialogFooter className="bg-zinc-50 dark:bg-slate-900/50 px-6 py-4 border-t border-zinc-200 dark:border-slate-800 flex items-center justify-end gap-3">
                    <button
                        type="button"
                        onClick={onClose}
                        disabled={isLoading}
                        className="px-4 py-2 text-sm font-medium text-zinc-600 dark:text-slate-400 hover:text-zinc-900 dark:hover:text-white transition-colors"
                    >
                        {cancelText}
                    </button>
                    <button
                        type="button"
                        onClick={onConfirm}
                        disabled={isLoading}
                        className={`px-6 py-2 rounded-xl text-sm font-bold text-white transition-all flex items-center gap-2 shadow-lg disabled:opacity-50 ${variantStyles[variant]}`}
                    >
                        {isLoading && <Loader2 className="w-4 h-4 animate-spin" />}
                        {confirmText}
                    </button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
