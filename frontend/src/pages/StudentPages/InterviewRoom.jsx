// src/pages/StudentPages/InterviewRoom.jsx
import React, { useState, useEffect, useRef, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { API_BASE, getAuthHeader } from "../../utils/apiConfig";

/**
 * InterviewRoom — 1:1 video interview with AI cheat detection.
 *
 * Proctoring pipeline (same as ExamRoom):
 *   - Captures frames every 10s from local video
 *   - Sends to proctoring-svc /api/v1/proctoring/frame
 *   - CheatDetector runs: YOLO (face/phone/book) + gaze + audio
 *   - Alerts shown in real-time
 */

export default function InterviewRoom() {
  const { sessionId } = useParams();
  const navigate = useNavigate();

  const [session, setSession] = useState(null);
  const [connected, setConnected] = useState(false);
  const [notes, setNotes] = useState("");
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState("");
  const [elapsedTime, setElapsedTime] = useState(0);
  const [proctoringStatus, setProctoringStatus] = useState("initializing");
  const [alerts, setAlerts] = useState([]);

  const localVideoRef = useRef(null);
  const remoteVideoRef = useRef(null);
  const canvasRef = useRef(null);
  const timerRef = useRef(null);
  const frameIntervalRef = useRef(null);

  // Fetch session details
  useEffect(() => {
    const fetchSession = async () => {
      try {
        // Join the interview session
        await fetch(`${API_BASE}/api/interviews/${sessionId}/join`, {
          method: "POST",
          headers: { "Content-Type": "application/json", ...getAuthHeader() },
        }).catch(() => {});

        const res = await fetch(`${API_BASE}/api/interviews/${sessionId}`, {
          headers: getAuthHeader(),
        });
        const data = await res.json();
        setSession(data);
      } catch (err) {
        // Fallback: allow room to load even without backend session
        setSession({ title: "Interview Session", id: sessionId });
      }
    };
    fetchSession();
  }, [sessionId, navigate]);

  // Timer
  useEffect(() => {
    timerRef.current = setInterval(() => {
      setElapsedTime((prev) => prev + 1);
    }, 1000);
    return () => clearInterval(timerRef.current);
  }, []);

  // Start camera + proctoring frame capture
  useEffect(() => {
    const startCamera = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { width: 640, height: 480, facingMode: "user" },
          audio: true,
        });
        if (localVideoRef.current) {
          localVideoRef.current.srcObject = stream;
        }
        setConnected(true);
        setProctoringStatus("active");

        // Start frame capture loop (every 10 seconds)
        const jitter = Math.random() * 4000 - 2000;
        frameIntervalRef.current = setInterval(() => captureAndAnalyze(), 10000 + jitter);
      } catch (err) {
        console.error("Camera access denied:", err);
        setProctoringStatus("camera_error");
      }
    };
    startCamera();

    return () => {
      if (frameIntervalRef.current) clearInterval(frameIntervalRef.current);
    };
  }, []);

  // Capture frame and send to proctoring-svc
  const captureAndAnalyze = useCallback(async () => {
    if (!localVideoRef.current || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(localVideoRef.current, 0, 0, 320, 240);
    const frameData = canvas.toDataURL("image/jpeg", 0.6);

    try {
      const res = await fetch(`${API_BASE}/api/v1/proctoring/frame`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...getAuthHeader() },
        body: JSON.stringify({
          session_id: sessionId,
          session_kind: "interview",
          frame_data: frameData,
          timestamp: new Date().toISOString(),
        }),
      });
      const data = await res.json();

      if (data.suspicious) {
        setProctoringStatus("warning");
        setAlerts((prev) => [
          { type: data.alert_type, verdict: data.verdict, time: formatTime(elapsedTime) },
          ...prev.slice(0, 9),
        ]);
        // Reset warning after 5s
        setTimeout(() => setProctoringStatus("active"), 5000);
      }
    } catch (err) {
      console.error("Proctoring frame failed:", err);
    }
  }, [sessionId, elapsedTime]);

  // Tab switch detection
  useEffect(() => {
    const handleVisibility = async () => {
      if (document.hidden) {
        try {
          await fetch(`${API_BASE}/api/v1/proctoring/event`, {
            method: "POST",
            headers: { "Content-Type": "application/json", ...getAuthHeader() },
            body: JSON.stringify({
              session_id: sessionId,
              session_kind: "interview",
              event_type: "tab_switch",
              severity: "high",
              timestamp: new Date().toISOString(),
            }),
          });
        } catch {}
        setAlerts((prev) => [
          { type: "TAB_SWITCH", verdict: "HIGH", time: formatTime(elapsedTime) },
          ...prev.slice(0, 9),
        ]);
      }
    };
    document.addEventListener("visibilitychange", handleVisibility);
    return () => document.removeEventListener("visibilitychange", handleVisibility);
  }, [sessionId, elapsedTime]);

  const formatTime = (seconds) => {
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    const pad = (n) => n.toString().padStart(2, "0");
    return `${pad(hrs)}:${pad(mins)}:${pad(secs)}`;
  };

  const sendMessage = () => {
    if (!newMessage.trim()) return;
    setMessages((prev) => [
      ...prev,
      { sender: "You", text: newMessage, time: formatTime(elapsedTime) },
    ]);
    setNewMessage("");
  };

  const endInterview = async () => {
    if (!window.confirm("End this interview session?")) return;
    try {
      await fetch(`${API_BASE}/api/interviews/${sessionId}/end`, {
        method: "POST",
        headers: getAuthHeader(),
      });
    } catch (err) {
      console.error(err);
    }
    navigate("/student/dashboard");
  };

  if (!session) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-900">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-gray-900 text-white overflow-hidden">
      {/* Hidden canvas for frame capture */}
      <canvas ref={canvasRef} width="320" height="240" className="hidden" />

      {/* Header */}
      <div className="flex items-center justify-between px-6 py-3 bg-gray-800 border-b border-gray-700">
        <div>
          <h1 className="text-lg font-bold">{session.title || "Interview Session"}</h1>
          <p className="text-xs text-gray-400">Session: {sessionId}</p>
        </div>
        <div className="flex items-center gap-4">
          {/* Proctoring indicator */}
          <div className="flex items-center gap-2">
            <div className={`w-2.5 h-2.5 rounded-full animate-pulse ${
              proctoringStatus === "active" ? "bg-green-400" :
              proctoringStatus === "warning" ? "bg-yellow-400" :
              "bg-red-400"
            }`} />
            <span className="text-xs text-gray-300">
              {proctoringStatus === "active" ? "AI Proctoring Active" :
               proctoringStatus === "warning" ? "⚠️ Alert" :
               "Camera Error"}
            </span>
          </div>
          <div className="text-xl font-mono bg-gray-700 px-4 py-1.5 rounded-lg">
            {formatTime(elapsedTime)}
          </div>
          <button
            onClick={endInterview}
            className="px-4 py-2 bg-red-600 hover:bg-red-700 rounded-lg text-sm font-bold"
          >
            End Interview
          </button>
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Video panel */}
        <div className="w-3/5 flex flex-col p-4 gap-4">
          {/* Remote video (interviewer) */}
          <div className="flex-1 bg-gray-800 rounded-xl overflow-hidden relative">
            <video
              ref={remoteVideoRef}
              autoPlay
              playsInline
              className="w-full h-full object-cover"
            />
            {!remoteVideoRef.current?.srcObject && (
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="text-center">
                  <div className="text-4xl mb-2">👤</div>
                  <p className="text-gray-400">Waiting for interviewer...</p>
                </div>
              </div>
            )}
            <div className="absolute bottom-3 left-3 bg-black/60 px-3 py-1 rounded-lg text-sm">
              Interviewer
            </div>
          </div>

          {/* Local video (self) */}
          <div className="h-40 bg-gray-800 rounded-xl overflow-hidden relative">
            <video
              ref={localVideoRef}
              autoPlay
              muted
              playsInline
              className="w-full h-full object-cover"
            />
            <div className="absolute bottom-2 left-2 bg-black/60 px-2 py-0.5 rounded text-xs">
              You
            </div>
            {/* Proctoring status badge */}
            <div className={`absolute top-2 right-2 px-2 py-0.5 rounded text-[10px] font-bold ${
              proctoringStatus === "active" ? "bg-green-600" :
              proctoringStatus === "warning" ? "bg-yellow-600" :
              "bg-red-600"
            }`}>
              {proctoringStatus === "active" ? "🛡️ AI Active" : "⚠️ Alert"}
            </div>
          </div>
        </div>

        {/* Right panel: Alerts + Notes + Chat */}
        <div className="w-2/5 flex flex-col border-l border-gray-700">
          {/* Proctoring Alerts */}
          {alerts.length > 0 && (
            <div className="p-3 border-b border-gray-700 max-h-32 overflow-y-auto">
              <h3 className="text-xs font-bold text-red-400 mb-1">🚨 Proctoring Alerts</h3>
              {alerts.slice(0, 5).map((a, i) => (
                <div key={i} className="flex justify-between text-[10px] text-gray-400 py-0.5">
                  <span className="text-red-300">{a.type?.replace("_", " ")}</span>
                  <span>{a.time}</span>
                </div>
              ))}
            </div>
          )}

          {/* Notes */}
          <div className="flex-1 p-4 border-b border-gray-700">
            <h3 className="text-sm font-bold text-gray-300 mb-2">📝 Notes</h3>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Take notes during the interview..."
              className="w-full h-full bg-gray-800 text-gray-200 text-sm p-3 rounded-lg resize-none outline-none border border-gray-700 focus:border-blue-500"
            />
          </div>

          {/* Chat */}
          <div className="h-64 flex flex-col p-4">
            <h3 className="text-sm font-bold text-gray-300 mb-2">💬 Chat</h3>
            <div className="flex-1 overflow-y-auto space-y-2 mb-2">
              {messages.map((msg, i) => (
                <div key={i} className="text-sm">
                  <span className="text-blue-400 font-medium">{msg.sender}</span>
                  <span className="text-gray-500 text-xs ml-2">{msg.time}</span>
                  <p className="text-gray-300">{msg.text}</p>
                </div>
              ))}
              {messages.length === 0 && (
                <p className="text-gray-500 text-sm text-center">No messages yet</p>
              )}
            </div>
            <div className="flex gap-2">
              <input
                value={newMessage}
                onChange={(e) => setNewMessage(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && sendMessage()}
                placeholder="Type a message..."
                className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm outline-none focus:border-blue-500"
              />
              <button
                onClick={sendMessage}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm font-bold"
              >
                Send
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
