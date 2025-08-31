import React from "react";
import { useNavigate } from "react-router-dom";

export default function LanderPage() {
  const navigate = useNavigate();

  return (
    <section className="flex flex-col items-center justify-center min-h-[80vh] px-4 text-center">
      {/* Hero Section */}
      <main className="flex flex-col md:flex-row items-center justify-between px-6 py-16 gap-12 w-full max-w-6xl mx-auto">
        {/* Text Section */}
        <section className="max-w-xl text-center md:text-left">
          <h1 className="text-5xl md:text-6xl font-extrabold mb-6 text-purple-700 dark:text-blue-300 drop-shadow-lg">
            ProctoAI <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-purple-700 to-purple-800  dark:from-blue-300 dark:via-purple-400 dark:to-pink-300">
              AI-powered Proctoring Platform
            </span>
          </h1>
          <p className="text-xl md:text-2xl dark:text-gray-200 mb-8 max-w-2xl">
            Secure and scalable online exam platform with advanced anti-cheating
            measures and automated grading.
          </p>
          <div className="inline-block bg-gradient-to-r from-purple-700 via-teal-500 to-white dark:from-green-500 dark:via-blue-500 dark:to-green-400 p-[3px] rounded-xl">
            <button
              onClick={() => navigate("/home")}
              className="px-8 py-3 rounded-xl text-lg font-semibold shadow-lg transition-all duration-200
               bg-blue-500 hover:bg-blue-600 text-white
               dark:bg-blue-700 dark:hover:bg-blue-500 dark:text-gray-100"
            >
              Get Started!
            </button>
          </div>
        </section>

        {/* Monitor Illustration */}
        <div className="flex justify-center items-center w-full max-w-md mx-auto">
          <img
            src="/Desktop-proctoAI.png"
            alt="ProctoAI Desktop"
            className=" w-full h-auto object-contain bg-transparent rounded-xl shadow-2xl shadow-teal-200 dark:shadow-blue-900 p-2"
          />
        </div>
      </main>
    </section>
  );
}
