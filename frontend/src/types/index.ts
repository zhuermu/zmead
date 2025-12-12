/**
 * TypeScript type definitions for the AAE Web Platform.
 */

// User types
export interface User {
  id: number;
  email: string;
  displayName: string;
  avatarUrl?: string;
  oauthProvider: string;
  giftedCredits: number;
  purchasedCredits: number;
  language: string;
  timezone: string;
  createdAt: string;
  lastLoginAt?: string;
}

// Ad Account types
export interface AdAccount {
  id: number;
  platform: 'meta' | 'tiktok' | 'google';
  platformAccountId: string;
  accountName: string;
  status: 'active' | 'expired' | 'revoked';
  isActive: boolean;
  tokenExpiresAt?: string;
  createdAt: string;
  lastSyncedAt?: string;
}

// Creative types
export interface Creative {
  id: number;
  fileUrl: string;
  cdnUrl: string;
  signedUrl?: string;  // Signed URL for secure access (1 hour expiry)
  fileType: 'image' | 'video';
  fileSize: number;
  name?: string;
  productUrl?: string;
  style?: string;
  score?: number;
  tags: string[];
  status: 'active' | 'deleted';
  createdAt: string;
}

// Bucket file types (for syncing from GCS)
export interface BucketFile {
  name: string;
  size: number;
  contentType?: string;
  updated?: string;
  url: string;
  synced: boolean;
}

export interface BucketListResponse {
  files: BucketFile[];
  total: number;
  prefix?: string;
}

export interface BucketSyncResult {
  fileKey: string;
  success: boolean;
  creativeId?: number;
  error?: string;
}

export interface BucketSyncResponse {
  syncedCount: number;
  failedCount: number;
  results: BucketSyncResult[];
}

// Campaign types
export interface Campaign {
  id: number;
  adAccountId: number;
  platform: string;
  platformCampaignId?: string;
  name: string;
  objective: string;
  status: 'draft' | 'active' | 'paused' | 'deleted';
  budget: number;
  budgetType: 'daily' | 'lifetime';
  targeting: Record<string, unknown>;
  creativeIds: number[];
  landingPageId?: number;
  createdAt: string;
}

// Landing Page types
export interface LandingPage {
  id: number;
  name: string;
  url: string;
  productUrl: string;
  template: string;
  language: string;
  status: 'draft' | 'published' | 'archived';
  createdAt: string;
  publishedAt?: string;
}

// Notification types
export interface Notification {
  id: number;
  type: 'urgent' | 'important' | 'general';
  category: string;
  title: string;
  message: string;
  actionUrl?: string;
  actionText?: string;
  isRead: boolean;
  readAt?: string;
  createdAt: string;
}

// Credit types
export interface CreditTransaction {
  id: number;
  type: 'deduct' | 'refund' | 'recharge' | 'gift';
  amount: number;
  fromGifted: number;
  fromPurchased: number;
  balanceAfter: number;
  operationType?: string;
  operationId?: string;
  details: Record<string, unknown>;
  createdAt: string;
}

// Report Metrics types
export interface ReportMetrics {
  id: number;
  timestamp: string;
  userId: number;
  adAccountId: number;
  entityType: 'campaign' | 'adset' | 'ad';
  entityId: string;
  entityName: string;
  impressions: number;
  clicks: number;
  spend: number;
  conversions: number;
  revenue: number;
  ctr: number;
  cpc: number;
  cpa: number;
  roas: number;
  createdAt: string;
}

export interface MetricsSummary {
  spend: number;
  roas: number;
  cpa: number;
  impressions: number;
  clicks: number;
  conversions: number;
  revenue: number;
  ctr: number;
  cpc: number;
}

export interface TrendDataPoint {
  date: string;
  spend: number;
  roas: number;
  cpa: number;
  impressions: number;
  clicks: number;
  conversions: number;
  revenue: number;
}

// API Response types
export interface ApiResponse<T> {
  data: T;
  message?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

export interface ApiError {
  detail: string;
  errorCode?: string;
}
