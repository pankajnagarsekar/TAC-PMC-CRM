/**
 * UndoRedoHistory Component
 *
 * Displays undo/redo history timeline with ability to:
 * - View all previous states
 * - Jump to any historical point
 * - Undo/redo operations with visual feedback
 * - See operation type and user who made the change
 *
 * Task #16: Frontend Integration for Undo/Redo System
 */

'use client';

import React, { useState, useEffect } from 'react';
import {
  ChevronUp,
  ChevronDown,
  RotateCcw,
  RotateCw,
  Clock,
  User,
  Loader,
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

export interface HistoryEntry {
  id: string;
  change_type: string;
  summary: string;
  captured_by: string;
  captured_at: string;
  stack_position: number;
}

export interface StackInfo {
  can_undo: boolean;
  can_redo: boolean;
  current_position: number;
  total_entries: number;
  total_reverted: number;
}

export interface UndoRedoHistoryProps {
  projectId: string;
  history: HistoryEntry[];
  stackInfo: StackInfo;
  onUndo: () => void;
  onRedo: () => void;
  onRestore: (entryId: string) => void;
  isLoading?: boolean;
  onLoadHistory?: () => void;
}

/**
 * Helper to get color for operation type
 */
function getOperationColor(changeType: string): string {
  const colorMap: Record<string, string> = {
    SAVE_SCHEDULE: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-200',
    DELETE_TASK: 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-200',
    BULK_UPDATE: 'bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-200',
    RESOURCE_LEVEL: 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-200',
    RESTORE: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-200',
  };
  return colorMap[changeType] || 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-200';
}

/**
 * Helper to format operation type for display
 */
function formatOperationType(changeType: string): string {
  return changeType
    .split('_')
    .map((word) => word.charAt(0) + word.slice(1).toLowerCase())
    .join(' ');
}

/**
 * UndoRedoHistory Component
 *
 * Displays a sidebar with undo/redo controls and history timeline
 */
export const UndoRedoHistory: React.FC<UndoRedoHistoryProps> = ({
  projectId,
  history,
  stackInfo,
  onUndo,
  onRedo,
  onRestore,
  isLoading = false,
  onLoadHistory,
}) => {
  const [expanded, setExpanded] = useState(true);
  const [selectedEntryId, setSelectedEntryId] = useState<string | null>(null);

  // Load history on mount or when projectId changes
  useEffect(() => {
    if (onLoadHistory) {
      onLoadHistory();
    }
  }, [projectId, onLoadHistory]);

  // Calculate entries before and after current position
  const currentIndex = history.findIndex(
    (entry) => entry.stack_position === stackInfo.current_position
  );
  const entriesAfter = currentIndex >= 0 ? history.slice(0, currentIndex) : [];
  const entriesBefore = currentIndex >= 0 ? history.slice(currentIndex + 1) : [];

  return (
    <div className="w-80 bg-white dark:bg-gray-900 border-l border-gray-200 dark:border-gray-700 flex flex-col h-screen">
      {/* Header */}
      <div className="px-4 py-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
            <Clock className="w-4 h-4" />
            History
          </h2>
          <button
            onClick={() => setExpanded(!expanded)}
            className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800"
          >
            {expanded ? (
              <ChevronUp className="w-4 h-4" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )}
          </button>
        </div>

        {/* Undo/Redo Controls */}
        <div className="flex gap-2">
          <button
            onClick={onUndo}
            disabled={!stackInfo.can_undo || isLoading}
            className={`flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded font-medium text-sm transition-colors ${
              stackInfo.can_undo
                ? 'bg-blue-100 text-blue-700 hover:bg-blue-200 dark:bg-blue-900 dark:text-blue-200 dark:hover:bg-blue-800'
                : 'bg-gray-100 text-gray-400 cursor-not-allowed dark:bg-gray-800 dark:text-gray-600'
            }`}
            title={stackInfo.can_undo ? 'Undo (Ctrl+Z)' : 'Nothing to undo'}
          >
            <RotateCcw className="w-4 h-4" />
            <span>Undo</span>
            {isLoading && <Loader className="w-3 h-3 animate-spin ml-1" />}
          </button>

          <button
            onClick={onRedo}
            disabled={!stackInfo.can_redo || isLoading}
            className={`flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded font-medium text-sm transition-colors ${
              stackInfo.can_redo
                ? 'bg-green-100 text-green-700 hover:bg-green-200 dark:bg-green-900 dark:text-green-200 dark:hover:bg-green-800'
                : 'bg-gray-100 text-gray-400 cursor-not-allowed dark:bg-gray-800 dark:text-gray-600'
            }`}
            title={stackInfo.can_redo ? 'Redo (Ctrl+Y)' : 'Nothing to redo'}
          >
            <RotateCw className="w-4 h-4" />
            <span>Redo</span>
            {isLoading && <Loader className="w-3 h-3 animate-spin ml-1" />}
          </button>
        </div>

        {/* History Stats */}
        <div className="mt-3 text-xs text-gray-600 dark:text-gray-400">
          <div className="flex justify-between">
            <span>Position: {stackInfo.current_position + 1}</span>
            <span>Total: {stackInfo.total_entries}</span>
          </div>
        </div>
      </div>

      {/* History Timeline */}
      {expanded && (
        <div className="flex-1 overflow-y-auto px-4 py-3">
          {isLoading ? (
            <div className="flex items-center justify-center h-full">
              <Loader className="w-5 h-5 animate-spin text-gray-400" />
            </div>
          ) : history.length === 0 ? (
            <div className="text-center py-8">
              <Clock className="w-8 h-8 text-gray-300 mx-auto mb-2" />
              <p className="text-sm text-gray-500 dark:text-gray-400">
                No history yet
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {/* Future entries (redo available) */}
              {entriesAfter.length > 0 && (
                <>
                  <div className="sticky top-0 pt-2 pb-1 bg-white dark:bg-gray-900">
                    <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Available to Redo
                    </p>
                  </div>
                  {entriesAfter.map((entry) => (
                    <HistoryEntryItem
                      key={entry.id}
                      entry={entry}
                      isSelected={selectedEntryId === entry.id}
                      isCurrent={false}
                      onRestore={() => {
                        onRestore(entry.id);
                        setSelectedEntryId(entry.id);
                      }}
                    />
                  ))}
                </>
              )}

              {/* Current entry (separator) */}
              {currentIndex >= 0 && (
                <div className="relative my-3">
                  <div className="absolute inset-0 flex items-center">
                    <div className="w-full border-t-2 border-blue-400 dark:border-blue-600" />
                  </div>
                  <div className="relative flex justify-center">
                    <span className="px-2 bg-white dark:bg-gray-900 text-xs font-semibold text-blue-600 dark:text-blue-400 uppercase">
                      Current
                    </span>
                  </div>
                </div>
              )}

              {/* Past entries (undo available) */}
              {entriesBefore.length > 0 && (
                <>
                  <div className="sticky top-0 pt-2 pb-1 bg-white dark:bg-gray-900">
                    <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Available to Undo
                    </p>
                  </div>
                  {entriesBefore.map((entry) => (
                    <HistoryEntryItem
                      key={entry.id}
                      entry={entry}
                      isSelected={selectedEntryId === entry.id}
                      isCurrent={false}
                      onRestore={() => {
                        onRestore(entry.id);
                        setSelectedEntryId(entry.id);
                      }}
                    />
                  ))}
                </>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

/**
 * Individual History Entry Item
 */
interface HistoryEntryItemProps {
  entry: HistoryEntry;
  isSelected: boolean;
  isCurrent: boolean;
  onRestore: () => void;
}

const HistoryEntryItem: React.FC<HistoryEntryItemProps> = ({
  entry,
  isSelected,
  isCurrent,
  onRestore,
}) => {
  const colorClass = getOperationColor(entry.change_type);
  const operationLabel = formatOperationType(entry.change_type);
  const timeAgo = formatDistanceToNow(new Date(entry.captured_at), {
    addSuffix: true,
  });

  return (
    <button
      onClick={onRestore}
      className={`w-full text-left p-3 rounded-lg border-2 transition-all ${
        isSelected
          ? 'border-blue-400 bg-blue-50 dark:bg-blue-900 dark:border-blue-600'
          : 'border-transparent hover:border-gray-200 dark:hover:border-gray-700'
      } ${isCurrent ? 'ring-2 ring-blue-400' : ''}`}
    >
      <div className="flex items-start gap-2">
        {/* Operation Badge */}
        <span
          className={`inline-block px-2 py-1 rounded text-xs font-semibold whitespace-nowrap ${colorClass}`}
        >
          {operationLabel}
        </span>
      </div>

      {/* Summary */}
      <p className="mt-2 text-sm text-gray-700 dark:text-gray-300 line-clamp-2">
        {entry.summary}
      </p>

      {/* Metadata */}
      <div className="mt-2 flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
        <div className="flex items-center gap-1">
          <User className="w-3 h-3" />
          <span>{entry.captured_by}</span>
        </div>
        <span title={new Date(entry.captured_at).toLocaleString()}>
          {timeAgo}
        </span>
      </div>
    </button>
  );
};

export default UndoRedoHistory;
