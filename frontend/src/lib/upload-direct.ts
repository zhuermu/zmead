/**
 * Direct upload to GCS using presigned URLs
 *
 * Flow:
 * 1. Request presigned URL from backend
 * 2. Upload file directly to GCS
 * 3. On message send, confirm upload (backend moves to permanent storage)
 */

export interface PresignedUploadResponse {
  uploadUrl: string
  fileKey: string
  fileId: string
  expiresAt: string
  cdnUrl: string
}

export interface ConfirmUploadResponse {
  fileKey: string
  fileId: string
  permanentUrl: string
  cdnUrl: string
  geminiFileUri?: string
  geminiFileName?: string
}

export interface UploadedFile {
  file: File
  presigned: PresignedUploadResponse
  status: 'pending' | 'uploading' | 'uploaded' | 'confirmed' | 'error'
  progress: number
  error?: string
  confirmed?: ConfirmUploadResponse
}

/**
 * Step 1: Request presigned URL from backend
 */
export async function requestPresignedUrl(
  file: File,
  token?: string
): Promise<PresignedUploadResponse> {
  const response = await fetch('/api/v1/uploads/presigned/generate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({
      filename: file.name,
      contentType: file.type,
      size: file.size,
    }),
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to get presigned URL')
  }

  return response.json()
}

/**
 * Step 2: Upload file directly to GCS using presigned URL
 */
export async function uploadToGCS(
  file: File,
  presignedUrl: string,
  onProgress?: (progress: number) => void
): Promise<void> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()

    xhr.upload.addEventListener('progress', (e) => {
      if (e.lengthComputable && onProgress) {
        const progress = (e.loaded / e.total) * 100
        onProgress(progress)
      }
    })

    xhr.addEventListener('load', () => {
      if (xhr.status === 200 || xhr.status === 204) {
        resolve()
      } else {
        reject(new Error(`Upload failed with status ${xhr.status}`))
      }
    })

    xhr.addEventListener('error', () => {
      reject(new Error('Upload failed'))
    })

    xhr.addEventListener('abort', () => {
      reject(new Error('Upload aborted'))
    })

    xhr.open('PUT', presignedUrl)
    xhr.setRequestHeader('Content-Type', file.type)
    xhr.send(file)
  })
}

/**
 * Step 3: Confirm upload and move to permanent storage
 * Called when user sends the message
 */
export async function confirmUpload(
  fileKey: string,
  fileId: string,
  token?: string
): Promise<ConfirmUploadResponse> {
  const response = await fetch('/api/v1/uploads/presigned/confirm', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({
      fileKey,
      fileId,
    }),
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to confirm upload')
  }

  return response.json()
}

/**
 * Complete upload flow: presigned URL → upload → return file info
 */
export async function uploadFileDirect(
  file: File,
  token?: string,
  onProgress?: (progress: number) => void
): Promise<UploadedFile> {
  // Step 1: Get presigned URL
  const presigned = await requestPresignedUrl(file, token)

  const uploadedFile: UploadedFile = {
    file,
    presigned,
    status: 'uploading',
    progress: 0,
  }

  try {
    // Step 2: Upload to GCS
    await uploadToGCS(file, presigned.uploadUrl, (progress) => {
      uploadedFile.progress = progress
      onProgress?.(progress)
    })

    uploadedFile.status = 'uploaded'
    uploadedFile.progress = 100
    return uploadedFile
  } catch (error) {
    uploadedFile.status = 'error'
    uploadedFile.error = error instanceof Error ? error.message : 'Upload failed'
    throw error
  }
}

/**
 * Confirm multiple uploads at once
 */
export async function confirmMultipleUploads(
  files: UploadedFile[],
  token?: string
): Promise<ConfirmUploadResponse[]> {
  const confirmations = await Promise.all(
    files
      .filter(f => f.status === 'uploaded')
      .map(f => confirmUpload(f.presigned.fileKey, f.presigned.fileId, token))
  )

  return confirmations
}
