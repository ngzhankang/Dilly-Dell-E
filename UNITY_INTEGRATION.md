# Unity Frontend Integration Guide

Complete API reference for integrating the Dilly-Dell-E backend with your Unity application.

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [API Endpoints](#api-endpoints)
3. [Integration Flow](#integration-flow)
4. [Request/Response Examples](#requestresponse-examples)
5. [Unity C# Code Examples](#unity-c-code-examples)
6. [Error Handling](#error-handling)
7. [Testing](#testing)
8. [Troubleshooting](#troubleshooting)

---

## Getting Started

### Backend Server Details

```
Base URL: http://localhost:3001
Protocol: HTTP/REST (JSON)
Content-Type: application/json
```

### System Requirements

- Backend running locally (or accessible via network)
- All Docker services up: `docker compose up -d` from project root
- Network connectivity between Unity app and backend
- Unity 2020.3 LTS or later (for UnityWebRequest)

### Health Check

Before integrating, verify the backend is healthy:

```bash
curl http://localhost:3001/health
```

Expected response:

```json
{
  "status": "ok",
  "mongodb": true,
  "ml_service": true
}
```

---

## API Endpoints

### 1. Create Patient Profile

**Endpoint:** `POST /api/profiles`

**Purpose:** Store a patient's unified profile in MongoDB

**Request Body:**

```json
{
  "agency_name": "string",
  "record": {
    "name": "string",
    "dob": "YYYY-MM-DD",
    "age": "number",
    "contact": "string (phone/email)",
    "emotion": "happy | neutral | worried | confused",
    "problem_classes": ["string", "string"],
    "special_case": "string or null"
  }
}
```

**Example Request:**

```json
{
  "agency_name": "Community Health Center",
  "record": {
    "name": "John Doe",
    "dob": "1950-06-15",
    "age": 75,
    "contact": "91234567",
    "emotion": "neutral",
    "problem_classes": ["Dementia", "Hypertension"],
    "special_case": null
  }
}
```

**Response (200 OK):**

```json
{
  "patient_id": "pat_000000",
  "created": true,
  "updated": false
}
```

**Status Codes:**
- `200 OK` - Profile created successfully
- `400 Bad Request` - Invalid request body
- `500 Internal Server Error` - Database error

---

### 2. Get Patient Profile

**Endpoint:** `GET /api/profiles/{patient_id}`

**Purpose:** Retrieve a patient's full profile including history

**Path Parameters:**
- `patient_id` (string) - The patient ID returned from profile creation

**Example URL:** `GET /api/profiles/pat_000000`

**Response (200 OK):**

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
  "agency_imports": {
    "Community Health Center": {
      "import_date": "2026-06-22T14:54:46.747000",
      "record": {
        "name": "John Doe",
        "dob": "1950-06-15",
        "age": 75,
        "contact": "91234567",
        "emotion": "neutral",
        "problem_classes": ["Dementia", "Hypertension"],
        "special_case": null
      }
    }
  },
  "last_updated": "2026-06-22T14:54:46.747000",
  "created_at": "2026-06-22T14:54:46.747000"
}
```

**Status Codes:**
- `200 OK` - Profile found
- `404 Not Found` - Patient doesn't exist
- `500 Internal Server Error` - Database error

---

### 3. Start Voice Session

**Endpoint:** `POST /api/voice/sessions/start`

**Purpose:** Create a new conversation session for a patient

**Request Body:**

```json
{
  "patient_id": "string"
}
```

**Example Request:**

```json
{
  "patient_id": "pat_000000"
}
```

**Response (200 OK):**

```json
{
  "session_id": "sess_83cf6c2f6fac",
  "patient_id": "pat_000000"
}
```

**Status Codes:**
- `200 OK` - Session created
- `400 Bad Request` - Missing patient_id
- `500 Internal Server Error` - Database error

**Important:** Store the `session_id` - you'll need it for all subsequent turn requests

---

### 4. Send Voice Turn (Main Loop)

**Endpoint:** `POST /api/voice/turn`

**Purpose:** Send a user message and get AI response with confidence scoring

**Request Body:**

```json
{
  "session_id": "string",
  "patient_id": "string",
  "text": "string (transcribed user input)"
}
```

**Example Request:**

```json
{
  "session_id": "sess_83cf6c2f6fac",
  "patient_id": "pat_000000",
  "text": "I have a sharp pain in my chest"
}
```

**Response (200 OK):**

```json
{
  "session_id": "sess_83cf6c2f6fac",
  "user_input": "I have a sharp pain in my chest",
  "assistant_response": "Chest pain can be concerning. This could be related to several conditions. Have you experienced this before? Please describe the severity on a scale of 1-10, and how long it has been occurring.",
  "confidence": 0.87,
  "retrieved_sources": [
    "Chest pain is a common complaint in elderly patients and can indicate cardiovascular issues.",
    "Assessment should include duration, severity, associated symptoms, and medical history."
  ],
  "turn_count": 1
}
```

**Response Fields:**
- `session_id` - Your session identifier
- `user_input` - Echo of what the user said
- `assistant_response` - AI-generated response from the model
- `confidence` - Confidence score (0.0-1.0) of the response quality
  - `>= 0.8` = High confidence (green light)
  - `0.6-0.79` = Medium confidence (yellow flag)
  - `< 0.6` = Low confidence (red flag - may need review)
- `retrieved_sources` - Knowledge base sources used to generate response
- `turn_count` - Which turn in the conversation (increments each call)

**Status Codes:**
- `200 OK` - Response generated successfully
- `400 Bad Request` - Missing required fields
- `404 Not Found` - Session or patient doesn't exist
- `500 Internal Server Error` - AI generation failed

**Important:**
- This is the main endpoint you'll call repeatedly during a conversation
- The AI response is context-aware (includes patient history and previous turns)
- Check the `confidence` score to determine if human review is needed

---

### 5. End Session

**Endpoint:** `POST /api/voice/sessions/{session_id}/end`

**Purpose:** Close a conversation session (cleanup)

**Path Parameters:**
- `session_id` (string) - The session ID from session start

**Example URL:** `POST /api/voice/sessions/sess_83cf6c2f6fac/end`

**Response (200 OK):**

```json
{
  "session_id": "sess_83cf6c2f6fac",
  "status": "closed",
  "total_turns": 5
}
```

**Status Codes:**
- `200 OK` - Session closed
- `404 Not Found` - Session doesn't exist
- `500 Internal Server Error` - Database error

---

### 6. QA Check Response (Optional - for validating responses)

**Endpoint:** `POST /api/qa/check-response`

**Purpose:** Validate response quality, confidence level, and hallucination detection

**Request Body:**

```json
{
  "response": "string (AI response to validate)",
  "confidence": "number (0.0-1.0)",
  "retrieved_sources": ["string", "string"]
}
```

**Example Request:**

```json
{
  "response": "For chest pain, you should seek immediate medical attention if it's severe.",
  "confidence": 0.75,
  "retrieved_sources": [
    "Chest pain may indicate serious conditions requiring immediate evaluation.",
    "Emergency services should be contacted for severe chest pain."
  ]
}
```

**Response (200 OK):**

```json
{
  "response": "For chest pain, you should seek immediate medical attention if it's severe.",
  "confidence": 0.75,
  "confidence_level": "medium",
  "hallucination_check": {
    "is_hallucination": false,
    "score": 0.0,
    "reason": "Response matches sources",
    "matched_sources": [
      "Chest pain may indicate serious conditions requiring immediate evaluation.",
      "Emergency services should be contacted for severe chest pain."
    ],
    "unmatched_claims": []
  },
  "needs_review": false,
  "reason_for_review": null
}
```

**Response Fields:**
- `confidence_level` - Human-readable confidence: "high" | "medium" | "low"
- `hallucination_check` - Detects if AI made up information not in sources
  - `is_hallucination` - true if response includes unverified claims
  - `score` - Hallucination severity (0.0-1.0)
  - `matched_sources` - Which sources support the response
  - `unmatched_claims` - What claims aren't backed by sources
- `needs_review` - Whether human should review (low confidence OR hallucinations detected)

**Status Codes:**
- `200 OK` - Check completed
- `400 Bad Request` - Invalid input
- `500 Internal Server Error` - Server error

---

### 7. Get Pending Reviews (Optional - for human-in-the-loop)

**Endpoint:** `GET /api/qa/reviews/pending`

**Purpose:** Retrieve responses flagged for human review (low confidence or hallucinations)

**Query Parameters:**
- `limit` (optional, default: 50) - Max number of reviews to return

**Example URL:** `GET /api/qa/reviews/pending?limit=10`

**Response (200 OK):**

```json
{
  "pending_count": 2,
  "items": [
    {
      "review_id": "rev_abc123",
      "session_id": "sess_xyz789",
      "patient_id": "pat_000000",
      "user_input": "What medication should I take?",
      "ai_response": "Take aspirin",
      "confidence": 0.45,
      "reason": "Low confidence response",
      "hallucination_detected": false,
      "timestamp": "2026-06-22T14:55:00",
      "status": "pending"
    }
  ]
}
```

**Status Codes:**
- `200 OK` - Reviews retrieved
- `500 Internal Server Error` - Database error

---

## Integration Flow

### Typical Conversation Flow

```
┌──────────────────────────────────────────────┐
│         UNITY APPLICATION                     │
└──────────────────────────────────────────────┘
                    │
                    ▼
          1. User selects patient
                    │
                    ▼
   POST /api/profiles (get or create)
                    │
                    ▼
 POST /api/voice/sessions/start
        [Store session_id locally]
                    │
   ┌───────────────┴───────────────┐
   │                               │
   ▼                               ▼
User speaks        Audio→Transcription
(or types)         (your responsibility)
   │                               │
   └───────────────┬───────────────┘
                   │
                   ▼
           POST /api/voice/turn
           ├─ session_id
           ├─ patient_id
           └─ text (transcribed)
                   │
                   ▼
        [Get AI Response + Confidence]
                   │
             ┌─────┴─────┐
             │            │
        Confidence      Confidence
        >= 0.8          < 0.8
        (High)          (Low/Medium)
        │               │
        ▼               ▼
   Display              Flag for
   to user              review
        │               │
        └─────┬─────────┘
              │
        Loop until done
              │
              ▼
POST /api/voice/sessions/{id}/end
```

### Step-by-Step Implementation

#### **Step 1: Initialize Patient (On App Start)**

```csharp
// 1. Create or fetch patient profile
POST /api/profiles
{
  "agency_name": "Unity Clinic",
  "record": {
    "name": "Patient Name",
    "dob": "1950-06-15",
    "age": 75,
    "contact": "Phone or Email",
    "emotion": "neutral",
    "problem_classes": ["Diabetes", "Hypertension"],
    "special_case": null
  }
}

// Response contains: patient_id
// Store patient_id for the session
```

#### **Step 2: Start Conversation**

```csharp
// 2. Create a new session
POST /api/voice/sessions/start
{
  "patient_id": "pat_000000"
}

// Response contains: session_id
// Store session_id - use for all turns
```

#### **Step 3: Main Conversation Loop**

```csharp
// 3. For each user input:
while (conversation_active) {
  // Get user input (voice→text transcription)
  string userText = TranscribeAudio();

  // Send to backend
  POST /api/voice/turn
  {
    "session_id": "sess_abc123",
    "patient_id": "pat_000000",
    "text": userText
  }

  // Get response
  {
    "assistant_response": "AI says...",
    "confidence": 0.85
  }

  // Display response to user
  DisplayText(response);

  // If confidence is low, flag for review
  if (confidence < 0.8f) {
    FlagForHumanReview(response);
  }
}
```

#### **Step 4: End Conversation**

```csharp
// 4. When done:
POST /api/voice/sessions/{session_id}/end
```

---

## Request/Response Examples

### Example 1: Complete Conversation

**Initial Setup:**

```bash
# Create patient
curl -X POST http://localhost:3001/api/profiles \
  -H "Content-Type: application/json" \
  -d '{
    "agency_name": "Clinic A",
    "record": {
      "name": "Alice Smith",
      "dob": "1955-03-20",
      "age": 68,
      "contact": "alice@email.com",
      "emotion": "worried",
      "problem_classes": ["Anxiety", "Diabetes"],
      "special_case": null
    }
  }'

# Response:
# {"patient_id": "pat_000001", "created": true, "updated": false}
```

**Start Session:**

```bash
curl -X POST http://localhost:3001/api/voice/sessions/start \
  -H "Content-Type: application/json" \
  -d '{"patient_id": "pat_000001"}'

# Response:
# {"session_id": "sess_xyz789", "patient_id": "pat_000001"}
```

**Turn 1:**

```bash
curl -X POST http://localhost:3001/api/voice/turn \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "sess_xyz789",
    "patient_id": "pat_000001",
    "text": "I am having trouble sleeping lately"
  }'
```

**Turn 2:**

```bash
curl -X POST http://localhost:3001/api/voice/turn \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "sess_xyz789",
    "patient_id": "pat_000001",
    "text": "It started about two weeks ago"
  }'
```

**End Session:**

```bash
curl -X POST http://localhost:3001/api/voice/sessions/sess_xyz789/end \
  -H "Content-Type: application/json"

# Response:
# {"session_id": "sess_xyz789", "status": "closed", "total_turns": 2}
```

---

## Unity C# Code Examples

### Setup: Required Packages

Your script needs these using statements:

```csharp
using UnityEngine;
using UnityEngine.Networking;
using System.Collections;
using System.Collections.Generic;
```

No additional packages needed - `UnityWebRequest` is built-in!

### Basic Helper Class

```csharp
// BackendManager.cs
using UnityEngine;
using UnityEngine.Networking;
using System.Collections;
using System;

[System.Serializable]
public class PatientRecord {
    public string name;
    public string dob;
    public int age;
    public string contact;
    public string emotion = "neutral";
    public string[] problem_classes;
    public string special_case;
}

[System.Serializable]
public class ProfileRequest {
    public string agency_name;
    public PatientRecord record;
}

[System.Serializable]
public class SessionStartRequest {
    public string patient_id;
}

[System.Serializable]
public class VoiceTurnRequest {
    public string session_id;
    public string patient_id;
    public string text;
}

[System.Serializable]
public class ProfileResponse {
    public string patient_id;
    public bool created;
    public bool updated;
}

[System.Serializable]
public class SessionResponse {
    public string session_id;
    public string patient_id;
}

[System.Serializable]
public class VoiceTurnResponse {
    public string session_id;
    public string user_input;
    public string assistant_response;
    public float confidence;
    public string[] retrieved_sources;
    public int turn_count;
}

public class BackendManager : MonoBehaviour {
    private string baseURL = "http://localhost:3001";
    private string currentPatientId;
    private string currentSessionId;

    // Events
    public event System.Action OnPatientCreated;
    public event System.Action OnSessionStarted;
    public event System.Action<VoiceTurnResponse> OnVoiceResponseReceived;
    public event System.Action OnSessionEnded;
    public event System.Action<string> OnError;

    /// <summary>
    /// Create or fetch a patient profile
    /// </summary>
    public void CreatePatient(string name, string dob, int age, string contact, string[] problems) {
        var record = new PatientRecord {
            name = name,
            dob = dob,
            age = age,
            contact = contact,
            emotion = "neutral",
            problem_classes = problems,
            special_case = null
        };

        var request = new ProfileRequest {
            agency_name = "Unity Clinic",
            record = record
        };

        StartCoroutine(PostRequest<ProfileRequest, ProfileResponse>(
            "/api/profiles",
            request,
            response => {
                currentPatientId = response.patient_id;
                OnPatientCreated?.Invoke();
            }
        ));
    }

    /// <summary>
    /// Start a new conversation session
    /// </summary>
    public void StartSession(string patientId) {
        var request = new SessionStartRequest {
            patient_id = patientId
        };

        StartCoroutine(PostRequest<SessionStartRequest, SessionResponse>(
            "/api/voice/sessions/start",
            request,
            response => {
                currentSessionId = response.session_id;
                OnSessionStarted?.Invoke();
            }
        ));
    }

    /// <summary>
    /// Send a voice turn (main conversation loop)
    /// </summary>
    public void SendVoiceTurn(string sessionId, string patientId, string userText) {
        var request = new VoiceTurnRequest {
            session_id = sessionId,
            patient_id = patientId,
            text = userText
        };

        StartCoroutine(PostRequest<VoiceTurnRequest, VoiceTurnResponse>(
            "/api/voice/turn",
            request,
            response => {
                OnVoiceResponseReceived?.Invoke(response);
            }
        ));
    }

    /// <summary>
    /// End a conversation session
    /// </summary>
    public void EndSession(string sessionId) {
        StartCoroutine(PostRequestNoBody(
            $"/api/voice/sessions/{sessionId}/end",
            () => OnSessionEnded?.Invoke()
        ));
    }

    // Generic POST request helper
    private IEnumerator PostRequest<TRequest, TResponse>(
        string endpoint,
        TRequest requestData,
        System.Action<TResponse> onSuccess) where TResponse : new() {

        string url = baseURL + endpoint;
        string jsonBody = JsonUtility.ToJson(requestData);

        using (UnityWebRequest www = new UnityWebRequest(url, "POST")) {
            byte[] bodyRaw = System.Text.Encoding.UTF8.GetBytes(jsonBody);
            www.uploadHandler = new UploadHandlerRaw(bodyRaw);
            www.downloadHandler = new DownloadHandlerBuffer();
            www.SetRequestHeader("Content-Type", "application/json");

            yield return www.SendWebRequest();

            if (www.result == UnityWebRequest.Result.Success) {
                try {
                    TResponse response = JsonUtility.FromJson<TResponse>(www.downloadHandler.text);
                    onSuccess?.Invoke(response);
                } catch (Exception e) {
                    OnError?.Invoke($"JSON Parse Error: {e.Message}");
                }
            } else {
                OnError?.Invoke($"HTTP {www.responseCode}: {www.error}");
            }
        }
    }

    // Helper for POST without body
    private IEnumerator PostRequestNoBody(string endpoint, System.Action onSuccess) {
        string url = baseURL + endpoint;

        using (UnityWebRequest www = UnityWebRequest.Post(url, "")) {
            www.SetRequestHeader("Content-Type", "application/json");
            yield return www.SendWebRequest();

            if (www.result == UnityWebRequest.Result.Success) {
                onSuccess?.Invoke();
            } else {
                OnError?.Invoke($"HTTP {www.responseCode}: {www.error}");
            }
        }
    }

    // Properties for easy access
    public string CurrentPatientId => currentPatientId;
    public string CurrentSessionId => currentSessionId;
}
```

### Usage in Your Game

```csharp
// In your game script
public class PatientInteractionManager : MonoBehaviour {
    private BackendManager backend;

    void Start() {
        // Get or create the backend manager
        backend = GetComponent<BackendManager>();
        if (backend == null) {
            backend = gameObject.AddComponent<BackendManager>();
        }

        // Subscribe to events
        backend.OnPatientCreated += HandlePatientCreated;
        backend.OnSessionStarted += HandleSessionStarted;
        backend.OnVoiceResponseReceived += HandleVoiceResponse;
        backend.OnError += HandleError;

        // Create patient
        string[] problems = { "Hypertension", "Diabetes" };
        backend.CreatePatient(
            "John Doe",
            "1950-06-15",
            75,
            "91234567",
            problems
        );
    }

    private void HandlePatientCreated() {
        Debug.Log($"Patient created: {backend.CurrentPatientId}");
        // Start session with the new patient
        backend.StartSession(backend.CurrentPatientId);
    }

    private void HandleSessionStarted() {
        Debug.Log($"Session started: {backend.CurrentSessionId}");
        // Now ready for voice input
        EnableVoiceInput();
    }

    private void HandleVoiceResponse(VoiceTurnResponse response) {
        Debug.Log($"AI Response: {response.assistant_response}");
        Debug.Log($"Confidence: {response.confidence}");

        // Display response
        DisplayText(response.assistant_response);

        // Check if needs review
        if (response.confidence < 0.8f) {
            ShowWarning("Low confidence - this response may need human review");
        }

        // Wait for next input
        WaitForNextInput();
    }

    private void HandleError(string error) {
        Debug.LogError($"Backend Error: {error}");
        ShowErrorUI(error);
    }

    public void SendUserInput(string transcribedText) {
        backend.SendVoiceTurn(
            backend.CurrentSessionId,
            backend.CurrentPatientId,
            transcribedText
        );
    }

    public void EndConversation() {
        backend.EndSession(backend.CurrentSessionId);
    }

    // UI Helper methods (implement as needed)
    private void EnableVoiceInput() { /* ... */ }
    private void WaitForNextInput() { /* ... */ }
    private void DisplayText(string text) { /* ... */ }
    private void ShowWarning(string warning) { /* ... */ }
    private void ShowErrorUI(string error) { /* ... */ }
}
```

### Coroutine Example with Timeout

```csharp
// If you need timeout handling
private IEnumerator PostRequestWithTimeout<TRequest, TResponse>(
    string endpoint,
    TRequest requestData,
    System.Action<TResponse> onSuccess,
    float timeoutSeconds = 30f) where TResponse : new() {

    string url = baseURL + endpoint;
    string jsonBody = JsonUtility.ToJson(requestData);

    using (UnityWebRequest www = new UnityWebRequest(url, "POST")) {
        byte[] bodyRaw = System.Text.Encoding.UTF8.GetBytes(jsonBody);
        www.uploadHandler = new UploadHandlerRaw(bodyRaw);
        www.downloadHandler = new DownloadHandlerBuffer();
        www.SetRequestHeader("Content-Type", "application/json");
        www.timeout = (int)timeoutSeconds;

        yield return www.SendWebRequest();

        if (www.result == UnityWebRequest.Result.Success) {
            try {
                TResponse response = JsonUtility.FromJson<TResponse>(www.downloadHandler.text);
                onSuccess?.Invoke(response);
            } catch (Exception e) {
                OnError?.Invoke($"Parse Error: {e.Message}");
            }
        } else if (www.result == UnityWebRequest.Result.Timeout) {
            OnError?.Invoke("Request timed out");
        } else {
            OnError?.Invoke($"HTTP {www.responseCode}: {www.error}");
        }
    }
}
```

---

## Error Handling

### Common HTTP Errors

| Status | Meaning | Action |
|--------|---------|--------|
| 200 | Success | Process response normally |
| 400 | Bad Request | Check request body format |
| 404 | Not Found | Patient/Session doesn't exist |
| 500 | Server Error | Backend crashed - restart `docker compose` |

### Error Response Format

```json
{
  "detail": "Error message describing what went wrong"
}
```

### Handling Errors in Unity

```csharp
backend.OnError += (error) => {
    Debug.LogError($"API Error: {error}");

    if (error.Contains("404")) {
        ShowUserMessage("Patient or session not found");
    } else if (error.Contains("500")) {
        ShowUserMessage("Backend error - please try again");
    } else if (error.Contains("Timeout")) {
        ShowUserMessage("Network timeout - check connection");
    } else {
        ShowUserMessage($"Error: {error}");
    }
};
```

---

## Testing

### Manual Testing with curl

Test all endpoints:

```bash
# 1. Create patient
curl -X POST http://localhost:3001/api/profiles \
  -H "Content-Type: application/json" \
  -d '{
    "agency_name": "Test",
    "record": {
      "name": "Test Patient",
      "dob": "1950-01-01",
      "age": 75,
      "contact": "123",
      "emotion": "neutral",
      "problem_classes": ["Test"]
    }
  }'

# 2. Start session
curl -X POST http://localhost:3001/api/voice/sessions/start \
  -H "Content-Type: application/json" \
  -d '{"patient_id": "PAT_ID"}'

# 3. Send turn
curl -X POST http://localhost:3001/api/voice/turn \
  -H "Content-Type: application/json" \
  -d '{"session_id": "SESSION_ID", "patient_id": "PAT_ID", "text": "Hello"}'

# 4. Check health
curl http://localhost:3001/health
```

### Unity Testing

Create a test scene:

```csharp
public class BackendTester : MonoBehaviour {
    public BackendManager backend;

    public void TestCreatePatient() {
        Debug.Log("Test 1: Creating patient...");
        backend.CreatePatient(
            "Test Patient",
            "1950-01-01",
            75,
            "123",
            new[] { "Test" }
        );
    }

    public void TestStartSession() {
        Debug.Log("Test 2: Starting session...");
        backend.StartSession(backend.CurrentPatientId);
    }

    public void TestSendTurn() {
        Debug.Log("Test 3: Sending voice turn...");
        backend.SendVoiceTurn(
            backend.CurrentSessionId,
            backend.CurrentPatientId,
            "test input"
        );
    }

    public void TestEndSession() {
        Debug.Log("Test 4: Ending session...");
        backend.EndSession(backend.CurrentSessionId);
    }
}
```

---

## Troubleshooting

### "Connection Refused"

**Problem:** `http://localhost:3001` returns connection refused

**Solution:**

```bash
# Check if backend is running
curl http://localhost:3001/health

# If not, start Docker services
cd /path/to/project
docker compose up -d

# Verify services are running
docker compose ps
```

### "Patient Not Found"

**Problem:** Profile request returns 404

**Solution:**
- Make sure you used the patient ID from the create response
- Check MongoDB is running: `docker compose logs mongo`

### "Session Not Found"

**Problem:** Voice turn returns 404

**Solution:**
- Make sure you're using the session ID from start-session response
- Don't use a closed session (call start-session again)

### "Low Confidence Response"

**Problem:** Assistant response has confidence < 0.6

**Possible causes:**
- LLM is uncertain about the answer
- User input was unclear
- Topic is outside knowledge base

**Solution:**
- Show user "This answer needs human review"
- Flag for human review via `/api/qa/reviews/pending`

### "Request Times Out"

**Problem:** UnityWebRequest takes 10+ seconds

**Causes:**
- LLM is slow (normal for first run)
- Network latency
- Backend is overloaded

**Solution:**
- Increase timeout: `www.timeout = 60;` (60 seconds)
- Show loading spinner to user
- Consider caching common responses

### Network Issues

If on different machines (not localhost):

```csharp
// Update base URL in BackendManager
private string baseURL = "http://192.168.1.100:3001"; // Your backend machine IP
```

### JSON Serialization Issues

If `JsonUtility.FromJson` fails:

```csharp
// Debug the JSON response
Debug.Log($"Raw Response: {www.downloadHandler.text}");

// Or use a JSON library for more flexibility
// Install Newtonsoft.Json via Package Manager if needed
```

---

## Summary

### Quick Reference

| Task | Endpoint | Method | Key Response |
|------|----------|--------|--------------|
| Create Patient | `/api/profiles` | POST | `patient_id` |
| Start Conversation | `/api/voice/sessions/start` | POST | `session_id` |
| Send User Input | `/api/voice/turn` | POST | `assistant_response`, `confidence` |
| End Conversation | `/api/voice/sessions/{id}/end` | POST | status |

### Essential Fields to Track

```csharp
string patientId;      // From create patient
string sessionId;      // From start session
float confidence;      // From each voice turn
string response;       // From each voice turn
```

### Always Check

1. ✅ Backend health: `GET /health`
2. ✅ Request format: Valid JSON
3. ✅ Response status: 200 OK
4. ✅ Confidence scores: Flag if < 0.8

---

## Support

If you encounter issues:

1. Check `/BACKEND_INTEGRATION.md` for backend troubleshooting
2. Review the Unity C# examples above
3. Test endpoints with curl first
4. Check Docker logs: `docker compose logs ml-service`
5. Check backend logs: `npm run dev` output

Good luck with your Unity integration! 🚀
