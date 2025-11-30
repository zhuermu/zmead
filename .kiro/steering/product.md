---
inclusion: always
---

# AAE Product Context

AAE (Automated Ad Engine) is an AI-powered advertising management platform where users manage ad operations through a conversational AI agent.

## Core Design Principle

**Chat-first UX** — Every feature MUST be accessible via natural language through the embedded AI chat (floating button, bottom-right). Dashboard pages are supplementary views only.

## Feature Domains

| Domain | Capabilities | Implementation Location |
|--------|--------------|------------------------|
| Chat Interface | Primary entry point; inline charts, cards, action buttons | `frontend/src/components/chat/`, `backend/app/api/v1/websocket.py` |
| Creative Generation | AI-generated ad creatives, competitor analysis, variant testing | `ai-orchestrator/app/modules/ad_creative/` |
| Performance Analytics | Real-time metrics, anomaly detection, recommendations | `ai-orchestrator/app/modules/ad_performance/` |
| Landing Pages | Automated generation, A/B testing, conversion tracking | `ai-orchestrator/app/modules/landing_page/` |
| Campaign Automation | Ad creation, budget optimization, rule-based automation | `ai-orchestrator/app/modules/campaign_automation/` |
| Market Intelligence | Competitor tracking, trend analysis, audience insights | `ai-orchestrator/app/modules/market_insights/` |

## Supported Ad Platforms

- **Meta Ads** (Facebook/Instagram) — Full support
- **TikTok Ads** — Full support
- **Google Ads** — Planned (do not implement yet)

## Critical Implementation Rules

### Chat-First Development
- **New features**: Always implement chat interface first, dashboard UI second
- **User requests**: If user asks for a dashboard feature, remind them it should also work via chat
- **Testing**: Verify features work through natural language commands before building UI

### Embedded Component Rendering
Chat messages can contain embedded components via metadata:
```typescript
// Message format from AI orchestrator
{
  type: "assistant",
  content: "Here are your campaign metrics:",
  metadata: {
    component: "chart" | "card" | "table" | "action_buttons",
    data: { /* component-specific data */ }
  }
}
```

Supported embedded types:
- `chart`: Performance trends, comparisons (uses Recharts)
- `card`: Metric summaries, creative previews
- `table`: Campaign lists, performance data
- `action_buttons`: Follow-up actions (e.g., "Approve", "Edit", "View Details")

### Confirmation Patterns
**Always require confirmation** for:
- Campaign creation/deletion
- Budget changes > 20%
- Ad account disconnection
- Bulk operations (pause/resume multiple campaigns)
- Credit purchases

Implementation: AI orchestrator returns `requires_confirmation: true` in metadata, frontend shows confirmation dialog.

### Credit System
Track credit usage for:
- AI creative generation (5 credits/image)
- Landing page generation (10 credits/page)
- Competitor analysis (3 credits/report)
- Performance insights (1 credit/query)

Deduct credits via `backend/app/services/credit.py` before executing operations.

## MCP Tool Development Guidelines

When creating/modifying MCP tools in `backend/app/mcp/tools/`:

### Required Parameters
```python
@mcp_tool
async def tool_name(
    user_id: str,  # Always required for authorization
    ad_account_id: str | None = None,  # Required if platform-specific
    # ... other params
) -> dict:
```

### Response Structure
```python
return {
    "success": bool,
    "data": {...},  # Structured data for chat rendering
    "metadata": {
        "component": "chart" | "card" | "table",  # For embedded rendering
        "requires_confirmation": bool,
        "credit_cost": int
    },
    "message": str  # User-friendly summary
}
```

### Error Handling
- Raise `HTTPException(status_code=4xx)` for user errors
- Return `{"success": false, "error": "message"}` for recoverable failures
- Include suggested recovery actions in error messages

## User Journey Context

1. **Onboarding**: Google OAuth → Connect ad account (Meta/TikTok) → View dashboard
2. **Primary workflow**: Open chat → Natural language command → AI routes to capability → Results render inline
3. **Secondary workflow**: Browse dashboard → Click "Ask AI" → Chat opens with context pre-filled
4. **Follow-up actions**: Click embedded action buttons → Execute with confirmation if needed

## When Adding New Features

**Checklist**:
- [ ] Implement capability module in `ai-orchestrator/app/modules/{domain}/`
- [ ] Create MCP tool in `backend/app/mcp/tools/` with proper auth/response structure
- [ ] Register tool in `backend/app/mcp/registry.py`
- [ ] Add embedded component rendering in `frontend/src/components/chat/`
- [ ] Test via natural language commands in chat
- [ ] Add dashboard UI as secondary view (optional)
- [ ] Document credit costs if applicable

## Common Pitfalls to Avoid

- **Don't** build dashboard-only features (violates chat-first principle)
- **Don't** skip confirmation for destructive operations
- **Don't** forget to check ad account authorization in MCP tools
- **Don't** return unstructured text when embedded components are appropriate
- **Don't** implement Google Ads features yet (not supported)
