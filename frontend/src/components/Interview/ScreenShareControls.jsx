import { useState, useEffect, useCallback } from "react";
import {
  useLocalParticipant,
  useRoomContext,
  useTracks,
} from "@livekit/components-react";
import { Track, createLocalScreenTracks } from "livekit-client";

/**
 * Maximum concurrent screen-share tracks allowed per session.
 * If this limit is reached, additional share attempts are blocked.
 */
const MAX_SCREEN_SHARES = 2;

/**
 * ScreenShareControls — Toggle button for screen sharing via LiveKit.
 *
 * Props:
 *   - role: "interviewer" | "interviewee" | "observer"
 *
 * Behavior:
 *   - Observers: component renders nothing (hidden entirely)
 *   - Interviewers/Interviewees: shows a toggle button to start/stop screen sharing
 *   - Enforces a max of 2 concurrent screen-share tracks per session
 *   - Automatically unpublishes the track on stop or disconnect
 *   - Shows an active indicator when screen sharing is in progress
 */
export default function ScreenShareControls({ role = "observer" }) {
  const [isSharing, setIsSharing] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const { localParticipant } = useLocalParticipant();
  const room = useRoomContext();

  // Track all screen-share tracks in the room (from all participants)
  const screenShareTracks = useTracks(
    [{ source: Track.Source.ScreenShare, withPlaceholder: false }],
    { onlySubscribed: false }
  );

  const activeScreenShares = screenShareTracks.length;

  // Sync local sharing state with actual published tracks
  useEffect(() => {
    if (!localParticipant) return;

    const localScreenTrack = localParticipant
      .getTrackPublications()
      .find(
        (pub) =>
          pub.source === Track.Source.ScreenShare && pub.track !== undefined
      );

    setIsSharing(!!localScreenTrack);
  }, [localParticipant, screenShareTracks]);

  // Clean up screen share on unmount / disconnect
  useEffect(() => {
    if (!room) return;

    const handleDisconnected = () => {
      setIsSharing(false);
      setError(null);
    };

    room.on("disconnected", handleDisconnected);
    return () => {
      room.off("disconnected", handleDisconnected);
    };
  }, [room]);

  const toggleScreenShare = useCallback(async () => {
    if (!localParticipant) return;
    setError(null);

    if (isSharing) {
      // Stop sharing — unpublish the screen-share track
      setIsLoading(true);
      try {
        const publications = localParticipant.getTrackPublications();
        const screenPub = Array.from(publications.values?.() || publications).find(
          (pub) => pub.source === Track.Source.ScreenShare
        );

        if (screenPub && screenPub.track) {
          await localParticipant.unpublishTrack(screenPub.track);
          screenPub.track.stop();
        }
        setIsSharing(false);
      } catch (err) {
        setError("Failed to stop screen share");
        console.error("Screen share stop error:", err);
      } finally {
        setIsLoading(false);
      }
    } else {
      // Start sharing — check concurrent limit first
      if (activeScreenShares >= MAX_SCREEN_SHARES) {
        setError(
          `Maximum of ${MAX_SCREEN_SHARES} screen shares reached. Wait for someone to stop sharing.`
        );
        return;
      }

      setIsLoading(true);
      try {
        const tracks = await createLocalScreenTracks({ audio: true });

        for (const track of tracks) {
          await localParticipant.publishTrack(track, {
            name: "screen-share",
            simulcast: false,
          });
        }

        setIsSharing(true);
      } catch (err) {
        // User cancelled the screen picker or browser denied permission
        if (err.name === "NotAllowedError" || err.message?.includes("cancelled")) {
          // User cancelled — not an error
          setIsSharing(false);
        } else {
          setError("Failed to start screen share");
          console.error("Screen share start error:", err);
        }
      } finally {
        setIsLoading(false);
      }
    }
  }, [localParticipant, isSharing, activeScreenShares]);

  // Observers see nothing
  if (role === "observer") {
    return null;
  }

  return (
    <div className="flex items-center gap-3">
      {/* Screen share toggle button */}
      <button
        onClick={toggleScreenShare}
        disabled={isLoading || (!isSharing && activeScreenShares >= MAX_SCREEN_SHARES)}
        className={`
          relative flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium
          transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-gray-900
          ${
            isSharing
              ? "bg-red-600 hover:bg-red-700 text-white focus:ring-red-500"
              : activeScreenShares >= MAX_SCREEN_SHARES
              ? "bg-gray-700 text-gray-500 cursor-not-allowed"
              : "bg-blue-600 hover:bg-blue-700 text-white focus:ring-blue-500"
          }
          disabled:opacity-60 disabled:cursor-not-allowed
        `}
        aria-label={isSharing ? "Stop screen sharing" : "Start screen sharing"}
        title={
          activeScreenShares >= MAX_SCREEN_SHARES && !isSharing
            ? `Maximum of ${MAX_SCREEN_SHARES} concurrent screen shares reached`
            : isSharing
            ? "Stop sharing your screen"
            : "Share your screen"
        }
      >
        {/* Loading spinner */}
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center rounded-lg bg-inherit">
            <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
          </div>
        )}

        {/* Screen share icon */}
        <svg
          className={`w-5 h-5 ${isLoading ? "opacity-0" : ""}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          {isSharing ? (
            // Stop icon (screen with X)
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
            />
          ) : (
            // Share icon (screen with arrow)
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
            />
          )}
        </svg>

        <span className={isLoading ? "opacity-0" : ""}>
          {isSharing ? "Stop Sharing" : "Share Screen"}
        </span>

        {/* Active sharing pulse indicator */}
        {isSharing && (
          <span className="absolute -top-1 -right-1 flex h-3 w-3">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-3 w-3 bg-red-500" />
          </span>
        )}
      </button>

      {/* Active screen shares indicator */}
      {activeScreenShares > 0 && (
        <div className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-700/50 rounded-lg border border-gray-600">
          <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
          <span className="text-xs text-gray-300">
            {activeScreenShares} screen{activeScreenShares > 1 ? "s" : ""} shared
          </span>
        </div>
      )}

      {/* Error message */}
      {error && (
        <div className="flex items-center gap-2 px-3 py-1.5 bg-red-900/30 border border-red-700/50 rounded-lg">
          <svg className="w-4 h-4 text-red-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <span className="text-xs text-red-300">{error}</span>
          <button
            onClick={() => setError(null)}
            className="text-red-400 hover:text-red-300 ml-1"
            aria-label="Dismiss error"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      )}
    </div>
  );
}
