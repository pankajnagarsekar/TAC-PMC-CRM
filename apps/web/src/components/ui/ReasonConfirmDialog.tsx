"use client";

import { useState } from "react";
import {
    Dialog,
    DialogContent,
    DialogTitle,
    DialogFooter,
} from "@tac-pmc/ui";
import { AlertCircle, Loader2 } from "lucide-react";

interface ReasonConfirmDialogProps {
    isOpen: boolean;
    onClose: () => void;
    onConfirm: (reason: string) => void;
    title: string;
    description: string;
    confirmText?: string;
    cancelText?: string;
    isLoading?: boolean;
}

export default function ReasonConfirmDialog({
    isOpen,
    onClose,
    onConfirm,
    title,
    description,
    confirmText = "Confirm",
    cancelText = "Cancel",
    isLoading = false,
}: ReasonConfirmDialogProps) {
    const [reason, setReason] = useState("");

    const handleConfirm = () => {
        if (reason.trim().length < 5) return;
        onConfirm(reason);
        setReason("");
    };

    return (
        <Dialog open={isOpen} onOpenChange={onClose}>
            <DialogContent className="max-w-md bg-white dark:bg-slate-950 border border-zinc-200 dark:border-slate-800 text-zinc-900 dark:text-white p-0 overflow-hidden">
                <div className="p-6 space-y-4">
                    <div className="flex items-center gap-3">
                        <div className="p-2 rounded-full bg-orange-500/10">
                            <AlertCircle className="text-orange-500" size={24} />
                        </div>
                        <DialogTitle className="text-xl font-bold tracking-tight">
                            {title}
                        </DialogTitle>
                    </div>

                    <p className="text-sm text-zinc-500 dark:text-slate-400 leading-relaxed">
                        {description}
                    </p>

                    <div className="space-y-2">
                        <label className="text-[10px] font-black uppercase tracking-widest text-zinc-400">
                            Reason for Modification <span className="text-rose-500">*</span>
                        </label>
                        <textarea
                            value={reason}
                            onChange={(e) => setReason(e.target.value)}
                            placeholder="Enter justification (min 5 chars)..."
                            className="w-full min-h-[100px] p-3 rounded-xl bg-zinc-50 dark:bg-slate-900 border border-zinc-200 dark:border-slate-800 text-sm focus:ring-2 focus:ring-orange-500 outline-none transition-all resize-none"
                        />
                        {reason.length > 0 && reason.length < 5 && (
                            <p className="text-[10px] text-rose-500 font-bold">Reason must be at least 5 characters.</p>
                        )}
                    </div>
                </div>

                <DialogFooter className="bg-zinc-50 dark:bg-slate-900/50 px-6 py-4 border-t border-zinc-200 dark:border-slate-800 flex items-center justify-end gap-3">
                    <button
                        type="button"
                        onClick={() => {
                            onClose();
                            setReason("");
                        }}
                        disabled={isLoading}
                        className="px-4 py-2 text-sm font-medium text-zinc-600 dark:text-slate-400 hover:text-zinc-900 dark:hover:text-white transition-colors"
                    >
                        {cancelText}
                    </button>
                    <button
                        type="button"
                        onClick={handleConfirm}
                        disabled={isLoading || reason.trim().length < 5}
                        className="px-6 py-2 rounded-xl text-sm font-bold text-white transition-all flex items-center gap-2 shadow-lg disabled:opacity-50 bg-orange-600 hover:bg-orange-500 shadow-orange-900/20"
                    >
                        {isLoading && <Loader2 className="w-4 h-4 animate-spin" />}
                        {confirmText}
                    </button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
