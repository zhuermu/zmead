import { Card } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';

interface TableSkeletonProps {
  rows?: number;
  columns?: number;
}

/**
 * Table Loading Skeleton
 * Shows placeholder for data tables
 */
export function TableSkeleton({ rows = 5, columns = 5 }: TableSkeletonProps) {
  return (
    <Card className="overflow-hidden">
      {/* Table Header */}
      <div className="border-b bg-gray-50 p-4">
        <div className="flex gap-4">
          {Array.from({ length: columns }).map((_, i) => (
            <Skeleton key={i} className="h-4 flex-1" />
          ))}
        </div>
      </div>

      {/* Table Rows */}
      <div className="divide-y">
        {Array.from({ length: rows }).map((_, rowIndex) => (
          <div key={rowIndex} className="p-4">
            <div className="flex gap-4">
              {Array.from({ length: columns }).map((_, colIndex) => (
                <Skeleton key={colIndex} className="h-4 flex-1" />
              ))}
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
