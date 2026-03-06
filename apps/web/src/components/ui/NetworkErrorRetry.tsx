'use client';

import React from 'react';
import { WifiOff, RefreshCw, AlertTriangle } from 'lucide-react';

interface NetworkErrorRetryProps {
  message?: string;
  onRetry: () => void;
  isRetrying?: boolean;
}

/**
 * Component to display when a network request fails, allowing the user to retry.
 * Aligned with Phase 8.7.2 Resilience requirements.
 */
export default function NetworkErrorRetry({ 
  message = "A network error occurred while fetching data.", 
  onRetry, 
  isRetrying = false 
}: NetworkErrorRetryProps) {
  return (
    <div className="flex flex-col items-center justify-center p-8 bg-slate-900/40 backdrop-blur-sm border border-red-500/20 rounded-2xl text-center">
      <div className="w-16 h-16 bg-red-500/10 rounded-full flex items-center justify-center mb-4 text-red-500 border border-red-500/20">
        <WifiOff size={32} />
      </div>
      
      <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2 justify-center">
        <AlertTriangle className="text-orange-500" size={20} /> Connection Lost
      </h3>
      
      <p className="text-slate-400 text-sm mt-2 max-w-xs mx-auto">
        {message} Please check your internet connection and try again.
      </p>
      
      <button
        onClick={onRetry}
        disabled={isRetrying}
        className="mt-6 flex items-center gap-2 px-6 py-2.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-100 rounded-xl font-medium transition-all border border-slate-700 active:scale-95"
      >
        <RefreshCw size={18} className={isRetrying ? 'animate-spin' : ''} />
        {isRetrying ? 'Retrying...' : 'Retry Connection'}
      </button>
    </div>
  );
}
