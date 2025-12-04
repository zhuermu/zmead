/**
 * Preview component for file attachments before sending
 * Shows thumbnails for images, file icons for documents, and progress indicators
 */

'use client';

import { X } from 'lucide-react';
import Image from 'next/image';
import type { FileAttachment, UploadProgress } from '@/hooks/useFileUpload';

interface AttachmentPreviewProps {
  attachments: FileAttachment[];
  uploadProgress: UploadProgress[];
  onRemove: (fileId: string) => void;
}

export function AttachmentPreview({ attachments, uploadProgress, onRemove }: AttachmentPreviewProps) {
  if (attachments.length === 0 && uploadProgress.length === 0) {
    return null;
  }

  const getFileIcon = (contentType: string) => {
    if (contentType.startsWith('image/')) {
      return '🖼️';
    } else if (contentType.startsWith('video/')) {
      return '🎬';
    } else if (contentType === 'application/pdf') {
      return '📄';
    } else if (contentType.startsWith('text/')) {
      return '📝';
    }
    return '📎';
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="px-4 pb-2">
      <div className="flex flex-wrap gap-2">
        {/* Completed attachments */}
        {attachments.map((attachment) => (
          <div
            key={attachment.file_id}
            className="relative group bg-white border border-gray-200 rounded-lg overflow-hidden hover:border-purple-300 transition-colors"
            style={{ width: '120px', height: '120px' }}
          >
            {/* Image preview */}
            {attachment.content_type.startsWith('image/') && attachment.preview_url ? (
              <div className="w-full h-full relative">
                <Image
                  src={attachment.preview_url}
                  alt={attachment.filename}
                  fill
                  className="object-cover"
                />
              </div>
            ) : attachment.content_type.startsWith('video/') && attachment.preview_url ? (
              /* Video preview */
              <div className="w-full h-full relative bg-black">
                <video
                  src={attachment.preview_url}
                  className="w-full h-full object-cover"
                  muted
                />
                <div className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-30">
                  <div className="text-white text-4xl">▶️</div>
                </div>
              </div>
            ) : (
              /* Document/other file preview */
              <div className="w-full h-full flex flex-col items-center justify-center p-2 bg-gray-50">
                <div className="text-4xl mb-1">{getFileIcon(attachment.content_type)}</div>
                <div className="text-xs text-gray-600 text-center truncate w-full px-1">
                  {attachment.filename}
                </div>
                <div className="text-xs text-gray-400">
                  {formatFileSize(attachment.file_size)}
                </div>
              </div>
            )}

            {/* Remove button */}
            <button
              onClick={() => onRemove(attachment.file_id)}
              className="absolute top-1 right-1 p-1 bg-red-500 text-white rounded-full opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-600"
              title="移除"
            >
              <X className="w-3 h-3" />
            </button>

            {/* Filename tooltip */}
            <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black to-transparent p-2 opacity-0 group-hover:opacity-100 transition-opacity">
              <div className="text-white text-xs truncate">{attachment.filename}</div>
            </div>
          </div>
        ))}

        {/* Uploading files */}
        {uploadProgress.map((progress) => (
          <div
            key={progress.file_id}
            className="relative bg-white border border-gray-200 rounded-lg overflow-hidden"
            style={{ width: '120px', height: '120px' }}
          >
            <div className="w-full h-full flex flex-col items-center justify-center p-2 bg-gray-50">
              {progress.status === 'uploading' ? (
                <>
                  <div className="text-2xl mb-2">⏫</div>
                  <div className="w-full bg-gray-200 rounded-full h-2 mb-1">
                    <div
                      className="bg-purple-600 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${progress.progress}%` }}
                    />
                  </div>
                  <div className="text-xs text-gray-600">{progress.progress}%</div>
                  <div className="text-xs text-gray-500 truncate w-full text-center mt-1">
                    {progress.filename}
                  </div>
                </>
              ) : progress.status === 'error' ? (
                <>
                  <div className="text-2xl mb-2">❌</div>
                  <div className="text-xs text-red-600 text-center">上传失败</div>
                  <div className="text-xs text-gray-500 truncate w-full text-center mt-1">
                    {progress.filename}
                  </div>
                  {progress.error && (
                    <div className="text-xs text-red-500 text-center mt-1 px-1">
                      {progress.error}
                    </div>
                  )}
                </>
              ) : progress.status === 'pending' ? (
                <>
                  <div className="text-2xl mb-2">⏳</div>
                  <div className="text-xs text-gray-600">准备上传...</div>
                  <div className="text-xs text-gray-500 truncate w-full text-center mt-1">
                    {progress.filename}
                  </div>
                </>
              ) : null}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
