// src/pages/student/Profile.jsx
import React, { useState } from "react";

export default function Profile() {
  const [activeTab, setActiveTab] = useState("info");

  const userInfo = {
    name: "Rahul Sharma",
    email: "rahul.sharma@example.com",
    studentId: "STU2025001",
    phone: "+91 98765 43210",
    institution: "Delhi Technical University",
    program: "B.Tech Computer Science",
    year: "3rd Year",
    avatar: "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=150&h=150&fit=crop&crop=face"
  };

  return (
      <div className="max-w-2xl mx-auto">
        <header className="mb-8 text-center">
          <div className="inline-flex items-center justify-center w-24 h-24 bg-gradient-to-r from-blue-500 to-purple-600 rounded-3xl shadow-2xl mb-6 border-4 border-white/50 dark:border-[#3B82F6]/50">
            <img 
              src={userInfo.avatar} 
              alt="Profile" 
              className="w-20 h-20 rounded-2xl object-cover shadow-lg"
            />
          </div>
          <h1 className="text-3xl font-bold text-gray-800 dark:text-gray-100 mb-2">
            {userInfo.name}
          </h1>
          <p className="text-sm text-gray-600 dark:text-gray-300">
            {userInfo.studentId} • {userInfo.program}
          </p>
        </header>

        {/* Tab Navigation */}
        <div className="bg-white dark:bg-[#0f1724] rounded-xl shadow border border-[#E5E7EB] dark:border-[#3B82F6]/40 p-1 mb-8">
          <div className="flex bg-transparent rounded-xl">
            {["info", "security", "activity"].map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`flex-1 py-3 px-4 text-sm font-semibold rounded-lg transition-all ${
                  activeTab === tab
                    ? "bg-gradient-to-r from-[#4F46E5] to-[#7C3AED] text-white shadow-lg"
                    : "text-gray-700 dark:text-gray-300 hover:text-[#6D28D9] hover:bg-[#EEF2FF] dark:hover:bg-[#013243]"
                }`}
              >
                {tab === "info" ? "Profile Info" : tab === "security" ? "Security" : "Activity"}
              </button>
            ))}
          </div>
        </div>

        {/* Tab Content */}
        <div className="space-y-6">
          {activeTab === "info" && (
            <div className="p-6 bg-white dark:bg-[#0f1724] rounded-xl shadow border border-[#E5E7EB] dark:border-[#3B82F6]/40 space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">Full Name</label>
                  <input type="text" value={userInfo.name} className="w-full px-4 py-3 border border-[#E5E7EB] rounded-xl focus:ring-2 focus:ring-[#3B82F6] focus:border-transparent dark:bg-[#1D1A17] dark:border-[#3B82F6]/40" />
                </div>
                <div>
                  <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">Student ID</label>
                  <input type="text" value={userInfo.studentId} className="w-full px-4 py-3 border border-[#E5E7EB] rounded-xl focus:ring-2 focus:ring-[#3B82F6] focus:border-transparent dark:bg-[#1D1A17] dark:border-[#3B82F6]/40" />
                </div>
                <div>
                  <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">Email</label>
                  <input type="email" value={userInfo.email} className="w-full px-4 py-3 border border-[#E5E7EB] rounded-xl focus:ring-2 focus:ring-[#3B82F6] focus:border-transparent dark:bg-[#1D1A17] dark:border-[#3B82F6]/40" />
                </div>
                <div>
                  <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">Phone</label>
                  <input type="tel" value={userInfo.phone} className="w-full px-4 py-3 border border-[#E5E7EB] rounded-xl focus:ring-2 focus:ring-[#3B82F6] focus:border-transparent dark:bg-[#1D1A17] dark:border-[#3B82F6]/40" />
                </div>
              </div>
              <div className="flex gap-3 pt-4 border-t border-[#E5E7EB] dark:border-[#3B82F6]/40">
                <button className="flex-1 bg-gradient-to-r from-[#4F46E5] to-[#7C3AED] text-white py-3 px-6 rounded-xl font-semibold shadow-lg hover:shadow-xl transition-all">
                  Update Profile
                </button>
                <button className="px-6 py-3 border border-[#3B82F6]/40 text-[#3B82F6] bg-[#EEF2FF] rounded-xl font-semibold hover:bg-[#E0E7FF] dark:bg-[#013243] dark:text-[#0fc1a0] transition">
                  Cancel
                </button>
              </div>
            </div>
          )}

          {activeTab === "security" && (
            <div className="p-6 bg-gradient-to-r from-orange-50 to-red-50 dark:from-orange-900/20 dark:to-red-900/20 rounded-2xl border border-orange-200/50 shadow-sm space-y-4">
              <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100">
                Account Security
              </h2>
              <div className="space-y-3">
                <div className="flex items-center justify-between p-4 bg-white/60 dark:bg-[#1D1A17]/50 rounded-xl border border-[#3B82F6]/20">
                  <div>
                    <p className="font-semibold text-gray-900 dark:text-gray-100">Password</p>
                    <p className="text-sm text-gray-600 dark:text-gray-300">Last changed 3 months ago</p>
                  </div>
                  <button className="px-4 py-2 bg-orange-500 text-white rounded-xl text-sm font-medium hover:bg-orange-600">
                    Change
                  </button>
                </div>
                <div className="flex items-center justify-between p-4 bg-white/60 dark:bg-[#1D1A17]/50 rounded-xl border border-[#3B82F6]/20">
                  <div>
                    <p className="font-semibold text-gray-900 dark:text-gray-100">2FA</p>
                    <p className="text-sm text-gray-600 dark:text-gray-300">Disabled</p>
                  </div>
                  <button className="px-4 py-2 bg-green-500 text-white rounded-xl text-sm font-medium hover:bg-green-600">
                    Enable
                  </button>
                </div>
                <div className="p-4 bg-white/60 dark:bg-[#1D1A17]/50 rounded-xl border border-[#3B82F6]/20">
                  <p className="text-sm text-gray-700 dark:text-gray-300">
                    Last login: Dec 23, 2025 5:46 PM from Delhi, IN
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
  );
}
