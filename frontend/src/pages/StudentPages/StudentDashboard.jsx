import React from "react";
import { getUser, logout } from "../../utils/authStorage";
import { useNavigate } from "react-router-dom";

export default function StudentDashboard() {
  const user = getUser();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/home");
  };
  return (
    <div className="max-w-6xl  mx-auto p-6 lg:p-12 space-y-8">
      <header className="mb-8 text-center lg:text-left">
        <div className="flex items-center justify-evenly">
          <div>
            <h1 className="text-3xl font-black bg-gradient-to-r from-gray-900 via-blue-900 to-purple-900 bg-clip-text text-transparent dark:from-blue-400 dark:via-purple-400 dark:to-pink-400">
              Student Dashboard
            </h1>
            <p className="text-sm text-gray-600 dark:text-gray-300 max-w-2xl">
              Welcome,{" "}
              <span className="font-semibold">
                {user?.username || user?.name || "Student"}
              </span>
            </p>
          </div>
          <div>
            <button
              onClick={handleLogout}
              className="px-3 py-2 rounded bg-red-500 text-white hover:bg-red-600"
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="p-6 bg-white dark:bg-[#0f1724] rounded-xl shadow border border-[#E5E7EB] dark:border-[#3B82F6]/40">
          <h3 className="text-sm text-gray-500 dark:text-gray-300">
            Enrolled Exams
          </h3>
          <p className="text-2xl font-bold mt-2">—</p>
        </div>

        <div className="p-6 bg-white dark:bg-[#0f1724] rounded-xl shadow border border-[#E5E7EB] dark:border-[#3B82F6]/40">
          <h3 className="text-sm text-gray-500 dark:text-gray-300">Upcoming</h3>
          <p className="text-2xl font-bold mt-2">—</p>
        </div>

        <div className="p-6 bg-white dark:bg-[#0f1724] rounded-xl shadow border border-[#E5E7EB] dark:border-[#3B82F6]/40">
          <h3 className="text-sm text-gray-500 dark:text-gray-300">
            Notifications
          </h3>
          <p className="text-2xl font-bold mt-2">—</p>
        </div>
      </section>

      <section className="mt-8">
        <div className="p-6 bg-white dark:bg-[#0f1724] rounded-xl shadow border border-[#E5E7EB] dark:border-[#3B82F6]/40">
          <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100">
            Quick Links
          </h2>
          <div className="mt-4 flex gap-3 flex-wrap">
            <button className="px-4 py-2 rounded bg-blue-500 text-white">
              Start Exam
            </button>
            <button className="px-4 py-2 rounded bg-green-500 text-white">
              My Results
            </button>
            <button className="px-4 py-2 rounded bg-yellow-500 text-white">
              Support
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}
