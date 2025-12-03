'use client';

import { useChat } from '@/hooks/useChat';
import { useEffect, useRef, useCallback } from 'react';
import { useChatStore } from '@/lib/store';

export function useSessionChat(sessionId: string | null) {
  const {
    sessions,
    addMessageToSession,
  } = useChatStore();

  const initializedRef = useRef(false);

  // Get current session messages
  const currentSession = sessions.find((s) => s.id === sessionId);
  const sessionMessages = currentSession?.messages || [];

  const chatHelpers = useChat();

  const {
    messages,
    isLoading,
    error,
    retry: regenerate,
    stop,
    append: sendMessage,
    setMessages,
    isTimeout,
    input: localInput,
    handleInputChange: baseHandleInputChange,
    handleSubmit: baseHandleSubmit,
  } = chatHelpers;

  // Initialize messages from session when sessionId changes
  useEffect(() => {
    if (sessionId && sessionMessages.length > 0 && !initializedRef.current) {
      setMessages(sessionMessages as any);
      initializedRef.current = true;
    }
    // Reset flag when session changes
    return () => {
      initializedRef.current = false;
    };
  }, [sessionId, sessionMessages, setMessages]);

  // Custom input handling - wraps base handler
  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
      baseHandleInputChange(e);
    },
    [baseHandleInputChange]
  );

  // Enhanced submit - wraps base handler
  const handleSubmit = useCallback(
    async (e: React.FormEvent<HTMLFormElement>) => {
      if (!sessionId) return;
      await baseHandleSubmit(e);
    },
    [sessionId, baseHandleSubmit]
  );

  // Sync messages to store when they change
  useEffect(() => {
    if (sessionId && messages.length > 0) {
      // Only add the latest message if it's new
      const lastMessage = messages[messages.length - 1];
      const sessionLastMsg = sessionMessages[sessionMessages.length - 1];

      if (!sessionLastMsg || lastMessage.id !== sessionLastMsg.id) {
        addMessageToSession(sessionId, lastMessage as any);
      }
    }
  }, [sessionId, messages, sessionMessages, addMessageToSession]);

  return {
    messages,
    input: localInput,
    handleInputChange,
    handleSubmit,
    isLoading,
    error,
    reload: regenerate,
    stop,
    append: sendMessage,
    setMessages,
    isTimeout,
    retry: regenerate,
  };
}
