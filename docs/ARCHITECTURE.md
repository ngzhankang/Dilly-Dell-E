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
| **ML Service** | Python + FastAPI | Model inference + data pipelines |
| **├─ Adapter** | Python + LLM | Multi-format data import + normalization |
| **├─ Profile Builder** | MongoDB + Pydantic | Unified patient profiles |
| **├─ Turn Orchestrator** | MongoDB + FastAPI | Conversation session management |
| **├─ Voice Gateway** | FastAPI + Whisper | Audio input/output handling |
| **├─ RAG Pipeline** | ChromaDB + Ollama/API | Care navigation Q&A |
| **├─ QA Service** | MongoDB + LLM | Confidence gate + hallucination check |
| **└─ Review Queue** | MongoDB + FastAPI | Human-in-the-loop review dashboard |
| Database | MongoDB | Persistent storage (profiles, sessions, audits) |
| Vector DB | ChromaDB | RAG embeddings + retrieval |
| Cache | Redis | Session storage, rate limiting |
| LLM | Ollama (fallback) + API | SEA-LION v3.5, inference |
| Infra (dev) | Docker Compose | Local service orchestration |
| Infra (prod) | Kubernetes | Container orchestration + scaling |

## ML Service Architecture (FastAPI Namespaces)

The ML service organizes data pipelines and voice AI into 6 namespaces:

### Phase 1: Adapter (`/adapter`)
**Multi-format data import + semantic field mapping**
- Accepts: CSV, Excel, JSON, fillable PDF forms
- Uses LLM (SEA-LION) to map agency field names to unified schema
- Output: Normalized patient records (name, dob, age, contact, emotion, problem_classes, special_case)
- Files: `ml/app/adapters/`, `ml/app/llm/`

### Phase 2: Profile Builder (`/profiles`)
**Unified patient profile storage + retrieval**
- Stores normalized records in MongoDB
- Simple merge: latest agency data wins
- Used by Voice Gateway for patient context
- Files: `ml/app/profile_builder/`

### Phase 3: Turn Orchestrator + Voice Gateway (`/voice`)
**Conversation session management + voice I/O**
- Sessions: Store conversation history, patient context
- Turns: Process user input → RAG response → store history
- Fetches patient context from Profile Builder
- Integrates: Adapter → Profiles → RAG → Voice responses
- Files: `ml/app/turn_orchestrator/`

### Phase 4: RAG Pipeline (`/query`, `/query-audio`, `/predict`)
**Care navigation Q&A with patient context**
- ChromaDB vector store for care resources
- Ollama (fallback) + LLM API (primary) for inference
- Retrieves relevant sources, generates personalized responses
- Files: `ml/app/rag/`, `ml/app/llm/`

### Phase 5: QA Namespace (`/qa`)
**Quality assurance + human-in-the-loop review**

**Confidence Gate:**
- HIGH (≥0.8): No review needed
- MEDIUM (0.6-0.79): Optional review
- LOW (<0.6): Escalate to review

**Hallucination Check:**
- Compare response claims against retrieved sources
- Calculate % of unmatched sentences
- >30% unmatched = likely hallucination

**Escalation:**
- Low confidence OR hallucination detected → review_queue
- Human reviewer dashboard (`/qa/reviews/pending`)

**Audit Log:**
- Every interaction logged with metadata
- Tracks review actions for compliance/bias detection

Files: `ml/app/qa_service/`

---

## Data Flow: End-to-End Voice Interaction

```
User (mobile audio)
    ↓ [transcribed via Whisper]
    ↓
POST /voice/turn
    ├─ TurnOrchestratorService (session management)
    ├─ ProfileService (fetch patient context)
    └─ RAGPipeline (query with context + retrieve sources)
    ↓
POST /qa/check-response
    ├─ Confidence Gate (classify: high/medium/low)
    ├─ Hallucination Check (compare vs sources)
    └─ Escalation Decision (needs_review?)
    ↓
If needs_review:
    └─ POST /qa/escalate → review_queue
        ├─ Human reviewer GET /qa/reviews/pending
        ├─ Review action (approve/reject/modify)
        └─ Audit logged
    ↓
Response → POST /qa/log-interaction (audit trail)
    ↓
Return to mobile (synthesize to audio)
    ↓
User (mobile audio output)
```

---

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
