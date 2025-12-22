import { useState } from 'react';
import { Creative } from '@/types';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';
import {
  X,
  Star,
  Download,
  Trash2,
  Edit2,
  Save,
  ExternalLink,
  Image as ImageIcon,
  Video,
} from 'lucide-react';
import Image from 'next/image';

interface CreativeDetailModalProps {
  creative: Creative;
  onClose: () => void;
  onUpdate: () => void;
  onDelete: () => void;
}

export function CreativeDetailModal({
  creative,
  onClose,
  onUpdate,
  onDelete,
}: CreativeDetailModalProps) {
  // Use signed URL for secure access, fallback to cdnUrl
  const imageUrl = creative.signedUrl || creative.cdnUrl;

  const [isEditing, setIsEditing] = useState(false);
  const [editedTags, setEditedTags] = useState<string[]>(creative.tags);
  const [editedProductUrl, setEditedProductUrl] = useState(creative.productUrl || '');
  const [newTag, setNewTag] = useState('');
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const handleAddTag = () => {
    if (newTag.trim() && !editedTags.includes(newTag.trim())) {
      setEditedTags([...editedTags, newTag.trim()]);
      setNewTag('');
    }
  };

  const handleRemoveTag = (tagToRemove: string) => {
    setEditedTags(editedTags.filter((tag) => tag !== tagToRemove));
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      await api.put(`/creatives/${creative.id}`, {
        tags: editedTags,
        product_url: editedProductUrl || null,
      });
      setIsEditing(false);
      onUpdate();
    } catch (error) {
      console.error('Failed to update creative:', error);
      alert('Failed to update creative');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm('Are you sure you want to delete this creative?')) {
      return;
    }

    try {
      setDeleting(true);
      await api.delete(`/creatives/${creative.id}`);
      onDelete();
    } catch (error) {
      console.error('Failed to delete creative:', error);
      alert('Failed to delete creative');
    } finally {
      setDeleting(false);
    }
  };

  const handleDownload = () => {
    window.open(imageUrl, '_blank');
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <Card className="w-full max-w-4xl max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold">Creative Details</h2>
            <Button variant="ghost" size="sm" onClick={onClose}>
              <X className="w-5 h-5" />
            </Button>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Left Column - Preview */}
            <div>
              <div className="relative w-full aspect-square bg-gray-100 rounded-lg overflow-hidden">
                {creative.fileType === 'image' ? (
                  <Image
                    src={imageUrl}
                    alt="Creative"
                    fill
                    className="object-contain"
                    unoptimized
                  />
                ) : (
                  <div className="flex flex-col items-center justify-center h-full">
                    <Video className="w-16 h-16 text-gray-400 mb-4" />
                    <p className="text-sm text-gray-500">Video preview not available</p>
                    <Button
                      variant="outline"
                      size="sm"
                      className="mt-4"
                      onClick={handleDownload}
                    >
                      <ExternalLink className="w-4 h-4 mr-2" />
                      Open Video
                    </Button>
                  </div>
                )}
              </div>

              {/* Action Buttons */}
              <div className="flex gap-2 mt-4">
                <Button
                  variant="outline"
                  className="flex-1"
                  onClick={handleDownload}
                >
                  <Download className="w-4 h-4 mr-2" />
                  Download
                </Button>
                <Button
                  variant="outline"
                  className="flex-1"
                  onClick={() => setIsEditing(!isEditing)}
                  disabled={deleting}
                >
                  <Edit2 className="w-4 h-4 mr-2" />
                  {isEditing ? 'Cancel' : 'Edit'}
                </Button>
                <Button
                  variant="destructive"
                  onClick={handleDelete}
                  disabled={deleting}
                >
                  <Trash2 className="w-4 h-4" />
                </Button>
              </div>
            </div>

            {/* Right Column - Details */}
            <div className="space-y-6">
              {/* Type and Score */}
              <div>
                <h3 className="text-sm font-medium text-gray-500 mb-2">Type & Quality</h3>
                <div className="flex items-center gap-2">
                  <Badge variant={creative.fileType === 'image' ? 'default' : 'secondary'}>
                    {creative.fileType === 'image' ? (
                      <ImageIcon className="w-3 h-3 mr-1" />
                    ) : (
                      <Video className="w-3 h-3 mr-1" />
                    )}
                    {creative.fileType}
                  </Badge>
                  {creative.score && (
                    <Badge className="bg-yellow-500 text-white">
                      <Star className="w-3 h-3 mr-1 fill-current" />
                      {creative.score.toFixed(1)} / 10
                    </Badge>
                  )}
                </div>
              </div>

              {/* File Info */}
              <div>
                <h3 className="text-sm font-medium text-gray-500 mb-2">File Information</h3>
                <div className="space-y-1 text-sm">
                  <p>
                    <span className="text-gray-600">Size:</span>{' '}
                    <span className="font-medium">{formatFileSize(creative.fileSize)}</span>
                  </p>
                  <p>
                    <span className="text-gray-600">Created:</span>{' '}
                    <span className="font-medium">{formatDate(creative.createdAt)}</span>
                  </p>
                  <div className="flex items-center gap-2">
                    <span className="text-gray-600 text-sm">Status:</span>
                    <Badge variant={creative.status === 'active' ? 'default' : 'secondary'}>
                      {creative.status}
                    </Badge>
                  </div>
                </div>
              </div>

              {/* Product URL */}
              <div>
                <h3 className="text-sm font-medium text-gray-500 mb-2">Product URL</h3>
                {isEditing ? (
                  <Input
                    type="url"
                    placeholder="https://example.com/product"
                    value={editedProductUrl}
                    onChange={(e) => setEditedProductUrl(e.target.value)}
                  />
                ) : creative.productUrl ? (
                  <a
                    href={creative.productUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:underline text-sm flex items-center gap-1"
                  >
                    {creative.productUrl}
                    <ExternalLink className="w-3 h-3" />
                  </a>
                ) : (
                  <p className="text-sm text-gray-500">No product URL</p>
                )}
              </div>

              {/* Tags */}
              <div>
                <h3 className="text-sm font-medium text-gray-500 mb-2">Tags</h3>
                <div className="flex flex-wrap gap-2 mb-2">
                  {editedTags.map((tag, index) => (
                    <Badge key={index} variant="outline" className="text-sm">
                      {tag}
                      {isEditing && (
                        <button
                          onClick={() => handleRemoveTag(tag)}
                          className="ml-1 hover:text-red-500"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      )}
                    </Badge>
                  ))}
                  {editedTags.length === 0 && !isEditing && (
                    <p className="text-sm text-gray-500">No tags</p>
                  )}
                </div>
                {isEditing && (
                  <div className="flex gap-2">
                    <Input
                      placeholder="Add tag..."
                      value={newTag}
                      onChange={(e) => setNewTag(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                          e.preventDefault();
                          handleAddTag();
                        }
                      }}
                    />
                    <Button onClick={handleAddTag} size="sm">
                      Add
                    </Button>
                  </div>
                )}
              </div>

              {/* Style */}
              {creative.style && (
                <div>
                  <h3 className="text-sm font-medium text-gray-500 mb-2">Style</h3>
                  <Badge variant="outline">{creative.style}</Badge>
                </div>
              )}

              {/* Save Button */}
              {isEditing && (
                <Button
                  onClick={handleSave}
                  disabled={saving}
                  className="w-full"
                >
                  <Save className="w-4 h-4 mr-2" />
                  {saving ? 'Saving...' : 'Save Changes'}
                </Button>
              )}
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}
