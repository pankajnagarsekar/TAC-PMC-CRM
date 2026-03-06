export interface ToastProps {
  title?: string;
  description?: string;
  variant?: 'default' | 'destructive';
}

export function useToast() {
  return {
    toast: (props: ToastProps) => {
      console.log(`[Toast] ${props.title}: ${props.description}`);
      // Fallback for UI visibility during development
      if (props.variant === 'destructive') {
        alert(`${props.title}\n\n${props.description}`);
      }
    }
  };
}
