"use client";

import { useState, useEffect } from 'react';
import { Creative, PaginatedResponse } from '@/types';
import api from '@/lib/api';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { CreativeCard } from '@/components/creatives/CreativeCard';
import { CreativeFilters } from '@/components/creatives/CreativeFilters';
import { CreativeUpload } from '@/components/creatives/CreativeUpload';
import { CreativeDetailModal } from '@/components/creatives/CreativeDetailModal';
import { BucketSyncModal } from '@/components/creatives/BucketSyncModal';
import { Button } from '@/components/ui/button';
import { Grid3x3, List, Plus, Cloud } from 'lucide-react';

type ViewMode = 'grid' | 'list';

interface FilterState {
  type?: 'image' | 'video';
  status?: 'active' | 'deleted';
  dateFrom?: string;
  dateTo?: string;
  search?: string;
}

// Helper function to convert snake_case to camelCase
const snakeToCamel = (str: string): string =>
  str.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase());

// Convert object keys from snake_case to camelCase
const convertToCamelCase = <T extends Record<string, unknown>>(obj: T): T => {
  if (Array.isArray(obj)) {
    return obj.map(convertToCamelCase) as unknown as T;
  }
  if (obj !== null && typeof obj === 'object') {
    return Object.keys(obj).reduce((result, key) => {
      const camelKey = snakeToCamel(key);
      const value = obj[key];
      (result as Record<string, unknown>)[camelKey] =
        value !== null && typeof value === 'object'
          ? convertToCamelCase(value as Record<string, unknown>)
          : value;
      return result;
    }, {} as T);
  }
  return obj;
};

export default function CreativesPage() {
  const [creatives, setCreatives] = useState<Creative[]>([]);
  const [viewMode, setViewMode] = useState<ViewMode>('grid');
  const [filters, setFilters] = useState<FilterState>({});
  const [page, setPage] = useState(1);
  const [pageSize] = useState(12);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [showUpload, setShowUpload] = useState(false);
  const [showBucketSync, setShowBucketSync] = useState(false);
  const [selectedCreative, setSelectedCreative] = useState<Creative | null>(null);

  useEffect(() => {
    fetchCreatives();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, filters]);

  const fetchCreatives = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString(),
        ...filters,
      });

      const response = await api.get(`/creatives?${params}`);
      // Convert snake_case API response to camelCase for frontend
      const data = convertToCamelCase(response.data) as PaginatedResponse<Creative>;
      setCreatives(data.items);
      setTotal(data.total);
    } catch (error) {
      console.error('Failed to fetch creatives:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleFilterChange = (newFilters: FilterState) => {
    setFilters(newFilters);
    setPage(1); // Reset to first page when filters change
  };

  const handleDelete = async (id: number) => {
    try {
      await api.delete(`/creatives/${id}`);
      fetchCreatives(); // Refresh list
    } catch (error) {
      console.error('Failed to delete creative:', error);
    }
  };

  const handleUploadComplete = () => {
    setShowUpload(false);
    fetchCreatives(); // Refresh list
  };

  const handleSyncComplete = () => {
    setShowBucketSync(false);
    fetchCreatives(); // Refresh list
  };

  const totalPages = Math.ceil(total / pageSize);

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">Creative Library</h1>
            <p className="text-gray-600 mt-1">
              Manage your ad creatives and assets
            </p>
          </div>
          <div className="flex gap-3">
            <Button variant="outline" onClick={() => setShowBucketSync(true)}>
              <Cloud className="w-4 h-4 mr-2" />
              Sync from Cloud
            </Button>
            <Button onClick={() => setShowUpload(true)}>
              <Plus className="w-4 h-4 mr-2" />
              Upload Creative
            </Button>
          </div>
        </div>

        {/* Filters and View Toggle */}
        <div className="flex items-center justify-between gap-4">
          <CreativeFilters
            filters={filters}
            onFilterChange={handleFilterChange}
          />
          <div className="flex gap-2">
            <Button
              variant={viewMode === 'grid' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setViewMode('grid')}
            >
              <Grid3x3 className="w-4 h-4" />
            </Button>
            <Button
              variant={viewMode === 'list' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setViewMode('list')}
            >
              <List className="w-4 h-4" />
            </Button>
          </div>
        </div>

        {/* Loading State */}
        {loading && (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          </div>
        )}

        {/* Empty State */}
        {!loading && creatives.length === 0 && (
          <div className="text-center py-12">
            <p className="text-gray-500 mb-4">No creatives found</p>
            <Button onClick={() => setShowUpload(true)}>
              <Plus className="w-4 h-4 mr-2" />
              Upload Your First Creative
            </Button>
          </div>
        )}

        {/* Creatives Grid/List */}
        {!loading && creatives.length > 0 && (
          <>
            <div
              className={
                viewMode === 'grid'
                  ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6'
                  : 'space-y-4'
              }
            >
              {creatives.map((creative) => (
                <CreativeCard
                  key={creative.id}
                  creative={creative}
                  viewMode={viewMode}
                  onClick={() => setSelectedCreative(creative)}
                  onDelete={() => handleDelete(creative.id)}
                />
              ))}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-center gap-2 mt-8">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page === 1}
                  onClick={() => setPage(page - 1)}
                >
                  Previous
                </Button>
                <span className="text-sm text-gray-600">
                  Page {page} of {totalPages}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page === totalPages}
                  onClick={() => setPage(page + 1)}
                >
                  Next
                </Button>
              </div>
            )}
          </>
        )}
      </div>

      {/* Upload Modal */}
      {showUpload && (
        <CreativeUpload
          onClose={() => setShowUpload(false)}
          onComplete={handleUploadComplete}
        />
      )}

      {/* Bucket Sync Modal */}
      {showBucketSync && (
        <BucketSyncModal
          onClose={() => setShowBucketSync(false)}
          onComplete={handleSyncComplete}
        />
      )}

      {/* Detail Modal */}
      {selectedCreative && (
        <CreativeDetailModal
          creative={selectedCreative}
          onClose={() => setSelectedCreative(null)}
          onUpdate={fetchCreatives}
          onDelete={() => {
            handleDelete(selectedCreative.id);
            setSelectedCreative(null);
          }}
        />
      )}
    </DashboardLayout>
  );
}
