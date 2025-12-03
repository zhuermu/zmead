'use client';

import { useEffect, useRef, useState } from 'react';
import { useChat } from '@/hooks/useChat';
import { MessageBubble } from './MessageBubble';
import { useAuth } from '@/components/auth';
import type { Message } from '@/hooks/useChat';

interface ChatAreaProps {
  sessionId: string | null;
  onFirstMessage?: () => void;
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
          {messages.map((message: Message, index: number) => {
            // Check if this is the last assistant message being streamed
            const isLastMessage = index === messages.length - 1;
            const isStreamingMessage = isLoading && isLastMessage && message.role === 'assistant';

            return (
              <MessageBubble
                key={message.id}
                message={message}
                isStreaming={isStreamingMessage}
                agentStatus={isStreamingMessage ? agentStatus : null}
              />
            );
          })}

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
