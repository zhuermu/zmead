import { toast } from './toast';

/**
 * API Error Handler
 * Handles API errors and displays appropriate toast notifications
 */

interface ApiError {
  message?: string;
  error?: string;
  detail?: string;
  status?: number;
}

/**
 * Handle API error and show toast notification
 */
export function handleApiError(error: unknown, defaultMessage = 'An error occurred') {
  console.error('API Error:', error);

  let errorMessage = defaultMessage;
  let errorTitle = 'Error';

  if (error instanceof Error) {
    errorMessage = error.message;
  } else if (typeof error === 'object' && error !== null) {
    const apiError = error as ApiError;
    
    // Extract error message from various API response formats
    errorMessage = apiError.message || apiError.error || apiError.detail || defaultMessage;
    
    // Set title based on status code
    if (apiError.status) {
      switch (apiError.status) {
        case 400:
          errorTitle = 'Bad Request';
          break;
        case 401:
          errorTitle = 'Unauthorized';
          errorMessage = 'Please log in to continue';
          break;
        case 403:
          errorTitle = 'Forbidden';
          errorMessage = 'You do not have permission to perform this action';
          break;
        case 404:
          errorTitle = 'Not Found';
          break;
        case 429:
          errorTitle = 'Too Many Requests';
          errorMessage = 'Please slow down and try again later';
          break;
        case 500:
          errorTitle = 'Server Error';
          errorMessage = 'An internal server error occurred. Please try again later';
          break;
        case 503:
          errorTitle = 'Service Unavailable';
          errorMessage = 'The service is temporarily unavailable. Please try again later';
          break;
        default:
          errorTitle = `Error ${apiError.status}`;
      }
    }
  }

  toast.error(errorMessage, errorTitle);
}

/**
 * Handle successful API operations
 */
export function handleApiSuccess(message: string, title = 'Success') {
  toast.success(message, title);
}

/**
 * Wrapper for API calls with automatic error handling
 */
export async function withErrorHandling<T>(
  apiCall: () => Promise<T>,
  options?: {
    successMessage?: string;
    errorMessage?: string;
    showSuccessToast?: boolean;
  }
): Promise<T | null> {
  try {
    const result = await apiCall();
    
    if (options?.showSuccessToast && options?.successMessage) {
      handleApiSuccess(options.successMessage);
    }
    
    return result;
  } catch (error) {
    handleApiError(error, options?.errorMessage);
    return null;
  }
}
