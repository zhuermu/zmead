'use client';

import { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import { useChatStore } from '@/lib/store';
import { useAuth } from '@/components/auth/AuthProvider';

const MESSAGE_TIMEOUT = 60000; // 60 seconds

// Generated image data (supports both GCS object and fallback base64)
export interface GeneratedImage {
  index: number;
  format: string;
  size: number;
  // GCS storage (preferred) - frontend fetches signed URL
  object_name?: string;
  bucket?: string;
  gcs_url?: string;
  // Signed URL (resolved from object_name)
  signed_url?: string;
  // Fallback base64 (only if GCS upload fails)
  data_b64?: string;
}

// File attachment with S3 URL
export interface MessageAttachment {
  id: string;
  filename: string;
  contentType: string;
  size: number;
  s3Url: string;
  cdnUrl?: string;
  type: 'image' | 'video' | 'document' | 'other';
}

// Message type matching AI SDK format
export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  createdAt?: Date;
  // Agent process info (collapsible, contains thinking + actions + observations)
  // All intermediate process is consolidated here, only final text shows in main content
  processInfo?: string;
  // Generated images from tool calls
  generatedImages?: GeneratedImage[];
  // Generated video URL from tool calls (signed URL or data URL)
  generatedVideoUrl?: string;
  // GCS object name for video (used to fetch signed URL)
  videoObjectName?: string;
  // Uploaded file attachments (with S3 URLs)
  attachments?: MessageAttachment[];
}

// Helper function to extract string content from message
// Handles both string content and legacy AI SDK v5 format (parts array)
function getMessageContentAsString(msg: any): string {
  // Handle string content (current format)
  if (typeof msg.content === 'string') {
    return msg.content;
  }

  // Handle content array format
  if (Array.isArray(msg.content)) {
    return msg.content
      .filter((part: any) => part.type === 'text')
      .map((part: any) => part.text || '')
      .join('');
  }

  // Handle parts array format (legacy AI SDK v5 format)
  if (Array.isArray(msg.parts)) {
    return msg.parts
      .filter((part: any) => part.type === 'text')
      .map((part: any) => part.text || '')
      .join('');
  }

  return '';
}

// Agent status from streaming data
export interface AgentStatus {
  type: 'thinking' | 'status' | 'action' | 'observation' | 'thought';
  message?: string;
  node?: string;
  tool?: string;
  success?: boolean;
  result?: string;
}

// User input request option from Human-in-the-Loop
export interface UserInputOption {
  value: string;
  label: string;
  description?: string;
  primary?: boolean;
}

// User input request from Human-in-the-Loop
export interface UserInputRequest {
  type: 'confirmation' | 'selection' | 'input';
  question: string;
  message: string;
  options?: UserInputOption[];
  defaultValue?: string;
  metadata?: Record<string, any>;
}

interface UseChatSSEOptions {
  apiUrl?: string;
}

export function useChat(options: UseChatSSEOptions = {}) {
  // Use Edge Runtime API route for true streaming (no buffering)
  const { apiUrl = '/api/chat' } = options;
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
  const currentProcessInfoRef = useRef<string>('');
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

  // Fetch signed URL for GCS video object (defined early for use in load effect)
  const fetchSignedUrl = useCallback(async (objectName: string, messageId: string) => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`/api/media/signed-url/${encodeURIComponent(objectName)}`, {
        method: 'GET',
        headers: {
          ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
        },
      });

      if (!response.ok) {
        console.error('Failed to fetch signed URL:', response.status);
        return;
      }

      const data = await response.json();
      const signedUrl = data.signed_url;

      // Update the message with the signed URL
      setMessages(prev =>
        prev.map(msg =>
          msg.id === messageId
            ? { ...msg, generatedVideoUrl: signedUrl }
            : msg
        )
      );
    } catch (err) {
      console.error('Error fetching signed URL:', err);
    }
  }, []);

  // Fetch signed URL for GCS image object
  const fetchImageSignedUrl = useCallback(async (objectName: string, messageId: string, imageIndex: number) => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`/api/media/signed-url/${encodeURIComponent(objectName)}`, {
        method: 'GET',
        headers: {
          ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
        },
      });

      if (!response.ok) {
        console.error('Failed to fetch image signed URL:', response.status);
        return;
      }

      const data = await response.json();
      const signedUrl = data.signed_url;

      // Update the specific image in the message with the signed URL
      setMessages(prev =>
        prev.map(msg => {
          if (msg.id === messageId && msg.generatedImages) {
            const updatedImages = msg.generatedImages.map((img, idx) =>
              idx === imageIndex ? { ...img, signed_url: signedUrl } : img
            );
            return { ...msg, generatedImages: updatedImages };
          }
          return msg;
        })
      );
    } catch (err) {
      console.error('Error fetching image signed URL:', err);
    }
  }, []);

  // Load chat history from store on mount and refresh signed URLs
  useEffect(() => {
    const storedMessages = useChatStore.getState().messages;
    if (storedMessages.length > 0 && messages.length === 0) {
      const loadedMessages = storedMessages as Message[];
      setMessages(loadedMessages);

      // Re-fetch signed URLs for messages that have videoObjectName but no valid URL
      loadedMessages.forEach((msg) => {
        if (msg.videoObjectName && !msg.generatedVideoUrl) {
          fetchSignedUrl(msg.videoObjectName, msg.id);
        }
        // Re-fetch signed URLs for images with GCS object names
        if (msg.generatedImages) {
          msg.generatedImages.forEach((img, idx) => {
            if (img.object_name && !img.signed_url && !img.data_b64) {
              fetchImageSignedUrl(img.object_name, msg.id, idx);
            }
          });
        }
      });
    }
  }, [messages.length, fetchSignedUrl, fetchImageSignedUrl]);

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
  const sendMessage = useCallback(async (
    content: string,
    attachments?: any[]  // Can be MessageAttachment[] or temp attachment references
  ) => {
    if (!content.trim() || isLoading) return;

    // Close any existing connection
    closeEventSource();

    // Clear previous state
    setError(null);
    setIsTimeout(false);
    setAgentStatus(null);
    setUserInputRequest(null);
    currentAssistantMessageRef.current = '';
    currentProcessInfoRef.current = '';

    // Add user message with attachments (for display only)
    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: content.trim(),
      createdAt: new Date(),
      attachments: [], // Display doesn't need full attachments yet
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

      // Determine if attachments are temp files or permanent files
      const hasTempAttachments = attachments && attachments.length > 0 && 'fileKey' in attachments[0];

      // Build messages array (conversation history + current message)
      // Ensure content is always a string (handle legacy AI SDK v5 format)
      const allMessages = [
        ...messages.map(msg => ({
          role: msg.role,
          content: getMessageContentAsString(msg),
        })).filter(msg => msg.content), // Filter out empty messages
        {
          role: 'user',
          content: content.trim(),
          // Send tempAttachments if they are temp files, otherwise send attachments
          ...(hasTempAttachments
            ? { tempAttachments: attachments }
            : { attachments: attachments || [] }
          ),
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
          user_id: String(user?.id || 'anonymous'),
          session_id: sessionId,
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
              // All process info (thought, action, observation) goes into processInfo
              // Only 'text' type goes to main content
              if (event.type === 'thought') {
                // Agent's thinking process - append to processInfo
                if (event.content) {
                  currentProcessInfoRef.current += event.content;
                  setMessages(prev =>
                    prev.map(msg =>
                      msg.id === currentMessageIdRef.current
                        ? { ...msg, processInfo: currentProcessInfoRef.current }
                        : msg
                    )
                  );
                  setAgentStatus({
                    type: 'thought',
                    message: 'Thinking...',
                  });
                }
              } else if (event.type === 'text' || event.type === 'token') {
                // Final response text - append to main content field
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
              } else if (event.type === 'action') {
                // Tool execution - append to processInfo
                const actionText = `\n🔧 ${event.tool}: ${event.message || 'Executing...'}`;
                currentProcessInfoRef.current += actionText;
                setMessages(prev =>
                  prev.map(msg =>
                    msg.id === currentMessageIdRef.current
                      ? { ...msg, processInfo: currentProcessInfoRef.current }
                      : msg
                  )
                );
                setAgentStatus({
                  type: 'action',
                  message: event.message,
                  tool: event.tool,
                });
              } else if (event.type === 'observation') {
                // Tool result - append to processInfo
                const resultText = `\n${event.success ? '✅' : '❌'} Result: ${event.result || 'No result'}`;
                currentProcessInfoRef.current += resultText;

                // Extract generated images/videos from observation
                const generatedImages = event.images as GeneratedImage[] | undefined;
                // Video object name for signed URL (stored as pending, resolved later)
                const videoObjectName = event.video_object_name as string | undefined;

                // Priority: GCS object name > base64 > direct URL
                let generatedVideoUrl: string | undefined;
                let pendingVideoObjectName: string | undefined;

                if (videoObjectName) {
                  // Store object name - will be resolved to signed URL
                  pendingVideoObjectName = videoObjectName;
                } else if (event.video_data_b64) {
                  // Create data URL from base64 video data
                  const videoFormat = event.video_format || 'mp4';
                  generatedVideoUrl = `data:video/${videoFormat};base64,${event.video_data_b64}`;
                } else if (event.video_url) {
                  generatedVideoUrl = event.video_url as string;
                }

                // Process images - fetch signed URLs for GCS objects
                const processedImages = generatedImages ? [...generatedImages] : [];
                
                setMessages(prev =>
                  prev.map(msg => {
                    if (msg.id === currentMessageIdRef.current) {
                      const updates: Partial<Message> = {
                        processInfo: currentProcessInfoRef.current,
                      };
                      // Append new images to existing ones
                      if (processedImages.length > 0) {
                        updates.generatedImages = [
                          ...(msg.generatedImages || []),
                          ...processedImages,
                        ];
                      }
                      if (generatedVideoUrl) {
                        updates.generatedVideoUrl = generatedVideoUrl;
                      }
                      if (pendingVideoObjectName) {
                        // Store object name for later resolution
                        (updates as any).videoObjectName = pendingVideoObjectName;
                      }
                      return { ...msg, ...updates };
                    }
                    return msg;
                  })
                );

                // Fetch signed URLs for images with GCS object names
                if (processedImages.length > 0) {
                  processedImages.forEach((img, idx) => {
                    if (img.object_name && !img.signed_url && !img.data_b64) {
                      fetchImageSignedUrl(img.object_name, currentMessageIdRef.current, idx);
                    }
                  });
                }

                // If we have a video object name, fetch the signed URL
                if (pendingVideoObjectName) {
                  fetchSignedUrl(pendingVideoObjectName, currentMessageIdRef.current);
                }
                setAgentStatus({
                  type: 'observation',
                  message: event.result || (event.success ? '执行成功' : '执行失败'),
                  tool: event.tool,
                  success: event.success,
                  result: event.result,
                });
              } else if (event.type === 'thinking' || event.type === 'status') {
                // Initial thinking status - just update status indicator
                setAgentStatus({
                  type: event.type,
                  message: event.message,
                });
              } else if (event.type === 'user_input_request') {
                // Human-in-the-Loop request
                // Data structure: { type, data: { type, question, options, ... }, message }
                const requestData = event.data || {};
                setUserInputRequest({
                  type: requestData.type || 'selection',
                  question: requestData.question || event.message || '',
                  message: event.message || requestData.question || '',
                  options: requestData.options || [],
                  defaultValue: requestData.default_value,
                  metadata: requestData.metadata,
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
