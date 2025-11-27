import { useState, useRef, DragEvent, ChangeEvent } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card } from '@/components/ui/card';
import api from '@/lib/api';
import { Upload, X, Video, CheckCircle } from 'lucide-react';
import Image from 'next/image';

interface CreativeUploadProps {
  onClose: () => void;
  onComplete: () => void;
}

interface UploadFile {
  file: File;
  preview: string;
  progress: number;
  status: 'pending' | 'uploading' | 'success' | 'error';
  error?: string;
}

export function CreativeUpload({ onClose, onComplete }: CreativeUploadProps) {
  const [files, setFiles] = useState<UploadFile[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [productUrl, setProductUrl] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);

    const droppedFiles = Array.from(e.dataTransfer.files);
    addFiles(droppedFiles);
  };

  const handleFileSelect = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const selectedFiles = Array.from(e.target.files);
      addFiles(selectedFiles);
    }
  };

  const addFiles = (newFiles: File[]) => {
    const validFiles = newFiles.filter((file) => {
      const isImage = file.type.startsWith('image/');
      const isVideo = file.type.startsWith('video/');
      return isImage || isVideo;
    });

    const uploadFiles: UploadFile[] = validFiles.map((file) => ({
      file,
      preview: URL.createObjectURL(file),
      progress: 0,
      status: 'pending',
    }));

    setFiles((prev) => [...prev, ...uploadFiles]);
  };

  const removeFile = (index: number) => {
    setFiles((prev) => {
      const newFiles = [...prev];
      URL.revokeObjectURL(newFiles[index].preview);
      newFiles.splice(index, 1);
      return newFiles;
    });
  };

  const uploadFile = async (uploadFile: UploadFile, index: number) => {
    try {
      // Update status to uploading
      setFiles((prev) => {
        const newFiles = [...prev];
        newFiles[index].status = 'uploading';
        return newFiles;
      });

      // Step 1: Get presigned upload URL
      const urlResponse = await api.post('/creatives/upload-url', {
        file_name: uploadFile.file.name,
        file_type: uploadFile.file.type,
        file_size: uploadFile.file.size,
      });

      const { upload_url, creative_id } = urlResponse.data;

      // Step 2: Upload file to S3 with progress tracking
      await new Promise<void>((resolve, reject) => {
        const xhr = new XMLHttpRequest();

        xhr.upload.addEventListener('progress', (e) => {
          if (e.lengthComputable) {
            const progress = Math.round((e.loaded / e.total) * 100);
            setFiles((prev) => {
              const newFiles = [...prev];
              newFiles[index].progress = progress;
              return newFiles;
            });
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

        xhr.open('PUT', upload_url);
        xhr.setRequestHeader('Content-Type', uploadFile.file.type);
        xhr.send(uploadFile.file);
      });

      // Step 3: Confirm upload and save metadata
      await api.post(`/creatives/${creative_id}/confirm`, {
        product_url: productUrl || undefined,
      });

      // Update status to success
      setFiles((prev) => {
        const newFiles = [...prev];
        newFiles[index].status = 'success';
        newFiles[index].progress = 100;
        return newFiles;
      });
    } catch (error) {
      console.error('Upload failed:', error);
      setFiles((prev) => {
        const newFiles = [...prev];
        newFiles[index].status = 'error';
        newFiles[index].error = 'Upload failed';
        return newFiles;
      });
    }
  };

  const handleUploadAll = async () => {
    // Upload files sequentially to avoid overwhelming the server
    for (let i = 0; i < files.length; i++) {
      if (files[i].status === 'pending') {
        await uploadFile(files[i], i);
      }
    }

    // Check if all uploads succeeded
    const allSuccess = files.every((f) => f.status === 'success');
    if (allSuccess) {
      onComplete();
    }
  };

  const allUploaded = files.length > 0 && files.every((f) => f.status === 'success');
  const hasFiles = files.length > 0;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <Card className="w-full max-w-3xl max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold">Upload Creatives</h2>
            <Button variant="ghost" size="sm" onClick={onClose}>
              <X className="w-5 h-5" />
            </Button>
          </div>

          {/* Product URL Input */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Product URL (Optional)
            </label>
            <Input
              type="url"
              placeholder="https://example.com/product"
              value={productUrl}
              onChange={(e) => setProductUrl(e.target.value)}
            />
          </div>

          {/* Drag and Drop Area */}
          <div
            className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
              isDragging
                ? 'border-blue-500 bg-blue-50'
                : 'border-gray-300 hover:border-gray-400'
            }`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <Upload className="w-12 h-12 mx-auto mb-4 text-gray-400" />
            <p className="text-lg font-medium text-gray-700 mb-2">
              Drag and drop files here
            </p>
            <p className="text-sm text-gray-500 mb-4">
              or click to browse (images and videos)
            </p>
            <Button
              variant="outline"
              onClick={() => fileInputRef.current?.click()}
            >
              Browse Files
            </Button>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept="image/*,video/*"
              className="hidden"
              onChange={handleFileSelect}
            />
          </div>

          {/* File List */}
          {hasFiles && (
            <div className="mt-6 space-y-3">
              {files.map((uploadFile, index) => (
                <div
                  key={index}
                  className="flex items-center gap-4 p-3 bg-gray-50 rounded-lg"
                >
                  {/* Preview */}
                  <div className="relative w-16 h-16 bg-gray-200 rounded overflow-hidden flex-shrink-0">
                    {uploadFile.file.type.startsWith('image/') ? (
                      <Image
                        src={uploadFile.preview}
                        alt="Preview"
                        fill
                        className="object-cover"
                      />
                    ) : (
                      <div className="flex items-center justify-center h-full">
                        <Video className="w-6 h-6 text-gray-400" />
                      </div>
                    )}
                  </div>

                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {uploadFile.file.name}
                    </p>
                    <p className="text-xs text-gray-500">
                      {(uploadFile.file.size / (1024 * 1024)).toFixed(2)} MB
                    </p>

                    {/* Progress Bar */}
                    {uploadFile.status === 'uploading' && (
                      <div className="mt-2">
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-blue-600 h-2 rounded-full transition-all"
                            style={{ width: `${uploadFile.progress}%` }}
                          />
                        </div>
                        <p className="text-xs text-gray-500 mt-1">
                          {uploadFile.progress}%
                        </p>
                      </div>
                    )}

                    {/* Error Message */}
                    {uploadFile.status === 'error' && (
                      <p className="text-xs text-red-500 mt-1">
                        {uploadFile.error}
                      </p>
                    )}
                  </div>

                  {/* Status Icon */}
                  <div className="flex-shrink-0">
                    {uploadFile.status === 'success' && (
                      <CheckCircle className="w-5 h-5 text-green-500" />
                    )}
                    {uploadFile.status === 'pending' && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => removeFile(index)}
                      >
                        <X className="w-4 h-4" />
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Actions */}
          <div className="mt-6 flex justify-end gap-3">
            <Button variant="outline" onClick={onClose}>
              Cancel
            </Button>
            {allUploaded ? (
              <Button onClick={onComplete}>Done</Button>
            ) : (
              <Button
                onClick={handleUploadAll}
                disabled={!hasFiles || files.some((f) => f.status === 'uploading')}
              >
                Upload {files.length > 0 && `(${files.length})`}
              </Button>
            )}
          </div>
        </div>
      </Card>
    </div>
  );
}
