// src/components/Interview/ParticipantSidebar.jsx
import { useState, useEffect, useCallback } from "react";
import { API_BASE, getAuthHeader } from "../../utils/apiConfig";

const ROLE_BADGES = {
  interviewer: {
    label: "Interviewer",
    className: "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300",
  },
  interviewee: {
    label: "Interviewee",
    className: "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300",
  },
  observer: {
    label: "Observer",
    className: "bg-gray-100 text-gray-600 dark:bg-gray-700/40 dark:text-gray-300",
  },
};

const STATUS_INDICATORS = {
  connected: {
    className: "bg-green-400",
    label: "Connected",
  },
  disconnected: {
    className: "bg-red-400",
    label: "Disconnected",
  },
  removed: {
    className: "bg-gray-400",
    label: "Removed",
  },
};

/**
 * ParticipantSidebar — Displays the list of participants in an interview session.
 *
 * Props:
 *   - sessionId: string — the interview session ID
 *   - isInterviewer: boolean — whether the current user is an interviewer (shows remove buttons)
 *   - pollInterval: number — how often to refresh participants (ms, default 5000)
 */
export default function ParticipantSidebar({
  sessionId,
  isInterviewer = false,
  pollInterval = 5000,
}) {
  const [participants, setParticipants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [removingId, setRemovingId] = useState(null);

  const fetchParticipants = useCallback(async () => {
    if (!sessionId) return;

    try {
      const res = await fetch(
        `${API_BASE}/api/v1/interviews/sessions/${sessionId}/participants`,
        {
          headers: getAuthHeader(),
        }
      );

      if (!res.ok) {
        throw new Error("Failed to fetch participants");
      }

      const data = await res.json();
      setParticipants(data.participants || data || []);
      setError("");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  // Initial fetch and polling
  useEffect(() => {
    fetchParticipants();

    const interval = setInterval(fetchParticipants, pollInterval);
    return () => clearInterval(interval);
  }, [fetchParticipants, pollInterval]);

  const handleRemove = async (participantId, displayName) => {
    if (!window.confirm(`Remove ${displayName} from the session?`)) return;

    setRemovingId(participantId);

    try {
      const res = await fetch(
        `${API_BASE}/api/v1/interviews/sessions/${sessionId}/participants/${participantId}`,
        {
          method: "DELETE",
          headers: getAuthHeader(),
        }
      );

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "Failed to remove participant");
      }

      // Refresh the list
      await fetchParticipants();
    } catch (err) {
      alert(err.message || "Failed to remove participant");
    } finally {
      setRemovingId(null);
    }
  };

  if (loading) {
    return (
      <div className="w-72 bg-white dark:bg-[#0f1724] border-l border-gray-200 dark:border-gray-700 p-4">
        <h2 className="text-sm font-bold text-gray-900 dark:text-gray-100 uppercase tracking-wide mb-4">
          Participants
        </h2>
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500"></div>
        </div>
      </div>
    );
  }

  const connectedCount = participants.filter(
    (p) => p.status === "connected"
  ).length;

  return (
    <div className="w-72 bg-white dark:bg-[#0f1724] border-l border-gray-200 dark:border-gray-700 flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <h2 className="text-sm font-bold text-gray-900 dark:text-gray-100 uppercase tracking-wide">
          Participants
        </h2>
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
          {connectedCount} connected
        </p>
      </div>

      {/* Error */}
      {error && (
        <div className="mx-4 mt-3 p-2 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-600 dark:text-red-400 text-xs">
          {error}
        </div>
      )}

      {/* Participant List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-2">
        {participants.length === 0 ? (
          <p className="text-sm text-gray-400 dark:text-gray-500 text-center py-4">
            No participants yet.
          </p>
        ) : (
          participants.map((participant) => {
            const roleBadge = ROLE_BADGES[participant.role] || ROLE_BADGES.observer;
            const statusInfo =
              STATUS_INDICATORS[participant.status] || STATUS_INDICATORS.disconnected;

            return (
              <div
                key={participant.id || participant.user_id}
                className={`p-3 rounded-xl border transition-all ${
                  participant.status === "connected"
                    ? "border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/30"
                    : "border-gray-100 dark:border-gray-800 bg-gray-50/50 dark:bg-gray-800/10 opacity-60"
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    {/* Name + Status */}
                    <div className="flex items-center gap-2">
                      <div
                        className={`w-2 h-2 rounded-full flex-shrink-0 ${statusInfo.className}`}
                        title={statusInfo.label}
                      />
                      <span className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                        {participant.display_name}
                      </span>
                    </div>

                    {/* Role Badge */}
                    <div className="mt-1.5">
                      <span
                        className={`inline-block text-xs font-medium px-2 py-0.5 rounded-full ${roleBadge.className}`}
                      >
                        {roleBadge.label}
                      </span>
                    </div>
                  </div>

                  {/* Remove Button (interviewers only) */}
                  {isInterviewer && participant.status === "connected" && (
                    <button
                      onClick={() =>
                        handleRemove(
                          participant.id || participant.user_id,
                          participant.display_name
                        )
                      }
                      disabled={removingId === (participant.id || participant.user_id)}
                      className="flex-shrink-0 p-1.5 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors disabled:opacity-50"
                      title={`Remove ${participant.display_name}`}
                    >
                      {removingId === (participant.id || participant.user_id) ? (
                        <span className="animate-spin inline-block w-4 h-4 border-2 border-red-300 border-t-red-600 rounded-full"></span>
                      ) : (
                        <svg
                          className="w-4 h-4"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M6 18L18 6M6 6l12 12"
                          />
                        </svg>
                      )}
                    </button>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
