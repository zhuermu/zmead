import { Creative } from '@/types';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Trash2, Star, Image as ImageIcon, Video } from 'lucide-react';
import Image from 'next/image';

interface CreativeCardProps {
  creative: Creative;
  viewMode: 'grid' | 'list';
  onClick: () => void;
  onDelete: () => void;
}

export function CreativeCard({ creative, viewMode, onClick, onDelete }: CreativeCardProps) {
  // Use signed URL for secure access, fallback to cdnUrl
  const imageUrl = creative.signedUrl || creative.cdnUrl;

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  if (viewMode === 'list') {
    return (
      <Card className="p-4 hover:shadow-md transition-shadow cursor-pointer">
        <div className="flex items-center gap-4">
          {/* Thumbnail */}
          <div
            className="relative w-24 h-24 bg-gray-100 rounded-lg overflow-hidden flex-shrink-0"
            onClick={onClick}
          >
            {creative.fileType === 'image' ? (
              <Image
                src={imageUrl}
                alt="Creative"
                fill
                className="object-cover"
                unoptimized
              />
            ) : (
              <div className="flex items-center justify-center h-full">
                <Video className="w-8 h-8 text-gray-400" />
              </div>
            )}
          </div>

          {/* Info */}
          <div className="flex-1 min-w-0" onClick={onClick}>
            <div className="flex items-center gap-2 mb-1">
              <Badge variant={creative.fileType === 'image' ? 'default' : 'secondary'}>
                {creative.fileType}
              </Badge>
              {creative.score && (
                <div className="flex items-center gap-1 text-sm text-yellow-600">
                  <Star className="w-4 h-4 fill-current" />
                  <span>{creative.score.toFixed(1)}</span>
                </div>
              )}
            </div>
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <span>{formatFileSize(creative.fileSize)}</span>
              <span>•</span>
              <span>{formatDate(creative.createdAt)}</span>
            </div>
            {creative.tags.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-2">
                {creative.tags.map((tag, index) => (
                  <Badge key={index} variant="outline" className="text-xs">
                    {tag}
                  </Badge>
                ))}
              </div>
            )}
          </div>

          {/* Actions */}
          <Button
            variant="ghost"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              onDelete();
            }}
          >
            <Trash2 className="w-4 h-4 text-red-500" />
          </Button>
        </div>
      </Card>
    );
  }

  // Grid view
  return (
    <Card className="overflow-hidden hover:shadow-lg transition-shadow cursor-pointer">
      {/* Thumbnail */}
      <div
        className="relative w-full aspect-square bg-gray-100"
        onClick={onClick}
      >
        {creative.fileType === 'image' ? (
          <Image
            src={imageUrl}
            alt="Creative"
            fill
            className="object-cover"
            unoptimized
          />
        ) : (
          <div className="flex items-center justify-center h-full">
            <Video className="w-12 h-12 text-gray-400" />
          </div>
        )}

        {/* Type Badge */}
        <div className="absolute top-2 left-2">
          <Badge variant={creative.fileType === 'image' ? 'default' : 'secondary'}>
            {creative.fileType === 'image' ? (
              <ImageIcon className="w-3 h-3 mr-1" />
            ) : (
              <Video className="w-3 h-3 mr-1" />
            )}
            {creative.fileType}
          </Badge>
        </div>

        {/* Score Badge */}
        {creative.score && (
          <div className="absolute top-2 right-2">
            <Badge className="bg-yellow-500 text-white">
              <Star className="w-3 h-3 mr-1 fill-current" />
              {creative.score.toFixed(1)}
            </Badge>
          </div>
        )}
      </div>

      {/* Info */}
      <div className="p-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-gray-600">
            {formatFileSize(creative.fileSize)}
          </span>
          <Button
            variant="ghost"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              onDelete();
            }}
          >
            <Trash2 className="w-4 h-4 text-red-500" />
          </Button>
        </div>

        {/* Tags */}
        {creative.tags.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-2">
            {creative.tags.slice(0, 3).map((tag, index) => (
              <Badge key={index} variant="outline" className="text-xs">
                {tag}
              </Badge>
            ))}
            {creative.tags.length > 3 && (
              <Badge variant="outline" className="text-xs">
                +{creative.tags.length - 3}
              </Badge>
            )}
          </div>
        )}

        <p className="text-xs text-gray-500">{formatDate(creative.createdAt)}</p>
      </div>
    </Card>
  );
}
