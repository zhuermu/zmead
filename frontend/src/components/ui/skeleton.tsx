import { cn } from "@/lib/utils";

/**
 * Skeleton Component
 * Displays a loading placeholder with shimmer animation
 */
function Skeleton({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "animate-pulse rounded-md bg-gray-200",
        className
      )}
      {...props}
    />
  );
}

export { Skeleton };
