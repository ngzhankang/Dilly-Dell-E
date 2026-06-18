#!/bin/bash

set -e

echo "======================================"
echo "Form Adapter Testing Script"
echo "======================================"
echo ""

# Check if ML service is running
echo "📋 Checking ML service health..."
if ! curl -s http://localhost:8000/health | grep -q "ok"; then
    echo "❌ ML service is not running. Start it with: make ml-dev"
    exit 1
fi
echo "✅ ML service is running"
echo ""

# Create temp directory for test files
TEMP_DIR="/tmp/adapter_test"
mkdir -p "$TEMP_DIR"

echo "========== TEST 1: CSV IMPORT =========="
echo "Testing CSV ingestion with Care Corner format..."
echo ""

# Extract first few rows from sample data for testing
head -6 docs/sample_interrai_data.csv > "$TEMP_DIR/care_corner_test.csv"

echo "📤 Uploading CSV file..."
RESPONSE=$(curl -s -X POST http://localhost:8000/adapter/import \
  -F "file=@$TEMP_DIR/care_corner_test.csv" \
  -F "agency_name=Care Corner")

echo "Response:"
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
echo ""

# Extract confidence from response
CONFIDENCE=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('mapping_confidence', 0))" 2>/dev/null || echo "0")
echo "Mapping Confidence: $CONFIDENCE"

if (( $(echo "$CONFIDENCE > 0.7" | bc -l) )); then
    echo "✅ Confidence is good (> 0.7)"
else
    echo "⚠️  Confidence is low (< 0.7) — may need mapping tuning"
fi
echo ""

echo "========== TEST 2: JSON IMPORT =========="
echo "Testing JSON ingestion with AIC format..."
echo ""

# Extract AIC data from JSON sample
python3 << 'PYEOF'
import json

with open('docs/sample_agency_formats.json') as f:
    data = json.load(f)

with open('/tmp/adapter_test/aic_test.json', 'w') as f:
    json.dump(data['aic_export'], f, indent=2)

print(f"Created test file with {len(data['aic_export'])} AIC records")
PYEOF

echo "📤 Uploading JSON file..."
RESPONSE=$(curl -s -X POST http://localhost:8000/adapter/import \
  -F "file=@$TEMP_DIR/aic_test.json" \
  -F "agency_name=AIC")

echo "Response:"
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
echo ""

echo "========== TEST 3: DEMENTIA SINGAPORE =========="
echo "Testing different agency format with unique field names..."
echo ""

# Extract Dementia Singapore data
python3 << 'PYEOF'
import json

with open('docs/sample_agency_formats.json') as f:
    data = json.load(f)

with open('/tmp/adapter_test/dementia_sg_test.json', 'w') as f:
    json.dump(data['dementia_singapore_export'], f, indent=2)

print(f"Created test file with {len(data['dementia_singapore_export'])} Dementia Singapore records")
PYEOF

echo "📤 Uploading JSON file..."
RESPONSE=$(curl -s -X POST http://localhost:8000/adapter/import \
  -F "file=@$TEMP_DIR/dementia_sg_test.json" \
  -F "agency_name=Dementia Singapore")

echo "Response:"
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
echo ""

echo "========== TEST SUMMARY =========="
echo "✅ All tests completed successfully!"
echo ""
echo "📊 Test artifacts saved to: $TEMP_DIR"
echo ""
echo "Next steps:"
echo "1. Review the mapping confidence scores above"
echo "2. Check the normalized records in the response"
echo "3. For backend integration test: make docker-up && test with /api/admin/import-agency-form"
echo "4. Verify MongoDB records: docker exec mongo mongosh --eval \"db.agencyimports.find().pretty()\""
echo ""
