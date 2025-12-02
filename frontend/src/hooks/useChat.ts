'use client';

import { useChat as useVercelChat } from '@ai-sdk/react';
import { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import { useChatStore } from '@/lib/store';
import { useAuth } from '@/components/auth/AuthProvider';

const MESSAGE_TIMEOUT = 60000; // 60 seconds

// Type for agent status from streaming data
export interface AgentStatus {
  type: 'thinking' | 'status' | 'tool_start' | 'tool_complete';
  message?: string;
  node?: string;
  tool?: string;
}

// Type for generated images from v3 API
export interface GeneratedImage {
  imageData: string; // base64 or URL
  mimeType: string;
}

interface UseChatOptions {
  /** Use v3 API (Gemini 3 with sub-agents) */
  useV3?: boolean;
}

export function useChat(options: UseChatOptions = {}) {
  const { useV3 = true } = options; // Default to v3
  const { clearMessages } = useChatStore();
  const { user } = useAuth();
  const [isTimeout, setIsTimeout] = useState(false);
  const [localInput, setLocalInput] = useState('');
  const [agentStatus, setAgentStatus] = useState<AgentStatus | null>(null);
  const [generatedImages, setGeneratedImages] = useState<GeneratedImage[]>([]);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Select API endpoint based on version
  const apiEndpoint = useV3 ? '/api/chat/v3' : '/api/chat';

  // Generate stable session ID
  const sessionId = useMemo(() => {
    const stored = typeof window !== 'undefined' ? sessionStorage.getItem('chat_session_id') : null;
    if (stored) return stored;
    const newId = `session-${user?.id || 'anon'}-${Date.now().toString(36)}`;
    if (typeof window !== 'undefined') {
      sessionStorage.setItem('chat_session_id', newId);
    }
    return newId;
  }, [user?.id]);

  const chatHelpers = useVercelChat({
    id: 'main-chat',
    api: apiEndpoint,
    // Pass user_id and session_id in request body
    body: {
      user_id: user?.id?.toString() || 'anonymous',
      session_id: sessionId,
    },
    // Handle custom data parts from streaming
    // onData is called for data-* type events
    onData: (dataPart: any) => {
      console.log('useChat onData received:', dataPart);
      // dataPart contains type and data fields
      if (dataPart && dataPart.type === 'data-agent-status' && dataPart.data) {
        const statusData = dataPart.data;
        setAgentStatus({
          type: statusData.statusType as AgentStatus['type'],
          message: statusData.message,
          node: statusData.node,
          tool: statusData.tool,
        });
      }
      // Handle generated images from v3 API
      if (dataPart && dataPart.type === 'data-image' && dataPart.data) {
        setGeneratedImages(prev => [...prev, {
          imageData: dataPart.data.imageData,
          mimeType: dataPart.data.mimeType || 'image/png',
        }]);
      }
    },
    onFinish: () => {
      // Clear agent status when streaming finishes
      setAgentStatus(null);
    },
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

  // Clear generated images when starting a new message
  const handleSubmitWithClear = useCallback(async (e: React.FormEvent<HTMLFormElement>) => {
    setGeneratedImages([]); // Clear previous images
    return handleSubmit(e);
  }, [handleSubmit]);

  return {
    messages,
    input: localInput,
    handleInputChange,
    handleSubmit: handleSubmitWithClear,
    isLoading,
    error,
    reload: retry,
    stop,
    append: sendMessage,
    setMessages,
    isTimeout,
    retry,
    agentStatus,
    generatedImages,
    clearHistory: () => {
      clearMessages();
      setMessages([]);
      setGeneratedImages([]);
    },
    /** Whether using v3 API */
    isV3: useV3,
  };
}
