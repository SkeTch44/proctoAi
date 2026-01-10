import React, { useEffect, useState } from "react";
import { getUser, logout } from "../../utils/authStorage";
import { useNavigate } from "react-router-dom";
import StudentSidebar from "../../components/StudentSidebar";

const DEFAULT_EXAMS = [
  { id: 1, name: "Data Structures Midterm", date: "2025-12-25", status: "ready" },
  { id: 2, name: "Web Fundamentals", date: "2025-12-28", status: "ready" },
  { id: 3, name: "Database Systems", date: "2026-01-05", status: "not-started" },
];

export default function StudentDashboard() {
  const user = getUser();
  const navigate = useNavigate();
  const [exams, setExams] = useState([]);
  const [notifications, setNotifications] = useState([]);

  useEffect(() => {
    // try to load exams/notifications from localStorage, fallback to defaults
    try {
      const stored = JSON.parse(localStorage.getItem("exams"));
      setExams(Array.isArray(stored) && stored.length ? stored : DEFAULT_EXAMS);

      const notifs = JSON.parse(localStorage.getItem("notifications"));
      setNotifications(Array.isArray(notifs) ? notifs : [
        { id: 1, text: "Welcome to ProctoAI — good luck on your exams!" },
      ]);
    } catch (e) {
      setExams(DEFAULT_EXAMS);
      setNotifications([{ id: 1, text: "Welcome to ProctoAI — good luck on your exams!" }]);
    }
  }, []);

  const handleLogout = () => {
    logout();
    navigate("/home");
  };

  const enrolledCount = exams.length;
  const upcomingCount = exams.filter((e) => new Date(e.date) >= new Date()).length;

  return (
    <StudentSidebar>
      <div className="max-w-6xl mx-auto">
        <header className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-800 dark:text-gray-100">
                Student Dashboard
              </h1>
              <p className="text-sm text-gray-600 dark:text-gray-300 mt-1">
                Welcome, {" "}
                <span className="font-semibold">
                  {user?.username || user?.name || "Student"}
                </span>
              </p>
            </div>
            <div>
              <button onClick={handleLogout} className="px-3 py-2 rounded bg-red-500 text-white hover:bg-red-600">Logout</button>
            </div>
          </div>
        </header>

        <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="p-6 bg-white dark:bg-[#0f1724] rounded-xl shadow border border-[#E5E7EB] dark:border-[#3B82F6]/40">
            <h3 className="text-sm text-gray-500 dark:text-gray-300">Enrolled Exams</h3>
            <p className="text-2xl font-bold mt-2">{enrolledCount}</p>
          </div>

          <div className="p-6 bg-white dark:bg-[#0f1724] rounded-xl shadow border border-[#E5E7EB] dark:border-[#3B82F6]/40">
            <h3 className="text-sm text-gray-500 dark:text-gray-300">Upcoming</h3>
            <p className="text-2xl font-bold mt-2">{upcomingCount}</p>
          </div>

          <div className="p-6 bg-white dark:bg-[#0f1724] rounded-xl shadow border border-[#E5E7EB] dark:border-[#3B82F6]/40">
            <h3 className="text-sm text-gray-500 dark:text-gray-300">Notifications</h3>
            <p className="text-2xl font-bold mt-2">{notifications.length}</p>
          </div>
        </section>

        <section className="mt-8">
          <div className="p-6 bg-white dark:bg-[#0f1724] rounded-xl shadow border border-[#E5E7EB] dark:border-[#3B82F6]/40">
            <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100">
              Upcoming Exams
            </h2>
            <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
              {exams.map((exam) => (
                <div key={exam.id} className="p-4 rounded-xl border hover:shadow-md transition flex items-center justify-between">
                  <div>
                    <h3 className="font-semibold">{exam.name}</h3>
                    <p className="text-sm text-gray-600">{exam.date} • {exam.status}</p>
                  </div>
                  <div>
                    <button
                      onClick={() => navigate("/student/start")}
                      className="px-4 py-2 rounded bg-blue-500 text-white"
                    >
                      Start
                    </button>
                  </div>
                </div>
              ))}
            </div>

            <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mt-6">Notifications</h2>
            <ul className="mt-3 space-y-2">
              {notifications.map((n) => (
                <li key={n.id} className="p-3 bg-gray-50 dark:bg-[#111827] rounded-md">{n.text}</li>
              ))}
            </ul>
          </div>
        </section>
      </div>
    </StudentSidebar>
  );
}
