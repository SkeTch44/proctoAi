import React from "react";
import { MdAdminPanelSettings } from "react-icons/md";

export default function AdminPanelCard() {
  return (
    <div className="flex-1 bg-white dark:bg-gray-800 border border-blue-500 dark:border-green-500 rounded-xl shadow-lg p-6 transition-all duration-300 hover:shadow-xl">
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

      <div className="mt-4 p-4 rounded-lg border border-purple-500 dark:border-green-500 bg-gradient-to-r from-purple-300 via-purple-100 to-white dark:bg-gradient-to-r dark:from-gray-700 dark:via-gray-800 dark:to-gray-900 text-sm text-purple-900 dark:text-green-300 font-medium shadow-sm">
        Click the tab above to log in as an admin.
      </div>
    </div>
  );
}
