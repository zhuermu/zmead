/**
 * Full-screen image lightbox viewer
 * Features: zoom, download, keyboard shortcuts
 */

'use client';

import { useEffect, useState } from 'react';
import Image from 'next/image';
import { X, ZoomIn, ZoomOut, Download, Maximize2, Minimize2 } from 'lucide-react';

interface ImageLightboxProps {
  imageUrl: string;
  filename: string;
  onClose: () => void;
}

export function ImageLightbox({ imageUrl, filename, onClose }: ImageLightboxProps) {
  const [zoom, setZoom] = useState(100);
  const [isFullscreen, setIsFullscreen] = useState(false);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      } else if (e.key === '=' || e.key === '+') {
        setZoom(prev => Math.min(prev + 25, 200));
      } else if (e.key === '-' || e.key === '_') {
        setZoom(prev => Math.max(prev - 25, 50));
      } else if (e.key === '0') {
        setZoom(100);
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  // Prevent body scroll when lightbox is open
  useEffect(() => {
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = 'unset';
    };
  }, []);

  const handleDownload = async () => {
    try {
      const response = await fetch(imageUrl);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Download failed:', error);
      // Fallback: open in new tab
      window.open(imageUrl, '_blank');
    }
  };

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen();
      setIsFullscreen(false);
    }
  };

  const handleBackdropClick = (e: React.MouseEvent<HTMLDivElement>) => {
    // Only close if clicking the backdrop, not the image
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 bg-black bg-opacity-95 flex items-center justify-center"
      onClick={handleBackdropClick}
    >
      {/* Top toolbar */}
      <div className="absolute top-0 left-0 right-0 p-4 flex items-center justify-between bg-gradient-to-b from-black/50 to-transparent z-10">
        <div className="text-white text-sm truncate max-w-md">
          {filename}
        </div>

        <div className="flex items-center gap-2">
          {/* Zoom controls */}
          <div className="flex items-center gap-1 bg-black/30 rounded-lg px-2 py-1">
            <button
              onClick={() => setZoom(prev => Math.max(prev - 25, 50))}
              className="p-1 hover:bg-white/10 rounded transition-colors"
              title="缩小 (-)"
              disabled={zoom <= 50}
            >
              <ZoomOut className="w-4 h-4 text-white" />
            </button>

            <span className="text-white text-xs font-medium min-w-[45px] text-center">
              {zoom}%
            </span>

            <button
              onClick={() => setZoom(prev => Math.min(prev + 25, 200))}
              className="p-1 hover:bg-white/10 rounded transition-colors"
              title="放大 (+)"
              disabled={zoom >= 200}
            >
              <ZoomIn className="w-4 h-4 text-white" />
            </button>

            <button
              onClick={() => setZoom(100)}
              className="ml-1 px-2 py-1 text-xs text-white hover:bg-white/10 rounded transition-colors"
              title="重置 (0)"
            >
              重置
            </button>
          </div>

          {/* Download button */}
          <button
            onClick={handleDownload}
            className="p-2 hover:bg-white/10 rounded-lg transition-colors"
            title="下载"
          >
            <Download className="w-5 h-5 text-white" />
          </button>

          {/* Fullscreen button */}
          <button
            onClick={toggleFullscreen}
            className="p-2 hover:bg-white/10 rounded-lg transition-colors"
            title={isFullscreen ? "退出全屏" : "全屏"}
          >
            {isFullscreen ? (
              <Minimize2 className="w-5 h-5 text-white" />
            ) : (
              <Maximize2 className="w-5 h-5 text-white" />
            )}
          </button>

          {/* Close button */}
          <button
            onClick={onClose}
            className="p-2 hover:bg-white/10 rounded-lg transition-colors"
            title="关闭 (Esc)"
          >
            <X className="w-5 h-5 text-white" />
          </button>
        </div>
      </div>

      {/* Image container */}
      <div className="relative max-w-[90vw] max-h-[90vh] overflow-auto">
        <div
          style={{
            transform: `scale(${zoom / 100})`,
            transformOrigin: 'center center',
            transition: 'transform 0.2s ease-out',
          }}
        >
          <Image
            src={imageUrl}
            alt={filename}
            width={1200}
            height={800}
            className="object-contain"
            style={{ maxHeight: '85vh', width: 'auto' }}
            priority
          />
        </div>
      </div>

      {/* Bottom help text */}
      <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 bg-black/50 text-white text-xs px-4 py-2 rounded-full">
        ESC 关闭 | + / - 缩放 | 0 重置
      </div>
    </div>
  );
}
