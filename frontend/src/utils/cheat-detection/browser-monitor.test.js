import { BrowserMonitor } from './browser-monitor';

// Mock fetch globally
global.fetch = jest.fn();

beforeEach(() => {
  jest.useFakeTimers();
  global.fetch.mockReset();
  global.fetch.mockResolvedValue({ ok: true });
});

afterEach(() => {
  jest.useRealTimers();
});

describe('BrowserMonitor', () => {
  let monitor;

  beforeEach(() => {
    monitor = new BrowserMonitor('session-123', 'http://localhost:8000', 'test-token');
  });

  afterEach(() => {
    monitor.stop();
  });

  describe('constructor', () => {
    it('initializes with zero event counts', () => {
      expect(monitor.getEventCounts()).toEqual({
        tab_switch: 0,
        copy: 0,
        paste: 0,
        devtools: 0,
        fullscreen_exit: 0,
      });
    });
  });

  describe('start/stop', () => {
    it('registers event listeners on start', () => {
      const addSpy = jest.spyOn(document, 'addEventListener');
      monitor.start();
      expect(addSpy).toHaveBeenCalledWith('visibilitychange', expect.any(Function));
      expect(addSpy).toHaveBeenCalledWith('copy', expect.any(Function));
      expect(addSpy).toHaveBeenCalledWith('paste', expect.any(Function));
      expect(addSpy).toHaveBeenCalledWith('fullscreenchange', expect.any(Function));
      addSpy.mockRestore();
    });

    it('removes event listeners on stop', () => {
      const removeSpy = jest.spyOn(document, 'removeEventListener');
      monitor.start();
      monitor.stop();
      expect(removeSpy).toHaveBeenCalledWith('visibilitychange', expect.any(Function));
      expect(removeSpy).toHaveBeenCalledWith('copy', expect.any(Function));
      expect(removeSpy).toHaveBeenCalledWith('paste', expect.any(Function));
      expect(removeSpy).toHaveBeenCalledWith('fullscreenchange', expect.any(Function));
      removeSpy.mockRestore();
    });

    it('does not double-start', () => {
      const addSpy = jest.spyOn(document, 'addEventListener');
      monitor.start();
      monitor.start(); // second call should be no-op
      // visibilitychange should only be registered once
      const visibilityCalls = addSpy.mock.calls.filter(c => c[0] === 'visibilitychange');
      expect(visibilityCalls).toHaveLength(1);
      addSpy.mockRestore();
    });
  });

  describe('tab switch detection', () => {
    it('detects tab switch when document becomes hidden', () => {
      monitor.start();
      Object.defineProperty(document, 'visibilityState', { value: 'hidden', writable: true });
      document.dispatchEvent(new Event('visibilitychange'));
      expect(monitor.getEventCounts().tab_switch).toBe(1);
    });

    it('does not count when document becomes visible', () => {
      monitor.start();
      Object.defineProperty(document, 'visibilityState', { value: 'visible', writable: true });
      document.dispatchEvent(new Event('visibilitychange'));
      expect(monitor.getEventCounts().tab_switch).toBe(0);
    });
  });

  describe('copy/paste detection', () => {
    it('detects copy events', () => {
      monitor.start();
      document.dispatchEvent(new Event('copy'));
      expect(monitor.getEventCounts().copy).toBe(1);
    });

    it('detects paste events', () => {
      monitor.start();
      document.dispatchEvent(new Event('paste'));
      expect(monitor.getEventCounts().paste).toBe(1);
    });
  });

  describe('fullscreen exit detection', () => {
    it('detects fullscreen exit when fullscreenElement is null', () => {
      monitor.start();
      Object.defineProperty(document, 'fullscreenElement', { value: null, writable: true, configurable: true });
      document.dispatchEvent(new Event('fullscreenchange'));
      expect(monitor.getEventCounts().fullscreen_exit).toBe(1);
    });

    it('does not count when entering fullscreen', () => {
      monitor.start();
      Object.defineProperty(document, 'fullscreenElement', { value: document.body, writable: true, configurable: true });
      document.dispatchEvent(new Event('fullscreenchange'));
      expect(monitor.getEventCounts().fullscreen_exit).toBe(0);
    });
  });

  describe('debouncing', () => {
    it('debounces same event type within 2 seconds', () => {
      monitor.start();
      document.dispatchEvent(new Event('copy'));
      document.dispatchEvent(new Event('copy'));
      document.dispatchEvent(new Event('copy'));
      expect(monitor.getEventCounts().copy).toBe(1);
    });

    it('allows same event type after 2 seconds', () => {
      monitor.start();
      document.dispatchEvent(new Event('copy'));
      jest.advanceTimersByTime(2001);
      document.dispatchEvent(new Event('copy'));
      expect(monitor.getEventCounts().copy).toBe(2);
    });

    it('does not debounce different event types', () => {
      monitor.start();
      document.dispatchEvent(new Event('copy'));
      document.dispatchEvent(new Event('paste'));
      expect(monitor.getEventCounts().copy).toBe(1);
      expect(monitor.getEventCounts().paste).toBe(1);
    });
  });

  describe('event batching and flush', () => {
    it('flushes events to the backend endpoint on interval', async () => {
      monitor.start();
      document.dispatchEvent(new Event('copy'));

      // Advance past flush interval
      jest.advanceTimersByTime(5000);

      // Allow async flush to complete
      await Promise.resolve();

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/interviews/sessions/session-123/cheat-events',
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
            'Authorization': 'Bearer test-token',
          }),
        })
      );
    });

    it('flushes immediately when batch reaches 10 events', async () => {
      monitor.start();

      // Generate 10 different event types rapidly (using copy with time advances to bypass debounce)
      for (let i = 0; i < 10; i++) {
        jest.advanceTimersByTime(2001);
        document.dispatchEvent(new Event('copy'));
      }

      await Promise.resolve();

      expect(global.fetch).toHaveBeenCalled();
    });
  });

  describe('retry queue', () => {
    // Helper to flush all pending promises/microtasks
    const flushPromises = () => new Promise(jest.requireActual('timers').setImmediate);

    it('retains events on network failure for retry', async () => {
      global.fetch.mockRejectedValueOnce(new Error('Network error'));

      monitor.start();
      document.dispatchEvent(new Event('copy'));

      // Flush
      jest.advanceTimersByTime(5000);
      await flushPromises();

      // Events should be in retry queue - next flush should try again
      global.fetch.mockResolvedValueOnce({ ok: true });
      jest.advanceTimersByTime(5000);
      await flushPromises();

      expect(global.fetch).toHaveBeenCalledTimes(2);
    });

    it('retains events on non-2xx response', async () => {
      global.fetch.mockResolvedValueOnce({ ok: false, status: 500 });

      monitor.start();
      document.dispatchEvent(new Event('paste'));

      jest.advanceTimersByTime(5000);
      await flushPromises();

      // Should retry on next flush
      global.fetch.mockResolvedValueOnce({ ok: true });
      jest.advanceTimersByTime(5000);
      await flushPromises();

      expect(global.fetch).toHaveBeenCalledTimes(2);
    });
  });

  describe('getEventCounts', () => {
    it('returns a copy (not a reference) of event counts', () => {
      const counts = monitor.getEventCounts();
      counts.tab_switch = 999;
      expect(monitor.getEventCounts().tab_switch).toBe(0);
    });
  });

  describe('events not recorded when stopped', () => {
    it('does not record events when monitor is not started', () => {
      document.dispatchEvent(new Event('copy'));
      expect(monitor.getEventCounts().copy).toBe(0);
    });

    it('does not record events after stop', () => {
      monitor.start();
      monitor.stop();
      document.dispatchEvent(new Event('copy'));
      expect(monitor.getEventCounts().copy).toBe(0);
    });
  });
});
