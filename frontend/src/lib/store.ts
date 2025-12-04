/**
 * Global state management using Zustand.
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface User {
  id: number;
  email: string;
  displayName: string;
  avatarUrl?: string;
  giftedCredits: number;
  purchasedCredits: number;
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  setUser: (user: User | null) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      isAuthenticated: false,
      setUser: (user) => set({ user, isAuthenticated: !!user }),
      logout: () => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        set({ user: null, isAuthenticated: false });
      },
    }),
    {
      name: 'auth-storage',
    }
  )
);

import type { Message } from '@/hooks/useChat';

// Chat session interface
export interface ChatSession {
  id: string;
  title: string;
  messages: Message[];
  createdAt: Date;
  updatedAt: Date;
  synced?: boolean; // Whether this session is synced with backend
}

interface ChatState {
  // Legacy state for floating chat window
  isOpen: boolean;
  messages: Message[];
  toggleChat: () => void;
  openChat: () => void;
  closeChat: () => void;
  addMessage: (message: Message) => void;
  clearMessages: () => void;

  // New state for full-page chat with sessions
  sessions: ChatSession[];
  currentSessionId: string | null;
  sidebarOpen: boolean;
  isLoadingFromDb: boolean;
  pendingDeleteId: string | null; // For delete confirmation

  // Session actions
  createSession: () => string;
  deleteSession: (sessionId: string) => void;
  confirmDeleteSession: (sessionId: string) => void;
  cancelDeleteSession: () => void;
  selectSession: (sessionId: string) => void;
  getCurrentSession: () => ChatSession | null;
  addMessageToSession: (sessionId: string, message: Message) => void;
  updateSessionTitle: (sessionId: string, title: string) => void;
  updateSessionMessages: (sessionId: string, messages: Message[]) => void;
  toggleSidebar: () => void;
  setIsLoadingFromDb: (loading: boolean) => void;
  setSessions: (sessions: ChatSession[]) => void;
  markSessionSynced: (sessionId: string) => void;
}

// Generate unique session ID
const generateSessionId = () => `session-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;

// Generate title from first message
const generateTitleFromMessage = (content: string): string => {
  const maxLength = 30;
  const cleaned = content.replace(/\n/g, ' ').trim();
  return cleaned.length > maxLength ? cleaned.slice(0, maxLength) + '...' : cleaned;
};

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
      // Legacy state
      isOpen: false,
      messages: [],
      toggleChat: () => set((state) => ({ isOpen: !state.isOpen })),
      openChat: () => set({ isOpen: true }),
      closeChat: () => set({ isOpen: false }),
      addMessage: (message) =>
        set((state) => ({
          messages: [...state.messages, message],
        })),
      clearMessages: () => set({ messages: [] }),

      // New session-based state
      sessions: [],
      currentSessionId: null,
      sidebarOpen: true,
      isLoadingFromDb: false,
      pendingDeleteId: null,

      createSession: () => {
        const newSession: ChatSession = {
          id: generateSessionId(),
          title: '新对话',
          messages: [],
          createdAt: new Date(),
          updatedAt: new Date(),
          synced: false,
        };
        set((state) => ({
          sessions: [newSession, ...state.sessions],
          currentSessionId: newSession.id,
        }));
        return newSession.id;
      },

      confirmDeleteSession: (sessionId: string) => {
        set({ pendingDeleteId: sessionId });
      },

      cancelDeleteSession: () => {
        set({ pendingDeleteId: null });
      },

      deleteSession: (sessionId: string) => {
        set((state) => {
          const newSessions = state.sessions.filter((s) => s.id !== sessionId);
          // If deleting current session, clear messages and select another or create new
          let newCurrentId = state.currentSessionId;
          if (state.currentSessionId === sessionId) {
            newCurrentId = newSessions[0]?.id || null;
          }
          return {
            sessions: newSessions,
            currentSessionId: newCurrentId,
            pendingDeleteId: null,
          };
        });
      },

      selectSession: (sessionId: string) => {
        set({ currentSessionId: sessionId });
      },

      getCurrentSession: () => {
        const state = get();
        return state.sessions.find((s) => s.id === state.currentSessionId) || null;
      },

      addMessageToSession: (sessionId: string, message: Message) => {
        set((state) => {
          const sessions = state.sessions.map((session) => {
            if (session.id !== sessionId) return session;

            const updatedMessages = [...session.messages, message];
            // Auto-generate title from first user message
            let title = session.title;
            if (
              session.title === '新对话' &&
              message.role === 'user' &&
              typeof (message as any).content === 'string'
            ) {
              title = generateTitleFromMessage((message as any).content);
            } else if (
              session.title === '新对话' &&
              message.role === 'user' &&
              Array.isArray((message as any).parts)
            ) {
              const textPart = (message as any).parts.find((p: any) => p.type === 'text');
              if (textPart) {
                title = generateTitleFromMessage(textPart.text);
              }
            }

            return {
              ...session,
              title,
              messages: updatedMessages,
              updatedAt: new Date(),
            };
          });
          return { sessions };
        });
      },

      updateSessionTitle: (sessionId: string, title: string) => {
        set((state) => ({
          sessions: state.sessions.map((s) =>
            s.id === sessionId ? { ...s, title, updatedAt: new Date() } : s
          ),
        }));
      },

      updateSessionMessages: (sessionId: string, messages: Message[]) => {
        set((state) => ({
          sessions: state.sessions.map((s) =>
            s.id === sessionId ? { ...s, messages, updatedAt: new Date() } : s
          ),
        }));
      },

      toggleSidebar: () => {
        set((state) => ({ sidebarOpen: !state.sidebarOpen }));
      },

      setIsLoadingFromDb: (loading: boolean) => {
        set({ isLoadingFromDb: loading });
      },

      setSessions: (sessions: ChatSession[]) => {
        set({ sessions });
      },

      markSessionSynced: (sessionId: string) => {
        set((state) => ({
          sessions: state.sessions.map((s) =>
            s.id === sessionId ? { ...s, synced: true } : s
          ),
        }));
      },
    }),
    {
      name: 'chat-storage',
      partialize: (state) => ({
        // Only persist minimal data - full messages are in database
        sessions: state.sessions.map((session) => ({
          id: session.id,
          title: session.title,
          messages: [], // Don't persist messages to localStorage, they're in DB
          createdAt: session.createdAt,
          updatedAt: session.updatedAt,
          synced: session.synced,
        })),
        currentSessionId: state.currentSessionId,
      }),
    }
  )
);
