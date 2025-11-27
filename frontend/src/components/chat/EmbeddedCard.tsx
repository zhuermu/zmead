'use client';

interface EmbeddedCardProps {
  title: string;
  data: Record<string, any>;
  type?: 'metric' | 'info' | 'warning' | 'success';
}

export function EmbeddedCard({ title, data, type = 'info' }: EmbeddedCardProps) {
  const typeStyles = {
    metric: 'bg-gradient-to-br from-purple-50 to-blue-50 border-purple-200',
    info: 'bg-blue-50 border-blue-200',
    warning: 'bg-yellow-50 border-yellow-200',
    success: 'bg-green-50 border-green-200',
  };

  const iconStyles = {
    metric: 'text-purple-600',
    info: 'text-blue-600',
    warning: 'text-yellow-600',
    success: 'text-green-600',
  };

  return (
    <div className={`my-3 p-4 border rounded-lg ${typeStyles[type]}`}>
      <div className="flex items-start gap-3">
        <div className={`flex-shrink-0 ${iconStyles[type]}`}>
          {type === 'metric' && (
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          )}
          {type === 'info' && (
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          )}
          {type === 'warning' && (
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          )}
          {type === 'success' && (
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          )}
        </div>
        
        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-semibold text-gray-900 mb-2">{title}</h4>
          
          <div className="space-y-1.5">
            {Object.entries(data).map(([key, value]) => (
              <div key={key} className="flex justify-between items-center text-xs">
                <span className="text-gray-600">{key}:</span>
                <span className="font-medium text-gray-900">{String(value)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
