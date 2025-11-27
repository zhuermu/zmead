# Error Handling and Loading States Guide

This guide documents the error handling and loading state implementation for the AAE Web Platform.

## Overview

The application implements a comprehensive error handling and loading state system with three main components:

1. **Global Error Boundary** - Catches and displays React errors gracefully
2. **Loading Skeletons** - Provides visual feedback during data loading
3. **Toast Notifications** - Displays API errors and success messages

## 1. Global Error Boundary

### Location
- `frontend/src/components/error/ErrorBoundary.tsx`

### Features
- Catches all React errors in the component tree
- Displays user-friendly error message
- Provides "Reload" and "Try Again" buttons
- Logs errors to monitoring service
- Shows detailed error info in development mode

### Usage

The ErrorBoundary is already wrapped around the entire application in `app/layout.tsx`:

```tsx
<ErrorBoundary>
  <AuthProvider>
    {children}
  </AuthProvider>
</ErrorBoundary>
```

You can also use it for specific components:

```tsx
import { ErrorBoundary } from '@/components/error';

<ErrorBoundary fallback={<CustomErrorUI />}>
  <YourComponent />
</ErrorBoundary>
```

### Error Logging

Errors are automatically logged to:
- Console (development mode)
- Backend logging endpoint: `POST /api/v1/logs/error`

The error log includes:
- Error message and stack trace
- Component stack
- Timestamp
- User agent
- Current URL

## 2. Loading Skeletons

### Components

#### Skeleton (Base Component)
```tsx
import { Skeleton } from '@/components/ui/skeleton';

<Skeleton className="h-4 w-32" />
```

#### DashboardSkeleton
Shows placeholder for dashboard metrics and charts.

```tsx
import { DashboardSkeleton } from '@/components/loading';

{isLoading ? <DashboardSkeleton /> : <Dashboard data={data} />}
```

#### TableSkeleton
Shows placeholder for data tables.

```tsx
import { TableSkeleton } from '@/components/loading';

{isLoading ? (
  <TableSkeleton rows={10} columns={5} />
) : (
  <DataTable data={data} />
)}
```

#### CardGridSkeleton
Shows placeholder for card grids (creatives, campaigns, etc.).

```tsx
import { CardGridSkeleton } from '@/components/loading';

{isLoading ? (
  <CardGridSkeleton count={6} columns={3} />
) : (
  <CardGrid items={items} />
)}
```

#### FormSkeleton
Shows placeholder for forms.

```tsx
import { FormSkeleton } from '@/components/loading';

{isLoading ? <FormSkeleton fields={5} /> : <Form />}
```

#### LoadingSpinner
Shows a spinning loader icon with optional text.

```tsx
import { LoadingSpinner } from '@/components/loading';

<LoadingSpinner size="md" text="Loading..." />

// In buttons
<Button disabled={isLoading}>
  {isLoading ? <LoadingSpinner size="sm" /> : 'Submit'}
</Button>
```

#### ProgressBar
Shows progress indicator for long operations.

```tsx
import { ProgressBar } from '@/components/loading';

<ProgressBar 
  progress={uploadProgress} 
  showLabel 
  size="md" 
/>
```

## 3. Toast Notifications

### Location
- `frontend/src/lib/toast.ts` - Toast store and helper functions
- `frontend/src/components/toast/` - Toast UI components

### Features
- Auto-dismiss after 5 seconds (configurable)
- Four types: success, error, warning, info
- Stacked display in top-right corner
- Smooth animations
- Manual dismiss option

### Usage

#### Basic Toast

```tsx
import { toast } from '@/lib/toast';

// Success
toast.success('Operation completed successfully!');
toast.success('Data saved', 'Success', 3000); // Custom duration

// Error
toast.error('Something went wrong');
toast.error('Failed to save data', 'Error');

// Warning
toast.warning('This action cannot be undone');

// Info
toast.info('New features available');
```

#### API Error Handling

The application includes automatic API error handling:

```tsx
import { handleApiError, handleApiSuccess } from '@/lib/api-error-handler';

try {
  const response = await api.post('/campaigns', data);
  handleApiSuccess('Campaign created successfully');
} catch (error) {
  handleApiError(error, 'Failed to create campaign');
}
```

#### Wrapper for API Calls

```tsx
import { withErrorHandling } from '@/lib/api-error-handler';

const result = await withErrorHandling(
  () => api.post('/campaigns', data),
  {
    successMessage: 'Campaign created successfully',
    errorMessage: 'Failed to create campaign',
    showSuccessToast: true,
  }
);
```

#### Automatic Error Handling

The axios interceptor automatically shows toast notifications for API errors:

```tsx
// This will automatically show an error toast if the request fails
const response = await api.get('/campaigns');
```

## Best Practices

### 1. Loading States

Always show loading feedback for async operations:

```tsx
const [isLoading, setIsLoading] = useState(false);

const fetchData = async () => {
  setIsLoading(true);
  try {
    const response = await api.get('/data');
    setData(response.data);
  } catch (error) {
    // Error is automatically handled by interceptor
  } finally {
    setIsLoading(false);
  }
};

return isLoading ? <TableSkeleton /> : <DataTable data={data} />;
```

### 2. Error Handling

Use try-catch for operations that need custom error handling:

```tsx
const handleSubmit = async () => {
  try {
    await api.post('/campaigns', formData);
    toast.success('Campaign created successfully');
    router.push('/campaigns');
  } catch (error) {
    // Custom error handling if needed
    handleApiError(error, 'Failed to create campaign');
  }
};
```

### 3. Form Validation

Show validation errors using toast:

```tsx
const validateForm = () => {
  if (!formData.name) {
    toast.error('Campaign name is required', 'Validation Error');
    return false;
  }
  return true;
};
```

### 4. Long Operations

Use progress bar for operations with progress tracking:

```tsx
const [progress, setProgress] = useState(0);

const uploadFile = async (file: File) => {
  const formData = new FormData();
  formData.append('file', file);

  await api.post('/upload', formData, {
    onUploadProgress: (progressEvent) => {
      const percentCompleted = Math.round(
        (progressEvent.loaded * 100) / progressEvent.total
      );
      setProgress(percentCompleted);
    },
  });
};

return <ProgressBar progress={progress} showLabel />;
```

## Testing

### Test Error Boundary

```tsx
// Throw an error to test ErrorBoundary
const TestComponent = () => {
  throw new Error('Test error');
};
```

### Test Toast Notifications

```tsx
import { toast } from '@/lib/toast';

// Test all toast types
toast.success('Success message');
toast.error('Error message');
toast.warning('Warning message');
toast.info('Info message');
```

### Test Loading States

```tsx
// Simulate loading
const [isLoading, setIsLoading] = useState(true);

useEffect(() => {
  setTimeout(() => setIsLoading(false), 2000);
}, []);

return isLoading ? <DashboardSkeleton /> : <Dashboard />;
```

## Accessibility

All components follow accessibility best practices:

- **Error Boundary**: Provides clear error messages and recovery options
- **Loading Skeletons**: Use semantic HTML and proper ARIA attributes
- **Toast Notifications**: 
  - Use `role="alert"` for screen readers
  - Support keyboard navigation
  - Auto-dismiss with sufficient time to read
  - Manual dismiss option available

## Configuration

### Toast Duration

Default duration is 5000ms (5 seconds). You can customize per toast:

```tsx
toast.success('Message', 'Title', 10000); // 10 seconds
```

### Error Logging Endpoint

Configure the error logging endpoint in `ErrorBoundary.tsx`:

```tsx
fetch('/api/v1/logs/error', {
  method: 'POST',
  body: JSON.stringify(errorData),
});
```

## Future Enhancements

Potential improvements for future versions:

1. **Sentry Integration**: Add Sentry for production error tracking
2. **Toast Queue**: Limit number of simultaneous toasts
3. **Toast Actions**: Add action buttons to toasts
4. **Offline Detection**: Show toast when connection is lost
5. **Retry Logic**: Automatic retry for failed requests
6. **Loading Priorities**: Different skeleton styles for critical vs non-critical content

## Related Files

- `frontend/src/components/error/ErrorBoundary.tsx`
- `frontend/src/components/loading/`
- `frontend/src/components/toast/`
- `frontend/src/lib/toast.ts`
- `frontend/src/lib/api-error-handler.ts`
- `frontend/src/lib/api.ts`
- `frontend/src/app/layout.tsx`
