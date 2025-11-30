'use client';

import { useChat as useVercelChat } from '@ai-sdk/react';
import { useEffect, useRef, useState, useCallback } from 'react';
import { useChatStore } from '@/lib/store';

const MESSAGE_TIMEOUT = 60000; // 60 seconds

export function useSessionChat(sessionId: string | null) {
  const {
    sessions,
    addMessageToSession,
    getCurrentSession,
  } = useChatStore();

  const [isTimeout, setIsTimeout] = useState(false);
  const [localInput, setLocalInput] = useState('');
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  const initializedRef = useRef(false);

  // Get current session messages
  const currentSession = sessions.find((s) => s.id === sessionId);
  const sessionMessages = currentSession?.messages || [];

  const chatHelpers = useVercelChat({
    id: sessionId || 'default-chat',
    api: '/api/chat',
    initialMessages: [],
  } as any);

  const {
    messages,
    status,
    error,
    regenerate,
    stop,
    sendMessage,
    setMessages,
  } = chatHelpers;

  const isLoading = status === 'streaming' || status === 'submitted';

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

  // Custom input handling
  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
      setLocalInput(e.target.value);
    },
    []
  );

  // Enhanced submit with timeout handling
  const handleSubmit = useCallback(
    async (e: React.FormEvent<HTMLFormElement>) => {
      e.preventDefault();

      if (!localInput.trim() || !sessionId) return;

      // Clear any existing timeout
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }

      setIsTimeout(false);

      // Set timeout for response
      timeoutRef.current = setTimeout(() => {
        console.warn('Message timeout - no response received within 60 seconds');
        setIsTimeout(true);
        stop();
      }, MESSAGE_TIMEOUT);

      const messageContent = localInput;
      setLocalInput('');

      // Send message - AI SDK v5 expects an object with parts
      await (sendMessage as any)({
        parts: [{ type: 'text', text: messageContent }],
      });
    },
    [localInput, sendMessage, stop, sessionId]
  );

  // Retry last message
  const retry = useCallback(() => {
    setIsTimeout(false);
    regenerate();

    // Set new timeout
    timeoutRef.current = setTimeout(() => {
      console.warn('Retry timeout - no response received within 60 seconds');
      setIsTimeout(true);
      stop();
    }, MESSAGE_TIMEOUT);
  }, [regenerate, stop]);

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

  // Clear timeout when loading completes
  useEffect(() => {
    if (!isLoading && timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
  }, [isLoading]);

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  return {
    messages,
    input: localInput,
    handleInputChange,
    handleSubmit,
    isLoading,
    error,
    reload: retry,
    stop,
    append: sendMessage,
    setMessages,
    isTimeout,
    retry,
  };
}
