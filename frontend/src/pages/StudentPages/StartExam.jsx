// src/pages/StudentPages/StartExam.jsx - COMPLETE VERSION
import React, { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import PermissionModal from "../../components/PermissionModal";
import { getToken } from "../../utils/authStorage";

const statusColors = {
  blue: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300",
  green: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300",
  yellow:
    "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300",
};

const availableExams = [
  {
    id: 1,
    name: "Data Structures & Algorithms",
    duration: "90 min",
    status: "Ready",
    date: "Dec 25, 2025",
    color: "green",
  },
  {
    id: 2,
    name: "Web Development Fundamentals",
    duration: "120 min",
    status: "Ready",
    date: "Dec 28, 2025",
    color: "blue",
  },
  {
    id: 3,
    name: "Database Systems",
    duration: "75 min",
    status: "Not Started",
    date: "Jan 5, 2026",
    color: "yellow",
  },
];

export default function StartExam() {
  const navigate = useNavigate();
  const [permissionsGranted, setPermissionsGranted] = useState({
    camera: false,
    microphone: false,
    screen: false,
  });
  const [checklistComplete, setChecklistComplete] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  // Request permissions (triggers browser popup)
  const requestPermissions = async () => {
    try {
      console.log("🔐 Requesting camera permission...");
      const cameraStream = await navigator.mediaDevices.getUserMedia({
        video: { width: 320, height: 240, facingMode: "user" },
      });
      setPermissionsGranted((prev) => ({ ...prev, camera: true }));
      cameraStream.getTracks().forEach((track) => track.stop());

      console.log("🔊 Requesting microphone permission...");
      const micStream = await navigator.mediaDevices.getUserMedia({
        audio: true,
      });
      setPermissionsGranted((prev) => ({ ...prev, microphone: true }));
      micStream.getTracks().forEach((track) => track.stop());

      setPermissionsGranted((prev) => ({ ...prev, screen: true }));
      console.log("✅ All permissions granted!");
    } catch (err) {
      console.error("❌ Permission denied:", err.name);
      const denied = err.name === "NotAllowedError";
      setPermissionsGranted({
        camera: !denied,
        microphone: !denied,
        screen: false,
      });
    }
  };

  // Check existing permissions (no popup)
  const checkPermissions = useCallback(async () => {
    try {
      const camera = await navigator.permissions.query({ name: "camera" });
      const microphone = await navigator.permissions.query({
        name: "microphone",
      });

      setPermissionsGranted({
        camera: camera.state === "granted",
        microphone: microphone.state === "granted",
        screen: true, // Screen always available
      });
    } catch (err) {
      console.log("Permission API not supported:", err);
    }
  }, []);

  // Backend exam start
  const startExam = async (examId) => {
    const token = getToken();
    if (!token) throw new Error("No auth token");

    const res = await fetch("http://127.0.0.1:5000/api/start_exam", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ exam_id: examId }),
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.message);

    localStorage.setItem("currentSessionId", data.session_id);
    return data;
  };

  const BeginButton = ({ exam }) => {
    const [open, setOpen] = useState(false);
    const [sessionId, setSessionId] = useState(null);
    const [isStarting, setIsStarting] = useState(false);
    const disabled =
      exam.status !== "Ready" ||
      !checklistComplete ||
      !permissionsGranted.camera ||
      !permissionsGranted.microphone;

    const handleClick = async () => {
      if (disabled && !permissionsGranted.camera) {
        requestPermissions();
        return;
      }

      setIsStarting(true);
      try {
        const data = await startExam(exam.id);
        setSessionId(data.session_id);
        setOpen(true);
      } catch (err) {
        alert(err.message || "Failed to start exam");
      } finally {
        setIsStarting(false);
      }
    };

    return (
      <>
        <button
          disabled={disabled || isStarting}
          onClick={handleClick}
          className={`
            mt-4 w-full py-3 px-6 rounded-2xl font-semibold text-sm shadow-lg transition-all duration-300 transform
            ${disabled || isStarting
              ? "bg-gray-400 cursor-not-allowed opacity-60 shadow-none"
              : "bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600 hover:from-indigo-700 hover:via-purple-700 hover:to-pink-700 hover:shadow-2xl hover:-translate-y-1 hover:scale-[1.02] text-white"
            }
          `}
        >
          {isStarting ? (
            <span className="flex items-center gap-2">
              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              Starting Exam...
            </span>
          ) : (
            "🚀 Begin Exam"
          )}
        </button>

        <PermissionModal
          open={open}
          sessionId={sessionId}
          onClose={() => {
            setOpen(false);
            if (sessionId) navigate(`/student/exam-room/${exam.id}`);
          }}
          permissions={permissionsGranted}
        />
      </>
    );
  };

  return (
    <div className="max-w-6xl mx-auto p-6 lg:p-12 space-y-8">
      {/* Header */}
      <header className="text-center lg:text-left">
        <h1 className="text-3xl font-black bg-gradient-to-r from-gray-900 via-blue-900 to-purple-900 bg-clip-text text-transparent dark:from-blue-400 dark:via-purple-400 dark:to-pink-400">
          Start Your Exam
        </h1>
        <p className="text-sm text-gray-600 dark:text-gray-300 max-w-2xl">
          Select exam and complete pre-exam checklist. AI proctoring will be
          activated.
        </p>
      </header>

      {/* Permissions - Compact Classy Version */}
      <div className="p-4 bg-gradient-to-br from-orange-50/90 via-amber-50/80 to-yellow-50/90 dark:from-orange-500/20 dark:via-amber-500/20 dark:to-yellow-500/20 rounded-2xl border border-orange-200/60 shadow-lg backdrop-blur-xl">
        <div className="p-4 rounded-xl bg-white/95 dark:bg-slate-900/90 border border-orange-100/50 shadow-inner">
          <div className="flex items-center justify-between mb-3 pb-2 border-b border-orange-100/50 dark:border-orange-500/30">
            <h3 className="text-lg font-bold text-orange-900 dark:text-orange-300 tracking-tight flex items-center gap-1.5">
              🔐 Permissions{" "}
              <span className="text-xs bg-orange-200/80 dark:bg-orange-900/60 px-1.5 py-0.5 rounded-full font-medium">
                Required
              </span>
            </h3>
            <button
              onClick={requestPermissions}
              className="px-5 py-2 bg-gradient-to-r from-orange-500 to-orange-600 hover:from-orange-600 hover:to-orange-700 text-white font-semibold text-sm rounded-lg shadow-md hover:shadow-lg transition-all whitespace-nowrap"
            >
              🔓 Grant All
            </button>
          </div>

          {/* Horizontal Permissions */}
          <div className="grid grid-cols-3 gap-3">
            <PermissionStatus
              type="📷 Cam"
              granted={permissionsGranted.camera}
              onRequest={requestPermissions}
              size="sm"
            />
            <PermissionStatus
              type="🎤 Mic"
              granted={permissionsGranted.microphone}
              onRequest={requestPermissions}
              size="sm"
            />
            <PermissionStatus
              type="🖥️ Screen"
              granted={permissionsGranted.screen}
              onRequest={() =>
                navigator.mediaDevices.getDisplayMedia({ video: true })
              }
              size="sm"
            />
          </div>
        </div>
      </div>
      {/* Checklist */}
      <section className="p-8 rounded-3xl border-2 border-emerald-200/50 bg-gradient-to-br from-emerald-50 to-green-50 dark:from-emerald-900/20 dark:to-green-900/20 shadow-2xl">
        <h2 className="text-2xl font-bold mb-6 text-emerald-900 dark:text-emerald-300">
          ✅ Pre-Exam Checklist
        </h2>
        <div className="grid md:grid-cols-2 gap-4 max-w-3xl">
          <ChecklistItem
            text="Stable internet (minimum 5 Mbps)"
            onChange={setChecklistComplete}
          />
          <ChecklistItem
            text="Working webcam & microphone"
            checked={permissionsGranted.camera && permissionsGranted.microphone}
            disabled
          />
          <ChecklistItem
            text="Quiet environment, clear desk"
            onChange={setChecklistComplete}
          />
          <ChecklistItem
            text="Single monitor, no external devices"
            onChange={setChecklistComplete}
          />
        </div>
      </section>
      {/* Available Exams */}
      <section className="p-8 bg-gradient-to-br from-indigo-50 via-blue-50 to-purple-50 dark:from-slate-900/50 dark:via-blue-900/20 dark:to-purple-900/20 rounded-3xl border border-indigo-200/50 dark:border-blue-500/30 shadow-2xl">
        <h2 className="text-3xl font-bold mb-8 bg-gradient-to-r from-gray-800 to-slate-800 bg-clip-text text-transparent dark:from-blue-400 dark:to-purple-400">
          📚 Available Exams
        </h2>
        <div className="grid md:grid-cols-2 lg:grid-cols-1 gap-6">
          {availableExams.map((exam) => (
            <ExamCard key={exam.id} exam={exam} />
          ))}
        </div>
      </section>
    </div>
  );
}

// Components
function ExamCard({ exam }) {
  const navigate = useNavigate();
  const disabled = exam.status !== "Ready";

  return (
    <div className="group relative p-8 rounded-3xl bg-white/70 dark:bg-slate-800/70 backdrop-blur-xl border-2 hover:border-4 transition-all duration-300 hover:shadow-2xl hover:-translate-y-2 hover:scale-[1.02] cursor-pointer border-gray-200/50 dark:border-slate-700/50 hover:border-blue-400/70">
      <div
        className={`absolute -top-3 left-1/2 transform -translate-x-1/2 px-4 py-1 rounded-full text-xs font-bold shadow-lg ${statusColors[exam.color]
          }`}
      >
        {exam.status}
      </div>

      <h3 className="text-xl font-bold mb-3 text-gray-900 dark:text-gray-100 leading-tight">
        {exam.name}
      </h3>

      <div className="space-y-2 mb-6 text-sm text-gray-600 dark:text-gray-400">
        <div>⏱️ {exam.duration}</div>
        <div>📅 {exam.date}</div>
      </div>

      <button
        disabled={disabled}
        onClick={() => navigate(`/student/exam-room/${exam.id}`)}
        className="w-full py-4 px-6 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 disabled:from-gray-400 disabled:to-gray-500 text-white font-bold rounded-2xl shadow-xl hover:shadow-2xl transition-all duration-300 transform hover:-translate-y-1 disabled:cursor-not-allowed disabled:shadow-none"
      >
        {disabled ? "Not Available" : `🚀 Start ${exam.name}`}
      </button>
    </div>
  );
}

function PermissionStatus({ type, granted, onRequest, size = "md" }) {
  return (
    <div
      className={`flex items-center justify-between gap-2 p-2 lg:p-3 rounded-xl border transition-all duration-300 shadow-sm backdrop-blur-sm overflow-hidden ${granted
        ? "bg-emerald-100/90 border-emerald-300/70 text-emerald-800 shadow-emerald-200/40 dark:bg-emerald-900/40 dark:border-emerald-400/60 dark:text-emerald-200"
        : "bg-rose-100/90 border-rose-300/70 text-rose-800 shadow-rose-200/40 dark:bg-rose-900/40 dark:border-rose-400/60 dark:text-rose-200 hover:shadow-rose-300/60"
        }`}
    >
      <div className="flex items-center gap-2 flex-shrink-0">
        <div
          className={`w-3 h-3 rounded-full shadow-sm transition-all ${granted
            ? "bg-emerald-500 scale-110 shadow-emerald-300 animate-pulse"
            : "bg-rose-500 shadow-rose-200 hover:scale-110"
            }`}
        />
        <span
          className={`font-medium text-xs lg:text-sm ${size === "sm" ? "tracking-tight" : ""
            }`}
        >
          {type}
        </span>
      </div>
      {!granted && (
        <button
          onClick={onRequest}
          className="px-3 py-1.5 lg:px-2.5 lg:py-1.5 bg-gradient-to-r from-blue-500/90 to-blue-600/90 hover:from-blue-600 hover:to-blue-700 text-white text-xs font-bold rounded-lg shadow-md hover:shadow-lg transition-all duration-200 transform hover:scale-105 whitespace-nowrap"
        >
          Grant
        </button>
      )}
    </div>
  );
}

function ChecklistItem({ text, checked, onChange, disabled }) {
  return (
    <label className="flex items-center gap-4 p-5 bg-white/80 dark:bg-slate-800/70 rounded-2xl border-2 border-emerald-200/50 dark:border-emerald-400/50 cursor-pointer hover:shadow-xl hover:border-emerald-300/70 transition-all duration-300 group backdrop-blur-sm hover:bg-white/95 dark:hover:bg-slate-800/90">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange?.(e.target.checked)}
        disabled={disabled}
        className="w-6 h-6 rounded-lg text-emerald-600 border-2 border-emerald-300 focus:ring-emerald-500 focus:ring-2 shadow-md transition-all group-hover:scale-110 disabled:opacity-50 disabled:cursor-not-allowed"
      />
      <span
        className={`text-lg font-medium transition-colors ${checked
          ? "text-emerald-700 dark:text-emerald-300"
          : "text-gray-700 dark:text-gray-300 group-hover:text-emerald-600"
          }`}
      >
        {text}
      </span>
    </label>
  );
}
