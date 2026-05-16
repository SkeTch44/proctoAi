/**
 * BrowserMonitor - Client-side browser event detection for interview cheat detection.
 *
 * Detects:
 * - Tab switches (visibilitychange)
 * - Copy/Paste (clipboard events)
 * - DevTools opening (timing-based detection)
 * - Fullscreen exit (fullscreenchange)
 *
 * Features:
 * - 2-second debounce per event type
 * - Event batching: flush every 5 seconds or at 10 events
 * - Retry queue (max 50 events) for network failures
 * - Auth token included in requests
 *
 * Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.9
 */

const DEBOUNCE_INTERVAL_MS = 2000;
const FLUSH_INTERVAL_MS = 5000;
const MAX_BATCH_SIZE = 10;
const MAX_RETRY_QUEUE_SIZE = 50;
const DEVTOOLS_CHECK_INTERVAL_MS = 1000;

export class BrowserMonitor {
  /**
   * @param {string} sessionId - The interview session ID
   * @param {string} apiBaseUrl - Base URL for the interview-svc API
   * @param {string} authToken - JWT auth token for authenticated requests
   */
  constructor(sessionId, apiBaseUrl, authToken) {
    this._sessionId = sessionId;
    this._apiBaseUrl = apiBaseUrl;
    this._authToken = authToken;

    // Event counts
    this._eventCounts = {
      tab_switch: 0,
      copy: 0,
      paste: 0,
      devtools: 0,
      fullscreen_exit: 0,
    };

    // Debounce tracking: event_type -> last timestamp
    this._lastEventTime = {};

    // Event queue for batching
    this._eventQueue = [];

    // Retry queue for failed deliveries
    this._retryQueue = [];

    // Interval/timer references
    this._flushIntervalId = null;
    this._devtoolsIntervalId = null;

    // Bound event handlers (for cleanup)
    this._handleVisibilityChange = this._onVisibilityChange.bind(this);
    this._handleCopy = this._onCopy.bind(this);
    this._handlePaste = this._onPaste.bind(this);
    this._handleFullscreenChange = this._onFullscreenChange.bind(this);

    // DevTools detection state
    this._devtoolsOpen = false;

    // Running state
    this._running = false;
  }

  /**
   * Start monitoring browser events.
   */
  start() {
    if (this._running) return;
    this._running = true;

    // Register event listeners
    document.addEventListener('visibilitychange', this._handleVisibilityChange);
    document.addEventListener('copy', this._handleCopy);
    document.addEventListener('paste', this._handlePaste);
    document.addEventListener('fullscreenchange', this._handleFullscreenChange);

    // Start periodic flush
    this._flushIntervalId = setInterval(() => {
      this._flushEvents();
    }, FLUSH_INTERVAL_MS);

    // Start DevTools detection
    this._devtoolsIntervalId = setInterval(() => {
      this._checkDevTools();
    }, DEVTOOLS_CHECK_INTERVAL_MS);
  }

  /**
   * Stop monitoring and clean up all listeners and timers.
   */
  stop() {
    if (!this._running) return;
    this._running = false;

    // Remove event listeners
    document.removeEventListener('visibilitychange', this._handleVisibilityChange);
    document.removeEventListener('copy', this._handleCopy);
    document.removeEventListener('paste', this._handlePaste);
    document.removeEventListener('fullscreenchange', this._handleFullscreenChange);

    // Clear intervals
    if (this._flushIntervalId) {
      clearInterval(this._flushIntervalId);
      this._flushIntervalId = null;
    }
    if (this._devtoolsIntervalId) {
      clearInterval(this._devtoolsIntervalId);
      this._devtoolsIntervalId = null;
    }

    // Final flush of remaining events
    this._flushEvents();
  }

  /**
   * Returns current event counts by type.
   * @returns {{ tab_switch: number, copy: number, paste: number, devtools: number, fullscreen_exit: number }}
   */
  getEventCounts() {
    return { ...this._eventCounts };
  }

  // ─── Private: Event Handlers ───────────────────────────────────────────

  _onVisibilityChange() {
    if (document.visibilityState === 'hidden') {
      this._recordEvent('TAB_SWITCH', 'tab_switch', { state: 'hidden' });
    }
  }

  _onCopy(event) {
    this._recordEvent('COPY_DETECTED', 'copy', { target: event.target?.tagName || 'unknown' });
  }

  _onPaste(event) {
    this._recordEvent('PASTE_DETECTED', 'paste', { target: event.target?.tagName || 'unknown' });
  }

  _onFullscreenChange() {
    // Only report when exiting fullscreen (fullscreenElement becomes null)
    if (!document.fullscreenElement) {
      this._recordEvent('FULLSCREEN_EXIT', 'fullscreen_exit', {});
    }
  }

  /**
   * DevTools detection using timing-based heuristic.
   * A debugger statement takes significantly longer when DevTools is open.
   */
  _checkDevTools() {
    const threshold = 100; // ms - debugger pauses when DevTools is open
    const start = performance.now();

    // The debugger statement causes a pause when DevTools is open
    // eslint-disable-next-line no-debugger
    debugger;

    const elapsed = performance.now() - start;

    if (elapsed > threshold) {
      if (!this._devtoolsOpen) {
        this._devtoolsOpen = true;
        this._recordEvent('DEVTOOLS_OPEN', 'devtools', { detection_method: 'timing', elapsed_ms: elapsed });
      }
    } else {
      this._devtoolsOpen = false;
    }
  }

  // ─── Private: Event Recording & Debouncing ─────────────────────────────

  /**
   * Record an event with debounce logic.
   * @param {string} eventType - AlertType enum value for the backend
   * @param {string} countKey - Key in _eventCounts
   * @param {object} details - Additional event details
   */
  _recordEvent(eventType, countKey, details) {
    if (!this._running) return;

    const now = Date.now();

    // Debounce: skip if same event type occurred within 2 seconds
    if (this._lastEventTime[eventType] && (now - this._lastEventTime[eventType]) < DEBOUNCE_INTERVAL_MS) {
      return;
    }

    this._lastEventTime[eventType] = now;
    this._eventCounts[countKey]++;

    const event = {
      session_id: this._sessionId,
      event_type: eventType,
      timestamp: new Date(now).toISOString(),
      details,
    };

    this._eventQueue.push(event);

    // Flush immediately if batch size reached
    if (this._eventQueue.length >= MAX_BATCH_SIZE) {
      this._flushEvents();
    }
  }

  // ─── Private: Batching & Network ───────────────────────────────────────

  /**
   * Flush queued events to the backend endpoint.
   * On failure, events are moved to the retry queue (max 50).
   */
  async _flushEvents() {
    // Combine retry queue with current queue
    const eventsToSend = [...this._retryQueue, ...this._eventQueue];
    this._eventQueue = [];
    this._retryQueue = [];

    if (eventsToSend.length === 0) return;

    const url = `${this._apiBaseUrl}/api/v1/interviews/sessions/${this._sessionId}/cheat-events`;

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this._authToken}`,
        },
        body: JSON.stringify({ events: eventsToSend }),
      });

      if (!response.ok) {
        // Non-2xx response - retain events for retry
        this._enqueueForRetry(eventsToSend);
      }
    } catch (error) {
      // Network error - retain events for retry
      this._enqueueForRetry(eventsToSend);
    }
  }

  /**
   * Add failed events back to the retry queue, respecting the max size.
   * @param {Array} events - Events that failed to send
   */
  _enqueueForRetry(events) {
    // Add events to retry queue, capping at MAX_RETRY_QUEUE_SIZE
    const available = MAX_RETRY_QUEUE_SIZE - this._retryQueue.length;
    if (available > 0) {
      this._retryQueue.push(...events.slice(0, available));
    }
  }
}
