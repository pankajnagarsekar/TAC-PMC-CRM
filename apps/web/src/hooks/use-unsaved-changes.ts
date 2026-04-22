"use client";

import { useEffect } from "react";

/**
 * Hook to warn user about unsaved changes.
 * Currently only handles browser-level events (refresh, tab close)
 * as Next.js App Router does not currently support route interception
 * with confirmation dialogs natively without complex workarounds.
 */
export function useUnsavedChanges(isDirty: boolean) {
    useEffect(() => {
        const handleBeforeUnload = (e: BeforeUnloadEvent) => {
            if (isDirty) {
                e.preventDefault();
                e.returnValue = "";
                return "";
            }
        };

        window.addEventListener("beforeunload", handleBeforeUnload);
        return () => {
            window.removeEventListener("beforeunload", handleBeforeUnload);
        };
    }, [isDirty]);
}
