/**
 * Display file attachments in message bubbles
 * Supports images, videos, and documents with appropriate preview/player
 */

'use client';

import { useState, useEffect, useRef } from 'react';
import Image from 'next/image';
import { Download, FileText, File } from 'lucide-react';
import { ImageLightbox } from './ImageLightbox';

interface Attachment {
  // New format (preferred)
  gcs_path?: string;
  filename: string;
  content_type?: string;
  file_size?: number;
  download_url?: string;

  // Legacy format
  contentType?: string;
  size?: number;
  cdnUrl?: string;
  previewUrl?: string;
  s3Url?: string;
}

interface AttachmentDisplayProps {
  attachments: Attachment[];
  isUserMessage?: boolean;
}

export function AttachmentDisplay({ attachments, isUserMessage = false }: AttachmentDisplayProps) {
  const [lightboxImage, setLightboxImage] = useState<{ url: string; filename: string } | null>(null);
  const [presignedUrls, setPresignedUrls] = useState<Record<number, string>>({});
  const fetchedRef = useRef<Set<string>>(new Set()); // Track which S3 URLs we've already fetched

  // Debug: Log attachments structure
  useEffect(() => {
    console.log('[AttachmentDisplay] Received attachments:', attachments);
    attachments.forEach((att, idx) => {
      console.log(`[AttachmentDisplay] Attachment ${idx}:`, {
        filename: att.filename,
        s3Url: att.s3Url,
        download_url: att.download_url,
        cdnUrl: att.cdnUrl,
        previewUrl: att.previewUrl,
        contentType: att.contentType || att.content_type,
      });
    });
  }, [attachments]);

  // Fetch presigned URLs for attachments with s3Url
  useEffect(() => {
    console.log('[AttachmentDisplay] useEffect triggered for new attachments');

    const fetchPresignedUrl = async (attachment: Attachment, idx: number) => {
      // Skip if already has a direct URL
      if (attachment.download_url || attachment.cdnUrl || attachment.previewUrl) {
        console.log(`[AttachmentDisplay] Skipping ${idx}: already has direct URL`);
        return;
      }

      // Skip if no s3Url
      if (!attachment.s3Url) {
        console.log(`[AttachmentDisplay] No s3Url for ${idx}, cannot fetch presigned URL`);
        return;
      }

      // Skip if already fetched
      if (fetchedRef.current.has(attachment.s3Url)) {
        console.log(`[AttachmentDisplay] Already fetched ${idx}:`, attachment.s3Url);
        return;
      }

      // Mark as fetching
      fetchedRef.current.add(attachment.s3Url);

      console.log(`[AttachmentDisplay] Fetching presigned URL for ${idx}:`, attachment.s3Url);
      try {
        const token = localStorage.getItem('access_token');
        const response = await fetch(`/api/v1/media/signed-url/${encodeURIComponent(attachment.s3Url)}`, {
          method: 'GET',
          headers: {
            ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
          },
        });

        console.log(`[AttachmentDisplay] Response for ${idx}:`, response.status);
        if (response.ok) {
          const data = await response.json();
          console.log(`[AttachmentDisplay] Got presigned URL for ${idx}:`, data.signed_url);
          setPresignedUrls(prev => ({ ...prev, [idx]: data.signed_url }));
        } else {
          console.error(`[AttachmentDisplay] Failed to fetch presigned URL for ${idx}:`, response.status, await response.text());
        }
      } catch (error) {
        console.error(`[AttachmentDisplay] Error fetching presigned URL for ${idx}:`, error);
      }
    };

    // Fetch all attachments that need presigned URLs
    attachments.forEach((attachment, idx) => {
      fetchPresignedUrl(attachment, idx);
    });
  }, [attachments]);

  if (!attachments || attachments.length === 0) {
    return null;
  }

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const getFileIcon = (contentType: string) => {
    if (contentType.includes('pdf')) {
      return <FileText className="w-5 h-5" />;
    }
    return <File className="w-5 h-5" />;
  };

  const handleDownload = async (url: string, filename: string) => {
    try {
      const response = await fetch(url);
      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(downloadUrl);
    } catch (error) {
      console.error('Download failed:', error);
      // Fallback: open in new tab
      window.open(url, '_blank');
    }
  };

  return (
    <>
      <div className={`mt-3 space-y-2 ${isUserMessage ? '' : ''}`}>
        {attachments.map((attachment, idx) => {
          // Get content type (prefer new format)
          const contentType = attachment.content_type || attachment.contentType || '';
          const fileSize = attachment.file_size || attachment.size || 0;
          // Use presigned URL if available, fallback to direct URLs
          const url = attachment.download_url || attachment.cdnUrl || attachment.previewUrl || presignedUrls[idx] || '';

          // Debug: Log URL construction
          console.log(`[AttachmentDisplay] Rendering attachment ${idx}:`, {
            filename: attachment.filename,
            contentType,
            download_url: attachment.download_url,
            cdnUrl: attachment.cdnUrl,
            previewUrl: attachment.previewUrl,
            presignedUrl: presignedUrls[idx],
            finalUrl: url,
          });

          // Image attachment
          if (contentType.startsWith('image/')) {
            // Check if URL is a presigned URL (contains AWS signature parameters)
            const isPresignedUrl = url && (url.includes('X-Amz-Signature') || url.includes('X-Amz-Algorithm'));

            return (
              <div key={idx} className="relative group">
                <div
                  className="relative rounded-lg overflow-hidden cursor-pointer hover:opacity-95 transition-opacity"
                  style={{ maxWidth: '300px' }}
                  onClick={() => setLightboxImage({ url, filename: attachment.filename })}
                >
                  {url ? (
                    <Image
                      src={url}
                      alt={attachment.filename}
                      width={300}
                      height={200}
                      className="rounded-lg object-cover"
                      style={{ maxHeight: '200px', width: 'auto' }}
                      unoptimized={isPresignedUrl}
                    />
                  ) : (
                    <div className="w-full h-32 bg-gray-200 dark:bg-gray-700 rounded-lg flex items-center justify-center">
                      <span className="text-gray-500 text-sm">图片加载中...</span>
                    </div>
                  )}

                  {/* Hover overlay */}
                  <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-10 transition-all flex items-center justify-center opacity-0 group-hover:opacity-100">
                    <span className="text-white text-sm bg-black bg-opacity-50 px-3 py-1 rounded-full">
                      点击查看
                    </span>
                  </div>
                </div>

                {/* Filename and size */}
                <div className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                  <span className="truncate max-w-[250px] inline-block">{attachment.filename}</span>
                  {fileSize > 0 && <span className="ml-2">({formatFileSize(fileSize)})</span>}
                </div>
              </div>
            );
          }

          // Video attachment
          if (contentType.startsWith('video/')) {
            return (
              <div key={idx} className="relative">
                <video
                  src={url}
                  controls
                  className="rounded-lg shadow-md"
                  style={{ maxWidth: '400px', maxHeight: '300px' }}
                >
                  您的浏览器不支持视频播放
                </video>

                {/* Filename and size */}
                <div className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                  <span className="truncate max-w-[350px] inline-block">{attachment.filename}</span>
                  {fileSize > 0 && <span className="ml-2">({formatFileSize(fileSize)})</span>}
                </div>
              </div>
            );
          }

          // Document/other file attachment
          return (
            <div
              key={idx}
              className={`flex items-center gap-3 p-3 rounded-lg border ${
                isUserMessage
                  ? 'bg-white/10 border-white/20'
                  : 'bg-gray-50 dark:bg-gray-800 border-gray-200 dark:border-gray-700'
              }`}
              style={{ maxWidth: '400px' }}
            >
              {/* File icon */}
              <div
                className={`flex-shrink-0 w-10 h-10 rounded-lg flex items-center justify-center ${
                  isUserMessage
                    ? 'bg-white/20 text-white'
                    : 'bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-300'
                }`}
              >
                {getFileIcon(contentType)}
              </div>

              {/* File info */}
              <div className="flex-1 min-w-0">
                <div
                  className={`text-sm font-medium truncate ${
                    isUserMessage ? 'text-white' : 'text-gray-900 dark:text-gray-100'
                  }`}
                >
                  {attachment.filename}
                </div>
                <div
                  className={`text-xs ${
                    isUserMessage ? 'text-white/70' : 'text-gray-500 dark:text-gray-400'
                  }`}
                >
                  {fileSize > 0 ? formatFileSize(fileSize) : '未知大小'}
                  {contentType && ` • ${contentType.split('/')[1]?.toUpperCase()}`}
                </div>
              </div>

              {/* Download button */}
              {url && (
                <button
                  onClick={() => handleDownload(url, attachment.filename)}
                  className={`flex-shrink-0 p-2 rounded-lg transition-colors ${
                    isUserMessage
                      ? 'hover:bg-white/10 text-white'
                      : 'hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-600 dark:text-gray-300'
                  }`}
                  title="下载"
                >
                  <Download className="w-4 h-4" />
                </button>
              )}
            </div>
          );
        })}
      </div>

      {/* Image Lightbox */}
      {lightboxImage && (
        <ImageLightbox
          imageUrl={lightboxImage.url}
          filename={lightboxImage.filename}
          onClose={() => setLightboxImage(null)}
        />
      )}
    </>
  );
}
