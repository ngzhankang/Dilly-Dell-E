# Unreal Engine Frontend Integration Guide

Complete API reference for integrating the Dilly-Dell-E backend with your Unreal Engine application.

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [API Endpoints](#api-endpoints)
3. [Integration Flow](#integration-flow)
4. [Request/Response Examples](#requestresponse-examples)
5. [Unreal C++ Code Examples](#unreal-c-code-examples)
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
- Network connectivity between Unreal app and backend

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
    },
    {
      "review_id": "rev_def456",
      "session_id": "sess_xyz789",
      "patient_id": "pat_000000",
      "user_input": "What's my blood type?",
      "ai_response": "Your blood type is O+",
      "confidence": 0.72,
      "reason": "Hallucination detected",
      "hallucination_detected": true,
      "timestamp": "2026-06-22T14:56:00",
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
┌─────────────────────────────────────────────────────────────┐
│                      UNREAL APPLICATION                      │
└─────────────────────────────────────────────────────────────┘
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
         ┌────────────────────┴────────────────────┐
         │                                          │
         ▼                                          ▼
    User speaks          Audio→Transcription
    (or types)           (your responsibility)
         │                                          │
         └────────────────────┬────────────────────┘
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

```cpp
// 1. Create or fetch patient profile
POST /api/profiles
{
  "agency_name": "Unreal Clinic",
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

```cpp
// 2. Create a new session
POST /api/voice/sessions/start
{
  "patient_id": "pat_000000"
}

// Response contains: session_id
// Store session_id - use for all turns
```

#### **Step 3: Main Conversation Loop**

```cpp
// 3. For each user input:
while (conversation_active) {
  // Get user input (voice→text transcription)
  string user_text = TranscribeAudio();
  
  // Send to backend
  POST /api/voice/turn
  {
    "session_id": "sess_abc123",
    "patient_id": "pat_000000",
    "text": user_text
  }
  
  // Get response
  {
    "assistant_response": "AI says...",
    "confidence": 0.85
  }
  
  // Display response to user
  DisplayText(response);
  
  // If confidence is low, flag for review
  if (confidence < 0.8) {
    FlagForHumanReview(response);
  }
}
```

#### **Step 4: End Conversation**

```cpp
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

# Response:
{
  "session_id": "sess_xyz789",
  "user_input": "I am having trouble sleeping lately",
  "assistant_response": "Sleep issues are common, especially with anxiety. Can you tell me when this started? Also, are you experiencing any other symptoms?",
  "confidence": 0.89,
  "retrieved_sources": [
    "Insomnia may be related to anxiety disorders",
    "Sleep assessment should include onset, duration, and associated symptoms"
  ],
  "turn_count": 1
}
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

# Response:
{
  "session_id": "sess_xyz789",
  "user_input": "It started about two weeks ago",
  "assistant_response": "Two weeks is relatively recent. Has anything stressful happened recently? Sleep deprivation can affect your anxiety, and anxiety can worsen sleep. Have you tried any relaxation techniques?",
  "confidence": 0.85,
  "retrieved_sources": [
    "Sleep and anxiety have bidirectional relationships",
    "Relaxation and cognitive behavioral approaches help with insomnia"
  ],
  "turn_count": 2
}
```

**End Session:**
```bash
curl -X POST http://localhost:3001/api/voice/sessions/sess_xyz789/end \
  -H "Content-Type: application/json"

# Response:
# {"session_id": "sess_xyz789", "status": "closed", "total_turns": 2}
```

---

## Unreal C++ Code Examples

### Setup: HTTP Module

Add to your `.Build.cs` file:
```csharp
PublicDependencyModuleNames.AddRange(new string[] { 
  "Core", 
  "CoreUObject", 
  "Engine", 
  "HTTP", 
  "Json", 
  "JsonUtilities"
});
```

### Basic Helper Class

```cpp
// BackendManager.h
#pragma once

#include "CoreMinimal.h"
#include "Http.h"
#include "Json.h"
#include "Containers/List.h"

struct FPatientProfile {
    FString PatientId;
    FString Name;
    int32 Age;
    FString DOB;
    FString Contact;
};

struct FVoiceResponse {
    FString AssistantResponse;
    float Confidence;
    FString SessionId;
    int32 TurnCount;
    TArray<FString> RetrievedSources;
};

UCLASS()
class YOURPROJECT_API ABackendManager : public AActor {
    GENERATED_BODY()

public:
    ABackendManager();
    virtual void BeginPlay() override;

    // Create patient
    void CreatePatient(
        const FString& Name,
        const FString& DOB,
        int32 Age,
        const FString& Contact,
        const TArray<FString>& ProblemClasses
    );

    // Start conversation
    void StartSession(const FString& PatientId);

    // Send voice turn
    void SendVoiceTurn(
        const FString& SessionId,
        const FString& PatientId,
        const FString& UserText
    );

    // End session
    void EndSession(const FString& SessionId);

    // Callbacks
    FSimpleDelegate OnPatientCreated;
    FSimpleDelegate OnSessionStarted;
    FSimpleDelegate OnVoiceResponseReceived;
    FSimpleDelegate OnSessionEnded;

private:
    FString BaseURL = "http://localhost:3001";
    FString CurrentPatientId;
    FString CurrentSessionId;

    // HTTP callbacks
    void OnCreatePatientResponse(FHttpRequestPtr Request, FHttpResponsePtr Response, bool bWasSuccessful);
    void OnStartSessionResponse(FHttpRequestPtr Request, FHttpResponsePtr Response, bool bWasSuccessful);
    void OnVoiceTurnResponse(FHttpRequestPtr Request, FHttpResponsePtr Response, bool bWasSuccessful);
    void OnEndSessionResponse(FHttpRequestPtr Request, FHttpResponsePtr Response, bool bWasSuccessful);

    // Helper functions
    FString MakeJsonString(const TSharedPtr<FJsonObject>& JsonObject);
    TSharedPtr<FJsonObject> ParseJsonResponse(const FString& JsonString);
};
```

### Implementation

```cpp
// BackendManager.cpp
#include "BackendManager.h"
#include "Http.h"
#include "JsonUtilities.h"
#include "Containers/StringConv.h"

ABackendManager::ABackendManager() {
    PrimaryActorTick.bCanEverTick = false;
}

void ABackendManager::BeginPlay() {
    Super::BeginPlay();
    UE_LOG(LogTemp, Warning, TEXT("Backend Manager initialized"));
}

void ABackendManager::CreatePatient(
    const FString& Name,
    const FString& DOB,
    int32 Age,
    const FString& Contact,
    const TArray<FString>& ProblemClasses) {

    FHttpModule& HttpModule = FHttpModule::Get();
    TSharedRef<IHttpRequest, ESPMode::ThreadSafe> Request = HttpModule.CreateRequest();

    // Build JSON
    TSharedPtr<FJsonObject> JsonObject = MakeShareable(new FJsonObject());
    JsonObject->SetStringField("agency_name", "Unreal Clinic");

    TSharedPtr<FJsonObject> RecordObject = MakeShareable(new FJsonObject());
    RecordObject->SetStringField("name", Name);
    RecordObject->SetStringField("dob", DOB);
    RecordObject->SetNumberField("age", Age);
    RecordObject->SetStringField("contact", Contact);
    RecordObject->SetStringField("emotion", "neutral");

    // Problem classes array
    TArray<TSharedPtr<FJsonValue>> ProblemArray;
    for (const FString& Problem : ProblemClasses) {
        ProblemArray.Add(MakeShareable(new FJsonValueString(Problem)));
    }
    RecordObject->SetArrayField("problem_classes", ProblemArray);
    RecordObject->SetNullField("special_case");

    JsonObject->SetObjectField("record", RecordObject);

    // Set up request
    Request->SetURL(BaseURL + "/api/profiles");
    Request->SetVerb(TEXT("POST"));
    Request->SetHeader(TEXT("Content-Type"), TEXT("application/json"));
    Request->SetContentAsString(MakeJsonString(JsonObject));

    // Bind callback
    Request->OnProcessRequestComplete().BindUObject(this, &ABackendManager::OnCreatePatientResponse);

    // Send
    Request->ProcessRequest();
}

void ABackendManager::StartSession(const FString& PatientId) {
    FHttpModule& HttpModule = FHttpModule::Get();
    TSharedRef<IHttpRequest, ESPMode::ThreadSafe> Request = HttpModule.CreateRequest();

    TSharedPtr<FJsonObject> JsonObject = MakeShareable(new FJsonObject());
    JsonObject->SetStringField("patient_id", PatientId);

    Request->SetURL(BaseURL + "/api/voice/sessions/start");
    Request->SetVerb(TEXT("POST"));
    Request->SetHeader(TEXT("Content-Type"), TEXT("application/json"));
    Request->SetContentAsString(MakeJsonString(JsonObject));

    Request->OnProcessRequestComplete().BindUObject(this, &ABackendManager::OnStartSessionResponse);
    Request->ProcessRequest();
}

void ABackendManager::SendVoiceTurn(
    const FString& SessionId,
    const FString& PatientId,
    const FString& UserText) {

    FHttpModule& HttpModule = FHttpModule::Get();
    TSharedRef<IHttpRequest, ESPMode::ThreadSafe> Request = HttpModule.CreateRequest();

    TSharedPtr<FJsonObject> JsonObject = MakeShareable(new FJsonObject());
    JsonObject->SetStringField("session_id", SessionId);
    JsonObject->SetStringField("patient_id", PatientId);
    JsonObject->SetStringField("text", UserText);

    Request->SetURL(BaseURL + "/api/voice/turn");
    Request->SetVerb(TEXT("POST"));
    Request->SetHeader(TEXT("Content-Type"), TEXT("application/json"));
    Request->SetContentAsString(MakeJsonString(JsonObject));

    Request->OnProcessRequestComplete().BindUObject(this, &ABackendManager::OnVoiceTurnResponse);
    Request->ProcessRequest();
}

void ABackendManager::EndSession(const FString& SessionId) {
    FHttpModule& HttpModule = FHttpModule::Get();
    TSharedRef<IHttpRequest, ESPMode::ThreadSafe> Request = HttpModule.CreateRequest();

    FString URL = BaseURL + "/api/voice/sessions/" + SessionId + "/end";
    Request->SetURL(URL);
    Request->SetVerb(TEXT("POST"));
    Request->SetHeader(TEXT("Content-Type"), TEXT("application/json"));

    Request->OnProcessRequestComplete().BindUObject(this, &ABackendManager::OnEndSessionResponse);
    Request->ProcessRequest();
}

// Response Handlers
void ABackendManager::OnCreatePatientResponse(FHttpRequestPtr Request, FHttpResponsePtr Response, bool bWasSuccessful) {
    if (!bWasSuccessful || !Response.IsValid()) {
        UE_LOG(LogTemp, Error, TEXT("Create Patient request failed"));
        return;
    }

    FString JsonString = Response->GetContentAsString();
    TSharedPtr<FJsonObject> JsonObject = ParseJsonResponse(JsonString);

    if (JsonObject.IsValid()) {
        CurrentPatientId = JsonObject->GetStringField("patient_id");
        UE_LOG(LogTemp, Warning, TEXT("Patient created: %s"), *CurrentPatientId);
        OnPatientCreated.Broadcast();
    }
}

void ABackendManager::OnStartSessionResponse(FHttpRequestPtr Request, FHttpResponsePtr Response, bool bWasSuccessful) {
    if (!bWasSuccessful || !Response.IsValid()) {
        UE_LOG(LogTemp, Error, TEXT("Start Session request failed"));
        return;
    }

    FString JsonString = Response->GetContentAsString();
    TSharedPtr<FJsonObject> JsonObject = ParseJsonResponse(JsonString);

    if (JsonObject.IsValid()) {
        CurrentSessionId = JsonObject->GetStringField("session_id");
        UE_LOG(LogTemp, Warning, TEXT("Session started: %s"), *CurrentSessionId);
        OnSessionStarted.Broadcast();
    }
}

void ABackendManager::OnVoiceTurnResponse(FHttpRequestPtr Request, FHttpResponsePtr Response, bool bWasSuccessful) {
    if (!bWasSuccessful || !Response.IsValid()) {
        UE_LOG(LogTemp, Error, TEXT("Voice Turn request failed"));
        return;
    }

    FString JsonString = Response->GetContentAsString();
    TSharedPtr<FJsonObject> JsonObject = ParseJsonResponse(JsonString);

    if (JsonObject.IsValid()) {
        FVoiceResponse VoiceResp;
        VoiceResp.AssistantResponse = JsonObject->GetStringField("assistant_response");
        VoiceResp.Confidence = JsonObject->GetNumberField("confidence");
        VoiceResp.SessionId = JsonObject->GetStringField("session_id");
        VoiceResp.TurnCount = JsonObject->GetIntegerField("turn_count");

        UE_LOG(LogTemp, Warning, TEXT("AI Response: %s (Confidence: %.2f)"),
            *VoiceResp.AssistantResponse, VoiceResp.Confidence);

        // Check confidence
        if (VoiceResp.Confidence < 0.8f) {
            UE_LOG(LogTemp, Warning, TEXT("LOW CONFIDENCE - Consider human review"));
        }

        OnVoiceResponseReceived.Broadcast();
    }
}

void ABackendManager::OnEndSessionResponse(FHttpRequestPtr Request, FHttpResponsePtr Response, bool bWasSuccessful) {
    if (!bWasSuccessful || !Response.IsValid()) {
        UE_LOG(LogTemp, Error, TEXT("End Session request failed"));
        return;
    }

    UE_LOG(LogTemp, Warning, TEXT("Session ended successfully"));
    OnSessionEnded.Broadcast();
}

// Helper functions
FString ABackendManager::MakeJsonString(const TSharedPtr<FJsonObject>& JsonObject) {
    FString OutString;
    TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&OutString);
    FJsonSerializer::Serialize(JsonObject.ToSharedRef(), Writer);
    return OutString;
}

TSharedPtr<FJsonObject> ABackendManager::ParseJsonResponse(const FString& JsonString) {
    TSharedPtr<FJsonObject> JsonObject = MakeShareable(new FJsonObject());
    TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(JsonString);
    FJsonSerializer::Deserialize(Reader, JsonObject);
    return JsonObject;
}
```

### Using in Your Unreal Game

```cpp
// In your game character or player controller
void AMyCharacter::BeginPlay() {
    Super::BeginPlay();

    // Spawn backend manager
    ABackendManager* Backend = GetWorld()->SpawnActor<ABackendManager>();

    // Bind callbacks
    Backend->OnPatientCreated.AddDynamic(this, &AMyCharacter::OnPatientReady);
    Backend->OnSessionStarted.AddDynamic(this, &AMyCharacter::OnSessionReady);
    Backend->OnVoiceResponseReceived.AddDynamic(this, &AMyCharacter::OnResponseReceived);

    // Create patient
    TArray<FString> Problems = {"Hypertension", "Diabetes"};
    Backend->CreatePatient(
        "John Doe",
        "1950-06-15",
        75,
        "91234567",
        Problems
    );
}

void AMyCharacter::OnPatientReady() {
    UE_LOG(LogTemp, Warning, TEXT("Patient ready, starting session"));
    // Start session with patient ID
}

void AMyCharacter::OnSessionReady() {
    UE_LOG(LogTemp, Warning, TEXT("Session ready, waiting for user input"));
    // Enable voice input
}

void AMyCharacter::OnResponseReceived() {
    UE_LOG(LogTemp, Warning, TEXT("Got AI response"));
    // Display response to user
    // If confidence < 0.8, show flag for review
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

### Handling Errors in Unreal

```cpp
void ABackendManager::OnVoiceTurnResponse(FHttpRequestPtr Request, FHttpResponsePtr Response, bool bWasSuccessful) {
    if (!bWasSuccessful) {
        UE_LOG(LogTemp, Error, TEXT("HTTP Request failed"));
        return;
    }

    if (Response->GetResponseCode() != 200) {
        FString ErrorMsg = Response->GetContentAsString();
        UE_LOG(LogTemp, Error, TEXT("API Error: %s"), *ErrorMsg);
        return;
    }

    // Process successful response
}
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
    "record": {"name": "Test Patient", "dob": "1950-01-01", "age": 75, "contact": "123", "emotion": "neutral", "problem_classes": ["Test"]}
  }'

# 2. Start session (replace PAT_ID with response above)
curl -X POST http://localhost:3001/api/voice/sessions/start \
  -H "Content-Type: application/json" \
  -d '{"patient_id": "PAT_ID"}'

# 3. Send turn (replace SESSION_ID and PAT_ID)
curl -X POST http://localhost:3001/api/voice/turn \
  -H "Content-Type: application/json" \
  -d '{"session_id": "SESSION_ID", "patient_id": "PAT_ID", "text": "Hello"}'

# 4. Check health
curl http://localhost:3001/health
```

### Unit Testing in Unreal

```cpp
void TestBackendIntegration() {
    // Create backend manager
    ABackendManager* Backend = GetWorld()->SpawnActor<ABackendManager>();
    
    // Test 1: Create patient
    TArray<FString> Problems = {"Test"};
    Backend->CreatePatient("Test", "1950-01-01", 75, "123", Problems);
    
    // Wait for callback
    // Assert patient ID is set
    
    // Test 2: Start session
    Backend->StartSession(Backend->CurrentPatientId);
    // Assert session ID is set
    
    // Test 3: Send voice turn
    Backend->SendVoiceTurn(Backend->CurrentSessionId, Backend->CurrentPatientId, "test input");
    // Assert response received
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

**Problem:** `/api/profiles/pat_xxx` returns 404

**Solution:**
- Make sure you used the patient ID from the create response
- Check MongoDB is running: `docker compose logs mongo`

### "Session Not Found"

**Problem:** `/api/voice/turn` returns 404

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

### "Response Takes Too Long"

**Problem:** Turn requests take 10+ seconds

**Causes:**
- LLM is slow (normal for first run)
- Network latency
- Backend is overloaded

**Solution:**
- Add timeout handling (suggest 30 seconds)
- Show loading spinner to user
- Consider caching common responses

### Network Issues

If on different machines (not localhost):

```cpp
// Update base URL in BackendManager
FString BaseURL = "http://192.168.1.100:3001"; // Your backend machine IP
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

```cpp
FString PatientId;      // From create patient
FString SessionId;      // From start session
float Confidence;       // From each voice turn
FString Response;       // From each voice turn
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
2. Review the Unreal C++ examples above
3. Test endpoints with curl first
4. Check Docker logs: `docker compose logs ml-service`
5. Check backend logs: `npm run dev` output

Good luck with your integration! 🚀
