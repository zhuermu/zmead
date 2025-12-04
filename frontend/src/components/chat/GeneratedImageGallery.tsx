'use client';

import { useState } from 'react';
import { Download, X, ChevronLeft, ChevronRight, ZoomIn, Image as ImageIcon } from 'lucide-react';

// Support GCS storage, API format, and legacy format
export interface GeneratedImage {
  // API format (from generate_image_tool)
  index?: number;
  format?: string;
  size?: number;
  // GCS storage (preferred) - frontend fetches signed URL
  object_name?: string;
  bucket?: string;
  gcs_url?: string;
  signed_url?: string;  // Resolved signed URL for display
  // Fallback base64 (only if GCS upload fails)
  data_b64?: string;
  // Legacy format
  imageData?: string;
  mimeType?: string;
  prompt?: string;
}

interface GeneratedImageGalleryProps {
  images: GeneratedImage[];
  onSave?: (images: GeneratedImage[]) => void;
}

export function GeneratedImageGallery({ images, onSave }: GeneratedImageGalleryProps) {
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);

  if (!images || images.length === 0) return null;

  const handleDownload = async (image: GeneratedImage, index: number) => {
    const format = image.format || image.mimeType?.split('/')[1] || 'png';
    const mimeType = image.mimeType || `image/${format}`;

    // Priority: signed_url > data_b64 > imageData
    if (image.signed_url) {
      // For signed URLs, fetch and download
      try {
        const response = await fetch(image.signed_url);
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `generated-image-${index + 1}.${format}`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
      } catch (err) {
        console.error('Download failed:', err);
        // Fallback: open in new tab
        window.open(image.signed_url, '_blank');
      }
      return;
    }

    // Get image data from either format
    const imageData = image.data_b64 || image.imageData || '';

    // Handle URL format
    if (imageData.startsWith('http')) {
      window.open(imageData, '_blank');
      return;
    }

    // For base64 data, create download link
    const link = document.createElement('a');
    const isDataUrl = imageData.startsWith('data:');
    link.href = isDataUrl ? imageData : `data:${mimeType};base64,${imageData}`;
    link.download = `generated-image-${index + 1}.${format}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const getImageSrc = (image: GeneratedImage) => {
    // Priority: signed_url > data_b64 > imageData (legacy)
    // GCS signed URLs are preferred for performance and cost savings
    if (image.signed_url) {
      return image.signed_url;
    }

    const imageData = image.data_b64 || image.imageData || '';
    const format = image.format || 'png';
    const mimeType = image.mimeType || `image/${format}`;

    if (imageData.startsWith('data:') || imageData.startsWith('http')) {
      return imageData;
    }
    if (imageData) {
      return `data:${mimeType};base64,${imageData}`;
    }

    // If we have object_name but no signed_url yet, show placeholder
    if (image.object_name) {
      return ''; // Will show loading state
    }

    return '';
  };

  // Check if image is still loading (has object_name but no signed_url)
  const isImageLoading = (image: GeneratedImage) => {
    return image.object_name && !image.signed_url && !image.data_b64;
  };

  return (
    <div className="my-3">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <ImageIcon className="w-4 h-4 text-indigo-500" />
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
            已生成 {images.length} 张图片
          </span>
        </div>
        {onSave && (
          <button
            onClick={() => onSave(images)}
            className="text-sm text-indigo-600 hover:text-indigo-800 dark:text-indigo-400 dark:hover:text-indigo-300 font-medium"
          >
            保存到素材库
          </button>
        )}
      </div>

      {/* Image Grid */}
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">
        {images.map((image, index) => (
          <div
            key={index}
            className="relative group cursor-pointer rounded-lg overflow-hidden bg-gray-100 dark:bg-gray-800 aspect-square shadow-sm hover:shadow-md transition-shadow"
            onClick={() => !isImageLoading(image) && setSelectedIndex(index)}
          >
            {isImageLoading(image) ? (
              // Loading state for GCS images
              <div className="w-full h-full flex items-center justify-center">
                <div className="animate-pulse flex flex-col items-center gap-2">
                  <ImageIcon className="w-8 h-8 text-gray-400" />
                  <span className="text-xs text-gray-500">加载中...</span>
                </div>
              </div>
            ) : (
              <img
                src={getImageSrc(image)}
                alt={`Generated image ${index + 1}`}
                className="w-full h-full object-cover"
              />
            )}
            {!isImageLoading(image) && (
              <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDownload(image, index);
                  }}
                  className="p-2 bg-white/90 rounded-full hover:bg-white transition-colors"
                  title="下载"
                >
                  <Download className="w-5 h-5 text-gray-700" />
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setSelectedIndex(index);
                  }}
                  className="p-2 bg-white/90 rounded-full hover:bg-white transition-colors"
                  title="预览"
                >
                  <ZoomIn className="w-5 h-5 text-gray-700" />
                </button>
              </div>
            )}
            <div className="absolute bottom-1 right-1 bg-black/70 text-white text-xs px-1.5 py-0.5 rounded">
              {index + 1}
            </div>
          </div>
        ))}
      </div>

      {/* Lightbox Modal */}
      {selectedIndex !== null && (
        <div
          className="fixed inset-0 z-50 bg-black/90 flex items-center justify-center p-4"
          onClick={() => setSelectedIndex(null)}
        >
          <button
            onClick={() => setSelectedIndex(null)}
            className="absolute top-4 right-4 text-white hover:text-gray-300 p-2 rounded-full hover:bg-white/10 transition-colors"
          >
            <X className="w-8 h-8" />
          </button>

          {/* Navigation */}
          {images.length > 1 && (
            <>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setSelectedIndex((prev) => (prev === 0 ? images.length - 1 : (prev || 0) - 1));
                }}
                className="absolute left-4 text-white hover:text-gray-300 p-2 rounded-full hover:bg-white/10 transition-colors"
              >
                <ChevronLeft className="w-10 h-10" />
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setSelectedIndex((prev) => ((prev || 0) + 1) % images.length);
                }}
                className="absolute right-4 text-white hover:text-gray-300 p-2 rounded-full hover:bg-white/10 transition-colors"
              >
                <ChevronRight className="w-10 h-10" />
              </button>
            </>
          )}

          <img
            src={getImageSrc(images[selectedIndex])}
            alt={`Generated image ${selectedIndex + 1}`}
            className="max-w-full max-h-[90vh] object-contain rounded-lg"
            onClick={(e) => e.stopPropagation()}
          />

          {/* Image counter */}
          <div className="absolute bottom-4 left-1/2 -translate-x-1/2 text-white bg-black/50 px-3 py-1 rounded-full text-sm">
            {selectedIndex + 1} / {images.length}
          </div>

          {/* Download button */}
          <button
            onClick={(e) => {
              e.stopPropagation();
              handleDownload(images[selectedIndex], selectedIndex);
            }}
            className="absolute bottom-4 right-4 bg-white/90 hover:bg-white text-gray-800 px-4 py-2 rounded-lg flex items-center gap-2 transition-colors"
          >
            <Download className="w-5 h-5" />
            下载
          </button>
        </div>
      )}
    </div>
  );
}
