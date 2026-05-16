# Requirements Document

## Introduction

The Interview Session feature extends proctoAi's platform to support multi-party video conferencing for technical interviews. It enables multiple interviewers to collaboratively evaluate a candidate in a single session with real-time video, audio, and presentation/screen sharing capabilities. The system uses LiveKit as the media server (SFU architecture) and introduces an `interview-svc` microservice for session orchestration, participant management, and signaling coordination.

## Glossary

- **Interview_Session**: A scheduled or active multi-party video conferencing room where interviewers evaluate a candidate
- **Session_Service**: The core service component responsible for interview session lifecycle management and participant coordination
- **LiveKit_Adapter**: The abstraction layer over the LiveKit Server SDK that manages rooms and generates access tokens
- **Presentation_Service**: The component responsible for file upload, conversion to slide images, and slide synchronization
- **Participant**: A user who has joined an interview session in one of the defined roles
- **ParticipantRole**: One of three roles a user can hold in a session: interviewer, interviewee, or observer
- **LiveKit_Room**: A virtual media room on the LiveKit SFU server corresponding to one interview session
- **VideoGrants**: The permission set embedded in a LiveKit access token controlling publish/subscribe capabilities
- **Slide_Sync**: The mechanism by which slide navigation changes are broadcast to all connected participants via data channels
- **SFU**: Selective Forwarding Unit — a media server architecture that receives and redistributes media streams without mixing

## Requirements

### Requirement 1: Session Creation

**User Story:** As an interviewer, I want to create an interview session, so that I can schedule and host a multi-party video interview with a candidate.

#### Acceptance Criteria

1. WHEN an authenticated user with interviewer or admin role submits a session creation request with a valid title and participant limit, THE Session_Service SHALL create a new Interview_Session with status "scheduled", a default max_participants of 6 if not specified, and persist it to the database
2. WHEN a session is created, THE LiveKit_Adapter SHALL create a corresponding LiveKit_Room with the room name pattern `interview_{session_id[:8]}`, the same max_participants value as the session, and an empty_timeout of 300 seconds
3. IF the title is empty or exceeds 500 characters, THEN THE Session_Service SHALL reject the request with a validation error indicating the title constraint that was violated
4. IF the max_participants value is outside the range of 2 to 10, THEN THE Session_Service SHALL reject the request with a validation error indicating the allowed range
5. WHEN a session is successfully created, THE Session_Service SHALL return the session_id, join_url, and room_name to the caller
6. IF the LiveKit server is unreachable during room creation, THEN THE Session_Service SHALL reject the request with a service unavailability error and SHALL NOT persist the session to the database

### Requirement 2: Session Joining

**User Story:** As a participant (interviewer, interviewee, or observer), I want to join an interview session, so that I can participate in the video conference.

#### Acceptance Criteria

1. WHEN an authenticated user requests to join a session that exists and has not ended, THE Session_Service SHALL create a participant record with status "connected", generate a LiveKit access token scoped to the session's room_name with grants based on the participant's role (can_publish=true and can_publish_data=true for interviewers and interviewees; can_publish=false and can_publish_data=false for observers; can_subscribe=true for all roles), and return the token, room_name, and current participant list
2. IF the session has reached its max_participants limit based on the count of participants with status "connected", THEN THE Session_Service SHALL reject the join request with a session full error
3. IF a user with role interviewee attempts to join a session that already has a participant with role interviewee and status "connected", THEN THE Session_Service SHALL reject the join request with a duplicate interviewee error
4. WHEN a user who previously left (status "disconnected") rejoins the same session, THE Session_Service SHALL reactivate the existing participant record by setting status to "connected", updating joined_at to the current timestamp, and clearing left_at, rather than creating a duplicate record
5. WHEN the first participant joins a session with status "scheduled", THE Session_Service SHALL transition the session status to "active" and record the started_at timestamp
6. IF the session status is "ended", THEN THE Session_Service SHALL reject the join request with a session ended error
7. IF the requested session_id does not exist, THEN THE Session_Service SHALL reject the join request with a session not found error

### Requirement 3: Token Generation and Permissions

**User Story:** As a system administrator, I want participant tokens to be scoped by role, so that observers cannot publish media and session isolation is maintained.

#### Acceptance Criteria

1. WHEN generating a token for a participant with role "interviewer", THE LiveKit_Adapter SHALL set can_publish to true, can_subscribe to true, and can_publish_data to true
2. WHEN generating a token for a participant with role "interviewee", THE LiveKit_Adapter SHALL set can_publish to true, can_subscribe to true, and can_publish_data to true
3. WHEN generating a token for a participant with role "observer", THE LiveKit_Adapter SHALL set can_publish to false, can_subscribe to true, and can_publish_data to false
4. THE LiveKit_Adapter SHALL scope every generated token to the specific room_name of the session and set the token's room grant exclusively to that room_name, so that the token cannot be used to join any other room
5. THE LiveKit_Adapter SHALL set the token identity to the string representation of the user_id
6. THE LiveKit_Adapter SHALL set the token expiration (TTL) to a maximum of 24 hours from the time of generation
7. IF the provided participant role is not one of "interviewer", "interviewee", or "observer", THEN THE LiveKit_Adapter SHALL reject the token generation request and return an error indicating an invalid role was provided
8. IF the LiveKit server is unreachable during token generation, THEN THE LiveKit_Adapter SHALL return an error indicating media server unavailability and preserve the session in its current state

### Requirement 4: Session Lifecycle Management

**User Story:** As an interviewer, I want to end an interview session, so that all participants are disconnected and resources are cleaned up.

#### Acceptance Criteria

1. WHEN an interviewer or admin ends a session, THE Session_Service SHALL transition the session status to "ended", record the ended_at timestamp, and remove all participants with status "connected" by setting their status to "disconnected" and recording their left_at timestamp
2. WHEN a session is ended, THE LiveKit_Adapter SHALL delete the corresponding LiveKit_Room within 5 seconds of the session status transitioning to "ended"
3. IF a status transition is attempted that violates the permitted order (scheduled → active → ended), THEN THE Session_Service SHALL reject the request with an error indicating the invalid transition and preserve the current session status unchanged
4. WHEN all participants with role "interviewer" disconnect from an active session, THE Session_Service SHALL start a 5-minute empty_timeout countdown and automatically end the session when the countdown expires, regardless of whether interviewee or observer participants remain connected
5. IF an interviewer rejoins within the 5-minute empty_timeout period, THEN THE Session_Service SHALL cancel the automatic session termination and the session SHALL remain in "active" status
6. IF the LiveKit_Adapter fails to delete the LiveKit_Room when a session is ended, THEN THE Session_Service SHALL log the failure, retain the session status as "ended", and retry the room deletion up to 3 times with 5-second intervals between attempts

### Requirement 5: Participant Management

**User Story:** As an interviewer, I want to see who is in the session and manage participants, so that I can maintain control of the interview.

#### Acceptance Criteria

1. WHEN the LiveKit server sends a `participant_disconnected` webhook event for a session participant, THE Session_Service SHALL update that participant's status to "disconnected" within 5 seconds of receiving the webhook
2. WHEN a participant leaves voluntarily, THE Session_Service SHALL update the participant status to "disconnected" and record the left_at timestamp
3. WHILE a session is active, THE Session_Service SHALL reject any join request that would cause the count of participants with status "connected" to exceed the session's max_participants value
4. IF a user attempts to join a session where a participant record with the same user_id and session_id already exists with status "connected", THEN THE Session_Service SHALL reject the request with a duplicate participant error
5. WHEN an authenticated user requests the participant list for a session they belong to, THE Session_Service SHALL return all participant records for that session including each participant's user_id, display_name, role, status, and joined_at timestamp
6. WHEN an interviewer or admin requests removal of a participant from an active session, THE Session_Service SHALL update the participant's status to "removed", record the left_at timestamp, and instruct the LiveKit_Adapter to remove that participant from the LiveKit_Room
7. IF a participant with status "removed" attempts to rejoin the session, THEN THE Session_Service SHALL reject the join request with a participant removed error

### Requirement 6: Presentation Upload and Conversion

**User Story:** As an interviewer or interviewee, I want to upload and share a presentation, so that all participants can view slides during the interview.

#### Acceptance Criteria

1. WHEN an interviewer or interviewee uploads a file with extension .ppt, .pptx, .pdf, or .key to an active session, THE Presentation_Service SHALL store the file in object storage and convert it to individual slide images within 120 seconds
2. IF the uploaded file exceeds 50MB, THEN THE Presentation_Service SHALL reject the upload with a file too large error and not store the file
3. IF the uploaded file has an extension other than .ppt, .pptx, .pdf, or .key, THEN THE Presentation_Service SHALL reject the upload with an invalid file type error
4. IF the upload targets a session that is not in "active" status, THEN THE Presentation_Service SHALL reject the upload with an invalid session error
5. IF the file conversion fails or exceeds 120 seconds, THEN THE Presentation_Service SHALL retain the original file in storage and return a conversion failure error to the uploader
6. WHEN a new presentation is uploaded to a session that already has an active presentation, THE Presentation_Service SHALL deactivate the previous presentation so that only one presentation remains active per session
7. WHEN a presentation is successfully converted, THE Presentation_Service SHALL notify all connected participants via a LiveKit data channel message containing the presentation_id and slide_count

### Requirement 7: Slide Navigation and Synchronization

**User Story:** As an interviewer, I want to navigate presentation slides and have all participants see the same slide, so that the presentation is synchronized across the session.

#### Acceptance Criteria

1. WHEN an interviewer or interviewee changes the current slide to a valid slide_index, THE Presentation_Service SHALL update the current_slide value to the requested slide_index and broadcast a slide_change message containing the presentation_id and new slide_index to all connected participants via LiveKit data channel within 500 milliseconds
2. IF the requested slide_index is outside the range of 0 to slide_count minus 1, THEN THE Presentation_Service SHALL reject the navigation request with an error indicating the index is out of bounds and SHALL NOT modify the current_slide value
3. THE Presentation_Service SHALL maintain the invariant that current_slide is always within the range 0 to slide_count minus 1 for any active presentation
4. WHEN two participants attempt to change slides concurrently, THE Presentation_Service SHALL apply last-write-wins ordering based on server-side receipt time and broadcast the final authoritative slide_index to all connected participants
5. IF a participant with the observer role attempts to change the current slide, THEN THE Presentation_Service SHALL reject the navigation request with a permission denied error
6. IF the presentation_id in a navigation request does not refer to an active presentation in the session, THEN THE Presentation_Service SHALL reject the request with an error indicating the presentation is not found or inactive

### Requirement 8: Screen Sharing

**User Story:** As a participant with publish permissions, I want to share my screen, so that I can present content directly from my desktop during the interview.

#### Acceptance Criteria

1. WHEN an interviewer or interviewee initiates screen sharing, THE Frontend SHALL publish a screen-share track to the LiveKit_Room, limited to 1 active screen-share track per participant at a time
2. WHILE a screen-share track is published, THE LiveKit_Room SHALL distribute the track to all subscribed participants
3. WHEN a participant with role "observer" attempts to publish a screen-share track, THE LiveKit_Room SHALL reject the publish request based on token grants
4. WHEN a participant stops screen sharing or disconnects, THE Frontend SHALL unpublish the screen-share track from the LiveKit_Room and the LiveKit_Room SHALL notify all subscribed participants that the track has been removed
5. IF a second participant attempts to publish a screen-share track while another screen-share track is already active in the session, THEN THE Frontend SHALL allow the publish and the LiveKit_Room SHALL distribute both tracks, limited to a maximum of 2 concurrent screen-share tracks per session

### Requirement 9: Error Handling and Resilience

**User Story:** As a system operator, I want the interview session system to handle failures gracefully, so that interviews are not disrupted by transient errors.

#### Acceptance Criteria

1. IF the LiveKit server does not respond within 5 seconds during room creation or token generation, THEN THE Session_Service SHALL return HTTP 503 with a retry_after value of 5 seconds and keep the session in its current state
2. IF presentation conversion fails, THEN THE Presentation_Service SHALL return HTTP 422 with a response body indicating the conversion failure reason, retain the original file in storage, and include an indication that the user may retry the upload or use screen sharing instead
3. WHEN a participant's WebRTC connection drops, THE Frontend SHALL display a "reconnecting" indicator in place of the participant's video tile and allow the participant to rejoin for up to 60 seconds before showing a "disconnected" state
4. IF all interviewers leave and the empty_timeout of 300 seconds expires, THEN THE Session_Service SHALL transition the session status to "ended" and delete the associated LiveKit_Room
5. IF an interviewer rejoins the session while the empty_timeout countdown is active, THEN THE Session_Service SHALL cancel the empty_timeout countdown and keep the session in "active" state

### Requirement 10: Security and Access Control

**User Story:** As a platform administrator, I want interview sessions to be secure and isolated, so that unauthorized users cannot access session media or data.

#### Acceptance Criteria

1. THE Session_Service SHALL validate the JWT token on every API request by verifying the signature, confirming the token type is "access", and checking that the token has not expired, before processing the request
2. IF JWT validation fails due to an invalid signature, expired token, or missing claims, THEN THE Session_Service SHALL reject the request with an HTTP 401 response and an error message indicating the authentication failure reason
3. THE LiveKit_Adapter SHALL generate tokens scoped to a single room by setting the token's room grant to exactly the session's room_name, with token identity equal to the participant's user ID, and grants determined by participant role (observers: can_publish=false, can_publish_data=false; interviewers and interviewees: can_publish=true, can_publish_data=true)
4. WHEN a file is uploaded, THE Presentation_Service SHALL validate that the file extension is one of .ppt, .pptx, .pdf, or .key, that the detected MIME type matches the declared extension, and that the file size does not exceed 50 MB
5. IF file upload validation fails due to a disallowed extension, MIME type mismatch, or file size exceeding 50 MB, THEN THE Presentation_Service SHALL reject the upload and return an error message indicating which validation check failed
6. THE Session_Service SHALL ensure each LiveKit_Room is isolated by assigning a unique room_name per session following the pattern "interview_{session_id[:8]}" and generating participant tokens that grant access to only that single room_name
7. WHILE recording is enabled for a session, THE Session_Service SHALL notify all currently connected participants that the session is being recorded, and SHALL notify any participant who joins after recording has started upon their successful connection
