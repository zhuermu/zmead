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

import type { UIMessage } from 'ai';

type Message = UIMessage;

// Chat session interface
export interface ChatSession {
  id: string;
  title: string;
  messages: Message[];
  createdAt: Date;
  updatedAt: Date;
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

  // Session actions
  createSession: () => string;
  deleteSession: (sessionId: string) => void;
  selectSession: (sessionId: string) => void;
  getCurrentSession: () => ChatSession | null;
  addMessageToSession: (sessionId: string, message: Message) => void;
  updateSessionTitle: (sessionId: string, title: string) => void;
  toggleSidebar: () => void;
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

      createSession: () => {
        const newSession: ChatSession = {
          id: generateSessionId(),
          title: '新对话',
          messages: [],
          createdAt: new Date(),
          updatedAt: new Date(),
        };
        set((state) => ({
          sessions: [newSession, ...state.sessions],
          currentSessionId: newSession.id,
        }));
        return newSession.id;
      },

      deleteSession: (sessionId: string) => {
        set((state) => {
          const newSessions = state.sessions.filter((s) => s.id !== sessionId);
          const newCurrentId =
            state.currentSessionId === sessionId
              ? newSessions[0]?.id || null
              : state.currentSessionId;
          return {
            sessions: newSessions,
            currentSessionId: newCurrentId,
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

      toggleSidebar: () => {
        set((state) => ({ sidebarOpen: !state.sidebarOpen }));
      },
    }),
    {
      name: 'chat-storage',
      partialize: (state) => ({
        messages: state.messages,
        sessions: state.sessions,
        currentSessionId: state.currentSessionId,
      }),
    }
  )
);
