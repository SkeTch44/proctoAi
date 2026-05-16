# Implementation Plan: Interview Cheat Detection

## Overview

This plan implements real-time anti-cheating capabilities for the interview session system. The implementation spans the `interview-svc` (Python/FastAPI), `proctoring-svc` (Python), and the frontend (TypeScript/React). The approach builds data models first, then core detection logic, then API/integration layers, and finally wires everything together with LiveKit data channels.

## Tasks

- [x] 1. Define data models and enumerations
  - [x] 1.1 Create AlertType enum and Pydantic models (CheatDetectionResult, RiskSummary)
    - Create `services/interview-svc/app/models/cheat_models.py`
    - Define `AlertType` enum with all 14 alert types (MULTIPLE_FACES, NO_FACE, GAZE_AWAY, PHONE_DETECTED, BOOK_DETECTED, TAB_SWITCH, COPY_DETECTED, PASTE_DETECTED, DEVTOOLS_OPEN, FULLSCREEN_EXIT, MULTIPLE_SPEAKERS, WHISPER_DETECTED, SUSPICIOUS_PATTERN)
    - Define `CheatDetectionResult` Pydantic model with validation: score in [0, 100], confidence in [0.0, 1.0], verdict in {SAFE, MILD, HIGH, CRITICAL}
    - Define `RiskSummary` Pydantic model with all fields from design
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6_

  - [x] 1.2 Create SQLAlchemy models (CheatAlert, CheatMonitoringState)
    - Create `services/interview-svc/app/models/cheat_alert.py`
    - Define `CheatAlert` table with columns: id, session_id, alert_type, severity, score, confidence, details, evidence_snapshot, created_at, acknowledged, acknowledged_by, acknowledged_at
    - Define `CheatMonitoringState` table with columns: id, session_id, status, started_at, stopped_at, total_frames_processed, total_events_processed, total_alerts_generated, current_risk_score, current_verdict, config
    - Add foreign key constraints to interview_sessions table
    - Add validation constraints (score range, severity enum, status enum)
    - _Requirements: 11.1, 11.2, 11.3, 11.7, 11.8, 11.9_

  - [ ]* 1.3 Write property tests for data model validation
    - **Property 12: Data Validation Completeness**
    - **Validates: Requirements 11.1, 11.2, 11.3, 11.4, 11.5**
    - Use Hypothesis to generate random CheatDetectionResult instances and verify all constraints hold
    - Test that invalid alert_type, severity, score, confidence values are rejected

  - [x] 1.4 Create Alembic migration for cheat detection tables
    - Create migration file for `cheat_alerts` and `cheat_monitoring_states` tables
    - Include indexes on session_id and created_at for query performance
    - _Requirements: 11.9, 13.6_

- [x] 2. Implement risk score aggregation and verdict determination
  - [x] 2.1 Implement the verdict determination function
    - Create `services/interview-svc/app/services/verdict.py`
    - Implement `determine_verdict(risk_score: float) -> str` with thresholds: [0,30)→SAFE, [30,50)→MILD, [50,80)→HIGH, [80,100]→CRITICAL
    - Implement input clamping for scores outside [0, 100]
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

  - [ ]* 2.2 Write property tests for verdict monotonicity
    - **Property 2: Verdict Monotonicity with Score**
    - **Validates: Requirements 6.1, 6.2**
    - Use Hypothesis to generate pairs of scores and verify monotonicity

  - [x] 2.3 Implement risk score aggregation with EMA smoothing
    - Create `services/interview-svc/app/services/risk_aggregator.py`
    - Implement `aggregate_risk_score(session_id, new_signal, new_score) -> float`
    - Implement EMA smoothing with α = 0.3
    - Implement multi-signal boost: `boost = 1 + (active_count - 1) * 0.1`
    - Implement signal window expiry (30 seconds)
    - Implement aggregation formula: `min(100, (max_score * 0.6 + avg_score * 0.4) * boost)`
    - Use Redis for signal history storage with in-memory fallback
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7_

  - [ ]* 2.4 Write property tests for risk score boundedness
    - **Property 1: Risk Score Boundedness**
    - **Validates: Requirements 5.2, 11.3, 11.6**
    - Use Hypothesis to generate arbitrary sequences of signal scores and verify output is always in [0, 100]

  - [ ]* 2.5 Write property tests for EMA convergence
    - **Property 4: Temporal Smoothing Convergence**
    - **Validates: Requirements 5.1, 5.8**
    - Use Hypothesis to generate constant values and verify convergence within 10 iterations to within 2 units

  - [ ]* 2.6 Write property tests for multi-signal boost boundedness
    - **Property 5: Multi-Signal Boost Boundedness**
    - **Validates: Requirements 5.3, 5.4**
    - Use Hypothesis to generate sets of active signals and verify final score never exceeds 100

  - [ ]* 2.7 Write property tests for signal window expiry
    - **Property 9: Signal Window Expiry**
    - **Validates: Requirement 5.5**
    - Verify that signals older than 30 seconds are excluded from aggregation

- [x] 3. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Implement CheatMonitor orchestrator
  - [x] 4.1 Implement monitoring lifecycle management (start/stop/pause)
    - Create `services/interview-svc/app/services/cheat_monitor.py`
    - Implement `start_monitoring(session_id, room_name, candidate_identity)`
    - Implement `stop_monitoring(session_id)`
    - Enforce state transitions: inactive → active → (paused ↔ active) → inactive
    - Reject invalid transitions with descriptive error messages
    - Initialize Redis keys for signal tracking on start
    - Persist final statistics on stop
    - _Requirements: 1.1, 1.2, 1.4, 1.5, 1.7, 1.8_

  - [ ]* 4.2 Write property tests for monitoring state lifecycle
    - **Property 6: Monitoring State Lifecycle**
    - **Validates: Requirements 1.7, 1.5**
    - Use Hypothesis to generate random sequences of start/stop/pause operations and verify state never enters an invalid state

  - [x] 4.3 Implement the main monitoring loop
    - Implement `monitoring_loop(session_id, room_name, candidate_identity)` as an asyncio background task
    - Frame capture at 2-second intervals (0.5 FPS)
    - Audio capture at 5-second intervals
    - Risk broadcast to interviewers every 10 seconds
    - Proper cancellation handling via `asyncio.create_task`
    - Skip visually identical frames using perceptual hash (hamming distance threshold 5 bits)
    - _Requirements: 1.3, 2.1, 2.7, 4.1_

  - [ ]* 4.4 Write property tests for frame rate limiting
    - **Property 7: Frame Rate Limiting**
    - **Validates: Requirement 2.1**
    - Verify that no more than 1 frame is processed per 2-second window

  - [x] 4.5 Implement process_frame method
    - Forward frame to proctoring-svc via `POST /api/v1/proctoring/frame`
    - Handle YOLO detection results (multiple faces, phone, book)
    - Handle gaze estimation results
    - Generate alerts for MULTIPLE_FACES (confidence > 0.6), NO_FACE (10s absence), GAZE_AWAY (3s deviation), PHONE_DETECTED, BOOK_DETECTED
    - Update monitoring state counters
    - _Requirements: 2.2, 2.3, 2.4, 2.5, 2.6, 2.8_

  - [x] 4.6 Implement process_browser_event method with deduplication
    - Forward events to proctoring-svc via `POST /api/v1/proctoring/event`
    - Apply interview-specific scoring adjustments
    - Implement deduplication using composite key (session_id, event_type, timestamp)
    - Retain deduplication state for 30 seconds
    - Return cached result for duplicate events
    - Update risk cache and event counters
    - _Requirements: 3.7, 12.1, 12.2, 12.3, 12.4, 12.5_

  - [ ]* 4.7 Write property tests for browser event idempotency
    - **Property 10: Browser Event Idempotency**
    - **Validates: Requirements 12.1, 12.2**
    - Use Hypothesis to generate events and verify processing same event twice yields identical results

  - [x] 4.8 Implement process_audio_segment method
    - Forward audio to proctoring-svc via `POST /api/v1/proctoring/audio`
    - Handle multiple speaker detection and whispering detection
    - Skip analysis when audio track unavailable or insufficient data
    - Generate alerts for HIGH/CRITICAL audio verdicts
    - _Requirements: 4.1, 4.6, 4.7, 4.8_

  - [x] 4.9 Implement get_session_risk_summary and get_alert_history
    - Query current risk score from Redis (or in-memory fallback)
    - Aggregate alert counts by severity and type from PostgreSQL
    - Calculate monitoring duration
    - Return top 3 active signals
    - Implement paginated alert history (default 50, max 100)
    - _Requirements: 8.1, 8.2_

- [x] 5. Implement AlertDispatcher
  - [x] 5.1 Create AlertDispatcher service
    - Create `services/interview-svc/app/services/alert_dispatcher.py`
    - Implement `dispatch_alert(session_id, room_name, alert)` - sends alert via LiveKit data channel
    - Implement `dispatch_risk_update(session_id, room_name, risk_summary)` - periodic risk updates
    - Implement `dispatch_monitoring_status(session_id, room_name, status)` - monitoring started/stopped/degraded/restored
    - Ensure alert payload includes all required fields: alert_id, alert_type, severity, score, confidence, details, timestamp, session_id
    - Ensure alerts only go to the specific session room (no cross-session leakage)
    - Handle LiveKit send failures gracefully (log, don't retry)
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7_

  - [ ]* 5.2 Write property tests for alert dispatch targeting
    - **Property 8: Alert Dispatch Targeting**
    - **Validates: Requirement 7.5**
    - Verify alerts are only sent to the correct room

  - [ ]* 5.3 Write property tests for alert payload completeness
    - **Property 14: Alert Payload Completeness**
    - **Validates: Requirement 7.3**
    - Use Hypothesis to generate CheatAlert instances and verify all required fields are present in the dispatch payload

  - [ ]* 5.4 Write property tests for alert generation threshold consistency
    - **Property 3: Alert Generation Threshold Consistency**
    - **Validates: Requirements 6.3, 6.4**
    - Verify should_alert is true iff verdict is HIGH or CRITICAL

- [x] 6. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Implement error handling and resilience
  - [x] 7.1 Implement proctoring-svc failure handling in CheatMonitor
    - Add 3-second timeout to all proctoring-svc HTTP calls
    - Skip detection cycle on timeout or 5xx response
    - Track consecutive failures; emit "monitoring_degraded" after 5 failures
    - Emit "monitoring_restored" on recovery and reset failure counter
    - _Requirements: 10.1, 10.2, 10.3_

  - [x] 7.2 Implement Redis fallback to in-memory tracking
    - Detect Redis unavailability (connection refused, timeout > 1 second)
    - Fall back to in-memory dict for risk scores and signal history
    - Resume Redis writes when connectivity is restored
    - _Requirements: 10.4_

  - [x] 7.3 Implement frame capture failure handling
    - Skip frame analysis when video track is unpublished
    - Generate single NO_FACE alert after 10 seconds of continuous absence
    - Do not repeat alert until track is re-published and unpublished again
    - Handle invalid base64/JPEG data gracefully (log and skip)
    - _Requirements: 10.5, 10.6_

  - [x] 7.4 Implement LiveKit data channel failure handling
    - Catch exceptions from send_data operations
    - Log failure without retrying (alert already persisted to PostgreSQL)
    - Apply 2-second timeout to send operations
    - _Requirements: 10.7_

- [x] 8. Implement AudioAnomalyDetector in proctoring-svc
  - [x] 8.1 Create AudioAnomalyDetector class
    - Create `services/proctoring-svc/app/inference/audio_anomaly_detector.py`
    - Implement `analyze_segment(audio_data, sample_rate)` returning AudioAnalysisResult
    - Implement `detect_multiple_speakers(audio_data, sample_rate)` using spectral clustering on mel-frequency features
    - Implement `detect_whispering(audio_data, sample_rate)` using frequency spectrum analysis
    - Implement `get_voice_activity(audio_data, sample_rate)` for speech/silence distinction
    - Require minimum 1 second of audio data (sample_rate samples)
    - Return non-suspicious result for insufficient data
    - Ensure no mutation of input audio_data array
    - _Requirements: 4.2, 4.3, 4.4, 4.5, 4.8_

  - [ ]* 8.2 Write property tests for audio input immutability
    - **Property 13: Audio Input Immutability**
    - **Validates: Requirement 4.5**
    - Use Hypothesis to generate random numpy arrays and verify they are unchanged after analysis

  - [x] 8.3 Create proctoring-svc audio endpoint
    - Add `POST /api/v1/proctoring/audio` endpoint to proctoring-svc
    - Accept audio_data, sample_rate, session_id, session_kind
    - Return AudioAnalysisResult with suspicious flag, speaker_count, whisper_detected, confidence
    - _Requirements: 4.2, 4.3_

- [x] 9. Implement InterviewCheatEventRouter (API layer)
  - [x] 9.1 Create the cheat events FastAPI router
    - Create `services/interview-svc/app/routers/cheat_events.py`
    - Implement `POST /api/v1/interviews/sessions/{session_id}/cheat-events` endpoint
    - Implement `GET /api/v1/interviews/sessions/{session_id}/cheat-summary` endpoint
    - Implement `GET /api/v1/interviews/sessions/{session_id}/cheat-alerts` endpoint
    - Implement `POST /api/v1/interviews/sessions/{session_id}/cheat-monitoring/start` endpoint
    - Implement `POST /api/v1/interviews/sessions/{session_id}/cheat-monitoring/stop` endpoint
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

  - [x] 9.2 Implement request validation and error responses
    - Validate browser events: non-empty session_id, valid AlertType event_type, well-formed ISO 8601 timestamp
    - Return validation error for missing/invalid fields
    - Return HTTP 409 for start on ended session or already-active monitoring
    - Return HTTP 429 for rate limit exceeded (>10 events/sec per session)
    - Return default response (score 0, verdict SAFE) for sessions with no monitoring state
    - _Requirements: 1.4, 1.5, 3.7, 3.8, 8.4, 8.5, 11.8_

  - [x] 9.3 Implement JWT authentication and role-based authorization
    - Require valid JWT on all endpoints
    - Return HTTP 401 for missing, malformed, or expired JWT
    - Validate candidate can only report events for their own session (JWT subject == session candidate)
    - Return HTTP 403 when candidate attempts to access cheat scores/alerts/summaries
    - Allow only interviewers and admins to access cheat data and start/stop monitoring
    - _Requirements: 13.1, 13.2, 13.3, 13.4_

- [x] 10. Implement no-auto-fail safeguards
  - [x] 10.1 Add no-auto-fail constraints to CheatMonitor
    - Ensure CheatMonitor never calls session termination, room close, or candidate removal APIs
    - Limit automated actions to: creating CheatAlert records, updating Redis risk score, notifying interviewer via data channel
    - Ensure no alert content, risk score, or verdict is sent to candidate's client
    - Add explicit guard checks before any session-modifying operation
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

  - [ ]* 10.2 Write property tests for no-auto-fail guarantee
    - **Property 11: No Auto-Fail Guarantee**
    - **Validates: Requirements 9.1, 9.2, 9.3, 9.4**
    - Use Hypothesis to generate arbitrary risk scores and verdicts and verify no session termination or candidate removal occurs

- [x] 11. Implement BrowserMonitor (Frontend)
  - [x] 11.1 Create BrowserMonitor TypeScript module
    - Create `frontend/src/services/cheat-detection/browser-monitor.ts`
    - Implement `start(sessionId, apiBaseUrl)` and `stop()` methods
    - Implement tab switch detection via `visibilitychange` event listener
    - Implement copy/paste detection via clipboard API interception
    - Implement DevTools detection using timing heuristics
    - Implement fullscreen exit detection
    - Implement 2-second debounce per event type
    - Implement event batching: flush every 5 seconds or at 10 events
    - Implement retry queue (max 50 events) for network failures
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.9_

  - [x] 11.2 Integrate BrowserMonitor into ExamRoom/InterviewRoom page
    - Import and initialize BrowserMonitor when interview session starts
    - Pass session JWT for authenticated event reporting
    - Stop BrowserMonitor when interview ends
    - _Requirements: 3.1, 13.3_

- [x] 12. Implement security and audit trail
  - [x] 12.1 Add audit logging for monitoring state transitions
    - Log all state transitions (inactive→active, active→paused, etc.) with timestamps
    - Persist transition records for post-interview review
    - Ensure AlertDispatcher does not include PII beyond session_id in payloads
    - _Requirements: 13.5, 13.6_

  - [x] 12.2 Add rate limiting middleware for cheat event endpoint
    - Implement per-session rate limiting (10 events/second)
    - Return HTTP 429 for excess events
    - Discard rejected events without affecting risk score
    - _Requirements: 8.4_

- [x] 13. Wire components together and integration
  - [x] 13.1 Register cheat events router in interview-svc main app
    - Add router to FastAPI app with proper prefix
    - Configure dependency injection for CheatMonitor, AlertDispatcher, Redis, DB session
    - Add LiveKit webhook handler to trigger monitoring on track_published events
    - _Requirements: 1.1, 1.6_

  - [x] 13.2 Add Traefik route for cheat event endpoints
    - Update `services/gateway/routes.yml` to route `/api/v1/interviews/sessions/*/cheat-*` to interview-svc
    - _Requirements: 3.7_

  - [ ]* 13.3 Write integration tests for full detection flow
    - Test browser event → interview-svc → proctoring-svc → alert → LiveKit data channel
    - Test frame capture → analysis → risk aggregation → alert dispatch
    - Test monitoring lifecycle: start → process events → stop → verify final state
    - Test Redis failover with in-memory fallback
    - _Requirements: 1.1, 1.2, 1.3, 7.1, 7.2, 10.4_

- [x] 14. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- The implementation uses Python (FastAPI) for backend services and TypeScript for the frontend BrowserMonitor
- Redis is used for real-time score caching with in-memory fallback for resilience
- LiveKit data channels provide sub-100ms alert delivery to interviewers

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2"] },
    { "id": 1, "tasks": ["1.3", "1.4", "2.1"] },
    { "id": 2, "tasks": ["2.2", "2.3"] },
    { "id": 3, "tasks": ["2.4", "2.5", "2.6", "2.7", "4.1"] },
    { "id": 4, "tasks": ["4.2", "4.3", "5.1", "8.1"] },
    { "id": 5, "tasks": ["4.4", "4.5", "4.6", "4.8", "5.2", "5.3", "5.4", "8.2", "8.3"] },
    { "id": 6, "tasks": ["4.7", "4.9", "7.1", "7.2", "7.3", "7.4"] },
    { "id": 7, "tasks": ["9.1", "10.1", "11.1"] },
    { "id": 8, "tasks": ["9.2", "9.3", "10.2", "11.2", "12.1", "12.2"] },
    { "id": 9, "tasks": ["13.1", "13.2"] },
    { "id": 10, "tasks": ["13.3"] }
  ]
}
```
