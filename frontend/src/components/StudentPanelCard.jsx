import React from "react";
import { useNavigate } from "react-router-dom";
import { PiStudentBold } from "react-icons/pi";
import SkeletonLoader from "./Loader";

export default function StudentPanelCard({ loading = false }) {
  let navigate = useNavigate();
  if (loading) return <SkeletonLoader type="card" />;

  const handleSelect = () => {
    localStorage.setItem("selected_role", "student");
    navigate("/register");
  };
  return (
    <div className="flex-1 bg-white dark:bg-[#1D1A17] border border-blue-500 dark:border-green-500 rounded-xl shadow-lg p-6 transition-all duration-300 hover:shadow-xl">
      <div className="flex items-center gap-3 mb-4">
        <div className="p-3 bg-purple-100 dark:bg-green-900 rounded-full">
          <PiStudentBold className="text-purple-700 dark:text-green-400 text-3xl" />
        </div>
        <h2 className="text-2xl font-bold text-purple-700 dark:text-green-400">
          Student/Candidate
        </h2>
      </div>
      <p className="text-gray-700 dark:text-gray-300 mb-4">
        Take secure, AI-monitored exams and instantly access results with smart proctoring tools.
      </p>
 
      <div className="mt-4 flex flex-col gap-3">
        <div
          onClick={handleSelect}
          className="cursor-pointer p-4 rounded-lg border border-purple-500 dark:border-green-500 bg-gradient-to-r from-purple-300 via-purple-100 to-white dark:bg-gradient-to-r dark:from-gray-700 dark:via-gray-800 dark:to-gray-900 text-sm text-purple-900 dark:text-green-300 font-medium shadow-sm"
        >
          Click to register as a student
        </div>

        <div
          onClick={() => navigate('/login')}
          className="cursor-pointer p-3 rounded-lg border border-red-300 text-red-700 bg-red-50 hover:bg-red-100 dark:bg-transparent dark:text-red-400 dark:border-red-600 text-sm font-medium text-center"
        >
          Already have an account? Login
        </div>
      </div>

    </div>
  );
}
