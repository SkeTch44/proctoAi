# Requirements Document

## Introduction

This document defines the requirements for the Interview Cheat Detection feature, which integrates real-time anti-cheating capabilities into the existing interview session system. The system monitors candidate behavior during live interviews through video frame analysis, browser event monitoring, audio anomaly detection, and screen-sharing validation. It follows a "no auto-fail" philosophy where suspicious behavior is scored, smoothed over time, and surfaced as alerts to interviewers who make the final judgment.

## Glossary

- **CheatMonitor**: The orchestrator component within interview-svc that coordinates all cheat detection activities for a given interview session.
- **BrowserMonitor**: Client-side JavaScript module that detects browser-level cheating behaviors (tab switches, copy-paste, DevTools, fullscreen exit) and reports them to the backend.
- **AlertDispatcher**: Component responsible for formatting and delivering cheat alerts to interviewers via LiveKit data channels.
- **InterviewCheatEventRouter**: FastAPI router providing REST API endpoints for receiving browser events and querying alert/risk data.
- **AudioAnomalyDetector**: Component within proctoring-svc that analyzes audio segments for multiple speakers and whispering patterns.
- **RiskScore**: A numeric value in the range [0, 100] representing the aggregated suspicion level for a session.
- **Verdict**: A categorical severity classification derived from the risk score: SAFE, MILD, HIGH, or CRITICAL.
- **Signal**: An individual detection channel output (e.g., gaze_away, tab_switch, multiple_speakers) with its own score.
- **EMA**: Exponential Moving Average, the temporal smoothing algorithm applied to signal scores.
- **SignalWindow**: The 30-second time window during which signals are considered "active" for aggregation.
- **LiveKit_Data_Channel**: The WebRTC-based communication channel used to deliver real-time alerts to interviewers.
- **AlertType**: An enumeration of all detectable cheating behaviors (MULTIPLE_FACES, TAB_SWITCH, DEVTOOLS_OPEN, etc.).
- **MonitoringState**: The lifecycle state of cheat monitoring for a session (inactive, active, paused).

## Requirements

### Requirement 1: Monitoring Lifecycle Management

**User Story:** As an interviewer, I want to start and stop cheat monitoring for an interview session, so that I can control when candidate behavior is being analyzed.

#### Acceptance Criteria

1. WHEN an interviewer starts monitoring on an active interview session, THE CheatMonitor SHALL create a monitoring state record with status "active" and begin the detection loop.
2. WHEN an interviewer stops monitoring, THE CheatMonitor SHALL transition the monitoring state to "inactive", cancel the detection loop, and persist final statistics including total frames processed, total events processed, total alerts generated, and the final risk score.
3. WHILE monitoring is active, THE CheatMonitor SHALL process video frames at a rate of one frame every 2 seconds, browser events as they arrive, and audio segments every 5 seconds, until monitoring is stopped.
4. IF monitoring start is attempted on a session that has already ended, THEN THE InterviewCheatEventRouter SHALL return HTTP 409 Conflict with an error message indicating the session has ended.
5. IF monitoring start is attempted on a session that already has active monitoring, THEN THE InterviewCheatEventRouter SHALL return HTTP 409 Conflict with an error message indicating monitoring is already active, and the existing monitoring state SHALL remain unchanged.
6. WHEN monitoring is started, THE AlertDispatcher SHALL notify all connected interviewers via LiveKit data channel with a "monitoring_started" message.
7. THE MonitoringState SHALL follow the lifecycle: inactive → active → (paused ↔ active) → inactive, and no other transitions shall be permitted.
8. IF an invalid state transition is attempted, THEN THE CheatMonitor SHALL reject the request, return an error message indicating the current state and the disallowed transition, and leave the monitoring state unchanged.

### Requirement 2: Video Frame Analysis

**User Story:** As an interviewer, I want the system to analyze the candidate's video feed for visual cheating indicators, so that I am alerted to suspicious visual behavior in real time.

#### Acceptance Criteria

1. WHILE monitoring is active, THE CheatMonitor SHALL capture and analyze video frames at a rate of one frame every 2 seconds (0.5 FPS).
2. WHEN a frame is analyzed, THE CheatMonitor SHALL forward it to proctoring-svc for YOLO-based object detection and gaze estimation.
3. WHEN 2 or more faces are detected in a frame with confidence above 0.6, THE CheatMonitor SHALL generate a MULTIPLE_FACES alert with confidence equal to the detection model's reported confidence value.
4. WHEN no face is detected for more than 10 consecutive seconds (5 consecutive frames), THE CheatMonitor SHALL generate a NO_FACE alert with confidence 0.5.
5. WHEN gaze direction deviates from the screen continuously for more than 3 seconds, THE CheatMonitor SHALL generate a GAZE_AWAY alert with confidence equal to the gaze estimation model's reported confidence value.
6. WHEN a phone or book is detected in the frame with confidence above 0.6, THE CheatMonitor SHALL generate a PHONE_DETECTED or BOOK_DETECTED alert respectively with confidence equal to the detection model's reported confidence value.
7. THE CheatMonitor SHALL skip frames that are visually identical to the previous frame using perceptual hash comparison (hamming distance threshold of 5 bits).
8. IF proctoring-svc returns no detection results for a frame, THEN THE CheatMonitor SHALL discard that frame without generating any alert and proceed to the next capture cycle.

### Requirement 3: Browser Event Detection

**User Story:** As an interviewer, I want the system to detect browser-level cheating behaviors on the candidate's machine, so that I am informed when the candidate navigates away or uses developer tools.

#### Acceptance Criteria

1. WHEN the candidate switches tabs or loses window focus, THE BrowserMonitor SHALL detect the visibilitychange event and report a TAB_SWITCH event to the backend including the session_id, event_type, and an ISO 8601 timestamp.
2. WHEN the candidate performs a copy or paste operation, THE BrowserMonitor SHALL intercept the clipboard event and report a COPY_DETECTED or PASTE_DETECTED event to the backend.
3. WHEN the candidate opens browser DevTools, THE BrowserMonitor SHALL detect it using timing heuristics and report a DEVTOOLS_OPEN event to the backend.
4. WHEN the candidate exits fullscreen mode during the interview, THE BrowserMonitor SHALL report a FULLSCREEN_EXIT event to the backend.
5. THE BrowserMonitor SHALL debounce events of the same type using a minimum interval of 2 seconds, discarding subsequent occurrences of the same event type within that window.
6. THE BrowserMonitor SHALL batch queued events and flush them to the InterviewCheatEventRouter endpoint every 5 seconds or when the batch reaches 10 events, whichever occurs first.
7. WHEN a browser event is received, THE InterviewCheatEventRouter SHALL validate that the request contains a non-empty session_id, a valid AlertType event_type, and a well-formed ISO 8601 timestamp, authenticate the caller via JWT, and route the event to the CheatMonitor.
8. IF the InterviewCheatEventRouter receives a browser event with missing or invalid required fields, THEN THE InterviewCheatEventRouter SHALL reject the request with an error response indicating the validation failure and SHALL NOT route the event to the CheatMonitor.
9. IF the BrowserMonitor fails to deliver a batch due to a network error, THEN THE BrowserMonitor SHALL retain the unsent events in its local queue (up to a maximum of 50 events) and retry delivery on the next flush cycle.

### Requirement 4: Audio Anomaly Detection

**User Story:** As an interviewer, I want the system to detect audio anomalies such as secondary speakers or whispering, so that I am alerted to potential coaching during the interview.

#### Acceptance Criteria

1. WHILE monitoring is active, THE CheatMonitor SHALL capture and analyze audio segments of up to 5 seconds duration every 5 seconds.
2. WHEN more than one speaker is detected in an audio segment with confidence above 0.6, THE AudioAnomalyDetector SHALL return a suspicious result with the speaker count and a MULTIPLE_SPEAKERS alert type.
3. WHEN whispering patterns are detected in the audio frequency spectrum with confidence above 0.6, THE AudioAnomalyDetector SHALL return a suspicious result indicating whisper detection with a WHISPER_DETECTED alert type.
4. THE AudioAnomalyDetector SHALL use at least 1 second of audio data (sample_rate samples) for analysis.
5. THE AudioAnomalyDetector SHALL not mutate the input audio data during analysis.
6. WHEN an audio anomaly result yields a verdict of HIGH or CRITICAL, THE CheatMonitor SHALL generate an alert and dispatch it to interviewers via the AlertDispatcher.
7. IF the candidate's audio track is unavailable or unpublished, THEN THE CheatMonitor SHALL skip audio analysis for that cycle and continue monitoring on the next cycle without generating an alert.
8. IF the audio segment contains insufficient data (less than 1 second of audio), THEN THE AudioAnomalyDetector SHALL skip analysis and return a non-suspicious result.

### Requirement 5: Risk Score Aggregation

**User Story:** As an interviewer, I want suspicious behaviors to be aggregated into a unified risk score with temporal smoothing, so that I see a stable and meaningful assessment rather than noisy individual signals.

#### Acceptance Criteria

1. WHEN a new signal score is received, THE CheatMonitor SHALL apply exponential moving average (EMA) smoothing per signal using smoothing factor α = 0.3, where smoothed_score = α × new_score + (1 − α) × previous_smoothed_score, before including that signal in the aggregation calculation.
2. THE aggregated risk score SHALL always remain in the range [0, 100] regardless of the combination of input signals, with individual input signal scores also constrained to the range [0, 100].
3. WHEN multiple signals are active simultaneously within the 30-second signal window, THE CheatMonitor SHALL apply a multi-signal boost of 10% per additional active signal beyond the first, where a signal is considered "active" if its smoothed score is greater than 0 and it was last updated within the preceding 30 seconds.
4. THE CheatMonitor SHALL calculate the aggregated score as min(100, (max_score × 0.6 + avg_score × 0.4) × boost) where boost = 1 + (active_signal_count - 1) × 0.1, and max_score and avg_score are derived from the EMA-smoothed scores of all active signals.
5. IF a signal has not been updated for more than 30 seconds, THEN THE CheatMonitor SHALL exclude that signal from the aggregation calculation.
6. IF no signals are active (all signals have expired or no signals have been received), THEN THE CheatMonitor SHALL report an aggregated risk score of 0.
7. THE CheatMonitor SHALL cache the running risk score and signal history in Redis, updating the cache after each aggregation cycle.
8. WHEN a constant signal value is applied repeatedly, THE EMA-smoothed output SHALL converge to within 2 units of that constant value after no more than 10 consecutive applications of the same value.

### Requirement 6: Verdict Determination

**User Story:** As an interviewer, I want risk scores to be classified into clear severity levels, so that I can quickly understand the urgency of a detection.

#### Acceptance Criteria

1. THE CheatMonitor SHALL classify risk scores into verdicts using the following thresholds: [0, 30) → SAFE, [30, 50) → MILD, [50, 80) → HIGH, [80, 100] → CRITICAL.
2. THE verdict function SHALL be deterministic and monotonically non-decreasing: for any two scores s1 < s2, verdict(s1) ≤ verdict(s2) in severity ordering, and the same score SHALL always produce the same verdict regardless of prior state.
3. WHEN the verdict is HIGH or CRITICAL, THE CheatMonitor SHALL set should_alert to true in the CheatDetectionResult.
4. WHEN the verdict is SAFE or MILD, THE CheatMonitor SHALL set should_alert to false in the CheatDetectionResult.
5. IF the input risk score is less than 0 or greater than 100, THEN THE CheatMonitor SHALL clamp the value to the nearest bound (0 or 100) before applying verdict classification.

### Requirement 7: Alert Generation and Dispatch

**User Story:** As an interviewer, I want to receive real-time alerts about suspicious candidate behavior via the interview interface, so that I can make informed decisions during the interview.

#### Acceptance Criteria

1. WHEN a detection result has should_alert set to true, THE CheatMonitor SHALL persist a CheatAlert record to PostgreSQL with alert_type, severity, score, confidence, details, and timestamp before initiating dispatch.
2. WHEN an alert is persisted, THE AlertDispatcher SHALL send the alert payload to all connected interviewers via the LiveKit data channel for the session room within 2 seconds of persistence.
3. THE alert payload SHALL include alert_id, alert_type, severity, score, confidence, details, timestamp, and session_id.
4. WHILE monitoring is active, THE AlertDispatcher SHALL send risk score updates to interviewers every 10 seconds, including session_id, current_score, current_verdict, total_alerts, and top active signals.
5. WHEN the AlertDispatcher sends an alert, the alert SHALL only be delivered to participants in the specific session room, preventing cross-session alert leakage.
6. IF the LiveKit data channel is unavailable, THEN THE AlertDispatcher SHALL log the failure and not retry delivery, leaving the alert accessible only via the REST endpoint.
7. WHEN monitoring transitions to inactive, THE AlertDispatcher SHALL stop sending periodic risk score updates for that session within the next update cycle.

### Requirement 8: REST API for Cheat Data

**User Story:** As an interviewer, I want REST API endpoints to query cheat alerts and risk summaries, so that I can review detection history and current status even if I missed a real-time alert.

#### Acceptance Criteria

1. WHEN an interviewer requests the cheat summary for a session, THE InterviewCheatEventRouter SHALL return the current risk score, verdict, total alerts, alerts by severity, alerts by type, monitoring duration in seconds, and the top 3 active signals with their scores.
2. WHEN an interviewer requests the alert history for a session, THE InterviewCheatEventRouter SHALL return a paginated list of CheatAlert records ordered by creation time descending (most recent first), with a default page size of 50 and a maximum page size of 100.
3. THE InterviewCheatEventRouter SHALL authenticate all requests via JWT and authorize only interviewers and admins to access cheat data.
4. IF the browser event endpoint receives more than 10 events per second for a single session, THEN THE InterviewCheatEventRouter SHALL reject excess events with an HTTP 429 response and discard the rejected events without affecting the risk score.
5. IF an interviewer requests cheat summary or alert history for a session that has no monitoring state, THEN THE InterviewCheatEventRouter SHALL return a response with a risk score of 0, verdict SAFE, zero alerts, and an empty alert list.

### Requirement 9: No Auto-Fail Policy

**User Story:** As a candidate, I want assurance that the system will never automatically terminate my interview or penalize me without human review, so that I am treated fairly.

#### Acceptance Criteria

1. THE CheatMonitor SHALL never automatically end an interview session, close the LiveKit room, or revoke the candidate's session access regardless of the risk score or verdict.
2. THE CheatMonitor SHALL never automatically remove, kick, or mute the candidate in the interview room regardless of alert severity or number of alerts generated.
3. THE CheatMonitor SHALL limit its automated actions exclusively to: generating CheatAlert records with "flag_for_review" status, updating the risk score in Redis, and notifying the interviewer via the LiveKit data channel.
4. WHEN a CRITICAL verdict is reached, THE CheatMonitor SHALL notify the interviewer via the LiveKit data channel but SHALL NOT terminate the session, remove the candidate, disable the candidate's audio or video tracks, lock the candidate's coding interface, or alter the candidate's ability to participate.
5. THE CheatMonitor SHALL NOT send any alert content, risk score, or verdict information to the candidate's client during the interview session.

### Requirement 10: Error Handling and Resilience

**User Story:** As a system operator, I want the cheat detection system to handle failures gracefully without disrupting the interview, so that technical issues do not affect the candidate experience.

#### Acceptance Criteria

1. IF proctoring-svc does not respond within 3 seconds or returns an HTTP 5xx error, THEN THE CheatMonitor SHALL skip the current detection cycle, log the failure, and continue monitoring on the next cycle.
2. IF proctoring-svc fails for 5 consecutive cycles, THEN THE CheatMonitor SHALL emit a "monitoring_degraded" status to interviewers via data channel and SHALL NOT re-emit the status until it has been cleared by a recovery.
3. WHEN proctoring-svc returns a successful response after a "monitoring_degraded" status has been emitted, THE CheatMonitor SHALL reset the consecutive failure counter to zero and emit a "monitoring_restored" status to interviewers via data channel.
4. IF Redis is unavailable (connection refused or timeout exceeding 1 second), THEN THE CheatMonitor SHALL fall back to in-memory score tracking for the current session and resume writing to Redis once connectivity is restored.
5. IF the candidate's video track is unpublished, THEN THE CheatMonitor SHALL skip frame analysis and generate a single NO_FACE alert after 10 seconds of continuous absence, without repeating the alert until the track is re-published and unpublished again.
6. IF frame data fails base64 decoding or is not a decodable JPEG image, THEN THE CheatMonitor SHALL log the error, skip the frame, and continue with the next capture cycle.
7. IF the LiveKit data channel send operation throws an exception or does not complete within 2 seconds, THEN THE AlertDispatcher SHALL log the failure without losing the alert (already persisted to PostgreSQL).

### Requirement 11: Data Validation

**User Story:** As a developer, I want all cheat detection data to be validated against defined constraints, so that the system maintains data integrity.

#### Acceptance Criteria

1. THE CheatAlert record SHALL validate that alert_type is a member of the AlertType enumeration.
2. THE CheatAlert record SHALL validate that severity is one of: MILD, HIGH, CRITICAL.
3. THE CheatAlert record SHALL validate that score is a numeric value in the range [0.0, 100.0] inclusive.
4. THE CheatAlert record SHALL validate that confidence is a numeric value in the range [0.0, 1.0] inclusive.
5. THE CheatDetectionResult SHALL validate that verdict is one of: SAFE, MILD, HIGH, CRITICAL.
6. THE CheatDetectionResult SHALL validate that score is a numeric value in the range [0.0, 100.0] inclusive and that confidence is a numeric value in the range [0.0, 1.0] inclusive.
7. THE MonitoringState SHALL validate that current_risk_score is a numeric value in the range [0.0, 100.0] inclusive and that status is one of: inactive, active, paused.
8. IF a record fails any validation constraint, THEN THE system SHALL reject the record and return an error message indicating which field failed validation and the constraint that was violated.
9. THE CheatAlert record SHALL validate that session_id, alert_type, severity, score, confidence, and created_at are present and non-null before persisting.

### Requirement 12: Browser Event Idempotency

**User Story:** As a developer, I want duplicate browser events to be handled safely, so that network retries do not corrupt the risk score.

#### Acceptance Criteria

1. WHEN a browser event with identical session_id, event_type, and timestamp is processed multiple times, THE CheatMonitor SHALL produce the same score, verdict, and should_alert value in the CheatDetectionResult each time.
2. WHEN duplicate events are received, THE CheatMonitor SHALL not double-count them in the risk score aggregation.
3. THE CheatMonitor SHALL identify duplicate events using the composite key of (session_id, event_type, timestamp) and SHALL retain deduplication state for at least 30 seconds after the original event is received.
4. WHEN a duplicate event is detected, THE CheatMonitor SHALL return the CheatDetectionResult from the original processing of that event without re-executing the risk score aggregation.
5. IF two browser events share the same session_id, event_type, and timestamp but differ in their details field, THEN THE CheatMonitor SHALL treat them as duplicates and process only the first received instance.

### Requirement 13: Security and Authorization

**User Story:** As a system administrator, I want cheat detection endpoints to be properly secured, so that only authorized users can access or influence detection data.

#### Acceptance Criteria

1. THE InterviewCheatEventRouter SHALL require a valid JWT for all endpoints.
2. IF a request is made with a missing, malformed, or expired JWT, THEN THE InterviewCheatEventRouter SHALL return HTTP 401 Unauthorized and not process the request.
3. THE BrowserMonitor SHALL only report events for the candidate's own session, validated server-side by comparing the JWT subject claim to the session's assigned candidate identity.
4. WHEN a candidate attempts to access cheat scores, alerts, or risk summaries, THE InterviewCheatEventRouter SHALL return HTTP 403 Forbidden and not disclose any detection data.
5. THE AlertDispatcher SHALL not include personally identifiable information beyond session_id in data channel payloads.
6. THE CheatMonitor SHALL persist all alerts and monitoring state transitions (inactive, active, paused) with timestamps for audit trail purposes.
