'use client';

import { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import { ChevronDown, ChevronRight, Brain, Wrench, CheckCircle2, XCircle, Sparkles, Loader2 } from 'lucide-react';
import type { Message, AgentStatus } from '@/hooks/useChat';
import { GeneratedImageGallery } from './GeneratedImageGallery';

interface MessageBubbleProps {
  message: Message;
  compact?: boolean;
  isStreaming?: boolean;
  agentStatus?: AgentStatus | null;
}

// Process step structure
interface ProcessStep {
  id: string;
  type: 'thinking' | 'thought' | 'action' | 'observation';
  content: string;
  tool?: string;
  success?: boolean;
  timestamp: Date;
}

// Parse processInfo string into structured steps
function parseProcessInfo(processInfo: string): ProcessStep[] {
  if (!processInfo) return [];

  const steps: ProcessStep[] = [];
  const lines = processInfo.split('\n').filter(line => line.trim());
  let stepId = 0;

  for (const line of lines) {
    // Parse action lines: 🔧 tool_name: message
    if (line.includes('🔧')) {
      const match = line.match(/🔧\s*([^:]+):\s*(.*)/);
      if (match) {
        steps.push({
          id: `step-${stepId++}`,
          type: 'action',
          tool: match[1].trim(),
          content: match[2].trim() || '执行中...',
          timestamp: new Date(),
        });
      }
    }
    // Parse observation lines: ✅ or ❌ Result: message
    else if (line.includes('✅') || line.includes('❌')) {
      const success = line.includes('✅');
      const match = line.match(/[✅❌]\s*Result:\s*(.*)/);
      steps.push({
        id: `step-${stepId++}`,
        type: 'observation',
        content: match ? match[1].trim() : line.replace(/[✅❌]/g, '').trim(),
        success,
        timestamp: new Date(),
      });
    }
    // Parse thought content (excluding JSON blocks)
    else if (!line.startsWith('```') && !line.includes('"action"') && !line.includes('"is_complete"')) {
      const cleanedLine = line.trim();
      if (cleanedLine && !cleanedLine.startsWith('{') && !cleanedLine.startsWith('}') && cleanedLine.length > 5) {
        steps.push({
          id: `step-${stepId++}`,
          type: 'thought',
          content: cleanedLine.substring(0, 100),
          timestamp: new Date(),
        });
      }
    }
  }

  return steps;
}

// Get human-readable status text
function getStatusText(status: AgentStatus | null | undefined): string {
  if (!status) return '正在思考...';

  switch (status.type) {
    case 'thinking':
      return '正在分析问题...';
    case 'thought':
      return '正在推理...';
    case 'action':
      return `正在执行 ${status.tool || '工具'}...`;
    case 'observation':
      return status.success !== false ? '执行完成' : '执行失败';
    default:
      return '处理中...';
  }
}

export function MessageBubble({ message, compact = false, isStreaming = false, agentStatus }: MessageBubbleProps) {
  const [showProcess, setShowProcess] = useState(false);
  const [streamingSteps, setStreamingSteps] = useState<ProcessStep[]>([]);
  const stepIdRef = useRef(0);
  const isUser = message.role === 'user';

  // Parse static process info from completed message
  const staticSteps = !isUser && message.processInfo ? parseProcessInfo(message.processInfo) : [];

  // Combine static and streaming steps
  const allSteps = isStreaming ? streamingSteps : staticSteps;
  const hasProcessInfo = allSteps.length > 0 || isStreaming;

  // Track streaming steps based on agentStatus changes
  useEffect(() => {
    if (!isStreaming || !agentStatus) return;

    const stepId = `stream-${++stepIdRef.current}`;

    if (agentStatus.type === 'thinking') {
      setStreamingSteps([{
        id: stepId,
        type: 'thinking',
        content: agentStatus.message || '正在思考...',
        timestamp: new Date(),
      }]);
    } else if (agentStatus.type === 'thought') {
      // Extract clean thought content
      let content = agentStatus.message || '';
      if (content.includes('```json')) {
        content = content.split('```json')[0].trim() || '分析中...';
      }
      if (content && content.length > 5) {
        setStreamingSteps(prev => {
          // Avoid duplicate thoughts
          const exists = prev.some(s => s.type === 'thought' && s.content === content.substring(0, 100));
          if (exists) return prev;
          return [...prev, {
            id: stepId,
            type: 'thought',
            content: content.substring(0, 100),
            timestamp: new Date(),
          }];
        });
      }
    } else if (agentStatus.type === 'action') {
      setStreamingSteps(prev => [...prev, {
        id: stepId,
        type: 'action',
        tool: agentStatus.tool,
        content: agentStatus.message || `执行 ${agentStatus.tool}...`,
        timestamp: new Date(),
      }]);
    } else if (agentStatus.type === 'observation') {
      setStreamingSteps(prev => [...prev, {
        id: stepId,
        type: 'observation',
        tool: agentStatus.tool,
        content: agentStatus.result || agentStatus.message || '完成',
        success: agentStatus.success !== false,
        timestamp: new Date(),
      }]);
    }
  }, [isStreaming, agentStatus]);

  // Clear streaming steps when streaming ends
  useEffect(() => {
    if (!isStreaming) {
      setStreamingSteps([]);
      stepIdRef.current = 0;
    }
  }, [isStreaming]);

  // Extract content from message
  const getMessageContent = () => {
    const msg = message as any;

    if (typeof msg.content === 'string') {
      return msg.content;
    }

    if (Array.isArray(msg.content)) {
      return msg.content
        .filter((part: any) => part.type === 'text')
        .map((part: any) => part.text)
        .join('');
    }

    if (Array.isArray(msg.parts)) {
      return msg.parts
        .filter((part: any) => part.type === 'text')
        .map((part: any) => part.text)
        .join('');
    }

    return '';
  };

  const content = getMessageContent();

  // Get generated images/videos from message
  const generatedImages = (message as any).generatedImages || [];
  const generatedVideoUrl = (message as any).generatedVideoUrl;

  // Filter meaningful steps for display
  const meaningfulSteps = allSteps.filter(step => {
    if (step.type === 'thought') {
      return step.content.length > 5 && !step.content.includes('"action"');
    }
    return true;
  });

  // Auto-expand during streaming, collapse after
  const shouldShowProcess = isStreaming ? true : showProcess;

  return (
    <div className={`mb-4 flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[85%] rounded-2xl overflow-hidden ${
          isUser
            ? 'bg-gradient-to-r from-indigo-600 to-purple-600 text-white'
            : 'bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 shadow-sm'
        }`}
      >
        {/* Process Info Section - Collapsible for completed, always visible for streaming */}
        {!isUser && (hasProcessInfo || isStreaming) && (
          <div className={`border-b ${isStreaming ? 'border-indigo-200 dark:border-indigo-800' : 'border-gray-100 dark:border-gray-800'}`}>
            {/* Header - Clickable to toggle */}
            <button
              onClick={() => !isStreaming && setShowProcess(!showProcess)}
              disabled={isStreaming}
              className={`w-full px-4 py-2.5 flex items-center justify-between transition-colors ${
                isStreaming
                  ? 'bg-gradient-to-r from-indigo-50 to-purple-50 dark:from-indigo-950/50 dark:to-purple-950/50'
                  : 'hover:bg-gray-50 dark:hover:bg-gray-800/50'
              }`}
            >
              <div className="flex items-center gap-2">
                {/* Animated icon during streaming */}
                {isStreaming ? (
                  <div className="relative">
                    <div className={`w-6 h-6 rounded-lg flex items-center justify-center ${
                      agentStatus?.type === 'action'
                        ? 'bg-amber-100 dark:bg-amber-900/30'
                        : agentStatus?.type === 'observation'
                          ? 'bg-green-100 dark:bg-green-900/30'
                          : 'bg-indigo-100 dark:bg-indigo-900/30'
                    }`}>
                      {agentStatus?.type === 'action' ? (
                        <Wrench className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400 animate-bounce" />
                      ) : agentStatus?.type === 'observation' ? (
                        <CheckCircle2 className="w-3.5 h-3.5 text-green-600 dark:text-green-400" />
                      ) : (
                        <Brain className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400 animate-pulse" />
                      )}
                    </div>
                    <span className="absolute -top-0.5 -right-0.5 flex h-2 w-2">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-2 w-2 bg-indigo-500"></span>
                    </span>
                  </div>
                ) : (
                  <Sparkles className="w-3.5 h-3.5 text-gray-400" />
                )}

                <span className={`text-xs font-medium ${
                  isStreaming ? 'text-indigo-700 dark:text-indigo-300' : 'text-gray-500 dark:text-gray-400'
                }`}>
                  {isStreaming ? getStatusText(agentStatus) : '查看 AI 思考过程'}
                </span>

                {!isStreaming && meaningfulSteps.length > 0 && (
                  <span className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-800 rounded text-[10px] text-gray-500">
                    {meaningfulSteps.length} 步
                  </span>
                )}

                {isStreaming && (
                  <Loader2 className="w-3 h-3 text-indigo-500 animate-spin" />
                )}
              </div>

              {!isStreaming && (
                shouldShowProcess ? (
                  <ChevronDown className="w-4 h-4 text-gray-400" />
                ) : (
                  <ChevronRight className="w-4 h-4 text-gray-400" />
                )
              )}
            </button>

            {/* Expanded Process Steps */}
            {shouldShowProcess && (
              <div className={`px-4 pb-3 pt-1 ${
                isStreaming
                  ? 'bg-gradient-to-b from-indigo-50/50 to-transparent dark:from-indigo-950/30'
                  : 'bg-gray-50/50 dark:bg-gray-800/30'
              }`}>
                <div className="space-y-2">
                  {/* Show initial thinking state if no steps yet during streaming */}
                  {isStreaming && meaningfulSteps.length === 0 && (
                    <div className="flex items-start gap-2 animate-pulse">
                      <div className="mt-0.5 w-5 h-5 rounded flex items-center justify-center flex-shrink-0 bg-indigo-100 dark:bg-indigo-900/30">
                        <Brain className="w-3 h-3 text-indigo-600 dark:text-indigo-400" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-xs text-indigo-700 dark:text-indigo-300">
                          正在分析您的问题...
                        </p>
                      </div>
                    </div>
                  )}

                  {meaningfulSteps.map((step, index) => (
                    <div
                      key={step.id}
                      className={`flex items-start gap-2 ${
                        isStreaming && index === meaningfulSteps.length - 1
                          ? 'animate-in fade-in slide-in-from-left-2 duration-300'
                          : ''
                      }`}
                    >
                      {/* Step Icon */}
                      <div className={`mt-0.5 w-5 h-5 rounded flex items-center justify-center flex-shrink-0 ${
                        step.type === 'thinking' || step.type === 'thought'
                          ? 'bg-indigo-100 dark:bg-indigo-900/30'
                          : step.type === 'action'
                            ? 'bg-amber-100 dark:bg-amber-900/30'
                            : step.success
                              ? 'bg-green-100 dark:bg-green-900/30'
                              : 'bg-red-100 dark:bg-red-900/30'
                      }`}>
                        {(step.type === 'thinking' || step.type === 'thought') && (
                          <Brain className="w-3 h-3 text-indigo-600 dark:text-indigo-400" />
                        )}
                        {step.type === 'action' && (
                          <Wrench className="w-3 h-3 text-amber-600 dark:text-amber-400" />
                        )}
                        {step.type === 'observation' && step.success && (
                          <CheckCircle2 className="w-3 h-3 text-green-600 dark:text-green-400" />
                        )}
                        {step.type === 'observation' && !step.success && (
                          <XCircle className="w-3 h-3 text-red-600 dark:text-red-400" />
                        )}
                      </div>

                      {/* Step Content */}
                      <div className="flex-1 min-w-0">
                        {step.type === 'action' && step.tool && (
                          <span className="text-xs font-medium text-amber-700 dark:text-amber-300">
                            工具: {step.tool}
                          </span>
                        )}
                        {step.type === 'observation' && step.tool && (
                          <span className={`text-xs font-medium ${
                            step.success
                              ? 'text-green-700 dark:text-green-300'
                              : 'text-red-700 dark:text-red-300'
                          }`}>
                            结果: {step.tool}
                          </span>
                        )}
                        <p className={`text-xs line-clamp-2 ${
                          step.type === 'thinking' || step.type === 'thought'
                            ? 'text-indigo-700 dark:text-indigo-300'
                            : step.type === 'action'
                              ? 'text-gray-600 dark:text-gray-400'
                              : step.success
                                ? 'text-green-700 dark:text-green-300'
                                : 'text-red-700 dark:text-red-300'
                        }`}>
                          {step.content}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Progress bar during streaming */}
                {isStreaming && (
                  <div className="mt-3 h-1 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-indigo-500 via-purple-500 to-indigo-500 animate-shimmer rounded-full"
                      style={{ backgroundSize: '200% 100%' }}
                    />
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Main Content */}
        <div className="px-4 py-3">
          {isUser ? (
            <p className="text-sm whitespace-pre-wrap break-words">{content}</p>
          ) : content ? (
            <div className="prose prose-sm dark:prose-invert max-w-none">
              <ReactMarkdown
                components={{
                  code(props: any) {
                    const { inline, className, children, ...rest } = props;
                    return inline ? (
                      <code
                        className="bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200 px-1.5 py-0.5 rounded text-xs font-mono"
                        {...rest}
                      >
                        {children}
                      </code>
                    ) : (
                      <pre className="bg-gray-900 text-gray-100 p-3 rounded-lg overflow-x-auto my-2">
                        <code className="text-xs font-mono" {...rest}>
                          {children}
                        </code>
                      </pre>
                    );
                  },
                  p(props: any) {
                    return <p className="text-sm mb-2 last:mb-0 text-gray-800 dark:text-gray-200">{props.children}</p>;
                  },
                  ul(props: any) {
                    return <ul className="text-sm list-disc list-inside mb-2 text-gray-800 dark:text-gray-200">{props.children}</ul>;
                  },
                  ol(props: any) {
                    return <ol className="text-sm list-decimal list-inside mb-2 text-gray-800 dark:text-gray-200">{props.children}</ol>;
                  },
                  a(props: any) {
                    return (
                      <a
                        href={props.href}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-indigo-600 hover:text-indigo-800 dark:text-indigo-400 dark:hover:text-indigo-300 underline"
                      >
                        {props.children}
                      </a>
                    );
                  },
                  h1(props: any) {
                    return <h1 className="text-base font-bold mb-2 text-gray-900 dark:text-gray-100">{props.children}</h1>;
                  },
                  h2(props: any) {
                    return <h2 className="text-sm font-bold mb-2 text-gray-900 dark:text-gray-100">{props.children}</h2>;
                  },
                  h3(props: any) {
                    return <h3 className="text-sm font-semibold mb-1 text-gray-900 dark:text-gray-100">{props.children}</h3>;
                  },
                  li(props: any) {
                    return <li className="text-gray-800 dark:text-gray-200">{props.children}</li>;
                  },
                  strong(props: any) {
                    return <strong className="font-semibold text-gray-900 dark:text-gray-100">{props.children}</strong>;
                  },
                }}
              >
                {content}
              </ReactMarkdown>
            </div>
          ) : isStreaming ? (
            // Show placeholder while waiting for content during streaming
            <div className="flex items-center gap-2 text-gray-400">
              <div className="flex gap-1">
                <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
              <span className="text-xs">等待回复...</span>
            </div>
          ) : null}

          {/* Generated Images Gallery */}
          {!isUser && generatedImages.length > 0 && (
            <GeneratedImageGallery images={generatedImages} />
          )}

          {/* Generated Video */}
          {!isUser && generatedVideoUrl && (
            <div className="my-3">
              <video
                src={generatedVideoUrl}
                controls
                className="w-full rounded-lg shadow-sm"
                style={{ maxHeight: '400px' }}
              >
                您的浏览器不支持视频播放
              </video>
            </div>
          )}

          {/* Timestamp */}
          {!isStreaming && (
            <div className={`text-xs mt-2 ${isUser ? 'text-white/70' : 'text-gray-400'}`}>
              {new Date((message as any).createdAt || Date.now()).toLocaleTimeString('zh-CN', {
                hour: '2-digit',
                minute: '2-digit',
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
