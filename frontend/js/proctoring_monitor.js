/**
 * Advanced Proctoring - Frontend Monitors
 * Implements: Browser Security, Typing Patterns, Mouse Tracking, Network Monitoring
 */

class ProctoringMonitor {
    constructor(sessionId, apiEndpoint) {
        this.sessionId = sessionId;
        this.apiEndpoint = apiEndpoint;

        // State
        this.typingIntervals = [];
        this.mouseEvents = [];
        this.lastKeyTime = Date.now();
        this.lastMouseTime = Date.now();
        this.networkBaseline = null;

        // Initialize all monitors
        this.initBrowserSecurity();
        this.initTypingMonitor();
        this.initMouseMonitor();
        this.initNetworkMonitor();
        this.initSystemChecks();
    }

    // ==========================================
    // 1. Browser Security Monitoring
    // ==========================================
    initBrowserSecurity() {
        // Window Blur (Lost Focus)
        window.addEventListener('blur', () => {
            this.reportViolation('WINDOW_BLUR', {
                timestamp: Date.now(),
                duration: 0
            });
        });

        // Fullscreen Exit
        document.addEventListener('fullscreenchange', () => {
            if (!document.fullscreenElement) {
                this.reportViolation('FULLSCREEN_EXIT', {
                    timestamp: Date.now()
                });
            }
        });

        // Right Click Block
        document.addEventListener('contextmenu', (e) => {
            e.preventDefault();
            this.reportViolation('RIGHT_CLICK', {
                timestamp: Date.now(),
                target: e.target.tagName
            });
        });

        // DevTools Detection
        setInterval(() => {
            const widthThreshold = 160;
            const heightThreshold = 160;
            const widthDiff = window.outerWidth - window.innerWidth;
            const heightDiff = window.outerHeight - window.innerHeight;

            if (widthDiff > widthThreshold || heightDiff > heightThreshold) {
                this.reportViolation('DEVTOOLS_OPEN', {
                    widthDiff,
                    heightDiff
                });
            }
        }, 2000);

        // Copy/Cut/Paste Detection
        document.addEventListener('copy', (e) => {
            this.reportViolation('COPY_ATTEMPT', {
                timestamp: Date.now(),
                selection: window.getSelection().toString().substring(0, 100)
            });
        });

        document.addEventListener('cut', (e) => {
            this.reportViolation('CUT_ATTEMPT', {
                timestamp: Date.now()
            });
        });

        document.addEventListener('paste', (e) => {
            const pastedText = (e.clipboardData || window.clipboardData).getData('text');
            this.reportViolation('PASTE_ATTEMPT', {
                timestamp: Date.now(),
                length: pastedText.length,
                preview: pastedText.substring(0, 50)
            });
        });

        // Tab Visibility
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.reportViolation('TAB_HIDDEN', {
                    timestamp: Date.now()
                });
            }
        });

        // Console Access Detection
        const devtools = /./;
        devtools.toString = function () {
            this.opened = true;
            this.reportViolation('CONSOLE_ACCESSED', {
                timestamp: Date.now()
            });
        };
        console.log('%c', devtools);
    }

    // ==========================================
    // 2. Typing Pattern Monitor
    // ==========================================
    initTypingMonitor() {
        document.addEventListener('keydown', (e) => {
            const now = Date.now();
            const interval = now - this.lastKeyTime;

            this.typingIntervals.push(interval);

            // Keep last 100 intervals
            if (this.typingIntervals.length > 100) {
                this.typingIntervals.shift();
            }

            // Analyze pattern every 50 keystrokes
            if (this.typingIntervals.length >= 50 && this.typingIntervals.length % 10 === 0) {
                this.analyzeTypingPattern();
            }

            this.lastKeyTime = now;
        });
    }

    analyzeTypingPattern() {
        if (this.typingIntervals.length < 10) return;

        const avg = this.typingIntervals.reduce((a, b) => a + b, 0) / this.typingIntervals.length;
        const variance = this.calculateVariance(this.typingIntervals);
        const std = Math.sqrt(variance);

        // Detect anomalies
        if (avg < 20 && std < 10) {
            // Likely paste
            this.reportViolation('TYPING_PASTE_DETECTED', {
                avg_interval: avg,
                std_deviation: std,
                confidence: 0.95
            });
        } else if (avg > 500) {
            // Very slow typing (looking at notes?)
            this.reportViolation('TYPING_SLOW', {
                avg_interval: avg,
                std_deviation: std,
                confidence: 0.7,
                reason: 'Possibly looking at notes'
            });
        }

        // Send pattern to backend for analysis
        this.sendTypingPattern(this.typingIntervals.slice(-50));
    }

    calculateVariance(arr) {
        const mean = arr.reduce((a, b) => a + b, 0) / arr.length;
        return arr.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / arr.length;
    }

    sendTypingPattern(intervals) {
        fetch(`${this.apiEndpoint}/analyze_typing`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: this.sessionId,
                intervals: intervals
            })
        });
    }

    // ==========================================
    // 3. Mouse Activity Monitor
    // ==========================================
    initMouseMonitor() {
        let inactivityTimer = null;

        document.addEventListener('mousemove', (e) => {
            const now = Date.now();

            this.mouseEvents.push({
                x: e.clientX,
                y: e.clientY,
                timestamp: now
            });

            // Keep last 100 events
            if (this.mouseEvents.length > 100) {
                this.mouseEvents.shift();
            }

            // Reset inactivity timer
            clearTimeout(inactivityTimer);
            inactivityTimer = setTimeout(() => {
                this.reportViolation('MOUSE_INACTIVE', {
                    duration: 30000,  // 30 seconds
                    last_position: { x: e.clientX, y: e.clientY }
                });
            }, 30000);

            this.lastMouseTime = now;
        });

        // Analyze mouse pattern every 10 seconds
        setInterval(() => {
            if (this.mouseEvents.length > 10) {
                this.analyzeMousePattern();
            }
        }, 10000);
    }

    analyzeMousePattern() {
        if (this.mouseEvents.length < 5) return;

        // Calculate average speed
        let totalDistance = 0;
        for (let i = 1; i < this.mouseEvents.length; i++) {
            const dx = this.mouseEvents[i].x - this.mouseEvents[i - 1].x;
            const dy = this.mouseEvents[i].y - this.mouseEvents[i - 1].y;
            totalDistance += Math.sqrt(dx * dx + dy * dy);
        }

        const avgSpeed = totalDistance / this.mouseEvents.length;

        // Very slow movement
        if (avgSpeed < 5) {
            this.reportViolation('MOUSE_SLOW', {
                avg_speed: avgSpeed,
                confidence: 0.4,
                reason: 'Possibly distracted'
            });
        }
    }

    // ==========================================
    // 4. Network Monitor
    // ==========================================
    initNetworkMonitor() {
        // Monitor network requests
        const originalFetch = window.fetch;
        window.fetch = (...args) => {
            const url = args[0];

            // Check for suspicious external requests
            if (typeof url === 'string' && !url.includes(window.location.hostname)) {
                this.reportViolation('EXTERNAL_REQUEST', {
                    url: url,
                    timestamp: Date.now()
                });
            }

            return originalFetch.apply(this, args);
        };

        // Monitor WebSocket connections
        const originalWebSocket = window.WebSocket;
        window.WebSocket = function (...args) {
            const ws = new originalWebSocket(...args);
            this.reportViolation('WEBSOCKET_CONNECTION', {
                url: args[0],
                timestamp: Date.now()
            });
            return ws;
        };
    }

    // ==========================================
    // 5. System Checks
    // ==========================================
    initSystemChecks() {
        // Check for multiple monitors
        if (window.screen.availWidth > window.innerWidth * 1.5) {
            this.reportViolation('MULTIPLE_MONITORS_SUSPECTED', {
                screen_width: window.screen.availWidth,
                window_width: window.innerWidth
            });
        }

        // Check for virtual machine (heuristic)
        const isVM = /VirtualBox|VMware|QEMU|Parallels/i.test(navigator.userAgent);
        if (isVM) {
            this.reportViolation('VIRTUAL_MACHINE_DETECTED', {
                user_agent: navigator.userAgent
            });
        }

        // Check for screen recording (experimental)
        if (navigator.mediaDevices && navigator.mediaDevices.getDisplayMedia) {
            navigator.mediaDevices.getDisplayMedia({ video: true })
                .then(() => {
                    this.reportViolation('SCREEN_RECORDING_ACTIVE', {
                        timestamp: Date.now()
                    });
                })
                .catch(() => {
                    // Normal - no screen recording
                });
        }

        // Browser extension detection (Chrome only)
        if (window.chrome && chrome.runtime) {
            try {
                chrome.management.getAll((extensions) => {
                    const suspicious = extensions.filter(ext =>
                        ext.name.toLowerCase().includes('screenshot') ||
                        ext.name.toLowerCase().includes('translator') ||
                        ext.name.toLowerCase().includes('chatgpt') ||
                        ext.name.toLowerCase().includes('copilot')
                    );

                    if (suspicious.length > 0) {
                        this.reportViolation('SUSPICIOUS_EXTENSIONS', {
                            extensions: suspicious.map(e => ({ name: e.name, id: e.id }))
                        });
                    }
                });
            } catch (e) {
                // Permission denied - that's fine
            }
        }
    }

    // ==========================================
    // Violation Reporting
    // ==========================================
    reportViolation(type, data) {
        const violation = {
            session_id: this.sessionId,
            type: type,
            data: data,
            timestamp: Date.now(),
            url: window.location.href
        };

        // Send to backend
        fetch(`${this.apiEndpoint}/report_violation`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(violation)
        }).catch(err => {
            console.error('Failed to report violation:', err);
        });

        // Log locally (for debugging)
        console.warn(`[PROCTORING] ${type}:`, data);
    }
}

// ==========================================
// Initialize on Page Load
// ==========================================
document.addEventListener('DOMContentLoaded', () => {
    // Get session ID from URL or cookie
    const urlParams = new URLSearchParams(window.location.search);
    const sessionId = urlParams.get('session_id') || 'default_session';
    const apiEndpoint = '/api/proctoring';  // Adjust to your API

    // Initialize monitor
    window.proctoringMonitor = new ProctoringMonitor(sessionId, apiEndpoint);

    console.log('[PROCTORING] Advanced monitoring initialized');
});

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ProctoringMonitor;
}
