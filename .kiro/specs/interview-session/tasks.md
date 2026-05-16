# Implementation Plan: Interview Session

## Overview

This plan implements the `interview-svc` microservice for multi-party video conferencing in proctoAi. The implementation follows a bottom-up approach: data models and configuration first, then core services (LiveKit adapter, session service, presentation service), API routes, webhook handling, and finally frontend integration. Python (FastAPI) is used for the backend service, with React/TypeScript for frontend components.

## Tasks

- [x] 1. Set up interview-svc project structure and configuration
  - [x] 1.1 Create the interview-svc directory structure and FastAPI application scaffold
    - Create `services/interview-svc/` with `app/`, `app/core/`, `app/models/`, `app/schemas/`, `app/services/`, `app/api/`, `app/api/v1/`, `tests/` directories
    - Create `pyproject.toml` with dependencies: fastapi, uvicorn, sqlalchemy, livekit-server-sdk, python-multipart, pdf2image, python-pptx, httpx, pydantic
    - Create `app/main.py` with FastAPI app instance and router includes
    - Create `app/core/config.py` with settings for LiveKit URL, API key/secret, database URL, S3/MinIO credentials, max upload size
    - _Requirements: 1.1, 1.2_

  - [x] 1.2 Create SQLAlchemy data models for InterviewSession, SessionParticipant, and Presentation
    - Create `app/models/interview_session.py` with InterviewSession model (id, title, room_name, creator_id, status, max_participants, scheduled_at, started_at, ended_at, created_at, recording_url)
    - Create `app/models/participant.py` with SessionParticipant model (id, session_id, user_id, role, display_name, joined_at, left_at, status)
    - Create `app/models/presentation.py` with Presentation model (id, session_id, filename, file_url, slide_count, current_slide, slides_json, uploaded_by, uploaded_at, is_active)
    - Create `app/models/__init__.py` exporting all models
    - Enforce unique constraint on (user_id, session_id) in SessionParticipant
    - Enforce unique constraint on room_name in InterviewSession
    - _Requirements: 1.1, 2.4, 5.4, 6.6, 7.3_

  - [x] 1.3 Create Pydantic schemas for request/response validation
    - Create `app/schemas/session.py` with CreateSessionRequest (title: str 1-500 chars, max_participants: int 2-10, scheduled_at: optional datetime), SessionResponse, JoinSessionRequest, JoinSessionResponse
    - Create `app/schemas/participant.py` with ParticipantResponse, ParticipantRole enum (interviewer, interviewee, observer)
    - Create `app/schemas/presentation.py` with PresentationResponse, SlideChangeRequest (slide_index: int), UploadResponse
    - _Requirements: 1.3, 1.4, 3.7, 6.2, 6.3, 7.2_

  - [x] 1.4 Set up database connection and Alembic migration for interview-svc
    - Create `app/core/database.py` with async SQLAlchemy engine and session factory
    - Create initial Alembic migration for interview_sessions, session_participants, and presentations tables
    - _Requirements: 1.1_

- [x] 2. Implement LiveKitAdapter service
  - [x] 2.1 Implement LiveKitAdapter class with room management and token generation
    - Create `app/services/livekit_adapter.py` with LiveKitAdapter class
    - Implement `create_room(room_name, max_participants, empty_timeout)` using livekit-server-sdk RoomServiceClient
    - Implement `generate_token(room_name, identity, name, grants)` using livekit AccessToken with VideoGrants scoped to the specific room, identity set to user_id string, TTL of 24 hours max
    - Implement `delete_room(room_name)` with retry logic (3 attempts, 5-second intervals)
    - Implement `remove_participant(room_name, identity)` for kicking participants
    - Implement `list_participants(room_name)` for querying room state
    - Add 5-second timeout on all LiveKit API calls, raising ServiceUnavailableError on timeout
    - _Requirements: 1.2, 1.6, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 4.2, 4.6, 9.1_

  - [x]* 2.2 Write property test for token grant determinism (Property 4)
    - **Property 4: Token Grant Determinism**
    - For any participant role and session, verify that generated grants are deterministic: interviewers/interviewees get (can_publish=true, can_subscribe=true, can_publish_data=true), observers get (can_publish=false, can_subscribe=true, can_publish_data=false), identity equals str(user_id), room equals session room_name
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**

  - [x]* 2.3 Write unit tests for LiveKitAdapter
    - Test token generation for each role (interviewer, interviewee, observer)
    - Test room creation with valid parameters
    - Test delete_room retry logic on failure
    - Test 5-second timeout handling
    - Test invalid role rejection
    - _Requirements: 3.1, 3.2, 3.3, 3.7, 3.8, 4.6_

- [x] 3. Implement InterviewSessionService core logic
  - [x] 3.1 Implement create_session method
    - Create `app/services/session_service.py` with InterviewSessionService class
    - Implement `create_session(creator_id, title, scheduled_at, max_participants)` that validates title (1-500 chars) and max_participants (2-10), creates InterviewSession record, calls LiveKitAdapter.create_room with room_name pattern `interview_{session_id[:8]}`, rolls back DB on LiveKit failure
    - Return session_id, join_url, and room_name on success
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6_

  - [x]* 3.2 Write property test for session creation validation (Property 7)
    - **Property 7: Session Creation Validation**
    - For any title that is empty or exceeds 500 chars, or max_participants outside [2, 10], creation must be rejected. For valid inputs (1-500 char title, 2-10 max_participants), creation must succeed.
    - **Validates: Requirements 1.3, 1.4**

  - [x]* 3.3 Write property test for room name convention (Property 10)
    - **Property 10: Room Name Convention**
    - For any created session, room_name must follow pattern `interview_{session_id[:8]}` and be unique across all sessions.
    - **Validates: Requirement 1.2**

  - [x] 3.4 Implement join_session method with role constraints and rejoin logic
    - Implement `join_session(session_id, user_id, role)` following the design's join algorithm
    - Validate session exists and is not ended
    - Check participant count against max_participants
    - Enforce single interviewee constraint
    - Handle rejoin for disconnected participants (reactivate existing record)
    - Reject participants with status "removed"
    - Transition session from "scheduled" to "active" on first join
    - Generate LiveKit token with role-based grants
    - Return JoinResult with token, room_name, and participant list
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 5.3, 5.4, 5.7_

  - [x]* 3.5 Write property test for participant limit invariant (Property 1)
    - **Property 1: Participant Limit Invariant**
    - For any active session and any sequence of join/leave operations, the count of connected participants shall never exceed max_participants.
    - **Validates: Requirements 2.2, 5.3**

  - [x]* 3.6 Write property test for single interviewee constraint (Property 2)
    - **Property 2: Single Interviewee Constraint**
    - For any session and any sequence of join operations, the count of connected interviewees shall never exceed 1.
    - **Validates: Requirement 2.3**

  - [x]* 3.7 Write property test for rejoin idempotency (Property 6)
    - **Property 6: Rejoin Idempotency**
    - For any user who has left a session, rejoining reactivates the existing record. The total count of participant records for that (user_id, session_id) is always exactly 1.
    - **Validates: Requirements 2.4, 5.4**

  - [x] 3.8 Implement end_session and session lifecycle management
    - Implement `end_session(session_id, ended_by)` that validates caller is interviewer/admin, transitions status to "ended", records ended_at, disconnects all connected participants, calls LiveKitAdapter.delete_room
    - Implement `leave_session(session_id, user_id)` that sets participant status to "disconnected" and records left_at
    - Enforce status monotonicity: only scheduled→active→ended transitions allowed
    - _Requirements: 4.1, 4.2, 4.3, 5.2_

  - [x]* 3.9 Write property test for status monotonicity (Property 3)
    - **Property 3: Status Monotonicity**
    - For any session and any sequence of state transition attempts, status only progresses forward (scheduled→active→ended). No backward transition shall succeed.
    - **Validates: Requirements 2.5, 2.6, 4.1, 4.3**

  - [x] 3.10 Implement empty_timeout auto-end logic
    - Implement background task that monitors active sessions where all interviewers have disconnected
    - Start 5-minute countdown when last interviewer leaves
    - Cancel countdown if an interviewer rejoins within the timeout
    - Auto-end session and delete LiveKit room when countdown expires
    - Use Redis for timeout tracking (set key with TTL, cancel by deleting key)
    - _Requirements: 4.4, 4.5, 9.4, 9.5_

  - [x] 3.11 Implement participant management (list, remove)
    - Implement `list_participants(session_id)` returning all participant records with user_id, display_name, role, status, joined_at
    - Implement `remove_participant(session_id, user_id, removed_by)` that validates caller is interviewer/admin, sets participant status to "removed", records left_at, calls LiveKitAdapter.remove_participant
    - _Requirements: 5.5, 5.6_

- [x] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement PresentationService
  - [x] 5.1 Implement presentation upload and file conversion
    - Create `app/services/presentation_service.py` with PresentationService class
    - Implement `upload_presentation(session_id, file, uploaded_by)` following the design's upload algorithm
    - Validate file extension (.ppt, .pptx, .pdf, .key), MIME type matching, and size (≤50MB)
    - Store original file in MinIO/S3 at path `interviews/{session_id}/presentations/{uuid}{ext}`
    - Convert to slide images using LibreOffice headless (PPT/PPTX) or pdf2image (PDF) with 120-second timeout
    - Deactivate previous active presentation for the session
    - Notify all participants via LiveKit data channel with presentation_id and slide_count
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 10.4, 10.5_

  - [x]* 5.2 Write property test for file upload validation (Property 8)
    - **Property 8: File Upload Validation**
    - For any file exceeding 50MB, or with extension not in {.ppt, .pptx, .pdf, .key}, or with MIME type mismatch, upload must be rejected. Valid files must be accepted.
    - **Validates: Requirements 6.2, 6.3, 10.4**

  - [x]* 5.3 Write property test for single active presentation (Property 9)
    - **Property 9: Single Active Presentation**
    - For any session, after any upload_presentation operation, there shall be exactly one active presentation. All previously active presentations shall be deactivated.
    - **Validates: Requirement 6.6**

  - [x] 5.4 Implement slide navigation and synchronization
    - Implement `set_current_slide(presentation_id, slide_index, changed_by)` that validates slide_index is in [0, slide_count-1], validates caller has interviewer/interviewee role (reject observers), updates current_slide, broadcasts slide_change via LiveKit data channel within 500ms
    - Apply last-write-wins for concurrent navigation based on server-side receipt time
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_

  - [x]* 5.5 Write property test for slide index bounds (Property 5)
    - **Property 5: Slide Index Bounds**
    - For any active presentation and any sequence of set_current_slide operations (including rejected out-of-bounds attempts), current_slide always satisfies 0 <= current_slide < slide_count.
    - **Validates: Requirements 7.2, 7.3**

- [x] 6. Implement API routes and webhook handling
  - [x] 6.1 Create session API endpoints
    - Create `app/api/v1/sessions.py` with FastAPI router
    - `POST /api/v1/interviews/sessions` — create session (requires interviewer/admin role)
    - `GET /api/v1/interviews/sessions` — list sessions for authenticated user
    - `GET /api/v1/interviews/sessions/{session_id}` — get session details
    - `POST /api/v1/interviews/sessions/{session_id}/join` — join session
    - `POST /api/v1/interviews/sessions/{session_id}/leave` — leave session
    - `POST /api/v1/interviews/sessions/{session_id}/end` — end session (interviewer/admin only)
    - Add JWT validation middleware that verifies signature, token type "access", and expiration on every request
    - Return HTTP 401 with error reason on auth failure
    - _Requirements: 1.1, 1.5, 2.1, 4.1, 5.5, 10.1, 10.2_

  - [x] 6.2 Create participant management API endpoints
    - Add to sessions router or create `app/api/v1/participants.py`
    - `GET /api/v1/interviews/sessions/{session_id}/participants` — list participants (session members only)
    - `DELETE /api/v1/interviews/sessions/{session_id}/participants/{user_id}` — remove participant (interviewer/admin only)
    - _Requirements: 5.5, 5.6_

  - [x] 6.3 Create presentation API endpoints
    - Create `app/api/v1/presentations.py` with FastAPI router
    - `POST /api/v1/interviews/sessions/{session_id}/presentations` — upload presentation (interviewer/interviewee only, active session only)
    - `GET /api/v1/interviews/sessions/{session_id}/presentations/{presentation_id}` — get presentation details
    - `PATCH /api/v1/interviews/sessions/{session_id}/presentations/{presentation_id}` — change current slide
    - `DELETE /api/v1/interviews/sessions/{session_id}/presentations/{presentation_id}` — delete presentation
    - _Requirements: 6.1, 7.1, 7.5_

  - [x] 6.4 Implement LiveKit webhook handler for participant events
    - Create `app/api/v1/webhooks.py` with webhook endpoint
    - `POST /api/v1/interviews/webhooks/livekit` — receive LiveKit webhook events
    - Handle `participant_disconnected` event: update participant status to "disconnected" within 5 seconds
    - Handle `room_finished` event: clean up session state
    - Validate webhook signature using LiveKit API secret
    - _Requirements: 5.1, 9.3_

  - [x]* 6.5 Write integration tests for API endpoints
    - Test full session lifecycle: create → join → leave → end
    - Test participant limit enforcement via API
    - Test presentation upload and slide navigation via API
    - Test JWT validation and role-based access control
    - Test error responses (404, 401, 403, 422, 503)
    - _Requirements: 1.1, 2.1, 4.1, 6.1, 7.1, 9.1, 10.1_

- [x] 7. Implement gateway routing and service registration
  - [x] 7.1 Add Traefik route configuration for interview-svc
    - Update `services/gateway/routes.yml` to add routing rules for `/api/v1/interviews/*` to interview-svc
    - Configure path prefix stripping and service discovery
    - Add health check endpoint `/health` in interview-svc
    - _Requirements: 1.1, 2.1_

- [x] 8. Implement frontend components for interview session
  - [x] 8.1 Create InterviewSessionPage with LiveKit video grid
    - Create `frontend/src/pages/InterviewPages/InterviewSessionPage.jsx`
    - Integrate `@livekit/components-react` LiveKitRoom and VideoConference components
    - Connect to LiveKit server using token from join API response
    - Display video tiles for all participants with role labels
    - Show "reconnecting" indicator when WebRTC connection drops (60-second timeout before showing "disconnected")
    - _Requirements: 8.1, 8.2, 8.4, 9.3_

  - [x] 8.2 Create PresentationViewer component with slide synchronization
    - Create `frontend/src/components/Interview/PresentationViewer.jsx`
    - Display current slide image from presentation slides array
    - Listen for `slide_change` data channel messages and update displayed slide
    - Provide next/previous slide navigation controls for interviewers and interviewees
    - Hide navigation controls for observers
    - _Requirements: 7.1, 7.5, 8.2_

  - [x] 8.3 Create screen sharing controls and display
    - Add screen share button to InterviewSessionPage for interviewers and interviewees
    - Use LiveKit client `publishTrack` for screen-share track publishing
    - Handle unpublish on stop sharing or disconnect
    - Allow up to 2 concurrent screen-share tracks per session
    - Hide screen share button for observers
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

  - [x] 8.4 Create session management UI (create, join, end)
    - Create `frontend/src/pages/InterviewPages/CreateInterviewPage.jsx` with form for title, scheduled_at, max_participants
    - Create join flow that calls join API and redirects to InterviewSessionPage with token
    - Add end session button for interviewers with confirmation dialog
    - Add participant list sidebar showing connected participants with roles
    - _Requirements: 1.1, 1.5, 2.1, 4.1, 5.5_

- [x] 9. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Wire everything together and final integration
  - [x] 10.1 Add recording notification support
    - Implement recording state tracking in InterviewSession model
    - Notify all connected participants when recording starts
    - Notify newly joining participants if recording is already active
    - _Requirements: 10.7_

  - [x] 10.2 Add error handling middleware and structured error responses
    - Create `app/core/exceptions.py` with custom exception classes (SessionNotFoundError, SessionFullError, DuplicateIntervieweeError, etc.)
    - Create exception handler middleware that maps exceptions to appropriate HTTP status codes and structured error responses
    - Ensure HTTP 503 with retry_after=5 for LiveKit timeouts
    - Ensure HTTP 422 for conversion failures with retry guidance
    - _Requirements: 9.1, 9.2_

  - [x]* 10.3 Write end-to-end integration tests
    - Test complete flow: create session → multiple participants join → upload presentation → navigate slides → end session
    - Test webhook-driven participant disconnect handling
    - Test empty_timeout auto-end behavior
    - Test recording notification delivery
    - _Requirements: 4.4, 4.5, 5.1, 6.7, 7.4, 10.7_

- [x] 11. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document using Hypothesis (Python)
- Unit tests validate specific examples and edge cases
- The backend uses Python/FastAPI consistent with the existing proctoAi service architecture
- Frontend uses React with @livekit/components-react for video UI
- LiveKit server SDK handles room management and token generation server-side
- File conversion (PPT→images) should be offloaded to a Celery worker for production, but can be synchronous for initial implementation

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.3"] },
    { "id": 1, "tasks": ["1.2", "1.4"] },
    { "id": 2, "tasks": ["2.1", "3.1"] },
    { "id": 3, "tasks": ["2.2", "2.3", "3.2", "3.3", "3.4"] },
    { "id": 4, "tasks": ["3.5", "3.6", "3.7", "3.8"] },
    { "id": 5, "tasks": ["3.9", "3.10", "3.11"] },
    { "id": 6, "tasks": ["5.1"] },
    { "id": 7, "tasks": ["5.2", "5.3", "5.4"] },
    { "id": 8, "tasks": ["5.5", "6.1", "6.2", "6.3"] },
    { "id": 9, "tasks": ["6.4", "6.5", "7.1"] },
    { "id": 10, "tasks": ["8.1", "8.4"] },
    { "id": 11, "tasks": ["8.2", "8.3"] },
    { "id": 12, "tasks": ["10.1", "10.2"] },
    { "id": 13, "tasks": ["10.3"] }
  ]
}
```
