import React from 'react';

export default function Home() {
  return (
    <div className="flex flex-col items-center justify-center h-screen text-center px-4">
      <h1 className="text-4xl font-bold text-blue-700 dark:text-blue-400 mb-4">
        Welcome to MySite
      </h1>
      <p className="text-lg text-gray-600 dark:text-gray-300 mb-6 max-w-md">
        Build fast, accessible, and beautiful web experiences.
      </p>
      <button className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700 transition">
        Explore Projects
      </button>
    </div>
  );
}
