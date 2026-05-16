// src/pages/InterviewPages/JoinInterviewPage.jsx
import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { API_BASE, getAuthHeader } from "../../utils/apiConfig";

export default function JoinInterviewPage() {
  const { sessionId } = useParams();
  const navigate = useNavigate();

  const [role, setRole] = useState("interviewee");
  const [displayName, setDisplayName] = useState("");
  const [isJoining, setIsJoining] = useState(false);
  const [error, setError] = useState("");

  const handleJoin = async (e) => {
    e.preventDefault();
    setError("");

    if (!displayName.trim()) {
      setError("Display name is required.");
      return;
    }

    if (!sessionId) {
      setError("Invalid session link. No session ID found.");
      return;
    }

    setIsJoining(true);

    try {
      const res = await fetch(
        `${API_BASE}/api/v1/interviews/sessions/${sessionId}/join`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...getAuthHeader(),
          },
          body: JSON.stringify({
            role,
            display_name: displayName.trim(),
          }),
        }
      );

      const data = await res.json();

      if (!res.ok) {
        // Handle specific error cases
        if (res.status === 404) {
          throw new Error("Session not found. It may have been deleted.");
        }
        if (res.status === 409) {
          throw new Error(
            data.detail || "Conflict: You may already be in this session."
          );
        }
        if (res.status === 410) {
          throw new Error("This session has ended.");
        }
        if (res.status === 422) {
          throw new Error(
            data.detail || "Invalid request. Please check your inputs."
          );
        }
        throw new Error(
          data.detail || data.message || "Failed to join session."
        );
      }

      // Navigate to the interview session page with connection details
      navigate("/interview/session", {
        state: {
          token: data.livekit_token,
          roomName: data.room_name,
          sessionTitle: data.session?.title || "Interview Session",
          participants: data.participants || [],
        },
        replace: true,
      });
    } catch (err) {
      setError(err.message || "Something went wrong. Please try again.");
    } finally {
      setIsJoining(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#F3F4F6] dark:bg-[#011627] flex items-center justify-center p-4">
      <div className="w-full max-w-md bg-white dark:bg-[#0f1724] rounded-2xl shadow-xl border border-gray-200 dark:border-gray-700 p-8">
        <div className="mb-6">
          <div className="w-14 h-14 bg-blue-100 dark:bg-blue-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
            <span className="text-2xl">🎥</span>
          </div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 text-center">
            Join Interview
          </h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1 text-center text-sm">
            Enter your details to join the session.
          </p>
          {sessionId && (
            <p className="text-xs text-gray-400 dark:text-gray-500 text-center mt-2 font-mono">
              Session: {sessionId}
            </p>
          )}
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl text-red-700 dark:text-red-400 text-sm">
            {error}
          </div>
        )}

        <form onSubmit={handleJoin} className="space-y-5">
          {/* Display Name */}
          <div>
            <label
              htmlFor="displayName"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
            >
              Display Name <span className="text-red-500">*</span>
            </label>
            <input
              id="displayName"
              type="text"
              required
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="How others will see you"
              className="w-full px-4 py-3 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all"
            />
          </div>

          {/* Role Selection */}
          <div>
            <label
              htmlFor="role"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
            >
              Role
            </label>
            <select
              id="role"
              value={role}
              onChange={(e) => setRole(e.target.value)}
              className="w-full px-4 py-3 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all appearance-none"
            >
              <option value="interviewer">Interviewer</option>
              <option value="interviewee">Interviewee</option>
              <option value="observer">Observer</option>
            </select>
            <p className="text-xs text-gray-400 mt-1">
              {role === "interviewer" &&
                "You can publish audio/video and manage the session."}
              {role === "interviewee" &&
                "You can publish audio/video and share your screen."}
              {role === "observer" &&
                "You can watch and listen but cannot publish audio/video."}
            </p>
          </div>

          {/* Submit */}
          <button
            type="submit"
            disabled={isJoining}
            className="w-full py-3 px-4 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-medium rounded-xl shadow-lg hover:shadow-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isJoining ? (
              <span className="flex items-center justify-center gap-2">
                <span className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></span>
                Joining...
              </span>
            ) : (
              "Join Session"
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
