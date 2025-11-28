# Project Structure

## Repository Layout

```
.
├── backend/          # FastAPI backend application
├── frontend/         # Next.js frontend application
├── docker-compose.yml
└── .kiro/            # Kiro AI assistant configuration
```

## Backend Structure

```
backend/
├── alembic/                    # Database migrations
│   ├── versions/               # Migration files
│   └── env.py                  # Alembic configuration
├── app/
│   ├── api/                    # API endpoints
│   │   ├── deps.py             # Dependency injection
│   │   └── v1/                 # API v1 routes
│   │       ├── router.py       # Main router
│   │       ├── auth.py         # Authentication endpoints
│   │       ├── campaigns.py    # Campaign management
│   │       ├── creatives.py    # Creative management
│   │       ├── credits.py      # Credit/billing
│   │       ├── landing_pages.py
│   │       ├── reports.py
│   │       ├── notifications.py
│   │       ├── users.py
│   │       ├── websocket.py    # WebSocket chat
│   │       ├── chat.py         # Chat endpoints
│   │       └── mcp.py          # MCP server endpoints
│   ├── core/                   # Core configuration
│   │   ├── config.py           # Settings (Pydantic)
│   │   ├── database.py         # SQLAlchemy setup
│   │   ├── security.py         # Auth utilities
│   │   ├── redis.py            # Redis client
│   │   ├── storage.py          # S3 client
│   │   ├── celery.py           # Celery app
│   │   └── rate_limit.py       # Rate limiting
│   ├── models/                 # SQLAlchemy models
│   │   ├── user.py
│   │   ├── campaign.py
│   │   ├── creative.py
│   │   ├── landing_page.py
│   │   ├── report_metrics.py
│   │   ├── notification.py
│   │   ├── ad_account.py
│   │   ├── credit_config.py
│   │   └── credit_transaction.py
│   ├── schemas/                # Pydantic schemas (API contracts)
│   │   ├── auth.py
│   │   ├── campaign.py
│   │   ├── creative.py
│   │   ├── landing_page.py
│   │   ├── report.py
│   │   ├── notification.py
│   │   ├── user.py
│   │   └── credit.py
│   ├── services/               # Business logic
│   │   ├── auth.py
│   │   ├── campaign.py
│   │   ├── creative.py
│   │   ├── landing_page.py
│   │   ├── report.py
│   │   ├── notification.py
│   │   ├── user.py
│   │   ├── credit.py
│   │   ├── stripe.py
│   │   ├── email.py
│   │   ├── platform_sync.py    # Ad platform sync
│   │   ├── account_deletion.py # GDPR compliance
│   │   └── data_export.py      # GDPR data export
│   ├── tasks/                  # Celery background tasks
│   │   ├── data_fetch.py       # Periodic data sync
│   │   ├── reports.py          # Report generation
│   │   ├── token_refresh.py    # OAuth token refresh
│   │   └── anomaly_detection.py
│   ├── mcp/                    # MCP Server implementation
│   │   ├── server.py           # MCP server
│   │   ├── registry.py         # Tool registry
│   │   ├── auth.py             # MCP authentication
│   │   ├── types.py            # Type definitions
│   │   ├── validation.py       # Input validation
│   │   └── tools/              # MCP tools
│   │       ├── ad_account.py
│   │       ├── campaign.py
│   │       ├── creative.py
│   │       ├── credit.py
│   │       ├── landing_page.py
│   │       ├── notification.py
│   │       └── report.py
│   └── main.py                 # FastAPI app entry point
├── tests/                      # Test files
├── pyproject.toml              # Python dependencies
├── alembic.ini                 # Alembic config
└── .env                        # Environment variables
```

## Frontend Structure

```
frontend/
├── src/
│   ├── app/                    # Next.js App Router
│   │   ├── layout.tsx          # Root layout
│   │   ├── page.tsx            # Home page
│   │   ├── globals.css         # Global styles
│   │   ├── dashboard/          # Dashboard page
│   │   ├── campaigns/          # Campaign management
│   │   │   ├── page.tsx        # List view
│   │   │   ├── new/            # Create campaign
│   │   │   └── [id]/           # Campaign detail/edit
│   │   ├── creatives/          # Creative management
│   │   ├── landing-pages/      # Landing page management
│   │   ├── reports/            # Reports page
│   │   ├── notifications/      # Notifications page
│   │   ├── billing/            # Billing pages
│   │   │   ├── page.tsx        # Overview
│   │   │   ├── recharge/       # Credit recharge
│   │   │   ├── history/        # Transaction history
│   │   │   └── settings/       # Billing settings
│   │   ├── settings/           # User settings
│   │   ├── admin/              # Admin pages
│   │   │   └── config/         # Admin config
│   │   ├── auth/               # Auth pages
│   │   │   └── callback/       # OAuth callback
│   │   ├── ad-accounts/        # Ad account binding
│   │   │   └── callback/       # Platform OAuth callback
│   │   ├── login/              # Login page
│   │   ├── privacy/            # Privacy policy
│   │   ├── terms/              # Terms of service
│   │   ├── cookies/            # Cookie policy
│   │   └── api/                # API routes
│   │       └── chat/           # Chat API endpoint
│   ├── components/             # React components
│   │   ├── auth/               # Auth components
│   │   │   ├── AuthProvider.tsx
│   │   │   ├── ProtectedRoute.tsx
│   │   │   └── GoogleLoginButton.tsx
│   │   ├── chat/               # Chat components
│   │   │   ├── ChatWindow.tsx  # Main chat interface
│   │   │   ├── ChatButton.tsx  # Toggle button
│   │   │   ├── ChatInput.tsx
│   │   │   ├── MessageList.tsx
│   │   │   ├── MessageBubble.tsx
│   │   │   ├── ConnectionStatus.tsx
│   │   │   ├── ToolInvocationCard.tsx
│   │   │   ├── EmbeddedCard.tsx
│   │   │   └── EmbeddedChart.tsx
│   │   ├── dashboard/          # Dashboard components
│   │   │   ├── MetricCard.tsx
│   │   │   ├── TrendChart.tsx
│   │   │   └── AISuggestionsCard.tsx
│   │   ├── creatives/          # Creative components
│   │   ├── reports/            # Report components
│   │   ├── notifications/      # Notification components
│   │   ├── settings/           # Settings components
│   │   ├── ad-accounts/        # Ad account components
│   │   ├── gdpr/               # GDPR components
│   │   │   └── CookieConsent.tsx
│   │   ├── loading/            # Loading states
│   │   │   ├── LoadingSpinner.tsx
│   │   │   ├── DashboardSkeleton.tsx
│   │   │   ├── TableSkeleton.tsx
│   │   │   └── CardGridSkeleton.tsx
│   │   ├── error/              # Error handling
│   │   │   └── ErrorBoundary.tsx
│   │   ├── toast/              # Toast notifications
│   │   └── ui/                 # Shadcn/ui components
│   │       ├── button.tsx
│   │       ├── card.tsx
│   │       ├── input.tsx
│   │       ├── select.tsx
│   │       └── skeleton.tsx
│   ├── hooks/                  # Custom React hooks
│   │   ├── useChat.ts          # Chat hook
│   │   └── useWebSocket.ts     # WebSocket hook
│   ├── lib/                    # Utilities
│   │   ├── api.ts              # API client
│   │   ├── api-error-handler.ts
│   │   ├── auth.ts             # Auth utilities
│   │   ├── config.ts           # Frontend config
│   │   ├── store.ts            # Zustand store
│   │   ├── toast.ts            # Toast utilities
│   │   └── utils.ts            # General utilities
│   └── types/                  # TypeScript types
│       └── index.ts
├── public/                     # Static assets
├── package.json
├── tsconfig.json
├── tailwind.config.ts
├── next.config.mjs
└── .env.local                  # Environment variables
```

## Architecture Patterns

### Backend Patterns

- **Layered Architecture**: API → Services → Models
- **Dependency Injection**: FastAPI's `Depends()` for database sessions, auth
- **Repository Pattern**: Services encapsulate data access logic
- **Background Tasks**: Celery for async operations (data sync, reports)
- **MCP Server**: Exposes tools for AI agent to access data

### Frontend Patterns

- **App Router**: Next.js 14 file-based routing
- **Server Components**: Default for data fetching
- **Client Components**: Interactive UI with `'use client'`
- **Component Composition**: Atomic design (ui → components → pages)
- **State Management**: Zustand for global state, React Query for server state
- **Embedded Chat**: Bottom-right floating chat window using Vercel AI SDK

## Key Conventions

- **API Versioning**: `/api/v1/` prefix for all backend endpoints
- **Authentication**: JWT tokens in Authorization header
- **WebSocket**: `/ws/chat` endpoint for real-time chat
- **File Uploads**: Multipart form data to S3 via backend
- **Error Handling**: Consistent error responses with status codes
- **Database**: Async SQLAlchemy with connection pooling
- **Migrations**: Alembic for schema changes (never modify DB directly)
- **Environment**: Separate `.env` files for backend/frontend
