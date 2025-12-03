'use client';

import { useState } from 'react';

// Local type definition for generated images
interface GeneratedImage {
  imageData: string;
  mimeType: string;
  prompt?: string;
}

interface GeneratedImageGalleryProps {
  images: GeneratedImage[];
  onSave?: (images: GeneratedImage[]) => void;
}

export function GeneratedImageGallery({ images, onSave }: GeneratedImageGalleryProps) {
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);

  if (images.length === 0) return null;

  const handleDownload = (image: GeneratedImage, index: number) => {
    // Handle both URL and base64 image data
    const isDataUrl = image.imageData.startsWith('data:');
    const isUrl = image.imageData.startsWith('http');

    if (isUrl) {
      window.open(image.imageData, '_blank');
      return;
    }

    // For base64 data, create download link
    const link = document.createElement('a');
    link.href = isDataUrl ? image.imageData : `data:${image.mimeType};base64,${image.imageData}`;
    link.download = `generated-image-${index + 1}.${image.mimeType.split('/')[1] || 'png'}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const getImageSrc = (image: GeneratedImage) => {
    if (image.imageData.startsWith('data:') || image.imageData.startsWith('http')) {
      return image.imageData;
    }
    return `data:${image.mimeType};base64,${image.imageData}`;
  };

  return (
    <div className="my-4">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-gray-700">
          {images.length} image(s) generated
        </span>
        {onSave && (
          <button
            onClick={() => onSave(images)}
            className="text-sm text-purple-600 hover:text-purple-800 font-medium"
          >
            Save to library
          </button>
        )}
      </div>

      {/* Image Grid */}
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {images.map((image, index) => (
          <div
            key={index}
            className="relative group cursor-pointer rounded-lg overflow-hidden bg-gray-100 aspect-square"
            onClick={() => setSelectedIndex(index)}
          >
            <img
              src={getImageSrc(image)}
              alt={`Generated image ${index + 1}`}
              className="w-full h-full object-cover"
            />
            <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleDownload(image, index);
                }}
                className="p-2 bg-white/90 rounded-full hover:bg-white"
                title="Download"
              >
                <svg className="w-5 h-5 text-gray-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setSelectedIndex(index);
                }}
                className="p-2 bg-white/90 rounded-full hover:bg-white"
                title="Preview"
              >
                <svg className="w-5 h-5 text-gray-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v3m0 0v3m0-3h3m-3 0H7" />
                </svg>
              </button>
            </div>
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
            className="absolute top-4 right-4 text-white hover:text-gray-300"
          >
            <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>

          {/* Navigation */}
          {images.length > 1 && (
            <>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setSelectedIndex((prev) => (prev === 0 ? images.length - 1 : (prev || 0) - 1));
                }}
                className="absolute left-4 text-white hover:text-gray-300"
              >
                <svg className="w-10 h-10" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setSelectedIndex((prev) => ((prev || 0) + 1) % images.length);
                }}
                className="absolute right-4 text-white hover:text-gray-300"
              >
                <svg className="w-10 h-10" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </button>
            </>
          )}

          <img
            src={getImageSrc(images[selectedIndex])}
            alt={`Generated image ${selectedIndex + 1}`}
            className="max-w-full max-h-[90vh] object-contain"
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
            className="absolute bottom-4 right-4 bg-white/90 hover:bg-white text-gray-800 px-4 py-2 rounded-lg flex items-center gap-2"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            Download
          </button>
        </div>
      )}
    </div>
  );
}
