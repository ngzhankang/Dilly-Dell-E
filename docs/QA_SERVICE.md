# QA Service (Phase 4 & 5)

Quality Assurance pipeline for ensuring response reliability through automated checks and human review.

## Overview

The QA Service validates every response from the voice AI before it reaches the user:

1. **Confidence Gate** — Score responses on reliability
2. **Hallucination Check** — Verify claims against retrieved sources
3. **Escalation** — Route questionable responses to human review
4. **Audit Logging** — Track all interactions for compliance

---

## Architecture

### QA Service (`qa_service.py`)

Performs automated QA checks on responses.

**Methods:**
- `check_response(response, confidence, retrieved_sources)` → `QACheckResult`
  - Classifies confidence level (HIGH/MEDIUM/LOW)
  - Checks for hallucinations
  - Determines if needs human review
  
- `escalate_to_review(session_id, patient_id, user_input, response, confidence, hallucination_score)` → `review_id`
  - Adds response to review queue

- `log_interaction(session_id, patient_id, turn_count, user_input, response, confidence, hallucination_score, was_reviewed, review_action)` → `audit_id`
  - Logs every interaction for audit trail

### Review Queue Service (`review_service.py`)

Manages human reviewer workflow.

**Methods:**
- `get_pending_reviews(limit=50)` → `List[ReviewQueueItem]`
  - Dashboard of pending reviews

- `approve_review(review_id, reviewer_id, notes)` → `bool`
  - Accept LLM response as-is

- `reject_review(review_id, reviewer_id, notes)` → `bool`
  - Mark response as unsuitable (no alternative provided)

- `modify_and_approve(review_id, reviewer_id, approved_response, notes)` → `bool`
  - Provide corrected response

- `get_review_stats()` → `dict`
  - Queue statistics (total, pending, approved, rejected, modified)

---

## QA Logic

### Confidence Classification

```
score >= 0.8  →  HIGH     (Green) → No review needed
0.6-0.79      →  MEDIUM   (Yellow) → Optional review
< 0.6         →  LOW      (Red) → Escalate
```

### Hallucination Detection

**Algorithm:**
1. Extract sentences from response
2. For each sentence:
   - Extract key words (length > 4)
   - Check how many appear in retrieved sources
   - If < 30% matched → unmatched claim
3. Calculate hallucination score: `unmatched / (unmatched + matched)`
4. If score > 0.3 → likely hallucination

**Example:**

```
Response: "Ibuprofen is used for treating arthritis. 
           It should be taken with milk. 
           It cures cancer."

Sources: "Ibuprofen is a pain reliever. 
          Take with food or milk to prevent stomach upset."

Analysis:
- Sentence 1: "arthritis" → found in context ✓
- Sentence 2: "milk" → found ✓  
- Sentence 3: "cures cancer" → NOT found ✗

Hallucination score: 1/3 = 0.33 → LIKELY HALLUCINATION
```

### Escalation Criteria

Response is escalated to human review if:
- Confidence score < 0.7, OR
- Hallucination detected (score > 0.3)

---

## API Endpoints

### QA Check

**POST /qa/check-response**

```json
{
  "response": "Ibuprofen can help with arthritis pain.",
  "confidence": 0.75,
  "retrieved_sources": [
    "Ibuprofen is a pain reliever...",
    "Arthritis is a joint inflammation..."
  ]
}
```

**Response:**

```json
{
  "response": "Ibuprofen can help with arthritis pain.",
  "confidence": 0.75,
  "confidence_level": "medium",
  "hallucination_check": {
    "is_hallucination": false,
    "score": 0.1,
    "reason": "Response matches sources",
    "matched_sources": [...],
    "unmatched_claims": []
  },
  "needs_review": false,
  "reason_for_review": null
}
```

### Escalation

**POST /qa/escalate**

```json
{
  "session_id": "sess_abc123",
  "patient_id": "pat_001",
  "user_input": "What can I take for pain?",
  "response": "You can take ibuprofen...",
  "confidence": 0.65,
  "hallucination_score": 0.2
}
```

**Response:**

```json
{
  "review_id": "rev_xyz789",
  "status": "escalated"
}
```

### Review Queue

**GET /qa/reviews/pending?limit=50**

```json
{
  "pending_count": 3,
  "items": [
    {
      "review_id": "rev_abc123",
      "session_id": "sess_xyz",
      "patient_id": "pat_001",
      "user_input": "What medications can I take?",
      "llm_response": "You can take ibuprofen and paracetamol...",
      "confidence": 0.65,
      "hallucination_score": 0.2,
      "status": "pending",
      "created_at": "2026-06-18T12:00:00Z"
    }
  ]
}
```

**GET /qa/reviews/{review_id}**

Get a specific review item.

**POST /qa/reviews/{review_id}/approve**

```json
{
  "reviewer_id": "reviewer_alice",
  "notes": "Response is accurate and helpful."
}
```

**POST /qa/reviews/{review_id}/reject**

```json
{
  "reviewer_id": "reviewer_alice",
  "notes": "Contains potentially harmful medical advice."
}
```

**POST /qa/reviews/{review_id}/modify**

```json
{
  "reviewer_id": "reviewer_alice",
  "approved_response": "You should consult a doctor before taking ibuprofen...",
  "notes": "Added important safety disclaimer."
}
```

**GET /qa/reviews/stats**

```json
{
  "total": 47,
  "pending": 3,
  "approved": 35,
  "rejected": 5,
  "modified": 4
}
```

---

## Data Models

### QACheckResult

```python
{
  "response": str,
  "confidence": float,  # 0.0-1.0
  "confidence_level": "high" | "medium" | "low",
  "hallucination_check": {
    "is_hallucination": bool,
    "score": float,  # 0.0-1.0
    "reason": str,
    "matched_sources": List[str],
    "unmatched_claims": List[str]
  },
  "needs_review": bool,
  "reason_for_review": Optional[str]
}
```

### ReviewQueueItem

```python
{
  "review_id": str,
  "session_id": str,
  "patient_id": str,
  "user_input": str,
  "llm_response": str,
  "confidence": float,
  "hallucination_score": float,
  "status": "pending" | "approved" | "rejected" | "modified",
  "reviewer_notes": Optional[str],
  "approved_response": Optional[str],  # If modified
  "created_at": datetime,
  "reviewed_at": Optional[datetime],
  "reviewer_id": Optional[str]
}
```

### AuditLog

```python
{
  "audit_id": str,
  "session_id": str,
  "patient_id": str,
  "turn_count": int,
  "user_input": str,
  "llm_response": str,
  "confidence": float,
  "hallucination_score": float,
  "was_reviewed": bool,
  "review_action": Optional["approved" | "rejected" | "modified"],
  "timestamp": datetime
}
```

---

## Database Schema

### MongoDB Collections

**review_queue**
```javascript
{
  _id: ObjectId,
  review_id: String (unique),
  session_id: String,
  patient_id: String,
  user_input: String,
  llm_response: String,
  confidence: Number,
  hallucination_score: Number,
  status: String ("pending" | "approved" | "rejected" | "modified"),
  reviewer_notes: String,
  approved_response: String,
  created_at: Date,
  reviewed_at: Date,
  reviewer_id: String
}

// Indexes:
// - review_id (unique)
// - status + created_at (for pending reviews dashboard)
// - patient_id (for filtering by patient)
// - session_id (for filtering by session)
```

**audit_logs**
```javascript
{
  _id: ObjectId,
  audit_id: String (unique),
  session_id: String,
  patient_id: String,
  turn_count: Number,
  user_input: String,
  llm_response: String,
  confidence: Number,
  hallucination_score: Number,
  was_reviewed: Boolean,
  review_action: String,
  timestamp: Date
}

// Indexes:
// - audit_id (unique)
// - patient_id + timestamp (for querying by patient)
```

---

## Integration with Voice Gateway

Voice Gateway should call QA check BEFORE returning response:

```python
# In voice_gateway/orchestrator.py
async def process_user_input(session_id, patient_id, user_input):
    # ... get RAG response ...
    rag_result = await self.rag_pipeline.query(context_prompt)
    response = rag_result.get("answer")
    confidence = rag_result.get("confidence", 0.7)
    sources = rag_result.get("sources", [])
    
    # Check quality
    qa_result = await self.qa_service.check_response(
        response=response,
        confidence=confidence,
        retrieved_sources=sources
    )
    
    # Log interaction
    await self.qa_service.log_interaction(
        session_id=session_id,
        patient_id=patient_id,
        turn_count=turn_count,
        user_input=user_input,
        llm_response=response,
        confidence=qa_result.confidence,
        hallucination_score=qa_result.hallucination_check.score,
        was_reviewed=False  # updated later if human reviews
    )
    
    # Escalate if needed
    if qa_result.needs_review:
        review_id = await self.qa_service.escalate_to_review(
            session_id=session_id,
            patient_id=patient_id,
            user_input=user_input,
            response=response,
            confidence=qa_result.confidence,
            hallucination_score=qa_result.hallucination_check.score
        )
        # Return response with escalation notice
        return {
            "response": response,
            "escalated_for_review": True,
            "review_id": review_id
        }
    
    # Return response directly if high confidence
    return {
        "response": response,
        "escalated_for_review": False
    }
```

---

## Human Reviewer Workflow

### Scenario 1: Approve

Reviewer sees low-confidence response and verifies it's correct:

```bash
POST /qa/reviews/{review_id}/approve
{
  "reviewer_id": "alice_smith",
  "notes": "Verified against medical database. Accurate."
}
```

Status changes to `approved`. Patient gets the original response.

### Scenario 2: Reject

Reviewer identifies inaccuracy or harmful content:

```bash
POST /qa/reviews/{review_id}/reject
{
  "reviewer_id": "alice_smith",
  "notes": "Contains outdated dosage information. Rejected."
}
```

Status changes to `rejected`. Mobile app is notified to show fallback message ("Unable to provide answer, please consult a healthcare provider").

### Scenario 3: Modify & Approve

Reviewer corrects the response:

```bash
POST /qa/reviews/{review_id}/modify
{
  "reviewer_id": "alice_smith",
  "approved_response": "Ibuprofen is commonly used for arthritis pain. Always follow your doctor's dosage recommendations and take with food to prevent stomach upset.",
  "notes": "Added important safety warning."
}
```

Status changes to `modified`. Mobile app displays the corrected response instead.

---

## Compliance & Audit Trail

Every interaction is logged in `audit_logs`:

```json
{
  "audit_id": "audit_xyz123",
  "session_id": "sess_abc",
  "patient_id": "pat_001",
  "turn_count": 1,
  "user_input": "What pain medication can I take?",
  "llm_response": "Ibuprofen is recommended...",
  "confidence": 0.65,
  "hallucination_score": 0.15,
  "was_reviewed": true,
  "review_action": "modified",
  "timestamp": "2026-06-18T12:05:00Z"
}
```

Use audit logs for:
- **Compliance:** Prove all medical advice was reviewed
- **Bias Detection:** Identify if certain demographics get lower-quality responses
- **Training Data:** Build dataset of human-corrected responses
- **Incident Response:** Trace who reviewed what and when

---

## Hackathon Configuration

For the hackathon, default thresholds are:

| Setting | Value | Rationale |
|---------|-------|-----------|
| Confidence threshold | < 0.7 | Moderate threshold (medium/low gets escalated) |
| Hallucination threshold | > 0.3 | 30% unmatched claims triggers review |
| Max review queue | 50 pending | Limit reviewer workload |
| Hallucination detection | Keyword matching | Fast, no LLM overhead |

**For production, consider:**
- Tuning thresholds based on false positive/negative rates
- Using LLM-based hallucination checks (slower but more accurate)
- Adding confidence decay over time
- Automatic escalation to supervisor for > 5 rejections in a row

---

## Testing

### Manual Testing

```bash
# Check a low-confidence response
curl -X POST http://localhost:8000/qa/check-response \
  -H "Content-Type: application/json" \
  -d '{
    "response": "Ibuprofen cures arthritis permanently.",
    "confidence": 0.55,
    "retrieved_sources": ["Ibuprofen is a pain reliever for temporary relief."]
  }'

# Should return: needs_review = true, reason = "Low confidence score: 0.55"

# Escalate to review
curl -X POST http://localhost:8000/qa/escalate \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "sess_test",
    "patient_id": "pat_test",
    "user_input": "What medication?",
    "response": "...",
    "confidence": 0.55,
    "hallucination_score": 0.4
  }'

# Get pending reviews
curl http://localhost:8000/qa/reviews/pending

# Approve a review
curl -X POST http://localhost:8000/qa/reviews/{review_id}/approve \
  -H "Content-Type: application/json" \
  -d '{
    "reviewer_id": "test_reviewer",
    "notes": "Verified."
  }'
```

### Unit Tests

Test files: `tests/qa_service/`

```python
# test_hallucination_check.py
def test_exact_match():
    # All sentences match sources → score = 0.0
    pass

def test_no_match():
    # All sentences unmatched → score = 1.0
    pass

def test_partial_match():
    # 50% unmatched → is_hallucination = True
    pass

# test_confidence_classification.py
def test_high_confidence():
    assert classify_confidence(0.85) == "high"

def test_low_confidence():
    assert classify_confidence(0.55) == "low"
```

---

## Future Enhancements

1. **LLM-based Hallucination Check**
   - Use another LLM to verify claims
   - More accurate but slower

2. **Multi-turn Hallucination Detection**
   - Check for contradictions across conversation
   - "I said X but now I'm saying not-X"

3. **Confidence Feedback Loop**
   - When reviewers approve/reject, retrain confidence model
   - Personalize thresholds by medical domain (cardiology vs dermatology)

4. **Automatic Escalation Rules**
   - Route certain domains (medication) to specialized reviewers
   - Route high-urgency queries (patient in pain) to fast-track reviewers

5. **Reviewer Metrics**
   - Approval rate, average review time
   - Performance dashboard for QA manager

6. **Content Filtering**
   - Pre-check responses against blocked medical claims
   - Prevent spreading of known misinformation
