'use client';

import { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import { useChatStore } from '@/lib/store';
import { useAuth } from '@/components/auth/AuthProvider';

const MESSAGE_TIMEOUT = 60000; // 60 seconds

// Message type matching AI SDK format
export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  createdAt?: Date;
}

// Agent status from streaming data
export interface AgentStatus {
  type: 'thinking' | 'status' | 'tool_start' | 'tool_complete';
  message?: string;
  node?: string;
  tool?: string;
}

// User input request from Human-in-the-Loop
export interface UserInputRequest {
  type: 'confirmation' | 'selection' | 'input';
  message: string;
  options?: string[];
}

interface UseChatSSEOptions {
  apiUrl?: string;
}

export function useChat(options: UseChatSSEOptions = {}) {
  const { apiUrl = '/api/v1/chat' } = options;
  const { clearMessages } = useChatStore();
  const { user } = useAuth();
  
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [isTimeout, setIsTimeout] = useState(false);
  const [agentStatus, setAgentStatus] = useState<AgentStatus | null>(null);
  const [userInputRequest, setUserInputRequest] = useState<UserInputRequest | null>(null);
  
  const eventSourceRef = useRef<EventSource | null>(null);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  const currentAssistantMessageRef = useRef<string>('');
  const currentMessageIdRef = useRef<string>('');

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

  // Load chat history from store on mount
  useEffect(() => {
    const storedMessages = useChatStore.getState().messages;
    if (storedMessages.length > 0 && messages.length === 0) {
      setMessages(storedMessages as Message[]);
    }
  }, [messages.length]);

  // Sync messages to store
  useEffect(() => {
    if (messages.length > 0) {
      useChatStore.setState({ messages: messages as any });
    }
  }, [messages]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  // Close existing EventSource
  const closeEventSource = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
  }, []);

  // Handle input change
  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setInput(e.target.value);
  }, []);

  // Send message using fetch + EventSource
  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim() || isLoading) return;

    // Close any existing connection
    closeEventSource();

    // Clear previous state
    setError(null);
    setIsTimeout(false);
    setAgentStatus(null);
    setUserInputRequest(null);
    currentAssistantMessageRef.current = '';
    
    // Add user message
    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: content.trim(),
      createdAt: new Date(),
    };
    
    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    // Create assistant message placeholder
    const assistantMessageId = `assistant-${Date.now()}`;
    currentMessageIdRef.current = assistantMessageId;
    
    const assistantMessage: Message = {
      id: assistantMessageId,
      role: 'assistant',
      content: '',
      createdAt: new Date(),
    };
    
    setMessages(prev => [...prev, assistantMessage]);

    // Set timeout
    timeoutRef.current = setTimeout(() => {
      console.warn('Message timeout - no response received within 60 seconds');
      setIsTimeout(true);
      setIsLoading(false);
      closeEventSource();
    }, MESSAGE_TIMEOUT);

    try {
      // Get auth token
      const token = localStorage.getItem('access_token');
      
      // Build messages array (conversation history + current message)
      const allMessages = [
        ...messages.map(msg => ({
          role: msg.role,
          content: msg.content,
        })),
        {
          role: 'user',
          content: content.trim(),
        }
      ];

      // Send POST request to initiate SSE stream
      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          messages: allMessages,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      // Read SSE stream
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error('No response body');
      }

      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        
        if (done) {
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            
            if (data === '[DONE]') {
              continue;
            }

            try {
              const event = JSON.parse(data);
              
              // Handle different event types
              if (event.type === 'text' || event.type === 'token') {
                // Append text to current assistant message
                if (event.content) {
                  currentAssistantMessageRef.current += event.content;
                  setMessages(prev => 
                    prev.map(msg => 
                      msg.id === currentMessageIdRef.current
                        ? { ...msg, content: currentAssistantMessageRef.current }
                        : msg
                    )
                  );
                }
              } else if (event.type === 'thinking' || event.type === 'status' || event.type === 'tool_start' || event.type === 'tool_complete') {
                // Update agent status
                setAgentStatus({
                  type: event.type,
                  message: event.message,
                  node: event.node,
                  tool: event.tool,
                });
              } else if (event.type === 'user_input_request') {
                // Human-in-the-Loop request
                setUserInputRequest({
                  type: event.input_type || 'confirmation',
                  message: event.message || '',
                  options: event.options,
                });
              } else if (event.type === 'done') {
                // Stream complete
                setAgentStatus(null);
              } else if (event.type === 'error') {
                throw new Error(event.error || 'Unknown error');
              }
            } catch (e) {
              console.error('Failed to parse SSE event:', e);
            }
          }
        }
      }

      // Clear timeout on success
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }

    } catch (err) {
      console.error('Chat error:', err);
      setError(err instanceof Error ? err : new Error('Unknown error'));
      
      // Remove empty assistant message on error
      setMessages(prev => prev.filter(msg => msg.id !== currentMessageIdRef.current || msg.content));
    } finally {
      setIsLoading(false);
      closeEventSource();
    }
  }, [isLoading, messages, user, sessionId, apiUrl, closeEventSource]);

  // Handle form submit
  const handleSubmit = useCallback(async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!input.trim()) return;
    
    const messageContent = input;
    setInput('');
    await sendMessage(messageContent);
  }, [input, sendMessage]);

  // Retry last message
  const retry = useCallback(() => {
    const lastUserMessage = [...messages].reverse().find(msg => msg.role === 'user');
    if (lastUserMessage) {
      // Remove last assistant message if exists
      setMessages(prev => {
        const lastAssistantIndex = prev.map(m => m.role).lastIndexOf('assistant');
        if (lastAssistantIndex > -1) {
          return prev.slice(0, lastAssistantIndex);
        }
        return prev;
      });
      
      setIsTimeout(false);
      sendMessage(lastUserMessage.content);
    }
  }, [messages, sendMessage]);

  // Stop current generation
  const stop = useCallback(() => {
    closeEventSource();
    setIsLoading(false);
    setAgentStatus(null);
  }, [closeEventSource]);

  // Clear history
  const clearHistory = useCallback(() => {
    clearMessages();
    setMessages([]);
    setInput('');
    setError(null);
    setIsTimeout(false);
    setAgentStatus(null);
    setUserInputRequest(null);
  }, [clearMessages]);

  // Respond to user input request
  const respondToUserInput = useCallback(async (response: string) => {
    if (!userInputRequest) return;
    
    setUserInputRequest(null);
    await sendMessage(response);
  }, [userInputRequest, sendMessage]);

  return {
    messages,
    input,
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
    agentStatus,
    userInputRequest,
    respondToUserInput,
    clearHistory,
  };
}
