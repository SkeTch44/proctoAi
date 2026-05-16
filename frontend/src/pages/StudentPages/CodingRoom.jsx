// src/pages/StudentPages/CodingRoom.jsx
// Full coding environment with Monaco editor, DSA problem panel, AI scoring
import React, { useState, useEffect, useRef, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { API_BASE, getAuthHeader } from "../../utils/apiConfig";

// Monaco editor — install: npm install @monaco-editor/react
let MonacoEditor;
try {
  MonacoEditor = require("@monaco-editor/react").default;
} catch {
  MonacoEditor = null; // Fallback to textarea if not installed
}

const LANGUAGES = [
  { id: "python", label: "Python 3", monacoId: "python" },
  { id: "javascript", label: "JavaScript", monacoId: "javascript" },
  { id: "typescript", label: "TypeScript", monacoId: "typescript" },
  { id: "java", label: "Java", monacoId: "java" },
  { id: "cpp", label: "C++", monacoId: "cpp" },
  { id: "c", label: "C", monacoId: "c" },
  { id: "go", label: "Go", monacoId: "go" },
  { id: "rust", label: "Rust", monacoId: "rust" },
  { id: "csharp", label: "C#", monacoId: "csharp" },
  { id: "kotlin", label: "Kotlin", monacoId: "kotlin" },
];

export default function CodingRoom() {
  const { problemId } = useParams();
  const navigate = useNavigate();

  const [problem, setProblem] = useState(null);
  const [language, setLanguage] = useState("python");
  const [code, setCode] = useState("");
  const [output, setOutput] = useState("");
  const [isRunning, setIsRunning] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const [aiRubric, setAiRubric] = useState(null);
  const [activeTab, setActiveTab] = useState("description");
  const [customInput, setCustomInput] = useState("");
  const [showCustomInput, setShowCustomInput] = useState(false);
  const [fontSize, setFontSize] = useState(14);

  // Cheat telemetry
  const pasteCountRef = useRef(0);
  const keystrokeTimesRef = useRef([]);
  const editorRef = useRef(null);

  // Proctoring (camera + cheat detection during coding)
  const [proctoringStatus, setProctoringStatus] = useState("initializing");
  const [proctoringAlerts, setProctoringAlerts] = useState([]);
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const frameIntervalRef = useRef(null);

  // Start camera + proctoring frame capture for coding session
  useEffect(() => {
    const startProctoring = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { width: 320, height: 240, facingMode: "user" },
          audio: true,
        });
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
        setProctoringStatus("active");

        // Capture frames every 12 seconds
        const jitter = Math.random() * 4000 - 2000;
        frameIntervalRef.current = setInterval(async () => {
          if (!videoRef.current || !canvasRef.current) return;
          const canvas = canvasRef.current;
          const ctx = canvas.getContext("2d");
          ctx.drawImage(videoRef.current, 0, 0, 320, 240);
          const frameData = canvas.toDataURL("image/jpeg", 0.5);

          try {
            const res = await fetch(`${API_BASE}/api/v1/proctoring/frame`, {
              method: "POST",
              headers: { "Content-Type": "application/json", ...getAuthHeader() },
              body: JSON.stringify({
                session_id: `coding_${problemId}`,
                session_kind: "coding",
                frame_data: frameData,
                timestamp: new Date().toISOString(),
              }),
            });
            const data = await res.json();
            if (data.suspicious) {
              setProctoringStatus("warning");
              setProctoringAlerts((prev) => [
                { type: data.alert_type, time: new Date().toLocaleTimeString() },
                ...prev.slice(0, 4),
              ]);
              setTimeout(() => setProctoringStatus("active"), 5000);
            }
          } catch {}
        }, 12000 + jitter);
      } catch (err) {
        console.error("Camera denied for coding proctoring:", err);
        setProctoringStatus("camera_error");
      }
    };
    startProctoring();
    return () => { if (frameIntervalRef.current) clearInterval(frameIntervalRef.current); };
  }, [problemId]);

  // Tab switch detection during coding
  useEffect(() => {
    const handleVisibility = async () => {
      if (document.hidden) {
        try {
          await fetch(`${API_BASE}/api/v1/proctoring/event`, {
            method: "POST",
            headers: { "Content-Type": "application/json", ...getAuthHeader() },
            body: JSON.stringify({
              session_id: `coding_${problemId}`,
              session_kind: "coding",
              event_type: "tab_switch",
              severity: "high",
              timestamp: new Date().toISOString(),
            }),
          });
        } catch {}
        setProctoringAlerts((prev) => [
          { type: "TAB_SWITCH", time: new Date().toLocaleTimeString() },
          ...prev.slice(0, 4),
        ]);
      }
    };
    document.addEventListener("visibilitychange", handleVisibility);
    return () => document.removeEventListener("visibilitychange", handleVisibility);
  }, [problemId]);

  // Fetch problem
  useEffect(() => {
    const fetchProblem = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/v1/coding/problems/${problemId}`, {
          headers: getAuthHeader(),
        });
        if (!res.ok) throw new Error("Problem not found");
        const data = await res.json();
        setProblem(data);
        if (data.starter_code?.[language]) {
          setCode(data.starter_code[language]);
        }
      } catch (err) {
        alert(err.message);
        navigate("/student/dashboard");
      }
    };
    fetchProblem();
  }, [problemId, navigate]);

  // Update starter code when language changes
  useEffect(() => {
    if (problem?.starter_code?.[language]) {
      setCode(problem.starter_code[language]);
    }
  }, [language, problem]);

  // Track paste events
  const handlePaste = useCallback(() => {
    pasteCountRef.current += 1;
  }, []);

  // Track keystrokes for typing speed
  const handleKeyDown = useCallback(() => {
    keystrokeTimesRef.current.push(Date.now());
    if (keystrokeTimesRef.current.length > 200) {
      keystrokeTimesRef.current = keystrokeTimesRef.current.slice(-200);
    }
  }, []);

  const getTypingSpeed = () => {
    const times = keystrokeTimesRef.current;
    if (times.length < 10) return null;
    const elapsed = (times[times.length - 1] - times[0]) / 1000 / 60;
    const words = times.length / 5;
    return elapsed > 0 ? Math.round(words / elapsed) : null;
  };

  // Monaco editor mount
  const handleEditorMount = (editor) => {
    editorRef.current = editor;
    editor.onDidPaste(() => { pasteCountRef.current += 1; });
    editor.onKeyDown(() => {
      keystrokeTimesRef.current.push(Date.now());
      if (keystrokeTimesRef.current.length > 200) {
        keystrokeTimesRef.current = keystrokeTimesRef.current.slice(-200);
      }
    });
  };

  // Run code
  const handleRun = async () => {
    setIsRunning(true);
    setActiveTab("output");
    setOutput("⏳ Running...");
    try {
      const res = await fetch(`${API_BASE}/api/v1/coding/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...getAuthHeader() },
        body: JSON.stringify({
          problem_id: parseInt(problemId),
          language,
          source_code: code,
          custom_input: showCustomInput ? customInput : null,
        }),
      });
      const data = await res.json();
      if (data.stderr) {
        setOutput(`❌ ERROR:\n${data.stderr}`);
      } else {
        setOutput(`✅ OUTPUT:\n${data.stdout || "(no output)"}\n\n⏱ Time: ${data.execution_time_ms || 0}ms | Status: ${data.status}`);
      }
    } catch (err) {
      setOutput(`❌ Error: ${err.message}`);
    } finally {
      setIsRunning(false);
    }
  };

  // Submit code
  const handleSubmit = async () => {
    if (!window.confirm("Submit your solution for grading? This will run against all test cases.")) return;
    setIsSubmitting(true);
    setActiveTab("result");
    setResult(null);
    setAiRubric(null);
    try {
      const res = await fetch(`${API_BASE}/api/v1/coding/submit`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...getAuthHeader() },
        body: JSON.stringify({
          problem_id: parseInt(problemId),
          language,
          source_code: code,
          paste_count: pasteCountRef.current,
          typing_speed_wpm: getTypingSpeed(),
        }),
      });
      const data = await res.json();

      if (data.submission_id) {
        let attempts = 0;
        const poll = setInterval(async () => {
          attempts++;
          try {
            const statusRes = await fetch(
              `${API_BASE}/api/v1/coding/submissions/${data.submission_id}`,
              { headers: getAuthHeader() }
            );
            const statusData = await statusRes.json();
            if (statusData.status !== "pending" && statusData.status !== "running") {
              clearInterval(poll);
              setResult(statusData);
              // Fetch AI rubric
              if (statusData.ai_rubric) {
                setAiRubric(statusData.ai_rubric);
              }
              setIsSubmitting(false);
            }
          } catch { /* retry */ }
          if (attempts > 60) {
            clearInterval(poll);
            setResult({ status: "timeout", message: "Judging timed out" });
            setIsSubmitting(false);
          }
        }, 1000);
      } else {
        setResult(data);
        setIsSubmitting(false);
      }
    } catch (err) {
      setResult({ status: "error", message: err.message });
      setIsSubmitting(false);
    }
  };

  // Reset code
  const handleReset = () => {
    if (window.confirm("Reset to starter code?")) {
      setCode(problem?.starter_code?.[language] || "");
    }
  };

  if (!problem) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-900">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  const monacoLang = LANGUAGES.find(l => l.id === language)?.monacoId || "plaintext";

  return (
    <div className="h-screen flex flex-col bg-[#1e1e1e] text-white overflow-hidden">
      {/* Hidden proctoring elements */}
      <video ref={videoRef} autoPlay muted playsInline className="hidden" />
      <canvas ref={canvasRef} width="320" height="240" className="hidden" />

      {/* Top bar */}
      <div className="flex items-center justify-between px-4 py-2 bg-[#252526] border-b border-[#3c3c3c]">
        <div className="flex items-center gap-3">
          <h1 className="text-sm font-bold truncate max-w-xs">{problem.title}</h1>
          <span className={`px-2 py-0.5 rounded text-xs font-bold uppercase ${
            problem.difficulty === "easy" ? "bg-green-700 text-green-100" :
            problem.difficulty === "medium" ? "bg-yellow-700 text-yellow-100" :
            problem.difficulty === "hard" ? "bg-red-700 text-red-100" :
            "bg-purple-700 text-purple-100"
          }`}>
            {problem.difficulty}
          </span>
          <span className="text-xs text-gray-400">⏱ {problem.time_limit_ms}ms | 💾 {Math.round(problem.memory_limit_kb/1024)}MB</span>
        </div>
        <div className="flex items-center gap-2">
          {/* Proctoring status */}
          <div className="flex items-center gap-1 mr-2">
            <div className={`w-2 h-2 rounded-full animate-pulse ${
              proctoringStatus === "active" ? "bg-green-400" :
              proctoringStatus === "warning" ? "bg-yellow-400" : "bg-red-400"
            }`} />
            <span className="text-[10px] text-gray-400">
              {proctoringStatus === "active" ? "🛡️" : "⚠️"}
            </span>
          </div>
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            className="bg-[#3c3c3c] border border-[#555] rounded px-2 py-1 text-xs"
          >
            {LANGUAGES.map((l) => (
              <option key={l.id} value={l.id}>{l.label}</option>
            ))}
          </select>
          <select
            value={fontSize}
            onChange={(e) => setFontSize(Number(e.target.value))}
            className="bg-[#3c3c3c] border border-[#555] rounded px-2 py-1 text-xs w-16"
          >
            {[12, 13, 14, 15, 16, 18, 20].map(s => (
              <option key={s} value={s}>{s}px</option>
            ))}
          </select>
          <button onClick={handleReset} className="px-3 py-1 bg-gray-600 hover:bg-gray-500 rounded text-xs">↺ Reset</button>
          <button
            onClick={handleRun}
            disabled={isRunning}
            className="px-4 py-1.5 bg-green-600 hover:bg-green-700 rounded text-xs font-bold disabled:opacity-50"
          >
            {isRunning ? "⏳ Running..." : "▶ Run"}
          </button>
          <button
            onClick={handleSubmit}
            disabled={isSubmitting}
            className="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 rounded text-xs font-bold disabled:opacity-50"
          >
            {isSubmitting ? "⏳ Judging..." : "🚀 Submit"}
          </button>
        </div>
      </div>

      {/* Main split */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left panel: Problem + Output + Result */}
        <div className="w-[38%] flex flex-col border-r border-[#3c3c3c]">
          {/* Tabs */}
          <div className="flex border-b border-[#3c3c3c] bg-[#252526]">
            {["description", "output", "result"].map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-4 py-2 text-xs font-medium capitalize border-b-2 transition ${
                  activeTab === tab
                    ? "border-blue-500 text-white bg-[#1e1e1e]"
                    : "border-transparent text-gray-400 hover:text-white"
                }`}
              >
                {tab === "result" && aiRubric ? "📊 Result" : tab}
              </button>
            ))}
          </div>

          {/* Tab content */}
          <div className="flex-1 overflow-y-auto p-4">
            {activeTab === "description" && (
              <div className="space-y-4">
                <div className="text-sm text-gray-200 whitespace-pre-wrap leading-relaxed">
                  {problem.description}
                </div>
                {problem.constraints && (
                  <div className="bg-[#2d2d2d] rounded-lg p-3">
                    <h4 className="text-xs font-bold text-gray-300 mb-1">Constraints</h4>
                    <p className="text-xs text-gray-400">{problem.constraints}</p>
                  </div>
                )}
                {problem.sample_cases?.length > 0 && (
                  <div>
                    <h4 className="text-xs font-bold text-gray-300 mb-2">Examples</h4>
                    {problem.sample_cases.map((tc, i) => (
                      <div key={i} className="mb-3 bg-[#2d2d2d] rounded-lg p-3 text-xs">
                        <div className="text-gray-400 mb-1">Input:</div>
                        <pre className="text-green-300 mb-2 font-mono">{tc.input}</pre>
                        <div className="text-gray-400 mb-1">Expected:</div>
                        <pre className="text-blue-300 font-mono">{tc.expected_output}</pre>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {activeTab === "output" && (
              <div className="space-y-3">
                {/* Custom input toggle */}
                <div className="flex items-center gap-2">
                  <label className="flex items-center gap-1.5 text-xs text-gray-400 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={showCustomInput}
                      onChange={(e) => setShowCustomInput(e.target.checked)}
                      className="rounded"
                    />
                    Custom Input
                  </label>
                </div>
                {showCustomInput && (
                  <textarea
                    value={customInput}
                    onChange={(e) => setCustomInput(e.target.value)}
                    placeholder="Enter custom input..."
                    className="w-full h-20 bg-[#2d2d2d] text-gray-200 text-xs font-mono p-2 rounded border border-[#555] resize-none outline-none"
                  />
                )}
                <pre className="text-xs text-gray-300 whitespace-pre-wrap font-mono bg-[#1a1a1a] rounded-lg p-3 min-h-[150px] border border-[#333]">
                  {output || "▶ Run your code to see output here."}
                </pre>
              </div>
            )}

            {activeTab === "result" && (
              <div className="space-y-4">
                {isSubmitting && (
                  <div className="text-center py-8">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-3"></div>
                    <p className="text-gray-400 text-sm">Running against all test cases + AI review...</p>
                  </div>
                )}
                {result && !isSubmitting && (
                  <>
                    {/* Test results */}
                    <div className={`p-4 rounded-lg border ${
                      result.status === "accepted"
                        ? "bg-green-900/20 border-green-700"
                        : "bg-red-900/20 border-red-700"
                    }`}>
                      <div className="text-base font-bold mb-1">
                        {result.status === "accepted" ? "✅ All Tests Passed" : `❌ ${result.status?.replace("_", " ")}`}
                      </div>
                      <div className="text-sm text-gray-300">
                        Tests: {result.tests_passed}/{result.tests_total} | Score: {result.score}%
                      </div>
                      {result.execution_time_ms && (
                        <div className="text-xs text-gray-400 mt-1">⏱ {result.execution_time_ms}ms</div>
                      )}
                    </div>

                    {/* AI Rubric */}
                    {aiRubric && (
                      <div className="bg-[#2d2d2d] rounded-lg p-4 border border-[#444]">
                        <h4 className="text-sm font-bold text-blue-300 mb-3">🤖 AI Code Review (Score: {aiRubric.total_score}/100)</h4>
                        <div className="space-y-2">
                          {aiRubric.correctness && (
                            <ScoreBar label="Correctness" score={aiRubric.correctness.score} max={40} feedback={aiRubric.correctness.feedback} />
                          )}
                          {aiRubric.code_quality && (
                            <ScoreBar label="Code Quality" score={aiRubric.code_quality.score} max={25} feedback={aiRubric.code_quality.feedback} />
                          )}
                          {aiRubric.complexity_analysis && (
                            <ScoreBar label="Complexity" score={aiRubric.complexity_analysis.score} max={20}
                              feedback={`${aiRubric.complexity_analysis.time_complexity} / ${aiRubric.complexity_analysis.space_complexity} — ${aiRubric.complexity_analysis.feedback}`} />
                          )}
                          {aiRubric.style_readability && (
                            <ScoreBar label="Style" score={aiRubric.style_readability.score} max={15} feedback={aiRubric.style_readability.feedback} />
                          )}
                        </div>
                        {aiRubric.overall_feedback && (
                          <p className="mt-3 text-xs text-gray-300 italic border-t border-[#444] pt-2">
                            {aiRubric.overall_feedback}
                          </p>
                        )}
                        {aiRubric.suggestions?.length > 0 && (
                          <div className="mt-2">
                            <p className="text-xs text-gray-400 font-bold">Suggestions:</p>
                            <ul className="list-disc list-inside text-xs text-gray-400 mt-1">
                              {aiRubric.suggestions.map((s, i) => <li key={i}>{s}</li>)}
                            </ul>
                          </div>
                        )}
                      </div>
                    )}

                    <p className="text-xs text-gray-500 text-center">
                      Score sent to examiner for final review.
                    </p>
                  </>
                )}
                {!result && !isSubmitting && (
                  <p className="text-gray-500 text-sm text-center py-8">Submit your code to see results and AI review.</p>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Right panel: Code editor */}
        <div className="flex-1 flex flex-col">
          {MonacoEditor ? (
            <MonacoEditor
              height="100%"
              language={monacoLang}
              theme="vs-dark"
              value={code}
              onChange={(val) => setCode(val || "")}
              onMount={handleEditorMount}
              options={{
                fontSize,
                minimap: { enabled: false },
                scrollBeyondLastLine: false,
                wordWrap: "on",
                tabSize: 4,
                automaticLayout: true,
                suggestOnTriggerCharacters: true,
                quickSuggestions: true,
                parameterHints: { enabled: true },
                bracketPairColorization: { enabled: true },
                lineNumbers: "on",
                renderLineHighlight: "all",
                cursorBlinking: "smooth",
                smoothScrolling: true,
              }}
            />
          ) : (
            <textarea
              value={code}
              onChange={(e) => setCode(e.target.value)}
              onPaste={handlePaste}
              onKeyDown={handleKeyDown}
              spellCheck={false}
              className="flex-1 bg-[#1e1e1e] text-green-300 font-mono p-4 resize-none outline-none border-none"
              style={{ fontSize: `${fontSize}px`, lineHeight: "1.6" }}
              placeholder="// Write your solution here..."
            />
          )}
        </div>
      </div>
    </div>
  );
}

// Score bar component
function ScoreBar({ label, score, max, feedback }) {
  const pct = Math.round((score / max) * 100);
  const color = pct >= 80 ? "bg-green-500" : pct >= 50 ? "bg-yellow-500" : "bg-red-500";
  return (
    <div>
      <div className="flex justify-between text-xs mb-0.5">
        <span className="text-gray-300">{label}</span>
        <span className="text-gray-400">{score}/{max}</span>
      </div>
      <div className="h-1.5 bg-[#444] rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full transition-all`} style={{ width: `${pct}%` }} />
      </div>
      {feedback && <p className="text-[10px] text-gray-500 mt-0.5">{feedback}</p>}
    </div>
  );
}
