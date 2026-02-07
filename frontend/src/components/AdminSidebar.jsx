// src/components/AdminSidebar.jsx
import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { PiX } from "react-icons/pi";
import { FaCaretRight } from "react-icons/fa";
import { logout, getUser } from "../utils/authStorage";
import { useNavigate } from "react-router-dom";

const navItems = [
  { label: "Document Upload", path: "documentUpload" },
  { label: "AI Question Generator", path: "analyzer" },
  { label: "Test creation", path: "test-creator" },
<<<<<<< HEAD
  { label: "Monitoring", path: "admin-monitoring" },
=======
  { label: "Live monitoring", path: "admin-monitoring" },
>>>>>>> rohan
  { label: "Proctoring Logs", path: "admin-logs" },
  { label: "Analytics", path: "admin-analytics" },
  { label: "Reports", path: "compiled-reports" },
];

export default function AdminSidebar() {
  const navigate = useNavigate();
  const user = getUser();
  const [isOpen, setIsOpen] = useState(true);

  return (
    <div className="flex min-h-screen bg-[#F3F4F6] text-gray-900 dark:bg-[#011627] dark:text-gray-100">
      {/* Sidebar */}
      <aside
        className={`
  w-64 h-screen transform transition-transform duration-200 border-2 rounded-xl
  bg-white border-[#3B82F6]/30 relative
  dark:bg-[#1D1A17] dark:border-[#3B82F6]/60 dark:rounded-2xl
  ${isOpen ? "translate-x-0" : "-translate-x-full"}
  md:translate-x-0 fixed md:static inset-y-0 left-0 z-40
`}
      >
        {/* Header */}
        <div className="h-28 flex items-center justify-between px-4 border-b border-[#3B82F6]/20 dark:border-[#3B82F6]/40 rounded-t-xl dark:rounded-t-2xl">
          <div className="flex flex-col items-start gap-1 flex-1">
            <div className="flex items-center gap-3 hover:scale-105 transition-transform">
              <span className="text-xl font-extrabold tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-blue-700 via-purple-900 to-pink-900 dark:from-[#0ea5e9] dark:via-[#6366f1] dark:to-[#ec4899]">
                ProctoAI
              </span>
            </div>
            <div className="text-xs text-gray-600 dark:text-gray-300">
              Signed in as{" "}
              <span className="font-semibold">
                {user?.username || user?.name || "Admin"}
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
            className="
              md:hidden p-1.5 rounded-xl border-2 border-transparent
              text-gray-500 hover:text-gray-900 hover:bg-gray-100 hover:border-gray-300
              dark:text-gray-400 dark:hover:text-white dark:hover:bg-[#013243] 
              dark:hover:border-[#3B82F6]/60
              transition-all shadow-sm hover:shadow-md
            "
            onClick={() => setIsOpen(false)}
            title="Close menu"
          >
            <PiX className="h-4 w-4" />
          </button>
        </div>

        {/* Nav */}
        <nav className="mt-4 px-2 flex-1 overflow-y-auto">
          <NavLink
            to="/AdminDashboard"
            className="px-2 text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400 mb-4 inline-block"
          >
            Admin panel
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
                  {/* <span className="h-2 w-2 rounded-full bg-[#6D28D9] dark:bg-[#0fc1a0]" /> */}
                  {item.label}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>

        {/* Footer badge */}
        <div className="absolute bottom-0 left-0 right-0 p-6 text-xs border-t border-[#E5E7EB] dark:border-[#3B82F6]/40 rounded-b-xl dark:rounded-b-2xl bg-white/90 dark:bg-[#011627]/90 backdrop-blur-sm">
          <span className="inline-flex items-center gap-2 rounded-full px-4 py-2 bg-[#EEF2FF] text-[#6D28D9] border border-[#6D28D9]/30 dark:bg-[#013243] dark:text-[#0fc1a0] dark:border-[#3B82F6]/50">
            <span className="h-2 w-2 rounded-full bg-[#14B8A6] dark:bg-[#3B82F6]" />
            Secure AI proctoring
          </span>
        </div>
      </aside>

      {/* Main content area */}
      <div className="flex-1">
        {/* Mobile toggle - only when closed */}
        {!isOpen && (
          <button
            className="
              md:hidden fixed top-4 left-4 z-50 p-2.5 rounded-2xl text-gray-700 bg-white shadow-xl border-2 border-gray-200
              hover:text-[#6D28D9] hover:bg-[#EEF2FF] hover:shadow-2xl hover:scale-105 hover:border-[#3B82F6]/60
              dark:text-gray-300 dark:bg-[#011627] dark:border-[#3B82F6]/60
              dark:hover:text-[#0fc1a0] dark:hover:bg-[#013243] dark:hover:border-[#3B82F6]/80
              transition-all duration-200 border-[#3B82F6]/30 
            "
            onClick={() => setIsOpen(true)}
            title="Show menu"
          >
            <FaCaretRight className="h-5 w-5" />
          </button>
        )}
        <main className="p-4 md:p-8 lg:p-12 bg-white dark:bg-[#1D1A17] min-h-screen">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
