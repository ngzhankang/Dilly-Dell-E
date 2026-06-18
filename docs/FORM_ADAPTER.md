# Agency Form Adapter — Semantic Field Mapping

## Overview

The form adapter enables importing patient assessment data from multiple agencies with **fragmented data formats** (HTML forms, Excel, CSV, JSON) and automatically **normalizes** them to your unified patient schema using LLM-powered semantic field mapping.

**Key capability:** The LLM (SEA-LION) understands that `date_of_birth`, `DOB`, `birth_date`, and `yob` all mean the same thing — and maps them intelligently without hardcoding per-agency rules.

---

## Architecture

```
┌─────────────────────────┐
│  Agency Data (CSV/JSON) │
└──────────┬──────────────┘
           │
    ┌──────▼──────────┐
    │  Ingest Layer   │   Extract raw fields
    │  (parse format) │
    └──────┬──────────┘
           │
    ┌──────▼──────────────┐
    │  LLM Field Mapper    │   Semantic mapping
    │  (SEA-LION)          │   "dob" → "dob"
    │                      │   "diagnosis_code" → "problem_classes"
    └──────┬──────────────┘
           │
    ┌──────▼──────────────┐
    │  Normalized Schema   │   Unified record
    └──────┬──────────────┘
           │
    ┌──────▼──────────────┐
    │  MongoDB Storage     │   Persisted import
    └─────────────────────┘
```

---

## End-to-End Flow

### 1. **User Uploads File**

```bash
curl -X POST http://localhost:3001/api/admin/import-agency-form \
  -F "file=@care_corner_export.csv" \
  -F "agency_name=Care Corner"
```

### 2. **Backend Receives & Forwards to ML Service**

```typescript
POST /api/admin/import-agency-form
  ├─ Save file to temp location
  ├─ Call ML service: POST /adapter/import
  ├─ Receive normalized records + mapping metadata
  └─ Store in MongoDB
```

### 3. **ML Service: Parse & Map**

```python
POST /adapter/import
  ├─ Ingest: Parse CSV/JSON
  │  └─ Raw fields: {patient_name, dob, diagnosis_code, ...}
  │
  ├─ Map: Call LLM
  │  └─ "Map these fields to our schema"
  │
  ├─ LLM Response:
  │  {
  │    "mappings": {
  │      "patient_name" → "name",
  │      "dob" → "dob",
  │      "diagnosis_code" → "problem_classes"
  │    },
  │    "confidence": 0.92
  │  }
  │
  ├─ Normalize: Apply mapping
  │  └─ Transform records to unified schema
  │
  └─ Return normalized data + metadata
```

### 4. **Backend Stores & Responds**

```json
{
  "success": true,
  "agency": "Care Corner",
  "records_imported": 42,
  "mapping_confidence": 0.92,
  "unmapped_fields": ["staff_notes"],
  "sample_record": {
    "name": "John Doe",
    "dob": "1950-05-15",
    "emotion": "neutral",
    "problem_classes": ["F03"],
    "special_case": null
  },
  "db_import_id": "...",
  "mapping_metadata": {
    "source_to_target": {...},
    "confidence": 0.92
  }
}
```

---

## Unified Schema

All imported records are normalized to this schema:

```python
{
  "name": str,                           # Patient name
  "dob": str,                            # Date of birth (YYYY-MM-DD)
  "age": int,                            # Age in years (optional)
  "contact": str,                        # Phone/email (optional)
  "emotion": "happy|neutral|worried|confused",  # Emotional state
  "problem_classes": list[str],          # Diagnoses/conditions
  "special_case": str                    # Red flags, urgent notes
}
```

---

## Supported File Formats

| Format | Extension | Parser | Note |
|---|---|---|---|
| **CSV** | `.csv` | pandas | Fast, handles headers |
| **Excel** | `.xlsx`, `.xls` | pandas + openpyxl | Supports multiple sheets |
| **JSON** | `.json` | json (native) | Array of objects or single object |
| **HTML** | (future) | BeautifulSoup + Selenium | Web form scraping (planned) |

---

## API Endpoints

### Backend: Import Agency Form

```
POST /api/admin/import-agency-form

Headers:
  Content-Type: multipart/form-data

Body:
  file: <CSV/Excel/JSON file>
  agency_name: "Care Corner" | "AIC" | "Dementia Singapore"

Response (200):
{
  "success": true,
  "agency": string,
  "records_imported": number,
  "mapping_confidence": 0.0-1.0,
  "unmapped_fields": string[],
  "sample_record": {...},
  "db_import_id": string,
  "mapping_metadata": {...}
}

Response (400/500):
{
  "error": "Reason for failure"
}
```

### ML Service: Adapter Import (internal)

```
POST /adapter/import

Body: multipart/form-data
  file: <uploaded file>
  agency_name: string

Response:
{
  "success": true | false,
  "agency": string,
  "records_normalized": number,
  "mapping_confidence": 0.0-1.0,
  "unmapped_fields": string[],
  "records": [...],
  "mapping_metadata": {
    "source_to_target": {...},
    "confidence": 0.0-1.0,
    "unmapped": string[]
  }
}
```

---

## Usage Examples

### Example 1: Import Care Corner CSV

**File:** `care_corner_export.csv`
```csv
patient_name,dob,diagnosis_code,mobility_status,contact_phone
John Doe,1950-05-15,F03,bedridden,98765432
Jane Smith,1955-03-20,G30,assisted walking,91234567
```

**Request:**
```bash
curl -X POST http://localhost:3001/api/admin/import-agency-form \
  -F "file=@care_corner_export.csv" \
  -F "agency_name=Care Corner"
```

**Response:**
```json
{
  "success": true,
  "agency": "Care Corner",
  "records_imported": 2,
  "mapping_confidence": 0.95,
  "sample_record": {
    "name": "John Doe",
    "dob": "1950-05-15",
    "problem_classes": ["F03"],
    "special_case": "bedridden"
  }
}
```

---

### Example 2: Import AIC JSON

**File:** `aic_patients.json`
```json
[
  {
    "pt_name": "Alice Wong",
    "birth_date": "1948-01-10",
    "current_condition": "Parkinson's",
    "phone": "91234567"
  },
  {
    "pt_name": "Bob Tan",
    "birth_date": "1952-07-22",
    "current_condition": "Stroke recovery",
    "phone": "98765432"
  }
]
```

**Request:**
```bash
curl -X POST http://localhost:3001/api/admin/import-agency-form \
  -F "file=@aic_patients.json" \
  -F "agency_name=AIC"
```

**Response:**
```json
{
  "success": true,
  "agency": "AIC",
  "records_imported": 2,
  "mapping_confidence": 0.88,
  "sample_record": {
    "name": "Alice Wong",
    "dob": "1948-01-10",
    "contact": "91234567",
    "problem_classes": ["Parkinson's"]
  }
}
```

---

### Example 3: Using Postman

**Steps:**
1. Set method to `POST`
2. URL: `http://localhost:3001/api/admin/import-agency-form`
3. Go to **Body** tab → Select **form-data**
4. Add rows:
   - Key: `file`, Type: **File**, Value: select CSV/Excel/JSON
   - Key: `agency_name`, Type: **Text**, Value: `Care Corner`
5. Click **Send**

---

## How It Works: Field Mapping

The LLM is given the agency name and raw field names, then asked to map them semantically:

### LLM Prompt
```
Agency: Care Corner

Raw fields from their form:
["patient_name", "dob", "diagnosis_code", "mobility_status"]

First row of sample data:
{"patient_name": "John Doe", "dob": "1950-05-15", "diagnosis_code": "F03", "mobility_status": "bedridden"}

Please map these fields to our unified schema.

Available fields:
- name (patient name)
- dob (date of birth, format: YYYY-MM-DD)
- age (age in years)
- contact (phone/email)
- emotion (happy, neutral, worried, confused)
- problem_classes (list of diagnoses/conditions)
- special_case (red flags, urgent notes)
```

### LLM Response
```json
{
  "mappings": {
    "patient_name": "name",
    "dob": "dob",
    "diagnosis_code": "problem_classes",
    "mobility_status": "special_case"
  },
  "confidence": 0.95,
  "unmapped_fields": [],
  "notes": "Diagnosis code F03 (ICD-10 Dementia) mapped to problem_classes. Mobility status treated as special case for care planning."
}
```

---

## Confidence Score

The LLM returns a `confidence` score (0.0–1.0) indicating how certain it is about the mapping quality.

| Confidence | Interpretation |
|---|---|
| **> 0.9** | Highly confident; field names are clear and unambiguous |
| **0.7–0.9** | Reasonably confident; some terminology variations handled well |
| **0.5–0.7** | Moderate confidence; some ambiguity or non-standard fields |
| **< 0.5** | Low confidence; may have interpretation issues; review recommended |

**Recommendation:** Always review imports with confidence < 0.7 before using in production.

---

## Error Handling

### Common Errors

#### 1. **Unsupported file format**
```json
{
  "error": "Unsupported file format: docx. Supported: csv, xlsx, xls, json"
}
```
**Fix:** Convert to CSV, Excel, or JSON.

#### 2. **Empty file**
```json
{
  "error": "Uploaded file is empty"
}
```
**Fix:** Ensure the file contains data.

#### 3. **Invalid JSON**
```json
{
  "error": "Failed to parse JSON file: ..."
}
```
**Fix:** Validate JSON format using `jq` or a JSON linter.

#### 4. **ML service timeout**
```json
{
  "error": "Failed to import agency data: timeout"
}
```
**Fix:** Check that the ML service is running (`curl http://localhost:8000/health`).

#### 5. **MongoDB connection error**
```json
{
  "error": "Failed to save import to database"
}
```
**Fix:** Check MongoDB is running and `MONGO_URI` is set in `.env`.

---

## Testing

### Local Test (ML Service Only)

```bash
cd ml
python -m pytest tests/test_adapter.py -v
```

### End-to-End Test (with Backend)

```bash
# 1. Start all services
make docker-up

# 2. Create test CSV
cat > /tmp/test.csv << EOF
patient_name,dob,diagnosis_code
John Doe,1950-05-15,F03
Jane Smith,1955-03-20,G30
EOF

# 3. Upload file
curl -X POST http://localhost:3001/api/admin/import-agency-form \
  -F "file=@/tmp/test.csv" \
  -F "agency_name=Test Agency"

# 4. Check MongoDB
docker exec dilly-dell-e-mongo-1 mongosh --eval "db.agencyimports.findOne()"
```

---

## Best Practices

1. **Test with 2-3 sample records** before uploading large batches
2. **Review mapping confidence** — if < 0.7, inspect the mapping manually
3. **Keep unique identifiers** — if the file has `patient_id`, store it in `agency_patient_id` field for linking
4. **Validate data quality** — clean up null/empty fields before upload
5. **Monitor for errors** — check logs if imports fail
6. **Version your imports** — MongoDB timestamps each import for audit trail

---

## Limitations & Future Work

### Current Limitations
- HTML web form scraping not yet implemented (planned)
- No real-time syncing from agencies
- Mapping confidence based on LLM, not guaranteed 100% accuracy

### Future Enhancements
- **Web form scraping** for agencies with online forms
- **Scheduled syncing** for agencies with APIs
- **Manual mapping override** for low-confidence fields
- **Bulk validation** UI for reviewing mappings before import
- **Field value normalization** (e.g., standardize age ranges, emotion labels)

---

## Architecture Files

- **ML Service:**
  - `ml/app/adapters/ingestors/base.py` — Abstract ingestor
  - `ml/app/adapters/ingestors/csv_ingestor.py` — CSV/Excel parsing
  - `ml/app/adapters/ingestors/json_ingestor.py` — JSON parsing
  - `ml/app/adapters/llm_field_mapper.py` — LLM-powered field mapping
  - `ml/app/adapters/mapper.py` — Orchestration
  - `ml/app/main.py` — `/adapter/import` endpoint

- **Backend:**
  - `backend/src/models/AgencyImport.ts` — Mongoose schema
  - `backend/src/routes/admin/import.ts` — Express route handler

---

## References

- **Unified Schema:** `backend/src/models/AgencyImport.ts`
- **LLM Prompt Template:** `ml/app/adapters/llm_field_mapper.py`
- **Test Suite:** `ml/tests/test_adapter.py`
