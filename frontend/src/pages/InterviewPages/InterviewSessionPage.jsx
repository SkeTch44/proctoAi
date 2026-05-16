// src/pages/InterviewPages/InterviewSessionPage.jsx
import { useState, useEffect, useCallback } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import {
  LiveKitRoom,
  VideoConference,
  RoomAudioRenderer,
  ConnectionStateToast,
  useConnectionState,
  useParticipants,
} from "@livekit/components-react";
import "@livekit/components-styles";

// Support both Vite (VITE_LIVEKIT_URL) and CRA (REACT_APP_LIVEKIT_URL) env variables
const LIVEKIT_URL =
  (typeof import.meta !== "undefined" && import.meta.env?.VITE_LIVEKIT_URL) ||
  process.env.REACT_APP_LIVEKIT_URL ||
  "ws://localhost:7880";

/**
 * ConnectionStatusOverlay — shows reconnecting/disconnected indicators
 * based on WebRTC connection state with a 60-second timeout.
 *
 * Requirements: 9.3 — "reconnecting" indicator when WebRTC drops,
 * 60-second timeout before showing "disconnected".
 */
function ConnectionStatusOverlay() {
  const connectionState = useConnectionState();
  const [showDisconnected, setShowDisconnected] = useState(false);
  const [reconnectStart, setReconnectStart] = useState(null);

  useEffect(() => {
    let timer;

    if (connectionState === "reconnecting") {
      if (!reconnectStart) {
        setReconnectStart(Date.now());
      }
      setShowDisconnected(false);

      // Start 60-second timeout
      timer = setTimeout(() => {
        setShowDisconnected(true);
      }, 60000);
    } else if (connectionState === "connected") {
      setReconnectStart(null);
      setShowDisconnected(false);
    } else if (connectionState === "disconnected") {
      setShowDisconnected(true);
    }

    return () => {
      if (timer) clearTimeout(timer);
    };
  }, [connectionState, reconnectStart]);

  if (connectionState === "reconnecting" && !showDisconnected) {
    return (
      <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
        <div className="text-center p-8 rounded-2xl bg-gray-800/90 border border-yellow-500/50 shadow-2xl">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-yellow-400 mx-auto mb-4"></div>
          <h2 className="text-xl font-bold text-yellow-400 mb-2">
            Reconnecting...
          </h2>
          <p className="text-gray-300 text-sm">
            Your connection was interrupted. Attempting to reconnect.
          </p>
        </div>
      </div>
    );
  }

  if (showDisconnected) {
    return (
      <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm">
        <div className="text-center p-8 rounded-2xl bg-gray-800/90 border border-red-500/50 shadow-2xl">
          <div className="w-12 h-12 rounded-full bg-red-500/20 flex items-center justify-center mx-auto mb-4">
            <span className="text-2xl">⚠️</span>
          </div>
          <h2 className="text-xl font-bold text-red-400 mb-2">Disconnected</h2>
          <p className="text-gray-300 text-sm mb-4">
            Unable to reconnect to the session. Please check your network
            connection.
          </p>
          <button
            onClick={() => window.location.reload()}
            className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
          >
            Rejoin Session
          </button>
        </div>
      </div>
    );
  }

  return null;
}

/**
 * ParticipantRoleLabels — overlays role labels on participant video tiles.
 * Reads participant metadata to determine role.
 */
function ParticipantRoleLabels() {
  const participants = useParticipants();

  return (
    <div className="absolute top-2 left-2 z-10 flex flex-col gap-1">
      {participants.map((participant) => {
        const role = participant.metadata
          ? (() => {
              try {
                return JSON.parse(participant.metadata).role || "participant";
              } catch {
                return "participant";
              }
            })()
          : "participant";

        return (
          <div
            key={participant.identity}
            className="flex items-center gap-2 bg-black/60 px-2 py-1 rounded text-xs text-white"
          >
            <span
              className={`w-2 h-2 rounded-full ${
                role === "interviewer"
                  ? "bg-blue-400"
                  : role === "interviewee"
                  ? "bg-green-400"
                  : "bg-gray-400"
              }`}
            />
            <span className="font-medium">
              {participant.name || participant.identity}
            </span>
            <span className="text-gray-400 capitalize">({role})</span>
          </div>
        );
      })}
    </div>
  );
}

/**
 * InterviewSessionPage — Multi-party video conferencing page using LiveKit.
 *
 * Receives `token` and `roomName` via:
 *   1. Route state (location.state) from the join flow
 *   2. Props (for direct embedding)
 *
 * Requirements:
 *   8.1 — LiveKit video grid with all participants
 *   8.2 — Distribute tracks to all subscribed participants
 *   8.4 — Unpublish tracks on disconnect
 *   9.3 — Reconnecting indicator with 60s timeout
 */
export default function InterviewSessionPage({ token: propToken, roomName: propRoomName }) {
  const location = useLocation();
  const navigate = useNavigate();

  // Resolve token and roomName from props or route state
  const token = propToken || location.state?.token;
  const roomName = propRoomName || location.state?.roomName;
  const sessionTitle = location.state?.sessionTitle || "Interview Session";
  const participants = location.state?.participants || [];

  // If no token/roomName, redirect to join flow
  useEffect(() => {
    if (!token || !roomName) {
      navigate("/interview/join", { replace: true });
    }
  }, [token, roomName, navigate]);

  const handleDisconnected = useCallback(() => {
    // Session ended or user was removed — navigate away
    navigate("/student/dashboard", { replace: true });
  }, [navigate]);

  if (!token || !roomName) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-900">
        <div className="text-center p-8">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-300">Connecting to interview session...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-gray-900 text-white overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-3 bg-gray-800 border-b border-gray-700">
        <div>
          <h1 className="text-lg font-bold">{sessionTitle}</h1>
          <p className="text-xs text-gray-400">Room: {roomName}</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <div className="w-2.5 h-2.5 rounded-full bg-green-400 animate-pulse" />
            <span className="text-xs text-gray-300">Live</span>
          </div>
          <button
            onClick={() => navigate("/student/dashboard", { replace: true })}
            className="px-4 py-1.5 bg-red-600 hover:bg-red-700 text-white text-sm rounded-lg font-medium transition-colors"
          >
            Leave
          </button>
        </div>
      </div>

      {/* LiveKit Room */}
      <div className="flex-1 relative">
        <LiveKitRoom
          token={token}
          serverUrl={LIVEKIT_URL}
          connect={true}
          onDisconnected={handleDisconnected}
          data-lk-theme="default"
          className="h-full"
        >
          {/* Connection status overlay (reconnecting / disconnected) */}
          <ConnectionStatusOverlay />

          {/* Role labels for participants */}
          <ParticipantRoleLabels />

          {/* Video conference grid — handles video tiles, controls, etc. */}
          <VideoConference />

          {/* Audio renderer for remote participants */}
          <RoomAudioRenderer />

          {/* Built-in connection state toast from LiveKit */}
          <ConnectionStateToast />
        </LiveKitRoom>
      </div>
    </div>
  );
}
