// src/pages/StudentPages/ExamRoom.jsx
import React, { useState, useEffect, useRef, useCallback } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getToken } from "../../utils/authStorage";
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
  const [showInstructions, setShowInstructions] = useState(false);
  const [answers, setAnswers] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [sessionId, setSessionId] = useState(localStorage.getItem("currentSessionId"));

  const dropdownRef = useRef(null);
  const wsRef = useRef(null);

  // 1. Fetch real exam data
  useEffect(() => {
    fetchExam();
  }, [examId]);

  const fetchExam = async () => {
    const token = getToken();
    try {
      const res = await fetch(`http://127.0.0.1:5000/api/exams/${examId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.message);

      setExam(data);
      setTimeLeft(data.duration * 60); // Convert minutes to seconds
    } catch (err) {
      alert(err.message || "Exam not found");
      navigate("/student/start-exam");
    }
  };

  // 2. Real camera + frame capture
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

        // Send frames every 10 seconds (with +/- 2s jitter to prevent thundering herd)
        const jitter = Math.random() * 4000 - 2000; // -2s to +2s
        const intervalTime = 10000 + jitter;

        const interval = setInterval(captureFrame, intervalTime);
        return () => clearInterval(interval);
      } catch (err) {
        setProctoringStatus("camera_error");
        console.error("Camera access denied:", err);
      }
    };
    startCamera();
  }, []);

  const captureFrame = useCallback(async () => {
    if (!videoRef.current || proctoringStatus !== "active") return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(videoRef.current, 0, 0, 320, 240);

    const frameData = canvas.toDataURL("image/jpeg", 0.6);
    const token = getToken();

    try {
      await fetch("http://127.0.0.1:5000/api/proctoring_frame", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          session_id: sessionId,
          frame_data: frameData
        })
      });
    } catch (err) {
      console.error("Frame upload failed:", err);
    }
  }, [sessionId, proctoringStatus]);

  // 3. Socket.IO for live proctoring
  useEffect(() => {
    const socket = getSocket();

    // Join session room
    const joinSession = () => {
      if (sessionId) {
        socket.emit('join_session', { session_id: sessionId });
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
      socket.off('status');
      unsubscribe();
    };
  }, [sessionId]);

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
  }, []);

  const handlePageExit = (e) => {
    logViolation("page_exit", "critical");
    e.preventDefault();
    e.returnValue = "Exam in progress. Are you sure?";
  };

  const logViolation = async (type, severity) => {
    const token = getToken();
    await fetch("http://127.0.0.1:5000/api/proctoring_event", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`
      },
      body: JSON.stringify({
        session_id: sessionId,
        event_type: type,
        severity
      })
    });
  };

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
  }, [timeLeft, exam]);

  // 6. Answer handling
  const selectAnswer = (questionId, option) => {
    setAnswers(prev => ({
      ...prev,
      [questionId]: option
    }));
  };

  // 7. Submit exam
  const handleExamEnd = async () => {
    if (isSubmitting) return;
    setIsSubmitting(true);

    const token = getToken();
    try {
      await fetch("http://127.0.0.1:5000/api/end_exam", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
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
  };

  const toggleFullScreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().catch(() => { });
    } else {
      document.exitFullscreen();
    }
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  // Mock questions (replace with exam.questions)
  const questions = exam?.questions || [{
    id: 1,
    text: "What is the time complexity of binary search?",
    options: ["O(n)", "O(log n)", "O(n log n)", "O(n²)"]
  }];

  const currentQ = questions[currentQuestion - 1] || questions[0];

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
            {/* Your existing header JSX */}
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-xl font-bold">{exam.title}</h1>
                <div className="flex gap-2 text-xs mt-1">
                  <span>Q{currentQuestion}/{exam.questions}</span>
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

      {/* Questions + Answers - Your existing JSX */}
      <div className="bg-white/95 dark:bg-[#0f1724]/95 backdrop-blur-xl rounded-2xl shadow-xl border overflow-hidden">
        {/* Question header, options, navigation - keep your existing */}

        {/* Submit button in navigation */}
        <button
          onClick={handleExamEnd}
          disabled={isSubmitting}
          className="ml-4 px-8 py-3 bg-gradient-to-r from-red-500 to-red-600 text-white rounded-xl font-bold shadow-xl hover:shadow-2xl transition-all disabled:opacity-50"
        >
          {isSubmitting ? "Submitting..." : `End Exam (${Object.keys(answers).length}/${exam.questions} answered)`}
        </button>
      </div>
    </div>
  );
}
