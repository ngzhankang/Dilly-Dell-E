# Deployment Guide

How to containerize and deploy Dilly-Dell-E to Kubernetes (with Unreal frontend pending).

---

## Deployment Scenarios

### Scenario 1: Local Development (Docker Compose)

**Current state:** Backend not yet updated, Unreal frontend not ready
**Best for:** Developing phases 1-5 (Adapter → QA Service)

```bash
# Start MongoDB, Redis, Ollama, ML service
make docker-up

# Or manually:
docker compose up -d

# ML service available at: http://localhost:8000
# MongoDB at: localhost:27017
# Redis at: localhost:6379
# Ollama at: http://localhost:11434
```

### Scenario 2: Local Backend + Container Services

**When:** Backend is ready
**Setup:** Backend runs locally, services in Docker

```bash
# Terminal 1: Start infrastructure
make docker-up

# Terminal 2: Start backend
cd backend && npm run dev

# Terminal 3 (optional): Start Unreal frontend
# (once your friend finishes it)
```

### Scenario 3: Production on Kubernetes

**When:** Ready to deploy to shared cluster
**Setup:** Everything containerized in Kubernetes

```bash
# Build images
make build-images TAG=v1.0.0

# Push to registry
make push-images REGISTRY=ghcr.io/your-org/dilly-dell-e TAG=v1.0.0

# Deploy to K8s
make k8s-apply

# Check status
kubectl -n dilly-dell-e get pods
```

---

## Architecture: What Gets Deployed

### Local Docker Compose (Scenario 1)

```
┌──────────────────────────────────────────┐
│         Your Machine (Docker)            │
├──────────────────────────────────────────┤
│                                          │
│  ┌─────────────┐  ┌──────────────────┐  │
│  │  MongoDB    │  │  Redis           │  │
│  │  :27017     │  │  :6379           │  │
│  └─────────────┘  └──────────────────┘  │
│                                          │
│  ┌─────────────┐  ┌──────────────────┐  │
│  │  Ollama     │  │  ML Service      │  │
│  │  :11434     │  │  :8000 (FastAPI) │  │
│  └─────────────┘  └──────────────────┘  │
│                                          │
│  Backend runs locally (npm run dev)     │
│                                          │
│  Unreal Frontend (when ready)           │
│  → connects to http://localhost:3001    │
│                                          │
└──────────────────────────────────────────┘
```

### Kubernetes (Scenario 3)

```
┌────────────────────────────────────────────────────────────┐
│  Kubernetes Cluster (e.g., GKE, EKS, on-prem)             │
│  Namespace: dilly-dell-e                                  │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  ┌──────────────────┐  ┌──────────────────┐              │
│  │ ml-service Pod   │  │ backend Pod      │              │
│  │ (FastAPI)        │  │ (Express)        │              │
│  │ ClusterIP: 8000  │  │ ClusterIP: 3001  │              │
│  └──────────────────┘  └──────────────────┘              │
│           │                      │                        │
│  ┌────────▼──────────────────────▼──────────┐            │
│  │  External LoadBalancer (or Ingress)      │            │
│  │  :443 → backend service                  │            │
│  └────────────────────────────────────────────┘            │
│                                                            │
│  MongoDB (external or StatefulSet)                        │
│  Redis (external or Deployment)                           │
│  Ollama (Deployment with GPU)                            │
│                                                            │
│  Unreal Frontend                                          │
│  → connects to https://your-domain.com                   │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

---

## Deployment Workflow

### Step 1: Build & Push Images

**Prerequisite:** Docker installed, container registry access (GitHub Container Registry, Docker Hub, etc.)

```bash
# Set registry (example: GitHub Container Registry)
export REGISTRY=ghcr.io/your-org/dilly-dell-e
export TAG=v1.0.0

# Build backend + ML service images
make build-images TAG=$TAG

# Tag and push to registry
make push-images REGISTRY=$REGISTRY TAG=$TAG

# Verify images are pushed
docker images | grep dilly-dell-e
```

### Step 2: Update Kubernetes Manifests

Update image references in K8s manifests:

**File:** `k8s/ml-service/deployment.yaml`
```yaml
spec:
  containers:
    - name: ml-service
      image: ghcr.io/your-org/dilly-dell-e/ml-service:v1.0.0  # Update this
```

**File:** `k8s/backend/deployment.yaml`
```yaml
spec:
  containers:
    - name: backend
      image: ghcr.io/your-org/dilly-dell-e/backend:v1.0.0    # Update this
```

Or use image pull secrets if registry is private:

```bash
kubectl create secret docker-registry regcred \
  --docker-server=ghcr.io \
  --docker-username=<your-username> \
  --docker-password=<your-token> \
  --docker-email=<your-email> \
  -n dilly-dell-e
```

### Step 3: Deploy to Kubernetes

```bash
# Apply all manifests (namespace → ollama → ml-service → backend)
make k8s-apply

# Monitor rollout
kubectl -n dilly-dell-e rollout status deployment/ml-service
kubectl -n dilly-dell-e rollout status deployment/backend

# Check all pods are running
kubectl -n dilly-dell-e get pods

# View logs
kubectl -n dilly-dell-e logs -f deployment/ml-service
kubectl -n dilly-dell-e logs -f deployment/backend
```

### Step 4: Expose via LoadBalancer or Ingress

**Option A: LoadBalancer (simple, works everywhere)**

```bash
kubectl -n dilly-dell-e expose deployment backend \
  --type=LoadBalancer \
  --port=443 \
  --target-port=3001 \
  --name=backend-lb
```

Then get the external IP:
```bash
kubectl -n dilly-dell-e get svc backend-lb
```

**Option B: Ingress (if you have Ingress controller)**

```yaml
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: dilly-dell-e-ingress
  namespace: dilly-dell-e
spec:
  rules:
    - host: api.dilly-dell-e.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: backend
                port:
                  number: 3001
```

### Step 5: Configure Unreal Frontend (When Ready)

When your friend finishes the Unreal mobile app, configure it to connect:

**Connect to Kubernetes API:**
```
API_BASE_URL = "https://api.dilly-dell-e.com"  // or LoadBalancer IP
ML_SERVICE_URL = "https://api.dilly-dell-e.com/ml"  // proxied through backend
```

**Connect to Local Docker Compose (dev):**
```
API_BASE_URL = "http://localhost:3001"
ML_SERVICE_URL = "http://localhost:8000"
```

---

## Kubernetes Manifests Explained

### Namespace

**File:** `k8s/namespace.yaml`
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: dilly-dell-e
```

Creates isolated namespace for all Dilly-Dell-E resources.

### ML Service Deployment

**File:** `k8s/ml-service/deployment.yaml`
```yaml
spec:
  replicas: 1  # Scale up for load
  containers:
    - name: ml-service
      image: ghcr.io/your-org/dilly-dell-e/ml-service:latest
      ports:
        - containerPort: 8000
      env:
        - name: MONGO_URI
          value: mongodb://mongo:27017
        - name: OLLAMA_BASE_URL
          value: http://ollama:11434
        # ... more env vars
```

**Service** routes internal traffic:
```yaml
apiVersion: v1
kind: Service
metadata:
  name: ml-service
spec:
  ports:
    - port: 8000
      targetPort: 8000
  selector:
    app: ml-service
```

### Backend Deployment

**File:** `k8s/backend/deployment.yaml`
```yaml
spec:
  containers:
    - name: backend
      image: ghcr.io/your-org/dilly-dell-e/backend:latest
      ports:
        - containerPort: 3001
      env:
        - name: ML_SERVICE_URL
          value: http://ml-service:8000
        - name: MONGO_URI
          value: mongodb://mongo:27017
```

### Ollama Deployment (GPU-accelerated)

**File:** `k8s/ollama/deployment.yaml`
```yaml
spec:
  containers:
    - name: ollama
      image: ollama/ollama:latest
      ports:
        - containerPort: 11434
      resources:
        limits:
          nvidia.com/gpu: 1  # Request 1 GPU (if available)
```

---

## Environment Variables (K8s Secrets)

### Create Secrets

```bash
# Create secret with LLM API key
kubectl create secret generic ml-secrets \
  --from-literal=LLM_API_KEY=sk-your-api-key \
  -n dilly-dell-e

# Create secret for MongoDB credentials (if needed)
kubectl create secret generic mongo-secrets \
  --from-literal=MONGO_USER=admin \
  --from-literal=MONGO_PASSWORD=your-password \
  -n dilly-dell-e
```

### Reference in Deployment

```yaml
env:
  - name: LLM_API_KEY
    valueFrom:
      secretKeyRef:
        name: ml-secrets
        key: LLM_API_KEY
```

---

## Scaling

### Horizontal Scaling (more replicas)

```bash
# Scale ML service to 3 replicas
kubectl -n dilly-dell-e scale deployment ml-service --replicas=3

# Scale backend to 2 replicas
kubectl -n dilly-dell-e scale deployment backend --replicas=2
```

### Vertical Scaling (more CPU/memory per pod)

Edit `k8s/ml-service/deployment.yaml`:

```yaml
spec:
  containers:
    - name: ml-service
      resources:
        requests:
          memory: "2Gi"
          cpu: "1000m"
        limits:
          memory: "4Gi"
          cpu: "2000m"
```

Then apply:
```bash
kubectl apply -f k8s/ml-service/deployment.yaml
```

---

## Monitoring & Debugging

### Check Pod Status

```bash
# List all pods
kubectl -n dilly-dell-e get pods

# Watch pods (live updates)
kubectl -n dilly-dell-e get pods -w

# Describe a pod (detailed info)
kubectl -n dilly-dell-e describe pod ml-service-abc123
```

### View Logs

```bash
# Last 50 lines
kubectl -n dilly-dell-e logs deployment/ml-service -n=50

# Follow logs (tail -f)
kubectl -n dilly-dell-e logs -f deployment/ml-service

# Multiple pods
kubectl -n dilly-dell-e logs -f deployment/ml-service --all-containers=true
```

### Port Forward (for debugging)

```bash
# Access ML service locally
kubectl -n dilly-dell-e port-forward svc/ml-service 8000:8000

# Then: curl http://localhost:8000/health
```

### Check Services & Endpoints

```bash
kubectl -n dilly-dell-e get svc
kubectl -n dilly-dell-e get endpoints
```

---

## Rollout & Updates

### Deploy a New Version

```bash
# Build and push new image
make build-images TAG=v1.1.0
make push-images REGISTRY=ghcr.io/your-org/dilly-dell-e TAG=v1.1.0

# Update deployment image
kubectl -n dilly-dell-e set image deployment/ml-service \
  ml-service=ghcr.io/your-org/dilly-dell-e/ml-service:v1.1.0

# Or update manifest and apply
kubectl apply -f k8s/ml-service/deployment.yaml
```

### Monitor Rollout

```bash
# Watch progress
kubectl -n dilly-dell-e rollout status deployment/ml-service -w

# View rollout history
kubectl -n dilly-dell-e rollout history deployment/ml-service

# Rollback to previous version
kubectl -n dilly-dell-e rollout undo deployment/ml-service
```

---

## Production Checklist

Before deploying to production:

- [ ] **MongoDB persistence**
  - Use persistent volumes or external MongoDB service (MongoDB Atlas, AWS RDS)
  - Backup strategy in place

- [ ] **Redis persistence**
  - Use persistent volumes or external Redis (AWS ElastiCache, Redis Cloud)

- [ ] **Image registry**
  - Push to private registry (GitHub Container Registry, Docker Hub, ECR)
  - Set image pull secrets

- [ ] **Secrets management**
  - LLM_API_KEY stored in Kubernetes Secrets
  - Database credentials in Secrets (not in code)
  - Rotate keys regularly

- [ ] **Resource limits**
  - CPU/memory requests and limits set
  - Prevent pods from starving each other

- [ ] **Health checks**
  - Liveness probes (restart if unhealthy)
  - Readiness probes (remove from traffic if not ready)

- [ ] **Ingress/LoadBalancer**
  - TLS/HTTPS enabled
  - DNS configured
  - CORS configured (for Unreal frontend)

- [ ] **Monitoring & logging**
  - Logs aggregated (e.g., ELK, Stackdriver)
  - Metrics collected (Prometheus, DataDog)
  - Alerts set up

- [ ] **Backups**
  - MongoDB snapshots
  - Regular backups tested

---

## Unreal Frontend Integration (Waiting for Your Friend)

When the Unreal mobile app is ready:

### 1. Update Backend to Proxy ML Service

**File:** `backend/src/routes/ml.ts`

```typescript
// Proxy ML service endpoints
router.post('/predict', async (req, res) => {
  try {
    const response = await fetch(`${ML_SERVICE_URL}/predict`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req.body)
    });
    const data = await response.json();
    res.json(data);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

router.post('/voice/turn', async (req, res) => {
  // Proxy to ML service
  const response = await fetch(`${ML_SERVICE_URL}/voice/turn`, { ... });
  // ... handle response
});
```

### 2. Configure Unreal to Connect to Backend

```cpp
// In Unreal C++
const FString ApiUrl = TEXT("https://api.your-domain.com");
const FString VoiceEndpoint = ApiUrl + TEXT("/voice/turn");

// POST request with audio transcript
FHttpModule::Get().GetHttpManager().AddRequest(Request);
```

### 3. Enable CORS on Backend

```typescript
app.use(cors({
  origin: ['unreal-app://...', 'http://localhost:3001'],
  credentials: true
}));
```

### 4. API Flow

```
Unreal App
  ↓ (audio transcription on device)
  ↓ POST /voice/turn
Backend
  ↓ proxy
ML Service
  ├─ Profile Builder (fetch patient context)
  ├─ RAG Pipeline (generate response)
  ├─ QA Service (validate quality)
  └─ Turn Orchestrator (store session)
  ↓
Backend (returns TurnResponse)
  ↓
Unreal App
  ↓ (text-to-speech on device)
  ↓ Play audio
User hears response
```

---

## Cost Estimation (Rough)

| Component | Cloud | Monthly Cost |
|-----------|-------|--------------|
| **Kubernetes** (GKE, 2 nodes) | GCP | $150-200 |
| **MongoDB** (managed) | MongoDB Atlas | $100-500 |
| **Redis** (managed) | AWS ElastiCache | $20-100 |
| **Ollama/LLM** (GPU node, optional) | GCP | $100-300 |
| **Total** | — | **$400-1100** |

**Cost optimization:**
- Use CPU-only Ollama (lower cost)
- Use external LLM API (GPT-4, Claude) instead of self-hosted Ollama
- Auto-scale down during off-hours
- Use spot instances (if K8s supports)

---

## Summary

| Stage | Status | When |
|-------|--------|------|
| **Local Dev** | ✅ Ready | Now (Scenario 1: `make docker-up`) |
| **K8s Staging** | ✅ Ready | Soon (Scenario 3: `make k8s-apply`) |
| **Production** | 🟡 Ready | After Unreal frontend + testing |
| **Unreal Integration** | ⏳ Waiting | When your friend finishes |

**Next step:** Decide where to deploy.
- **Local only?** → `make docker-up`
- **Full K8s on a cluster?** → Choose cloud (GKE, EKS, AKS) and update image registry
- **Hybrid?** → Run K8s on-prem or self-hosted cluster
