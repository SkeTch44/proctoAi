// src/pages/AdminPages/AIQuestionGenerator.jsx
import React, { useState } from "react";

export default function AIQuestionGenerator() {
  const [questionType, setQuestionType] = useState("");
  const [noOfQuestions, setNoOfQuestions] = useState("");
  const [level, setLevel] = useState("");

  const handleGenerate = () => {
    console.log({ questionType, noOfQuestions, level });
    // Generate questions logic here
  };

  return (
    <div className="max-w-2xl mx-auto p-6 space-y-8">
      {/* Header */}
      <div className="text-center">
        <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
          AI Question Generator
        </h2>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Generate smart questions instantly with AI
        </p>
      </div>

      {/* Form Card */}
      <div className="bg-white dark:bg-[#171A1D] border border-[#D1D5DB] dark:border-[#374151] rounded-2xl p-8 shadow-xl">
        <div className="space-y-6">
          {/* Question Type */}
          <div>
            <label className="block text-sm font-semibold text-gray-700 dark:text-gray-100 mb-2">
              Question Type
            </label>
            <select
              value={questionType}
              onChange={(e) => setQuestionType(e.target.value)}
              className="w-full px-4 py-3 rounded-xl border-2 border-[#D1D5DB] dark:border-[#374151] 
                         bg-[#F9FAFB] dark:bg-[#1A1D21] 
                         text-gray-900 dark:text-gray-100
                         focus:border-[#6D28D9] dark:focus:border-[#10B981] 
                         focus:ring-2 focus:ring-[#6D28D9]/20 dark:focus:ring-[#10B981]/20
                         transition-all"
            >
              <option value="">Select type...</option>
              <option value="mcq">Multiple Choice (MCQ)</option>
              <option value="short">Short Answer</option>
              <option value="long">Long Answer</option>
              <option value="truefalse">True/False</option>
            </select>
          </div>

          {/* Number of Questions */}
          <div>
            <label className="block text-sm font-semibold text-gray-700 dark:text-gray-100 mb-2">
              Number of Questions
            </label>
            <input
              type="number"
              min="1"
              max="50"
              value={noOfQuestions}
              onChange={(e) => setNoOfQuestions(e.target.value)}
              placeholder="e.g. 10"
              className="w-full px-4 py-3 rounded-xl border-2 border-[#D1D5DB] dark:border-[#374151] 
                         bg-[#F9FAFB] dark:bg-[#1A1D21] 
                         text-gray-900 dark:text-gray-100
                         focus:border-[#6D28D9] dark:focus:border-[#10B981] 
                         focus:ring-2 focus:ring-[#6D28D9]/20 dark:focus:ring-[#10B981]/20
                         transition-all"
            />
          </div>

          {/* Difficulty Level */}
          <div>
            <label className="block text-sm font-semibold text-gray-700 dark:text-gray-100 mb-2">
              Difficulty Level
            </label>
            <select
              value={level}
              onChange={(e) => setLevel(e.target.value)}
              className="w-full px-4 py-3 rounded-xl border-2 border-[#D1D5DB] dark:border-[#374151] 
                         bg-[#F9FAFB] dark:bg-[#1A1D21] 
                         text-gray-900 dark:text-gray-100
                         focus:border-[#6D28D9] dark:focus:border-[#10B981] 
                         focus:ring-2 focus:ring-[#6D28D9]/20 dark:focus:ring-[#10B981]/20
                         transition-all"
            >
              <option value="">Select level...</option>
              <option value="easy">Easy</option>
              <option value="medium">Medium</option>
              <option value="hard">Hard</option>
            </select>
          </div>
        </div>
      </div>

      {/* Generate Button */}
      <div className="flex justify-center mt-6">
        <div className="bg-gradient-to-r from-purple-700 via-teal-500 to-white dark:from-green-500 dark:via-blue-500 dark:to-green-400 p-[3px] rounded-xl">
          <button
            onClick={handleGenerate}
            disabled={!questionType || !noOfQuestions || !level}
            className="
        w-full max-w-md px-8 py-4 rounded-2xl text-lg font-semibold shadow-xl
        bg-blue-500 hover:bg-blue-600 text-white
        dark:bg-blue-700 dark:hover:bg-blue-500 dark:text-gray-100
        focus:ring-4 focus:ring-[#6D28D9]/30 dark:focus:ring-[#10B981]/30
        transform hover:scale-[1.02] active:scale-[0.98]
        disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none
        transition-all duration-200
      "
          >
            Generate Questions
          </button>
        </div>
      </div>
    </div>
  );
}
