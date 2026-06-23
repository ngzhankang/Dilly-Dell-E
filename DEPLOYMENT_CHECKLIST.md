# Deployment Checklist

Deploy your backend to a live cloud endpoint in 15 minutes.

---

## 📋 Checklist

### Part 1: Create Cloud Accounts (5 minutes)

- [ ] Create Fly.io account: https://fly.io
- [ ] Create MongoDB Atlas account: https://www.mongodb.com/cloud/atlas
  - [ ] Create free cluster
  - [ ] Create database user
  - [ ] Get connection string
- [ ] Create Upstash Redis account: https://upstash.com
  - [ ] Create Redis database
  - [ ] Get connection URL

### Part 2: Local Setup (5 minutes)

- [ ] Install Fly CLI: `brew install flyctl` (or Windows equivalent)
- [ ] Login to Fly: `flyctl auth login`
- [ ] Verify credentials: `flyctl status`

### Part 3: Configure & Deploy (5 minutes)

```bash
cd /Users/ngzhankang/Documents/Github\ Projects/Dilly-Dell-E

# Initialize Fly app (creates fly.toml)
flyctl launch

# Set environment variables
flyctl secrets set \
  MONGO_URI="mongodb+srv://..." \
  REDIS_URL="redis://..." \
  JWT_SECRET="your-secret-key"

# Deploy
flyctl deploy
```

- [ ] Wait 3-5 minutes for deployment
- [ ] Check status: `flyctl status`
- [ ] Get URL: `https://dilly-dell-e.fly.dev`

### Part 4: Test Live Endpoint

```bash
# Test health
curl https://dilly-dell-e.fly.dev/health

# Should return: {"status":"ok","mongodb":true,"ml_service":false}
```

- [ ] Health check returns 200
- [ ] MongoDB connects
- [ ] Endpoint is accessible

### Part 5: Update Unity App

- [ ] Update backend URL to: `https://dilly-dell-e.fly.dev`
- [ ] Test connection from Unity
- [ ] Works from anywhere! ✅

---

## 🎯 Summary

| Step | Time | What | Result |
|------|------|------|--------|
| 1 | 5 min | Create cloud accounts | Credentials ready |
| 2 | 5 min | Install & login to Fly | Local setup done |
| 3 | 5 min | Deploy to cloud | Live endpoint |
| 4 | 2 min | Test endpoint | Verify it works |
| 5 | 2 min | Update Unity | App ready |
| **Total** | **~20 min** | **From localhost to cloud** | **Live app! 🚀** |

---

## 💰 Cost

- **Free tier** during hackathon (~$0/month)
- **Production ready** if you upgrade (~$15/month for Fly + MongoDB + Redis)

---

## 📚 Full Guides

- Setup: `WINDOWS_SETUP.md` (for your friend)
- Fly.io: `FLY_DEPLOYMENT.md` (detailed deployment)
- Unity: `UNITY_INTEGRATION.md` (API endpoints)

---

## ⚠️ Important

**Keep these safe:**
- MongoDB URI (includes password)
- Redis URL (includes password)
- JWT Secret (change it!)

**Never commit secrets to Git.**

---

## ✅ After Deployment

Your live endpoint:
```
https://dilly-dell-e.fly.dev
```

Your friend can now:
1. Install Unity on Windows (or use existing setup)
2. Update backend URL to live endpoint
3. Test from anywhere in the world
4. Download app to phone and it works! 📱

---

## Next Steps

1. Create cloud accounts (MongoDB Atlas, Upstash, Fly.io)
2. Follow FLY_DEPLOYMENT.md step-by-step
3. Get your live URL
4. Share with your friend
5. Update Unity app
6. Done! 🎉

**Questions?** Check FLY_DEPLOYMENT.md troubleshooting section.

