# Windows Setup Guide for Frontend Development

Quick setup guide to get the backend running on Windows so you can test your Unity app.

---

## Prerequisites

Install these first:

1. **Docker Desktop for Windows**
   - Download: https://www.docker.com/products/docker-desktop
   - Install and restart your machine

2. **Git**
   - Download: https://git-scm.com/download/win
   - Install with default settings

3. **Node.js (LTS)**
   - Download: https://nodejs.org/
   - Install with default settings

---

## Setup Steps

### Step 1: Clone the Repository

```bash
git clone https://github.com/ngzhankang/Dilly-Dell-E.git
cd Dilly-Dell-E
git checkout ml
```

### Step 2: Start Docker Services

```bash
# Start MongoDB, Redis, and ML service
docker compose up -d

# Wait 30 seconds for services to start
# Then verify they're running:
docker compose ps
```

**You should see 4 containers running:**
- mongo (running)
- redis (running)
- ollama (running)
- ml-service (running)

### Step 3: Set Up Backend

```bash
cd backend

# Install dependencies
npm install

# Start the backend server
npm run dev
```

**Backend should start at:** `http://localhost:3001`

### Step 4: Test the Connection

Open a new terminal and run:

```bash
curl http://localhost:3001/health
```

**Expected response:**
```json
{
  "status": "ok",
  "mongodb": true,
  "ml_service": true
}
```

If all three are `true`, you're ready to test! ✅

---

## Using with Your Unity App

Update your backend URL in the Unity code:

```csharp
// In BackendManager.cs
private string baseURL = "http://localhost:3001";
```

That's it! Your Unity app should now connect to the backend.

---

## Common Issues

### "Port 3001 is already in use"

```bash
# Find the process using port 3001
netstat -ano | findstr :3001

# Kill the process (replace PID with the number)
taskkill /PID <PID> /F
```

### Docker containers won't start

```bash
# Make sure Docker Desktop is running (check system tray)
# Then restart:
docker compose down
docker compose up -d
```

### "mongodb: false" in health check

Wait 30 seconds longer - MongoDB takes time to start.

### Backend crashes on startup

```bash
# Make sure .env file exists
dir backend\.env

# If missing, copy from template
copy backend\.env.example backend\.env
```

---

## Keeping Services Running

**Terminal 1** (keep open):
```bash
docker compose up
```

**Terminal 2** (keep open):
```bash
cd backend
npm run dev
```

**Terminal 3** (for testing):
```bash
curl http://localhost:3001/health
```

---

## Quick Reference

| Service | URL | Status |
|---------|-----|--------|
| Backend | http://localhost:3001 | Check `/health` endpoint |
| MongoDB | localhost:27017 | Internal to Docker |
| Redis | localhost:6379 | Internal to Docker |
| ML Service | localhost:8000 | Internal to Docker |

---

## Next Steps

1. All services running locally
2. Backend accessible at `http://localhost:3001`
3. Update Unity code to use `http://localhost:3001`
4. Test your endpoints

---

## Need Help?

If something isn't working:

1. Check all Docker containers are running: `docker compose ps`
2. Check backend is running: `curl http://localhost:3001/health`
3. Check backend console for errors
4. Restart everything: `docker compose down && docker compose up -d`

Good luck! 🚀
