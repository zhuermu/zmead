'use client';

import { useCallback, useEffect, useRef } from 'react';
import { useChatStore, ChatSession } from '@/lib/store';
import { api } from '@/lib/api';
import type { Message } from '@/hooks/useChat';

interface ConversationResponse {
  id: number;
  session_id: string;
  title: string | null;
  messages: Array<{
    id: string;
    role: string;
    content: string;
    tool_calls?: any[];
    tool_call_id?: string;
    metadata?: any;
    process_info?: string;
    attachments?: any[];  // Unified attachments (images, videos, documents, etc.)
    created_at?: string;
  }>;
  created_at: string;
  updated_at: string | null;
}

interface ConversationListResponse {
  conversations: Array<{
    id: number;
    session_id: string;
    title: string | null;
    message_count: number;
    created_at: string;
    updated_at: string | null;
  }>;
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
}

export function useConversationSync() {
  const {
    sessions,
    currentSessionId,
    setSessions,
    setIsLoadingFromDb,
    markSessionSynced,
    updateSessionMessages,
    updateSessionTitle,
  } = useChatStore();

  const syncInProgressRef = useRef(false);
  const lastSyncedMessagesRef = useRef<Map<string, number>>(new Map());

  // Load conversations from database on mount
  const loadConversations = useCallback(async () => {
    try {
      setIsLoadingFromDb(true);
      const response = await api.get<ConversationListResponse>('/conversations', {
        params: { page: 1, page_size: 50 },
      });

      const dbSessions: ChatSession[] = response.data.conversations.map((conv) => ({
        id: conv.session_id,
        title: conv.title || '新对话',
        messages: [], // Messages will be loaded when session is selected
        createdAt: new Date(conv.created_at),
        updatedAt: conv.updated_at ? new Date(conv.updated_at) : new Date(conv.created_at),
        synced: true,
      }));

      // Merge with local sessions (keep local sessions that aren't in DB yet)
      const localOnlySessions = sessions.filter(
        (s) => !s.synced && !dbSessions.find((db) => db.id === s.id)
      );

      setSessions([...localOnlySessions, ...dbSessions]);
    } catch (error) {
      console.error('Failed to load conversations:', error);
    } finally {
      setIsLoadingFromDb(false);
    }
  }, [sessions, setSessions, setIsLoadingFromDb]);

  // Load messages for a specific session
  const loadSessionMessages = useCallback(async (sessionId: string): Promise<Message[]> => {
    try {
      const response = await api.get<ConversationResponse>(`/conversations/${sessionId}`);
      
      const messages: Message[] = response.data.messages.map((msg) => ({
        id: msg.id,
        role: msg.role as 'user' | 'assistant' | 'system',
        content: msg.content,
        createdAt: msg.created_at ? new Date(msg.created_at) : new Date(),
        processInfo: msg.process_info,
        attachments: msg.attachments,
      }));

      updateSessionMessages(sessionId, messages);
      lastSyncedMessagesRef.current.set(sessionId, messages.length);
      
      if (response.data.title) {
        updateSessionTitle(sessionId, response.data.title);
      }

      return messages;
    } catch (error: any) {
      if (error.response?.status === 404) {
        // Session doesn't exist in DB yet, that's okay
        return [];
      }
      console.error('Failed to load session messages:', error);
      return [];
    }
  }, [updateSessionMessages, updateSessionTitle]);

  // Create a new conversation in database
  const createConversation = useCallback(async (sessionId: string, title: string = '新对话') => {
    try {
      await api.post('/conversations', {
        session_id: sessionId,
        title,
        messages: [],
      });
      markSessionSynced(sessionId);
    } catch (error: any) {
      if (error.response?.status === 409) {
        // Already exists, mark as synced
        markSessionSynced(sessionId);
      } else {
        console.error('Failed to create conversation:', error);
      }
    }
  }, [markSessionSynced]);

  // Save messages to database
  const saveMessages = useCallback(async (
    sessionId: string,
    messages: Message[],
    title?: string
  ) => {
    if (syncInProgressRef.current) return;
    
    const lastSyncedCount = lastSyncedMessagesRef.current.get(sessionId) || 0;
    const newMessages = messages.slice(lastSyncedCount);
    
    if (newMessages.length === 0 && !title) return;

    syncInProgressRef.current = true;
    try {
      const messagesToSave = newMessages.map((msg) => ({
        id: msg.id,
        role: msg.role,
        content: msg.content || '',
        metadata: {},
        process_info: msg.processInfo || null,  // Convert undefined to null for backend
        attachments: msg.attachments || null,  // Unified attachments format
        created_at: msg.createdAt instanceof Date
          ? msg.createdAt.toISOString()
          : typeof msg.createdAt === 'string'
            ? msg.createdAt
            : new Date().toISOString(),
      }));

      await api.patch(`/conversations/${sessionId}`, {
        title,
        messages: messagesToSave.length > 0 ? messagesToSave : undefined,
      });

      lastSyncedMessagesRef.current.set(sessionId, messages.length);
      markSessionSynced(sessionId);
    } catch (error: any) {
      if (error.response?.status === 404) {
        // Conversation doesn't exist, create it first
        await createConversation(sessionId, title);
        // Then try saving messages again
        if (messages.length > 0) {
          await saveMessages(sessionId, messages, title);
        }
      } else {
        console.error('Failed to save messages:', error);
      }
    } finally {
      syncInProgressRef.current = false;
    }
  }, [createConversation, markSessionSynced]);

  // Delete conversation from database
  const deleteConversation = useCallback(async (sessionId: string) => {
    try {
      await api.delete(`/conversations/${sessionId}`);
    } catch (error: any) {
      if (error.response?.status !== 404) {
        console.error('Failed to delete conversation:', error);
      }
    }
  }, []);

  return {
    loadConversations,
    loadSessionMessages,
    createConversation,
    saveMessages,
    deleteConversation,
  };
}
