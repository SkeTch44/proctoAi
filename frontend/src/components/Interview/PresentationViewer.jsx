import { useState, useEffect, useCallback } from "react";
import { useDataChannel } from "@livekit/components-react";

/**
 * PresentationViewer — Displays presentation slides and syncs navigation
 * across all participants via LiveKit data channels.
 *
 * Props:
 *   - slides: string[] — Array of slide image URLs
 *   - role: "interviewer" | "interviewee" | "observer"
 *   - initialSlide: number (default 0)
 *   - onSlideChange: (index: number) => void — optional callback when slide changes
 *
 * Listens for `slide_change` messages on the LiveKit data channel to keep
 * all participants in sync. Interviewers and interviewees can navigate;
 * observers can only view.
 */
export default function PresentationViewer({
  slides = [],
  role = "observer",
  initialSlide = 0,
  onSlideChange,
}) {
  const [currentSlide, setCurrentSlide] = useState(initialSlide);

  // Clamp initial slide to valid range
  useEffect(() => {
    if (slides.length > 0 && initialSlide >= 0 && initialSlide < slides.length) {
      setCurrentSlide(initialSlide);
    }
  }, [initialSlide, slides.length]);

  // Handle incoming data channel messages for slide synchronization
  const onDataReceived = useCallback(
    (payload) => {
      try {
        const decoder = new TextDecoder();
        const raw = payload.payload instanceof Uint8Array
          ? decoder.decode(payload.payload)
          : typeof payload.payload === "string"
          ? payload.payload
          : decoder.decode(new Uint8Array(payload.payload));

        const message = JSON.parse(raw);

        if (message.type === "slide_change" && typeof message.slide === "number") {
          const newIndex = message.slide;
          if (newIndex >= 0 && newIndex < slides.length) {
            setCurrentSlide(newIndex);
          }
        }
      } catch {
        // Ignore malformed messages
      }
    },
    [slides.length]
  );

  // useDataChannel hook — send and receive on the "presentation" topic
  const { send } = useDataChannel("presentation", onDataReceived);

  // Broadcast slide change to all participants
  const broadcastSlideChange = useCallback(
    (index) => {
      if (!send) return;
      const message = JSON.stringify({ type: "slide_change", slide: index });
      const encoder = new TextEncoder();
      send(encoder.encode(message), { reliable: true });
    },
    [send]
  );

  const canNavigate = role === "interviewer" || role === "interviewee";

  const goToSlide = useCallback(
    (index) => {
      if (!canNavigate) return;
      if (index < 0 || index >= slides.length) return;
      setCurrentSlide(index);
      broadcastSlideChange(index);
      onSlideChange?.(index);
    },
    [canNavigate, slides.length, broadcastSlideChange, onSlideChange]
  );

  const goNext = useCallback(() => {
    goToSlide(currentSlide + 1);
  }, [currentSlide, goToSlide]);

  const goPrevious = useCallback(() => {
    goToSlide(currentSlide - 1);
  }, [currentSlide, goToSlide]);

  // Handle keyboard navigation
  useEffect(() => {
    if (!canNavigate) return;

    const handleKeyDown = (e) => {
      if (e.key === "ArrowRight" || e.key === "ArrowDown") {
        e.preventDefault();
        goNext();
      } else if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
        e.preventDefault();
        goPrevious();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [canNavigate, goNext, goPrevious]);

  // Empty state
  if (!slides.length) {
    return (
      <div className="flex items-center justify-center h-full bg-gray-800 rounded-xl border border-gray-700">
        <div className="text-center p-8">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gray-700 flex items-center justify-center">
            <svg
              className="w-8 h-8 text-gray-500"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>
          </div>
          <p className="text-gray-400 text-sm">No presentation loaded</p>
          {canNavigate && (
            <p className="text-gray-500 text-xs mt-1">
              Upload a presentation to get started
            </p>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
      {/* Slide display area */}
      <div className="flex-1 relative flex items-center justify-center p-4 bg-gray-900">
        <img
          src={slides[currentSlide]}
          alt={`Slide ${currentSlide + 1} of ${slides.length}`}
          className="max-w-full max-h-full object-contain rounded-lg shadow-lg"
          draggable={false}
        />

        {/* Slide counter badge */}
        <div className="absolute top-3 right-3 px-3 py-1.5 bg-black/60 backdrop-blur-sm rounded-full text-xs text-gray-200 font-medium">
          Slide {currentSlide + 1} of {slides.length}
        </div>
      </div>

      {/* Navigation controls — hidden for observers */}
      {canNavigate && (
        <div className="flex items-center justify-between px-4 py-3 bg-gray-800 border-t border-gray-700">
          <button
            onClick={goPrevious}
            disabled={currentSlide === 0}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg transition-colors
              disabled:opacity-40 disabled:cursor-not-allowed
              bg-gray-700 hover:bg-gray-600 text-gray-200 disabled:hover:bg-gray-700"
            aria-label="Previous slide"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Previous
          </button>

          {/* Slide indicator dots (show up to 10, then collapse) */}
          <div className="flex items-center gap-1.5">
            {slides.length <= 10 ? (
              slides.map((_, idx) => (
                <button
                  key={idx}
                  onClick={() => goToSlide(idx)}
                  className={`w-2.5 h-2.5 rounded-full transition-all ${
                    idx === currentSlide
                      ? "bg-blue-500 scale-125"
                      : "bg-gray-600 hover:bg-gray-500"
                  }`}
                  aria-label={`Go to slide ${idx + 1}`}
                />
              ))
            ) : (
              <span className="text-sm text-gray-400 font-medium">
                {currentSlide + 1} / {slides.length}
              </span>
            )}
          </div>

          <button
            onClick={goNext}
            disabled={currentSlide === slides.length - 1}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg transition-colors
              disabled:opacity-40 disabled:cursor-not-allowed
              bg-gray-700 hover:bg-gray-600 text-gray-200 disabled:hover:bg-gray-700"
            aria-label="Next slide"
          >
            Next
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>
        </div>
      )}

      {/* Observer-only: minimal slide counter at bottom */}
      {!canNavigate && (
        <div className="flex items-center justify-center px-4 py-2 bg-gray-800 border-t border-gray-700">
          <span className="text-xs text-gray-500">
            Slide {currentSlide + 1} of {slides.length} — View only
          </span>
        </div>
      )}
    </div>
  );
}
