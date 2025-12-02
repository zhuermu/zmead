'use client';

import { useEffect, useRef, useState } from 'react';
import { useChat, type AgentStatus } from '@/hooks/useChat';
import { MessageBubble } from './MessageBubble';
import { GeneratedImageGallery } from './GeneratedImageGallery';
import { useAuth } from '@/components/auth';
import type { Message } from '@/hooks/useChat';

interface ChatAreaProps {
  sessionId: string | null;
  onFirstMessage?: () => void;
}

// Helper to get icon for agent status type
function getStatusIcon(type: AgentStatus['type']) {
  switch (type) {
    case 'thinking':
      return (
        <svg className="w-4 h-4 animate-pulse" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
        </svg>
      );
    case 'status':
      return (
        <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
      );
    case 'tool_start':
      return (
        <svg className="w-4 h-4 animate-pulse" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
      );
    case 'tool_complete':
      return (
        <svg className="w-4 h-4 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
        </svg>
      );
    default:
      return null;
  }
}

export function ChatArea({ sessionId, onFirstMessage }: ChatAreaProps) {
  const { user } = useAuth();
  const {
    messages,
    input,
    handleInputChange,
    handleSubmit,
    isLoading,
    stop,
    isTimeout,
    agentStatus,
    generatedImages,
  } = useChat();

  const [isComposing, setIsComposing] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    console.log('Messages updated:', messages);
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const onSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!input.trim() || isLoading || isComposing) return;

    // If this is the first message and no session exists, create one
    if (messages.length === 0 && onFirstMessage) {
      onFirstMessage();
    }

    handleSubmit(e);

    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey && !isComposing) {
      e.preventDefault();
      const formEvent = new Event('submit', {
        bubbles: true,
        cancelable: true,
      }) as unknown as React.FormEvent<HTMLFormElement>;
      onSubmit(formEvent);
    }
  };

  const handleTextareaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    handleInputChange(e);

    // Auto-resize textarea
    const textarea = e.target;
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px';
  };

  // Empty state - show welcome screen
  if (messages.length === 0) {
    return (
      <div className="flex-1 flex flex-col">
        {/* Welcome area */}
        <div className="flex-1 flex flex-col items-center justify-center px-4 pb-32">
          <div className="text-center max-w-2xl">
            <h1 className="text-4xl font-semibold text-gray-900 mb-2">
              你好{user?.displayName ? `，${user.displayName}` : ''}！
            </h1>
            <p className="text-lg text-gray-500 mb-8">
              我是 AAE 智能助手，可以帮助你管理广告投放、生成创意素材、分析数据等。
            </p>

            {/* Suggestion chips */}
            <div className="flex flex-wrap justify-center gap-2 mb-8">
              {[
                '帮我创建一个新的广告素材',
                '分析我的广告投放效果',
                '有什么优化建议？',
                '生成一个落地页',
              ].map((suggestion) => (
                <button
                  key={suggestion}
                  onClick={() => {
                    if (textareaRef.current) {
                      textareaRef.current.value = suggestion;
                      handleInputChange({
                        target: { value: suggestion },
                      } as any);
                      textareaRef.current.focus();
                    }
                  }}
                  className="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 text-sm rounded-full transition-colors"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Input area - centered at bottom */}
        <div className="pb-8 px-4">
          <form onSubmit={onSubmit} className="max-w-3xl mx-auto">
            <div className="relative bg-white border border-gray-300 rounded-2xl shadow-lg focus-within:border-blue-500 focus-within:ring-1 focus-within:ring-blue-500">
              <textarea
                ref={textareaRef}
                value={input}
                onChange={handleTextareaChange}
                onKeyDown={handleKeyDown}
                onCompositionStart={() => setIsComposing(true)}
                onCompositionEnd={() => setIsComposing(false)}
                placeholder="输入你想问的问题..."
                disabled={isLoading}
                rows={1}
                className="w-full px-4 py-4 pr-14 bg-transparent border-none focus:outline-none resize-none text-base"
                style={{ minHeight: '56px', maxHeight: '200px' }}
              />
              <button
                type="submit"
                disabled={!input.trim() || isLoading || isComposing}
                className="absolute right-2 bottom-2 p-2 bg-blue-600 hover:bg-blue-700 text-white rounded-full transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <svg
                  className="w-5 h-5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
                  />
                </svg>
              </button>
            </div>
            <p className="text-xs text-gray-400 text-center mt-2">
              按 Enter 发送，Shift + Enter 换行
            </p>
          </form>
        </div>
      </div>
    );
  }

  // Chat conversation view
  return (
    <div className="flex-1 flex flex-col h-full">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="max-w-3xl mx-auto">
          {messages.map((message: UIMessage) => (
            <MessageBubble key={message.id} message={message} />
          ))}

          {/* Display generated images from v3 API */}
          {generatedImages.length > 0 && (
            <div className="mb-4">
              <GeneratedImageGallery images={generatedImages} />
            </div>
          )}

          {/* Loading indicator with agent status */}
          {isLoading && (
            <div className="flex justify-start mb-4">
              <div className="bg-gray-100 rounded-lg px-4 py-3">
                {agentStatus ? (
                  <div className="flex items-center gap-2 text-gray-600 text-sm">
                    {getStatusIcon(agentStatus.type)}
                    <span>{agentStatus.message || '正在处理...'}</span>
                  </div>
                ) : (
                  <div className="flex items-center gap-1">
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                    <div
                      className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                      style={{ animationDelay: '0.1s' }}
                    />
                    <div
                      className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                      style={{ animationDelay: '0.2s' }}
                    />
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Timeout warning */}
          {isTimeout && (
            <div className="flex justify-center mb-4">
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg px-4 py-2 text-sm text-yellow-700">
                响应超时，请重试
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input area */}
      <div className="border-t border-gray-200 bg-white p-4">
        <form onSubmit={onSubmit} className="max-w-3xl mx-auto">
          <div className="flex gap-3 items-end">
            <div className="flex-1 relative bg-gray-100 rounded-2xl focus-within:bg-white focus-within:border focus-within:border-blue-500 focus-within:ring-1 focus-within:ring-blue-500">
              <textarea
                ref={textareaRef}
                value={input}
                onChange={handleTextareaChange}
                onKeyDown={handleKeyDown}
                onCompositionStart={() => setIsComposing(true)}
                onCompositionEnd={() => setIsComposing(false)}
                placeholder="继续对话..."
                disabled={isLoading}
                rows={1}
                className="w-full px-4 py-3 bg-transparent border-none focus:outline-none resize-none text-sm"
                style={{ minHeight: '44px', maxHeight: '200px' }}
              />
            </div>

            {isLoading ? (
              <button
                type="button"
                onClick={stop}
                className="p-3 bg-red-500 hover:bg-red-600 text-white rounded-full transition-colors"
              >
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                  <rect x="6" y="6" width="12" height="12" />
                </svg>
              </button>
            ) : (
              <button
                type="submit"
                disabled={!input.trim() || isComposing}
                className="p-3 bg-blue-600 hover:bg-blue-700 text-white rounded-full transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <svg
                  className="w-5 h-5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
                  />
                </svg>
              </button>
            )}
          </div>
        </form>
      </div>
    </div>
  );
}
