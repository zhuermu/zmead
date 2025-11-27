'use client';

import React, { Component, ErrorInfo, ReactNode } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { AlertTriangle } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

/**
 * Global Error Boundary Component
 * Catches and displays React errors gracefully
 * Provides reload button and logs errors to monitoring service
 */
export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): State {
    // Update state so the next render will show the fallback UI
    return {
      hasError: true,
      error,
      errorInfo: null,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log error to monitoring service (e.g., Sentry, CloudWatch)
    this.logErrorToService(error, errorInfo);

    // Update state with error details
    this.setState({
      error,
      errorInfo,
    });
  }

  logErrorToService(error: Error, errorInfo: ErrorInfo) {
    // Log to console in development
    if (process.env.NODE_ENV === 'development') {
      console.error('Error Boundary caught an error:', error);
      console.error('Error Info:', errorInfo);
    }

    // In production, send to monitoring service
    // Example: Sentry.captureException(error, { extra: errorInfo });
    // Example: CloudWatch Logs
    try {
      // Send to backend logging endpoint
      fetch('/api/v1/logs/error', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          error: {
            message: error.message,
            stack: error.stack,
            name: error.name,
          },
          errorInfo: {
            componentStack: errorInfo.componentStack,
          },
          timestamp: new Date().toISOString(),
          userAgent: navigator.userAgent,
          url: window.location.href,
        }),
      }).catch((err) => {
        // Silently fail if logging fails
        console.error('Failed to log error:', err);
      });
    } catch (loggingError) {
      // Prevent logging errors from breaking the app
      console.error('Error while logging:', loggingError);
    }
  }

  handleReload = () => {
    // Reset error state and reload the page
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
    window.location.reload();
  };

  handleReset = () => {
    // Reset error state without reloading
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
  };

  render() {
    if (this.state.hasError) {
      // Custom fallback UI
      if (this.props.fallback) {
        return this.props.fallback;
      }

      // Default error UI
      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
          <Card className="max-w-2xl w-full p-8">
            <div className="flex flex-col items-center text-center space-y-6">
              {/* Error Icon */}
              <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center">
                <AlertTriangle className="w-8 h-8 text-red-600" />
              </div>

              {/* Error Title */}
              <div>
                <h1 className="text-2xl font-bold text-gray-900 mb-2">
                  Oops! Something went wrong
                </h1>
                <p className="text-gray-600">
                  We're sorry for the inconvenience. An unexpected error has occurred.
                </p>
              </div>

              {/* Error Details (only in development) */}
              {process.env.NODE_ENV === 'development' && this.state.error && (
                <div className="w-full bg-gray-100 rounded-lg p-4 text-left">
                  <p className="text-sm font-semibold text-gray-700 mb-2">
                    Error Details:
                  </p>
                  <p className="text-xs text-red-600 font-mono mb-2">
                    {this.state.error.message}
                  </p>
                  {this.state.error.stack && (
                    <pre className="text-xs text-gray-600 overflow-x-auto whitespace-pre-wrap">
                      {this.state.error.stack}
                    </pre>
                  )}
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex gap-4">
                <Button onClick={this.handleReload} size="lg">
                  Reload Page
                </Button>
                <Button onClick={this.handleReset} variant="outline" size="lg">
                  Try Again
                </Button>
              </div>

              {/* Help Text */}
              <p className="text-sm text-gray-500">
                If the problem persists, please contact support at{' '}
                <a
                  href="mailto:support@aae.com"
                  className="text-blue-600 hover:underline"
                >
                  support@aae.com
                </a>
              </p>
            </div>
          </Card>
        </div>
      );
    }

    return this.props.children;
  }
}
