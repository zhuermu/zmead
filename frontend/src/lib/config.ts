/**
 * Application configuration.
 */

export const config = {
  apiUrl: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  wsUrl: process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000',
  appName: 'AAE Web Platform',
} as const;

export default config;
