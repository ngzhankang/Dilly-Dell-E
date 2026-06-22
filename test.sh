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
