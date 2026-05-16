import React, { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { io } from "socket.io-client";
import { getToken, getUser } from "../../utils/authStorage";
import { API_BASE, getAuthHeader } from "../../utils/apiConfig";

export default function WaitingRoom() {
  const { examId } = useParams();
  const navigate = useNavigate();
  const [exam, setExam] = useState(null);
  const [status, setStatus] = useState("Connecting...");
  const [socket, setSocket] = useState(null);
  const user = getUser();

  useEffect(() => {
    fetchExamInfo();
    const s = io(API_BASE, {
      auth: { token: getToken() },
      transports: ["websocket", "polling"]
    });

    setSocket(s);

    s.on("connect", () => {
      setStatus("Connected. Waiting for host to start...");
      s.emit("join_exam_room", {
        exam_id: examId,
        student_id: user.id || user.user_id,
        student_name: user.username || user.name
      });
    });

    s.on("exam_started", (data) => {
      if (data.exam_id == examId) {
        setStatus("Starting Exam...");
        setTimeout(() => navigate(`/student/exam-room/${examId}`), 1000);
      }
    });

    s.on("connect_error", (err) => {
      setStatus(`Connection Error: ${err.message}`);
    });

    return () => s.disconnect();
  }, [examId]);

  const fetchExamInfo = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/exams/verify/${examId}`, {
        headers: getAuthHeader()
      });
      const data = await res.json();
      if (data.success) {
        setExam(data.exam);
      }
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-6 bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800 text-center">
      <div className="bg-white dark:bg-gray-800 p-10 rounded-3xl shadow-2xl max-w-lg w-full space-y-8 border border-white/20">
        <div className="text-6xl animate-bounce">⏳</div>
        
        <div>
          <h1 className="text-3xl font-black text-gray-900 dark:text-white mb-2">
            Waiting Room
          </h1>
          {exam && (
            <p className="text-xl font-bold text-blue-600 dark:text-blue-400">
              {exam.title}
            </p>
          )}
        </div>

        <div className="p-4 bg-blue-50 dark:bg-blue-900/30 rounded-2xl border border-blue-200 dark:border-blue-800">
          <p className="text-blue-800 dark:text-blue-200 font-medium">
            {status}
          </p>
        </div>

        <div className="text-sm text-gray-500 dark:text-gray-400">
          <p>Please do not refresh this page.</p>
          <p>The exam will start automatically when the instructor is ready.</p>
        </div>

        {exam && (
          <div className="grid grid-cols-2 gap-4 pt-4 text-xs font-semibold uppercase tracking-wider text-gray-400">
            <div className="bg-gray-50 dark:bg-gray-700/50 p-3 rounded-xl">
              Duration: {exam.duration / 60}m
            </div>
            <div className="bg-gray-50 dark:bg-gray-700/50 p-3 rounded-xl">
              Questions: {exam.question_count}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
