import React from 'react'
import { useState } from "react";
import { pages } from './DragNdrop';

export default function AdminSidebar()
{
  const [active, setActive] = useState("Dashboard");

  return (
    <div className="min-h-screen flex bg-gray-100 dark:bg-[#111827]">
      {/* Sidebar */}
      <aside className="w-64 bg-white dark:bg-[#0F172A] shadow-lg p-6">
        <h1 className="text-xl font-semibold mb-8 text-gray-900 dark:text-white">
          My App
        </h1>

        <nav className="space-y-2">
          {pages.map((page) => (
            <button
              key={page}
              onClick={() => setActive(page)}
              className={`w-full text-left px-4 py-2 rounded-lg text-sm font-medium transition
                ${
                  active === page
                    ? "bg-[#10B981] text-white"
                    : "text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-[#1F2933]"
                }
              `}
            >
              {page}
            </button>
          ))}
        </nav>
      </aside>

      {/* Main Content */}
      <main className="flex-1 p-8">
        <h2 className="text-2xl font-semibold text-gray-900 dark:text-white">
          {active}
        </h2>
        <p className="mt-2 text-gray-600 dark:text-gray-400">
          Content for {active} page goes here.
        </p>
      </main>
    </div>
  );
}


