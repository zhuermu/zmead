'use client';

import { useCallback } from 'react';
import { ProtectedRoute } from '@/components/auth';
import { ChatSidebar, ChatArea } from '@/components/chat';
import { useChatStore } from '@/lib/store';

function ChatContent() {
  const { currentSessionId, createSession, sidebarOpen } = useChatStore();

  const handleNewChat = useCallback(() => {
    createSession();
  }, [createSession]);

  const handleFirstMessage = useCallback(() => {
    // If no session exists, create one before the first message
    if (!currentSessionId) {
      createSession();
    }
  }, [currentSessionId, createSession]);

  return (
    <div className="flex h-screen bg-white">
      {/* Sidebar */}
      <ChatSidebar onNewChat={handleNewChat} />

      {/* Main Chat Area */}
      <div
        className={`flex-1 flex flex-col transition-all duration-300 ${
          sidebarOpen ? '' : ''
        }`}
      >
        <ChatArea
          sessionId={currentSessionId}
          onFirstMessage={handleFirstMessage}
        />
      </div>
    </div>
  );
}

export default function ChatPage() {
  return (
    <ProtectedRoute>
      <ChatContent />
    </ProtectedRoute>
  );
}
