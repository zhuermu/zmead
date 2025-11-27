'use client';

import { useChat } from '@/hooks/useChat';
import { useState, useRef } from 'react';

export function ChatInput() {
  const { input, handleInputChange, handleSubmit, isLoading, stop } = useChat();
  const [isComposing, setIsComposing] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const onSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!input.trim() || isLoading || isComposing) return;
    handleSubmit(e);
    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Submit on Enter (without Shift)
    if (e.key === 'Enter' && !e.shiftKey && !isComposing) {
      e.preventDefault();
      const formEvent = new Event('submit', { bubbles: true, cancelable: true }) as unknown as React.FormEvent<HTMLFormElement>;
      onSubmit(formEvent);
    }
  };

  const handleTextareaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    handleInputChange(e);
    
    // Auto-resize textarea
    const textarea = e.target;
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
  };

  return (
    <form onSubmit={onSubmit} className="p-4 border-t border-gray-200 bg-gray-50">
      <div className="flex gap-2 items-end">
        {/* Text Input */}
        <div className="flex-1 relative">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={handleTextareaChange}
            onKeyDown={handleKeyDown}
            onCompositionStart={() => setIsComposing(true)}
            onCompositionEnd={() => setIsComposing(false)}
            placeholder="输入消息... (Enter 发送, Shift+Enter 换行)"
            disabled={isLoading}
            rows={1}
            className="w-full px-4 py-3 pr-12 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed resize-none text-sm"
            style={{ minHeight: '44px', maxHeight: '120px' }}
          />
          
          {/* Attachment button (placeholder for future) */}
          <button
            type="button"
            className="absolute right-2 bottom-2 p-1.5 text-gray-400 hover:text-gray-600 transition-colors"
            title="附加文件 (即将推出)"
            disabled
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
            </svg>
          </button>
        </div>

        {/* Send/Stop Button */}
        {isLoading ? (
          <button
            type="button"
            onClick={stop}
            className="px-4 py-3 bg-red-500 hover:bg-red-600 text-white rounded-lg transition-colors flex items-center gap-2 font-medium text-sm"
          >
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
              <rect x="6" y="6" width="12" height="12" />
            </svg>
            停止
          </button>
        ) : (
          <button
            type="submit"
            disabled={!input.trim() || isComposing}
            className="px-4 py-3 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 font-medium text-sm"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
            发送
          </button>
        )}
      </div>

      {/* Helper text */}
      <div className="mt-2 text-xs text-gray-500 flex items-center gap-4">
        <span>💡 提示: Enter 发送, Shift+Enter 换行</span>
      </div>
    </form>
  );
}
