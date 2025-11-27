# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AAE (Automated Ad Engine) is an advertising SaaS platform with an embedded AI agent assistant. Users interact through a unified conversational interface to manage ad campaigns across Meta, TikTok, and Google Ads.

**Core Architecture**: User Portal (Next.js + FastAPI) + Unified AI Agent (LangGraph) + 5 Capability Modules

## System Architecture

```
User Portal (用户入口)
├── Frontend: Next.js 14 + Vercel AI SDK
├── Backend: FastAPI + MCP Server
└── Data: PostgreSQL + TimescaleDB + Redis + S3
         │
         │ HTTP Streaming (对话) + MCP Protocol (数据)
         ▼
Unified AI Agent (LangGraph)
├── Intent Recognition (Gemini 2.5 Flash)
├── Orchestrator (协调器)
└── 5 Capability Modules:
    ├── Creative Capability (素材生成)
    ├── Market Intelligence Capability (市场洞察)
    ├── Reporting Capability (报表分析)
    ├── Landing Page Capability (落地页)
    └── Ad Engine Capability (广告投放)
```

## Specification Documents

All requirements are in `.kiro/specs/`:

| Document | Purpose |
|----------|---------|
| `ARCHITECTURE.md` | System architecture and tech stack |
| `INTERFACES.md` | MCP tools, WebSocket protocols, error codes |
| `SUMMARY.md` | Quick architecture overview |
| `user-portal/requirements.md` | User Portal requirements (auth, billing, Credit system) |
| `unified-ai-agent/requirements.md` | AI Agent with LangGraph implementation |
| `creative-capability/requirements.md` | Image generation capability |
| `market-intelligence-capability/requirements.md` | Competitor analysis, trends |
| `reporting-capability/requirements.md` | Data fetching, anomaly detection |
| `landing-page-capability/requirements.md` | Landing page generation |
| `ad-engine-capability/requirements.md` | Campaign creation, budget optimization |

## Key Technical Decisions

- **AI Agent Framework**: LangGraph (state machine with checkpointing)
- **Frontend Chat**: Vercel AI SDK (`ai` package) with streaming
- **Communication**: HTTP Streaming (frontend ↔ agent) + MCP Protocol (agent ↔ portal)
- **Billing**: Credit-based system (¥199/30K credits, ¥1999/400K credits, overage at ¥0.01/credit)
- **Primary LLM**: Gemini 2.5 Flash (Claude 3.5 Sonnet as fallback)
- **Image Generation**: AWS Bedrock Stable Diffusion XL

## MCP Tools Reference

High-priority tools defined in `INTERFACES.md`:

| Tool | Category | Purpose |
|------|----------|---------|
| `check_credit` / `deduct_credit` | Billing | Credit balance management |
| `create_creative` | Creative | Store generated assets |
| `create_campaign` | Ad Engine | Create ad campaigns |
| `get_reports` | Reporting | Fetch ad performance data |
| `get_credit_balance` | Billing | Check user credits |

## Error Codes

- `6011`: INSUFFICIENT_CREDITS
- `6012`: CREDIT_DEDUCTION_FAILED
- `6013`: SUBSCRIPTION_EXPIRED
- `4001-4003`: AI service errors
- `3001-3003`: MCP communication errors

## Development Notes

- All specs are in Chinese with English technical terms
- Requirements follow WHEN/THEN acceptance criteria format
- Credit consumption rules are dynamically configurable
- Capability modules communicate with User Portal exclusively via MCP (no direct DB access)
