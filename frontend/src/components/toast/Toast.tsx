'use client';

import { useEffect, useState } from 'react';
import { cn } from '@/lib/utils';
import { Toast as ToastType } from '@/lib/toast';
import {
  CheckCircle,
  XCircle,
  AlertTriangle,
  Info,
  X,
} from 'lucide-react';

interface ToastProps {
  toast: ToastType;
  onClose: () => void;
}

/**
 * Toast Component
 * Displays a single toast notification
 */
export function Toast({ toast, onClose }: ToastProps) {
  const [isExiting, setIsExiting] = useState(false);

  useEffect(() => {
    // Handle exit animation before removal
    const exitTimer = setTimeout(() => {
      if (toast.duration && toast.duration > 0) {
        setIsExiting(true);
        setTimeout(onClose, 300); // Wait for animation
      }
    }, (toast.duration || 5000) - 300);

    return () => clearTimeout(exitTimer);
  }, [toast.duration, onClose]);

  const handleClose = () => {
    setIsExiting(true);
    setTimeout(onClose, 300);
  };

  const icons = {
    success: <CheckCircle className="w-5 h-5 text-green-600" />,
    error: <XCircle className="w-5 h-5 text-red-600" />,
    warning: <AlertTriangle className="w-5 h-5 text-yellow-600" />,
    info: <Info className="w-5 h-5 text-blue-600" />,
  };

  const styles = {
    success: 'bg-green-50 border-green-200',
    error: 'bg-red-50 border-red-200',
    warning: 'bg-yellow-50 border-yellow-200',
    info: 'bg-blue-50 border-blue-200',
  };

  return (
    <div
      className={cn(
        'flex items-start gap-3 p-4 rounded-lg border shadow-lg max-w-md w-full',
        'transition-all duration-300 ease-in-out',
        isExiting
          ? 'opacity-0 translate-x-full'
          : 'opacity-100 translate-x-0',
        styles[toast.type]
      )}
      role="alert"
    >
      {/* Icon */}
      <div className="flex-shrink-0 mt-0.5">{icons[toast.type]}</div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        {toast.title && (
          <p className="text-sm font-semibold text-gray-900 mb-1">
            {toast.title}
          </p>
        )}
        <p className="text-sm text-gray-700">{toast.message}</p>
      </div>

      {/* Close Button */}
      <button
        onClick={handleClose}
        className="flex-shrink-0 text-gray-400 hover:text-gray-600 transition-colors"
        aria-label="Close notification"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
}
