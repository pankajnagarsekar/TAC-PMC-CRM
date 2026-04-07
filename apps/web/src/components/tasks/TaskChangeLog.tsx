import React from "react";
import { formatDistanceToNow } from "date-fns";
import { History, User, Clock, AlertCircle } from "lucide-react";

interface AuditLog {
  action: string;
  timestamp: string;
  user: string;
  detail: string;
}

interface TaskChangeLogProps {
  logs: AuditLog[];
}

export default function TaskChangeLog({ logs }: TaskChangeLogProps) {
  if (!logs || logs.length === 0) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 text-center">
        <History className="w-8 h-8 text-slate-700 mx-auto mb-3" />
        <p className="text-slate-500 text-sm">No activity logs recorded yet.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-bold text-white flex items-center gap-2 mb-4">
        <History className="text-blue-500" size={20} />
        Activity History
      </h3>
      
      <div className="relative before:absolute before:inset-0 before:ml-5 before:w-0.5 before:bg-slate-800 before:pointer-events-none">
        {logs.map((log, index) => (
          <div key={index} className="relative flex items-start gap-4 mb-6 last:mb-0">
            <div className="flex-shrink-0 w-10 h-10 rounded-full bg-slate-900 border border-slate-800 flex items-center justify-center z-10">
              {log.action.includes("CREATE") ? (
                <Plus size={16} className="text-blue-400" />
              ) : log.action.includes("STATUS") ? (
                <Clock size={16} className="text-amber-400" />
              ) : (
                <AlertCircle size={16} className="text-slate-400" />
              )}
            </div>
            
            <div className="flex-1 pt-1">
              <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-1 mb-1">
                <span className="font-bold text-slate-200 text-sm">
                  {log.action.replace(/_/g, " ")}
                </span>
                <span className="text-[10px] uppercase font-bold text-slate-500 bg-slate-800/50 px-2 py-0.5 rounded border border-slate-700/50">
                  {formatDistanceToNow(new Date(log.timestamp), { addSuffix: true })}
                </span>
              </div>
              
              <div className="flex items-center gap-2 text-xs text-slate-400 mb-2">
                <User size={12} />
                <span>{log.user}</span>
              </div>
              
              {log.detail && (
                <div className="bg-slate-950 border border-slate-800/50 rounded-lg p-3 text-xs">
                   <p className="text-slate-300">
                    {log.detail}
                  </p>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}


import { Plus } from "lucide-react";
