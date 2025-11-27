'use client';

import { useChat as useVercelChat } from '@ai-sdk/react';
import { useEffect, useRef, useState } from 'react';
import { useChatStore } from '@/lib/store';
import { toast } from '@/lib/toast';

const MESSAGE_TIMEOUT = 60000; // 60 seconds

export function useChat() {
  const { addMessage, clearMessages } = useChatStore();
  const [isTimeout, setIsTimeout] = useState(false);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Use any type to bypass strict typing issues with the AI SDK
  const chatHelpers: any = useVercelChat({});
  
  const {
    messages,
    input,
    handleInputChange,
    handleSubmit: originalHandleSubmit,
    isLoading,
    error,
    reload,
    stop,
    append,
    setMessages,
  } = chatHelpers;

  // Enhanced submit with timeout handling
  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    
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
    
    // Call original submit
    originalHandleSubmit(e);
  };

  // Retry last message
  const retry = () => {
    setIsTimeout(false);
    reload();
    
    // Set new timeout
    timeoutRef.current = setTimeout(() => {
      console.warn('Retry timeout - no response received within 60 seconds');
      setIsTimeout(true);
      stop();
    }, MESSAGE_TIMEOUT);
  };

  // Load chat history from store on mount
  useEffect(() => {
    const storedMessages = useChatStore.getState().messages;
    if (storedMessages.length > 0 && messages.length === 0) {
      setMessages(storedMessages);
    }
  }, []);

  // Sync messages to store
  useEffect(() => {
    if (messages.length > 0) {
      useChatStore.setState({ messages });
    }
  }, [messages]);

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
    input,
    handleInputChange,
    handleSubmit,
    isLoading,
    error,
    reload,
    stop,
    append,
    setMessages,
    isTimeout,
    retry,
    clearHistory: () => {
      clearMessages();
      setMessages([]);
    },
  };
}
