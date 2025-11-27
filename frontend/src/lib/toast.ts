import { create } from 'zustand';

export type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface Toast {
  id: string;
  type: ToastType;
  title?: string;
  message: string;
  duration?: number;
}

interface ToastStore {
  toasts: Toast[];
  addToast: (toast: Omit<Toast, 'id'>) => void;
  removeToast: (id: string) => void;
  clearAll: () => void;
}

/**
 * Toast Store
 * Manages toast notifications state
 */
export const useToastStore = create<ToastStore>((set) => ({
  toasts: [],
  
  addToast: (toast) => {
    const id = Math.random().toString(36).substring(2, 9);
    const newToast: Toast = {
      id,
      duration: 5000, // Default 5 seconds
      ...toast,
    };

    set((state) => ({
      toasts: [...state.toasts, newToast],
    }));

    // Auto-dismiss after duration
    if (newToast.duration && newToast.duration > 0) {
      setTimeout(() => {
        set((state) => ({
          toasts: state.toasts.filter((t) => t.id !== id),
        }));
      }, newToast.duration);
    }
  },

  removeToast: (id) => {
    set((state) => ({
      toasts: state.toasts.filter((t) => t.id !== id),
    }));
  },

  clearAll: () => {
    set({ toasts: [] });
  },
}));

/**
 * Toast Helper Functions
 * Convenient functions to show different types of toasts
 */
export const toast = {
  success: (message: string, title?: string, duration?: number) => {
    useToastStore.getState().addToast({
      type: 'success',
      title,
      message,
      duration,
    });
  },

  error: (message: string, title?: string, duration?: number) => {
    useToastStore.getState().addToast({
      type: 'error',
      title,
      message,
      duration,
    });
  },

  warning: (message: string, title?: string, duration?: number) => {
    useToastStore.getState().addToast({
      type: 'warning',
      title,
      message,
      duration,
    });
  },

  info: (message: string, title?: string, duration?: number) => {
    useToastStore.getState().addToast({
      type: 'info',
      title,
      message,
      duration,
    });
  },
};
