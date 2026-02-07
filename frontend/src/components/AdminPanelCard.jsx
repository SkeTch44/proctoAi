import React from "react";
import { MdAdminPanelSettings } from "react-icons/md";
import SkeletonLoader from "./Loader";
import { useNavigate } from "react-router-dom";

export default function AdminPanelCard({ loading = false }) {
  const navigate = useNavigate();

  const handleClick = () => {
    // select admin role and navigate to registration
    localStorage.setItem("selected_role","admin");
    navigate("/admin-register");
  };

  if (loading) return <SkeletonLoader type="card" />;
  return (
    <div className="flex-1 bg-white dark:bg-[#1D1A17] border border-blue-500 dark:border-green-500 rounded-xl shadow-lg p-6 transition-all duration-300 hover:shadow-xl">
      <div className="flex items-center gap-3 mb-4">
        <div className="p-3 bg-purple-100 dark:bg-green-900 rounded-full">
          <MdAdminPanelSettings className="text-purple-700 dark:text-green-400 text-3xl" />
        </div>
        <h2 className="text-2xl font-bold text-purple-700 dark:text-green-400">
          Administrator
        </h2>
      </div>
      <p className="text-gray-700 dark:text-gray-300 mb-4">
        Manage users, configure exams, and monitor live sessions with
        intelligent proctoring tools.
      </p>

      <div className="mt-4 flex flex-col gap-3">
        <div
          onClick={handleClick}
          className="cursor-pointer p-4 rounded-lg border border-purple-500 dark:border-green-500 bg-gradient-to-r from-purple-300 via-purple-100 to-white dark:bg-gradient-to-r dark:from-gray-700 dark:via-gray-800 dark:to-gray-900 text-sm text-purple-900 dark:text-green-300 font-medium shadow-sm"
        >
          Click to register as an admin
        </div>

        <div
          onClick={() => navigate('/admin-login')}
          className="cursor-pointer p-3 rounded-lg border border-red-300 text-red-700 bg-red-50 hover:bg-red-100 dark:bg-transparent dark:text-red-400 dark:border-red-600 text-sm font-medium text-center"
        >
          Already have an admin account? Login
        </div>
      </div>
    </div>
  );
}
