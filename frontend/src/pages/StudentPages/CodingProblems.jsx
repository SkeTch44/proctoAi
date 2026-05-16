// src/pages/StudentPages/CodingProblems.jsx
// List of coding problems available to students.
import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { API_BASE, getAuthHeader } from "../../utils/apiConfig";

const DIFF_STYLES = {
  easy: "bg-green-700/30 text-green-200 border-green-600",
  medium: "bg-yellow-700/30 text-yellow-200 border-yellow-600",
  hard: "bg-red-700/30 text-red-200 border-red-600",
  expert: "bg-purple-700/30 text-purple-200 border-purple-600",
};

export default function CodingProblems() {
  const navigate = useNavigate();
  const [problems, setProblems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState("");
  const [difficulty, setDifficulty] = useState("");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(`${API_BASE}/api/v1/coding/problems`, {
          headers: getAuthHeader(),
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (!cancelled) setProblems(Array.isArray(data) ? data : []);
      } catch (e) {
        if (!cancelled) setError(e.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const filtered = problems.filter((p) => {
    const matchesText =
      !search ||
      p.title.toLowerCase().includes(search.toLowerCase()) ||
      (p.tags || []).some((t) => t.toLowerCase().includes(search.toLowerCase()));
    const matchesDiff = !difficulty || p.difficulty === difficulty;
    return matchesText && matchesDiff;
  });

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
          Coding Problems
        </h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Solve algorithmic challenges in a proctored coding environment.
        </p>
      </div>

      <div className="flex flex-wrap gap-3">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by title or tag..."
          className="flex-1 min-w-[220px] px-4 py-2 rounded-xl border-2 dark:border-[#374151] bg-[#F9FAFB] dark:bg-[#1A1D21] text-gray-900 dark:text-gray-100 outline-none focus:border-blue-500"
        />
        <select
          value={difficulty}
          onChange={(e) => setDifficulty(e.target.value)}
          className="px-4 py-2 rounded-xl border-2 dark:border-[#374151] bg-[#F9FAFB] dark:bg-[#1A1D21] text-gray-900 dark:text-gray-100"
        >
          <option value="">All difficulties</option>
          <option value="easy">Easy</option>
          <option value="medium">Medium</option>
          <option value="hard">Hard</option>
          <option value="expert">Expert</option>
        </select>
      </div>

      {loading && (
        <div className="text-center py-10 text-gray-500 dark:text-gray-400">
          Loading problems...
        </div>
      )}

      {error && (
        <div className="p-4 rounded-xl bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-200 border border-red-300 dark:border-red-700">
          Failed to load problems: {error}
        </div>
      )}

      {!loading && !error && filtered.length === 0 && (
        <div className="text-center py-16 text-gray-500 dark:text-gray-400">
          No coding problems available yet.
        </div>
      )}

      <div className="grid gap-3">
        {filtered.map((p) => (
          <button
            key={p.id}
            onClick={() => navigate(`/student/coding/${p.id}`)}
            className="text-left bg-white dark:bg-[#171A1D] border border-gray-200 dark:border-[#374151] rounded-2xl p-5 shadow hover:shadow-xl hover:border-blue-500 transition group"
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs text-gray-400">#{p.id}</span>
                  <h3 className="text-base font-semibold text-gray-900 dark:text-white group-hover:text-blue-500">
                    {p.title}
                  </h3>
                </div>
                {(p.tags || []).length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-2">
                    {p.tags.slice(0, 5).map((t) => (
                      <span
                        key={t}
                        className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300"
                      >
                        {t}
                      </span>
                    ))}
                  </div>
                )}
              </div>
              <span
                className={`px-3 py-1 rounded-full text-xs font-bold uppercase border ${
                  DIFF_STYLES[p.difficulty] || "bg-gray-700/30 text-gray-200 border-gray-600"
                }`}
              >
                {p.difficulty}
              </span>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
