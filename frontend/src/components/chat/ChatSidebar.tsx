'use client';

import { useChatStore, ChatSession } from '@/lib/store';
import { useAuth } from '@/components/auth';
import Link from 'next/link';

interface ChatSidebarProps {
  onNewChat: () => void;
}

export function ChatSidebar({ onNewChat }: ChatSidebarProps) {
  const { user } = useAuth();
  const {
    sessions,
    currentSessionId,
    selectSession,
    deleteSession,
    sidebarOpen,
    toggleSidebar,
  } = useChatStore();

  // Group sessions by date
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);
  const sevenDaysAgo = new Date(today);
  sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);

  const groupedSessions = {
    today: [] as ChatSession[],
    yesterday: [] as ChatSession[],
    lastWeek: [] as ChatSession[],
    older: [] as ChatSession[],
  };

  sessions.forEach((session) => {
    const sessionDate = new Date(session.updatedAt);
    sessionDate.setHours(0, 0, 0, 0);

    if (sessionDate >= today) {
      groupedSessions.today.push(session);
    } else if (sessionDate >= yesterday) {
      groupedSessions.yesterday.push(session);
    } else if (sessionDate >= sevenDaysAgo) {
      groupedSessions.lastWeek.push(session);
    } else {
      groupedSessions.older.push(session);
    }
  });

  const SessionItem = ({ session }: { session: ChatSession }) => {
    const isActive = session.id === currentSessionId;

    return (
      <div
        className={`group flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer transition-colors ${
          isActive
            ? 'bg-blue-50 text-blue-700'
            : 'hover:bg-gray-100 text-gray-700'
        }`}
        onClick={() => selectSession(session.id)}
      >
        <svg
          className="w-4 h-4 flex-shrink-0"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
          />
        </svg>
        <span className="flex-1 text-sm truncate">{session.title}</span>
        <button
          className="opacity-0 group-hover:opacity-100 p-1 hover:bg-gray-200 rounded transition-opacity"
          onClick={(e) => {
            e.stopPropagation();
            deleteSession(session.id);
          }}
        >
          <svg
            className="w-4 h-4 text-gray-500"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
            />
          </svg>
        </button>
      </div>
    );
  };

  const SessionGroup = ({
    title,
    sessions,
  }: {
    title: string;
    sessions: ChatSession[];
  }) => {
    if (sessions.length === 0) return null;

    return (
      <div className="mb-4">
        <h3 className="px-3 mb-1 text-xs font-medium text-gray-500 uppercase">
          {title}
        </h3>
        <div className="space-y-1">
          {sessions.map((session) => (
            <SessionItem key={session.id} session={session} />
          ))}
        </div>
      </div>
    );
  };

  if (!sidebarOpen) {
    return (
      <div className="w-12 bg-gray-50 border-r border-gray-200 flex flex-col items-center py-4">
        <button
          onClick={toggleSidebar}
          className="p-2 hover:bg-gray-200 rounded-lg transition-colors"
          title="展开侧边栏"
        >
          <svg
            className="w-5 h-5 text-gray-600"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 5l7 7-7 7"
            />
          </svg>
        </button>
        <button
          onClick={onNewChat}
          className="mt-4 p-2 hover:bg-gray-200 rounded-lg transition-colors"
          title="新对话"
        >
          <svg
            className="w-5 h-5 text-gray-600"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 4v16m8-8H4"
            />
          </svg>
        </button>
      </div>
    );
  }

  return (
    <div className="w-64 bg-gray-50 border-r border-gray-200 flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
        <Link href="/dashboard" className="flex items-center gap-2">
          <div className="w-7 h-7 bg-blue-600 rounded-lg flex items-center justify-center">
            <svg
              className="w-4 h-4 text-white"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M13 10V3L4 14h7v7l9-11h-7z"
              />
            </svg>
          </div>
          <span className="text-base font-semibold text-gray-900">AAE Chat</span>
        </Link>
        <button
          onClick={toggleSidebar}
          className="p-1.5 hover:bg-gray-200 rounded-lg transition-colors"
        >
          <svg
            className="w-5 h-5 text-gray-600"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M15 19l-7-7 7-7"
            />
          </svg>
        </button>
      </div>

      {/* New Chat Button */}
      <div className="p-3">
        <button
          onClick={onNewChat}
          className="w-full flex items-center gap-2 px-4 py-2.5 bg-white border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 hover:border-gray-400 transition-colors"
        >
          <svg
            className="w-4 h-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 4v16m8-8H4"
            />
          </svg>
          发起新对话
        </button>
      </div>

      {/* Sessions List */}
      <div className="flex-1 overflow-y-auto px-2">
        <SessionGroup title="今天" sessions={groupedSessions.today} />
        <SessionGroup title="昨天" sessions={groupedSessions.yesterday} />
        <SessionGroup title="近7天" sessions={groupedSessions.lastWeek} />
        <SessionGroup title="更早" sessions={groupedSessions.older} />

        {sessions.length === 0 && (
          <div className="px-3 py-8 text-center text-gray-500 text-sm">
            暂无对话记录
          </div>
        )}
      </div>

      {/* User Info */}
      {user && (
        <div className="p-3 border-t border-gray-200">
          <Link
            href="/dashboard"
            className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-gray-100 transition-colors"
          >
            {user.avatarUrl ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={user.avatarUrl}
                alt={user.displayName}
                className="w-8 h-8 rounded-full"
              />
            ) : (
              <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center">
                <span className="text-sm font-medium text-white">
                  {user.displayName.charAt(0).toUpperCase()}
                </span>
              </div>
            )}
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900 truncate">
                {user.displayName}
              </p>
              <p className="text-xs text-gray-500 truncate">{user.email}</p>
            </div>
          </Link>
        </div>
      )}
    </div>
  );
}
