# Architecture

## System Overview

```
┌─────────────────────────────────────────┐
│                Browser                  │
└──────────────────┬──────────────────────┘
                   │ HTTP / WebSocket
┌──────────────────▼──────────────────────┐
│        React + Vite (frontend)           │
│        localhost:5173                    │
└──────────────────┬──────────────────────┘
                   │ REST API
┌──────────────────▼──────────────────────┐
│     Express + TypeScript (backend)       │
│     localhost:3001                       │
└───────┬──────────────────────┬──────────┘
        │                      │
┌───────▼──────┐    ┌──────────▼──────────┐
│   MongoDB    │    │        Redis         │
│  port 27017  │    │      port 6379       │
└──────────────┘    └─────────────────────┘
```

## Components

| Component | Tech | Purpose |
|-----------|------|---------|
| Frontend | React + Vite + TypeScript | UI |
| Backend | Express + TypeScript | API server |
| Database | MongoDB via Mongoose | Persistent storage |
| Cache | Redis | Session storage, rate limiting |

## Key Decisions

### ADR-001: Vite over CRA

**Status:** Accepted
**Decision:** Use Vite for frontend scaffolding instead of Create React App
**Reason:** CRA is unmaintained; Vite is faster, actively maintained, and the current community standard

### ADR-002: Zod for env validation

**Status:** Accepted
**Decision:** Parse all environment variables through a Zod schema at startup
**Reason:** Fail fast with clear errors on misconfiguration; avoids `undefined` leaking into app logic

---
<!-- Add new ADRs here as architectural decisions are made during the hackathon -->
