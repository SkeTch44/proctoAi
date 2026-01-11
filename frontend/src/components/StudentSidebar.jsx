// src/components/StudentSidebar.jsx
import { useState } from "react";
import { NavLink } from "react-router-dom";
import { FaCaretRight } from "react-icons/fa";
import { PiX } from "react-icons/pi";
import { logout, getUser } from "../utils/authStorage";
import { useNavigate } from "react-router-dom";

const navItems = [
  { label: "Start Exam", path: "/student/start-exam" },
  { label: "Results", path: "/student/results" },
  { label: "Profile", path: "/student/profile" },
  { label: "Support", path: "/student/support" },
];

export default function StudentSidebar({ children }) {
  const navigate = useNavigate();
  const user = getUser();
  const [isOpen, setIsOpen] = useState(true);

  return (
    <div className="flex min-h-screen bg-[#F3F4F6] text-gray-900 dark:bg-[#011627] dark:text-gray-100 overflow-hidden">
      <aside
        className={`
        w-64 h-screen fixed left-0 top-0 z-40 transform transition-transform duration-200 border-r-2 border-[#3B82F6]/30 rounded-r-xl
        bg-white shadow-2xl backdrop-blur-xl
        dark:bg-[#1D1A17] dark:border-[#3B82F6]/60 dark:rounded-r-2xl
        ${isOpen ? "translate-x-0" : "-translate-x-full"}
        md:translate-x-0 lg:w-72
      `}
      >
        <div className="h-28 sticky top-0 z-10 flex items-center justify-between px-4 border-b border-[#3B82F6]/20 bg-white/95 dark:bg-[#1D1A17]/95 backdrop-blur-sm rounded-t-xl dark:rounded-t-2xl shadow-sm">
          <div className="flex flex-col items-start gap-1 flex-1">
            <div className="flex items-center gap-3 hover:scale-105 transition-transform">
              <span className="text-xl font-extrabold tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-blue-700 via-purple-900 to-pink-900 dark:from-[#0ea5e9] dark:via-[#6366f1] dark:to-[#ec4899]">
                ProctoAI
              </span>
            </div>
            <div className="text-xs text-gray-600 dark:text-gray-300">
              Signed in as{" "}
              <span className="font-semibold">
                {user?.username || user?.name || "Student"}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                logout();
                navigate("/home");
              }}
              className="text-xs px-2 py-1 rounded-md bg-red-50 text-red-600 dark:bg-transparent dark:text-red-400 border border-red-100 hover:bg-red-100"
            >
              Logout
            </button>
          </div>
          {/* Close icon button */}
          <button
            className="md:hidden p-1.5 rounded-xl border-2 border-transparent
           text-gray-500 hover:text-gray-900 hover:bg-gray-100 hover:border-gray-300
           dark:text-gray-400 dark:hover:text-white dark:hover:bg-[#013243] 
           dark:hover:border-[#3B82F6]/60
            transition-all shadow-sm hover:shadow-md"
            onClick={() => setIsOpen(false)}
            title="Close menu"
          >
            <PiX className="h-4 w-4" />
          </button>
        </div>

        <nav className="h-[calc(100vh-7rem-5rem)] overflow-y-auto px-3 py-6 custom-scrollbar flex-1 mt-1">
          <NavLink
            to="/student/dashboard"
            className="px-2 text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400 mb-4 inline-block"
          >
            Student Panel
          </NavLink>
          <ul className="space-y-1">
            {navItems.map((item) => (
              <li key={item.path}>
                <NavLink
                  to={item.path}
                  className={({ isActive }) =>
                    [
                      "flex items-center gap-3 px-3 py-3 text-sm rounded-2xl transition-all border-2 shadow-sm",
                      "border-transparent text-gray-700 hover:bg-[#F3F4F6] hover:text-[#6D28D9] hover:border-[#6D28D9]/60 hover:shadow-md",
                      "dark:text-gray-300 dark:hover:bg-[#013243] dark:hover:text-[#0fc1a0] dark:hover:border-[#3B82F6]/60",
                      isActive
                        ? "bg-[#EDE9FE] text-[#6D28D9] border-[#6D28D9]/80 shadow-lg dark:bg-[#013243] dark:text-[#0fc1a0] dark:border-[#3B82F6]/80 dark:shadow-lg"
                        : "",
                    ].join(" ")
                  }
                >
                  {item.label}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>

        <div className="absolute bottom-0 left-0 right-0 p-6 text-xs border-t border-[#E5E7EB] dark:border-[#3B82F6]/40 rounded-b-xl dark:rounded-b-2xl bg-white/90 dark:bg-[#011627]/90 backdrop-blur-sm">
          <span className="inline-flex items-center gap-2 rounded-full px-4 py-2 bg-[#EEF2FF] text-[#6D28D9] border border-[#6D28D9]/30 dark:bg-[#013243] dark:text-[#0fc1a0] dark:border-[#3B82F6]/50">
            <span className="h-2 w-2 rounded-full bg-[#14B8A6] dark:bg-[#3B82F6]" />
            Secure AI proctoring
          </span>
        </div>
      </aside>

      <div className="flex-1 ml-0 md:ml-64 lg:ml-72 overflow-hidden">
        {!isOpen && (
          <button
            className="md:hidden fixed top-4 left-4 z-50 p-3 rounded-2xl bg-white dark:bg-[#011627] shadow-xl border-2 hover:shadow-2xl transition-all"
            onClick={() => setIsOpen(true)}
          >
            <FaCaretRight className="h-5 w-5" />
          </button>
        )}

        <main className="h-screen overflow-y-auto p-4 md:p-6 lg:p-8 scrollbar-thin scrollbar-thumb-gray-300 dark:scrollbar-thumb-slate-600 scrollbar-track-transparent">
          {children}
        </main>
      </div>
    </div>
  );
}
