"use client";

import React, { Component, ErrorInfo, ReactNode } from "react";
import { AlertTriangle, RefreshCcw } from "lucide-react";

interface Props {
    children?: ReactNode;
}

interface State {
    hasError: boolean;
    error?: Error;
}

export class ErrorBoundary extends Component<Props, State> {
    public state: State = {
        hasError: false,
    };

    public static getDerivedStateFromError(error: Error): State {
        return { hasError: true, error };
    }

    public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
        console.error("Uncaught error:", error, errorInfo);
    }

    public render() {
        if (this.state.hasError) {
            return (
                <div className="min-h-[400px] flex flex-col items-center justify-center p-6 text-center space-y-6 bg-slate-950/50 border border-red-500/20 rounded-[2.5rem] backdrop-blur-xl">
                    <div className="p-5 bg-red-500/10 rounded-3xl border border-red-500/20">
                        <AlertTriangle className="w-12 h-12 text-red-500" />
                    </div>
                    <div className="space-y-2">
                        <h2 className="text-2xl font-bold text-white tracking-tight">Deployment Sector Compromised</h2>
                        <p className="text-slate-400 max-w-md mx-auto text-sm leading-relaxed">
                            An unexpected structural failure occurred in this module. This is often caused by corrupted data or interface incompatibilities.
                        </p>
                    </div>
                    <button
                        onClick={() => window.location.reload()}
                        className="flex items-center gap-2 px-8 py-3 bg-red-600 hover:bg-red-500 text-white rounded-2xl font-black text-xs uppercase tracking-widest transition-all shadow-xl shadow-red-900/40 active:scale-95"
                    >
                        <RefreshCcw size={14} />
                        Reinitialize System
                    </button>
                    {this.state.error && (
                        <pre className="mt-8 p-4 bg-black/40 border border-white/5 rounded-xl text-[10px] text-slate-600 font-mono text-left max-w-full overflow-auto">
                            ID: {this.state.error.message}
                        </pre>
                    )}
                </div>
            );
        }

        return this.props.children;
    }
}
