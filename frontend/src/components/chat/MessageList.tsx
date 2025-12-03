'use client';

import { useEffect, useRef } from 'react';
import { useChat } from '@/hooks/useChat';
import { MessageBubble } from './MessageBubble';
import { ToolInvocationCard } from './ToolInvocationCard';

export function MessageList() {
  const { messages, isLoading, isTimeout, retry, agentStatus } = useChat();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive or agent status changes
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, agentStatus]);

  // Find the last assistant message index for streaming state
  const lastAssistantIndex = messages.map(m => m.role).lastIndexOf('assistant');

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-2">
      {messages.length === 0 && (
        <div className="flex flex-col items-center justify-center h-full text-center px-4">
          <div className="w-16 h-16 bg-gradient-to-r from-purple-100 to-blue-100 rounded-full flex items-center justify-center mb-4">
            <svg className="w-8 h-8 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
            </svg>
          </div>
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            你好！我是 AI 投放助手
          </h3>
          <p className="text-sm text-gray-600 mb-4">
            我可以帮你生成素材、创建广告、分析数据等
          </p>
          <div className="space-y-2 w-full">
            <button className="w-full text-left px-4 py-2 bg-gray-50 hover:bg-gray-100 rounded-lg text-sm text-gray-700 transition-colors">
              💡 帮我生成一个广告素材
            </button>
            <button className="w-full text-left px-4 py-2 bg-gray-50 hover:bg-gray-100 rounded-lg text-sm text-gray-700 transition-colors">
              📊 查看最近的广告表现
            </button>
            <button className="w-full text-left px-4 py-2 bg-gray-50 hover:bg-gray-100 rounded-lg text-sm text-gray-700 transition-colors">
              🚀 创建一个新的广告活动
            </button>
          </div>
        </div>
      )}

      {messages.map((message: any, index: number) => {
        // Check if this is the last assistant message and we're streaming
        const isLastAssistant = index === lastAssistantIndex;
        const isStreaming = isLoading && isLastAssistant && message.role === 'assistant';

        return (
          <div key={message.id}>
            <MessageBubble
              message={message}
              isStreaming={isStreaming}
              agentStatus={isStreaming ? agentStatus : null}
            />

            {/* Display tool invocations */}
            {message.toolInvocations?.map((toolInvocation: any) => (
              <ToolInvocationCard
                key={toolInvocation.toolCallId}
                toolInvocation={toolInvocation}
              />
            ))}
          </div>
        );
      })}

      {/* Timeout message */}
      {isTimeout && (
        <div className="mb-3 ml-0 mr-auto max-w-[85%]">
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="flex items-start gap-3">
              <svg className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div className="flex-1">
                <p className="text-sm text-red-800 font-medium mb-2">
                  响应超时
                </p>
                <p className="text-xs text-red-600 mb-3">
                  AI 响应时间过长，请重试或稍后再试
                </p>
                <button
                  onClick={retry}
                  className="px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white text-xs rounded transition-colors"
                >
                  重新发送
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      <div ref={messagesEndRef} />
    </div>
  );
}
