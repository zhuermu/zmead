# Design Document - Web Platform

## Overview

The Web Platform serves as the central user portal and data management hub for the AAE (Automated Ad Engine) system. It provides a Next.js-based web interface with an embedded AI Agent chat component, manages all business data (creatives, reports, landing pages, campaigns), handles user authentication and billing, and exposes an MCP Server interface for AI Agent integration.

### Key Responsibilities

1. **User Interface**: Next.js 14 web application with embedded AI chat
2. **Data Management**: Centralized storage for all business entities
3. **Authentication & Authorization**: User registration, login, OAuth integration
4. **Billing System**: Credit-based payment model with Stripe integration
5. **MCP Server**: Provides data access tools for AI Orchestrator
6. **WebSocket Server**: Real-time communication with AI Orchestrator
7. **Task Scheduling**: Celery-based background job processing

### System Boundaries

**In Scope**:
- Web frontend (Next.js + TypeScript + Tailwind CSS)
- Backend API (FastAPI + Python 3.11+)
- Data storage (PostgreSQL + TimescaleDB + Redis + S3)
- MCP Server implementation
- WebSocket server for real-time chat
- User authentication and authorization
- Credit billing system
- Notification system

**Out of Scope**:
- AI conversation logic (handled by AI Orchestrator)
- Intent recognition (handled by AI Orchestrator)
- Creative generation algorithms (handled by Ad Creative module)
- Performance analysis algorithms (handled by Ad Performance module)
- Market intelligence algorithms (handled by Market Insights module)


## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Web Platform                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                  Frontend Layer                            │ │
│  │  (Next.js 14 + TypeScript + Tailwind CSS)                 │ │
│  │                                                            │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │ │
│  │  │Dashboard │  │Creatives │  │Reports   │  │Settings  │ │ │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘ │ │
│  │                                                            │ │
│  │  ┌────────────────────────────────────────────────────┐  │ │
│  │  │   Embedded AI Chat (Vercel AI SDK)                 │  │ │
│  │  │   - useChat hook for streaming                     │  │ │
│  │  │   - Tool invocation UI                             │  │ │
│  │  │   - Message history                                │  │ │
│  │  └────────────────────────────────────────────────────┘  │ │
│  └───────────────────────────────────────────────────────────┘ │
│                          │                                      │
│                          │ HTTP / WebSocket                     │
│                          ▼                                      │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                  Backend Layer                             │ │
│  │  (FastAPI + Python 3.11+)                                 │ │
│  │                                                            │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │ │
│  │  │ Auth Module  │  │Billing Module│  │Account Module│   │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘   │ │
│  │                                                            │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │ │
│  │  │Creative Mgmt │  │Report Data   │  │Landing Page  │   │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘   │ │
│  │                                                            │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │ │
│  │  │Campaign Mgmt │  │Notification  │  │WebSocket Srv │   │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘   │ │
│  │                                                            │ │
│  │  ┌────────────────────────────────────────────────────┐  │ │
│  │  │              MCP Server                             │  │ │
│  │  │  - Tool registry                                    │  │ │
│  │  │  - Request validation                               │  │ │
│  │  │  - Response formatting                              │  │ │
│  │  └────────────────────────────────────────────────────┘  │ │
│  └───────────────────────────────────────────────────────────┘ │
│                          │                                      │
│                          │ Database / Cache / Storage           │
│                          ▼                                      │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                  Data Layer                                │ │
│  │                                                            │ │
│  │  ┌──────────────┐  ┌──────────────┐                      │ │
│  │  │    MySQL     │  │    Redis     │                      │ │
│  │  │  (Business)  │  │ (Cache/Queue)│                      │ │
│  │  └──────────────┘  └──────────────┘                      │ │
│  │                                                            │ │
│  │  ┌──────────────┐  ┌──────────────┐                      │ │
│  │  │   AWS S3     │  │  CloudFront  │                      │ │
│  │  │ (File Store) │  │    (CDN)     │                      │ │
│  │  └──────────────┘  └──────────────┘                      │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                          │
                          │ MCP Protocol
                          ▼
                  ┌───────────────────┐
                  │  AI Orchestrator  │
                  │  (External)       │
                  └───────────────────┘
```


### Technology Stack

#### Frontend
- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript 5.x
- **Styling**: Tailwind CSS + Shadcn/ui components
- **AI Chat SDK**: Vercel AI SDK (`ai` package)
- **State Management**: Zustand or React Context
- **Charts**: Recharts or Tremor
- **HTTP Client**: Fetch API / Axios
- **WebSocket**: Native WebSocket API

#### Backend
- **Framework**: FastAPI (Python 3.12+)
- **Async Runtime**: asyncio + uvicorn
- **Task Queue**: Celery + Redis
- **Authentication**: JWT + OAuth 2.0 (Google, Facebook)
- **Payment**: Stripe SDK
- **MCP**: Custom MCP Server implementation
- **WebSocket**: FastAPI WebSocket support

#### Data Storage
- **Primary Database**: MySQL 8.4 (AWS RDS)
- **Cache**: Redis 7.x (AWS ElastiCache)
- **File Storage**: AWS S3
- **CDN**: AWS CloudFront

#### Infrastructure
- **Hosting**: AWS Singapore region
- **Compute**: ECS (Fargate)
- **Database**: RDS (Multi-AZ)
- **Cache**: ElastiCache (Redis)
- **Storage**: S3 + CloudFront
- **Monitoring**: CloudWatch + Sentry
- **CI/CD**: GitHub Actions


## Components and Interfaces

### Frontend Components

#### 1. Chat Window Component
```typescript
// components/chat/ChatWindow.tsx
interface ChatWindowProps {
  isOpen: boolean;
  onToggle: () => void;
}

// Uses Vercel AI SDK's useChat hook
const { messages, input, handleInputChange, handleSubmit, isLoading } = useChat({
  api: '/api/chat',
  onResponse: (response) => { /* handle streaming start */ },
  onFinish: (message) => { /* handle completion */ },
  onError: (error) => { /* handle errors */ }
});
```

##### 1.1 视频持久化机制（Video Persistence）

生成的视频通过 GCS Signed URL 机制实现持久化访问，确保页面刷新后视频仍可播放。

**Message 数据结构**：
```typescript
interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  createdAt?: Date;
  processInfo?: string;              // Agent 处理过程
  generatedImages?: GeneratedImage[]; // 生成的图片
  generatedVideoUrl?: string;        // 视频 Signed URL（临时）
  videoObjectName?: string;          // GCS 对象路径（持久化存储）
}
```

**持久化流程**：

1. **视频生成时**：后端返回 `video_object_name`（GCS 路径），前端调用 Signed URL API 获取 `generatedVideoUrl`
2. **存储到 localStorage**：Zustand `partialize` 保留 `videoObjectName`，剥离 base64 数据 URL
3. **页面刷新后**：检测有 `videoObjectName` 但无 `generatedVideoUrl` 的消息，重新获取 Signed URL

**实现代码**：
```typescript
// hooks/useChat.ts
// 获取 GCS Signed URL
const fetchSignedUrl = useCallback(async (objectName: string, messageId: string) => {
  const response = await fetch(`/api/media/signed-url/${encodeURIComponent(objectName)}`);
  const data = await response.json();
  setMessages(prev =>
    prev.map(msg =>
      msg.id === messageId
        ? { ...msg, generatedVideoUrl: data.signed_url }
        : msg
    )
  );
}, []);

// 页面加载时恢复视频 URL
useEffect(() => {
  const storedMessages = useChatStore.getState().messages;
  if (storedMessages.length > 0 && messages.length === 0) {
    const loadedMessages = storedMessages as Message[];
    setMessages(loadedMessages);
    // Re-fetch signed URLs for messages with videoObjectName
    loadedMessages.forEach((msg) => {
      if (msg.videoObjectName && !msg.generatedVideoUrl) {
        fetchSignedUrl(msg.videoObjectName, msg.id);
      }
    });
  }
}, [messages.length, fetchSignedUrl]);
```

**Zustand Store 配置**：
```typescript
// lib/store.ts
persist(
  (set, get) => ({ /* state */ }),
  {
    name: 'chat-storage',
    partialize: (state) => ({
      messages: state.messages.map((msg) => ({
        ...msg,
        // 剥离 base64 数据 URL，保留 videoObjectName
        generatedVideoUrl: msg.generatedVideoUrl?.startsWith('data:')
          ? undefined
          : msg.generatedVideoUrl,
        // 剥离图片 base64 数据
        generatedImages: msg.generatedImages?.map((img) => ({
          ...img,
          data_b64: undefined,
        })),
      })),
    }),
  }
)
```

#### 2. Dashboard Component
```typescript
// app/dashboard/page.tsx
interface DashboardProps {
  metrics: {
    today: MetricsSummary;
    yesterday: MetricsSummary;
    trend: TrendData[];
  };
  suggestions: AISuggestion[];
}
```

#### 3. Creative Library Component
```typescript
// app/creatives/page.tsx
interface CreativeLibraryProps {
  creatives: Creative[];
  filters: CreativeFilters;
  onFilter: (filters: CreativeFilters) => void;
  onDelete: (id: string) => void;
}
```

### Backend API Endpoints

#### Authentication Endpoints
```python
GET    /api/v1/auth/oauth/google      # Google OAuth redirect
POST   /api/v1/auth/oauth/callback    # OAuth callback handler
POST   /api/v1/auth/logout            # User logout
POST   /api/v1/auth/refresh           # Refresh JWT token
```

#### User Management Endpoints
```python
GET    /api/v1/users/me               # Get current user info
PUT    /api/v1/users/me               # Update user profile
DELETE /api/v1/users/me               # Delete user account
GET    /api/v1/users/me/export        # Export user data (GDPR)
```

#### Ad Account Endpoints
```python
GET    /api/v1/ad-accounts            # List ad accounts
POST   /api/v1/ad-accounts            # Bind new ad account
GET    /api/v1/ad-accounts/{id}       # Get ad account details
PUT    /api/v1/ad-accounts/{id}       # Update ad account
DELETE /api/v1/ad-accounts/{id}       # Unbind ad account
POST   /api/v1/ad-accounts/{id}/refresh # Refresh OAuth token
```

#### Credit & Billing Endpoints
```python
GET    /api/v1/credits/balance        # Get credit balance
GET    /api/v1/credits/history        # Get credit history
POST   /api/v1/credits/recharge       # Create recharge order (Stripe payment)
GET    /api/v1/credits/packages       # List available credit packages
# Note: Credit config management is admin-only, not exposed via public API
```

#### Creative Management Endpoints
```python
GET    /api/v1/creatives              # List creatives
POST   /api/v1/creatives              # Create creative
GET    /api/v1/creatives/{id}         # Get creative details
PUT    /api/v1/creatives/{id}         # Update creative
DELETE /api/v1/creatives/{id}         # Delete creative
POST   /api/v1/creatives/upload-url   # Get S3 upload URL
```

#### Report Data Endpoints
```python
GET    /api/v1/reports                # Get report data
GET    /api/v1/reports/metrics        # Get metrics
POST   /api/v1/reports/metrics        # Save metrics
GET    /api/v1/reports/summary        # Get summary
```

#### Landing Page Endpoints
```python
GET    /api/v1/landing-pages          # List landing pages
POST   /api/v1/landing-pages          # Create landing page
GET    /api/v1/landing-pages/{id}     # Get landing page
PUT    /api/v1/landing-pages/{id}     # Update landing page
DELETE /api/v1/landing-pages/{id}     # Delete landing page
POST   /api/v1/landing-pages/{id}/publish # Publish to S3
```

#### Campaign Management Endpoints
```python
GET    /api/v1/campaigns              # List campaigns
POST   /api/v1/campaigns              # Create campaign
GET    /api/v1/campaigns/{id}         # Get campaign details
PUT    /api/v1/campaigns/{id}         # Update campaign
DELETE /api/v1/campaigns/{id}         # Delete campaign
```

#### Notification Endpoints
```python
GET    /api/v1/notifications          # List notifications
GET    /api/v1/notifications/unread   # Get unread count
PUT    /api/v1/notifications/{id}/read # Mark as read
PUT    /api/v1/notifications/read-all # Mark all as read
```

#### WebSocket Endpoint
```python
WS     /ws/chat                       # WebSocket chat connection
```

#### MCP Server Endpoint
```python
POST   /mcp/v1/tools                  # List available tools
POST   /mcp/v1/execute                # Execute tool
```


## Data Models

### User Model
```python
class User(Base):
    __tablename__ = "users"
    
    id: int = Column(BigInteger, primary_key=True, autoincrement=True)
    email: str = Column(String(255), unique=True, nullable=False)
    display_name: str = Column(String(255), nullable=False)
    avatar_url: str = Column(String(512), nullable=True)
    
    # OAuth (Google only)
    oauth_provider: str = Column(String(50), default='google')
    oauth_id: str = Column(String(255), nullable=False, unique=True)
    
    # Credits
    gifted_credits: Decimal = Column(Numeric(10, 2), default=500)
    purchased_credits: Decimal = Column(Numeric(10, 2), default=0)
    
    # Settings
    language: str = Column(String, default='en')
    timezone: str = Column(String, default='UTC')
    notification_preferences: JSON = Column(JSON, default={})
    
    # Metadata
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    updated_at: datetime = Column(DateTime, onupdate=datetime.utcnow)
    last_login_at: datetime = Column(DateTime, nullable=True)
    
    # Relationships
    ad_accounts = relationship("AdAccount", back_populates="user")
    creatives = relationship("Creative", back_populates="user")
    campaigns = relationship("Campaign", back_populates="user")
    landing_pages = relationship("LandingPage", back_populates="user")
```

### Ad Account Model
```python
class AdAccount(Base):
    __tablename__ = "ad_accounts"
    
    id: int = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id: int = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    
    # Platform info
    platform: str = Column(String, nullable=False)  # 'meta', 'tiktok', 'google'
    platform_account_id: str = Column(String, nullable=False)
    account_name: str = Column(String, nullable=False)
    
    # OAuth tokens (encrypted)
    access_token_encrypted: str = Column(Text, nullable=False)
    refresh_token_encrypted: str = Column(Text, nullable=True)
    token_expires_at: datetime = Column(DateTime, nullable=True)
    
    # Status
    status: str = Column(String, default='active')  # 'active', 'expired', 'revoked'
    is_active: bool = Column(Boolean, default=False)  # Currently selected account
    
    # Metadata
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    updated_at: datetime = Column(DateTime, onupdate=datetime.utcnow)
    last_synced_at: datetime = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="ad_accounts")
```

### Creative Model
```python
class Creative(Base):
    __tablename__ = "creatives"
    
    id: int = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id: int = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    
    # File info
    file_url: str = Column(String, nullable=False)  # S3 URL
    cdn_url: str = Column(String, nullable=False)   # CloudFront URL
    file_type: str = Column(String, nullable=False)  # 'image', 'video'
    file_size: int = Column(Integer, nullable=False)  # bytes
    
    # Metadata
    product_url: str = Column(String, nullable=True)
    style: str = Column(String, nullable=True)
    score: float = Column(Float, nullable=True)  # AI quality score
    tags: List[str] = Column(ARRAY(String), default=[])
    
    # Status
    status: str = Column(String, default='active')  # 'active', 'deleted'
    
    # Timestamps
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    updated_at: datetime = Column(DateTime, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="creatives")
```

### Campaign Model
```python
class Campaign(Base):
    __tablename__ = "campaigns"
    
    id: int = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id: int = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    ad_account_id: int = Column(BigInteger, ForeignKey("ad_accounts.id"), nullable=False)
    
    # Platform info
    platform: str = Column(String, nullable=False)
    platform_campaign_id: str = Column(String, nullable=True)  # ID from ad platform
    
    # Campaign data
    name: str = Column(String, nullable=False)
    objective: str = Column(String, nullable=False)
    status: str = Column(String, default='draft')  # 'draft', 'active', 'paused', 'deleted'
    
    # Budget
    budget: Decimal = Column(Numeric(10, 2), nullable=False)
    budget_type: str = Column(String, default='daily')  # 'daily', 'lifetime'
    
    # Targeting
    targeting: JSON = Column(JSON, default={})
    
    # Creative IDs
    creative_ids: List[int] = Column(JSON, default=[])  # Store as JSON array of integers
    landing_page_id: int = Column(BigInteger, ForeignKey("landing_pages.id"), nullable=True)
    
    # Timestamps
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    updated_at: datetime = Column(DateTime, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="campaigns")
    ad_account = relationship("AdAccount")
    landing_page = relationship("LandingPage")
```

### Landing Page Model
```python
class LandingPage(Base):
    __tablename__ = "landing_pages"
    
    id: int = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id: int = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    
    # Page info
    name: str = Column(String, nullable=False)
    url: str = Column(String, nullable=False)  # Public URL
    s3_key: str = Column(String, nullable=False)  # S3 object key
    
    # Content
    product_url: str = Column(String, nullable=False)
    template: str = Column(String, default='modern')
    language: str = Column(String, default='en')
    html_content: str = Column(Text, nullable=True)
    
    # Status
    status: str = Column(String, default='draft')  # 'draft', 'published', 'archived'
    
    # Timestamps
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    updated_at: datetime = Column(DateTime, onupdate=datetime.utcnow)
    published_at: datetime = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="landing_pages")
```

### Report Metrics Model
```python
class ReportMetrics(Base):
    __tablename__ = "report_metrics"
    
    id: int = Column(BigInteger, primary_key=True, autoincrement=True)
    timestamp: datetime = Column(DateTime, nullable=False, index=True)
    user_id: int = Column(BigInteger, nullable=False, index=True)
    ad_account_id: int = Column(BigInteger, nullable=False, index=True)
    
    # Entity info
    entity_type: str = Column(String, nullable=False)  # 'campaign', 'adset', 'ad'
    entity_id: str = Column(String, nullable=False, index=True)
    entity_name: str = Column(String, nullable=False)
    
    # Metrics
    impressions: int = Column(Integer, default=0)
    clicks: int = Column(Integer, default=0)
    spend: Decimal = Column(Numeric(10, 2), default=0)
    conversions: int = Column(Integer, default=0)
    revenue: Decimal = Column(Numeric(10, 2), default=0)
    
    # Calculated metrics
    ctr: float = Column(Float, default=0)  # Click-through rate
    cpc: Decimal = Column(Numeric(10, 2), default=0)  # Cost per click
    cpa: Decimal = Column(Numeric(10, 2), default=0)  # Cost per acquisition
    roas: float = Column(Float, default=0)  # Return on ad spend
    
    # Metadata
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
```

### Credit Transaction Model
```python
class CreditTransaction(Base):
    __tablename__ = "credit_transactions"
    
    id: int = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id: int = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    
    # Transaction info
    type: str = Column(String, nullable=False)  # 'deduct', 'refund', 'recharge', 'gift'
    amount: Decimal = Column(Numeric(10, 2), nullable=False)
    
    # Source tracking
    from_gifted: Decimal = Column(Numeric(10, 2), default=0)
    from_purchased: Decimal = Column(Numeric(10, 2), default=0)
    
    # Balance after transaction
    balance_after: Decimal = Column(Numeric(10, 2), nullable=False)
    
    # Operation details
    operation_type: str = Column(String, nullable=True)  # 'generate_creative', 'chat', etc.
    operation_id: str = Column(String, nullable=True)
    details: JSON = Column(JSON, default={})  # Model, tokens, etc.
    
    # Metadata
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User")
```

### Notification Model
```python
class Notification(Base):
    __tablename__ = "notifications"
    
    id: int = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id: int = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    
    # Notification info
    type: str = Column(String, nullable=False)  # 'urgent', 'important', 'general'
    category: str = Column(String, nullable=False)  # 'ad_rejected', 'token_expired', etc.
    title: str = Column(String, nullable=False)
    message: str = Column(Text, nullable=False)
    
    # Action
    action_url: str = Column(String, nullable=True)
    action_text: str = Column(String, nullable=True)
    
    # Status
    is_read: bool = Column(Boolean, default=False)
    read_at: datetime = Column(DateTime, nullable=True)
    
    # Channels
    sent_via: List[str] = Column(ARRAY(String), default=[])  # ['in_app', 'email']
    
    # Metadata
    metadata: JSON = Column(JSON, default={})
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User")
```

### Credit Config Model
```python
class CreditConfig(Base):
    __tablename__ = "credit_config"
    
    id: int = Column(BigInteger, primary_key=True, autoincrement=True)
    
    # Model rates (per 1K tokens)
    gemini_flash_input_rate: Decimal = Column(Numeric(10, 4), default=0.01)
    gemini_flash_output_rate: Decimal = Column(Numeric(10, 4), default=0.04)
    gemini_pro_input_rate: Decimal = Column(Numeric(10, 4), default=0.05)
    gemini_pro_output_rate: Decimal = Column(Numeric(10, 4), default=0.2)
    
    # Operation rates (fixed)
    image_generation_rate: Decimal = Column(Numeric(10, 2), default=0.5)
    video_generation_rate: Decimal = Column(Numeric(10, 2), default=5)
    landing_page_rate: Decimal = Column(Numeric(10, 2), default=15)
    competitor_analysis_rate: Decimal = Column(Numeric(10, 2), default=10)
    optimization_suggestion_rate: Decimal = Column(Numeric(10, 2), default=20)
    
    # Registration bonus
    registration_bonus: Decimal = Column(Numeric(10, 2), default=500)
    
    # Credit packages
    packages: JSON = Column(JSON, default={})
    
    # Metadata
    updated_at: datetime = Column(DateTime, onupdate=datetime.utcnow)
    updated_by: str = Column(String, nullable=True)
```


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: OAuth Login Creates or Retrieves User
*For any* valid OAuth token from Google, the system should either create a new user account or retrieve an existing one, and the user should be successfully authenticated.
**Validates: Requirements 1.1**

### Property 2: OAuth Token Encryption Round Trip
*For any* OAuth access token, encrypting then decrypting should produce the original token value.
**Validates: Requirements 2.2**

### Property 3: Token Refresh Before Expiry
*For any* ad account with a token expiring within 24 hours, the system should attempt to refresh the token automatically.
**Validates: Requirements 2.1.1, 2.3**

### Property 4: Token Refresh Failure Triggers Notifications
*For any* ad account where token refresh fails, the system should pause all operations using that account, display a warning banner, and send both email and in-app notifications.
**Validates: Requirements 2.1.2, 2.1.3, 2.1.4**

### Property 5: New User Registration Credit Grant
*For any* newly registered user, the system should automatically grant the configured registration bonus credits (default 500) to their gifted_credits balance.
**Validates: Requirements 3.1**

### Property 6: Credit Balance Display Accuracy
*For any* user, the displayed credit balance should equal the sum of gifted_credits and purchased_credits.
**Validates: Requirements 3.2**

### Property 7: Credit Deduction Order
*For any* credit deduction operation, the system should first deduct from gifted_credits, and only deduct from purchased_credits when gifted_credits is exhausted.
**Validates: Requirements 13.5**

### Property 8: Insufficient Credit Error
*For any* operation requiring credits, if the user's total available credits are less than required, the system should return error code 6011 and not execute the operation.
**Validates: Requirements 3.4, 13.3**

### Property 9: Credit Deduction Atomicity
*For any* credit deduction operation, either all changes (balance update, transaction record) succeed together, or all fail together with no partial state.
**Validates: Requirements 13.3.4**

### Property 10: Credit Config Changes Non-Retroactive
*For any* credit configuration change, the new rates should apply only to operations after the change timestamp, not to historical transactions.
**Validates: Requirements 3.5, 3.3.4**

### Property 11: Credit Transaction Logging
*For any* credit deduction or refund, the system should create a transaction record with timestamp, amount, operation type, and balance after transaction.
**Validates: Requirements 13.1.1**

### Property 12: Dashboard Metrics Display
*For any* user with ad accounts, the dashboard should display today's and yesterday's core metrics (spend, ROAS, CPA) and 7-day trend data.
**Validates: Requirements 4.2, 4.3, 4.4**

### Property 13: WebSocket Connection Establishment
*For any* valid user session, opening the chat window should establish a WebSocket connection and display connection status.
**Validates: Requirements 4.1.3, 12.1.1**

### Property 14: WebSocket Heartbeat Mechanism
*For any* active WebSocket connection, the system should send ping messages every 30 seconds and consider the connection dead if no pong is received within 60 seconds.
**Validates: Requirements 12.1.2**

### Property 15: WebSocket Auto-Reconnect
*For any* disconnected WebSocket, the system should attempt to reconnect up to 3 times using exponential backoff (1s, 2s, 4s).
**Validates: Requirements 12.1.3**

### Property 16: WebSocket Message Queue Preservation
*For any* messages sent during disconnection, the system should queue up to 10 messages and send them upon successful reconnection.
**Validates: Requirements 12.1.4**

### Property 17: S3 File Upload Round Trip
*For any* creative file uploaded to S3, the system should store both the S3 URL and CloudFront CDN URL, and both should be accessible.
**Validates: Requirements 7.2**

### Property 18: Creative Deletion Cascades to Storage
*For any* creative deletion, the system should delete both the database record and the S3 file.
**Validates: Requirements 7.5**

### Property 19: Report Metrics Storage
*For any* metrics data from ad platforms, the system should store it in MySQL with timestamp, user_id, and entity_id properly indexed.
**Validates: Requirements 8.1**

### Property 20: Report Data Archival
*For any* metrics data older than 90 days, the system should automatically archive it to summary tables.
**Validates: Requirements 8.4**

### Property 21: Landing Page S3 and CloudFront Deployment
*For any* published landing page, the system should upload HTML to S3 and configure CloudFront distribution.
**Validates: Requirements 9.2**

### Property 22: Campaign Platform Sync
*For any* campaign modification, the system should update both the local database and sync changes to the ad platform API.
**Validates: Requirements 10.3**

### Property 23: MCP Tool Authentication
*For any* MCP tool invocation, the system should verify the caller's service token before execution.
**Validates: Requirements 12.2**

### Property 24: MCP Tool Execution Result Format
*For any* successful MCP tool execution, the system should return a response with status "success" and the requested data.
**Validates: Requirements 12.3**

### Property 25: MCP Tool Execution Error Format
*For any* failed MCP tool execution, the system should return a response with status "error", error code, and error message.
**Validates: Requirements 12.4**

### Property 26: Notification Creation Multi-Channel
*For any* urgent notification, the system should send it via both in-app and email channels regardless of user preferences.
**Validates: Requirements 16.2.1, 16.1.5**

### Property 27: Notification Read Status Update
*For any* notification clicked by a user, the system should mark it as read and record the read timestamp.
**Validates: Requirements 16.4**

### Property 28: Data Export Completeness
*For any* user data export request, the generated ZIP file should contain all user data categories: profile, ad accounts, credits, creatives, landing pages, campaigns, and reports.
**Validates: Requirements 5.1.2**

### Property 29: Data Export Link Expiration
*For any* generated data export file, the download link should expire after 24 hours.
**Validates: Requirements 5.1.3**

### Property 30: Account Deletion Completeness
*For any* account deletion request, the system should delete all user data from database and S3, then log out the user session.
**Validates: Requirements 5.2.3, 5.2.4**

### Property 31: Account Deletion Rollback on Failure
*For any* account deletion that fails partway through, the system should rollback all changes and notify the user.
**Validates: Requirements 5.2.5**

### Property 32: Celery Task Retry on Failure
*For any* failed Celery task, the system should retry up to 3 times before marking it as permanently failed.
**Validates: Requirements 12.2.5**

### Property 33: Credit Balance Warning Threshold
*For any* user whose credit balance falls below 50, the system should display a balance warning in the UI.
**Validates: Requirements 13.2.1**

### Property 34: Credit Balance Critical Notification
*For any* user whose credit balance falls below 10, the system should send email and in-app notifications.
**Validates: Requirements 13.2.2**

### Property 35: Credit Pre-Deduction and Adjustment
*For any* MCP tool call, the system should pre-deduct estimated credits, then adjust (refund or additional deduct) based on actual consumption after completion.
**Validates: Requirements 13.3.1, 13.3.2**

### Property 36: Credit Refund on Operation Failure
*For any* operation that fails after credit pre-deduction, the system should refund the full pre-deducted amount.
**Validates: Requirements 13.3.3**


## Error Handling

### Error Response Format

All API endpoints and MCP tools should return errors in a consistent format:

```json
{
  "status": "error",
  "error": {
    "code": "6011",
    "type": "INSUFFICIENT_CREDITS",
    "message": "Credit balance insufficient",
    "details": {
      "required_credits": 20,
      "available_credits": 5,
      "recharge_url": "/billing/recharge"
    },
    "timestamp": "2024-11-26T10:00:15Z",
    "request_id": "req_123456"
  }
}
```

### Error Categories

#### Authentication Errors (1xxx)
- 1002: UNAUTHORIZED - Invalid or expired JWT token
- 1004: FORBIDDEN - Insufficient permissions

#### WebSocket Errors (2xxx)
- 2000: CONNECTION_FAILED - WebSocket connection failed
- 2003: CONNECTION_TIMEOUT - Connection timeout
- 2004: HEARTBEAT_TIMEOUT - Heartbeat timeout

#### MCP Errors (3xxx)
- 3001: MCP_TOOL_NOT_FOUND - Tool not found
- 3002: MCP_INVALID_PARAMETERS - Invalid parameters
- 3003: MCP_EXECUTION_FAILED - Execution failed

#### Data Errors (5xxx)
- 5000: DATA_NOT_FOUND - Resource not found
- 5002: DATABASE_ERROR - Database operation failed
- 5003: STORAGE_ERROR - S3 upload/download failed

#### Business Logic Errors (6xxx)
- 6000: AD_ACCOUNT_NOT_BOUND - No ad account bound
- 6001: AD_ACCOUNT_TOKEN_EXPIRED - OAuth token expired
- 6011: INSUFFICIENT_CREDITS - Credit balance insufficient
- 6012: CREDIT_DEDUCTION_FAILED - Credit deduction failed

### Error Handling Strategies

#### Retry Logic
```python
async def retry_with_backoff(func, max_retries=3):
    """Exponential backoff retry for transient failures"""
    for attempt in range(max_retries):
        try:
            return await func()
        except RetryableError as e:
            if attempt == max_retries - 1:
                raise
            wait_time = 2 ** attempt  # 1s, 2s, 4s
            await asyncio.sleep(wait_time)
            logger.warning(f"Retry attempt {attempt + 1}/{max_retries}")
```

#### Transaction Rollback
```python
async def deduct_credit_with_rollback(user_id: str, amount: Decimal):
    """Atomic credit deduction with rollback on failure"""
    async with db.transaction():
        try:
            # Deduct credit
            user = await update_credit_balance(user_id, -amount)
            # Record transaction
            await create_transaction_record(user_id, amount)
            return user
        except Exception as e:
            # Automatic rollback on exception
            logger.error(f"Credit deduction failed: {e}")
            raise CreditDeductionError("Failed to deduct credits")
```

#### Graceful Degradation
```python
async def get_dashboard_metrics(user_id: str):
    """Get dashboard metrics with fallback"""
    try:
        # Try to get real-time data
        return await fetch_realtime_metrics(user_id)
    except Exception as e:
        logger.warning(f"Real-time metrics failed: {e}")
        # Fall back to cached data
        return await get_cached_metrics(user_id)
```


## Testing Strategy

### Dual Testing Approach

The Web Platform will use both unit testing and property-based testing to ensure comprehensive coverage:

- **Unit tests** verify specific examples, edge cases, and integration points
- **Property tests** verify universal properties that should hold across all inputs
- Together they provide comprehensive coverage: unit tests catch concrete bugs, property tests verify general correctness

### Unit Testing

#### Framework
- **Python Backend**: pytest + pytest-asyncio
- **TypeScript Frontend**: Jest + React Testing Library

#### Coverage Areas
- API endpoint request/response handling
- Database CRUD operations
- Authentication and authorization flows
- Credit calculation logic
- File upload/download operations
- WebSocket connection handling
- MCP tool execution

#### Example Unit Tests
```python
# tests/test_credit_service.py
async def test_deduct_credit_success():
    """Test successful credit deduction"""
    user = await create_test_user(gifted_credits=100)
    result = await credit_service.deduct_credit(user.id, 20)
    assert result.balance_after == 80
    assert result.from_gifted == 20

async def test_deduct_credit_insufficient():
    """Test credit deduction with insufficient balance"""
    user = await create_test_user(gifted_credits=5)
    with pytest.raises(InsufficientCreditsError):
        await credit_service.deduct_credit(user.id, 20)

async def test_oauth_token_encryption_decryption():
    """Test OAuth token encryption round trip"""
    original_token = "test_access_token_12345"
    encrypted = encrypt_token(original_token)
    decrypted = decrypt_token(encrypted)
    assert decrypted == original_token
```

### Property-Based Testing

#### Framework
- **Python**: Hypothesis

#### Property Test Configuration
- Minimum 100 iterations per property test
- Each property test must reference the design document property number
- Tag format: `# Property {number}: {property_text}`

#### Example Property Tests
```python
# tests/property_tests/test_credit_properties.py
from hypothesis import given, strategies as st

@given(
    gifted=st.decimals(min_value=0, max_value=10000, places=2),
    purchased=st.decimals(min_value=0, max_value=100000, places=2)
)
@settings(max_examples=100)
async def test_property_6_credit_balance_accuracy(gifted, purchased):
    """
    Property 6: Credit Balance Display Accuracy
    For any user, displayed balance should equal gifted + purchased
    """
    user = await create_test_user(
        gifted_credits=gifted,
        purchased_credits=purchased
    )
    balance = await credit_service.get_balance(user.id)
    assert balance.total_available == gifted + purchased

@given(
    initial_gifted=st.decimals(min_value=50, max_value=1000, places=2),
    initial_purchased=st.decimals(min_value=0, max_value=5000, places=2),
    deduct_amount=st.decimals(min_value=1, max_value=100, places=2)
)
@settings(max_examples=100)
async def test_property_7_credit_deduction_order(
    initial_gifted, initial_purchased, deduct_amount
):
    """
    Property 7: Credit Deduction Order
    For any deduction, should deduct from gifted first, then purchased
    """
    user = await create_test_user(
        gifted_credits=initial_gifted,
        purchased_credits=initial_purchased
    )
    
    result = await credit_service.deduct_credit(user.id, deduct_amount)
    
    if deduct_amount <= initial_gifted:
        # Should only deduct from gifted
        assert result.from_gifted == deduct_amount
        assert result.from_purchased == 0
    else:
        # Should deduct all gifted, then from purchased
        assert result.from_gifted == initial_gifted
        assert result.from_purchased == deduct_amount - initial_gifted

@given(
    token=st.text(min_size=10, max_size=500)
)
@settings(max_examples=100)
def test_property_2_oauth_token_round_trip(token):
    """
    Property 2: OAuth Token Encryption Round Trip
    For any token, encrypt then decrypt should return original
    """
    encrypted = encrypt_token(token)
    decrypted = decrypt_token(encrypted)
    assert decrypted == token

@given(
    user_data=st.fixed_dictionaries({
        'email': st.emails(),
        'display_name': st.text(min_size=1, max_size=100),
        'oauth_provider': st.just('google'),
        'oauth_id': st.text(min_size=10, max_size=100)
    })
)
@settings(max_examples=100)
async def test_property_1_oauth_login_creates_or_retrieves(user_data):
    """
    Property 1: OAuth Login Creates or Retrieves User
    For any valid Google OAuth data, should create new or retrieve existing user
    """
    # First login - should create
    user1 = await auth_service.oauth_login(user_data)
    assert user1.email == user_data['email']
    assert user1.oauth_provider == 'google'
    
    # Second login - should retrieve same user
    user2 = await auth_service.oauth_login(user_data)
    assert user2.id == user1.id

@given(
    files=st.lists(
        st.fixed_dictionaries({
            'name': st.text(min_size=1, max_size=100),
            'content': st.binary(min_size=100, max_size=10000),
            'type': st.sampled_from(['image/jpeg', 'image/png'])
        }),
        min_size=1,
        max_size=10
    )
)
@settings(max_examples=100)
async def test_property_17_s3_upload_round_trip(files):
    """
    Property 17: S3 File Upload Round Trip
    For any file uploaded to S3, both S3 and CDN URLs should be accessible
    """
    user = await create_test_user()
    
    for file_data in files:
        # Upload file
        creative = await creative_service.create_creative(
            user_id=user.id,
            file_name=file_data['name'],
            file_content=file_data['content'],
            file_type=file_data['type']
        )
        
        # Verify S3 URL is accessible
        s3_response = await http_client.head(creative.file_url)
        assert s3_response.status_code == 200
        
        # Verify CDN URL is accessible
        cdn_response = await http_client.head(creative.cdn_url)
        assert cdn_response.status_code == 200
```

### Integration Testing

#### Test Scenarios
1. **End-to-End User Flow**: Google OAuth login → Ad account binding → Credit recharge → Creative generation
2. **WebSocket Communication**: Connect → Send message → Receive streaming response → Disconnect
3. **MCP Tool Invocation**: AI Orchestrator calls MCP tool → Web Platform executes → Returns result
4. **Credit Lifecycle**: Recharge → Deduct → Refund → Balance verification
5. **Token Refresh Flow**: Token expires → Auto refresh → Failure → User notification

### Performance Testing

#### Load Testing
- **Tool**: Locust
- **Scenarios**:
  - 10 concurrent users (MVP target)
  - Dashboard page load < 5 seconds
  - API response time < 2 seconds
  - WebSocket message latency < 100ms

#### Stress Testing
- Test system behavior under:
  - High concurrent WebSocket connections
  - Rapid credit deduction operations
  - Large file uploads to S3
  - Database connection pool exhaustion

### Security Testing

#### Test Areas
1. **Authentication**: JWT token validation, expiration handling
2. **Authorization**: Permission checks for all protected endpoints
3. **Encryption**: OAuth token encryption/decryption
4. **Input Validation**: SQL injection, XSS prevention
5. **Rate Limiting**: API rate limit enforcement


## Security Considerations

### Authentication & Authorization

#### JWT Token Management
- Access token expiration: 1 hour
- Refresh token expiration: 30 days
- Token rotation on refresh
- Secure HTTP-only cookies for web clients

#### OAuth Integration
- Support for Google OAuth 2.0 only (no traditional registration)
- PKCE (Proof Key for Code Exchange) for enhanced security
- State parameter validation to prevent CSRF
- Encrypted storage of OAuth tokens using AES-256

### Data Protection

#### Encryption at Rest
- OAuth tokens: AES-256 encryption
- Sensitive user data: Database-level encryption
- S3 files: Server-side encryption (SSE-S3)

#### Encryption in Transit
- HTTPS/TLS 1.3 for all API communications
- WSS (WebSocket Secure) for chat connections
- Certificate pinning for mobile clients (future)

### API Security

#### Rate Limiting
```python
# Per-user rate limits
RATE_LIMITS = {
    "api": "100/minute",
    "websocket": "50/minute",
    "mcp": "200/minute",
    "upload": "10/minute"
}
```

#### Input Validation
- Pydantic models for request validation
- SQL injection prevention via parameterized queries
- XSS prevention via output encoding
- File upload validation (type, size, content)

#### CORS Configuration
```python
CORS_SETTINGS = {
    "allow_origins": ["https://aae.com", "https://app.aae.com"],
    "allow_credentials": True,
    "allow_methods": ["GET", "POST", "PUT", "DELETE"],
    "allow_headers": ["Authorization", "Content-Type"]
}
```

### GDPR Compliance

#### Data Subject Rights
1. **Right to Access**: User can export all their data
2. **Right to Erasure**: User can delete their account and all data
3. **Right to Rectification**: User can update their personal information
4. **Right to Data Portability**: Export data in machine-readable format (JSON/CSV)

#### Data Retention
- Active user data: Retained indefinitely
- Deleted user data: Permanently deleted within 30 days
- Audit logs: Retained for 90 days
- Backup data: Encrypted, retained for 30 days

#### Cookie Consent
- Display cookie consent banner on first visit
- Allow users to manage cookie preferences
- Essential cookies only without consent
- Analytics/marketing cookies require explicit consent

### Audit Logging

#### Logged Events
```python
AUDIT_EVENTS = [
    "user.login",
    "user.logout",
    "user.delete",
    "ad_account.bind",
    "ad_account.unbind",
    "credit.recharge",
    "credit.deduct",
    "creative.create",
    "creative.delete",
    "campaign.create",
    "campaign.update",
    "config.update"
]
```

#### Log Format
```json
{
  "event": "credit.deduct",
  "user_id": "user_123",
  "timestamp": "2024-11-26T10:00:00Z",
  "ip_address": "192.168.1.1",
  "user_agent": "Mozilla/5.0...",
  "details": {
    "amount": 20,
    "operation": "generate_creative",
    "balance_before": 100,
    "balance_after": 80
  }
}
```

## Deployment Architecture

### AWS Infrastructure

```
┌─────────────────────────────────────────────────────────────┐
│                     AWS Singapore Region                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              CloudFront (CDN)                        │   │
│  │  - Static assets                                     │   │
│  │  - Creative files                                    │   │
│  │  - Landing pages                                     │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                   │
│                          ▼                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │         Application Load Balancer (ALB)             │   │
│  │  - SSL termination                                   │   │
│  │  - Health checks                                     │   │
│  │  - Request routing                                   │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                   │
│         ┌────────────────┴────────────────┐                 │
│         ▼                                  ▼                 │
│  ┌──────────────┐                  ┌──────────────┐        │
│  │  ECS Fargate │                  │  ECS Fargate │        │
│  │  (Frontend)  │                  │  (Backend)   │        │
│  │              │                  │              │        │
│  │  Next.js     │                  │  FastAPI     │        │
│  │  Container   │                  │  Container   │        │
│  └──────────────┘                  └──────────────┘        │
│                                            │                 │
│                          ┌─────────────────┴─────────┐      │
│                          ▼                           ▼      │
│                  ┌──────────────┐          ┌──────────────┐│
│                  │     RDS      │          │ ElastiCache  ││
│                  │    MySQL     │          │    Redis     ││
│                  │  (Multi-AZ)  │          │              ││
│                  └──────────────┘          └──────────────┘│
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                    S3 Buckets                        │   │
│  │  - aae-creatives (private)                          │   │
│  │  - aae-landing-pages (public)                       │   │
│  │  - aae-exports (private, lifecycle: 7 days)         │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Container Configuration

#### Frontend Container (Next.js)
```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --production
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
```

#### Backend Container (FastAPI)
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Configuration

#### Development
- Single ECS task per service
- RDS: db.t3.micro (single AZ)
- ElastiCache: cache.t3.micro (single node)
- S3: Standard storage class

#### Production (MVP)
- Frontend: 2 ECS tasks (auto-scaling 2-4)
- Backend: 2 ECS tasks (auto-scaling 2-6)
- RDS: db.t3.medium (Multi-AZ)
- ElastiCache: cache.t3.small (2 nodes)
- S3: Intelligent-Tiering

### Monitoring & Observability

#### CloudWatch Metrics
- ECS task CPU/memory utilization
- ALB request count and latency
- RDS connections and query performance
- ElastiCache hit rate
- S3 request metrics

#### Application Metrics
```python
# Custom metrics to track
METRICS = [
    "api.request.duration",
    "api.request.count",
    "websocket.connections.active",
    "credit.deduction.count",
    "credit.deduction.amount",
    "mcp.tool.execution.duration",
    "mcp.tool.execution.count",
    "s3.upload.duration",
    "s3.upload.size"
]
```

#### Logging
- Application logs: CloudWatch Logs
- Access logs: ALB access logs to S3
- Audit logs: Dedicated CloudWatch log group
- Log retention: 30 days (application), 90 days (audit)

#### Error Tracking
- Sentry for error monitoring and alerting
- Error grouping and deduplication
- Release tracking for deployment correlation
- Performance monitoring for slow transactions

### Disaster Recovery

#### Backup Strategy
- RDS: Automated daily backups (retention: 7 days)
- RDS: Manual snapshots before major changes
- S3: Versioning enabled for critical buckets
- S3: Cross-region replication for disaster recovery

#### Recovery Objectives
- RTO (Recovery Time Objective): 4 hours
- RPO (Recovery Point Objective): 1 hour
- Database restore time: < 30 minutes
- Application redeployment: < 15 minutes


## Performance Optimization

### Caching Strategy

#### Redis Cache Layers
```python
CACHE_KEYS = {
    # User data (TTL: 5 minutes)
    "user:{user_id}": 300,
    "user:{user_id}:credits": 60,
    
    # Dashboard metrics (TTL: 1 minute)
    "dashboard:{user_id}:metrics": 60,
    "dashboard:{user_id}:trends": 300,
    
    # Creative library (TTL: 5 minutes)
    "creatives:{user_id}:list": 300,
    
    # Ad accounts (TTL: 10 minutes)
    "ad_accounts:{user_id}": 600,
    
    # Credit config (TTL: 1 hour)
    "credit:config": 3600,
    
    # Session data (TTL: 1 hour)
    "session:{session_id}": 3600
}
```

#### Cache Invalidation
```python
# Invalidate on write operations
async def update_user_credits(user_id: str, amount: Decimal):
    await db.update_credits(user_id, amount)
    # Invalidate cache
    await cache.delete(f"user:{user_id}:credits")
    await cache.delete(f"user:{user_id}")
```

### Database Optimization

#### Indexing Strategy
```sql
-- User lookups
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_oauth ON users(oauth_provider, oauth_id);

-- Ad account lookups
CREATE INDEX idx_ad_accounts_user ON ad_accounts(user_id);
CREATE INDEX idx_ad_accounts_platform ON ad_accounts(platform, platform_account_id);

-- Creative queries
CREATE INDEX idx_creatives_user ON creatives(user_id, created_at DESC);
CREATE INDEX idx_creatives_status ON creatives(user_id, status);

-- Campaign queries
CREATE INDEX idx_campaigns_user ON campaigns(user_id, created_at DESC);
CREATE INDEX idx_campaigns_ad_account ON campaigns(ad_account_id);

-- Report metrics
CREATE INDEX idx_metrics_user_time ON report_metrics(user_id, timestamp DESC);
CREATE INDEX idx_metrics_entity ON report_metrics(entity_type, entity_id, timestamp DESC);
CREATE INDEX idx_metrics_timestamp ON report_metrics(timestamp DESC);

-- Credit transactions
CREATE INDEX idx_credit_tx_user ON credit_transactions(user_id, created_at DESC);

-- Notifications
CREATE INDEX idx_notifications_user_unread ON notifications(user_id, is_read, created_at DESC);
```

#### Query Optimization
```python
# Use select_related for foreign keys
campaigns = await Campaign.objects.select_related(
    'user', 'ad_account', 'landing_page'
).filter(user_id=user_id)

# Use prefetch_related for many-to-many
users = await User.objects.prefetch_related(
    'ad_accounts', 'creatives'
).filter(id=user_id)

# Pagination for large result sets
async def get_creatives_paginated(user_id: str, limit: int, offset: int):
    return await Creative.objects.filter(
        user_id=user_id
    ).order_by('-created_at').limit(limit).offset(offset)
```

### API Performance

#### Response Compression
```python
# Enable gzip compression for API responses
app.add_middleware(
    GZipMiddleware,
    minimum_size=1000  # Only compress responses > 1KB
)
```

#### Connection Pooling
```python
# Database connection pool
DATABASE_POOL_CONFIG = {
    "min_size": 10,
    "max_size": 20,
    "max_queries": 50000,
    "max_inactive_connection_lifetime": 300
}

# Redis connection pool
REDIS_POOL_CONFIG = {
    "max_connections": 50,
    "socket_keepalive": True,
    "socket_keepalive_options": {
        socket.TCP_KEEPIDLE: 60,
        socket.TCP_KEEPINTVL: 10,
        socket.TCP_KEEPCNT: 3
    }
}
```

#### Async Operations
```python
# Use asyncio for concurrent operations
async def get_dashboard_data(user_id: str):
    # Fetch multiple data sources concurrently
    metrics, trends, suggestions = await asyncio.gather(
        get_metrics(user_id),
        get_trends(user_id),
        get_ai_suggestions(user_id)
    )
    return {
        "metrics": metrics,
        "trends": trends,
        "suggestions": suggestions
    }
```

### Frontend Performance

#### Code Splitting
```typescript
// Dynamic imports for route-based code splitting
const Dashboard = dynamic(() => import('@/app/dashboard/page'));
const Creatives = dynamic(() => import('@/app/creatives/page'));
const Reports = dynamic(() => import('@/app/reports/page'));
```

#### Image Optimization
```typescript
// Use Next.js Image component for automatic optimization
import Image from 'next/image';

<Image
  src={creative.cdn_url}
  alt={creative.name}
  width={400}
  height={300}
  loading="lazy"
  placeholder="blur"
/>
```

#### API Response Caching
```typescript
// Use SWR for client-side caching
import useSWR from 'swr';

function useCreatives() {
  const { data, error } = useSWR('/api/v1/creatives', fetcher, {
    revalidateOnFocus: false,
    dedupingInterval: 60000  // 1 minute
  });
  return { creatives: data, isLoading: !error && !data, error };
}
```

### File Upload Optimization

#### Multipart Upload for Large Files
```python
async def upload_large_file(file_path: str, bucket: str, key: str):
    """Use S3 multipart upload for files > 100MB"""
    file_size = os.path.getsize(file_path)
    
    if file_size > 100 * 1024 * 1024:  # 100MB
        # Multipart upload
        mpu = s3_client.create_multipart_upload(Bucket=bucket, Key=key)
        parts = []
        
        with open(file_path, 'rb') as f:
            part_number = 1
            while True:
                data = f.read(10 * 1024 * 1024)  # 10MB chunks
                if not data:
                    break
                    
                part = s3_client.upload_part(
                    Bucket=bucket,
                    Key=key,
                    PartNumber=part_number,
                    UploadId=mpu['UploadId'],
                    Body=data
                )
                parts.append({
                    'PartNumber': part_number,
                    'ETag': part['ETag']
                })
                part_number += 1
        
        s3_client.complete_multipart_upload(
            Bucket=bucket,
            Key=key,
            UploadId=mpu['UploadId'],
            MultipartUpload={'Parts': parts}
        )
    else:
        # Regular upload
        s3_client.upload_file(file_path, bucket, key)
```

#### Client-Side Compression
```typescript
// Compress images before upload
import imageCompression from 'browser-image-compression';

async function uploadCreative(file: File) {
  const options = {
    maxSizeMB: 1,
    maxWidthOrHeight: 1920,
    useWebWorker: true
  };
  
  const compressedFile = await imageCompression(file, options);
  
  // Get presigned URL
  const { upload_url } = await fetch('/api/v1/creatives/upload-url', {
    method: 'POST',
    body: JSON.stringify({
      file_name: file.name,
      file_type: file.type,
      file_size: compressedFile.size
    })
  }).then(r => r.json());
  
  // Upload to S3
  await fetch(upload_url, {
    method: 'PUT',
    body: compressedFile,
    headers: { 'Content-Type': file.type }
  });
}
```

## Scalability Considerations

### Horizontal Scaling

#### Stateless Application Design
- No session state stored in application memory
- All session data in Redis
- WebSocket connections can reconnect to any backend instance

#### Auto-Scaling Configuration
```yaml
# ECS Auto Scaling
AutoScalingTarget:
  MinCapacity: 2
  MaxCapacity: 10
  TargetCPUUtilization: 70%
  TargetMemoryUtilization: 80%
  ScaleInCooldown: 300  # 5 minutes
  ScaleOutCooldown: 60  # 1 minute
```

### Database Scaling

#### Read Replicas
- Create read replicas for read-heavy operations
- Route dashboard queries to read replicas
- Route report queries to read replicas
- Write operations always go to primary

#### Connection Pooling
```python
# PgBouncer for connection pooling
PGBOUNCER_CONFIG = {
    "pool_mode": "transaction",
    "max_client_conn": 1000,
    "default_pool_size": 25,
    "reserve_pool_size": 5,
    "reserve_pool_timeout": 3
}
```

### Cache Scaling

#### Redis Cluster
- Use Redis Cluster for horizontal scaling
- Shard data across multiple nodes
- Automatic failover with Sentinel

### CDN Optimization

#### CloudFront Configuration
```python
CLOUDFRONT_CONFIG = {
    "price_class": "PriceClass_200",  # US, Europe, Asia
    "default_ttl": 86400,  # 24 hours
    "max_ttl": 31536000,  # 1 year
    "compress": True,
    "viewer_protocol_policy": "redirect-to-https"
}
```

## Migration Strategy

### Phase 1: Infrastructure Setup (Week 1)
1. Set up AWS account and VPC
2. Create RDS PostgreSQL instance
3. Create ElastiCache Redis cluster
4. Create S3 buckets
5. Set up CloudFront distributions

### Phase 2: Core Backend (Week 2-3)
1. Implement Google OAuth authentication
2. Implement user management
3. Implement credit system
4. Set up database migrations
5. Implement MCP server

### Phase 3: Data Management (Week 3-4)
1. Implement creative management
2. Implement campaign management
3. Implement landing page management
4. Implement report data storage
5. Set up database indexes for metrics queries

### Phase 4: Frontend (Week 4-5)
1. Set up Next.js project
2. Implement Google OAuth login UI
3. Implement dashboard
4. Implement chat component (Vercel AI SDK)
5. Implement data management UIs

### Phase 5: Integration & Testing (Week 5-6)
1. Integrate with AI Orchestrator
2. End-to-end testing
3. Performance testing
4. Security testing
5. User acceptance testing

### Phase 6: Deployment & Launch (Week 6)
1. Production deployment
2. Monitoring setup
3. Documentation
4. User onboarding
5. Launch

