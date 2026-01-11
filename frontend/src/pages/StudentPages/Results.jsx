// src/pages/student/Results.jsx
import React from "react";

const examResults = [
  { id: 1, name: "Data Structures Midterm", score: 92, maxScore: 100, date: "Dec 15, 2025", status: "Pass", color: "green" },
  { id: 2, name: "Web Dev Quiz", score: 78, maxScore: 100, date: "Dec 10, 2025", status: "Pass", color: "blue" },
  { id: 3, name: "Database Assignment", score: 85, maxScore: 100, date: "Dec 5, 2025", status: "Pass", color: "purple" },
];

export default function Results() {
  return (
      <div className="max-w-6xl mx-auto">
          <header className="mb-8 text-center lg:text-left">
        <h1 className="text-3xl font-black bg-gradient-to-r from-gray-900 via-blue-900 to-purple-900 bg-clip-text text-transparent  dark:from-blue-400 dark:via-purple-400 dark:to-pink-400">
           Exam Results
        </h1>
        <p className="text-sm text-gray-600 dark:text-gray-300 max-w-2xl">
          View your performance across all completed exams
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
                  <p className="text-3xl font-bold text-emerald-600 dark:text-emerald-400">92%</p>
                  <p className="text-sm text-gray-600 dark:text-gray-300">Avg Score</p>
                </div>
                <div>
                  <p className="text-3xl font-bold text-gray-900 dark:text-gray-100">3/3</p>
                  <p className="text-sm text-gray-600 dark:text-gray-300">Exams Passed</p>
                </div>
              </div>
            </div>

            {/* Performance Trend */}
            <div className="p-6 bg-white dark:bg-[#0f1724] rounded-xl shadow border border-[#E5E7EB] dark:border-[#3B82F6]/40">
              <h3 className="text-lg font-semibold mb-4">Score Trend</h3>
              <div className="h-48 bg-gradient-to-r from-gray-50 to-gray-100 dark:from-[#1D1A17] dark:to-[#0f1724] rounded-xl flex items-end justify-around p-4">
                {[78, 85, 92].map((score, idx) => (
                  <div key={idx} className="flex flex-col items-center">
                    <div className="w-12 h-48 bg-gradient-to-t from-[#10B981] to-[#34D399] rounded-lg shadow-sm mt-auto" style={{ height: `${score }px` }} />
                    <span className="text-xs mt-2">{score}%</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Recent Results */}
          <div className="space-y-6">
            <div className="p-6 bg-white dark:bg-[#0f1724] rounded-xl shadow border border-[#E5E7EB] dark:border-[#3B82F6]/40">
              <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-4">
                Recent Results
              </h2>
              <div className="space-y-3">
                {examResults.map((result) => (
                  <div key={result.id} className="group p-4 rounded-xl bg-white/50 dark:bg-[#1D1A17]/50 border border-[#E5E7EB]/50 dark:border-[#3B82F6]/30 hover:shadow-md transition-all">
                    <div className="flex items-start justify-between mb-2">
                      <h3 className="font-semibold text-gray-900 dark:text-gray-100 flex-1">
                        {result.name}
                      </h3>
                      <span className={`px-3 py-1 rounded-full text-xs font-medium bg-${result.color}-100 text-${result.color}-700 dark:bg-${result.color}-900/30`}>
                        {result.status}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 mb-2">
                      <div className="w-full bg-gray-200 rounded-full h-2 dark:bg-[#3B82F6]/20">
                        <div 
                          className={`bg-gradient-to-r from-${result.color}-500 to-${result.color}-600 h-2 rounded-full shadow-sm`}
                          style={{ width: `${(result.score / result.maxScore) * 100}%` }}
                        />
                      </div>
                      <span className="text-sm font-bold text-gray-900 dark:text-gray-100">
                        {result.score}/{result.maxScore}
                      </span>
                    </div>
                    <p className="text-xs text-gray-500 dark:text-gray-400">{result.date}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* Download Report */}
        <div className="mt-8 p-6 bg-gradient-to-r from-purple-50 to-pink-50 dark:from-[#241025] dark:to-[#311B5A] rounded-2xl border border-[#6D28D9]/30 shadow-sm">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div>
              <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-100">
                Download Performance Report
              </h3>
              <p className="text-sm text-gray-600 dark:text-gray-300 mt-1">
                Get detailed analytics and feedback for all your exams
              </p>
            </div>
            <button className="px-6 py-3 bg-gradient-to-r from-[#6D28D9] to-[#EC4899] text-white rounded-xl font-semibold shadow-lg hover:shadow-xl transition-all">
              Download PDF
            </button>
          </div>
        </div>
      </div>
  );
}
