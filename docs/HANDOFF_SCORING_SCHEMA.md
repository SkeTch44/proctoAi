# Handoff Document: Suspicion Scoring Schema

## From: Agent 2 - Anti-Cheating Intelligence Engineer

---

## To: Agent 5 - Dashboard Engineer
**Dependency Type:** Input  
**Required Artifact:** Scoring schema and alert data structure  
**Purpose:** Display real-time suspicion scores and alerts on the admin dashboard

### Suspicion Score Schema

#### Score Calculation
The suspicion score is calculated using a weighted formula:

```python
score = (
    (gaze_score * 0.15) +          # 15% weight
    (face_absence_score * 0.35) +  # 35% weight (High Priority)
    (multiple_faces_score * 0.30) +# 30% weight (High Priority)
    (emotion_score * 0.05) +       # 5% weight
    (mic_score * 0.05) +           # 5% weight
    (tab_switch_score * 0.10)      # 10% weight
) # Result: 0-100
```

#### Severity Thresholds
| Severity | Score Range | Color Recommendation |
|----------|-------------|---------------------|
| LOW      | 1 - 30      | Green (#10B981)     |
| MEDIUM   | 31 - 70     | Yellow (#F59E0B)    |
| HIGH     | 71 - 100    | Red (#EF4444)       |

#### Alert Types
- `GAZE_DEVIATION` - Student looking away from screen
- `FACE_ABSENCE` - No face detected in frame
- `MULTIPLE_FACES` - More than one person detected
- `EMOTION_ANOMALY` - Suspicious emotional state (fear, anger)
- `NONE` - No anomaly detected

### JSON Data Structure

#### Real-time Analysis Result
```json
{
  "suspicious": true,
  "suspicion_score": 75.5,
  "severity": "HIGH",
  "alert_type": "MULTIPLE_FACES",
  "confidence": 0.76,
  "details": {
    "gaze_deviation": 10.0,
    "face_absence": 0.0,
    "multiple_faces": 100.0,
    "emotion_anomaly": 5.0
  }
}
```

#### Suspicion Log Entry (from `suspicion_log.json`)
```json
{
  "timestamp": "2026-01-17T10:05:32.123456",
  "session_id": "session_12345",
  "alert_type": "MULTIPLE_FACES",
  "severity": "HIGH",
  "score_impact": 75.5,
  "details": {
    "gaze_deviation": 10.0,
    "face_absence": 0.0,
    "multiple_faces": 100.0,
    "emotion_anomaly": 5.0
  }
}
```

### Dashboard Integration Points

1. **Real-time Score Display**
   - Subscribe to WebSocket event: `proctoring_alert`
   - Display `suspicion_score` with color-coded severity
   - Show breakdown of individual component scores in `details`

2. **Alert History**
   - Read from `suspicion_log.json` for historical data
   - Filter by `session_id`, `severity`, or `alert_type`
   - Display timeline of alerts with timestamps

3. **Session Summary**
   - Aggregate scores per session from database `sessions.suspicion_score`
   - Show trend graph of suspicion over time
   - Highlight peak alert moments

### API Endpoints to Use

- `GET /api/admin/dashboard` - Get active sessions with suspicion scores
- WebSocket: `proctoring_alert` event - Real-time alerts
- Database: `proctoring_events` table - Historical event data
- File: `suspicion_log.json` - Detailed alert logs

---

## To: Agent 3 - WebSocket/Real-time Communication Engineer
**Dependency Type:** Integration  
**Required Artifact:** Alert schema for WebSocket emission  
**Purpose:** Emit real-time suspicion alerts to admin dashboard

### WebSocket Event Schema

#### Event Name
`proctoring_alert`

#### Event Payload
```json
{
  "session_id": "session_12345",
  "alert_type": "MULTIPLE_FACES",
  "severity": "HIGH",
  "confidence": 0.76,
  "suspicion_score": 75.5,
  "timestamp": "2026-01-17T10:05:32.123456",
  "details": {
    "gaze_deviation": 10.0,
    "face_absence": 0.0,
    "multiple_faces": 100.0,
    "emotion_anomaly": 5.0
  }
}
```

### Integration with CheatDetector

The `CheatDetector.analyze_frame()` method returns a result dictionary that should be emitted via WebSocket when `suspicious` is `True`.

#### Example Integration (in `app.py`)
```python
@socketio.on('proctoring_data')
def handle_proctoring_data(data):
    session_id = data.get('session_id')
    frame_data = data.get('frame_data')
    
    if session_id and frame_data:
        # Analyze frame
        result = cheat_detector.analyze_frame(frame_data, session_id)
        
        if result.get('suspicious'):
            # Emit to admins room
            socketio.emit('proctoring_alert', {
                'session_id': session_id,
                'alert_type': result.get('alert_type'),
                'severity': result.get('severity'),
                'confidence': result.get('confidence'),
                'suspicion_score': result.get('suspicion_score'),
                'timestamp': datetime.now().isoformat(),
                'details': result.get('details')
            }, room='admins')
```

### Alert Frequency Considerations

- **Debouncing**: Consider implementing alert cooldown to avoid spamming (e.g., max 1 alert per 5 seconds per session)
- **Severity Filtering**: Only emit MEDIUM and HIGH severity alerts to reduce noise
- **Batch Updates**: For LOW severity, consider batching and sending periodic summaries

### Room Management

- Admins should join room: `admins`
- Individual session monitoring: `session_{session_id}`
- Emit to appropriate room based on monitoring scope

---

## Implementation Status

✅ **Completed:**
- Weighted scoring formula implemented
- Threshold classification system
- JSON alert logging to `suspicion_log.json`
- Alert type determination logic
- Full test suite with 100% pass rate

📋 **File Locations:**
- Implementation: `backend/models/cheat_detector.py`
- Log file: `suspicion_log.json` (created at runtime)
- Tests: `test/test_scoring.py`

🔧 **Configuration:**
- Default log file: `suspicion_log.json`
- Customizable via `CheatDetector(config={'log_file': 'custom.json'})`

---

## Notes

- The scoring system is designed to reduce false positives by weighting high-priority anomalies (face absence, multiple faces) more heavily
- All scores are normalized to 0-100 scale for consistency
- The system gracefully handles missing dependencies (cv2, numpy, mediapipe, deepface) and logs warnings
- Alert logging is append-only to preserve audit trail
