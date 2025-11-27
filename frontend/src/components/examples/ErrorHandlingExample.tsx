'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { toast } from '@/lib/toast';
import { LoadingSpinner, ProgressBar } from '@/components/loading';
import { handleApiError, handleApiSuccess } from '@/lib/api-error-handler';

/**
 * Example Component demonstrating error handling and loading states
 * This is for demonstration purposes only
 */
export function ErrorHandlingExample() {
  const [isLoading, setIsLoading] = useState(false);
  const [progress, setProgress] = useState(0);

  const simulateSuccess = () => {
    toast.success('Operation completed successfully!', 'Success');
  };

  const simulateError = () => {
    toast.error('Something went wrong. Please try again.', 'Error');
  };

  const simulateWarning = () => {
    toast.warning('This action may have unintended consequences.', 'Warning');
  };

  const simulateInfo = () => {
    toast.info('This is an informational message.', 'Info');
  };

  const simulateApiError = () => {
    handleApiError({
      message: 'Failed to fetch data from the server',
      status: 500,
    });
  };

  const simulateApiSuccess = () => {
    handleApiSuccess('Data saved successfully');
  };

  const simulateLoading = () => {
    setIsLoading(true);
    setProgress(0);

    const interval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 100) {
          clearInterval(interval);
          setIsLoading(false);
          toast.success('Loading complete!');
          return 100;
        }
        return prev + 10;
      });
    }, 500);
  };

  const throwError = () => {
    // This will be caught by the ErrorBoundary
    throw new Error('This is a test error to demonstrate ErrorBoundary');
  };

  return (
    <div className="space-y-6 p-6">
      <Card className="p-6">
        <h2 className="text-2xl font-bold mb-4">Toast Notifications</h2>
        <div className="grid grid-cols-2 gap-4">
          <Button onClick={simulateSuccess} variant="default">
            Show Success Toast
          </Button>
          <Button onClick={simulateError} variant="destructive">
            Show Error Toast
          </Button>
          <Button onClick={simulateWarning} variant="outline">
            Show Warning Toast
          </Button>
          <Button onClick={simulateInfo} variant="outline">
            Show Info Toast
          </Button>
        </div>
      </Card>

      <Card className="p-6">
        <h2 className="text-2xl font-bold mb-4">API Error Handling</h2>
        <div className="grid grid-cols-2 gap-4">
          <Button onClick={simulateApiError} variant="destructive">
            Simulate API Error
          </Button>
          <Button onClick={simulateApiSuccess} variant="default">
            Simulate API Success
          </Button>
        </div>
      </Card>

      <Card className="p-6">
        <h2 className="text-2xl font-bold mb-4">Loading States</h2>
        <div className="space-y-4">
          <Button onClick={simulateLoading} disabled={isLoading}>
            {isLoading ? (
              <LoadingSpinner size="sm" text="Loading..." />
            ) : (
              'Start Loading'
            )}
          </Button>

          {isLoading && (
            <ProgressBar progress={progress} showLabel size="md" />
          )}
        </div>
      </Card>

      <Card className="p-6">
        <h2 className="text-2xl font-bold mb-4">Error Boundary</h2>
        <p className="text-gray-600 mb-4">
          Click the button below to throw an error that will be caught by the
          global ErrorBoundary component.
        </p>
        <Button onClick={throwError} variant="destructive">
          Throw Error (Test ErrorBoundary)
        </Button>
      </Card>
    </div>
  );
}
