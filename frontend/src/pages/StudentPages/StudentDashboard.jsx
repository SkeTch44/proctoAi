import React, { useState, useEffect } from "react";
import { getUser, logout, getToken } from "../../utils/authStorage";
import { useNavigate } from "react-router-dom";

export default function StudentDashboard() {
  const user = getUser();
  const navigate = useNavigate();

  const [stats, setStats] = useState({
    enrolledExams: 0,
    upcomingExams: 0,
    notifications: 0,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const handleLogout = () => {
    logout();
    navigate("/home");
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      const token = getToken();
      const res = await fetch("http://localhost:5000/api/student/dashboard", {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      });
      if (!res.ok) throw new Error("Failed to fetch dashboard data");
      const data = await res.json();
      setStats({
        enrolledExams: data.enrolled_exams || 0,
        upcomingExams: data.upcoming_exams || 0,
        notifications: data.notifications || 0,
      });
    } catch (err) {
      setError("Failed to load dashboard data");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600 dark:text-gray-400">
            Loading dashboard...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto p-4 sm:p-6 lg:p-12 space-y-6 lg:space-y-8 min-h-screen">
      {/* Header */}
      <header className="mb-6 lg:mb-8 text-center lg:text-left">
        <div className="flex flex-col lg:flex-row items-center lg:items-start justify-between gap-4 lg:gap-6">
          <div className="text-center lg:text-left">
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-black bg-gradient-to-r from-gray-900 via-blue-900 to-purple-900 bg-clip-text text-transparent dark:from-blue-400 dark:via-purple-400 dark:to-pink-400 mb-2 lg:mb-3">
              Student Dashboard
            </h1>
            <p className="text-base sm:text-lg text-gray-600 dark:text-gray-300">
              Welcome back,{" "}
              <span className="font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                {user?.full_name ||
                  user?.fullName ||
                  user?.name ||
                  user?.username ||
                  "Student"}
              </span>
            </p>
          </div>
          <button
            onClick={handleLogout}
            className="px-4 sm:px-6 py-2 sm:py-3 rounded-md bg-red-50 text-red-600 dark:bg-transparent dark:text-red-400 border border-red-100 hover:bg-red-100"
          >
            🚪 Logout
          </button>
        </div>
      </header>

      {/* Stats Cards - MOBILE PERFECT */}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 lg:gap-6 mb-8 lg:mb-12 p-2 sm:p-0">
        {/* Enrolled Exams */}
        <div className="group p-5 sm:p-6 lg:p-8 bg-gradient-to-br from-emerald-50 to-green-50 dark:from-emerald-900/20 dark:to-green-900/20 rounded-2xl lg:rounded-3xl border border-emerald-200/50 shadow-lg hover:shadow-2xl hover:-translate-y-2 transition-all duration-300 cursor-pointer">
          <div className="flex items-center justify-between mb-3 lg:mb-4">
            <div className="p-2 sm:p-3 bg-emerald-100 dark:bg-emerald-900/50 rounded-xl lg:rounded-2xl">
              <svg
                className="w-6 h-6 sm:w-7 sm:h-7 text-emerald-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
            <span className="px-2 py-1 bg-white/60 dark:bg-gray-800/50 rounded-full text-xs sm:text-sm font-semibold text-gray-700 dark:text-gray-200">
              Enrolled
            </span>
          </div>
          <h3 className="text-xs sm:text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2">
            Enrolled Exams
          </h3>
          <p className="text-3xl sm:text-4xl lg:text-5xl font-black text-emerald-600 dark:text-emerald-400 mb-1">
            {stats.enrolledExams}
          </p>
          <p className="text-xs sm:text-sm text-gray-500 dark:text-gray-400">
            Total exams registered
          </p>
        </div>

        {/* Upcoming Exams */}
        <div className="group p-5 sm:p-6 lg:p-8 bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 rounded-2xl lg:rounded-3xl border border-blue-200/50 shadow-lg hover:shadow-2xl hover:-translate-y-2 transition-all duration-300 cursor-pointer">
          <div className="flex items-center justify-between mb-3 lg:mb-4">
            <div className="p-2 sm:p-3 bg-blue-100 dark:bg-blue-900/50 rounded-xl lg:rounded-2xl">
              <svg
                className="w-6 h-6 sm:w-7 sm:h-7 text-blue-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
            <span className="px-2 py-1 bg-white/60 dark:bg-gray-800/50 rounded-full text-xs sm:text-sm font-semibold text-gray-700 dark:text-gray-200">
              Upcoming
            </span>
          </div>
          <h3 className="text-xs sm:text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2">
            Upcoming Exams
          </h3>
          <p className="text-3xl sm:text-4xl lg:text-5xl font-black text-blue-600 dark:text-blue-400 mb-1">
            {stats.upcomingExams}
          </p>
          <p className="text-xs sm:text-sm text-gray-500 dark:text-gray-400">
            Exams in next 7 days
          </p>
        </div>

        {/* Notifications */}
        <div className="group p-5 sm:p-6 lg:p-8 bg-gradient-to-br from-orange-50 to-red-50 dark:from-orange-900/20 dark:to-red-900/20 rounded-2xl lg:rounded-3xl border border-orange-200/50 shadow-lg hover:shadow-2xl hover:-translate-y-2 transition-all duration-300 cursor-pointer relative">
          {stats.notifications > 0 && (
            <div className="absolute -top-2 -right-2 w-5 h-5 sm:w-6 sm:h-6 bg-red-500 text-white rounded-full flex items-center justify-center text-xs font-bold shadow-lg">
              {stats.notifications}
            </div>
          )}
          <div className="flex items-center justify-between mb-3 lg:mb-4">
            <div className="p-2 sm:p-3 bg-orange-100 dark:bg-orange-900/50 rounded-xl lg:rounded-2xl">
              <svg
                className="w-6 h-6 sm:w-7 sm:h-7 text-orange-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
                />
              </svg>
            </div>
            <span className="px-2 py-1 bg-white/60 dark:bg-gray-800/50 rounded-full text-xs sm:text-sm font-semibold text-gray-700 dark:text-gray-200">
              New
            </span>
          </div>
          <h3 className="text-xs sm:text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2">
            Notifications
          </h3>
          <p className="text-3xl sm:text-4xl lg:text-5xl font-black text-orange-600 dark:text-orange-400 mb-1">
            {stats.notifications}
          </p>
          <p className="text-xs sm:text-sm text-gray-500 dark:text-gray-400">
            Unread messages
          </p>
        </div>
      </section>

      {/* Quick Links - MOBILE PERFECT */}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 lg:gap-6 p-2 sm:p-0">
        {[
          {
            icon: "🎓",
            title: "Available Exams",
            description: "Start your proctored exams",
            color: "from-orange-500 to-red-600",
            path: "/student/exams",
          },
          {
            icon: "📊",
            title: "My Results",
            description: "View exam performance",
            color: "from-emerald-500 to-green-600",
            path: "/student/results",
          },
          {
            icon: "🆘",
            title: "Support",
            description: "Get help instantly",
            color: "from-blue-500 to-indigo-600",
            path: "/student/support",
          },
          {
            icon: "⭐",
            title: "Feedback",
            description: "Share your thoughts",
            color: "from-purple-500 to-pink-600",
            path: "/student/feedback",
          },
        ].map((link, index) => (
          <a
            key={index}
            href={link.path}
            className="group p-5 sm:p-6 lg:p-8 bg-white dark:bg-[#0f1724] rounded-2xl lg:rounded-3xl shadow-lg border border-[#E5E7EB] dark:border-[#3B82F6]/40 hover:shadow-2xl hover:-translate-y-3 transition-all duration-300 h-44 sm:h-48 lg:h-full flex flex-col items-center justify-between text-center"
          >
            <div
              className={`w-16 h-16 sm:w-20 sm:h-20 bg-gradient-to-r ${link.color} rounded-2xl lg:rounded-3xl flex items-center justify-center mb-4 lg:mb-6 shadow-xl group-hover:scale-110 transition-transform duration-300`}
            >
              <span className="text-2xl sm:text-3xl">{link.icon}</span>
            </div>
            <h3 className="text-lg sm:text-xl font-bold text-gray-900 dark:text-white mb-2 lg:mb-3 group-hover:text-transparent group-hover:bg-clip-text group-hover:bg-gradient-to-r group-hover:from-gray-900 group-hover:via-blue-900 group-hover:to-purple-900 text-base sm:text-lg">
              {link.title}
            </h3>
            <p className="text-gray-600 dark:text-gray-400 mb-4 lg:mb-6 flex-1 text-xs sm:text-sm leading-relaxed px-2">
              {link.description}
            </p>
            <span className="px-4 py-2 bg-gradient-to-r from-gray-100 to-gray-200 dark:from-gray-800 dark:to-gray-700 rounded-xl font-semibold text-xs sm:text-sm group-hover:bg-gradient-to-r group-hover:from-blue-500 group-hover:to-indigo-600 group-hover:text-white transition-all duration-300">
              Go →
            </span>
          </a>
        ))}
      </section>

      {/* Error State */}
      {error && (
        <div className="p-6 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-3xl text-center">
          <div className="text-4xl sm:text-6xl mb-4">⚠️</div>
          <h3 className="text-lg sm:text-xl font-bold text-red-800 dark:text-red-200 mb-4">
            {error}
          </h3>
          <button
            onClick={fetchDashboardData}
            className="px-6 py-3 bg-red-500 hover:bg-red-600 text-white font-semibold rounded-xl transition-all"
          >
            🔄 Retry
          </button>
        </div>
      )}
    </div>
  );
}
