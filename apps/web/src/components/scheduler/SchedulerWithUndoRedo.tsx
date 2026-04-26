/**
 * SchedulerWithUndoRedo Component
 *
 * Example integration of the undo/redo system with the scheduler grid.
 * Shows how to combine UndoRedoHistory sidebar with the main scheduler interface.
 *
 * Task #16: Frontend Integration for Undo/Redo System
 */

'use client';

import React, { useCallback, useState } from 'react';
import { useProjectStore } from '@/store/projectStore';
import SchedulerGrid from './SchedulerGrid';
import { UndoRedoHistory } from './UndoRedoHistory';
import { useUndoRedo } from '@/hooks/useUndoRedo';

interface SchedulerWithUndoRedoProps {
  projectId?: string;
}

/**
 * Scheduler component with integrated undo/redo system
 *
 * Layout:
 * ┌─────────────────────────────────────────┬──────────────────┐
 * │ Scheduler Grid (tasks, gantt chart)     │ Undo/Redo Sidebar│
 * │                                         │ - History        │
 * │                                         │ - Controls       │
 * │                                         │ - Timeline       │
 * └─────────────────────────────────────────┴──────────────────┘
 */
export const SchedulerWithUndoRedo: React.FC<SchedulerWithUndoRedoProps> = ({
  projectId,
}) => {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const activeProject = useProjectStore((state: any) => state.activeProject);
  const [showError, setShowError] = useState(false);

  const resolvedProjectId = projectId || activeProject?.project_id || null;

  // Setup undo/redo hook
  const {
    history,
    stackInfo,
    isLoading,
    error,
    undo,
    redo,
    restore,
    loadHistory,
    canUndo,
    canRedo,
  } = useUndoRedo(resolvedProjectId);

  // Handle errors
  const handleError = useCallback(
    (err: string) => {
      setShowError(true);
      setTimeout(() => setShowError(false), 5000);
    },
    []
  );

  // Show error alert if undo/redo fails
  if (error && showError) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="w-96 rounded-lg border border-red-300 bg-red-50 dark:border-red-700 dark:bg-red-900/20 p-4 text-sm text-red-700 dark:text-red-300">
          {error}
        </div>
      </div>
    );
  }

  // Required project context
  if (!resolvedProjectId) {
    return (
      <div className="flex items-center justify-center h-screen text-gray-500">
        <div className="text-center">
          <p className="text-lg font-semibold">No project selected</p>
          <p className="text-sm">Please select a project to view the scheduler</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-gray-50 dark:bg-gray-950">
      {/* Main Scheduler Area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Scheduler Grid */}
        <div className="flex-1 overflow-auto">
          <SchedulerGrid />
        </div>

        {/* Keyboard Shortcut Hint (optional) */}
        <div className="px-4 py-2 bg-blue-50 dark:bg-blue-900 border-t border-blue-200 dark:border-blue-800 text-xs text-blue-700 dark:text-blue-200">
          💡 Keyboard shortcuts: <kbd>Ctrl+Z</kbd> undo •{' '}
          <kbd>Ctrl+Shift+Z</kbd> or <kbd>Ctrl+Y</kbd> redo
        </div>
      </div>

      {/* Undo/Redo Sidebar */}
      <div className="hidden lg:block">
        <UndoRedoHistory
          projectId={resolvedProjectId}
          history={history}
          stackInfo={
            stackInfo || {
              can_undo: false,
              can_redo: false,
              current_position: -1,
              total_entries: 0,
              total_reverted: 0,
            }
          }
          onUndo={undo}
          onRedo={redo}
          onRestore={restore}
          isLoading={isLoading}
          onLoadHistory={loadHistory}
        />
      </div>

      {/* Mobile: Undo/Redo Controls (Floating) */}
      <div className="lg:hidden fixed bottom-4 right-4 z-50">
        <div className="flex gap-2 bg-white dark:bg-gray-800 rounded-lg shadow-lg p-2 border border-gray-200 dark:border-gray-700">
          <button
            onClick={undo}
            disabled={!canUndo || isLoading}
            className={`p-2 rounded transition-colors ${canUndo
              ? 'bg-blue-100 text-blue-700 hover:bg-blue-200 dark:bg-blue-900 dark:text-blue-200'
              : 'bg-gray-100 text-gray-400 dark:bg-gray-700 dark:text-gray-500'
              }`}
            title="Undo (Ctrl+Z)"
          >
            ↶
          </button>
          <button
            onClick={redo}
            disabled={!canRedo || isLoading}
            className={`p-2 rounded transition-colors ${canRedo
              ? 'bg-green-100 text-green-700 hover:bg-green-200 dark:bg-green-900 dark:text-green-200'
              : 'bg-gray-100 text-gray-400 dark:bg-gray-700 dark:text-gray-500'
              }`}
            title="Redo (Ctrl+Shift+Z)"
          >
            ↷
          </button>
        </div>
      </div>
    </div>
  );
};

export default SchedulerWithUndoRedo;
