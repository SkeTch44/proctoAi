// src/pages/InterviewPages/CreateInterviewPage.jsx
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { API_BASE, getAuthHeader } from "../../utils/apiConfig";

export default function CreateInterviewPage() {
  const navigate = useNavigate();

  const [title, setTitle] = useState("");
  const [scheduledAt, setScheduledAt] = useState("");
  const [maxParticipants, setMaxParticipants] = useState(6);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [createdSession, setCreatedSession] = useState(null);
  const [copied, setCopied] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (!title.trim()) {
      setError("Title is required.");
      return;
    }
    if (title.length > 500) {
      setError("Title must be 500 characters or fewer.");
      return;
    }

    setIsSubmitting(true);

    try {
      const body = {
        title: title.trim(),
        max_participants: maxParticipants,
      };
      if (scheduledAt) {
        body.scheduled_at = new Date(scheduledAt).toISOString();
      }

      const res = await fetch(`${API_BASE}/api/v1/interviews/sessions`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...getAuthHeader(),
        },
        body: JSON.stringify(body),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || data.message || "Failed to create session");
      }

      setCreatedSession(data);
    } catch (err) {
      setError(err.message || "Something went wrong. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCopyLink = async () => {
    if (!createdSession?.join_url) return;
    try {
      await navigator.clipboard.writeText(createdSession.join_url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback for older browsers
      const input = document.createElement("input");
      input.value = createdSession.join_url;
      document.body.appendChild(input);
      input.select();
      document.execCommand("copy");
      document.body.removeChild(input);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  // Success state — show session details
  if (createdSession) {
    return (
      <div className="min-h-screen bg-[#F3F4F6] dark:bg-[#011627] flex items-center justify-center p-4">
        <div className="w-full max-w-lg bg-white dark:bg-[#0f1724] rounded-2xl shadow-xl border border-gray-200 dark:border-gray-700 p-8">
          <div className="text-center mb-6">
            <div className="w-16 h-16 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
              <span className="text-3xl">✅</span>
            </div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
              Session Created
            </h1>
            <p className="text-gray-500 dark:text-gray-400 mt-1">
              Share the join link with your participants.
            </p>
          </div>

          <div className="space-y-4">
            <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl p-4">
              <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                Session ID
              </label>
              <p className="text-sm font-mono text-gray-900 dark:text-gray-100 mt-1 break-all">
                {createdSession.session_id}
              </p>
            </div>

            <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl p-4">
              <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                Room Name
              </label>
              <p className="text-sm font-mono text-gray-900 dark:text-gray-100 mt-1">
                {createdSession.room_name}
              </p>
            </div>

            <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl p-4">
              <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                Join Link
              </label>
              <p className="text-sm font-mono text-blue-600 dark:text-blue-400 mt-1 break-all">
                {createdSession.join_url}
              </p>
            </div>

            <button
              onClick={handleCopyLink}
              className="w-full py-3 px-4 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-xl transition-colors flex items-center justify-center gap-2"
            >
              {copied ? (
                <>
                  <span>✓</span> Copied!
                </>
              ) : (
                <>
                  <span>📋</span> Copy Join Link
                </>
              )}
            </button>

            <button
              onClick={() => navigate(`/interview/join/${createdSession.session_id}`)}
              className="w-full py-3 px-4 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-900 dark:text-gray-100 font-medium rounded-xl transition-colors"
            >
              Join Session
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Form state
  return (
    <div className="min-h-screen bg-[#F3F4F6] dark:bg-[#011627] flex items-center justify-center p-4">
      <div className="w-full max-w-lg bg-white dark:bg-[#0f1724] rounded-2xl shadow-xl border border-gray-200 dark:border-gray-700 p-8">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            Create Interview Session
          </h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">
            Set up a new multi-party interview room.
          </p>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl text-red-700 dark:text-red-400 text-sm">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Title */}
          <div>
            <label
              htmlFor="title"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
            >
              Title <span className="text-red-500">*</span>
            </label>
            <input
              id="title"
              type="text"
              required
              maxLength={500}
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Senior Backend Engineer - Round 2"
              className="w-full px-4 py-3 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all"
            />
            <p className="text-xs text-gray-400 mt-1">
              {title.length}/500 characters
            </p>
          </div>

          {/* Scheduled At */}
          <div>
            <label
              htmlFor="scheduledAt"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
            >
              Scheduled At{" "}
              <span className="text-gray-400 font-normal">(optional)</span>
            </label>
            <input
              id="scheduledAt"
              type="datetime-local"
              value={scheduledAt}
              onChange={(e) => setScheduledAt(e.target.value)}
              className="w-full px-4 py-3 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all"
            />
          </div>

          {/* Max Participants */}
          <div>
            <label
              htmlFor="maxParticipants"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
            >
              Max Participants
            </label>
            <input
              id="maxParticipants"
              type="number"
              min={2}
              max={10}
              value={maxParticipants}
              onChange={(e) => setMaxParticipants(Number(e.target.value))}
              className="w-full px-4 py-3 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all"
            />
            <p className="text-xs text-gray-400 mt-1">
              Between 2 and 10 participants allowed.
            </p>
          </div>

          {/* Submit */}
          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full py-3 px-4 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-medium rounded-xl shadow-lg hover:shadow-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSubmitting ? (
              <span className="flex items-center justify-center gap-2">
                <span className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></span>
                Creating...
              </span>
            ) : (
              "Create Session"
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
