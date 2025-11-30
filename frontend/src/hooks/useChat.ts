'use client';

import { useChat as useVercelChat } from '@ai-sdk/react';
import { useEffect, useRef, useState, useCallback } from 'react';
import { useChatStore } from '@/lib/store';

const MESSAGE_TIMEOUT = 60000; // 60 seconds

export function useChat() {
  const { clearMessages } = useChatStore();
  const [isTimeout, setIsTimeout] = useState(false);
  const [localInput, setLocalInput] = useState('');
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  const chatHelpers = useVercelChat({
    id: 'main-chat',
    api: '/api/chat',
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

  // Custom input handling
  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setLocalInput(e.target.value);
  }, []);

  // Enhanced submit with timeout handling
  const handleSubmit = useCallback(async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    
    if (!localInput.trim()) return;
    
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
  }, [localInput, sendMessage, stop]);

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

  // Load chat history from store on mount
  useEffect(() => {
    const storedMessages = useChatStore.getState().messages;
    if (storedMessages.length > 0 && messages.length === 0) {
      setMessages(storedMessages as any);
    }
  }, [setMessages, messages.length]);

  // Sync messages to store
  useEffect(() => {
    if (messages.length > 0) {
      useChatStore.setState({ messages: messages as any });
    }
  }, [messages]);

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
    clearHistory: () => {
      clearMessages();
      setMessages([]);
    },
  };
}
