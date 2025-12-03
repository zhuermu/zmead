'use client';

import { useState } from 'react';
import { ChevronDown, ChevronRight, Sparkles } from 'lucide-react';

interface ProcessInfoBlockProps {
  content: string;
  defaultExpanded?: boolean;
}

/**
 * Collapsible block for displaying agent's process information.
 * Contains thinking, tool actions, and observations.
 * Shows a brief summary when collapsed, full content when expanded.
 */
export function ProcessInfoBlock({ content, defaultExpanded = false }: ProcessInfoBlockProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  if (!content) return null;

  // Clean up the content - remove JSON blocks for display
  const cleanContent = content
    .replace(/```json[\s\S]*?```/g, '')
    .replace(/```[\s\S]*?```/g, '')
    .replace(/## Thinking\s*/g, '')
    .replace(/## Decision\s*/g, '')
    .trim();

  if (!cleanContent) return null;

  // Get preview text - first meaningful line, truncated
  const lines = cleanContent.split('\n').filter(line => line.trim());
  const previewText = lines[0]?.slice(0, 80) + (lines[0]?.length > 80 || lines.length > 1 ? '...' : '');

  return (
    <div className="mb-3 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 overflow-hidden">
      {/* Header - always visible */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-gray-100 dark:hover:bg-gray-700/50 transition-colors"
      >
        <Sparkles className="w-4 h-4 text-purple-500 flex-shrink-0" />
        <span className="text-xs font-medium text-gray-600 dark:text-gray-400">
          Process
        </span>
        {isExpanded ? (
          <ChevronDown className="w-4 h-4 text-gray-400 ml-auto" />
        ) : (
          <ChevronRight className="w-4 h-4 text-gray-400 ml-auto" />
        )}
      </button>

      {/* Preview when collapsed */}
      {!isExpanded && (
        <div className="px-3 pb-2 text-xs text-gray-500 dark:text-gray-400 line-clamp-1">
          {previewText}
        </div>
      )}

      {/* Full content when expanded */}
      {isExpanded && (
        <div className="px-3 pb-3 text-sm text-gray-600 dark:text-gray-300 whitespace-pre-wrap border-t border-gray-200 dark:border-gray-700 pt-2 max-h-64 overflow-y-auto">
          {cleanContent}
        </div>
      )}
    </div>
  );
}

interface ActionBlockProps {
  actions: Array<{
    tool: string;
    message?: string;
    result?: string;
    success?: boolean;
  }>;
}

/**
 * Block for displaying tool actions and their results.
 */
export function ActionBlock({ actions }: ActionBlockProps) {
  if (!actions || actions.length === 0) return null;

  return (
    <div className="mb-3 space-y-2">
      {actions.map((action, index) => (
        <div
          key={index}
          className={`rounded-lg border px-3 py-2 text-sm ${
            action.success === undefined
              ? 'border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-900/20'
              : action.success
              ? 'border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-900/20'
              : 'border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20'
          }`}
        >
          <div className="flex items-center gap-2">
            <span className="font-medium text-gray-700 dark:text-gray-300">
              {action.tool}
            </span>
            {action.success === undefined && (
              <span className="text-xs text-blue-600 dark:text-blue-400">Running...</span>
            )}
            {action.success === true && (
              <span className="text-xs text-green-600 dark:text-green-400">Success</span>
            )}
            {action.success === false && (
              <span className="text-xs text-red-600 dark:text-red-400">Failed</span>
            )}
          </div>
          {action.message && (
            <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              {action.message}
            </div>
          )}
          {action.result && (
            <div className="text-xs text-gray-600 dark:text-gray-300 mt-1 line-clamp-2">
              {action.result}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
