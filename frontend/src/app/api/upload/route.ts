import { NextRequest, NextResponse } from 'next/server';

export const runtime = 'nodejs';

// Maximum file size: 50MB
const MAX_FILE_SIZE = 50 * 1024 * 1024;

// Allowed file types
const ALLOWED_TYPES = new Set([
  // Images
  'image/jpeg',
  'image/png',
  'image/gif',
  'image/webp',
  'image/svg+xml',
  'image/bmp',
  // Videos
  'video/mp4',
  'video/quicktime',
  'video/webm',
  'video/x-msvideo',
  // Documents
  'application/pdf',
  'application/msword',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  // Spreadsheets
  'application/vnd.ms-excel',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  'text/csv',
  // Presentations
  'application/vnd.ms-powerpoint',
  'application/vnd.openxmlformats-officedocument.presentationml.presentation',
  // Text/Code
  'text/plain',
  'text/markdown',
  'application/json',
  'application/xml',
  'text/xml',
  'text/yaml',
  'text/javascript',
  'text/typescript',
  'text/css',
  'text/html',
]);

interface UploadedFile {
  id: string;
  filename: string;
  contentType: string;
  size: number;
  s3Url: string;
  cdnUrl: string;
}

export async function POST(req: NextRequest) {
  try {
    const formData = await req.formData();
    const files = formData.getAll('files') as File[];

    if (!files || files.length === 0) {
      return NextResponse.json(
        { error: 'No files provided' },
        { status: 400 }
      );
    }

    // Get auth token from request
    const authHeader = req.headers.get('authorization');
    const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

    const uploadedFiles: UploadedFile[] = [];
    const errors: Array<{ filename: string; error: string }> = [];

    for (const file of files) {
      // Validate file size
      if (file.size > MAX_FILE_SIZE) {
        errors.push({
          filename: file.name,
          error: `File too large. Maximum size is ${MAX_FILE_SIZE / 1024 / 1024}MB`,
        });
        continue;
      }

      // Validate file type
      if (!ALLOWED_TYPES.has(file.type)) {
        errors.push({
          filename: file.name,
          error: `File type ${file.type} not allowed`,
        });
        continue;
      }

      try {
        // Step 1: Get presigned upload URL from backend
        const presignedResponse = await fetch(`${backendUrl}/api/v1/creatives/upload-url`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(authHeader && { 'Authorization': authHeader }),
          },
          body: JSON.stringify({
            filename: file.name,
            content_type: file.type,
          }),
        });

        if (!presignedResponse.ok) {
          const error = await presignedResponse.text();
          errors.push({
            filename: file.name,
            error: `Failed to get upload URL: ${error}`,
          });
          continue;
        }

        const presignedData = await presignedResponse.json();

        // Step 2: Upload file to S3 using presigned URL
        const fileBuffer = await file.arrayBuffer();

        // If upload_fields is provided, use multipart form upload
        if (presignedData.upload_fields && Object.keys(presignedData.upload_fields).length > 0) {
          const s3FormData = new FormData();

          // Add the presigned fields first
          for (const [key, value] of Object.entries(presignedData.upload_fields)) {
            s3FormData.append(key, value as string);
          }

          // Add the file last
          s3FormData.append('file', new Blob([fileBuffer], { type: file.type }), file.name);

          const s3Response = await fetch(presignedData.upload_url, {
            method: 'POST',
            body: s3FormData,
          });

          if (!s3Response.ok && s3Response.status !== 204) {
            const s3Error = await s3Response.text();
            errors.push({
              filename: file.name,
              error: `S3 upload failed: ${s3Error}`,
            });
            continue;
          }
        } else {
          // Use PUT request for presigned PUT URL
          const s3Response = await fetch(presignedData.upload_url, {
            method: 'PUT',
            body: fileBuffer,
            headers: {
              'Content-Type': file.type,
            },
          });

          if (!s3Response.ok && s3Response.status !== 204) {
            errors.push({
              filename: file.name,
              error: `S3 upload failed: HTTP ${s3Response.status}`,
            });
            continue;
          }
        }

        // Step 3: Create file record (optional - for tracking uploaded references)
        uploadedFiles.push({
          id: presignedData.file_key || `file_${Date.now()}_${Math.random().toString(36).slice(2)}`,
          filename: file.name,
          contentType: file.type,
          size: file.size,
          s3Url: presignedData.s3_url,
          cdnUrl: presignedData.cdn_url,
        });

      } catch (uploadError) {
        errors.push({
          filename: file.name,
          error: uploadError instanceof Error ? uploadError.message : 'Upload failed',
        });
      }
    }

    return NextResponse.json({
      success: uploadedFiles.length > 0,
      uploaded: uploadedFiles,
      errors: errors.length > 0 ? errors : undefined,
      message: uploadedFiles.length > 0
        ? `Successfully uploaded ${uploadedFiles.length} file(s)`
        : 'No files uploaded',
    });

  } catch (error) {
    console.error('Upload API error:', error);
    return NextResponse.json(
      {
        error: 'Internal server error',
        message: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    );
  }
}
