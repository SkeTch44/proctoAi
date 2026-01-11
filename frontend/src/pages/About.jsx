import React from "react";
import { FaRocket, FaShieldAlt, FaUsers } from "react-icons/fa";
import { useNavigate } from "react-router-dom";

export default function About() {
    const navigate = useNavigate();
  return (
    <section className="min-h-[80vh] px-6 py-16 flex items-center justify-center">
      <div className="max-w-6xl w-full text-center">
        {/* Heading */}
        <h1 className="text-4xl md:text-5xl font-extrabold mb-6
          text-blue-900 dark:text-blue-300">
          About{" "}
          <button onClick={() => navigate("/home")}>

          <span className="text-transparent bg-clip-text bg-gradient-to-r
            from-blue-700 via-purple-800 to-pink-800
            dark:from-blue-300 dark:via-purple-400 dark:to-pink-300">
            ProctoAI
          </span>
          </button>
        </h1>

        <p className="text-lg md:text-xl text-gray-700 dark:text-gray-300 max-w-3xl mx-auto mb-12">
          ProctoAI is built to simplify digital workflows by combining modern
          design, accessibility, and AI-powered tools — all wrapped in a fast,
          developer-friendly experience.
        </p>

        {/* Feature Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {/* Card 1 */}
          <div className="bg-white dark:bg-[#1D1A17]
            border border-teal-400 dark:border-green-500
            rounded-xl p-6 shadow-md hover:shadow-lg transition">
            <FaRocket className="text-3xl mb-4 mx-auto text-purple-700 dark:text-green-400" />
            <h3 className="text-xl font-semibold mb-2 dark:text-gray-100">
              Fast & Modern
            </h3>
            <p className="text-gray-600 dark:text-gray-400">
              Built using modern web technologies with performance and
              scalability in mind.
            </p>
          </div>

          {/* Card 2 */}
          <div className="bg-white dark:bg-[#1D1A17]
            border border-teal-400 dark:border-green-500
            rounded-xl p-6 shadow-md hover:shadow-lg transition">
            <FaShieldAlt className="text-3xl mb-4 mx-auto text-blue-700 dark:text-green-400" />
            <h3 className="text-xl font-semibold mb-2 dark:text-gray-100">
              Secure & Reliable
            </h3>
            <p className="text-gray-600 dark:text-gray-400">
              Designed with best practices to ensure data safety and system
              reliability.
            </p>
          </div>

          {/* Card 3 */}
          <div className="bg-white dark:bg-[#1D1A17]
            border border-teal-400 dark:border-green-500
            rounded-xl p-6 shadow-md hover:shadow-lg transition">
            <FaUsers className="text-3xl mb-4 mx-auto text-pink-700 dark:text-green-400" />
            <h3 className="text-xl font-semibold mb-2 dark:text-gray-100">
              User-Focused
            </h3>
            <p className="text-gray-600 dark:text-gray-400">
              Clean UI, dark mode support, and intuitive flows for every user.
            </p>
          </div>
        </div>

        <br/>
        <h1 className="text-4xl md:text-5xl font-extrabold mb-6
          text-blue-900 dark:text-blue-300">
          About{" "}

          <span className="text-transparent bg-clip-text bg-gradient-to-r
            from-blue-700 via-purple-800 to-pink-800
            dark:from-blue-300 dark:via-purple-400 dark:to-pink-300">
            Creator of ProctoAI
          </span>
        </h1>

        <p className="text-lg md:text-xl text-gray-700 dark:text-gray-300 max-w-3xl mx-auto mb-12">
          ProctoAI is built by two fellow collegues ayush (full stack developer) and rohan(ml and backend developer) with their different expertise in their field.
        </p>
      </div>
    </section>
  );
}
