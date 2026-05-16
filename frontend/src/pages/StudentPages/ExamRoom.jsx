// src/pages/StudentPages/ExamRoom.jsx
import React, { useState, useEffect, useRef, useCallback } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getToken } from "../../utils/authStorage";
import { API_BASE, getAuthHeader } from "../../utils/apiConfig";
import { getSocket, onConnectionChange } from "../../services/socket";

export default function ExamRoom() {
  const navigate = useNavigate();
  const { examId } = useParams();
  const videoRef = useRef(null);
  const canvasRef = useRef(null);

  // States
  const [exam, setExam] = useState(null);
  const [timeLeft, setTimeLeft] = useState(5400); // 90 min
  const [proctoringStatus, setProctoringStatus] = useState("initializing");
  const [isFullScreen, setIsFullScreen] = useState(false);
  const [currentQuestion, setCurrentQuestion] = useState(1);
  const [answers, setAnswers] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const sessionId = localStorage.getItem("currentSessionId");

  const wsRef = useRef(null);
  const audioContextRef = useRef(null);
  const audioAnalyzerRef = useRef(null);

  const fetchExam = useCallback(async () => {
    const token = getToken();
    try {
      const res = await fetch(`${API_BASE}/api/exams/${examId}`, {
        headers: getAuthHeader()
      });
      const data = await res.json();
      
      // Handle locked exam — show the locked UI and poll every 5s
      if (res.status === 403 && data.unlocked === false) {
        setExam((prev) => prev?.unlocked === false ? prev : { title: data.title || "Exam", questions: [], duration: 0, unlocked: false });
        return;
      }
      if (!res.ok) throw new Error(data.message);

      setExam(data);
      // Backend stores exam.duration in SECONDS. Use it as-is.
      setTimeLeft(Number(data.duration) || 0);
    } catch (err) {
      alert(err.message || "Exam not found");
      navigate("/student/start-exam");
    }
  }, [examId, navigate]);

  // Poll for exam unlock every 5 seconds when locked
  useEffect(() => {
    if (exam && exam.unlocked === false) {
      const pollInterval = setInterval(() => {
        fetchExam();
      }, 5000);
      return () => clearInterval(pollInterval);
    }
  }, [exam?.unlocked, fetchExam]);

  const captureFrame = useCallback(async () => {
    if (!videoRef.current || proctoringStatus !== "active") return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(videoRef.current, 0, 0, 320, 240);

    const frameData = canvas.toDataURL("image/jpeg", 0.6);
    
    // Capture audio data
    let audioData = null;
    if (audioAnalyzerRef.current) {
      const dataArray = new Uint8Array(audioAnalyzerRef.current.frequencyBinCount);
      audioAnalyzerRef.current.getByteFrequencyData(dataArray);
      audioData = Array.from(dataArray).slice(0, 64); // Send first 64 frequency bins
    }
    
    const token = getToken();

    try {
      await fetch(`${API_BASE}/api/proctoring_frame`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...getAuthHeader()
        },
        body: JSON.stringify({
          session_id: sessionId,
          frame_data: frameData,
          audio_data: audioData,
          timestamp: new Date().toISOString()
        })
      });
    } catch (err) {
      console.error("Frame upload failed:", err);
    }
  }, [sessionId, proctoringStatus]);

  const logViolation = useCallback(async (type, severity) => {
    const token = getToken();
      await fetch(`${API_BASE}/api/proctoring_event`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...getAuthHeader()
        },
      body: JSON.stringify({
        session_id: sessionId,
        event_type: type,
        severity,
        timestamp: new Date().toISOString()
      })
    });
  }, [sessionId]);

  const handlePageExit = useCallback((e) => {
    logViolation("page_exit", "critical");
    e.preventDefault();
    e.returnValue = "Exam in progress. Are you sure?";
  }, [logViolation]);

  const handleExamEnd = useCallback(async () => {
    if (isSubmitting) return;
    setIsSubmitting(true);

    const token = getToken();
    try {
      await fetch(`${API_BASE}/api/end_exam`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...getAuthHeader()
        },
        body: JSON.stringify({
          session_id: sessionId,
          answers
        })
      });
      navigate("/student/results");
    } catch (err) {
      alert("Failed to submit exam");
    }
  }, [isSubmitting, sessionId, answers, navigate]);

  // 1. Fetch real exam data
  useEffect(() => {
    fetchExam();
  }, [fetchExam]);

  // 2. Real camera + audio + frame capture
  useEffect(() => {
    const startCamera = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { width: 320, height: 240, facingMode: "user" },
          audio: true
        });
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          setProctoringStatus("active");
        }

        // Initialize Web Audio API for audio analysis
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const analyzer = audioContext.createAnalyser();
        const source = audioContext.createMediaStreamSource(stream);
        source.connect(analyzer);
        analyzer.fftSize = 2048;
        
        audioContextRef.current = audioContext;
        audioAnalyzerRef.current = analyzer;
        console.log("Audio context initialized");

        // Send frames every 10 seconds (with +/- 2s jitter to prevent thundering herd)
        const jitter = Math.random() * 4000 - 2000; // -2s to +2s
        const intervalTime = 10000 + jitter;

        const interval = setInterval(captureFrame, intervalTime);
        return () => clearInterval(interval);
      } catch (err) {
        setProctoringStatus("camera_error");
        console.error("Camera/audio access denied:", err);
      }
    };
    startCamera();
  }, [captureFrame]);


  // 3. Socket.IO for live proctoring
  useEffect(() => {
    const socket = getSocket();

    // Join session room
    const joinSession = () => {
      if (sessionId) {
        socket.emit('join_session', { session_id: sessionId });

        const token = getToken();
        let username = "Student";
        let userId = 0;
        try {
          const payload = JSON.parse(atob(token.split('.')[1]));
          username = payload.username || "Student";
          userId = payload.user_id || 0;
        } catch(e) {}
        
        socket.emit('join_exam_room', { 
            exam_id: examId, 
            student_id: userId, 
            student_name: username 
        });
      }
    };

    // Initial join
    joinSession();

    // Listen for proctoring alerts
    socket.on('proctoring_alert', (data) => {
      console.log('[ExamRoom] Proctoring alert received:', data);
      if (data.session_id === sessionId) {
        setProctoringStatus('warning');
        alert(`Proctoring Alert: ${data.details || data.alert_type}`);
      }
    });

    // Listen for exam_started broadcast from admin
    socket.on('exam_started', (data) => {
      console.log('[ExamRoom] Exam started signal received:', data);
      if (data.exam_id.toString() === examId) {
        setExam(prev => ({ ...prev, unlocked: true }));
        setProctoringStatus('active');
      }
    });

    // Listen for status messages
    socket.on('status', (data) => {
      console.log('[ExamRoom] Status:', data.message);
    });

    // Handle connection state changes
    const unsubscribe = onConnectionChange((status, data) => {
      console.log('[ExamRoom] Connection status:', status, data);

      if (status === 'connected' || status === 'reconnected') {
        setProctoringStatus('active');
        // Rejoin session after reconnection
        joinSession();
      } else if (status === 'disconnected') {
        setProctoringStatus('camera_error');
      } else if (status === 'reconnecting') {
        setProctoringStatus('initializing');
      }
    });

    wsRef.current = socket;

    return () => {
      socket.off('proctoring_alert');
      socket.off('exam_started');
      socket.off('status');
      unsubscribe();
    };
  }, [sessionId, examId]);


  // 4. Fullscreen + Anti-cheat Detection
  useEffect(() => {
    const handleVisibility = () => {
      if (document.hidden) {
        logViolation("tab_switch", "high");
      }
      if (!document.fullscreenElement) {
        setIsFullScreen(false);
      }
    };

    const handleFullscreen = () => {
      setIsFullScreen(!!document.fullscreenElement);
      if (!document.fullscreenElement) {
        logViolation("fullscreen_exit", "medium");
      }
    };

    document.addEventListener("visibilitychange", handleVisibility);
    document.addEventListener("fullscreenchange", handleFullscreen);
    window.addEventListener("beforeunload", handlePageExit);

    return () => {
      document.removeEventListener("visibilitychange", handleVisibility);
      document.removeEventListener("fullscreenchange", handleFullscreen);
      window.removeEventListener("beforeunload", handlePageExit);
    };
  }, [logViolation, handlePageExit]);

  // 5. Timer
  useEffect(() => {
    let interval;
    if (timeLeft > 0 && exam) {
      interval = setInterval(() => {
        setTimeLeft((prev) => {
          if (prev <= 1) {
            handleExamEnd();
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [timeLeft, exam, handleExamEnd]);

  // 6. Answer handling
  const selectAnswer = (questionId, option) => {
    setAnswers(prev => ({
      ...prev,
      [questionId]: option
    }));
  };

  // 7. Submit exam

  const toggleFullScreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().catch(() => { });
    } else {
      document.exitFullscreen();
    }
  };

  const formatTime = (seconds) => {
    const total = Math.max(0, Math.floor(seconds || 0));
    const hrs = Math.floor(total / 3600);
    const mins = Math.floor((total % 3600) / 60);
    const secs = total % 60;
    const pad = (n) => n.toString().padStart(2, '0');
    return hrs > 0 ? `${pad(hrs)}:${pad(mins)}:${pad(secs)}` : `${pad(mins)}:${pad(secs)}`;
  };

  // 8. Questions and navigation
  const questions = exam?.questions || [];
  const currentQ = questions[currentQuestion - 1];

  // Normalise a question object to a single shape the UI can rely on.
  const normaliseQuestion = (q) => {
    if (!q) return null;
    const text = q.question_text || q.question || q.text || '';

    // Options can arrive as {A: "..", B: ".."} OR ["..", "..", ..] OR
    // nested inside question_data. Flatten to [{letter, value}].
    let rawOptions =
      q.options ||
      (q.question_data && q.question_data.options) ||
      [];
    let normalisedOptions = [];
    if (Array.isArray(rawOptions)) {
      normalisedOptions = rawOptions.map((v, i) => ({
        letter: String.fromCharCode(65 + i),
        value: v,
      }));
    } else if (rawOptions && typeof rawOptions === 'object') {
      normalisedOptions = Object.entries(rawOptions)
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([letter, value]) => ({ letter, value }));
    }

    const id = q.id || q.uuid || q.question_text || q.question;
    return { id, text, options: normalisedOptions };
  };

  const nQ = normaliseQuestion(currentQ);

  if (!exam || !sessionId) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-[#F3F4F6] to-white">
        <div className="text-center p-8">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#3B82F6] mx-auto mb-6"></div>
          <h2 className="text-2xl font-bold mb-2">Loading Exam Room</h2>
        </div>
      </div>
    );
  }

  return (
    <div className={`min-h-screen bg-[#F3F4F6] dark:bg-[#011627] transition-all duration-300 ${isFullScreen ? 'p-2' : 'p-4 md:p-6 lg:p-8'}`}>

      {/* Header + Camera */}
      <div className="mb-6 rounded-2xl shadow-xl">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">

          {/* Header */}
          <div className="lg:col-span-10 bg-gradient-to-r from-[#1E3A8A] via-[#3730A3] to-[#1E40AF] p-4 lg:p-6 text-white rounded-l-2xl">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-xl font-bold">{exam.title}</h1>
                <div className="flex gap-2 text-xs mt-1">
                  <span>Q{currentQuestion}/{questions.length}</span>
                  <span>{exam.totalMarks} marks</span>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <div className="text-2xl font-mono font-bold bg-white/20 px-4 py-2 rounded-xl">
                  {formatTime(timeLeft)}
                </div>
                <button onClick={toggleFullScreen} className="p-2 rounded-xl bg-white/20">
                  {isFullScreen ? "📱" : "📺"}
                </button>
              </div>
            </div>
          </div>

          {/* Live Camera */}
          <div className="lg:col-span-2 bg-black/30 p-2 lg:p-4 rounded-r-2xl">
            <div className="relative">
              <video
                ref={videoRef}
                autoPlay
                muted
                className="w-full h-24 lg:h-32 rounded-xl object-cover border-2 border-white/30 shadow-xl"
              />
              <div className={`absolute top-1 right-1 w-3 h-3 rounded-full border-2 border-white/50 animate-pulse ${proctoringStatus === "active" ? "bg-green-400" :
                proctoringStatus === "warning" ? "bg-yellow-400" : "bg-red-400"
                }`} />
            </div>
          </div>
        </div>
      </div>

      {/* Hidden canvas for frame capture */}
      <canvas ref={canvasRef} width="320" height="240" className="hidden" />

      {/* Questions + Answers */}
      {!exam.unlocked ? (
        <div className="bg-white/95 dark:bg-[#0f1724]/95 backdrop-blur-xl rounded-2xl shadow-xl border p-16 text-center mt-8">
            <div className="mb-8 flex justify-center">
                <div className="w-20 h-20 bg-blue-100 dark:bg-blue-900/30 rounded-full flex items-center justify-center animate-bounce">
                    <span className="text-4xl text-blue-600 dark:text-blue-400">🔒</span>
                </div>
            </div>
            <h2 className="text-4xl font-black text-gray-900 dark:text-gray-100 mb-6 tracking-tight">Exam is Locked</h2>
            <p className="text-xl text-gray-600 dark:text-gray-400 max-w-2xl mx-auto leading-relaxed">
                Please wait for your <span className="font-bold text-blue-600 dark:text-blue-400">AI Proctor Dashboard</span> to unlock and start the exam for everyone.
            </p>
            <div className="mt-12 inline-block px-8 py-4 border-2 border-dashed border-gray-200 dark:border-gray-700 rounded-3xl">
                <p className="text-sm font-medium text-gray-500 flex items-center gap-2">
                   <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse"></div>
                   Checking for start signal from proctor...
                </p>
            </div>
        </div>
      ) : nQ ? (
        <div className="bg-white/95 dark:bg-[#0f1724]/95 backdrop-blur-xl rounded-2xl shadow-xl border overflow-hidden p-8 text-center mt-8">
            <h2 className="text-2xl font-bold mb-8 text-gray-800 dark:text-gray-100">{nQ.text}</h2>
            <div className="space-y-4 max-w-3xl mx-auto mb-12">
               {nQ.options.map(({ letter, value }) => {
                 const isSelected = answers[nQ.id] === letter;
                 return (
                   <button
                     key={letter}
                     onClick={() => selectAnswer(nQ.id, letter)}
                     className={`w-full p-5 rounded-xl border-2 text-lg font-medium transition-all transform hover:scale-[1.01] text-left flex gap-4 items-center ${
                       isSelected
                         ? 'border-blue-500 bg-blue-50 text-blue-800 dark:bg-blue-900/40 dark:text-blue-100'
                         : 'border-gray-200 text-gray-700 dark:border-gray-700 dark:text-gray-300 hover:border-blue-300'
                     }`}
                   >
                     <span className={`flex-none w-10 h-10 rounded-full flex items-center justify-center font-bold ${
                       isSelected ? 'bg-blue-600 text-white' : 'bg-gray-100 dark:bg-gray-700'
                     }`}>
                       {letter}
                     </span>
                     <span className="flex-1">{value}</span>
                   </button>
                 );
               })}
               {nQ.options.length === 0 && (
                 <p className="text-gray-500 italic">This question has no options.</p>
               )}
            </div>
            
            <div className="flex justify-between items-center px-4">
              <div className="flex gap-2">
                <button onClick={() => setCurrentQuestion(Math.max(1, currentQuestion - 1))} disabled={currentQuestion === 1} className="px-6 py-2 rounded-lg bg-gray-100 dark:bg-gray-800 disabled:opacity-50 font-bold">Prev</button>
                <button onClick={() => setCurrentQuestion(Math.min(questions.length, currentQuestion + 1))} disabled={currentQuestion === questions.length} className="px-6 py-2 rounded-lg bg-gray-100 dark:bg-gray-800 disabled:opacity-50 font-bold">Next</button>
              </div>
              <button
                onClick={handleExamEnd}
                disabled={isSubmitting}
                className="px-8 py-3 bg-gradient-to-r from-red-500 to-red-600 text-white rounded-xl font-bold shadow-xl hover:shadow-2xl transition-all hover:-translate-y-1 transform disabled:opacity-50"
              >
                {isSubmitting ? "Submitting..." : `Submit Exam (${Object.keys(answers).length}/${questions.length})`}
              </button>
            </div>
        </div>
      ) : null}
    </div>
  );
}
