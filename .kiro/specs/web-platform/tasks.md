# Implementation Plan - Web Platform

- [x] 1. Set up project infrastructure and core configuration
  - Initialize Next.js 14 frontend project with TypeScript and Tailwind CSS
  - Initialize FastAPI backend project with Python 3.12+
  - Configure MySQL database connection and ORM (SQLAlchemy)
  - Configure Redis connection for caching and sessions
  - Set up AWS S3 buckets for file storage
  - Configure environment variables and secrets management
  - _Requirements: All_

- [x] 2. Implement Google OAuth authentication
- [x] 2.1 Create OAuth flow backend
  - Implement Google OAuth redirect endpoint
  - Implement OAuth callback handler
  - Create JWT token generation and validation
  - Implement token refresh logic
  - _Requirements: 1.1_

- [ ]* 2.2 Write property test for OAuth authentication
  - **Property 1: OAuth Login Creates or Retrieves User**
  - **Validates: Requirements 1.1**

- [x] 2.3 Create authentication UI components
  - Build Google OAuth login button
  - Implement authentication state management
  - Create protected route wrapper
  - _Requirements: 1.1_

- [x] 3. Implement user management and data models
- [x] 3.1 Create database schema and migrations
  - Define User model with int64 ID
  - Define AdAccount model
  - Define Creative model
  - Define Campaign model
  - Define LandingPage model
  - Define ReportMetrics model
  - Define CreditTransaction model
  - Define Notification model
  - Define CreditConfig model
  - Create database migration scripts
  - _Requirements: All data models_

- [x] 3.2 Implement user CRUD operations
  - Create user service layer
  - Implement get user info endpoint
  - Implement update user profile endpoint
  - Implement delete user account endpoint
  - _Requirements: 5.1, 5.2, 5.3, 5.4_

- [ ]* 3.3 Write unit tests for user operations
  - Test user creation
  - Test user retrieval
  - Test user update
  - Test user deletion
  - _Requirements: 5.1, 5.2, 5.3, 5.4_

- [x] 4. Implement Credit system
- [x] 4.1 Create credit service layer
  - Implement get credit balance function
  - Implement deduct credit function with transaction support
  - Implement refund credit function
  - Implement credit transaction logging
  - _Requirements: 3.1, 3.2, 3.3, 13.1, 13.3, 13.5_

- [ ]* 4.2 Write property test for credit balance accuracy
  - **Property 6: Credit Balance Display Accuracy**
  - **Validates: Requirements 3.2**

- [ ]* 4.3 Write property test for credit deduction order
  - **Property 7: Credit Deduction Order**
  - **Validates: Requirements 13.5**

- [ ]* 4.4 Write property test for insufficient credit error
  - **Property 8: Insufficient Credit Error**
  - **Validates: Requirements 3.4, 13.3**

- [ ]* 4.5 Write property test for credit deduction atomicity
  - **Property 9: Credit Deduction Atomicity**
  - **Validates: Requirements 13.3.4**

- [x] 4.6 Implement credit recharge with Stripe
  - Integrate Stripe SDK
  - Create recharge order endpoint
  - Implement Stripe webhook handler
  - Update credit balance on successful payment
  - _Requirements: 3.2.1, 3.2.2, 3.2.3, 3.2.4_

- [ ]* 4.7 Write unit tests for Stripe integration
  - Test recharge order creation
  - Test webhook handling
  - Test payment success flow
  - Test payment failure handling
  - _Requirements: 3.2.1, 3.2.2, 3.2.3_

- [x] 4.8 Implement credit configuration management
  - Create credit config model
  - Implement get config endpoint (internal only)
  - Implement update config function (admin only)
  - Seed default configuration
  - _Requirements: 3.3.1, 3.3.2, 3.3.3, 3.3.4, 3.3.5_

- [ ]* 4.9 Write property test for config changes non-retroactive
  - **Property 10: Credit Config Changes Non-Retroactive**
  - **Validates: Requirements 3.5, 3.3.4**

- [x] 5. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.


- [x] 6. Implement Ad Account management
- [x] 6.1 Create ad account service layer
  - Implement bind ad account function
  - Implement OAuth token encryption/decryption
  - Implement list ad accounts endpoint
  - Implement get ad account details endpoint
  - Implement unbind ad account endpoint
  - _Requirements: 2.1, 2.2, 2.5_

- [ ]* 6.2 Write property test for OAuth token encryption
  - **Property 2: OAuth Token Encryption Round Trip**
  - **Validates: Requirements 2.2**

- [x] 6.3 Implement token refresh mechanism
  - Create background job for token expiry checking
  - Implement auto-refresh logic
  - Implement refresh failure handling
  - Create notification on refresh failure
  - _Requirements: 2.1.1, 2.1.2, 2.1.3, 2.1.4, 2.3, 2.4_

- [ ]* 6.4 Write property test for token refresh
  - **Property 3: Token Refresh Before Expiry**
  - **Validates: Requirements 2.1.1, 2.3**

- [ ]* 6.5 Write property test for token refresh failure notifications
  - **Property 4: Token Refresh Failure Triggers Notifications**
  - **Validates: Requirements 2.1.2, 2.1.3, 2.1.4**

- [ ]* 6.6 Write unit tests for ad account operations
  - Test ad account binding
  - Test token encryption/decryption
  - Test token refresh
  - Test account unbinding
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 7. Implement Creative management
- [x] 7.1 Create creative service layer
  - Implement create creative function
  - Implement get creatives list endpoint
  - Implement get creative details endpoint
  - Implement update creative endpoint
  - Implement delete creative endpoint
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [x] 7.2 Implement S3 file upload
  - Create presigned URL generation function
  - Implement file upload to S3
  - Configure CloudFront CDN
  - _Requirements: 7.2_

- [ ]* 7.3 Write property test for S3 upload round trip
  - **Property 17: S3 File Upload Round Trip**
  - **Validates: Requirements 7.2**

- [ ]* 7.4 Write property test for creative deletion
  - **Property 18: Creative Deletion Cascades to Storage**
  - **Validates: Requirements 7.5**

- [ ]* 7.5 Write unit tests for creative operations
  - Test creative creation
  - Test creative listing with filters
  - Test creative update
  - Test creative deletion
  - Test S3 upload
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [x] 8. Implement Report data management
- [x] 8.1 Create report metrics service layer
  - Implement save metrics function
  - Implement get metrics endpoint with time range filtering
  - Implement get aggregated metrics endpoint
  - Implement metrics archival logic
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [ ]* 8.2 Write property test for metrics storage
  - **Property 19: Report Metrics Storage**
  - **Validates: Requirements 8.1**

- [ ]* 8.3 Write property test for data archival
  - **Property 20: Report Data Archival**
  - **Validates: Requirements 8.4**

- [ ]* 8.4 Write unit tests for report operations
  - Test metrics saving
  - Test metrics retrieval with filters
  - Test aggregation
  - Test archival
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [x] 9. Implement Landing Page management
- [x] 9.1 Create landing page service layer
  - Implement create landing page function
  - Implement get landing pages list endpoint
  - Implement get landing page details endpoint
  - Implement update landing page endpoint
  - Implement delete landing page endpoint
  - _Requirements: 9.1, 9.3, 9.4, 9.5_

- [x] 9.2 Implement landing page publishing
  - Create S3 upload for HTML files
  - Configure CloudFront distribution
  - Implement publish endpoint
  - _Requirements: 9.2_

- [ ]* 9.3 Write property test for landing page deployment
  - **Property 21: Landing Page S3 and CloudFront Deployment**
  - **Validates: Requirements 9.2**

- [ ]* 9.4 Write unit tests for landing page operations
  - Test landing page creation
  - Test landing page listing
  - Test landing page update
  - Test landing page publishing
  - Test landing page deletion
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

- [x] 10. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 11. Implement Campaign management
- [x] 11.1 Create campaign service layer
  - Implement create campaign function
  - Implement get campaigns list endpoint
  - Implement get campaign details endpoint
  - Implement update campaign endpoint
  - Implement delete campaign endpoint
  - _Requirements: 10.1, 10.2, 10.4, 10.5_

- [x] 11.2 Implement platform sync
  - Create ad platform API client wrapper
  - Implement sync to platform on create/update
  - Handle platform API errors
  - _Requirements: 10.3_

- [ ]* 11.3 Write property test for campaign platform sync
  - **Property 22: Campaign Platform Sync**
  - **Validates: Requirements 10.3**

- [ ]* 11.4 Write unit tests for campaign operations
  - Test campaign creation
  - Test campaign listing
  - Test campaign update
  - Test platform sync
  - Test campaign deletion
  - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_

- [x] 12. Implement Notification system
- [x] 12.1 Create notification service layer
  - Implement create notification function
  - Implement get notifications list endpoint
  - Implement mark as read endpoint
  - Implement get unread count endpoint
  - _Requirements: 16.1, 16.2, 16.3, 16.4, 16.5_

- [x] 12.2 Implement notification channels
  - Create email notification sender
  - Create in-app notification handler
  - Implement notification preferences
  - _Requirements: 16.1.1, 16.1.2, 16.1.3, 16.1.4, 16.1.5, 16.2.1, 16.2.2, 16.2.3, 16.2.4_

- [ ]* 12.3 Write property test for urgent notification multi-channel
  - **Property 26: Notification Creation Multi-Channel**
  - **Validates: Requirements 16.2.1, 16.1.5**

- [ ]* 12.4 Write property test for notification read status
  - **Property 27: Notification Read Status Update**
  - **Validates: Requirements 16.4**

- [ ]* 12.5 Write unit tests for notification system
  - Test notification creation
  - Test notification listing
  - Test mark as read
  - Test email sending
  - Test notification preferences
  - _Requirements: 16.1, 16.2, 16.3, 16.4, 16.5_

- [x] 13. Implement MCP Server
- [x] 13.1 Create MCP server framework
  - Implement MCP protocol handler
  - Create tool registry
  - Implement request validation
  - Implement response formatting
  - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5_

- [x] 13.2 Implement MCP tools for creative management
  - Implement get_creatives tool
  - Implement get_creative tool
  - Implement create_creative tool
  - Implement update_creative tool
  - Implement delete_creative tool
  - Implement get_upload_url tool
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [x] 13.3 Implement MCP tools for report data
  - Implement get_reports tool
  - Implement get_metrics tool
  - Implement save_metrics tool
  - Implement analyze_performance tool
  - _Requirements: 8.1, 8.2, 8.3, 8.5_

- [x] 13.4 Implement MCP tools for landing pages
  - Implement get_landing_pages tool
  - Implement get_landing_page tool
  - Implement create_landing_page tool
  - Implement update_landing_page tool
  - Implement delete_landing_page tool
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

- [x] 13.5 Implement MCP tools for campaigns
  - Implement get_campaigns tool
  - Implement get_campaign tool
  - Implement create_campaign tool
  - Implement update_campaign tool
  - Implement delete_campaign tool
  - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_

- [x] 13.6 Implement MCP tools for credit management
  - Implement get_credit_balance tool
  - Implement check_credit tool
  - Implement deduct_credit tool
  - Implement refund_credit tool
  - Implement get_credit_history tool
  - Implement get_credit_config tool
  - Implement estimate_credit tool
  - _Requirements: 13.1, 13.2, 13.3_

- [x] 13.7 Implement MCP tools for notifications
  - Implement create_notification tool
  - Implement get_notifications tool
  - Implement mark_notification_read tool
  - Implement get_unread_count tool
  - _Requirements: 16.1, 16.2, 16.3, 16.4, 16.5_

- [x] 13.8 Implement MCP tools for ad accounts
  - Implement get_ad_account_token tool
  - Implement list_ad_accounts tool
  - Implement get_active_ad_account tool
  - Implement set_active_ad_account tool
  - Implement refresh_ad_account_token tool
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [ ]* 13.9 Write property test for MCP authentication
  - **Property 23: MCP Tool Authentication**
  - **Validates: Requirements 12.2**

- [ ]* 13.10 Write property test for MCP success response
  - **Property 24: MCP Tool Execution Result Format**
  - **Validates: Requirements 12.3**

- [ ]* 13.11 Write property test for MCP error response
  - **Property 25: MCP Tool Execution Error Format**
  - **Validates: Requirements 12.4**

- [ ]* 13.12 Write unit tests for MCP tools
  - Test tool registration
  - Test request validation
  - Test authentication
  - Test each tool execution
  - Test error handling
  - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5_

- [x] 14. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.



## Frontend UI Implementation

- [x] 15. Implement Dashboard UI with metrics and charts
- [x] 15.1 Install chart library
  - Install Recharts or Tremor for data visualization
  - Configure chart theme and defaults
  - _Requirements: 4.3, 15.1_

- [x] 15.2 Create Dashboard layout with sidebar navigation
  - Implement responsive sidebar with navigation links (Dashboard, Creatives, Campaigns, Landing Pages, Reports, Billing, Settings)
  - Create header with user info and notifications bell
  - Set up main content area layout
  - Add mobile menu toggle
  - _Requirements: 4.1, 4.2_

- [x] 15.3 Implement Dashboard metrics cards
  - Create today/yesterday core metrics display (Spend, ROAS, CPA)
  - Implement metric comparison with percentage change
  - Add loading states and error handling
  - _Requirements: 4.2, 4.3_

- [x] 15.4 Implement Dashboard charts
  - Create 7-day trend line chart using Recharts
  - Implement chart data fetching from API
  - Add chart tooltips and legends
  - _Requirements: 4.3_

- [x] 15.5 Implement AI suggestions card
  - Create suggestion card component
  - Fetch AI suggestions from backend
  - Add action buttons for suggestions
  - _Requirements: 4.4_

- [x] 15.6 Display AI Agent chat entry point
  - Show chat icon in bottom-right corner on Dashboard
  - Ensure chat is accessible from Dashboard
  - _Requirements: 4.5_

- [-] 16. Implement AI Agent Chat Interface
- [x] 16.1 Install and configure Vercel AI SDK
  - Install ai and @ai-sdk/react packages
  - Install react-markdown for message rendering
  - Configure API route for chat endpoint
  - _Requirements: 4.1, 4.2_

- [x] 16.2 Create chat window component
  - Build floating chat button (bottom-right corner)
  - Implement expandable chat window
  - Create message list with user/AI message styling
  - Implement message bubble component with Markdown support
  - Create tool invocation card component
  - _Requirements: 4.1.1, 4.1.2_

- [x] 16.3 Implement useChat hook integration
  - Use Vercel AI SDK's useChat hook
  - Configure API endpoint (/api/chat)
  - Handle onResponse, onFinish, onError callbacks
  - Implement message state management
  - _Requirements: 4.1.3, 4.1.4_

- [x] 16.4 Implement WebSocket connection (alternative to HTTP streaming)
  - Set up WebSocket client with auto-reconnect
  - Implement heartbeat mechanism (30s ping, 60s timeout)
  - Handle connection states (connected, reconnecting, disconnected)
  - Display connection status indicator (green/yellow/red)
  - Implement message queue for offline messages (max 10)
  - Implement exponential backoff reconnection (1s, 2s, 4s, max 3 attempts)
  - Show "Connection lost" message after max retries
  - _Requirements: 12.1.1, 12.1.2, 12.1.3, 12.1.4, 12.1.5_

- [x] 16.5 Implement chat message handling
  - Support text, image, and link input
  - Implement streaming response display
  - Create clickable action buttons in AI responses
  - Embed charts and cards in conversation
  - Implement message timeout handling (60s)
  - Show "Response timeout" message with retry button
  - _Requirements: 4.2.1, 4.2.2, 4.2.3, 4.2.4, 4.2.5, 12.1.6_

- [ ] 16.6 Implement chat history persistence
  - Save conversation history to local storage
  - Load previous conversations on window open
  - Implement conversation clear function
  - _Requirements: 4.1.5_

- [x] 17. Implement Creative Library UI
- [x] 17.1 Create creatives list page
  - Implement grid/list view toggle
  - Create creative card with thumbnail, score, tags
  - Add filtering by type, status, date
  - Implement pagination
  - _Requirements: 7.3, 7.4_

- [x] 17.2 Create creative upload component
  - Implement drag-and-drop file upload
  - Show upload progress
  - Support image and video preview
  - _Requirements: 7.1, 7.2_

- [x] 17.3 Create creative detail modal
  - Display full creative with metadata
  - Show AI quality score and tags
  - Add edit and delete actions
  - _Requirements: 7.3, 7.4, 7.5_

- [x] 18. Implement Campaign Management UI
- [x] 18.1 Create campaigns list page
  - Display campaigns in table format
  - Show status, budget, performance metrics
  - Add filtering and sorting
  - Implement pagination
  - _Requirements: 10.2_

- [x] 18.2 Create campaign detail page
  - Display campaign configuration
  - Show associated creatives and landing pages
  - Display real-time performance metrics
  - _Requirements: 10.2, 10.4_

- [x] 18.3 Create campaign form
  - Implement campaign creation wizard
  - Add targeting configuration
  - Budget and schedule settings
  - Creative and landing page selection
  - _Requirements: 10.1_

- [x] 19. Implement Landing Page Management UI
- [x] 19.1 Create landing pages list page
  - Display landing pages with thumbnails
  - Show status (draft, published, archived)
  - Add filtering and search
  - _Requirements: 9.3_

- [x] 19.2 Create landing page preview
  - Implement iframe preview
  - Show mobile/desktop toggle
  - Display conversion metrics
  - _Requirements: 9.3, 9.4_

- [x] 19.3 Create landing page visual editor
  - Implement visual editing interface
  - Support text editing (rich text: bold, italic, color)
  - Support image upload with auto-compression
  - Support drag-and-drop layout adjustment
  - Implement undo/redo (up to 20 steps)
  - Add theme color customization with live preview
  - Preview in new tab functionality
  - Publish/unpublish actions
  - _Requirements: 14.1, 14.1.1, 14.1.2, 14.1.3, 14.1.4, 14.1.5, 9.1, 9.2, 9.5_

- [x] 20. Implement Reports UI
- [x] 20.1 Create reports dashboard
  - Display core metrics cards (Spend, ROAS, CPA)
  - Date range selector (7d, 30d, custom)
  - Ad account filter
  - _Requirements: 15.1, 8.2, 8.3_

- [x] 20.2 Create performance charts
  - Implement 7-day ROAS trend line chart
  - Implement 7-day CPA trend line chart
  - Create spend distribution pie chart (by Campaign)
  - Add hover tooltips with detailed values
  - Implement legend toggle (show/hide data series)
  - Add time axis zoom/drag
  - Click data point to show details
  - Export chart as PNG/SVG
  - _Requirements: 15.1, 15.2.1, 15.2.2, 15.2.3, 15.2.4, 15.2.5, 8.2, 8.5_

- [x] 20.3 Create multi-level metrics table
  - Default display Campaign level data
  - Click Campaign to expand Adset data
  - Click Adset to expand Ad data
  - Click Ad to show creative performance
  - Maintain filters and sorting when switching levels
  - Sortable columns
  - Export to CSV functionality
  - _Requirements: 15.1.1, 15.1.2, 15.1.3, 15.1.4, 15.1.5, 8.2, 8.3_

- [x] 21. Implement Ad Account Management UI
- [x] 21.1 Create ad accounts list page
  - Display bound accounts with platform icons
  - Show account status and last sync time
  - Add unbind action
  - _Requirements: 2.5_

- [x] 21.2 Create ad account binding flow
  - Platform selection (Meta, TikTok, Google)
  - OAuth redirect handling
  - Success/error feedback
  - _Requirements: 2.1, 2.2_

- [x] 21.3 Create token expiry warning banner
  - Display warning when token expires soon
  - Show re-authorize button
  - Handle re-authorization flow
  - _Requirements: 2.1.3, 2.1.5_

- [x] 22. Implement Billing & Credits UI
- [x] 22.1 Create billing overview page
  - Display current credit balance with breakdown
  - Show gifted vs purchased credits
  - Display low balance warning (< 50 credits)
  - Display critical balance alert (< 10 credits)
  - Show recharge button
  - _Requirements: 6.1, 13.2.1, 13.2.2, 13.2.3_

- [x] 22.2 Create credit packages selection
  - Display all available packages with pricing
  - Show discount percentage and savings
  - Display unit price per credit
  - Stripe checkout integration
  - Show payment amount and credits to receive
  - _Requirements: 3.2.1, 3.2.2, 6.3_

- [x] 22.3 Create transaction history
  - Display credit consumption records (last 30 days)
  - Show transaction details (time, type, amount, operation, model, tokens)
  - Filter by type (deduct, refund, recharge, gift)
  - Date range filtering
  - Daily/weekly/monthly aggregation view
  - Export to CSV
  - Highlight anomalies (single transaction > 1000 credits)
  - _Requirements: 6.2, 13.1.1, 13.1.2, 13.1.3, 13.1.4, 13.1.5_

- [x] 22.4 Create credit alert threshold settings
  - Allow users to set custom warning threshold
  - Configure notification preferences for credit alerts
  - _Requirements: 13.2.4_

- [x] 23. Implement User Settings UI
- [x] 23.1 Create settings page layout
  - Tab navigation (Profile, Notifications, Security, Data)
  - Responsive design
  - _Requirements: 5.1_

- [x] 23.2 Create profile settings tab
  - Display and edit user info (name, email)
  - Avatar upload with preview
  - Language selection
  - Timezone settings
  - Save changes button
  - _Requirements: 5.2_

- [x] 23.3 Create notification preferences tab
  - Toggle for in-app notifications
  - Toggle for email notifications
  - Category-specific preferences (ad_rejected, token_expired, etc.)
  - Channel selection per category (in-app, email, both)
  - Note: Urgent notifications always sent regardless of preferences
  - _Requirements: 5.3, 16.1.1, 16.1.2, 16.1.3, 16.1.4, 16.1.5_

- [x] 23.4 Create data & privacy tab
  - Data export request button
  - Show export status and download link (24h expiry)
  - Account deletion with confirmation flow
  - Display data deletion warning
  - Require "DELETE" text confirmation
  - Show list of data to be deleted
  - _Requirements: 5.1.1, 5.1.2, 5.1.3, 5.1.4, 5.2.1, 5.2.2, 5.2.3_

- [x] 24. Implement Notification Center UI
- [x] 24.1 Create notification dropdown
  - Bell icon with unread count badge in header
  - Dropdown list of recent notifications (last 10)
  - Display notification type icons (🔴 urgent, 🟡 important, 🟢 general)
  - Show timestamp (relative time)
  - Mark as read on click
  - Navigate to related page on click
  - "View All" link to notifications page
  - _Requirements: 16.1, 16.3, 16.4_

- [x] 24.2 Create notifications page
  - Full list of all notifications (paginated)
  - Filter by type (urgent, important, general)
  - Filter by read status (all, unread, read)
  - Filter by category (ad_rejected, token_expired, etc.)
  - Sort by date
  - Mark all as read action
  - Auto-archive notifications older than 30 days
  - _Requirements: 16.3, 16.5, 16.2.5_

- [x] 25. Implement WebSocket Chat Backend (Alternative to HTTP Streaming)
- [x] 25.1 Create WebSocket endpoint
  - Implement WebSocket connection handler at /ws/chat
  - Add authentication middleware for WebSocket
  - Handle connection lifecycle (connect, disconnect)
  - Store active connections in memory/Redis
  - _Requirements: 12.1.1_

- [x] 25.2 Implement WebSocket message handling
  - Parse incoming messages from frontend
  - Validate message format
  - Forward messages to AI Orchestrator via HTTP
  - Stream responses back to frontend via WebSocket
  - Handle connection errors and timeouts
  - _Requirements: 4.1.4, 4.2.2_

- [x] 25.3 Implement heartbeat mechanism
  - Send ping every 30 seconds to all connected clients
  - Detect disconnection if no pong within 60 seconds
  - Clean up stale connections
  - Log connection metrics
  - _Requirements: 12.1.2_

- [x] 25.4 Create chat API route (HTTP Streaming alternative)
  - Implement POST /api/chat endpoint for Vercel AI SDK
  - Forward to AI Orchestrator
  - Return streaming response compatible with Vercel AI SDK
  - Handle authentication via JWT
  - _Requirements: 4.1.3, 4.1.4_

- [x] 26. Implement Celery Task Scheduling
- [x] 26.1 Configure Celery Beat scheduler
  - Set up Celery Beat with Redis broker
  - Configure scheduled tasks (data fetch: 6h, report: daily 9am, anomaly: hourly, token check: daily 2am)
  - _Requirements: 12.2.1_

- [x] 26.2 Create token refresh scheduled task
  - Implement Celery task to check expiring tokens (< 24h)
  - Call token refresh for each expiring account
  - Send notifications on refresh failure
  - _Requirements: 2.1.1, 2.1.2, 2.1.3, 2.1.4, 12.2.2, 12.2.5_

- [x] 27. Implement Data Export Backend
- [x] 27.1 Create data export service
  - Implement export all user data function
  - Generate ZIP file with all data (profile, ad accounts, credits, creatives, landing pages, campaigns, reports)
  - Upload ZIP to S3 with 24h expiry
  - Send email notification with download link
  - Handle long-running exports (> 5 min) in background
  - _Requirements: 5.1.1, 5.1.2, 5.1.3, 5.1.4, 5.1.5_

- [x] 27.2 Create data export endpoint
  - Implement POST /api/v1/users/me/export endpoint
  - Return export job ID
  - Implement GET /api/v1/users/me/export/{job_id} to check status
  - _Requirements: 5.1.1_

- [x] 28. Implement Account Deletion Backend
- [x] 28.1 Create account deletion service
  - Implement permanent delete function
  - Delete all user data from database
  - Delete all S3 files (creatives, landing pages)
  - Send deletion confirmation email
  - Implement rollback on failure
  - _Requirements: 5.2.3, 5.2.4, 5.2.5_

- [x] 28.2 Create account deletion endpoint
  - Implement DELETE /api/v1/users/me endpoint
  - Require password verification
  - Return success/error response
  - _Requirements: 5.2.2_

- [x] 28.3 Implement API Rate Limiting
  - Add rate limiting middleware for API endpoints
  - Configure per-user limits (e.g., 100 requests/minute)
  - Return 429 status code when limit exceeded
  - Add rate limit headers (X-RateLimit-Limit, X-RateLimit-Remaining)
  - _Requirements: 11.5_

- [x] 29. Implement Admin Credit Config UI
- [x] 29.1 Create admin config page
  - Display all configurable credit parameters
  - Show current values for all rates
  - Edit form for each configuration item
  - Validation for input values
  - Save button with confirmation
  - _Requirements: 3.3.1, 3.3.2_

- [x] 29.2 Implement config change logging
  - Record all configuration changes
  - Log timestamp, admin user, old value, new value
  - Display change history
  - _Requirements: 3.3.5_

- [x] 30. Implement GDPR Compliance Features
- [x] 30.1 Create Cookie consent banner
  - Display cookie consent popup on first visit
  - Store consent preference in localStorage
  - Link to Privacy Policy and Cookie Policy
  - _Requirements: Compliance 4_

- [x] 30.2 Create Terms of Service and Privacy Policy pages
  - Create /terms page with terms content
  - Create /privacy page with privacy policy
  - Create /cookies page with cookie policy
  - _Requirements: Compliance 1_

- [x] 31. Implement Error Handling and Loading States
- [x] 31.1 Create global error boundary
  - Catch and display React errors gracefully
  - Provide "Reload" button
  - Log errors to monitoring service
  - _Requirements: General UX_

- [x] 31.2 Create loading skeletons
  - Implement skeleton loaders for all data-heavy pages
  - Add loading spinners for buttons and forms
  - Show progress indicators for long operations
  - _Requirements: General UX_

- [x] 31.3 Create error toast notifications
  - Display API errors as toast messages
  - Show success confirmations
  - Auto-dismiss after 5 seconds
  - _Requirements: General UX_

- [x] 32. Final Frontend Checkpoint
  - Ensure all pages are accessible and functional
  - Verify responsive design on mobile/tablet
  - Test all API integrations
  - Ensure proper error handling and loading states
  - Test WebSocket connection and reconnection
  - Verify all forms have proper validation
  - Test GDPR compliance features (data export, account deletion, cookie consent)
  - Verify all notification types display correctly
