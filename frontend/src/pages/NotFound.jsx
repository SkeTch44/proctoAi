import React from "react";
import { useNavigate } from "react-router-dom";

export default function NotFound() {
  const navigate = useNavigate();
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-[#0B1220]">
      <div className="text-center p-8 rounded-xl bg-white dark:bg-[#0F1115] shadow">
        <h1 className="text-6xl font-bold text-gray-800 dark:text-white">404</h1>
        <p className="mt-4 text-gray-600 dark:text-gray-300">Page not found.</p>
        <div className="mt-6 flex items-center justify-center gap-3">
          <button onClick={() => navigate('/home')} className="px-4 py-2 rounded bg-blue-500 text-white">Go Home</button>
          <button onClick={() => navigate(-1)} className="px-4 py-2 rounded bg-gray-200 dark:bg-gray-700 dark:text-white">Go Back</button>
        </div>
      </div>
    </div>
  );
}
