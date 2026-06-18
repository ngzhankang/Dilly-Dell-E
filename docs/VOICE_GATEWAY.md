# Voice Gateway & Turn Orchestrator (Phase 3)

Conversation management and voice interaction layer for patient-AI dialogue.

## Overview

**Turn Orchestrator:** Manages conversation sessions and maintains history
**Voice Gateway:** Handles voice I/O, coordinates all services

Together they:
1. Create conversation sessions (session storage)
2. Maintain patient context (cached from Profile Builder)
3. Route user input through RAG + QA pipeline
4. Store conversation history for audit & learning

---

## Architecture

### Session Model

```python
{
  "session_id": "sess_abc123",
  "patient_id": "pat_001",
  "turns": [
    {
      "type": "user",
      "content": "I have a headache",
      "timestamp": "2026-06-18T12:00:00Z"
    },
    {
      "type": "assistant",
      "content": "I understand. Have you taken any medication?",
      "confidence": 0.95,
      "timestamp": "2026-06-18T12:00:01Z"
    }
  ],
  "patient_context": {
    "name": "John Doe",
    "age": 75,
    "problem_classes": ["Dementia", "Hypertension"]
  },
  "created_at": "2026-06-18T12:00:00Z",
  "last_activity": "2026-06-18T12:00:01Z",
  "status": "active"
}
```

### Turn Model

```python
{
  "type": "user" | "assistant",
  "content": str,
  "timestamp": datetime,
  "confidence": Optional[float]  # For assistant turns only
}
```

---

## Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    User (mobile)                            │
│              [speaks question via audio]                    │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │ Whisper (mobile-side)  │
        │ transcribe: audio→text │
        └────────────┬───────────┘
                     │
                     ▼
        ┌────────────────────────────────────────┐
        │  POST /voice/turn                      │
        │  {                                     │
        │    session_id: str,                    │
        │    patient_id: str,                    │
        │    text: "What can I take for pain?"   │
        │  }                                     │
        └────────────┬───────────────────────────┘
                     │
                     ▼
    ┌─────────────────────────────────────────┐
    │    VoiceOrchestrator.process_user_input │
    │                                         │
    │  1. Get/create session                 │
    │  2. Fetch patient context              │
    │  3. Augment input with context         │
    │  4. Query RAG pipeline                 │
    │  5. Store turn in session              │
    │  6. Return response + confidence       │
    └─────────────┬──────────────────────────┘
                  │
        ┌─────────┴──────────┬──────────────┐
        ▼                    ▼              ▼
    RAGPipeline      ProfileService    TurnService
   (get response)   (get context)    (store history)
        │                    │              │
        └────────────┬───────┴──────────────┘
                     │
                     ▼
        ┌────────────────────────────────────┐
        │ Return TurnResponse:               │
        │ {                                  │
        │   response: "Ibuprofen...",       │
        │   confidence: 0.85,                │
        │   sources: [...]                   │
        │ }                                  │
        └────────────┬───────────────────────┘
                     │
                     ▼
        ┌────────────────────────────────────┐
        │  Text-to-Speech (mobile-side)      │
        │  synthesize: text→audio            │
        └────────────┬───────────────────────┘
                     │
                     ▼
        ┌────────────────────────────────────┐
        │    User (mobile)                   │
        │    [hears response via audio]      │
        └────────────────────────────────────┘
```

---

## API Endpoints

### Start Session

**POST /voice/sessions/start**

Create a new conversation session.

```json
{
  "patient_id": "pat_001"
}
```

**Response:**

```json
{
  "session_id": "sess_abc123",
  "patient_id": "pat_001"
}
```

### Process Turn

**POST /voice/turn**

Process a single conversation turn (user input → AI response).

```json
{
  "session_id": "sess_abc123",
  "patient_id": "pat_001",
  "text": "What can I take for pain?"
}
```

**Response:**

```json
{
  "session_id": "sess_abc123",
  "user_input": "What can I take for pain?",
  "assistant_response": "For pain relief, common options include ibuprofen (for inflammation) or acetaminophen (for general pain). Always consult your doctor before starting new medications.",
  "confidence": 0.87,
  "retrieved_sources": [
    "Ibuprofen is an anti-inflammatory medication...",
    "Acetaminophen is used for pain and fever..."
  ],
  "turn_count": 2
}
```

### End Session

**POST /voice/sessions/{session_id}/end**

Close a conversation session.

**Response:**

```json
{
  "session_id": "sess_abc123",
  "status": "closed"
}
```

### Health Check

**GET /voice/health/ready**

Check if Voice Gateway is ready.

**Response:**

```json
{
  "status": "ready",
  "services": {
    "turn_service": true,
    "profile_service": true
  }
}
```

---

## Context Augmentation

Voice Orchestrator augments user input with patient context to make responses personalized:

**Original user input:**
```
"I have a headache"
```

**Augmented context prompt sent to RAG:**
```
Patient: John Doe, Age: 75, Conditions: Dementia, Hypertension

Recent conversation:
User: I have a headache
Assistant: I understand. Have you taken any medication?

User: I have a headache
```

This helps the RAG pipeline:
- Avoid recommending contraindicated medications (e.g., NSAIDs for someone on blood thinners)
- Tailor explanations for the patient's age/condition
- Maintain conversation context across turns

---

## Session Management

### Auto-Cleanup

Sessions are created on-demand. For cleanup:

**Option 1: Explicit close**
```bash
POST /voice/sessions/{session_id}/end
```

**Option 2: TTL-based (future)**
```
Sessions auto-close after 30 minutes of inactivity
```

### Query Session History

Get recent turns from a session:

```python
session = await turn_service.get_session(session_id)
recent_turns = session.turns[-5:]  # Last 5 turns
```

---

## Integration with QA Service

Voice Orchestrator should coordinate with QA after RAG response:

```python
# In VoiceOrchestrator.process_user_input

# Get RAG response
rag_result = await self.rag_pipeline.query(context_prompt)
response = rag_result.get("answer")
confidence = rag_result.get("confidence")
sources = rag_result.get("sources")

# Check quality via QA
qa_result = await self.qa_service.check_response(
    response=response,
    confidence=confidence,
    retrieved_sources=sources
)

# If needs review, escalate
if qa_result.needs_review:
    review_id = await self.qa_service.escalate_to_review(...)
    # Mark response as pending review
    response_status = "pending_review"
else:
    response_status = "approved"

# Store turn
await self.turn_service.add_turn(
    session_id=session_id,
    turn_type=TurnType.ASSISTANT,
    content=response,
    confidence=qa_result.confidence
)

# Log to audit trail
await self.qa_service.log_interaction(
    session_id=session_id,
    patient_id=patient_id,
    turn_count=len(session.turns) + 1,
    user_input=user_input,
    llm_response=response,
    confidence=qa_result.confidence,
    hallucination_score=qa_result.hallucination_check.score,
    was_reviewed=qa_result.needs_review
)

return TurnResponse(
    session_id=session_id,
    user_input=user_input,
    assistant_response=response,
    confidence=qa_result.confidence,
    retrieved_sources=sources,
    turn_count=turn_count,
    review_status=response_status
)
```

---

## Database Schema

### MongoDB: conversation_sessions

```javascript
{
  _id: ObjectId,
  session_id: String (unique),
  patient_id: String,
  turns: [
    {
      type: String ("user" | "assistant"),
      content: String,
      timestamp: Date,
      confidence: Number
    }
  ],
  patient_context: Object,
  created_at: Date,
  last_activity: Date,
  status: String ("active" | "paused" | "closed")
}

// Indexes:
// - session_id (unique)
// - patient_id
// - created_at
```

---

## Testing

### Manual Testing

```bash
# 1. Start a session
curl -X POST http://localhost:8000/voice/sessions/start \
  -H "Content-Type: application/json" \
  -d '{"patient_id": "pat_001"}'

# Response:
# {"session_id": "sess_xyz123", "patient_id": "pat_001"}

# 2. Send a turn
curl -X POST http://localhost:8000/voice/turn \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "sess_xyz123",
    "patient_id": "pat_001",
    "text": "I have a headache"
  }'

# Response:
# {
#   "session_id": "sess_xyz123",
#   "user_input": "I have a headache",
#   "assistant_response": "For headaches, you might consider...",
#   "confidence": 0.85,
#   "turn_count": 1
# }

# 3. Send another turn (context-aware)
curl -X POST http://localhost:8000/voice/turn \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "sess_xyz123",
    "patient_id": "pat_001",
    "text": "Is ibuprofen safe for me?"
  }'

# Response should consider patient's conditions & prior turns

# 4. Close the session
curl -X POST http://localhost:8000/voice/sessions/sess_xyz123/end

# Response:
# {"session_id": "sess_xyz123", "status": "closed"}
```

### Integration Test

End-to-end: Create session → Send turn → Close session

```python
# tests/voice_gateway/test_e2e.py

async def test_full_conversation():
    # 1. Create profile
    profile = await profile_service.upsert_profile(
        agency_name="Test Agency",
        normalized_record={
            "name": "Test Patient",
            "dob": "1950-01-01",
            "problem_classes": ["Hypertension"]
        }
    )
    patient_id = profile["patient_id"]
    
    # 2. Start session
    session_id = await orchestrator.start_session(patient_id)
    assert session_id.startswith("sess_")
    
    # 3. Send turn
    response = await orchestrator.process_user_input(
        session_id=session_id,
        patient_id=patient_id,
        user_input="What medication should I take?"
    )
    assert "assistant_response" in response
    assert response["confidence"] > 0.0
    
    # 4. Verify session contains turn
    session = await turn_service.get_session(session_id)
    assert len(session.turns) >= 2  # user + assistant
    
    # 5. Close session
    success = await orchestrator.end_session(session_id)
    assert success
    
    # 6. Verify closed
    session = await turn_service.get_session(session_id)
    assert session.status == "closed"
```

---

## Latency Optimization

Typical latency per turn:

| Component | Time |
|-----------|------|
| Fetch profile | 10ms |
| Build context | 5ms |
| RAG pipeline | 500-1000ms |
| QA check | 50-100ms |
| Store turn | 20ms |
| **Total** | **585-1145ms** |

**Optimizations:**
1. **Cache patient context** in session (avoid refetch per turn)
2. **Async profile fetch** (start while RAG is running)
3. **QA sampling** (check 1 in 10 responses, rest logged only)
4. **CDN for ChromaDB** (vector search in ML service local)

---

## Error Handling

### Session Not Found

```json
{
  "detail": "Session not found: sess_invalid"
}
```

### Patient Not Found

```json
{
  "detail": "Patient not found: pat_invalid"
}
```

### Empty Input

```json
{
  "detail": "Text cannot be empty"
}
```

### Service Timeout

```json
{
  "detail": "RAG pipeline timeout (>10s)"
}
```

---

## Future Enhancements

1. **Multi-turn Context Window**
   - Include longer conversation history in RAG context
   - Detect repeated questions, topic shifts

2. **Speaker Identification**
   - Multi-user sessions (family member, caregiver)
   - Track who said what for audit

3. **Session Analytics**
   - Session duration, turn count, sentiment trend
   - Patient engagement metrics

4. **Auto-Summary**
   - End session with summary of discussion
   - Email summary to patient's email on file

5. **Escalation Workflow**
   - If confidence stays low > 3 turns, escalate to human operator
   - "Hold for support team" audio message
