/**
 * Hook for uploading files to GCS with presigned URLs
 * Supports images, videos, and documents for chat attachments
 */

import { useState } from 'react';

export interface FileAttachment {
  gcs_path: string;
  filename: string;
  content_type: string;
  file_size: number;
  download_url: string;
  file_id: string;
  // For local preview before upload completes
  preview_url?: string;
}

export interface UploadProgress {
  file_id: string;
  filename: string;
  progress: number; // 0-100
  status: 'pending' | 'uploading' | 'success' | 'error';
  error?: string;
}

interface PresignedUrlResponse {
  upload_url: string;
  gcs_path: string;
  download_url: string;
  expires_in: number;
  file_id: string;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// File type limits
const FILE_SIZE_LIMITS: Record<string, number> = {
  'image': 20 * 1024 * 1024,      // 20MB
  'video': 200 * 1024 * 1024,     // 200MB
  'document': 50 * 1024 * 1024,   // 50MB
};

// Supported MIME types
const SUPPORTED_TYPES = {
  image: ['image/png', 'image/jpeg', 'image/jpg', 'image/webp', 'image/heic', 'image/heif'],
  video: ['video/mp4', 'video/mpeg', 'video/quicktime', 'video/x-msvideo', 'video/x-flv', 'video/webm', 'video/x-ms-wmv', 'video/3gpp'],
  document: ['application/pdf', 'text/plain', 'text/html', 'text/css', 'application/javascript', 'application/typescript', 'text/x-python', 'text/markdown', 'text/csv', 'application/xml', 'text/rtf'],
};

export function useFileUpload(sessionId: string) {
  const [uploadProgress, setUploadProgress] = useState<Map<string, UploadProgress>>(new Map());

  /**
   * Validate file type and size
   */
  const validateFile = (file: File): { valid: boolean; error?: string } => {
    const fileType = file.type;
    const category = Object.keys(SUPPORTED_TYPES).find(cat =>
      SUPPORTED_TYPES[cat as keyof typeof SUPPORTED_TYPES].includes(fileType)
    );

    if (!category) {
      return {
        valid: false,
        error: `Unsupported file type: ${fileType}. Please upload images, videos, or documents.`,
      };
    }

    const maxSize = FILE_SIZE_LIMITS[category];
    if (file.size > maxSize) {
      const maxSizeMB = Math.round(maxSize / 1024 / 1024);
      return {
        valid: false,
        error: `File too large. Maximum size for ${category} is ${maxSizeMB}MB`,
      };
    }

    return { valid: true };
  };

  /**
   * Get presigned upload URL from backend
   */
  const getPresignedUrl = async (
    filename: string,
    contentType: string,
    fileSize: number
  ): Promise<PresignedUrlResponse> => {
    const response = await fetch(`${API_BASE_URL}/api/v1/uploads/presigned/chat-attachment`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token')}`,
      },
      body: JSON.stringify({
        filename,
        content_type: contentType,
        file_size: fileSize,
        session_id: sessionId,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to get upload URL');
    }

    return response.json();
  };

  /**
   * Upload file to GCS using presigned URL
   */
  const uploadToGCS = async (
    file: File,
    uploadUrl: string,
    onProgress?: (progress: number) => void
  ): Promise<void> => {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();

      xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable && onProgress) {
          const progress = Math.round((e.loaded / e.total) * 100);
          onProgress(progress);
        }
      });

      xhr.addEventListener('load', () => {
        if (xhr.status === 200) {
          resolve();
        } else {
          reject(new Error(`Upload failed with status ${xhr.status}`));
        }
      });

      xhr.addEventListener('error', () => {
        reject(new Error('Upload failed'));
      });

      xhr.addEventListener('abort', () => {
        reject(new Error('Upload cancelled'));
      });

      xhr.open('PUT', uploadUrl);
      xhr.setRequestHeader('Content-Type', file.type);
      xhr.send(file);
    });
  };

  /**
   * Upload a single file
   */
  const uploadFile = async (file: File): Promise<FileAttachment> => {
    // Validate file
    const validation = validateFile(file);
    if (!validation.valid) {
      throw new Error(validation.error);
    }

    // Generate temporary file ID for tracking
    const tempFileId = `temp-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

    // Create preview URL for local display
    const previewUrl = file.type.startsWith('image/') || file.type.startsWith('video/')
      ? URL.createObjectURL(file)
      : undefined;

    // Initialize progress tracking
    setUploadProgress(prev => new Map(prev).set(tempFileId, {
      file_id: tempFileId,
      filename: file.name,
      progress: 0,
      status: 'pending',
    }));

    try {
      // Step 1: Get presigned URL
      const presignedData = await getPresignedUrl(file.name, file.type, file.size);

      // Step 2: Upload to GCS
      setUploadProgress(prev => new Map(prev).set(tempFileId, {
        file_id: tempFileId,
        filename: file.name,
        progress: 0,
        status: 'uploading',
      }));

      await uploadToGCS(file, presignedData.upload_url, (progress) => {
        setUploadProgress(prev => new Map(prev).set(tempFileId, {
          file_id: tempFileId,
          filename: file.name,
          progress,
          status: 'uploading',
        }));
      });

      // Step 3: Success
      setUploadProgress(prev => new Map(prev).set(tempFileId, {
        file_id: tempFileId,
        filename: file.name,
        progress: 100,
        status: 'success',
      }));

      // Return attachment info
      const attachment: FileAttachment = {
        gcs_path: presignedData.gcs_path,
        filename: file.name,
        content_type: file.type,
        file_size: file.size,
        download_url: presignedData.download_url,
        file_id: presignedData.file_id,
        preview_url: previewUrl,
      };

      return attachment;
    } catch (error) {
      // Update progress with error
      setUploadProgress(prev => new Map(prev).set(tempFileId, {
        file_id: tempFileId,
        filename: file.name,
        progress: 0,
        status: 'error',
        error: error instanceof Error ? error.message : 'Upload failed',
      }));

      throw error;
    }
  };

  /**
   * Upload multiple files
   */
  const uploadFiles = async (files: File[]): Promise<FileAttachment[]> => {
    const results = await Promise.allSettled(files.map(file => uploadFile(file)));

    const attachments: FileAttachment[] = [];
    const errors: string[] = [];

    results.forEach((result, index) => {
      if (result.status === 'fulfilled') {
        attachments.push(result.value);
      } else {
        errors.push(`${files[index].name}: ${result.reason.message}`);
      }
    });

    if (errors.length > 0) {
      console.error('Some files failed to upload:', errors);
      // Still return successful uploads
    }

    return attachments;
  };

  /**
   * Clear upload progress for a file
   */
  const clearProgress = (fileId: string) => {
    setUploadProgress(prev => {
      const next = new Map(prev);
      next.delete(fileId);
      return next;
    });
  };

  /**
   * Clear all upload progress
   */
  const clearAllProgress = () => {
    setUploadProgress(new Map());
  };

  return {
    uploadFile,
    uploadFiles,
    uploadProgress: Array.from(uploadProgress.values()),
    clearProgress,
    clearAllProgress,
  };
}
