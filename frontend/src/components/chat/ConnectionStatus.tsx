'use client';

import { useChat } from '@/hooks/useChat';

export function ConnectionStatus() {
  const { isLoading, error } = useChat();

  // With SSE, we don't have a persistent connection
  // Show status based on loading/error state
  if (error) {
    return (
      <div className="flex items-center gap-1.5 text-xs text-white/90">
        <span className="w-2 h-2 rounded-full bg-red-500" />
        <span>连接错误</span>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center gap-1.5 text-xs text-white/90">
        <span className="w-2 h-2 rounded-full bg-yellow-500 animate-pulse" />
        <span>处理中...</span>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-1.5 text-xs text-white/90">
      <span className="w-2 h-2 rounded-full bg-green-500" />
      <span>就绪</span>
    </div>
  );
}
