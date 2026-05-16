// src/pages/AdminPages/CodeReview.jsx
// Admin panel to review student coding submissions with AI rubric
import React, { useState, useEffect } from "react";
import { API_BASE, getAuthHeader } from "../../utils/apiConfig";

export default function CodeReview() {
  const [submissions, setSubmissions] = useState([]);
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(true);
  const [reviewScore, setReviewScore] = useState("");
  const [reviewFeedback, setReviewFeedback] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [filter, setFilter] = useState("pending"); // pending | reviewed

  const fetchSubmissions = async () => {
    setLoading(true);
    try {
      const reviewed = filter === "reviewed";
      const res = await fetch(
        `${API_BASE}/api/v1/coding/admin/submissions?reviewed=${reviewed}`,
        { headers: getAuthHeader() }
      );
      if (res.ok) {
        const data = await res.json();
        setSubmissions(data);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchSubmissions(); }, [filter]);

  const selectSubmission = async (id) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/coding/admin/submissions/${id}`, {
        headers: getAuthHeader(),
      });
      if (res.ok) {
        const data = await res.json();
        setSelected(data);
        setReviewScore(data.ai_score?.toString() || "");
        setReviewFeedback(data.admin_feedback || "");
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleReview = async () => {
    if (!selected) return;
    setSubmitting(true);
    try {
      const res = await fetch(
        `${API_BASE}/api/v1/coding/admin/submissions/${selected.id}/review`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json", ...getAuthHeader() },
          body: JSON.stringify({
            score: reviewScore ? parseFloat(reviewScore) : null,
            feedback: reviewFeedback,
          }),
        }
      );
      if (res.ok) {
        alert("Review saved!");
        setSelected(null);
        fetchSubmissions();
      }
    } catch (err) {
      alert("Failed to save review");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
          🧑‍💻 Code Submissions Review
        </h2>
        <div className="flex gap-2">
          <button
            onClick={() => setFilter("pending")}
            className={`px-4 py-2 rounded-lg text-sm font-medium ${
              filter === "pending" ? "bg-blue-600 text-white" : "bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300"
            }`}
          >
            Pending Review
          </button>
          <button
            onClick={() => setFilter("reviewed")}
            className={`px-4 py-2 rounded-lg text-sm font-medium ${
              filter === "reviewed" ? "bg-blue-600 text-white" : "bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300"
            }`}
          >
            Reviewed
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Submissions list */}
        <div className="lg:col-span-1 bg-white dark:bg-[#171A1D] rounded-2xl border border-gray-200 dark:border-gray-700 shadow-lg overflow-hidden">
          <div className="p-4 border-b border-gray-200 dark:border-gray-700">
            <h3 className="font-bold text-sm text-gray-700 dark:text-gray-200">
              Submissions ({submissions.length})
            </h3>
          </div>
          <div className="max-h-[600px] overflow-y-auto divide-y divide-gray-100 dark:divide-gray-800">
            {loading ? (
              <div className="p-8 text-center text-gray-500">Loading...</div>
            ) : submissions.length === 0 ? (
              <div className="p-8 text-center text-gray-500">No submissions</div>
            ) : (
              submissions.map((sub) => (
                <div
                  key={sub.id}
                  onClick={() => selectSubmission(sub.id)}
                  className={`p-3 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 transition ${
                    selected?.id === sub.id ? "bg-blue-50 dark:bg-blue-900/20" : ""
                  }`}
                >
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium text-gray-800 dark:text-gray-200">
                      #{sub.id} — {sub.language}
                    </span>
                    <span className={`text-xs px-2 py-0.5 rounded font-bold ${
                      sub.status === "accepted" ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"
                    }`}>
                      {sub.tests_passed}/{sub.tests_total}
                    </span>
                  </div>
                  <div className="flex justify-between mt-1 text-xs text-gray-500">
                    <span>AI: {sub.ai_score ?? "—"}/100</span>
                    {sub.paste_count > 3 && (
                      <span className="text-orange-500">⚠️ {sub.paste_count} pastes</span>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Detail + Review panel */}
        <div className="lg:col-span-2 space-y-4">
          {selected ? (
            <>
              {/* Problem info */}
              <div className="bg-white dark:bg-[#171A1D] rounded-2xl border border-gray-200 dark:border-gray-700 p-4">
                <h3 className="font-bold text-gray-800 dark:text-gray-100 mb-1">
                  {selected.problem?.title || `Problem #${selected.problem_id}`}
                </h3>
                <div className="flex gap-4 text-xs text-gray-500">
                  <span>User #{selected.user_id}</span>
                  <span>Lang: {selected.language}</span>
                  <span>Tests: {selected.tests_passed}/{selected.tests_total}</span>
                  <span>⏱ {selected.execution_time_ms}ms</span>
                  {selected.paste_count > 0 && <span className="text-orange-500">📋 {selected.paste_count} pastes</span>}
                  {selected.typing_speed_wpm && <span>⌨️ {Math.round(selected.typing_speed_wpm)} WPM</span>}
                </div>
              </div>

              {/* Source code */}
              <div className="bg-[#1e1e1e] rounded-2xl border border-gray-700 overflow-hidden">
                <div className="px-4 py-2 bg-[#252526] text-xs text-gray-400 border-b border-gray-700">
                  Student's Code ({selected.language})
                </div>
                <pre className="p-4 text-sm text-green-300 font-mono overflow-auto max-h-72 whitespace-pre-wrap">
                  {selected.source_code}
                </pre>
              </div>

              {/* AI Rubric */}
              {selected.ai_rubric && (
                <div className="bg-white dark:bg-[#171A1D] rounded-2xl border border-gray-200 dark:border-gray-700 p-4">
                  <h4 className="font-bold text-sm text-blue-600 dark:text-blue-400 mb-3">
                    🤖 AI Score: {selected.ai_rubric.total_score}/100
                  </h4>
                  <div className="grid grid-cols-2 gap-3 text-xs">
                    {selected.ai_rubric.correctness && (
                      <div className="bg-gray-50 dark:bg-gray-800 p-2 rounded">
                        <div className="font-bold">Correctness: {selected.ai_rubric.correctness.score}/40</div>
                        <div className="text-gray-500">{selected.ai_rubric.correctness.feedback}</div>
                      </div>
                    )}
                    {selected.ai_rubric.code_quality && (
                      <div className="bg-gray-50 dark:bg-gray-800 p-2 rounded">
                        <div className="font-bold">Quality: {selected.ai_rubric.code_quality.score}/25</div>
                        <div className="text-gray-500">{selected.ai_rubric.code_quality.feedback}</div>
                      </div>
                    )}
                    {selected.ai_rubric.complexity_analysis && (
                      <div className="bg-gray-50 dark:bg-gray-800 p-2 rounded">
                        <div className="font-bold">Complexity: {selected.ai_rubric.complexity_analysis.score}/20</div>
                        <div className="text-gray-500">
                          T: {selected.ai_rubric.complexity_analysis.time_complexity} |
                          S: {selected.ai_rubric.complexity_analysis.space_complexity}
                        </div>
                      </div>
                    )}
                    {selected.ai_rubric.style_readability && (
                      <div className="bg-gray-50 dark:bg-gray-800 p-2 rounded">
                        <div className="font-bold">Style: {selected.ai_rubric.style_readability.score}/15</div>
                        <div className="text-gray-500">{selected.ai_rubric.style_readability.feedback}</div>
                      </div>
                    )}
                  </div>
                  {selected.ai_rubric.overall_feedback && (
                    <p className="mt-3 text-xs text-gray-600 dark:text-gray-400 italic">
                      {selected.ai_rubric.overall_feedback}
                    </p>
                  )}
                </div>
              )}

              {/* Admin review form */}
              <div className="bg-white dark:bg-[#171A1D] rounded-2xl border border-gray-200 dark:border-gray-700 p-4">
                <h4 className="font-bold text-sm text-gray-800 dark:text-gray-100 mb-3">
                  ✍️ Your Review
                </h4>
                <div className="grid grid-cols-4 gap-3">
                  <div>
                    <label className="text-xs text-gray-500 block mb-1">Final Score (0-100)</label>
                    <input
                      type="number"
                      min="0"
                      max="100"
                      value={reviewScore}
                      onChange={(e) => setReviewScore(e.target.value)}
                      placeholder="AI suggested"
                      className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-800 text-sm"
                    />
                  </div>
                  <div className="col-span-3">
                    <label className="text-xs text-gray-500 block mb-1">Feedback to student</label>
                    <input
                      type="text"
                      value={reviewFeedback}
                      onChange={(e) => setReviewFeedback(e.target.value)}
                      placeholder="Optional feedback..."
                      className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-800 text-sm"
                    />
                  </div>
                </div>
                <div className="flex justify-end mt-3 gap-2">
                  <button
                    onClick={() => { setReviewScore(selected.ai_score?.toString() || ""); handleReview(); }}
                    className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm font-bold"
                    disabled={submitting}
                  >
                    ✅ Accept AI Score
                  </button>
                  <button
                    onClick={handleReview}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-bold"
                    disabled={submitting}
                  >
                    {submitting ? "Saving..." : "💾 Save Review"}
                  </button>
                </div>
              </div>
            </>
          ) : (
            <div className="bg-white dark:bg-[#171A1D] rounded-2xl border border-gray-200 dark:border-gray-700 p-16 text-center">
              <p className="text-gray-500">Select a submission to review</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
