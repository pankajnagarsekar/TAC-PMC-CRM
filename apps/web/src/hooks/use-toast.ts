import { useCallback, useMemo } from "react";
import { toast as sonnerToast } from "sonner";

export interface ToastProps {
  title?: string;
  description?: string;
  variant?: 'default' | 'destructive';
}

export function useToast() {
  const toast = useCallback((props: ToastProps) => {
    console.log(`[Toast] ${props.title}: ${props.description}`);

    const options = {
      description: props.description,
      duration: 5000,
    };

    if (props.variant === 'destructive') {
      sonnerToast.error(props.title || "Error", options);
    } else {
      sonnerToast.success(props.title || "Success", options);
    }
  }, []);

  return useMemo(() => ({ toast }), [toast]);
}
