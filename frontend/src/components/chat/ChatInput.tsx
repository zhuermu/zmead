'use client';

import { useChat } from '@/hooks/useChat';
import { useState, useRef, useMemo } from 'react';
import { useFileUpload, type FileAttachment } from '@/hooks/useFileUpload';
import { AttachmentPreview } from './AttachmentPreview';
import { Paperclip } from 'lucide-react';

export function ChatInput() {
  const { input, handleInputChange, isLoading, stop, append } = useChat();
  const [isComposing, setIsComposing] = useState(false);
  const [attachments, setAttachments] = useState<FileAttachment[]>([]);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Generate session ID (should match what useChat generates)
  const sessionId = useMemo(() => {
    const stored = typeof window !== 'undefined' ? sessionStorage.getItem('chat_session_id') : null;
    return stored || `session-${Date.now().toString(36)}`;
  }, []);

  const { uploadFile, uploadProgress, clearProgress } = useFileUpload(sessionId);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const onSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!input.trim() || isLoading || isComposing) return;

    // Send message with attachments
    const messageContent = input;

    // Convert FileAttachment to API format
    const messageAttachments = attachments.map(att => ({
      gcs_path: att.gcs_path,
      filename: att.filename,
      content_type: att.content_type,
      file_size: att.file_size,
      download_url: att.download_url,
    }));

    // Clear input and attachments
    handleInputChange({ target: { value: '' } } as any);
    setAttachments([]);
    setUploadError(null);

    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }

    // Send message
    await append(messageContent, messageAttachments);
  };

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    setUploadError(null);

    try {
      // Upload each file
      for (const file of Array.from(files)) {
        const attachment = await uploadFile(file);
        setAttachments(prev => [...prev, attachment]);
      }
    } catch (error) {
      setUploadError(error instanceof Error ? error.message : '文件上传失败');
    }

    // Reset file input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleRemoveAttachment = (fileId: string) => {
    setAttachments(prev => prev.filter(att => att.file_id !== fileId));
    clearProgress(fileId);

    // Revoke preview URL to free memory
    const attachment = attachments.find(att => att.file_id === fileId);
    if (attachment?.preview_url) {
      URL.revokeObjectURL(attachment.preview_url);
    }
  };

  const handleAttachClick = () => {
    fileInputRef.current?.click();
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Submit on Enter (without Shift)
    if (e.key === 'Enter' && !e.shiftKey && !isComposing) {
      e.preventDefault();
      const formEvent = new Event('submit', { bubbles: true, cancelable: true }) as unknown as React.FormEvent<HTMLFormElement>;
      onSubmit(formEvent);
    }
  };

  const handleTextareaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    handleInputChange(e);
    
    // Auto-resize textarea
    const textarea = e.target;
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
  };

  return (
    <form onSubmit={onSubmit} className="p-4 border-t border-gray-200 bg-gray-50">
      {/* File attachments preview */}
      <AttachmentPreview
        attachments={attachments}
        uploadProgress={uploadProgress}
        onRemove={handleRemoveAttachment}
      />

      {/* Upload error message */}
      {uploadError && (
        <div className="mb-2 px-4 py-2 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
          {uploadError}
        </div>
      )}

      <div className="flex gap-2 items-end">
        {/* Text Input */}
        <div className="flex-1 relative">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={handleTextareaChange}
            onKeyDown={handleKeyDown}
            onCompositionStart={() => setIsComposing(true)}
            onCompositionEnd={() => setIsComposing(false)}
            placeholder="输入消息... (Enter 发送, Shift+Enter 换行)"
            disabled={isLoading}
            rows={1}
            className="w-full px-4 py-3 pr-12 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed resize-none text-sm"
            style={{ minHeight: '44px', maxHeight: '120px' }}
          />

          {/* Attachment button */}
          <button
            type="button"
            onClick={handleAttachClick}
            className="absolute right-2 bottom-2 p-1.5 text-gray-400 hover:text-purple-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            title="附加文件 (图片、视频、文档)"
            disabled={isLoading}
          >
            <Paperclip className="w-5 h-5" />
          </button>

          {/* Hidden file input */}
          <input
            ref={fileInputRef}
            type="file"
            onChange={handleFileSelect}
            accept="image/*,video/*,.pdf,.txt,.html,.css,.js,.ts,.py,.md,.csv,.xml,.rtf"
            multiple
            className="hidden"
          />
        </div>

        {/* Send/Stop Button */}
        {isLoading ? (
          <button
            type="button"
            onClick={stop}
            className="px-4 py-3 bg-red-500 hover:bg-red-600 text-white rounded-lg transition-colors flex items-center gap-2 font-medium text-sm"
          >
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
              <rect x="6" y="6" width="12" height="12" />
            </svg>
            停止
          </button>
        ) : (
          <button
            type="submit"
            disabled={!input.trim() || isComposing}
            className="px-4 py-3 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 font-medium text-sm"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
            发送
          </button>
        )}
      </div>

      {/* Helper text */}
      <div className="mt-2 text-xs text-gray-500 flex items-center gap-4">
        <span>💡 提示: Enter 发送, Shift+Enter 换行</span>
        <span>📎 支持上传图片、视频、文档</span>
      </div>
    </form>
  );
}
