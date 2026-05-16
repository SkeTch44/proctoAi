// src/pages/AdminPages/CodingSubmissions.jsx
// Admin view: list coding submissions, view detail, override AI score with feedback.
import React, { useEffect, useState } from "react";
import { API_BASE, getAuthHeader } from "../../utils/apiConfig";

export default function CodingSubmissions() {
  const [submissions, setSubmissions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("pending"); // pending | reviewed | all
  const [selected, setSelected] = useState(null);

  const refresh = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filter === "pending") params.set("reviewed", "false");
      else if (filter === "reviewed") params.set("reviewed", "true");

      const res = await fetch(
        `${API_BASE}/api/v1/coding/admin/submissions?${params}`,
        { headers: getAuthHeader() }
      );
      const data = await res.json();
      setSubmissions(Array.isArray(data) ? data : []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filter]);

  const openDetail = async (id) => {
    try {
      const res = await fetch(
        `${API_BASE}/api/v1/coding/admin/submissions/${id}`,
        { headers: getAuthHeader() }
      );
      const data = await res.json();
      setSelected(data);
    } catch (e) {
      alert(e.message);
    }
  };

  const submitReview = async (id, score, feedback) => {
    const res = await fetch(
      `${API_BASE}/api/v1/coding/admin/submissions/${id}/review`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json", ...getAuthHeader() },
        body: JSON.stringify({ score, feedback }),
      }
    );
    if (res.ok) {
      setSelected(null);
      refresh();
    } else {
      alert("Review failed");
    }
  };

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Coding Submissions</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Review AI-scored submissions and finalize grades.
          </p>
        </div>
        <div className="flex gap-2">
          {["pending", "reviewed", "all"].map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-4 py-1.5 rounded-lg text-xs font-bold capitalize ${
                filter === f
                  ? "bg-blue-600 text-white"
                  : "bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-200"
              }`}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="text-gray-400 text-center py-10">Loading...</div>
      ) : submissions.length === 0 ? (
        <div className="text-gray-500 dark:text-gray-400 text-center py-10">
          No submissions {filter !== "all" ? filter : ""}.
        </div>
      ) : (
        <div className="bg-white dark:bg-[#171A1D] border border-gray-200 dark:border-[#374151] rounded-2xl overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 dark:bg-gray-800 text-left text-xs text-gray-500 uppercase">
              <tr>
                <th className="p-3">User</th>
                <th className="p-3">Problem</th>
                <th className="p-3">Lang</th>
                <th className="p-3">Status</th>
                <th className="p-3">Tests</th>
                <th className="p-3">Score</th>
                <th className="p-3">AI</th>
                <th className="p-3">Cheats</th>
                <th className="p-3">When</th>
                <th className="p-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y dark:divide-gray-700">
              {submissions.map((s) => (
                <tr key={s.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/50">
                  <td className="p-3 font-medium text-gray-800 dark:text-gray-100">
                    {s.username || `#${s.user_id}`}
                  </td>
                  <td className="p-3 truncate max-w-[200px]">{s.problem_title || `#${s.problem_id}`}</td>
                  <td className="p-3 text-xs">{s.language}</td>
                  <td className="p-3">
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                      s.status === "accepted"
                        ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300"
                        : "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300"
                    }`}>
                      {s.status?.replace("_", " ")}
                    </span>
                  </td>
                  <td className="p-3 text-xs">{s.tests_passed}/{s.tests_total}</td>
                  <td className="p-3 text-xs font-bold">{s.score}%</td>
                  <td className="p-3 text-xs">{s.ai_score != null ? `${Math.round(s.ai_score)}/100` : "—"}</td>
                  <td className="p-3 text-xs text-gray-500">
                    {s.paste_count > 0 && <span title="Paste count">📋 {s.paste_count}</span>}
                    {s.typing_speed_wpm > 80 && <span title="High typing speed" className="ml-1">⚡ {Math.round(s.typing_speed_wpm)} wpm</span>}
                  </td>
                  <td className="p-3 text-xs text-gray-500">
                    {s.submitted_at ? new Date(s.submitted_at).toLocaleString() : ""}
                  </td>
                  <td className="p-3">
                    <button
                      onClick={() => openDetail(s.id)}
                      className="px-3 py-1 text-xs rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-bold"
                    >
                      {s.admin_reviewed ? "View" : "Review"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {selected && (
        <DetailModal
          submission={selected}
          onClose={() => setSelected(null)}
          onReview={submitReview}
        />
      )}
    </div>
  );
}

function DetailModal({ submission, onClose, onReview }) {
  const [score, setScore] = useState(
    submission.admin_score != null
      ? submission.admin_score
      : submission.ai_score != null
      ? Math.round(submission.ai_score)
      : submission.score
  );
  const [feedback, setFeedback] = useState(submission.admin_feedback || "");

  const rubric = submission.ai_rubric;

  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4 overflow-y-auto">
      <div className="bg-white dark:bg-[#1A1D21] rounded-2xl shadow-2xl max-w-5xl w-full max-h-[92vh] overflow-y-auto">
        <div className="p-6 space-y-4">
          <div className="flex justify-between items-start">
            <div>
              <h2 className="text-xl font-bold text-gray-900 dark:text-white">
                {submission.problem?.title || `Problem #${submission.problem?.id}`}
              </h2>
              <p className="text-sm text-gray-500">
                Submitted by {submission.username || `#${submission.user_id}`} • {submission.language}
              </p>
            </div>
            <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-2xl">×</button>
          </div>

          <div className="grid grid-cols-3 gap-3 text-center">
            <Stat label="Tests" value={`${submission.tests_passed}/${submission.tests_total}`} />
            <Stat label="Test Score" value={`${submission.score}%`} />
            <Stat label="AI Score" value={submission.ai_score != null ? `${Math.round(submission.ai_score)}/100` : "—"} />
          </div>

          {(submission.paste_count > 0 || submission.typing_speed_wpm) && (
            <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-300 dark:border-yellow-700 rounded-lg p-3 text-xs">
              <span className="font-bold text-yellow-800 dark:text-yellow-200">⚠️ Cheat signals:</span>
              {submission.paste_count > 0 && <span className="ml-2">📋 {submission.paste_count} paste(s)</span>}
              {submission.typing_speed_wpm && <span className="ml-2">⚡ {Math.round(submission.typing_speed_wpm)} wpm avg</span>}
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div>
              <h3 className="text-sm font-bold text-gray-700 dark:text-gray-200 mb-2">Source Code</h3>
              <pre className="bg-[#0f1115] text-green-300 text-xs p-3 rounded-lg max-h-80 overflow-auto font-mono">
                {submission.source_code}
              </pre>
            </div>
            <div className="space-y-3">
              {rubric && (
                <div className="bg-gray-50 dark:bg-[#0f1115] border dark:border-gray-700 rounded-lg p-3">
                  <h3 className="text-sm font-bold text-blue-500 mb-2">🤖 AI Rubric ({rubric.total_score}/100)</h3>
                  <RubricRow label="Correctness" data={rubric.correctness} max={40} />
                  <RubricRow label="Code Quality" data={rubric.code_quality} max={25} />
                  <RubricRow label="Complexity" data={rubric.complexity_analysis} max={20}
                    extra={rubric.complexity_analysis ? `${rubric.complexity_analysis.time_complexity} / ${rubric.complexity_analysis.space_complexity}` : null} />
                  <RubricRow label="Style" data={rubric.style_readability} max={15} />
                  {rubric.overall_feedback && (
                    <p className="mt-2 text-xs text-gray-600 dark:text-gray-300 italic">
                      {rubric.overall_feedback}
                    </p>
                  )}
                  {rubric.suggestions?.length > 0 && (
                    <ul className="mt-2 list-disc list-inside text-xs text-gray-600 dark:text-gray-400">
                      {rubric.suggestions.map((s, i) => <li key={i}>{s}</li>)}
                    </ul>
                  )}
                </div>
              )}

              {submission.stderr && (
                <div className="bg-red-50 dark:bg-red-900/20 border border-red-300 dark:border-red-700 rounded-lg p-3">
                  <h4 className="text-xs font-bold text-red-700 dark:text-red-300 mb-1">Error</h4>
                  <pre className="text-xs text-red-700 dark:text-red-300 whitespace-pre-wrap font-mono">
                    {submission.stderr}
                  </pre>
                </div>
              )}
            </div>
          </div>

          <div className="border-t dark:border-gray-700 pt-4">
            <h3 className="text-sm font-bold text-gray-700 dark:text-gray-200 mb-2">Final Review</h3>
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="block text-xs text-gray-500 mb-1">Final score (0-100)</label>
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={score}
                  onChange={(e) => setScore(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border dark:border-gray-700 bg-white dark:bg-[#0f1115] text-gray-900 dark:text-gray-100"
                />
              </div>
              <div className="col-span-2">
                <label className="block text-xs text-gray-500 mb-1">Feedback for student</label>
                <input
                  type="text"
                  value={feedback}
                  onChange={(e) => setFeedback(e.target.value)}
                  placeholder="Optional feedback..."
                  className="w-full px-3 py-2 rounded-lg border dark:border-gray-700 bg-white dark:bg-[#0f1115] text-gray-900 dark:text-gray-100"
                />
              </div>
            </div>
            {submission.admin_reviewed && (
              <p className="text-xs text-green-600 dark:text-green-400 mt-2">
                ✓ Already reviewed (current admin score: {submission.admin_score})
              </p>
            )}
          </div>
        </div>

        <div className="border-t dark:border-gray-700 px-6 py-4 flex justify-end gap-3 bg-gray-50 dark:bg-[#0f1115] rounded-b-2xl">
          <button
            onClick={onClose}
            className="px-5 py-2 rounded-xl bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-200 font-bold"
          >
            Close
          </button>
          <button
            onClick={() => onReview(submission.id, parseFloat(score), feedback)}
            className="px-5 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold"
          >
            {submission.admin_reviewed ? "Update Review" : "Submit Review"}
          </button>
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value }) {
  return (
    <div className="bg-gray-50 dark:bg-[#0f1115] border dark:border-gray-700 rounded-lg p-3">
      <div className="text-xs text-gray-500 uppercase">{label}</div>
      <div className="text-lg font-bold text-gray-900 dark:text-white">{value}</div>
    </div>
  );
}

function RubricRow({ label, data, max, extra }) {
  if (!data) return null;
  const pct = Math.round((data.score / max) * 100);
  const color = pct >= 80 ? "bg-green-500" : pct >= 50 ? "bg-yellow-500" : "bg-red-500";
  return (
    <div className="mb-2">
      <div className="flex justify-between text-xs mb-0.5">
        <span className="text-gray-700 dark:text-gray-200">{label}</span>
        <span className="text-gray-400">{data.score}/{max}</span>
      </div>
      <div className="h-1 bg-gray-200 dark:bg-gray-800 rounded-full overflow-hidden">
        <div className={`h-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      {extra && <div className="text-[10px] text-gray-400 mt-0.5">{extra}</div>}
      {data.feedback && <div className="text-[10px] text-gray-500 mt-0.5">{data.feedback}</div>}
    </div>
  );
}
