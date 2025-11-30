---
inclusion: always
---

# AAE Product Context

AAE (Automated Ad Engine) is an AI-powered advertising management platform. Users manage ad operations through a conversational AI agent embedded in the web interface.

## Core Principle

**Chat-first UX** — all features must be accessible via natural language through the embedded AI chat (bottom-right floating button).

## Feature Domains

| Domain | Key Behaviors |
|--------|---------------|
| Chat Interface | Primary entry point; renders charts, cards, and action buttons inline |
| Creative Generation | AI generates/analyzes ad creatives; results display in chat |
| Performance Analytics | Real-time metrics, anomaly detection, AI insights |
| Landing Pages | Automated generation with A/B testing support |
| Campaign Automation | Ad creation, budget optimization, scheduling |
| Market Intelligence | Competitor analysis, trend insights |

## Supported Platforms

- Meta (Facebook/Instagram) Ads
- TikTok Ads
- Google Ads (planned)

## User Flow

1. Authenticate via Google OAuth
2. View dashboard metrics overview
3. Open AI chat → issue natural language commands
4. AI orchestrator routes to capability modules
5. Results render inline (charts, cards, confirmations)
6. Detailed views available in dedicated pages

## Implementation Rules

| Rule | Rationale |
|------|-----------|
| All features accessible via chat | Chat is the primary UX |
| Embedded components render in chat bubbles | Charts, cards, tables display inline |
| Confirmation required for destructive ops | Prevent accidental deletions/changes |
| Dashboard pages are secondary | Complement chat, not replace it |
| Track credit usage for AI operations | Credit-based billing model |

## Chat Response Patterns

When implementing AI responses:
- Return structured data for embedded components (charts, cards)
- Include actionable buttons for follow-up operations
- Provide confirmation prompts before mutations
- Show progress indicators for long-running operations
- Display errors with clear recovery actions

## MCP Tool Guidelines

Tools exposed to the AI orchestrator must:
- Accept user context (user_id, ad_account_id) for authorization
- Return structured responses suitable for chat rendering
- Include metadata for embedded component types
- Handle errors gracefully with user-friendly messages
