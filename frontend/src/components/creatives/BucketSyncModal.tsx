"use client";

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';
import {
  X,
  Cloud,
  CloudDownload,
  CheckCircle,
  AlertCircle,
  Image as ImageIcon,
  Video,
  Music,
  RefreshCw,
  Check
} from 'lucide-react';
import Image from 'next/image';
import { BucketFile, BucketListResponse, BucketSyncResponse } from '@/types';

interface BucketSyncModalProps {
  onClose: () => void;
  onComplete: () => void;
}

export function BucketSyncModal({ onClose, onComplete }: BucketSyncModalProps) {
  const [files, setFiles] = useState<BucketFile[]>([]);
  const [selectedFiles, setSelectedFiles] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [syncResult, setSyncResult] = useState<BucketSyncResponse | null>(null);

  useEffect(() => {
    fetchBucketFiles();
  }, []);

  const fetchBucketFiles = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await api.get<BucketListResponse>('/creatives/bucket/files');
      setFiles(response.data.files);
    } catch (err) {
      console.error('Failed to fetch bucket files:', err);
      setError('Failed to load files from cloud storage');
    } finally {
      setLoading(false);
    }
  };

  const toggleFileSelection = (fileName: string) => {
    const newSelected = new Set(selectedFiles);
    if (newSelected.has(fileName)) {
      newSelected.delete(fileName);
    } else {
      newSelected.add(fileName);
    }
    setSelectedFiles(newSelected);
  };

  const selectAllUnsynced = () => {
    const unsyncedFiles = files.filter(f => !f.synced).map(f => f.name);
    setSelectedFiles(new Set(unsyncedFiles));
  };

  const deselectAll = () => {
    setSelectedFiles(new Set());
  };

  const handleSync = async () => {
    if (selectedFiles.size === 0) return;

    try {
      setSyncing(true);
      setError(null);

      const response = await api.post<BucketSyncResponse>('/creatives/bucket/sync', {
        file_keys: Array.from(selectedFiles),
      });

      setSyncResult(response.data);

      // Refresh file list to update synced status
      await fetchBucketFiles();
      setSelectedFiles(new Set());

      // Auto-complete after showing result (longer delay if there are failures)
      if (response.data.syncedCount > 0) {
        const delay = response.data.failedCount > 0 ? 2500 : 1500;
        setTimeout(() => {
          onComplete();
        }, delay);
      }
    } catch (err) {
      console.error('Failed to sync files:', err);
      setError('Failed to sync files');
    } finally {
      setSyncing(false);
    }
  };

  const getFileIcon = (contentType?: string) => {
    if (!contentType) return <ImageIcon className="w-5 h-5 text-gray-400" />;

    if (contentType.startsWith('video/')) {
      return <Video className="w-5 h-5 text-purple-500" />;
    } else if (contentType.startsWith('audio/')) {
      return <Music className="w-5 h-5 text-green-500" />;
    } else {
      return <ImageIcon className="w-5 h-5 text-blue-500" />;
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return '';
    return new Date(dateStr).toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const unsyncedCount = files.filter(f => !f.synced).length;
  const selectedCount = selectedFiles.size;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <Card className="w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="p-6 border-b flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Cloud className="w-6 h-6 text-blue-500" />
            <div>
              <h2 className="text-xl font-bold">Sync from Cloud Storage</h2>
              <p className="text-sm text-gray-500">
                Import files uploaded via AI Agent
              </p>
            </div>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose}>
            <X className="w-5 h-5" />
          </Button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {/* Loading State */}
          {loading && (
            <div className="flex items-center justify-center py-12">
              <RefreshCw className="w-8 h-8 animate-spin text-blue-500" />
              <span className="ml-3 text-gray-600">Loading files...</span>
            </div>
          )}

          {/* Error State */}
          {error && (
            <div className="bg-red-50 text-red-700 p-4 rounded-lg flex items-center gap-2">
              <AlertCircle className="w-5 h-5" />
              <span>{error}</span>
              <Button
                variant="outline"
                size="sm"
                onClick={fetchBucketFiles}
                className="ml-auto"
              >
                Retry
              </Button>
            </div>
          )}

          {/* Sync Result */}
          {syncResult && (
            <div className={`mb-4 p-4 rounded-lg ${
              syncResult.failedCount === 0
                ? 'bg-green-50 text-green-700'
                : 'bg-yellow-50 text-yellow-700'
            }`}>
              <div className="flex items-center gap-2">
                {syncResult.failedCount === 0 ? (
                  <CheckCircle className="w-5 h-5" />
                ) : (
                  <AlertCircle className="w-5 h-5" />
                )}
                <span>
                  Synced {syncResult.syncedCount} files
                  {syncResult.failedCount > 0 && `, ${syncResult.failedCount} failed`}
                </span>
              </div>
            </div>
          )}

          {/* Empty State */}
          {!loading && !error && files.length === 0 && (
            <div className="text-center py-12">
              <Cloud className="w-16 h-16 mx-auto mb-4 text-gray-300" />
              <p className="text-gray-500 mb-2">No files found in cloud storage</p>
              <p className="text-sm text-gray-400">
                Upload files via AI Agent to see them here
              </p>
            </div>
          )}

          {/* File List */}
          {!loading && files.length > 0 && (
            <>
              {/* Selection Controls */}
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <span className="text-sm text-gray-600">
                    {files.length} files total, {unsyncedCount} not synced
                  </span>
                  {selectedCount > 0 && (
                    <Badge variant="secondary">
                      {selectedCount} selected
                    </Badge>
                  )}
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={selectAllUnsynced}
                    disabled={unsyncedCount === 0}
                  >
                    Select All Unsynced
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={deselectAll}
                    disabled={selectedCount === 0}
                  >
                    Deselect All
                  </Button>
                </div>
              </div>

              {/* File Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {files.map((file) => (
                  <div
                    key={file.name}
                    className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-all ${
                      file.synced
                        ? 'bg-gray-50 opacity-60 cursor-not-allowed'
                        : selectedFiles.has(file.name)
                          ? 'border-blue-500 bg-blue-50'
                          : 'border-gray-200 hover:border-gray-300'
                    }`}
                    onClick={() => !file.synced && toggleFileSelection(file.name)}
                  >
                    {/* Checkbox / Status */}
                    <div className="flex-shrink-0">
                      {file.synced ? (
                        <CheckCircle className="w-5 h-5 text-green-500" />
                      ) : (
                        <div className={`w-5 h-5 rounded border-2 flex items-center justify-center ${
                          selectedFiles.has(file.name)
                            ? 'border-blue-500 bg-blue-500'
                            : 'border-gray-300'
                        }`}>
                          {selectedFiles.has(file.name) && (
                            <Check className="w-3 h-3 text-white" />
                          )}
                        </div>
                      )}
                    </div>

                    {/* Preview */}
                    <div className="w-12 h-12 bg-gray-100 rounded overflow-hidden flex-shrink-0 flex items-center justify-center">
                      {file.contentType?.startsWith('image/') ? (
                        <Image
                          src={file.url}
                          alt={file.name}
                          width={48}
                          height={48}
                          className="object-cover w-full h-full"
                          unoptimized
                        />
                      ) : (
                        getFileIcon(file.contentType)
                      )}
                    </div>

                    {/* Info */}
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {file.name.split('/').pop()}
                      </p>
                      <div className="flex items-center gap-2 text-xs text-gray-500">
                        <span>{formatFileSize(file.size)}</span>
                        {file.updated && (
                          <>
                            <span>•</span>
                            <span>{formatDate(file.updated)}</span>
                          </>
                        )}
                      </div>
                    </div>

                    {/* Status Badge */}
                    <div className="flex-shrink-0">
                      {file.synced ? (
                        <Badge variant="secondary" className="text-xs">
                          Synced
                        </Badge>
                      ) : (
                        <Badge variant="outline" className="text-xs">
                          New
                        </Badge>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <div className="p-6 border-t flex items-center justify-between">
          <Button variant="outline" onClick={fetchBucketFiles} disabled={loading}>
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <div className="flex gap-3">
            <Button variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button
              onClick={handleSync}
              disabled={selectedCount === 0 || syncing}
              className={syncResult && syncResult.syncedCount > 0 ? 'bg-green-600 hover:bg-green-700' : ''}
            >
              {syncResult && syncResult.syncedCount > 0 ? (
                <>
                  <CheckCircle className="w-4 h-4 mr-2" />
                  Synced {syncResult.syncedCount} files!
                </>
              ) : syncing ? (
                <>
                  <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                  Syncing...
                </>
              ) : (
                <>
                  <CloudDownload className="w-4 h-4 mr-2" />
                  Sync {selectedCount > 0 ? `(${selectedCount})` : ''}
                </>
              )}
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
}
