'use client';

interface MetricCardProps {
  title: string;
  value: string | number;
  previousValue?: string | number;
  format?: 'currency' | 'number' | 'percentage';
  loading?: boolean;
}

export function MetricCard({ title, value, previousValue, format = 'number', loading = false }: MetricCardProps) {
  const formatValue = (val: string | number): string => {
    const numVal = typeof val === 'string' ? parseFloat(val) : val;
    
    if (isNaN(numVal)) return '0';
    
    switch (format) {
      case 'currency':
        return `$${numVal.toFixed(2)}`;
      case 'percentage':
        return `${numVal.toFixed(2)}%`;
      default:
        return numVal.toFixed(2);
    }
  };

  const calculateChange = (): { percentage: number; isPositive: boolean } | null => {
    if (previousValue === undefined) return null;
    
    const current = typeof value === 'string' ? parseFloat(value) : value;
    const previous = typeof previousValue === 'string' ? parseFloat(previousValue) : previousValue;
    
    if (isNaN(current) || isNaN(previous) || previous === 0) return null;
    
    const percentage = ((current - previous) / previous) * 100;
    const isPositive = percentage >= 0;
    
    return { percentage, isPositive };
  };

  const change = calculateChange();

  if (loading) {
    return (
      <div className="bg-white rounded-xl shadow-sm p-6 animate-pulse">
        <div className="h-4 bg-gray-200 rounded w-1/2 mb-3"></div>
        <div className="h-8 bg-gray-200 rounded w-3/4 mb-2"></div>
        <div className="h-3 bg-gray-200 rounded w-1/3"></div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl shadow-sm p-6 hover:shadow-md transition-shadow">
      <h3 className="text-sm font-medium text-gray-500 mb-1">{title}</h3>
      <p className="text-3xl font-bold text-gray-900 mb-2">
        {formatValue(value)}
      </p>
      {change && (
        <div className="flex items-center gap-1">
          {change.isPositive ? (
            <svg className="w-4 h-4 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
            </svg>
          ) : (
            <svg className="w-4 h-4 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
            </svg>
          )}
          <span className={`text-sm font-medium ${change.isPositive ? 'text-green-600' : 'text-red-600'}`}>
            {Math.abs(change.percentage).toFixed(1)}%
          </span>
          <span className="text-sm text-gray-500">vs yesterday</span>
        </div>
      )}
    </div>
  );
}
