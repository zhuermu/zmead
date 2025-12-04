'use client';

import { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import { useChat } from '@/hooks/useChat';
import { useChatStore } from '@/lib/store';
import { MessageBubble } from './MessageBubble';
import type { Message, AgentStatus, UserInputRequest } from '@/hooks/useChat';

interface ChatDrawerProps {
  isOpen: boolean;
  onClose: () => void;
}

// File attachment interface
interface FileAttachment {
  id: string;
  file: File;
  preview?: string;
  type: 'image' | 'video' | 'document' | 'spreadsheet' | 'presentation' | 'text' | 'file';
}

// Supported file extensions
const ACCEPTED_FILE_TYPES = [
  // Images
  'image/*',
  '.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.bmp', '.ico',
  // Videos
  'video/*',
  '.mp4', '.webm', '.mov', '.avi', '.mkv',
  // Documents
  '.pdf', '.doc', '.docx', '.odt', '.rtf',
  // Spreadsheets
  '.xls', '.xlsx', '.csv', '.ods',
  // Presentations
  '.ppt', '.pptx', '.odp',
  // Text/Code
  '.txt', '.md', '.markdown', '.json', '.xml', '.yaml', '.yml',
  '.js', '.ts', '.jsx', '.tsx', '.css', '.html', '.py', '.java', '.cpp', '.c', '.go', '.rs',
  // Archives
  '.zip', '.rar', '.7z', '.tar', '.gz',
].join(',');

// Get file type category
const getFileCategory = (file: File): FileAttachment['type'] => {
  const mimeType = file.type.toLowerCase();
  const ext = file.name.split('.').pop()?.toLowerCase() || '';

  if (mimeType.startsWith('image/')) return 'image';
  if (mimeType.startsWith('video/')) return 'video';
  if (['pdf', 'doc', 'docx', 'odt', 'rtf'].includes(ext)) return 'document';
  if (['xls', 'xlsx', 'csv', 'ods'].includes(ext)) return 'spreadsheet';
  if (['ppt', 'pptx', 'odp'].includes(ext)) return 'presentation';
  if (['txt', 'md', 'markdown', 'json', 'xml', 'yaml', 'yml', 'js', 'ts', 'jsx', 'tsx', 'css', 'html', 'py', 'java', 'cpp', 'c', 'go', 'rs'].includes(ext)) return 'text';
  return 'file';
};

// Get icon for file type
const FileTypeIcon = ({ type, className = "w-5 h-5" }: { type: FileAttachment['type']; className?: string }) => {
  switch (type) {
    case 'image':
      return (
        <svg className={`${className} text-green-600`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
      );
    case 'video':
      return (
        <svg className={`${className} text-purple-600`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      );
    case 'document':
      return (
        <svg className={`${className} text-blue-600`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      );
    case 'spreadsheet':
      return (
        <svg className={`${className} text-emerald-600`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M3 14h18m-9-4v8m-7 0h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
        </svg>
      );
    case 'presentation':
      return (
        <svg className={`${className} text-orange-600`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
        </svg>
      );
    case 'text':
      return (
        <svg className={`${className} text-gray-600`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
        </svg>
      );
    default:
      return (
        <svg className={`${className} text-gray-500`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
        </svg>
      );
  }
};

export function ChatDrawer({ isOpen, onClose }: ChatDrawerProps) {
  const {
    sessions,
    currentSessionId,
    createSession,
    deleteSession,
    selectSession,
  } = useChatStore();

  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [isComposing, setIsComposing] = useState(false);
  const [attachments, setAttachments] = useState<FileAttachment[]>([]);
  const [localInput, setLocalInput] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const dropZoneRef = useRef<HTMLDivElement>(null);
  const prevSessionIdRef = useRef<string | null>(null);
  const isLoadingFromStoreRef = useRef(false);

  // Initialize session if none exists
  useEffect(() => {
    if (isOpen && sessions.length === 0) {
      createSession();
    }
  }, [isOpen, sessions.length, createSession]);

  // State for agent status during streaming
  const [agentStatus, setAgentStatus] = useState<AgentStatus | null>(null);

  // Use SSE-based chat hook
  const {
    messages,
    isLoading,
    stop,
    append: sendMessage,
    setMessages,
    agentStatus: hookAgentStatus,
    userInputRequest,
    respondToUserInput,
  } = useChat();

  // Update agent status from hook
  useEffect(() => {
    if (hookAgentStatus) {
      setAgentStatus(hookAgentStatus);
    } else {
      setAgentStatus(null);
    }
  }, [hookAgentStatus]);

  // Load messages when session changes (only when session ID changes)
  useEffect(() => {
    if (currentSessionId && currentSessionId !== prevSessionIdRef.current) {
      prevSessionIdRef.current = currentSessionId;
      isLoadingFromStoreRef.current = true;

      const session = sessions.find(s => s.id === currentSessionId);
      if (session && session.messages.length > 0) {
        setMessages(session.messages as any);
      } else {
        setMessages([]);
      }

      setTimeout(() => {
        isLoadingFromStoreRef.current = false;
      }, 100);
    }
  }, [currentSessionId, setMessages]);

  // Save messages to session when they change (skip if loading from store)
  useEffect(() => {
    if (currentSessionId && messages.length > 0 && !isLoadingFromStoreRef.current) {
      useChatStore.setState(state => ({
        sessions: state.sessions.map(s =>
          s.id === currentSessionId
            ? {
                ...s,
                messages: messages as any,
                updatedAt: new Date(),
                title: s.title === '新对话' && messages[0]?.role === 'user'
                  ? generateTitle(messages[0])
                  : s.title,
              }
            : s
        ),
      }));
    }
  }, [messages, currentSessionId]);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Focus textarea when drawer opens
  useEffect(() => {
    if (isOpen && textareaRef.current) {
      setTimeout(() => textareaRef.current?.focus(), 300);
    }
  }, [isOpen]);

  // Handle escape key to close
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  const generateTitle = (message: Message) => {
    const content = message.content || '';
    const maxLength = 20;
    const cleaned = content.replace(/\n/g, ' ').trim();
    return cleaned.length > maxLength ? cleaned.slice(0, maxLength) + '...' : cleaned || '新对话';
  };

  const handleNewSession = () => {
    createSession();
    setMessages([]);
    setLocalInput('');
    setAttachments([]);
  };

  const handleSelectSession = (sessionId: string) => {
    selectSession(sessionId);
  };

  const handleDeleteSession = (e: React.MouseEvent, sessionId: string) => {
    e.stopPropagation();
    deleteSession(sessionId);
    if (sessions.length <= 1) {
      createSession();
    }
  };

  // Process files for attachment
  const processFiles = useCallback((files: FileList | File[]) => {
    const fileArray = Array.from(files);
    const newAttachments: FileAttachment[] = fileArray.map(file => {
      const type = getFileCategory(file);
      const attachment: FileAttachment = {
        id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
        file,
        type,
      };

      // Create preview for images
      if (type === 'image') {
        attachment.preview = URL.createObjectURL(file);
      }

      return attachment;
    });

    setAttachments(prev => [...prev, ...newAttachments]);
  }, []);

  // File input handler
  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      processFiles(e.target.files);
    }
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }, [processFiles]);

  // Drag and drop handlers
  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    // Only set dragging to false if leaving the drop zone entirely
    if (dropZoneRef.current && !dropZoneRef.current.contains(e.relatedTarget as Node)) {
      setIsDragging(false);
    }
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const files = e.dataTransfer.files;
    if (files.length > 0) {
      processFiles(files);
    }
  }, [processFiles]);

  const removeAttachment = useCallback((id: string) => {
    setAttachments(prev => {
      const att = prev.find(a => a.id === id);
      if (att?.preview) {
        URL.revokeObjectURL(att.preview);
      }
      return prev.filter(a => a.id !== id);
    });
  }, []);

  const [isUploading, setIsUploading] = useState(false);

  const uploadFiles = async (files: FileAttachment[]): Promise<Array<{
    id: string;
    filename: string;
    contentType: string;
    size: number;
    s3Url: string;
    cdnUrl: string;
  }>> => {
    if (files.length === 0) return [];

    const formData = new FormData();
    files.forEach(att => {
      formData.append('files', att.file);
    });

    const response = await fetch('/api/upload', {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      throw new Error('File upload failed');
    }

    const result = await response.json();
    return result.uploaded || [];
  };

  const onSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if ((!localInput.trim() && attachments.length === 0) || isLoading || isComposing || isUploading) return;

    let messageContent = localInput;
    setLocalInput('');

    // Upload files if any
    if (attachments.length > 0) {
      setIsUploading(true);
      try {
        const uploadedFiles = await uploadFiles(attachments);

        // Add file references to message content
        const fileRefs = uploadedFiles.map(f => 
          `[文件: ${f.filename} (${formatFileSize(f.size)})]`
        ).join('\n');
        
        messageContent = messageContent.trim() 
          ? `${messageContent}\n\n${fileRefs}`
          : fileRefs;
      } catch (error) {
        console.error('File upload failed:', error);
        // Show error to user
        messageContent = messageContent.trim()
          ? `${messageContent}\n\n[文件上传失败: ${attachments.map(a => a.file.name).join(', ')}]`
          : `[文件上传失败: ${attachments.map(a => a.file.name).join(', ')}]`;
      } finally {
        setIsUploading(false);
      }
    }

    attachments.forEach(att => {
      if (att.preview) URL.revokeObjectURL(att.preview);
    });
    setAttachments([]);

    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }

    if (messageContent.trim()) {
      await sendMessage(messageContent);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey && !isComposing) {
      e.preventDefault();
      const formEvent = new Event('submit', {
        bubbles: true,
        cancelable: true,
      }) as unknown as React.FormEvent<HTMLFormElement>;
      onSubmit(formEvent);
    }
  };

  const handleTextareaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setLocalInput(e.target.value);
    const textarea = e.target;
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  const formatDate = (date: Date | string) => {
    const d = new Date(date);
    const now = new Date();
    const isToday = d.toDateString() === now.toDateString();
    const yesterday = new Date(now);
    yesterday.setDate(yesterday.getDate() - 1);
    const isYesterday = d.toDateString() === yesterday.toDateString();

    if (isToday) return '今天';
    if (isYesterday) return '昨天';
    return d.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' });
  };

  return (
    <>

      {/* Drawer - wider layout */}
      <div
        ref={dropZoneRef}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
        className={`
          fixed right-0 top-0 h-full w-full sm:w-[85vw] md:w-[70vw] lg:w-[45vw] xl:w-[40vw] 2xl:w-[35vw] bg-white shadow-2xl z-50
          transform transition-transform duration-300 ease-out flex
          ${isOpen ? 'translate-x-0' : 'translate-x-full'}
        `}
      >
        {/* Drag overlay */}
        {isDragging && (
          <div className="absolute inset-0 z-50 bg-blue-500/10 border-2 border-dashed border-blue-500 rounded-lg flex items-center justify-center">
            <div className="text-center">
              <svg className="w-16 h-16 text-blue-500 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              <p className="text-lg font-medium text-blue-600">拖放文件到此处</p>
              <p className="text-sm text-blue-500 mt-1">支持图片、视频、文档等多种格式</p>
            </div>
          </div>
        )}

        {/* Session Sidebar - narrower */}
        <div
          className={`
            ${sidebarOpen ? 'w-52' : 'w-0'}
            transition-all duration-300 overflow-hidden border-r border-gray-200 bg-gray-50 flex flex-col flex-shrink-0
          `}
        >
          {/* Sidebar Header */}
          <div className="flex items-center justify-between p-3 border-b border-gray-200 min-w-[208px]">
            <span className="text-sm font-medium text-gray-700">历史会话</span>
            <button
              onClick={handleNewSession}
              className="p-1.5 hover:bg-gray-200 rounded-lg transition-colors"
              title="新建会话"
            >
              <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
            </button>
          </div>

          {/* Session List */}
          <div className="flex-1 overflow-y-auto min-w-[208px]">
            {sessions.map((session) => (
              <div
                key={session.id}
                onClick={() => handleSelectSession(session.id)}
                className={`
                  group px-3 py-2.5 cursor-pointer border-b border-gray-100 hover:bg-gray-100
                  ${currentSessionId === session.id ? 'bg-blue-50 border-l-2 border-l-blue-500' : ''}
                `}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {session.title}
                    </p>
                    <p className="text-xs text-gray-500 mt-0.5">
                      {formatDate(session.updatedAt || session.createdAt)}
                    </p>
                  </div>
                  <button
                    onClick={(e) => handleDeleteSession(e, session.id)}
                    className="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-100 rounded transition-all flex-shrink-0"
                    title="删除会话"
                  >
                    <svg className="w-4 h-4 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              </div>
            ))}

            {sessions.length === 0 && (
              <div className="p-4 text-center text-gray-500 text-sm">
                暂无会话记录
              </div>
            )}
          </div>
        </div>

        {/* Main Chat Area */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Header */}
          <div className="flex items-center justify-between h-14 px-4 border-b border-gray-200 bg-gradient-to-r from-blue-600 to-indigo-600 flex-shrink-0">
            <div className="flex items-center gap-3">
              <button
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="p-1.5 text-white/80 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h7" />
                </svg>
              </button>
              <div className="w-8 h-8 bg-white/20 rounded-lg flex items-center justify-center">
                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
              </div>
              <h2 className="text-base font-semibold text-white">AI 助手</h2>
            </div>
            <button
              onClick={onClose}
              className="p-2 text-white/80 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4">
            {messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-center px-4">
                <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-2xl flex items-center justify-center mb-4 shadow-lg">
                  <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                  </svg>
                </div>
                <h3 className="text-lg font-medium text-gray-900 mb-2">有什么可以帮你的？</h3>
                <p className="text-sm text-gray-500 mb-6">我可以帮你生成素材、分析数据、管理投放等</p>

                <div className="flex flex-wrap justify-center gap-2 mb-6">
                  {['生成广告素材', '查看投放数据', '优化建议'].map((suggestion) => (
                    <button
                      key={suggestion}
                      onClick={() => {
                        setLocalInput(suggestion);
                        textareaRef.current?.focus();
                      }}
                      className="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 text-gray-700 text-sm rounded-full transition-colors"
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>

                {/* Drag hint */}
                <div className="text-xs text-gray-400 flex items-center gap-2">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>
                  拖拽文件到此处上传
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                {messages.map((message: Message, index: number) => {
                  // Check if this is the last assistant message being streamed
                  const isLastMessage = index === messages.length - 1;
                  const isStreamingMessage = isLoading && isLastMessage && message.role === 'assistant';

                  return (
                    <MessageBubble
                      key={message.id}
                      message={message}
                      compact
                      isStreaming={isStreamingMessage}
                      agentStatus={isStreamingMessage ? agentStatus : null}
                    />
                  );
                })}

                <div ref={messagesEndRef} />
              </div>
            )}
          </div>

          {/* Human-in-the-Loop User Input Dialog */}
          {userInputRequest && (
            <div className="px-4 py-3 border-t border-blue-100 bg-blue-50 flex-shrink-0">
              <div className="mb-2">
                <p className="text-sm font-medium text-blue-800">{userInputRequest.question}</p>
              </div>
              <div className="flex flex-wrap gap-2">
                {userInputRequest.options?.map((option) => (
                  <button
                    key={option.value}
                    onClick={() => respondToUserInput(option.value === '__cancel__' ? '取消操作' : option.label)}
                    className={`
                      px-3 py-1.5 text-sm rounded-lg transition-colors
                      ${option.value === '__cancel__'
                        ? 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                        : option.value === '__other__'
                        ? 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50'
                        : 'bg-blue-600 text-white hover:bg-blue-700'}
                    `}
                    title={option.description}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
              {userInputRequest.options?.some(o => o.value === '__other__') && (
                <div className="mt-2 flex gap-2">
                  <input
                    type="text"
                    placeholder="输入自定义内容..."
                    className="flex-1 px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && e.currentTarget.value.trim()) {
                        respondToUserInput(e.currentTarget.value.trim());
                      }
                    }}
                  />
                </div>
              )}
            </div>
          )}

          {/* Attachments Preview */}
          {attachments.length > 0 && (
            <div className="px-4 py-2 border-t border-gray-100 bg-gray-50 flex-shrink-0">
              <div className="flex flex-wrap gap-2">
                {attachments.map((att) => (
                  <div
                    key={att.id}
                    className="relative group flex items-center gap-2 px-2 py-1.5 bg-white border border-gray-200 rounded-lg"
                  >
                    {att.type === 'image' && att.preview ? (
                      <img src={att.preview} alt={att.file.name} className="w-10 h-10 object-cover rounded" />
                    ) : (
                      <div className="w-10 h-10 bg-gray-100 rounded flex items-center justify-center">
                        <FileTypeIcon type={att.type} />
                      </div>
                    )}
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-medium text-gray-700 truncate max-w-[100px]">{att.file.name}</p>
                      <p className="text-xs text-gray-400">{formatFileSize(att.file.size)}</p>
                    </div>
                    <button
                      onClick={() => removeAttachment(att.id)}
                      className="absolute -top-1.5 -right-1.5 w-5 h-5 bg-red-500 text-white rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Input */}
          <div className="border-t border-gray-200 bg-white p-4 flex-shrink-0">
            <form onSubmit={onSubmit}>
              <div className="flex gap-2 items-end">
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  accept={ACCEPTED_FILE_TYPES}
                  onChange={handleFileSelect}
                  className="hidden"
                />
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="p-3 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-xl transition-colors"
                  title="上传文件 (支持拖拽)"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
                  </svg>
                </button>

                <div className="flex-1 relative">
                  <textarea
                    ref={textareaRef}
                    value={localInput}
                    onChange={handleTextareaChange}
                    onKeyDown={handleKeyDown}
                    onCompositionStart={() => setIsComposing(true)}
                    onCompositionEnd={() => setIsComposing(false)}
                    placeholder="输入消息... (支持拖拽上传文件)"
                    disabled={isLoading}
                    rows={1}
                    className="w-full px-4 py-3 bg-gray-100 border-none rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white resize-none text-sm"
                    style={{ minHeight: '44px', maxHeight: '120px' }}
                  />
                </div>

                {isLoading || isUploading ? (
                  <button
                    type="button"
                    onClick={isLoading ? stop : undefined}
                    disabled={isUploading}
                    className={`p-3 text-white rounded-xl transition-colors ${
                      isUploading
                        ? 'bg-blue-500 cursor-wait'
                        : 'bg-red-500 hover:bg-red-600'
                    }`}
                    title={isUploading ? '上传中...' : '停止生成'}
                  >
                    {isUploading ? (
                      <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                      </svg>
                    ) : (
                      <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                        <rect x="6" y="6" width="12" height="12" />
                      </svg>
                    )}
                  </button>
                ) : (
                  <button
                    type="submit"
                    disabled={(!localInput.trim() && attachments.length === 0) || isComposing}
                    className="p-3 bg-blue-600 hover:bg-blue-700 text-white rounded-xl transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                    </svg>
                  </button>
                )}
              </div>
            </form>
            <p className="text-xs text-gray-400 text-center mt-2">
              <kbd className="px-1.5 py-0.5 bg-gray-100 rounded text-gray-500">Esc</kbd> 关闭 · <kbd className="px-1.5 py-0.5 bg-gray-100 rounded text-gray-500">Enter</kbd> 发送 · 拖拽上传文件
            </p>
          </div>
        </div>
      </div>
    </>
  );
}
