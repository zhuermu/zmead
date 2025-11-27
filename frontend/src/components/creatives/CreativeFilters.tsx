import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Filter, X } from 'lucide-react';

interface FilterState {
  type?: 'image' | 'video';
  status?: 'active' | 'deleted';
  dateFrom?: string;
  dateTo?: string;
  search?: string;
}

interface CreativeFiltersProps {
  filters: FilterState;
  onFilterChange: (filters: FilterState) => void;
}

export function CreativeFilters({ filters, onFilterChange }: CreativeFiltersProps) {
  const [localFilters, setLocalFilters] = useState<FilterState>(filters);
  const [showFilters, setShowFilters] = useState(false);

  const handleApply = () => {
    onFilterChange(localFilters);
  };

  const handleClear = () => {
    const emptyFilters: FilterState = {};
    setLocalFilters(emptyFilters);
    onFilterChange(emptyFilters);
  };

  const hasActiveFilters = Object.keys(filters).length > 0;

  return (
    <div className="flex-1">
      <div className="flex items-center gap-2">
        {/* Search */}
        <Input
          placeholder="Search creatives..."
          value={localFilters.search || ''}
          onChange={(e) => setLocalFilters({ ...localFilters, search: e.target.value })}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              handleApply();
            }
          }}
          className="max-w-xs"
        />

        {/* Filter Toggle */}
        <Button
          variant={showFilters ? 'default' : 'outline'}
          size="sm"
          onClick={() => setShowFilters(!showFilters)}
        >
          <Filter className="w-4 h-4 mr-2" />
          Filters
          {hasActiveFilters && (
            <span className="ml-2 bg-blue-600 text-white rounded-full w-5 h-5 flex items-center justify-center text-xs">
              {Object.keys(filters).length}
            </span>
          )}
        </Button>

        {hasActiveFilters && (
          <Button variant="ghost" size="sm" onClick={handleClear}>
            <X className="w-4 h-4 mr-2" />
            Clear
          </Button>
        )}
      </div>

      {/* Filter Panel */}
      {showFilters && (
        <div className="mt-4 p-4 bg-gray-50 rounded-lg space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {/* Type Filter */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Type
              </label>
              <Select
                value={localFilters.type || 'all'}
                onValueChange={(value) =>
                  setLocalFilters({
                    ...localFilters,
                    type: value === 'all' ? undefined : (value as 'image' | 'video'),
                  })
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="All types" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All types</SelectItem>
                  <SelectItem value="image">Image</SelectItem>
                  <SelectItem value="video">Video</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Status Filter */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Status
              </label>
              <Select
                value={localFilters.status || 'all'}
                onValueChange={(value) =>
                  setLocalFilters({
                    ...localFilters,
                    status: value === 'all' ? undefined : (value as 'active' | 'deleted'),
                  })
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="All statuses" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All statuses</SelectItem>
                  <SelectItem value="active">Active</SelectItem>
                  <SelectItem value="deleted">Deleted</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Date From */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                From Date
              </label>
              <Input
                type="date"
                value={localFilters.dateFrom || ''}
                onChange={(e) =>
                  setLocalFilters({ ...localFilters, dateFrom: e.target.value })
                }
              />
            </div>

            {/* Date To */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                To Date
              </label>
              <Input
                type="date"
                value={localFilters.dateTo || ''}
                onChange={(e) =>
                  setLocalFilters({ ...localFilters, dateTo: e.target.value })
                }
              />
            </div>
          </div>

          {/* Apply Button */}
          <div className="flex justify-end">
            <Button onClick={handleApply}>Apply Filters</Button>
          </div>
        </div>
      )}
    </div>
  );
}
