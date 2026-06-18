# Form Adapter Testing Guide

## Sample Data Overview

Two realistic sample datasets have been created based on the **interRAI Community for Usual Care (CU)** assessment form:

### 1. **CSV Format** (`docs/sample_interrai_data.csv`)
- 5 synthetic patient records
- Structured like a typical agency export
- Fields include: demographics, cognitive assessment, ADL/IADL status, diagnoses, care needs
- Best for testing CSV ingestion and field mapping

### 2. **JSON Format** (`docs/sample_agency_formats.json`)
- 5 synthetic records from 3 different agencies (Care Corner, AIC, Dementia Singapore)
- **Each agency uses different field naming conventions** — perfect for testing semantic mapping
- Demonstrates real-world terminology variations

---

## Field Mapping Examples

The adapter should intelligently handle these field name variations:

### Patient Demographics
| Care Corner | AIC | Dementia Singapore | **Unified Schema** |
|---|---|---|---|
| `pt_name` | `full_name` | `client_name` | `name` |
| `date_of_birth` | `dob` | `birth_date` | `dob` |
| `sex` | `gender` | `sex` | (derived) |
| `phone` | `contact_phone` | `mobile` | `contact` |
| `preferred_lang` | `language` | `communication_language` | (derived) |

### Cognitive & Mental Status
| Care Corner | AIC | Dementia Singapore | **Unified Schema** |
|---|---|---|---|
| `cognitive_assessment` | `cognition_status` | `mental_status` | (derived) |
| `mood` | `emotional_state` | `psychological_status` | `emotion` |
| `behavior` | `behavior_issues` | `behavioral_concerns` | `special_case` |

### Medical Conditions
| Care Corner | AIC | Dementia Singapore | **Unified Schema** |
|---|---|---|---|
| `primary_condition` | `main_diagnosis` | `presenting_diagnosis` | `problem_classes` |
| `secondary_conditions` | `comorbidities` | `associated_medical_conditions` | `problem_classes` |
| `pain_level` | `discomfort_level` | `pain_assessment` | (derived) |

### Functional Status
| Care Corner | AIC | Dementia Singapore | **Unified Schema** |
|---|---|---|---|
| `eating_ability` | `eat_independence` | `self_care_eating` | (derived) |
| `fall_risk_level` | `fall_likelihood` | `injury_risk_assessment` | `special_case` |

---

## Testing Scenarios

### Scenario 1: CSV Import (Care Corner)

**Test Case:** Import typical Care Corner export in CSV format

```bash
# 1. Extract Care Corner data from the CSV
head -2 docs/sample_interrai_data.csv > /tmp/care_corner.csv
tail -4 docs/sample_interrai_data.csv >> /tmp/care_corner.csv

# 2. Test ML Service endpoint
curl -X POST http://localhost:8000/adapter/import \
  -F "file=@/tmp/care_corner.csv" \
  -F "agency_name=Care Corner"
```

**Expected Output:**
```json
{
  "success": true,
  "agency": "Care Corner",
  "records_normalized": 4,
  "mapping_confidence": 0.90,
  "unmapped_fields": []
}
```

---

### Scenario 2: JSON Import with Terminology Variations

**Test Case:** Import from different agency (different field names, same meaning)

```bash
# 1. Extract AIC data from JSON
python3 << 'EOF'
import json

with open('docs/sample_agency_formats.json') as f:
    data = json.load(f)
    
with open('/tmp/aic_export.json', 'w') as f:
    json.dump(data['aic_export'], f, indent=2)
EOF

# 2. Test ML Service endpoint
curl -X POST http://localhost:8000/adapter/import \
  -F "file=@/tmp/aic_export.json" \
  -F "agency_name=AIC"
```

**Expected Output:**
```json
{
  "success": true,
  "agency": "AIC",
  "records_normalized": 2,
  "mapping_confidence": 0.88,
  "sample_record": {
    "name": "Muhammad Ali Hassan",
    "dob": "1942-11-08",
    "contact": "93456789",
    "problem_classes": ["Parkinson's", "Diabetes", "Hypertension"],
    "special_case": "High fall risk"
  }
}
```

---

### Scenario 3: Dementia Singapore Export

**Test Case:** Import from another agency with unique field names

```bash
# 1. Extract Dementia Singapore data
python3 << 'EOF'
import json

with open('docs/sample_agency_formats.json') as f:
    data = json.load(f)
    
with open('/tmp/dementia_sg_export.json', 'w') as f:
    json.dump(data['dementia_singapore_export'], f, indent=2)
EOF

# 2. Test endpoint
curl -X POST http://localhost:8000/adapter/import \
  -F "file=@/tmp/dementia_sg_export.json" \
  -F "agency_name=Dementia Singapore"
```

---

## What to Verify

After running each test, verify:

### ✓ Mapping Confidence
- Should be **> 0.85** for standard fields (name, dob, diagnoses)
- May be **0.7–0.85** for less common fields (behavior assessments)
- If < 0.7, inspect the LLM mapping logs

### ✓ Field Mapping Accuracy
- Patient names correctly identified as `name`
- DOB variants (`dob`, `date_of_birth`, `birth_date`) → `dob`
- Diagnosis fields → `problem_classes` (as array)
- Mood/emotional fields → `emotion` (one of: happy, neutral, worried, confused)
- Risk/behavior flags → `special_case`

### ✓ Sample Record Structure
```python
{
  "name": str,
  "dob": str,
  "contact": str or None,
  "emotion": str or None,
  "problem_classes": list,
  "special_case": str or None
}
```

### ✓ Unmapped Fields
Log which fields couldn't be mapped. Examples:
- `assessor_name` → (no direct mapping)
- `facility_name` → (metadata, not patient data)
- Agency-specific codes → (domain knowledge needed)

---

## Advanced Testing

### 1. **Test Low-Confidence Scenarios**

Create a CSV with unusual field names:

```csv
weird_name_field,weird_dob_field,weird_diagnosis
John,1950,D12345
Jane,1955,D67890
```

Expected: confidence < 0.7, with warnings in logs

```bash
curl -X POST http://localhost:8000/adapter/import \
  -F "file=@/tmp/weird_fields.csv" \
  -F "agency_name=Unknown Agency"
```

### 2. **Test Empty/Null Handling**

```csv
patient_name,dob,diagnosis
John Doe,1950-06-15,
Jane Smith,,F03
```

Expected: Missing values are handled gracefully; `problem_classes` is empty array if null

### 3. **Performance Testing**

Generate a larger dataset:

```bash
python3 << 'EOF'
import csv
import random
from datetime import datetime, timedelta

names = ["Lim", "Chan", "Muhammad", "Tan", "Wong", "Ng", "Lee", "Ong", "Goh", "Chua"]
diagnoses = ["Dementia", "Parkinson's", "Stroke", "Heart Failure", "Diabetes", "Hypertension"]

with open('/tmp/large_dataset.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['Patient_ID', 'Patient_Name', 'Date_of_Birth', 'Primary_Diagnosis'])
    
    for i in range(100):
        name = f"{random.choice(names)} Patient {i}"
        dob = (datetime.now() - timedelta(days=random.randint(20000, 40000))).strftime('%Y-%m-%d')
        diagnosis = random.choice(diagnoses)
        writer.writerow([i, name, dob, diagnosis])

print("Generated 100 records")
EOF

curl -X POST http://localhost:8000/adapter/import \
  -F "file=@/tmp/large_dataset.csv" \
  -F "agency_name=Test Agency Large"
```

Expected: Should complete in < 30 seconds; records_normalized = 100

---

## Real Adapter Usage with Actual interRAI Form

Once you test with synthetic data, use the actual form:

1. **Extract from PDF:** Manually fill out the interRAI form (or get filled forms from agencies)
2. **Export as CSV/JSON:** Convert form data to CSV or JSON
3. **Map field names:** Create a mapping file that shows how agency field names relate to the form
4. **Upload via adapter:** Let the LLM do semantic matching
5. **Verify results:** Check MongoDB for normalized records

---

## Troubleshooting

### "LLM returned invalid JSON"
- Check ML service logs: `docker logs ml-service`
- The LLM response may not be valid JSON if the prompt is unclear
- Try simplifying the field names in the input

### "Confidence too low (< 0.7)"
- Field names are too ambiguous
- Add more context to the first row of sample data
- Update the LLM system prompt to include more healthcare terminology

### "MongoDB connection error"
- Check MONGO_URI in `.env`
- Ensure MongoDB is running: `docker ps | grep mongo`
- Verify connection: `docker exec mongo mongosh --eval "db.version()"`

### "Timeout during import"
- Large files may take time
- Increase timeout in backend route (currently 60s)
- Consider chunking large imports into smaller batches

---

## Sample Data Cleanup

To remove test data from MongoDB:

```bash
docker exec mongo mongosh << 'EOF'
use hackathon
db.agencyimports.deleteMany({ agency: "Test Agency" })
db.agencyimports.find().count()
EOF
```

---

## Next Steps

1. **Test with synthetic data** (CSV and JSON samples provided)
2. **Verify mapping accuracy** for your agencies
3. **Collect real form exports** from Care Corner, AIC, Dementia Singapore
4. **Fine-tune the LLM prompt** if certain mappings are consistently low-confidence
5. **Deploy to production** with confidence thresholds for automatic vs. manual review
