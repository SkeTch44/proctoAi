// src/pages/AdminPages/AIQuestionGenerator.jsx
import React, { useState, useRef } from "react";
import { generateQuestionsAI, generateQuestionsRAG, scanQuestionsPDF } from "../../services/questionApi";

const MODES = {
  AI: 'ai',
  RAG: 'rag',
  SCAN: 'scan'
};

const MODE_INFO = {
  [MODES.AI]: {
    title: '🤖 Pure AI',
    description: 'Generate questions from topic using AI',
    icon: '🤖'
  },
  [MODES.RAG]: {
    title: '📄 RAG + Doc',
    description: 'Upload document → AI generates questions',
    icon: '📄'
  },
  [MODES.SCAN]: {
    title: '📋 PDF Scan',
    description: 'Extract existing questions from PDF',
    icon: '📋'
  }
};

export default function AIQuestionGenerator() {
  const [activeMode, setActiveMode] = useState(MODES.AI);
  const [topic, setTopic] = useState("");
  const [questionType, setQuestionType] = useState("mcq");
  const [noOfQuestions, setNoOfQuestions] = useState("10");
  const [level, setLevel] = useState("medium");
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [showExamModal, setShowExamModal] = useState(false);
  const [examTitle, setExamTitle] = useState("");
  const [examDuration, setExamDuration] = useState(60);
  const [creatingExam, setCreatingExam] = useState(false);
  const fileInputRef = useRef(null);

  // Request notification permission on mount
  React.useEffect(() => {
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission();
    }

    // Restore persisted state from localStorage
    const savedState = localStorage.getItem('questionGeneratorState');
    if (savedState) {
      try {
        const { savedTopic, savedMode, savedResult, savedFile } = JSON.parse(savedState);
        if (savedTopic) setTopic(savedTopic);
        if (savedMode) setActiveMode(savedMode);
        if (savedResult) setResult(savedResult);
        if (savedFile && (savedMode === MODES.RAG || savedMode === MODES.SCAN)) {
          // Restore file metadata (actual file can't be persisted)
          setFile({ name: savedFile.name, size: savedFile.size, type: savedFile.type });
        }
      } catch (e) {
        console.error('Failed to restore state:', e);
      }
    }
  }, []);

  // Persist state to localStorage whenever it changes
  React.useEffect(() => {
    const stateToSave = {
      savedTopic: topic,
      savedMode: activeMode,
      savedResult: result,
      savedFile: file ? { name: file.name, size: file.size, type: file.type } : null
    };
    localStorage.setItem('questionGeneratorState', JSON.stringify(stateToSave));
  }, [topic, activeMode, result, file]);

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      setFile(selectedFile);
      setError(null);
    }
  };

  const handleGenerate = async () => {
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      let response;

      if (activeMode === MODES.AI) {
        if (!topic) {
          throw new Error('Topic is required');
        }
        response = await generateQuestionsAI({
          topic,
          count: parseInt(noOfQuestions),
          difficulty: level,
          types: [questionType]
        });
      }
      else if (activeMode === MODES.RAG) {
        if (!file) {
          throw new Error('Please upload a document');
        }
        response = await generateQuestionsRAG(file, {
          topic: topic || 'Document Content',
          count: parseInt(noOfQuestions),
          difficulty: level,
          types: [questionType]
        });
      }
      else if (activeMode === MODES.SCAN) {
        if (!file) {
          throw new Error('Please upload a question PDF');
        }
        response = await scanQuestionsPDF(file, {
          topic: topic || 'Extracted Questions'
        });
      }

      setResult(response);

      // Show browser notification
      if ('Notification' in window && Notification.permission === 'granted') {
        new Notification('✅ Questions Generated!', {
          body: `${response.count || response.questions?.length || 0} questions ready for "${topic || 'your exam'}"`,
          icon: '/logo192.png',
          tag: 'question-generation'
        });
      }

      // Play success sound (optional)
      try {
        const audio = new Audio('data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmwhBSuBzvLZiTYIGGS57OihUBELTKXh8bllHAU2jdXzzn0vBSh+zPLaizsKGGe67OmiUhELTKXh8bllHAU2jdXzzn0vBSh+zPLaizsKGGe67OmiUhELTKXh8bllHAU2jdXzzn0vBSh+zPLaizsKGGe67OmiUhELTKXh8bllHAU2jdXzzn0vBQ==');
        audio.volume = 0.3;
        audio.play().catch(() => { });
      } catch (e) { }
    } catch (err) {
      setError(err.message);

      // Show error notification
      if ('Notification' in window && Notification.permission === 'granted') {
        new Notification('❌ Generation Failed', {
          body: err.message,
          icon: '/logo192.png',
          tag: 'question-generation-error'
        });
      }
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setTopic("");
    setFile(null);
    setResult(null);
    setError(null);
    setShowExamModal(false);
    setExamTitle("");
    setExamDuration(60);
    localStorage.removeItem('questionGeneratorState'); // Clear persisted state
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  // Handle topic change - clear results if topic changed
  const handleTopicChange = (newTopic) => {
    if (newTopic !== topic && result) {
      // Topic changed, clear previous results
      setResult(null);
      setError(null);
    }
    setTopic(newTopic);
  };

  const handleCreateExam = async () => {
    console.log("📝 handleCreateExam called");

    if (!examTitle.trim()) {
      setError('Exam title is required');
      return;
    }

    setCreatingExam(true);
    setError(null);

    try {
      const token = localStorage.getItem('token');
      console.log("🔑 Token found:", !!token);

      const payload = {
        title: examTitle,
        description: `Generated via ${activeMode.toUpperCase()} mode - ${topic || 'Document'}`,
        questions: result.questions, // Send as object/array, NOT stringified
        duration: examDuration
      };

      console.log("🚀 Sending exam creation request:", payload);

      const response = await fetch('http://localhost:5000/api/exams', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(payload)
      });

      console.log("📨 Response status:", response.status);

      if (!response.ok) {
        const errText = await response.text();
        console.error("❌ Request failed:", errText);
        throw new Error(`Failed to create exam: ${response.statusText} - ${errText}`);
      }

      const data = await response.json();
      console.log("✅ Exam created:", data);

      alert(`✅ Exam "${examTitle}" created successfully! (ID: ${data.exam_id})`);
      resetForm();
    } catch (err) {
      console.error("💥 Error creating exam:", err);
      setError(err.message);
    } finally {
      setCreatingExam(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="text-center">
        <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
          AI Question Generator
        </h2>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Generate or extract questions with 3 powerful modes
        </p>
      </div>

      {/* Mode Tabs */}
      <div className="flex gap-2 justify-center">
        {Object.entries(MODE_INFO).map(([mode, info]) => (
          <button
            key={mode}
            onClick={() => { setActiveMode(mode); resetForm(); }}
            className={`px-4 py-3 rounded-xl font-medium transition-all ${activeMode === mode
              ? 'bg-blue-600 text-white shadow-lg scale-105'
              : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
              }`}
          >
            <span className="text-xl mr-2">{info.icon}</span>
            {info.title}
          </button>
        ))}
      </div>

      {/* Mode Description */}
      <div className="text-center text-sm text-gray-500 dark:text-gray-400">
        {MODE_INFO[activeMode].description}
      </div>

      {/* Form Card */}
      <div className="bg-white dark:bg-[#171A1D] border border-gray-200 dark:border-gray-700 rounded-2xl p-6 shadow-xl">
        <div className="space-y-5">

          {/* Topic Input - Always shown */}
          <div>
            <label className="block text-sm font-semibold text-gray-700 dark:text-gray-100 mb-2">
              {activeMode === MODES.SCAN ? 'Topic/Category Name' : 'Topic'}
            </label>
            <input
              type="text"
              value={topic}
              onChange={(e) => handleTopicChange(e.target.value)}
              placeholder={activeMode === MODES.AI ? "e.g. Machine Learning Basics" : "e.g. Physics Chapter 3"}
              className="w-full px-4 py-3 rounded-xl border-2 border-gray-200 dark:border-gray-600 
                         bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-gray-100
                         focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all"
            />
          </div>

          {/* File Upload - For RAG and SCAN modes */}
          {(activeMode === MODES.RAG || activeMode === MODES.SCAN) && (
            <div>
              <label className="block text-sm font-semibold text-gray-700 dark:text-gray-100 mb-2">
                Upload {activeMode === MODES.SCAN ? 'Question PDF' : 'Document (PDF/DOCX)'}
              </label>
              <div className="flex items-center gap-3">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,.docx,.doc"
                  onChange={handleFileChange}
                  className="flex-1 px-4 py-3 rounded-xl border-2 border-dashed border-gray-300 dark:border-gray-600 
                             bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-gray-100
                             file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0
                             file:bg-blue-50 file:text-blue-700 dark:file:bg-blue-900 dark:file:text-blue-200
                             hover:border-blue-400 transition-all cursor-pointer"
                />
              </div>
              {file && (
                <p className="mt-2 text-sm text-green-600 dark:text-green-400">
                  ✓ {file.name} selected
                </p>
              )}
            </div>
          )}

          {/* Question Type & Count - For AI and RAG modes */}
          {activeMode !== MODES.SCAN && (
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-semibold text-gray-700 dark:text-gray-100 mb-2">
                  Question Type
                </label>
                <select
                  value={questionType}
                  onChange={(e) => setQuestionType(e.target.value)}
                  className="w-full px-4 py-3 rounded-xl border-2 border-gray-200 dark:border-gray-600 
                             bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-gray-100
                             focus:border-blue-500 transition-all"
                >
                  <option value="mcq">Multiple Choice (MCQ)</option>
                  <option value="short_answer">Short Answer</option>
                  <option value="essay">Essay / Long Answer</option>
                  <option value="true_false">True/False</option>
                </select>
              </div>

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
                  className="w-full px-4 py-3 rounded-xl border-2 border-gray-200 dark:border-gray-600 
                             bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-gray-100
                             focus:border-blue-500 transition-all"
                />
              </div>
            </div>
          )}

          {/* Difficulty Level - For AI and RAG modes */}
          {activeMode !== MODES.SCAN && (
            <div>
              <label className="block text-sm font-semibold text-gray-700 dark:text-gray-100 mb-2">
                Difficulty Level
              </label>
              <div className="flex gap-3">
                {['easy', 'medium', 'hard', 'expert'].map((lv) => (
                  <button
                    key={lv}
                    onClick={() => setLevel(lv)}
                    className={`flex-1 py-2 rounded-lg font-medium capitalize transition-all ${level === lv
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200'
                      }`}
                  >
                    {lv}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-xl p-4 text-red-700 dark:text-red-300">
          ⚠️ {error}
        </div>
      )}

      {/* Generate Button */}
      <div className="flex justify-center">
        <button
          onClick={handleGenerate}
          disabled={loading || (activeMode === MODES.AI && !topic) || ((activeMode === MODES.RAG || activeMode === MODES.SCAN) && !file)}
          className={`px-8 py-4 rounded-xl text-lg font-semibold shadow-lg transition-all
            ${loading
              ? 'bg-gray-400 cursor-wait'
              : 'bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700'}
            text-white disabled:opacity-50 disabled:cursor-not-allowed
            transform hover:scale-[1.02] active:scale-[0.98]`}
        >
          {loading ? (
            <span className="flex items-center gap-2">
              <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Generating...
            </span>
          ) : activeMode === MODES.SCAN ? 'Extract Questions' : 'Generate Questions'}
        </button>
      </div>

      {/* Results Display */}
      {result && (
        <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-bold text-green-800 dark:text-green-200">
              ✅ {result.message || 'Questions Generated!'}
            </h3>
            <span className="bg-green-600 text-white px-3 py-1 rounded-full text-sm">
              {result.count || result.questions?.length || 0} questions
            </span>
          </div>

          {/* Preview first few questions */}
          <div className="space-y-3 max-h-60 overflow-y-auto">
            {result.questions?.slice(0, 5).map((q, i) => (
              <div key={i} className="bg-white dark:bg-gray-800 p-3 rounded-lg border border-gray-200 dark:border-gray-600">
                <p className="font-medium text-gray-800 dark:text-gray-200">
                  {i + 1}. {q.question_text || q.question || 'Question text'}
                </p>
                {q.question_data?.options && (
                  <div className="mt-2 pl-4 text-sm text-gray-600 dark:text-gray-400">
                    {Object.entries(q.question_data.options).map(([key, val]) => (
                      <div key={key}>{key}) {val}</div>
                    ))}
                  </div>
                )}
              </div>
            ))}
            {result.questions?.length > 5 && (
              <p className="text-gray-500 text-center">
                ... and {result.questions.length - 5} more questions
              </p>
            )}
          </div>

          {/* Create Exam Button */}
          <div className="mt-4 flex gap-3">
            <button
              onClick={() => setShowExamModal(true)}
              className="flex-1 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white px-6 py-3 rounded-xl font-semibold shadow-lg transition-all transform hover:scale-[1.02]"
            >
              📝 Create Exam from These Questions
            </button>
            <button
              onClick={resetForm}
              className="bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 px-6 py-3 rounded-xl font-semibold transition-all"
            >
              Generate New
            </button>
          </div>
        </div>
      )}

      {/* Create Exam Modal */}
      {showExamModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 max-w-md w-full shadow-2xl">
            <h3 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
              Create Exam
            </h3>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-semibold text-gray-700 dark:text-gray-200 mb-2">
                  Exam Title *
                </label>
                <input
                  type="text"
                  value={examTitle}
                  onChange={(e) => setExamTitle(e.target.value)}
                  placeholder="e.g., Physics Midterm - Faraday's Law"
                  className="w-full px-4 py-3 rounded-xl border-2 border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:border-blue-500 transition-all"
                />
              </div>

              <div>
                <label className="block text-sm font-semibold text-gray-700 dark:text-gray-200 mb-2">
                  Duration (minutes)
                </label>
                <input
                  type="number"
                  value={examDuration}
                  onChange={(e) => setExamDuration(parseInt(e.target.value))}
                  min="5"
                  max="180"
                  className="w-full px-4 py-3 rounded-xl border-2 border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:border-blue-500 transition-all"
                />
              </div>

              <div className="bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-800 rounded-lg p-3 text-sm text-blue-700 dark:text-blue-300">
                ℹ️ This exam will include {result.questions?.length || 0} questions with proctoring enabled (camera, microphone, screen monitoring).
              </div>
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={handleCreateExam}
                disabled={creatingExam || !examTitle.trim()}
                className="flex-1 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white px-6 py-3 rounded-xl font-semibold transition-all"
              >
                {creatingExam ? 'Creating...' : 'Create Exam'}
              </button>
              <button
                onClick={() => setShowExamModal(false)}
                disabled={creatingExam}
                className="bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 px-6 py-3 rounded-xl font-semibold transition-all"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
