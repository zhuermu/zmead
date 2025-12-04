/**
 * React Hook for direct file upload to GCS
 *
 * Usage:
 * ```tsx
 * const { uploadFiles, uploadedFiles, confirmUploads, isUploading } = useDirectUpload()
 *
 * // When user selects files
 * const handleFileSelect = async (files: FileList) => {
 *   await uploadFiles(Array.from(files))
 * }
 *
 * // When user sends message
 * const handleSendMessage = async () => {
 *   const confirmedFiles = await confirmUploads()
 *   // Send message with confirmedFiles
 * }
 * ```
 */

import { useState, useCallback } from 'react'
import {
  uploadFileDirect,
  confirmMultipleUploads,
  UploadedFile,
  ConfirmUploadResponse,
} from '@/lib/upload-direct'

export interface UseDirectUploadReturn {
  uploadFiles: (files: File[]) => Promise<void>
  uploadedFiles: UploadedFile[]
  confirmUploads: () => Promise<ConfirmUploadResponse[]>
  removeFile: (fileId: string) => void
  clearFiles: () => void
  isUploading: boolean
  hasUploadedFiles: boolean
}

export function useDirectUpload(): UseDirectUploadReturn {
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([])
  const [isUploading, setIsUploading] = useState(false)

  /**
   * Upload files directly to GCS (temp storage)
   */
  const uploadFiles = useCallback(
    async (files: File[]) => {
      const token = localStorage.getItem('access_token')
      console.log('[useDirectUpload] Checking token:', token ? 'Token exists' : 'No token (development mode)')

      setIsUploading(true)

      try {
        const uploads = await Promise.allSettled(
          files.map(file =>
            uploadFileDirect(file, token || undefined, (progress) => {
              // Update progress for this specific file
              setUploadedFiles(prev =>
                prev.map(f =>
                  f.file === file ? { ...f, progress } : f
                )
              )
            })
          )
        )

        const newFiles: UploadedFile[] = []

        uploads.forEach((result, index) => {
          if (result.status === 'fulfilled') {
            newFiles.push(result.value)
          } else {
            // Create error file entry
            newFiles.push({
              file: files[index],
              presigned: {
                uploadUrl: '',
                fileKey: '',
                fileId: '',
                expiresAt: '',
                cdnUrl: '',
              },
              status: 'error',
              progress: 0,
              error: result.reason?.message || 'Upload failed',
            })
          }
        })

        setUploadedFiles(prev => [...prev, ...newFiles])
      } finally {
        setIsUploading(false)
      }
    },
    []
  )

  /**
   * Confirm uploads and move to permanent storage
   * Call this when user sends the message
   */
  const confirmUploads = useCallback(async (): Promise<ConfirmUploadResponse[]> => {
    const token = localStorage.getItem('access_token')

    const filesToConfirm = uploadedFiles.filter(f => f.status === 'uploaded')

    if (filesToConfirm.length === 0) {
      return []
    }

    const confirmations = await confirmMultipleUploads(filesToConfirm, token || undefined)

    // Update files with confirmation data
    setUploadedFiles(prev =>
      prev.map(file => {
        const confirmation = confirmations.find(
          c => c.fileId === file.presigned.fileId
        )
        if (confirmation) {
          return {
            ...file,
            status: 'confirmed' as const,
            confirmed: confirmation,
          }
        }
        return file
      })
    )

    return confirmations
  }, [uploadedFiles])

  /**
   * Remove a file from the list
   */
  const removeFile = useCallback((fileId: string) => {
    setUploadedFiles(prev => prev.filter(f => f.presigned.fileId !== fileId))
  }, [])

  /**
   * Clear all files
   */
  const clearFiles = useCallback(() => {
    setUploadedFiles([])
  }, [])

  const hasUploadedFiles = uploadedFiles.some(
    f => f.status === 'uploaded' || f.status === 'confirmed'
  )

  return {
    uploadFiles,
    uploadedFiles,
    confirmUploads,
    removeFile,
    clearFiles,
    isUploading,
    hasUploadedFiles,
  }
}
