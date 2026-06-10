# Architecture

## System Overview

```
┌─────────────────────────────────────────┐
│      React Native + Expo (mobile)       │
│      iOS / Android / Expo Go            │
└──────────────────┬──────────────────────┘
                   │ REST API (HTTP)
┌──────────────────▼──────────────────────┐
│     Express + TypeScript (backend)      │
│     localhost:3001  /  K8s ClusterIP    │
└───────┬────────────────┬────────────────┘
        │                │ HTTP /predict
┌───────▼──────┐  ┌──────▼──────────────┐
│   MongoDB    │  │  FastAPI ML Service  │
│  port 27017  │  │  localhost:8000      │
└──────────────┘  └──────────────────────┘
        │
┌───────▼──────┐
│    Redis     │
│  port 6379   │
└──────────────┘
```

## Kubernetes Topology (production)

```
Namespace: dilly-dell-e
┌──────────────────────────────────────────────────────┐
│                                                      │
│   ┌────────────────┐      ┌────────────────────┐    │
│   │ backend (Pod)  │─────▶│ ml-service (Pod)   │    │
│   │ port 3001      │      │ port 8000          │    │
│   │ ClusterIP Svc  │      │ ClusterIP Svc      │    │
│   └───────┬────────┘      └────────────────────┘    │
│           │                                          │
│   (Secrets: MONGO_URI, REDIS_URL, JWT_SECRET)        │
└───────────┼──────────────────────────────────────────┘
            │ (external Mongo + Redis, or in-cluster)
```

## Components

| Component | Tech | Purpose |
|-----------|------|---------|
| Mobile | React Native + Expo | iOS / Android UI |
| Backend | Express + TypeScript | REST API server |
| ML Service | Python + FastAPI | Model inference (`/predict`) |
| Database | MongoDB via Mongoose | Persistent storage |
| Cache | Redis | Session storage, rate limiting |
| Infra (dev) | Docker Compose | Local service orchestration |
| Infra (prod) | Kubernetes | Container orchestration + scaling |

## Key Decisions

### ADR-001: Expo over bare React Native CLI

**Status:** Accepted
**Decision:** Use Expo (via `create-expo-app`) as the default mobile scaffold
**Reason:** Expo removes the Xcode/Android Studio requirement for day-to-day development; OTA updates, QR-code device testing, and a managed TypeScript template make it the fastest path for a hackathon. The bare RN CLI remains an option in `make init` for teams that need native module access.

### ADR-002: Zod for env validation

**Status:** Accepted
**Decision:** Parse all environment variables through a Zod schema at startup (`src/config/env.ts`)
**Reason:** Fail fast with clear errors on misconfiguration; avoids `undefined` leaking into app logic

### ADR-003: Separate ML service (FastAPI) over in-process inference

**Status:** Accepted
**Decision:** Run the ML model as a standalone FastAPI service, called by the backend over HTTP via `ML_SERVICE_URL`
**Reason:** Keeps Python/ML dependencies isolated from the Node.js backend; enables independent scaling of inference in Kubernetes; the same `ML_SERVICE_URL` env var resolves correctly in local Docker Compose and in K8s (ClusterIP DNS)

### ADR-004: Kubernetes over plain Docker Compose for production

**Status:** Accepted
**Decision:** Ship Kubernetes manifests in `k8s/` targeting a `dilly-dell-e` namespace
**Reason:** Independent Pod scaling for backend vs ml-service; K8s Secrets for sensitive env vars; avoids polluting the default namespace on a shared hackathon cluster. Docker Compose is still used for local development parity.

---
<!-- Add new ADRs here as architectural decisions are made during the hackathon -->
