import React, { useState } from "react";
import QuestionSelector from "../../components/QuestionSelector";
import { useNavigate } from "react-router-dom";

const API_BASE = process.env.REACT_APP_API_URL || "http://localhost:5000";

export default function TestCreator() {
  const navigate = useNavigate();
  const [title, setTitle] = useState("");
  const [duration, setDuration] = useState("");
  const [passingScore, setPassingScore] = useState("");
  const [selectedQuestions, setSelectedQuestions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [permissions, setPermissions] = useState({
    camera: false,
    mic: false,
    speaker: false,
    tabSwitch: false,
    aiMonitoring: false,
  });

  const handlePermissionChange = (key) => {
    setPermissions((prev) => ({
      ...prev,
      [key]: !prev[key],
    }));
  };

  const handleCreateTest = async () => {
    setLoading(true);
    setError(null);
    try {
      const token = localStorage.getItem("token");
      const response = await fetch(`${API_BASE}/api/exams`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          title,
          description: `Passing Score: ${passingScore}%`,
          duration: parseInt(duration) * 60, // convert minutes to seconds
          questions: selectedQuestions, // Array of IDs
          permissions,
        }),
      });

      const data = await response.json();
      if (!response.ok) throw new Error(data.message || "Failed to create test");

      alert(`Test Created Successfully! ID: ${data.exam_id}`);
      navigate("/admin/dashboard");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-8">
      {/* Header */}
      <div className="text-center">
        <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
          Create Test
        </h2>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Configure test details, proctoring permissions, and select questions
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        {/* Left: Test Details & Permissions */}
        <div className="bg-white dark:bg-[#171A1D] border border-[#D1D5DB] dark:border-[#374151] rounded-2xl p-8 shadow-xl space-y-6">
          <div>
            <label className="block text-sm font-semibold text-gray-700 dark:text-gray-100 mb-2">
              Test Title
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Frontend Assessment"
              className="w-full px-4 py-3 rounded-xl border-2 dark:border-[#374151] bg-[#F9FAFB] dark:bg-[#1A1D21] text-gray-900 dark:text-gray-100"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-semibold text-gray-700 dark:text-gray-100 mb-2">
                Duration (min)
              </label>
              <input
                type="number"
                value={duration}
                onChange={(e) => setDuration(e.target.value)}
                className="w-full px-4 py-3 rounded-xl border-2 dark:border-[#374151] bg-[#F9FAFB] dark:bg-[#1A1D21] text-gray-900 dark:text-gray-100"
              />
            </div>
            <div>
              <label className="block text-sm font-semibold text-gray-700 dark:text-gray-100 mb-2">
                Passing (%)
              </label>
              <input
                type="number"
                value={passingScore}
                onChange={(e) => setPassingScore(e.target.value)}
                className="w-full px-4 py-3 rounded-xl border-2 dark:border-[#374151] bg-[#F9FAFB] dark:bg-[#1A1D21] text-gray-900 dark:text-gray-100"
              />
            </div>
          </div>

          <div>
            <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-100 mb-3">
              Proctoring & Permissions
            </h3>
            <div className="space-y-3">
              {[
                { key: "camera", label: "Camera Access" },
                { key: "mic", label: "Microphone Access" },
                { key: "tabSwitch", label: "Restrict Tab Switching" },
                { key: "aiMonitoring", label: "AI Monitoring Enabled" },
              ].map(({ key, label }) => (
                <label key={key} className="flex items-center gap-3 cursor-pointer text-sm text-gray-700 dark:text-gray-200">
                  <input
                    type="checkbox"
                    checked={permissions[key]}
                    onChange={() => handlePermissionChange(key)}
                    className="h-5 w-5 rounded border-gray-300 dark:border-gray-600 text-blue-600"
                  />
                  {label}
                </label>
              ))}
            </div>
          </div>
          
          {error && <div className="text-red-500 text-sm">{error}</div>}
        </div>

        {/* Right: Question Selection */}
        <div className="bg-white dark:bg-[#171A1D] border border-[#D1D5DB] dark:border-[#374151] rounded-2xl p-6 shadow-xl overflow-hidden flex flex-col">
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-100 mb-4 flex justify-between">
            Pick Questions 
            <span className="text-blue-600">{selectedQuestions.length} Selected</span>
          </h3>
          <div className="flex-1 overflow-y-auto max-h-[400px]">
            <QuestionSelector 
              selectedIds={selectedQuestions} 
              onSelectionChange={setSelectedQuestions} 
            />
          </div>
        </div>
      </div>

      {/* Create Button */}
      <div className="flex justify-center mt-6">
        <button
          onClick={handleCreateTest}
          disabled={loading || !title || !duration || selectedQuestions.length === 0}
          className="px-12 py-4 bg-blue-600 hover:bg-blue-700 text-white rounded-2xl font-bold text-lg shadow-xl transform transition-all hover:scale-105 disabled:opacity-50"
        >
          {loading ? "Creating..." : "Create & Launch Test"}
        </button>
      </div>
    </div>
  );
}
