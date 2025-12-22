import React, { useState } from "react";

export default function TestCreator() {
  const [title, setTitle] = useState("");
  const [duration, setDuration] = useState("");
  const [passingScore, setPassingScore] = useState("");

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

  const handleCreateTest = () => {
    console.log({
      title,
      duration,
      passingScore,
      permissions,
    });
    // API call here
  };

  return (
    <div className="max-w-2xl mx-auto p-6 space-y-8">
      {/* Header */}
      <div className="text-center">
        <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
          Create Test
        </h2>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Configure test details and proctoring permissions
        </p>
      </div>

      {/* Form Card */}
      <div className="bg-white dark:bg-[#171A1D] border border-[#D1D5DB] dark:border-[#374151] rounded-2xl p-8 shadow-xl space-y-6">
        {/* Test Title */}
        <div>
          <label className="block text-sm font-semibold text-gray-700 dark:text-gray-100 mb-2">
            Test Title
          </label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Frontend Assessment"
            className="w-full px-4 py-3 rounded-xl border-2 border-[#D1D5DB] dark:border-[#374151]
                       bg-[#F9FAFB] dark:bg-[#1A1D21]
                       text-gray-900 dark:text-gray-100
                       focus:border-[#6D28D9] dark:focus:border-[#10B981]
                       focus:ring-2 focus:ring-[#6D28D9]/20 dark:focus:ring-[#10B981]/20
                       transition-all"
          />
        </div>

        {/* Duration */}
        <div>
          <label className="block text-sm font-semibold text-gray-700 dark:text-gray-100 mb-2">
            Duration (minutes)
          </label>
          <input
            type="number"
            min="1"
            value={duration}
            onChange={(e) => setDuration(e.target.value)}
            placeholder="e.g. 60"
            className="w-full px-4 py-3 rounded-xl border-2 border-[#D1D5DB] dark:border-[#374151]
                       bg-[#F9FAFB] dark:bg-[#1A1D21]
                       text-gray-900 dark:text-gray-100
                       focus:border-[#6D28D9] dark:focus:border-[#10B981]
                       focus:ring-2 focus:ring-[#6D28D9]/20 dark:focus:ring-[#10B981]/20
                       transition-all"
          />
        </div>

        {/* Passing Score */}
        <div>
          <label className="block text-sm font-semibold text-gray-700 dark:text-gray-100 mb-2">
            Passing Score (%)
          </label>
          <input
            type="number"
            min="0"
            max="100"
            value={passingScore}
            onChange={(e) => setPassingScore(e.target.value)}
            placeholder="e.g. 60"
            className="w-full px-4 py-3 rounded-xl border-2 border-[#D1D5DB] dark:border-[#374151]
                       bg-[#F9FAFB] dark:bg-[#1A1D21]
                       text-gray-900 dark:text-gray-100
                       focus:border-[#6D28D9] dark:focus:border-[#10B981]
                       focus:ring-2 focus:ring-[#6D28D9]/20 dark:focus:ring-[#10B981]/20
                       transition-all"
          />
        </div>

        {/* Permissions */}
        <div>
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-100 mb-3">
            Proctoring & Permissions
          </h3>

          <div className="space-y-3">
            {[
              { key: "camera", label: "Camera Access" },
              { key: "mic", label: "Microphone Access" },
              { key: "speaker", label: "Speaker Access" },
              { key: "tabSwitch", label: "Restrict Tab Switching" },
              { key: "aiMonitoring", label: "AI Monitoring Enabled" },
            ].map(({ key, label }) => (
              <label
                key={key}
                className="flex items-center gap-3 cursor-pointer text-sm text-gray-700 dark:text-gray-200"
              >
                <input
                  type="checkbox"
                  checked={permissions[key]}
                  onChange={() => handlePermissionChange(key)}
                  className="h-5 w-5 rounded border-gray-300 dark:border-gray-600
                             text-[#6D28D9] dark:text-[#10B981]
                             focus:ring-[#6D28D9]/30 dark:focus:ring-[#10B981]/30"
                />
                {label}
              </label>
            ))}
          </div>
        </div>
      </div>

      {/* Create Button */}
      <div className="flex justify-center mt-6">
        <div className="bg-gradient-to-r from-purple-700 via-teal-500 to-white dark:from-green-500 dark:via-blue-500 dark:to-green-400 p-[3px] rounded-xl">
          <button
            onClick={handleCreateTest}
            disabled={!title || !duration || !passingScore}
            className="
              px-10 py-4 rounded-2xl text-lg font-semibold shadow-xl
              bg-blue-500 hover:bg-blue-600 text-white
              dark:bg-blue-700 dark:hover:bg-blue-500 dark:text-gray-100
              focus:ring-4 focus:ring-[#6D28D9]/30 dark:focus:ring-[#10B981]/30
              transform hover:scale-[1.02] active:scale-[0.98]
              disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none
              transition-all duration-200
            "
          >
            Create Test
          </button>
        </div>
      </div>
    </div>
  );
}
