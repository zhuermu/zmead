'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { useChat } from '@/hooks/useChat';
import { useChatStore } from '@/lib/store';
import { useConversationSync } from '@/hooks/useConversationSync';
import { useFileUpload, type FileAttachment } from '@/hooks/useFileUpload';
import { MessageBubble } from './MessageBubble';
import type { Message, AgentStatus } from '@/hooks/useChat';

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
  'image/*', '.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.bmp', '.ico',
  'video/*', '.mp4', '.webm', '.mov', '.avi', '.mkv',
  '.pdf', '.doc', '.docx', '.odt', '.rtf',
  '.xls', '.xlsx', '.csv', '.ods',
  '.ppt', '.pptx', '.odp',
  '.txt', '.md', '.markdown', '.json', '.xml', '.yaml', '.yml',
  '.js', '.ts', '.jsx', '.tsx', '.css', '.html', '.py', '.java', '.cpp', '.c', '.go', '.rs',
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


// File type icon component
const FileTypeIcon = ({ type, className = "w-5 h-5" }: { type: FileAttachment['type']; className?: string }) => {
  const icons: Record<FileAttachment['type'], { color: string; path: string }> = {
    image: { color: 'text-green-600', path: 'M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z' },
    video: { color: 'text-purple-600', path: 'M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z' },
    document: { color: 'text-blue-600', path: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z' },
    spreadsheet: { color: 'text-emerald-600', path: 'M3 10h18M3 14h18m-9-4v8m-7 0h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z' },
    presentation: { color: 'text-orange-600', path: 'M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z' },
    text: { color: 'text-gray-600', path: 'M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4' },
    file: { color: 'text-gray-500', path: 'M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z' },
  };
  const { color, path } = icons[type];
  return (
    <svg className={`${className} ${color}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={path} />
    </svg>
  );
};

// Delete confirmation dialog component
function DeleteConfirmDialog({ 
  isOpen, 
  sessionTitle, 
  onConfirm, 
  onCancel 
}: { 
  isOpen: boolean; 
  sessionTitle: string; 
  onConfirm: () => void; 
  onCancel: () => void;
}) {
  if (!isOpen) return null;
  
  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50" onClick={onCancel}>
      <div 
        className="bg-white rounded-xl shadow-xl p-6 max-w-sm mx-4 animate-in fade-in zoom-in-95 duration-200"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 bg-red-100 rounded-full flex items-center justify-center">
            <svg className="w-5 h-5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900">删除会话</h3>
            <p className="text-sm text-gray-500">此操作无法撤销</p>
          </div>
        </div>
        <p className="text-sm text-gray-600 mb-6">
          确定要删除会话 "<span className="font-medium">{sessionTitle}</span>" 吗？所有消息记录将被永久删除。
        </p>
        <div className="flex gap-3 justify-end">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
          >
            取消
          </button>
          <button
            onClick={onConfirm}
            className="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-lg transition-colors"
          >
            确认删除
          </button>
        </div>
      </div>
    </div>
  );
}


export function ChatDrawer({ isOpen, onClose }: ChatDrawerProps) {
  const {
    sessions,
    currentSessionId,
    createSession,
    deleteSession,
    selectSession,
    pendingDeleteId,
    confirmDeleteSession,
    cancelDeleteSession,
    updateSessionMessages,
    draftInput,
    setDraftInput,
  } = useChatStore();

  const { 
    loadConversations, 
    loadSessionMessages, 
    saveMessages, 
    deleteConversation,
    createConversation,
  } = useConversationSync();

  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [isComposing, setIsComposing] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [agentStatus, setAgentStatus] = useState<AgentStatus | null>(null);
  const [attachments, setAttachments] = useState<FileAttachment[]>([]);

  // Use file upload hook for GCS
  const {
    uploadFiles: uploadFilesToGCS,
    uploadProgress,
    clearAllProgress,
  } = useFileUpload(currentSessionId || 'temp');

  // Check if any file is currently uploading
  const isUploading = uploadProgress.some(p => p.status === 'uploading');

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const dropZoneRef = useRef<HTMLDivElement>(null);
  const prevSessionIdRef = useRef<string | null>(null);
  const isLoadingFromDbRef = useRef(false);
  const hasLoadedConversationsRef = useRef(false);
  const lastSavedMessageCountRef = useRef<number>(0);

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

  // Load conversations from database on first open
  useEffect(() => {
    if (isOpen && !hasLoadedConversationsRef.current) {
      hasLoadedConversationsRef.current = true;
      loadConversations();
    }
  }, [isOpen, loadConversations]);

  // Initialize session if none exists
  useEffect(() => {
    if (isOpen && sessions.length === 0) {
      const newSessionId = createSession();
      createConversation(newSessionId);
    }
  }, [isOpen, sessions.length, createSession, createConversation]);


  // Update agent status from hook
  useEffect(() => {
    setAgentStatus(hookAgentStatus || null);
  }, [hookAgentStatus]);

  // Load messages when session changes
  useEffect(() => {
    if (currentSessionId && currentSessionId !== prevSessionIdRef.current) {
      prevSessionIdRef.current = currentSessionId;
      isLoadingFromDbRef.current = true;
      lastSavedMessageCountRef.current = 0; // Reset counter for new session

      const session = sessions.find(s => s.id === currentSessionId);
      
      // If session is synced, load from database
      if (session?.synced) {
        loadSessionMessages(currentSessionId).then((dbMessages) => {
          setMessages(dbMessages);
          lastSavedMessageCountRef.current = dbMessages.length;
          isLoadingFromDbRef.current = false;
        });
      } else if (session && session.messages.length > 0) {
        setMessages(session.messages as Message[]);
        lastSavedMessageCountRef.current = session.messages.length;
        isLoadingFromDbRef.current = false;
      } else {
        setMessages([]);
        isLoadingFromDbRef.current = false;
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentSessionId, setMessages, loadSessionMessages]);

  // Save messages to database when they change (only new messages)
  useEffect(() => {
    // Skip if loading from DB, still streaming, or no new messages
    if (!currentSessionId || isLoadingFromDbRef.current || isLoading) return;
    if (messages.length === 0 || messages.length <= lastSavedMessageCountRef.current) return;
    
    // Generate title from first user message if needed
    const title = messages[0]?.role === 'user' && messages[0]?.content
      ? generateTitle(messages[0])
      : undefined;
    
    // Save to database (this handles deduplication internally)
    saveMessages(currentSessionId, messages, title);
    lastSavedMessageCountRef.current = messages.length;
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentSessionId, messages.length, isLoading, saveMessages]);

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
        if (pendingDeleteId) {
          cancelDeleteSession();
        } else {
          onClose();
        }
      }
    };
    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose, pendingDeleteId, cancelDeleteSession]);


  const generateTitle = (message: Message) => {
    const content = message.content || '';
    const maxLength = 20;
    const cleaned = content.replace(/\n/g, ' ').trim();
    return cleaned.length > maxLength ? cleaned.slice(0, maxLength) + '...' : cleaned || '新对话';
  };

  const handleNewSession = useCallback(() => {
    const newSessionId = createSession();
    createConversation(newSessionId);
    setMessages([]);
    setDraftInput('');
    setAttachments([]);
    clearAllProgress();
  }, [createSession, createConversation, setMessages, setDraftInput, clearAllProgress]);

  const handleSelectSession = useCallback((sessionId: string) => {
    selectSession(sessionId);
  }, [selectSession]);

  const handleDeleteClick = useCallback((e: React.MouseEvent, sessionId: string) => {
    e.stopPropagation();
    confirmDeleteSession(sessionId);
  }, [confirmDeleteSession]);

  const handleConfirmDelete = useCallback(async () => {
    if (!pendingDeleteId) return;
    
    const isCurrentSession = pendingDeleteId === currentSessionId;
    const sessionToDelete = pendingDeleteId;
    
    // Delete from database first
    await deleteConversation(sessionToDelete);
    
    // Delete from local store
    deleteSession(sessionToDelete);
    
    // If we deleted the current session and it was the last one, create a new session
    if (isCurrentSession) {
      const remainingSessions = sessions.filter(s => s.id !== sessionToDelete);
      if (remainingSessions.length === 0) {
        const newSessionId = createSession();
        createConversation(newSessionId);
        setMessages([]);
      } else {
        // Messages will be loaded by the session change effect
      }
    }
  }, [pendingDeleteId, currentSessionId, sessions, deleteConversation, deleteSession, createSession, createConversation, setMessages]);


  // File handling - directly upload to GCS
  const processFiles = useCallback(async (files: FileList | File[]) => {
    try {
      const fileArray = Array.from(files);
      const uploadedAttachments = await uploadFilesToGCS(fileArray);
      setAttachments(prev => [...prev, ...uploadedAttachments]);
    } catch (error) {
      console.error('[ChatDrawer] File upload failed:', error);
      alert(`文件上传失败: ${error instanceof Error ? error.message : '未知错误'}`);
    }
  }, [uploadFilesToGCS]);

  const handleFileSelect = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      await processFiles(e.target.files);
    }
    if (fileInputRef.current) fileInputRef.current.value = '';
  }, [processFiles]);

  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (dropZoneRef.current && !dropZoneRef.current.contains(e.relatedTarget as Node)) {
      setIsDragging(false);
    }
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    if (e.dataTransfer.files.length > 0) {
      await processFiles(e.dataTransfer.files);
    }
  }, [processFiles]);
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

  const onSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if ((!draftInput.trim() && attachments.length === 0) || isLoading || isComposing) return;

    const messageContent = draftInput;
    const messageAttachments = attachments;

    // Clear input and attachments
    setDraftInput('');
    setAttachments([]);
    clearAllProgress();
    if (textareaRef.current) textareaRef.current.style.height = 'auto';

    // Send message with attachments in new format
    await sendMessage(messageContent, messageAttachments);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey && !isComposing) {
      e.preventDefault();
      const formEvent = new Event('submit', { bubbles: true, cancelable: true }) as unknown as React.FormEvent<HTMLFormElement>;
      onSubmit(formEvent);
    }
  };

  const handlePaste = useCallback(async (e: React.ClipboardEvent<HTMLTextAreaElement>) => {
    const items = e.clipboardData?.items;
    if (!items) return;

    const imageItems: DataTransferItem[] = [];
    for (let i = 0; i < items.length; i++) {
      const item = items[i];
      if (item.type.startsWith('image/')) {
        imageItems.push(item);
      }
    }

    if (imageItems.length === 0) return;

    // Prevent default paste behavior for images
    e.preventDefault();

    try {
      const files: File[] = [];
      for (const item of imageItems) {
        const file = item.getAsFile();
        if (file) {
          // Generate a meaningful filename for pasted images
          const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
          const extension = file.type.split('/')[1] || 'png';
          const pastedFile = new File(
            [file],
            `pasted-image-${timestamp}.${extension}`,
            { type: file.type }
          );
          files.push(pastedFile);
        }
      }

      if (files.length > 0) {
        await processFiles(files);
      }
    } catch (error) {
      console.error('[ChatDrawer] Paste image failed:', error);
      alert(`粘贴图片失败: ${error instanceof Error ? error.message : '未知错误'}`);
    }
  }, [processFiles]);

  const handleTextareaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setDraftInput(e.target.value);
    const textarea = e.target;
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
  };

  const pendingSession = sessions.find(s => s.id === pendingDeleteId);


  return (
    <>
      {/* Delete Confirmation Dialog */}
      <DeleteConfirmDialog
        isOpen={!!pendingDeleteId}
        sessionTitle={pendingSession?.title || ''}
        onConfirm={handleConfirmDelete}
        onCancel={cancelDeleteSession}
      />

      {/* Drawer */}
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

        {/* Session Sidebar */}
        <div className={`${sidebarOpen ? 'w-52' : 'w-0'} transition-all duration-300 overflow-hidden border-r border-gray-200 bg-gray-50 flex flex-col flex-shrink-0`}>
          <div className="flex items-center justify-between p-3 border-b border-gray-200 min-w-[208px]">
            <span className="text-sm font-medium text-gray-700">历史会话</span>
            <button onClick={handleNewSession} className="p-1.5 hover:bg-gray-200 rounded-lg transition-colors" title="新建会话">
              <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
            </button>
          </div>

          <div className="flex-1 overflow-y-auto min-w-[208px]">
            {sessions.map((session) => (
              <div
                key={session.id}
                onClick={() => handleSelectSession(session.id)}
                className={`group px-3 py-2.5 cursor-pointer border-b border-gray-100 hover:bg-gray-100 ${currentSessionId === session.id ? 'bg-blue-50 border-l-2 border-l-blue-500' : ''}`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">{session.title}</p>
                    <p className="text-xs text-gray-500 mt-0.5">{formatDate(session.updatedAt || session.createdAt)}</p>
                  </div>
                  <button
                    onClick={(e) => handleDeleteClick(e, session.id)}
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
            {sessions.length === 0 && <div className="p-4 text-center text-gray-500 text-sm">暂无会话记录</div>}
          </div>
        </div>


        {/* Main Chat Area */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Header */}
          <div className="flex items-center justify-between h-14 px-4 border-b border-gray-200 bg-gradient-to-r from-blue-600 to-indigo-600 flex-shrink-0">
            <div className="flex items-center gap-3">
              <button onClick={() => setSidebarOpen(!sidebarOpen)} className="p-1.5 text-white/80 hover:text-white hover:bg-white/10 rounded-lg transition-colors">
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
            <button onClick={onClose} className="p-2 text-white/80 hover:text-white hover:bg-white/10 rounded-lg transition-colors">
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
                      onClick={() => { setDraftInput(suggestion); textareaRef.current?.focus(); }}
                      className="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 text-gray-700 text-sm rounded-full transition-colors"
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
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
            <div className="px-4 py-4 border-t border-amber-200 bg-gradient-to-b from-amber-50 to-amber-100/50 flex-shrink-0 animate-in slide-in-from-bottom-2 duration-300">
              {/* Header with icon */}
              <div className="flex items-start gap-3 mb-3">
                <div className="w-10 h-10 bg-amber-500 rounded-lg flex items-center justify-center flex-shrink-0 shadow-sm">
                  {userInputRequest.type === 'confirmation' ? (
                    <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                  ) : userInputRequest.type === 'selection' ? (
                    <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
                    </svg>
                  ) : (
                    <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                    </svg>
                  )}
                </div>
                <div className="flex-1">
                  <p className="text-sm font-semibold text-amber-900 mb-1">
                    {userInputRequest.type === 'confirmation' ? '⚠️ 需要您的确认' :
                     userInputRequest.type === 'selection' ? '请选择操作' :
                     '请输入信息'}
                  </p>
                  <p className="text-sm text-amber-800">{userInputRequest.question}</p>
                  {userInputRequest.message && userInputRequest.message !== userInputRequest.question && (
                    <p className="text-xs text-amber-700 mt-1 opacity-90">{userInputRequest.message}</p>
                  )}
                </div>
              </div>

              {/* Input field for 'input' type */}
              {userInputRequest.type === 'input' ? (
                <div className="space-y-2">
                  <div className="p-3 bg-white rounded-lg border border-blue-200">
                    <input
                      type="text"
                      placeholder={userInputRequest.metadata?.placeholder || userInputRequest.defaultValue || "请输入..."}
                      defaultValue={userInputRequest.defaultValue}
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent mb-2"
                      autoFocus
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' && e.currentTarget.value.trim()) {
                          respondToUserInput(e.currentTarget.value.trim());
                          e.currentTarget.value = '';
                        }
                      }}
                      id="hitl-input-field"
                    />
                    <div className="flex gap-2">
                      <button
                        onClick={() => {
                          const input = document.getElementById('hitl-input-field') as HTMLInputElement;
                          if (input?.value.trim()) {
                            respondToUserInput(input.value.trim());
                            input.value = '';
                          }
                        }}
                        className="flex-1 px-4 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white text-sm font-medium rounded-lg hover:from-blue-700 hover:to-indigo-700 transition-all"
                      >
                        ✅ 提交
                      </button>
                      <button
                        onClick={() => respondToUserInput('取消操作')}
                        className="flex-1 px-4 py-2 bg-white border border-gray-300 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50 hover:border-gray-400 transition-all"
                      >
                        ❌ 取消
                      </button>
                    </div>
                  </div>
                </div>
              ) : (
                // Options for 'confirmation' and 'selection' types
                <div className="space-y-2">
                  {userInputRequest.options?.map((option) => {
                    const isCancel = option.value === '__cancel__';
                    const isOther = option.value === '__other__';
                    const isPrimary = option.primary || (!isCancel && !isOther);

                    return (
                      <button
                        key={option.value}
                        onClick={() => respondToUserInput(isCancel ? '取消操作' : option.label)}
                        className={`w-full px-4 py-3 text-left rounded-lg transition-all shadow-sm hover:shadow-md group ${
                          isCancel
                            ? 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 hover:border-gray-400'
                            : isOther
                              ? 'bg-white border border-blue-300 text-blue-700 hover:bg-blue-50 hover:border-blue-400'
                              : isPrimary
                                ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white hover:from-blue-700 hover:to-indigo-700'
                                : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 hover:border-gray-400'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex-1">
                            <div className="flex items-center gap-2">
                              {isPrimary && !isCancel && !isOther && (
                                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                                </svg>
                              )}
                              {isCancel && (
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                </svg>
                              )}
                              <span className="font-medium">{option.label}</span>
                            </div>
                            {option.description && (
                              <p className={`text-xs mt-1 ${isPrimary && !isCancel && !isOther ? 'text-blue-100' : 'text-gray-600'}`}>
                                {option.description}
                              </p>
                            )}
                          </div>
                          {!isCancel && (
                            <svg className={`w-5 h-5 opacity-0 group-hover:opacity-100 transition-opacity ${isPrimary && !isOther ? 'text-white' : 'text-gray-400'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                            </svg>
                          )}
                        </div>
                      </button>
                    );
                  })}

                  {/* Custom input for "Other" option */}
                  {userInputRequest.options?.some(o => o.value === '__other__') && (
                    <div className="mt-3 p-3 bg-white rounded-lg border border-blue-200">
                      <label className="block text-xs font-medium text-gray-700 mb-2">
                        或输入自定义内容:
                      </label>
                      <div className="flex gap-2">
                        <input
                          type="text"
                          placeholder={userInputRequest.defaultValue || "输入自定义内容..."}
                          className="flex-1 px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                          onKeyDown={(e) => {
                            if (e.key === 'Enter' && e.currentTarget.value.trim()) {
                              respondToUserInput(e.currentTarget.value.trim());
                              e.currentTarget.value = '';
                            }
                          }}
                        />
                        <button
                          onClick={(e) => {
                            const input = e.currentTarget.previousElementSibling as HTMLInputElement;
                            if (input.value.trim()) {
                              respondToUserInput(input.value.trim());
                              input.value = '';
                            }
                          }}
                          className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
                        >
                          发送
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Attachments Preview */}
          {attachments.length > 0 && (
            <div className="px-4 py-2 border-t border-gray-100 bg-gray-50 flex-shrink-0">
              <div className="flex flex-wrap gap-2">
                {attachments.map((attachment) => {
                  const isImage = attachment.content_type.startsWith('image/');
                  const isVideo = attachment.content_type.startsWith('video/');
                  const fileType = isImage ? 'image' : isVideo ? 'video' : 'document';

                  return (
                    <div key={attachment.file_id} className="relative group flex items-center gap-2 px-2 py-1.5 bg-white border border-gray-200 rounded-lg">
                      {isImage && attachment.preview_url ? (
                        <img
                          src={attachment.preview_url}
                          alt={attachment.filename}
                          className="w-10 h-10 object-cover rounded"
                        />
                      ) : (
                        <div className="w-10 h-10 bg-gray-100 rounded flex items-center justify-center">
                          <FileTypeIcon type={fileType} />
                        </div>
                      )}
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-medium text-gray-700 truncate max-w-[100px]">{attachment.filename}</p>
                        <p className="text-xs text-gray-400">
                          {formatFileSize(attachment.file_size)}
                        </p>
                      </div>
                      <button
                        onClick={() => setAttachments(prev => prev.filter(a => a.file_id !== attachment.file_id))}
                        className="absolute -top-1.5 -right-1.5 w-5 h-5 bg-red-500 text-white rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                      >
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    </div>
                  );
                })}
              </div>
            </div>
          )}


          {/* Input */}
          <div className="border-t border-gray-200 bg-white p-4 flex-shrink-0">
            <form onSubmit={onSubmit}>
              <div className="flex gap-2 items-end">
                <input ref={fileInputRef} type="file" multiple accept={ACCEPTED_FILE_TYPES} onChange={handleFileSelect} className="hidden" />
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
                    value={draftInput}
                    onChange={handleTextareaChange}
                    onKeyDown={handleKeyDown}
                    onPaste={handlePaste}
                    onCompositionStart={() => setIsComposing(true)}
                    onCompositionEnd={() => setIsComposing(false)}
                    placeholder="输入消息... (可粘贴图片或拖拽上传)"
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
                    className={`p-3 text-white rounded-xl transition-colors ${isUploading ? 'bg-blue-500 cursor-wait' : 'bg-red-500 hover:bg-red-600'}`}
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
                    disabled={(!draftInput.trim() && attachments.length === 0) || isComposing}
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
              <kbd className="px-1.5 py-0.5 bg-gray-100 rounded text-gray-500">Esc</kbd> 关闭 · <kbd className="px-1.5 py-0.5 bg-gray-100 rounded text-gray-500">Enter</kbd> 发送 · <kbd className="px-1.5 py-0.5 bg-gray-100 rounded text-gray-500">⌘V</kbd> 粘贴图片 · 拖拽上传
            </p>
          </div>
        </div>
      </div>
    </>
  );
}
