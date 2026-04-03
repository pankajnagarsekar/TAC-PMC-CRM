"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?:
  | "default"
  | "destructive"
  | "outline"
  | "secondary"
  | "ghost"
  | "link";
  size?: "default" | "sm" | "lg" | "icon";
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "default", size = "default", ...props }, ref) => {
    const baseStyles =
      "inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50";

    const variantStyles = {
      default:
        "bg-orange-600 text-white hover:bg-orange-500 focus-visible:ring-orange-500 shadow-lg shadow-orange-950/20 active:scale-95",
      destructive:
        "bg-destructive text-destructive-foreground hover:bg-destructive/90 focus-visible:ring-destructive active:scale-95",
      outline:
        "border border-border bg-background hover:bg-accent hover:text-accent-foreground focus-visible:ring-ring",
      secondary:
        "bg-secondary text-secondary-foreground hover:bg-secondary/80 focus-visible:ring-ring",
      ghost:
        "hover:bg-accent hover:text-accent-foreground focus-visible:ring-ring",
      link: "text-primary underline-offset-4 hover:underline focus-visible:ring-ring",
    };

    const sizeStyles = {
      default: "h-10 px-4 py-2",
      sm: "h-9 rounded-md px-3",
      lg: "h-11 rounded-md px-8",
      icon: "h-10 w-10",
    };

    return (
      <button
        className={cn(
          baseStyles,
          variantStyles[variant],
          sizeStyles[size],
          className,
        )}
        ref={ref}
        {...props}
      />
    );
  },
);
Button.displayName = "Button";

export { Button };
