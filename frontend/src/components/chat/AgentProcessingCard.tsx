'use client';

import { useState, useEffect, useRef } from 'react';
import { Loader2, Brain, Wrench, CheckCircle2, XCircle, ChevronDown, ChevronUp, Sparkles, Clock } from 'lucide-react';
import type { AgentStatus } from '@/hooks/useChat';

interface AgentProcessingCardProps {
  status: AgentStatus | null;
  isLoading: boolean;
  thinkingContent?: string;
}

interface ProcessStep {
  id: string;
  type: 'thinking' | 'thought' | 'action' | 'observation';
  content: string;
  tool?: string;
  success?: boolean;
  timestamp: Date;
}

/**
 * Agent Processing Card - Shows AI thinking and tool execution in real-time
 *
 * Design: Clean timeline view with collapsible details
 */
export function AgentProcessingCard({ status, isLoading, thinkingContent }: AgentProcessingCardProps) {
  const [steps, setSteps] = useState<ProcessStep[]>([]);
  const [isExpanded, setIsExpanded] = useState(true);
  const [displayedThought, setDisplayedThought] = useState('');
  const stepIdRef = useRef(0);

  // Parse thought content to extract readable text
  const parseThoughtContent = (content: string): string => {
    if (!content) return '';

    // Extract text before JSON block
    const jsonStart = content.indexOf('```json');
    if (jsonStart > 0) {
      const textBefore = content.substring(0, jsonStart).trim();
      if (textBefore) return textBefore;
    }

    // Try to extract reasoning from JSON
    try {
      const jsonMatch = content.match(/```json\s*([\s\S]*?)\s*```/);
      if (jsonMatch) {
        const parsed = JSON.parse(jsonMatch[1]);
        if (parsed.final_answer) {
          return `准备回答: ${parsed.final_answer.substring(0, 50)}...`;
        }
        if (parsed.action) {
          return `决定使用工具: ${parsed.action}`;
        }
      }
    } catch {
      // Ignore parse errors
    }

    // Clean up JSON-like content
    if (content.includes('```json')) {
      return '分析中...';
    }

    return content.substring(0, 100);
  };

  // Track steps based on status changes
  useEffect(() => {
    if (!status) return;

    const stepId = `step-${++stepIdRef.current}`;

    if (status.type === 'thinking') {
      // Initial thinking status
      setSteps([{
        id: stepId,
        type: 'thinking',
        content: status.message || '正在思考...',
        timestamp: new Date(),
      }]);
    } else if (status.type === 'thought') {
      // Update displayed thought with parsed content
      const parsed = parseThoughtContent(status.message || '');
      if (parsed && parsed !== '分析中...') {
        setDisplayedThought(parsed);
      }
    } else if (status.type === 'action') {
      // Tool execution starting
      setSteps(prev => {
        const filtered = prev.filter(s => !(s.type === 'action' && s.tool === status.tool));
        return [...filtered, {
          id: stepId,
          type: 'action',
          content: status.message || `正在执行 ${status.tool}...`,
          tool: status.tool,
          timestamp: new Date(),
        }];
      });
      setDisplayedThought('');
    } else if (status.type === 'observation') {
      // Tool execution result
      setSteps(prev => {
        const filtered = prev.filter(s => !(s.type === 'observation' && s.tool === status.tool));
        return [...filtered, {
          id: stepId,
          type: 'observation',
          content: status.message || '执行完成',
          tool: status.tool,
          success: status.success !== false, // Use actual success status from backend
          timestamp: new Date(),
        }];
      });
    }
  }, [status]);

  // Clear steps when loading finishes
  useEffect(() => {
    if (!isLoading) {
      const timer = setTimeout(() => {
        setSteps([]);
        setDisplayedThought('');
      }, 800);
      return () => clearTimeout(timer);
    }
  }, [isLoading]);

  // Don't render if not loading and no steps
  if (!isLoading && steps.length === 0) return null;

  // Show initial loading state even without steps
  const showInitialLoading = isLoading && steps.length === 0;

  // Determine current phase for header
  const hasActions = steps.some(s => s.type === 'action');
  const hasObservations = steps.some(s => s.type === 'observation');

  return (
    <div className="flex justify-start mb-4 animate-in fade-in slide-in-from-bottom-2 duration-300">
      <div className="max-w-[90%] w-full">
        <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-2xl shadow-lg overflow-hidden">

          {/* Header */}
          <div
            className="px-4 py-3 bg-gradient-to-r from-indigo-50 to-purple-50 dark:from-indigo-950/50 dark:to-purple-950/50 cursor-pointer"
            onClick={() => setIsExpanded(!isExpanded)}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                {/* Animated Icon */}
                <div className="relative flex-shrink-0">
                  <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                    hasObservations
                      ? 'bg-gradient-to-br from-green-400 to-emerald-500'
                      : hasActions
                        ? 'bg-gradient-to-br from-amber-400 to-orange-500'
                        : 'bg-gradient-to-br from-indigo-400 to-purple-500'
                  }`}>
                    {hasObservations ? (
                      <CheckCircle2 className="w-5 h-5 text-white" />
                    ) : hasActions ? (
                      <Wrench className="w-5 h-5 text-white animate-bounce" />
                    ) : (
                      <Brain className="w-5 h-5 text-white animate-pulse" />
                    )}
                  </div>
                  {isLoading && !hasObservations && (
                    <span className="absolute -top-1 -right-1 flex h-3 w-3">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-3 w-3 bg-indigo-500"></span>
                    </span>
                  )}
                </div>

                {/* Status Text */}
                <div>
                  <div className="text-sm font-semibold text-gray-800 dark:text-gray-100">
                    {hasObservations
                      ? '任务执行完成'
                      : hasActions
                        ? '正在执行工具...'
                        : 'AI 正在思考...'}
                  </div>
                  {displayedThought && !hasActions && (
                    <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5 line-clamp-1">
                      {displayedThought}
                    </div>
                  )}
                  {hasActions && !hasObservations && (
                    <div className="text-xs text-amber-600 dark:text-amber-400 mt-0.5">
                      {steps.find(s => s.type === 'action')?.tool || '工具'}
                    </div>
                  )}
                </div>
              </div>

              {/* Expand Toggle */}
              <button className="p-1.5 hover:bg-white/50 dark:hover:bg-gray-800/50 rounded-lg transition-colors">
                {isExpanded ? (
                  <ChevronUp className="w-4 h-4 text-gray-500" />
                ) : (
                  <ChevronDown className="w-4 h-4 text-gray-500" />
                )}
              </button>
            </div>
          </div>

          {/* Expanded Content - Timeline */}
          {isExpanded && (steps.length > 0 || showInitialLoading) && (
            <div className="px-4 py-3 border-t border-gray-100 dark:border-gray-800">
              <div className="space-y-3">
                {/* Show initial loading state */}
                {showInitialLoading && (
                  <div className="flex items-start gap-3">
                    <div className="flex flex-col items-center">
                      <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 bg-indigo-100 dark:bg-indigo-900/30">
                        <Brain className="w-4 h-4 text-indigo-600 dark:text-indigo-400 animate-pulse" />
                      </div>
                    </div>
                    <div className="flex-1 min-w-0 pt-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-indigo-700 dark:text-indigo-300">
                          正在分析问题...
                        </span>
                        <Loader2 className="w-3 h-3 text-gray-400 animate-spin" />
                      </div>
                      <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                        AI 正在理解您的请求
                      </div>
                    </div>
                  </div>
                )}
                {steps.map((step, index) => (
                  <div key={step.id} className="flex items-start gap-3">
                    {/* Timeline connector */}
                    <div className="flex flex-col items-center">
                      <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
                        step.type === 'thinking'
                          ? 'bg-indigo-100 dark:bg-indigo-900/30'
                          : step.type === 'action'
                            ? 'bg-amber-100 dark:bg-amber-900/30'
                            : step.type === 'observation'
                              ? step.success
                                ? 'bg-green-100 dark:bg-green-900/30'
                                : 'bg-red-100 dark:bg-red-900/30'
                              : 'bg-gray-100 dark:bg-gray-800'
                      }`}>
                        {step.type === 'thinking' && (
                          <Brain className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
                        )}
                        {step.type === 'thought' && (
                          <Sparkles className="w-4 h-4 text-purple-600 dark:text-purple-400" />
                        )}
                        {step.type === 'action' && (
                          <Wrench className="w-4 h-4 text-amber-600 dark:text-amber-400" />
                        )}
                        {step.type === 'observation' && step.success && (
                          <CheckCircle2 className="w-4 h-4 text-green-600 dark:text-green-400" />
                        )}
                        {step.type === 'observation' && !step.success && (
                          <XCircle className="w-4 h-4 text-red-600 dark:text-red-400" />
                        )}
                      </div>
                      {index < steps.length - 1 && (
                        <div className="w-0.5 h-4 bg-gray-200 dark:bg-gray-700 mt-1" />
                      )}
                    </div>

                    {/* Step Content */}
                    <div className="flex-1 min-w-0 pt-1">
                      <div className="flex items-center gap-2">
                        <span className={`text-sm font-medium ${
                          step.type === 'thinking' ? 'text-indigo-700 dark:text-indigo-300' :
                          step.type === 'action' ? 'text-amber-700 dark:text-amber-300' :
                          step.type === 'observation'
                            ? step.success
                              ? 'text-green-700 dark:text-green-300'
                              : 'text-red-700 dark:text-red-300'
                            : 'text-gray-700 dark:text-gray-300'
                        }`}>
                          {step.type === 'thinking' && '思考中'}
                          {step.type === 'thought' && '推理'}
                          {step.type === 'action' && `执行: ${step.tool || '工具'}`}
                          {step.type === 'observation' && `结果: ${step.tool || '工具'}`}
                        </span>
                        {isLoading && index === steps.length - 1 && step.type !== 'observation' && (
                          <Loader2 className="w-3 h-3 text-gray-400 animate-spin" />
                        )}
                      </div>
                      <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5 line-clamp-2">
                        {step.content}
                      </div>
                    </div>

                    {/* Timestamp */}
                    <div className="flex items-center gap-1 text-xs text-gray-400 flex-shrink-0 pt-1">
                      <Clock className="w-3 h-3" />
                      {step.timestamp.toLocaleTimeString('zh-CN', {
                        hour: '2-digit',
                        minute: '2-digit',
                        second: '2-digit'
                      })}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Progress indicator */}
          {isLoading && (
            <div className="h-1 bg-gray-100 dark:bg-gray-800 overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-indigo-500 via-purple-500 to-indigo-500 animate-shimmer"
                style={{ backgroundSize: '200% 100%' }}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
