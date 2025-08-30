import React from "react";
import {
  FaUser,
  FaMicrophone,
  FaVideo,
  FaDesktop,
  FaCheckCircle,
} from "react-icons/fa";
import StudentPanelCard from "../components/StudentPanelCard";
import AdminPanelCard from "../components/AdminPanelCard";

export default function Home() {
  return (
    <section className="flex flex-col items-center justify-center min-h-[80vh] px-4 text-center">
      {/* Hero Section */}
      <main className="flex flex-col md:flex-row items-center justify-between px-6 py-16 gap-12 w-full max-w-6xl mx-auto">
        {/* Text Section */}
        <section className="max-w-xl text-center md:text-left">
          <h1 className="text-5xl md:text-6xl font-extrabold mb-6 text-blue-900 dark:text-blue-300 drop-shadow-lg">
            Welcome to{" "}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-700 via-purple-900 to-pink-900 dark:from-blue-300 dark:via-purple-400 dark:to-pink-300">
              ProctoAI
            </span>
          </h1>
          <p className="text-xl md:text-2xl dark:text-gray-200 mb-8 max-w-2xl">
            Build fast, accessible, and beautiful web experiences with modern
            tools and a delightful dark mode.
          </p>
          <div className="inline-block bg-gradient-to-r from-purple-700 via-teal-500 to-white dark:from-green-500 dark:via-blue-500 dark:to-green-400 p-[3px] rounded-xl">
            <button
              className="px-8 py-3 rounded-xl text-lg font-semibold shadow-lg transition-all duration-200
               bg-blue-500 hover:bg-blue-600 text-white
               dark:bg-blue-700 dark:hover:bg-blue-500 dark:text-gray-100"
            >
              About Us!
            </button>
          </div>
        </section>

        {/* Monitor Illustration */}
        <section className="w-full max-w-sm">
          <div className="bg-white dark:bg-gray-800 border-2 border-teal-500 dark:border-green-500 rounded-lg p-6 shadow-md flex flex-col items-center">
            {/* Centered User Icon */}
            <div className="flex justify-center items-center h-24 w-24 bg-teal-500 dark:bg-green-500 rounded-full mb-6">
              <FaUser className="text-white text-4xl" />
            </div>

            {/* Control Icons */}
            <div className="flex justify-around w-full mt-2 text-teal-500 dark:text-green-500 text-xl">
              <FaMicrophone />
              <FaVideo />
              <FaDesktop />
              <FaCheckCircle className="text-rose-500 dark:text-green-400" />
            </div>
          </div>
        </section>
      </main>
      {/* Panel Cards Section */}
      <section className="w-full max-w-6xl mx-auto px-6 py-12">
        <div className="flex flex-col md:flex-row gap-8 justify-center items-stretch">
          <StudentPanelCard />
          <AdminPanelCard />
        </div>
      </section>
    </section>
  );
}
