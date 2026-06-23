# Deploy to Fly.io (Live Cloud API)

Complete guide to deploy Dilly-Dell-E to Fly.io and get a live endpoint.

---

## Architecture

For production, we'll use:

```
Fly.io (Backend + ML Service)
    ↓
MongoDB Atlas (Cloud Database - Free Tier)
    ↓
Upstash Redis (Cloud Cache - Free Tier)
    ↓
Ollama (Self-hosted or via API)
```

---

## Prerequisites

1. **Fly.io Account**
   - Sign up: https://fly.io
   - Free tier includes 3 shared-cpu machines

2. **Fly CLI**
   ```bash
   # macOS
   brew install flyctl

   # Windows (PowerShell)
   iwr https://fly.io/install.ps1 -useb | iex
   ```

3. **MongoDB Atlas Account**
   - Sign up: https://www.mongodb.com/cloud/atlas
   - Free tier: 512MB database

4. **Upstash Redis Account**
   - Sign up: https://upstash.com
   - Free tier: 10,000 commands/day

---

## Step-by-Step Deployment

### Step 1: Create MongoDB Atlas Database

1. Go to https://www.mongodb.com/cloud/atlas
2. Create a free cluster
3. Create a database user (username & password)
4. Whitelist IP address (allow all: 0.0.0.0/0)
5. Get connection string: `mongodb+srv://username:password@cluster.mongodb.net/hackathon?retryWrites=true`

**Copy this string - you'll need it in Step 4**

### Step 2: Create Upstash Redis

1. Go to https://upstash.com
2. Create a Redis database (free tier)
3. Copy the connection URL: `redis://default:password@host:port`

**Copy this URL - you'll need it in Step 4**

### Step 3: Authenticate with Fly.io

```bash
flyctl auth login

# Or if you already have an account:
flyctl auth signup
```

### Step 4: Create Fly App

```bash
cd /Users/ngzhankang/Documents/Github\ Projects/Dilly-Dell-E

# Initialize Fly app
flyctl launch

# When prompted:
# - App name: dilly-dell-e
# - Region: sin (Singapore - closest to you)
# - Deploy now: no (we'll configure first)
```

This creates a `fly.toml` file (already created for you).

### Step 5: Set Environment Variables

```bash
flyctl secrets set \
  MONGO_URI="mongodb+srv://username:password@cluster.mongodb.net/hackathon" \
  REDIS_URL="redis://default:password@host:port" \
  JWT_SECRET="your-super-secret-key-change-this" \
  ML_SERVICE_URL="http://localhost:8000" \
  NODE_ENV="production"
```

Replace the values with your actual credentials from Steps 1 & 2.

### Step 6: Deploy to Fly.io

```bash
flyctl deploy
```

**Wait 3-5 minutes for deployment to complete...**

### Step 7: Get Your Live Endpoint

```bash
flyctl status
```

Look for: **https://dilly-dell-e.fly.dev**

This is your live API endpoint! 🎉

---

## Test the Live Endpoint

```bash
curl https://dilly-dell-e.fly.dev/health

# Should return:
{
  "status": "ok",
  "mongodb": true,
  "ml_service": false  # (ML service needs its own deployment)
}
```

---

## Update Your Unity App

In your Unity backend URL:

```csharp
private string baseURL = "https://dilly-dell-e.fly.dev";
```

Now your app works from anywhere! ✅

---

## Important Notes

### ML Service

For a full production deployment, you also need to deploy the ML service. Two options:

**Option A: Simple (for hackathon)**
- Keep ML service running locally on your machine
- Backend proxies to `http://localhost:8000`
- Works for testing, not production

**Option B: Full Cloud**
- Deploy ML service to Fly.io as a separate app
- Update `ML_SERVICE_URL` to point to it
- More complex, but fully production-ready

For now, **Option A is recommended** for the hackathon.

### Database Limits

- **MongoDB Atlas Free Tier**: 512MB storage
  - Plenty for testing (~100K patient records)
  - Upgrade to $9/month for 5GB if needed

- **Upstash Redis Free Tier**: 10,000 commands/day
  - Good for session caching
  - Upgrade to $20+/month for production

---

## Cost Breakdown

| Service | Cost | Notes |
|---------|------|-------|
| Fly.io Backend | ~$15/month | 1 shared CPU, 512MB RAM |
| MongoDB Atlas | Free ($9/mo if upgraded) | Free: 512MB |
| Upstash Redis | Free ($20+/mo if upgraded) | Free: 10K commands/day |
| **Total** | **~$15/month** | **Can stay free during hackathon** |

---

## Monitoring & Logs

View live logs:
```bash
flyctl logs
```

Monitor health:
```bash
flyctl status
```

---

## Troubleshooting

### "MongoDB connection refused"

- Check MONGO_URI is correct
- Make sure MongoDB Atlas user is created
- Whitelist your Fly.io IP: https://docs.fly.io/reference/private-networking/

```bash
# Set secrets again
flyctl secrets set MONGO_URI="..."
```

### "Redis connection refused"

- Check REDIS_URL is correct
- Verify credentials

```bash
flyctl secrets set REDIS_URL="..."
```

### "App won't deploy"

```bash
# Check logs
flyctl logs

# Restart app
flyctl restart

# Redeploy
flyctl deploy
```

---

## Next: Deploy ML Service (Optional)

Once backend is working, you can deploy ML service separately:

```bash
# Create another Fly app for ML service
flyctl launch --name dilly-dell-e-ml

# Set ML-specific env vars
flyctl secrets set \
  MONGO_URI="..." \
  REDIS_URL="..." \
  OLLAMA_BASE_URL="http://ollama:11434"

# Deploy
flyctl deploy
```

Then update backend ML_SERVICE_URL to: `https://dilly-dell-e-ml.fly.dev`

---

## Quick Reference

```bash
# Check deployment status
flyctl status

# View logs
flyctl logs

# Set new secrets
flyctl secrets set KEY=value

# Restart app
flyctl restart

# Redeploy
flyctl deploy
```

---

## Your Live Endpoint

Once deployed:
```
https://dilly-dell-e.fly.dev/api/voice/turn
https://dilly-dell-e.fly.dev/health
https://dilly-dell-e.fly.dev/api/profiles
```

Share this URL with anyone who wants to test! 🚀

