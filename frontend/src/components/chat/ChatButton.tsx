'use client';

import { useState } from 'react';

interface ChatButtonProps {
  onClick?: () => void;
}

export function ChatButton({ onClick }: ChatButtonProps) {
  const [isHovered, setIsHovered] = useState(false);

  return (
    <button
      onClick={onClick}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      className="fixed bottom-6 right-6 z-50 w-14 h-14 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white rounded-full shadow-lg hover:shadow-xl transition-all duration-300 flex items-center justify-center group"
      aria-label="Open AI Chat"
    >
      {/* Chat Icon */}
      <svg 
        className={`w-6 h-6 transition-transform duration-300 ${isHovered ? 'scale-110' : 'scale-100'}`}
        fill="none" 
        stroke="currentColor" 
        viewBox="0 0 24 24"
      >
        <path 
          strokeLinecap="round" 
          strokeLinejoin="round" 
          strokeWidth={2} 
          d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" 
        />
      </svg>

      {/* Pulse animation */}
      <span className="absolute inset-0 rounded-full bg-purple-600 opacity-75 animate-ping"></span>

      {/* Notification badge (optional - can be shown when there are unread messages) */}
      {/* <span className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-white text-xs font-bold rounded-full flex items-center justify-center">
        3
      </span> */}
    </button>
  );
}
