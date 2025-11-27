import { Card } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';

interface CardGridSkeletonProps {
  count?: number;
  columns?: 2 | 3 | 4;
}

/**
 * Card Grid Loading Skeleton
 * Shows placeholder for card grids (creatives, campaigns, etc.)
 */
export function CardGridSkeleton({ count = 6, columns = 3 }: CardGridSkeletonProps) {
  const gridCols = {
    2: 'grid-cols-1 md:grid-cols-2',
    3: 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3',
    4: 'grid-cols-1 md:grid-cols-2 lg:grid-cols-4',
  };

  return (
    <div className={`grid ${gridCols[columns]} gap-6`}>
      {Array.from({ length: count }).map((_, i) => (
        <Card key={i} className="overflow-hidden">
          {/* Image placeholder */}
          <Skeleton className="h-48 w-full rounded-t-lg" />
          
          {/* Content */}
          <div className="p-4 space-y-3">
            <Skeleton className="h-5 w-3/4" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-5/6" />
            
            {/* Footer */}
            <div className="flex gap-2 pt-2">
              <Skeleton className="h-6 w-16" />
              <Skeleton className="h-6 w-16" />
            </div>
          </div>
        </Card>
      ))}
    </div>
  );
}
