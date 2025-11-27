'use client';

import { useWebSocket } from '@/hooks/useWebSocket';

export function ConnectionStatus() {
  const { connectionState } = useWebSocket();

  const statusConfig = {
    connected: {
      color: 'bg-green-500',
      text: '已连接',
      icon: '●',
    },
    connecting: {
      color: 'bg-yellow-500',
      text: '连接中...',
      icon: '●',
    },
    reconnecting: {
      color: 'bg-yellow-500',
      text: '重连中...',
      icon: '●',
    },
    disconnected: {
      color: 'bg-red-500',
      text: '已断开',
      icon: '●',
    },
  };

  const status = statusConfig[connectionState] || statusConfig.disconnected;

  return (
    <div className="flex items-center gap-1.5 text-xs text-white/90">
      <span className={`w-2 h-2 rounded-full ${status.color} ${connectionState === 'connecting' || connectionState === 'reconnecting' ? 'animate-pulse' : ''}`} />
      <span>{status.text}</span>
    </div>
  );
}
