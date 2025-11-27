import { Card } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';

interface FormSkeletonProps {
  fields?: number;
}

/**
 * Form Loading Skeleton
 * Shows placeholder for forms
 */
export function FormSkeleton({ fields = 5 }: FormSkeletonProps) {
  return (
    <Card className="p-6">
      <div className="space-y-6">
        {/* Form Title */}
        <div className="space-y-2">
          <Skeleton className="h-7 w-48" />
          <Skeleton className="h-4 w-96" />
        </div>

        {/* Form Fields */}
        <div className="space-y-4">
          {Array.from({ length: fields }).map((_, i) => (
            <div key={i} className="space-y-2">
              <Skeleton className="h-4 w-32" />
              <Skeleton className="h-10 w-full" />
            </div>
          ))}
        </div>

        {/* Action Buttons */}
        <div className="flex gap-3 pt-4">
          <Skeleton className="h-10 w-24" />
          <Skeleton className="h-10 w-24" />
        </div>
      </div>
    </Card>
  );
}
