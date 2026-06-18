# Backend Integration Guide (Option A: Quick & Minimal)

How to integrate backend with ML service endpoints.

---

## Files Created

New route files that proxy to ML service:

```
backend/src/routes/
├── adapter.ts      ← POST /adapter/import
├── profiles.ts     ← POST /profiles, GET /profiles/{id}
├── voice.ts        ← POST /voice/sessions/start, POST /voice/turn
├── qa.ts           ← POST /qa/check-response, GET /qa/reviews/*, etc.
└── (existing)
    └── admin/import.ts
```

**Updated main file:**
- `backend/src/index.ts.new` ← Use this as template, copy to `index.ts`

---

## Integration Steps

### 1. Copy Route Files

Copy the new route files to your backend:

```bash
# These files are already created in backend/src/routes/
ls -la backend/src/routes/
  adapter.ts    ✅
  profiles.ts   ✅
  voice.ts      ✅
  qa.ts         ✅
```

### 2. Update index.ts

Replace `backend/src/index.ts` with the template:

```bash
# Backup original
cp backend/src/index.ts backend/src/index.ts.backup

# Use the new version
cp backend/src/index.ts.new backend/src/index.ts
```

Or manually add these imports to your current `index.ts`:

```typescript
import { adapterRoutes } from './routes/adapter';
import { profileRoutes } from './routes/profiles';
import { voiceRoutes } from './routes/voice';
import { qaRoutes } from './routes/qa';
```

And register the routes:

```typescript
app.use('/api/adapter', adapterRoutes);
app.use('/api/profiles', profileRoutes);
app.use('/api/voice', voiceRoutes);
app.use('/api/qa', qaRoutes);
```

### 3. Verify Environment Variables

Check `.env` has `ML_SERVICE_URL`:

```bash
# In .env
ML_SERVICE_URL=http://localhost:8000  # for local Docker Compose
# OR
ML_SERVICE_URL=http://ml-service:8000  # for Kubernetes
```

The `env.ts` already validates this:

```typescript
ML_SERVICE_URL: z.string().url(),
```

### 4. Install Multipart Middleware (if needed)

For `/adapter/import` to work with file uploads:

```bash
npm install multer
npm install --save-dev @types/multer
```

Then add to `index.ts`:

```typescript
import multer from 'multer';

const upload = multer({ storage: multer.memoryStorage() });

// Apply to adapter routes
app.use('/api/adapter', upload.single('file'), adapterRoutes);
```

---

## Testing (Before Going Live)

### Setup

```bash
# Terminal 1: Start infrastructure
make docker-up

# Wait for services to be healthy
sleep 10

# Terminal 2: Start backend
cd backend && npm run dev

# Terminal 3: Test the API (this guide)
```

### Test 1: Health Check

```bash
curl http://localhost:3001/health
```

**Expected:**
```json
{
  "status": "ok",
  "mongodb": true,
  "ml_service": true
}
```

### Test 2: Adapter Import

```bash
# Create a test CSV
cat > /tmp/test.csv << 'EOF'
name,dob,contact,emotion,problem_classes
John Doe,1950-06-15,91234567,neutral,"Dementia, Hypertension"
Jane Smith,1955-08-20,91234568,anxious,"Arthritis"
EOF

# Upload
curl -X POST http://localhost:3001/api/adapter/import \
  -F "file=@/tmp/test.csv" \
  -F "agency_name=Test Agency"
```

**Expected:**
```json
{
  "success": true,
  "agency": "Test Agency",
  "records_imported": 2,
  "mapping_confidence": 0.95,
  "records": [...]
}
```

### Test 3: Create Profile

```bash
curl -X POST http://localhost:3001/api/profiles \
  -H "Content-Type: application/json" \
  -d '{
    "agency_name": "Test Agency",
    "record": {
      "name": "John Doe",
      "dob": "1950-06-15",
      "age": 75,
      "contact": "91234567",
      "emotion": "neutral",
      "problem_classes": ["Dementia", "Hypertension"],
      "special_case": null
    }
  }'
```

**Expected:**
```json
{
  "patient_id": "pat_000000",
  "created": true,
  "updated": false
}
```

### Test 4: Get Profile

```bash
# Get the patient_id from test 3 (should be pat_000000)
curl http://localhost:3001/api/profiles/pat_000000
```

**Expected:**
```json
{
  "patient_id": "pat_000000",
  "name": "John Doe",
  "dob": "1950-06-15",
  "age": 75,
  "contact": "91234567",
  "emotion": "neutral",
  "problem_classes": ["Dementia", "Hypertension"],
  "special_case": null,
  "agency_imports": {...},
  "last_updated": "...",
  "created_at": "..."
}
```

### Test 5: Start Voice Session

```bash
curl -X POST http://localhost:3001/api/voice/sessions/start \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": "pat_000000"
  }'
```

**Expected:**
```json
{
  "session_id": "sess_abc123",
  "patient_id": "pat_000000"
}
```

### Test 6: Send Voice Turn

```bash
# Get session_id from test 5
curl -X POST http://localhost:3001/api/voice/turn \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "sess_abc123",
    "patient_id": "pat_000000",
    "text": "I have a headache"
  }'
```

**Expected:**
```json
{
  "session_id": "sess_abc123",
  "user_input": "I have a headache",
  "assistant_response": "For headaches, you can consider...",
  "confidence": 0.85,
  "retrieved_sources": [...],
  "turn_count": 1
}
```

### Test 7: Check Response Quality (QA)

```bash
curl -X POST http://localhost:3001/api/qa/check-response \
  -H "Content-Type: application/json" \
  -d '{
    "response": "For headaches, ibuprofen is commonly used.",
    "confidence": 0.75,
    "retrieved_sources": [
      "Ibuprofen is an anti-inflammatory pain reliever."
    ]
  }'
```

**Expected:**
```json
{
  "response": "For headaches, ibuprofen is commonly used.",
  "confidence": 0.75,
  "confidence_level": "medium",
  "hallucination_check": {
    "is_hallucination": false,
    "score": 0.0,
    "reason": "Response matches sources"
  },
  "needs_review": false,
  "reason_for_review": null
}
```

### Test 8: Get Pending Reviews

```bash
curl http://localhost:3001/api/qa/reviews/pending
```

**Expected:**
```json
{
  "pending_count": 0,
  "items": []
}
```

---

## Troubleshooting

### "Cannot POST /api/adapter/import" (404)

**Issue:** Routes not registered in index.ts
**Fix:** Make sure you added the route imports and `app.use()` calls

### "ML_SERVICE_URL is not a valid URL"

**Issue:** Environment variable not set or invalid
**Fix:** Check `.env` has `ML_SERVICE_URL=http://localhost:8000`

### "connect ECONNREFUSED 127.0.0.1:8000"

**Issue:** ML service not running
**Fix:** Run `make docker-up` in another terminal

### "Cannot find module './routes/adapter'"

**Issue:** Route files not created
**Fix:** Copy the route files from this guide to `backend/src/routes/`

### Multipart form data errors

**Issue:** `multer` not installed
**Fix:** Run `npm install multer`

---

## Full Testing Script

Save as `test.sh` and run:

```bash
#!/bin/bash

set -e

BASE_URL="http://localhost:3001"
ML_URL="http://localhost:8000"

echo "🟢 Testing Dilly-Dell-E Backend Integration"
echo ""

# 1. Health check
echo "1️⃣ Health check..."
curl -s $BASE_URL/health | jq .
echo ""

# 2. Adapter import
echo "2️⃣ Adapter import..."
cat > /tmp/test.csv << 'EOF'
name,dob,contact,emotion,problem_classes
John Doe,1950-06-15,91234567,neutral,"Dementia, Hypertension"
EOF
IMPORT=$(curl -s -X POST $BASE_URL/api/adapter/import \
  -F "file=@/tmp/test.csv" \
  -F "agency_name=Test Agency")
echo $IMPORT | jq .
echo ""

# 3. Create profile
echo "3️⃣ Create profile..."
PROFILE=$(curl -s -X POST $BASE_URL/api/profiles \
  -H "Content-Type: application/json" \
  -d '{
    "agency_name": "Test Agency",
    "record": {
      "name": "John Doe",
      "dob": "1950-06-15",
      "age": 75,
      "contact": "91234567",
      "emotion": "neutral",
      "problem_classes": ["Dementia"],
      "special_case": null
    }
  }')
echo $PROFILE | jq .
PATIENT_ID=$(echo $PROFILE | jq -r '.patient_id')
echo "Patient ID: $PATIENT_ID"
echo ""

# 4. Get profile
echo "4️⃣ Get profile..."
curl -s $BASE_URL/api/profiles/$PATIENT_ID | jq .
echo ""

# 5. Start voice session
echo "5️⃣ Start voice session..."
SESSION=$(curl -s -X POST $BASE_URL/api/voice/sessions/start \
  -H "Content-Type: application/json" \
  -d "{\"patient_id\": \"$PATIENT_ID\"}")
echo $SESSION | jq .
SESSION_ID=$(echo $SESSION | jq -r '.session_id')
echo "Session ID: $SESSION_ID"
echo ""

# 6. Send voice turn
echo "6️⃣ Send voice turn..."
curl -s -X POST $BASE_URL/api/voice/turn \
  -H "Content-Type: application/json" \
  -d "{
    \"session_id\": \"$SESSION_ID\",
    \"patient_id\": \"$PATIENT_ID\",
    \"text\": \"I have a headache\"
  }" | jq .
echo ""

# 7. QA check
echo "7️⃣ QA check-response..."
curl -s -X POST $BASE_URL/api/qa/check-response \
  -H "Content-Type: application/json" \
  -d '{
    "response": "Ibuprofen can help.",
    "confidence": 0.8,
    "retrieved_sources": ["Ibuprofen is a pain reliever."]
  }' | jq .
echo ""

# 8. Pending reviews
echo "8️⃣ Pending reviews..."
curl -s $BASE_URL/api/qa/reviews/pending | jq .
echo ""

echo "✅ All tests passed!"
```

Run it:

```bash
chmod +x test.sh
./test.sh
```

---

## Next: Unreal Frontend

Once all tests pass and your friend finishes the Unreal app, update it to call:

```
Backend API Base: http://localhost:3001
(or https://your-domain.com when deployed)
```

Example Unreal code:

```cpp
// In Unreal C++
void PostVoiceTurn(const FString& SessionId, const FString& PatientId, const FString& TranscribedText)
{
    FString Url = FString::Printf(TEXT("http://localhost:3001/api/voice/turn"));
    FString JsonContent = FString::Printf(TEXT(
        "{\"session_id\":\"%s\",\"patient_id\":\"%s\",\"text\":\"%s\"}"),
        *SessionId, *PatientId, *TranscribedText
    );

    TSharedRef<IHttpRequest, ESPMode::ThreadSafe> Request = FHttpModule::Get().CreateRequest();
    Request->OnProcessRequestComplete().BindLambda([](FHttpRequestPtr Req, FHttpResponsePtr Res, bool bSuccess) {
        if (bSuccess && Res.IsValid()) {
            FString Response = Res->GetContentAsString();
            UE_LOG(LogTemp, Warning, TEXT("Voice response: %s"), *Response);
        }
    });

    Request->SetURL(Url);
    Request->SetVerb(TEXT("POST"));
    Request->SetHeader(TEXT("Content-Type"), TEXT("application/json"));
    Request->SetContentAsString(JsonContent);
    Request->ProcessRequest();
}
```

---

## Summary

| Step | Status | What to do |
|------|--------|-----------|
| 1. Copy route files | ✅ Done | Routes already created |
| 2. Update index.ts | 🟡 You do | Use `index.ts.new` template |
| 3. Set ML_SERVICE_URL | 🟡 You do | Add to `.env` |
| 4. Install multer | 🟡 You do | `npm install multer` |
| 5. Run tests | 🟡 You do | Use test script above |
| 6. Wait for Unreal | ⏳ Blocking | Then integrate frontend |

**Time estimate:** 30 minutes to integrate + test
