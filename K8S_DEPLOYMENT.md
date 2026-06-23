# Kubernetes Deployment Guide

Complete guide to deploy Dilly-Dell-E on Kubernetes locally or in production.

---

## Prerequisites

### Local (Docker Desktop K8s)

```bash
# 1. Enable Kubernetes in Docker Desktop
#    Docker → Preferences → Kubernetes → Enable Kubernetes
#    Wait 2-3 minutes

# 2. Verify K8s is running
kubectl cluster-info

# 3. You should see:
# Kubernetes control plane is running at https://...
# CoreDNS is running at https://...
```

### Alternative: Minikube

```bash
brew install minikube
minikube start --cpus=4 --memory=8192
```

---

## Deployment Steps

### Step 1: Build Docker Images (for K8s)

```bash
cd /Users/ngzhankang/Documents/Github\ Projects/Dilly-Dell-E

# Build backend image
docker build -t dilly-dell-e/backend:latest ./backend

# Build ML service image
docker build -t dilly-dell-e/ml-service:latest ./ml

# Build Ollama image (already available: ollama/ollama:latest)
```

### Step 2: Create Namespace

```bash
kubectl apply -f k8s/namespace.yaml

# Verify
kubectl get namespaces | grep dilly
```

### Step 3: Create Secrets

```bash
# Update k8s/secrets.yaml with your actual values
kubectl apply -f k8s/secrets.yaml

# Verify
kubectl get secrets -n dilly-dell-e
```

### Step 4: Create Storage (PVCs)

```bash
kubectl apply -f k8s/storage.yaml

# Verify
kubectl get pvc -n dilly-dell-e
```

### Step 5: Deploy Services

```bash
# Deploy Ollama first (takes longest)
kubectl apply -f k8s/ollama/

# Deploy MongoDB
kubectl apply -f k8s/mongo/

# Deploy Redis
kubectl apply -f k8s/redis/

# Deploy ML Service
kubectl apply -f k8s/ml-service/

# Deploy Backend
kubectl apply -f k8s/backend/

# Verify all deployments
kubectl get deployments -n dilly-dell-e
```

### Step 6: Wait for Services to Be Ready

```bash
# Watch the rollout
kubectl rollout status deployment/backend -n dilly-dell-e
kubectl rollout status deployment/ml-service -n dilly-dell-e
kubectl rollout status deployment/mongo -n dilly-dell-e
kubectl rollout status deployment/redis -n dilly-dell-e
kubectl rollout status deployment/ollama -n dilly-dell-e

# Or watch in real-time
kubectl get pods -n dilly-dell-e -w
```

### Step 7: Access Services

```bash
# Get the LoadBalancer IP for Backend
kubectl get svc -n dilly-dell-e

# Backend should be accessible at:
# http://localhost:3001 (local)
# http://<LoadBalancer-IP>:3001 (if using real LB)
```

---

## Verification

### Check Health

```bash
# Backend health
curl http://localhost:3001/health

# Should return:
{
  "status": "ok",
  "mongodb": true,
  "ml_service": true
}
```

### Check Logs

```bash
# Backend logs
kubectl logs -f deployment/backend -n dilly-dell-e

# ML Service logs
kubectl logs -f deployment/ml-service -n dilly-dell-e

# MongoDB logs
kubectl logs -f deployment/mongo -n dilly-dell-e

# Redis logs
kubectl logs -f deployment/redis -n dilly-dell-e
```

### SSH into a Pod (if needed)

```bash
# Get pod name
kubectl get pods -n dilly-dell-e

# Connect to a pod
kubectl exec -it <pod-name> -n dilly-dell-e -- sh
```

---

## Troubleshooting

### Pod Stuck in "Pending"

```bash
# Check events
kubectl describe pod <pod-name> -n dilly-dell-e

# Common causes:
# 1. Not enough resources - check `kubectl top nodes`
# 2. PVC not bound - check `kubectl get pvc -n dilly-dell-e`
# 3. Image not found - check `kubectl describe pod` for pull errors
```

### ImagePullBackOff Error

```bash
# This means the Docker image can't be found
# Solution: Use local images with imagePullPolicy: IfNotPresent

# Already configured in deployment.yaml
imagePullPolicy: IfNotPresent
```

### MongoDB Connection Refused

```bash
# Check if MongoDB is running
kubectl get pods -n dilly-dell-e | grep mongo

# Check MongoDB logs
kubectl logs -f deployment/mongo -n dilly-dell-e

# Verify service exists
kubectl get svc -n dilly-dell-e | grep mongo
```

### High Memory/CPU Usage

```bash
# Check resource usage
kubectl top nodes
kubectl top pods -n dilly-dell-e

# If pods are using too much:
# 1. Adjust limits in deployment.yaml
# 2. Scale down replicas: kubectl scale deployment backend --replicas=1
```

---

## Cleanup

```bash
# Delete all resources in namespace
kubectl delete namespace dilly-dell-e

# Or delete individually
kubectl delete deployment backend -n dilly-dell-e
kubectl delete deployment ml-service -n dilly-dell-e
kubectl delete deployment mongo -n dilly-dell-e
kubectl delete deployment redis -n dilly-dell-e
kubectl delete deployment ollama -n dilly-dell-e
```

---

## Manifest Files

| File | Purpose |
|------|---------|
| `k8s/namespace.yaml` | Create dilly-dell-e namespace |
| `k8s/secrets.yaml` | Store API keys & secrets |
| `k8s/storage.yaml` | PersistentVolumeClaims for data |
| `k8s/backend/deployment.yaml` | Express backend pods |
| `k8s/backend/service.yaml` | Backend service (LoadBalancer) |
| `k8s/mongo/deployment.yaml` | MongoDB pods |
| `k8s/mongo/service.yaml` | MongoDB service |
| `k8s/redis/deployment.yaml` | Redis pods |
| `k8s/redis/service.yaml` | Redis service |
| `k8s/ml-service/deployment.yaml` | FastAPI ML service pods |
| `k8s/ml-service/service.yaml` | ML service |
| `k8s/ollama/deployment.yaml` | Ollama pods |
| `k8s/ollama/service.yaml` | Ollama service |

---

## Production Checklist

- [ ] Update image names to use your registry (ghcr.io/your-org/...)
- [ ] Set real JWT_SECRET in k8s/secrets.yaml
- [ ] Set real LLM_API_KEY in k8s/secrets.yaml
- [ ] Increase resource requests/limits for production
- [ ] Set up ingress instead of LoadBalancer
- [ ] Configure TLS/HTTPS
- [ ] Enable pod autoscaling (HPA)
- [ ] Set up monitoring (Prometheus/Grafana)
- [ ] Configure backup strategy for MongoDB
- [ ] Use managed database in production (MongoDB Atlas, etc.)

---

## Quick Deploy (One Command)

```bash
# Deploy everything at once
kubectl apply -f k8s/

# Watch deployments
kubectl get pods -n dilly-dell-e -w
```

---

## Next Steps

Once K8s is running:
1. Test with `curl http://localhost:3001/health`
2. Connect your Unity frontend to the K8s backend
3. Run integration tests
4. Monitor with `kubectl logs` and `kubectl top`

