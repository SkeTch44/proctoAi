import React, { useState, useEffect } from "react";
import { getToken } from "../../utils/authStorage"; // Your auth utility

export default function Results() {
  const [results, setResults] = useState([]);
  const [stats, setStats] = useState({ avgScore: 0, totalExams: 0, passedExams: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchResults();
  }, []);

  const fetchResults = async () => {
    try {
      const token = getToken();
      const res = await fetch("http://127.0.0.1:5000/api/student/results", {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      });

      if (!res.ok) {
        throw new Error("Failed to fetch results");
      }

      const data = await res.json();
      setResults(data.results || []);
      setStats({
        avgScore: data.stats.avgScore || 0,
        totalExams: data.stats.totalExams || 0,
        passedExams: data.stats.passedExams || 0
      });
    } catch (err) {
      setError("No exam results found");
      console.error("Results fetch error:", err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto p-8">
        <div className="text-center py-20">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600 dark:text-gray-400">Loading results...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto p-6">
      <header className="mb-8 text-center lg:text-left">
        <h1 className="text-3xl font-black bg-gradient-to-r from-gray-900 via-blue-900 to-purple-900 bg-clip-text text-transparent dark:from-blue-400 dark:via-purple-400 dark:to-pink-400">
          Exam Results
        </h1>
        <p className="text-sm text-gray-600 dark:text-gray-300 max-w-2xl">
          {error || `Your performance across ${stats.totalExams} completed exams`}
        </p>
      </header>

      <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Stats Overview */}
        <div className="space-y-6">
          <div className="p-6 bg-gradient-to-r from-emerald-50 to-green-50 dark:from-emerald-900/20 dark:to-green-900/20 rounded-2xl border border-emerald-200/50 dark:border-emerald-400/30 shadow-sm">
            <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-4">
              Overall Performance
            </h2>
            <div className="grid grid-cols-2 gap-6">
              <div>
                <p className="text-3xl font-bold text-emerald-600 dark:text-emerald-400">
                  {stats.avgScore}%
                </p>
                <p className="text-sm text-gray-600 dark:text-gray-300">Avg Score</p>
              </div>
              <div>
                <p className="text-3xl font-bold text-gray-900 dark:text-gray-100">
                  {stats.passedExams}/{stats.totalExams}
                </p>
                <p className="text-sm text-gray-600 dark:text-gray-300">Exams Passed</p>
              </div>
            </div>
          </div>

          {/* Performance Trend */}
          <div className="p-6 bg-white dark:bg-[#0f1724] rounded-xl shadow border border-[#E5E7EB] dark:border-[#3B82F6]/40">
            <h3 className="text-lg font-semibold mb-4">Score Trend</h3>
            <div className="h-48 bg-gradient-to-r from-gray-50 to-gray-100 dark:from-[#1D1A17] dark:to-[#0f1724] rounded-xl flex items-end justify-around p-4">
              {results.slice(0, 5).map((result, idx) => (
                <div key={result.id} className="flex flex-col items-center">
                  <div
                    className={`w-12 h-48 bg-gradient-to-t from-${result.color === 'green' ? 'emerald' : 'red'}-500 to-${result.color === 'green' ? 'emerald' : 'red'}-600 rounded-lg shadow-sm mt-auto`}
                    style={{ height: `${(result.score / 100) * 300}px` }}
                  />
                  <span className="text-xs mt-2 font-semibold">{result.score}%</span>
                </div>
              )).reverse()}
            </div>
          </div>
        </div>

        {/* Recent Results */}
        <div className="space-y-6">
          <div className="p-6 bg-white dark:bg-[#0f1724] rounded-xl shadow border border-[#E5E7EB] dark:border-[#3B82F6]/40">
            <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-4">
              Recent Results
            </h2>
            {results.length === 0 ? (
              <div className="text-center py-12">
                <div className="w-16 h-16 bg-gray-100 dark:bg-gray-800 rounded-2xl flex items-center justify-center mx-auto mb-4">
                  📊
                </div>
                <p className="text-gray-500 dark:text-gray-400 text-lg font-medium">No exam results yet</p>
                <p className="text-sm text-gray-400 mt-1">Complete your first exam to see results here</p>
              </div>
            ) : (
              <div className="space-y-3 max-h-96 overflow-y-auto">
                {results.map((result) => (
                  <div key={result.id} className="group p-4 rounded-xl bg-white/50 dark:bg-[#1D1A17]/50 border border-[#E5E7EB]/50 dark:border-[#3B82F6]/30 hover:shadow-md transition-all cursor-pointer hover:bg-opacity-70">
                    <div className="flex items-start justify-between mb-2">
                      <h3 className="font-semibold text-gray-900 dark:text-gray-100 flex-1 pr-2 line-clamp-2">
                        {result.name}
                      </h3>
                      <span className={`px-3 py-1 rounded-full text-xs font-medium ${result.status === 'Pass'
                          ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300'
                          : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300'
                        }`}>
                        {result.status}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 mb-2">
                      <div className="w-full bg-gray-200 rounded-full h-2 dark:bg-[#3B82F6]/20">
                        <div
                          className={`bg-gradient-to-r from-${result.color}-500 to-${result.color}-600 h-2 rounded-full shadow-sm`}
                          style={{ width: `${(result.score / result.max_score) * 100}%` }}
                        />
                      </div>
                      <span className="text-sm font-bold text-gray-900 dark:text-gray-100 min-w-[60px]">
                        {result.score}/{result.max_score}
                      </span>
                    </div>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      {result.date || 'N/A'}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </section>

      {/* Download Report */}
      <div className="mt-12 p-6 bg-gradient-to-r from-purple-50 to-pink-50 dark:from-[#241025] dark:to-[#311B5A] rounded-2xl border border-[#6D28D9]/30 shadow-sm">
        <div className="flex flex-col md:flex-row items-center justify-between gap-4">
          <div>
            <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-100">
              Download Performance Report
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-300 mt-1">
              Get detailed analytics for {stats.totalExams} exams
            </p>
          </div>
          <button
            disabled={stats.totalExams === 0}
            className="px-6 py-3 bg-gradient-to-r from-[#6D28D9] to-[#EC4899] text-white rounded-xl font-semibold shadow-lg hover:shadow-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {stats.totalExams === 0 ? "No Results" : "Download PDF"}
          </button>
        </div>
      </div>
    </div>
  );
}
