// src/pages/student/Support.jsx
import React, { useState } from "react";

const supportTopics = [
  { id: 1, title: "Technical Issues", icon: "🖥️", color: "blue" },
  { id: 2, title: "Exam Rules", icon: "📋", color: "green" },
  { id: 3, title: "Results Query", icon: "📊", color: "purple" },
  { id: 4, title: "Proctoring Help", icon: "🎥", color: "orange" },
  { id: 5, title: "Account Issues", icon: "👤", color: "pink" },
];

export default function Support() {
  const [selectedTopic, setSelectedTopic] = useState(null);
  const [message, setMessage] = useState("");

  return (
      <div className="max-w-4xl mx-auto">
        <header className="mb-8">
          <h1 className="text-3xl font-bold text-gray-800 dark:text-gray-100">
            Support Center
          </h1>
          <p className="text-sm text-gray-600 dark:text-gray-300 mt-1">
            Get help with exams, technical issues, or proctoring
          </p>
        </header>

        <section className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Support Topics */}
          <div className="space-y-4">
            <div className="p-6 bg-white dark:bg-[#0f1724] rounded-xl shadow border border-[#E5E7EB] dark:border-[#3B82F6]/40">
              <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-6">
                Common Issues
              </h2>
              <div className="grid grid-cols-2 gap-3">
                {supportTopics.map((topic) => (
                  <button
                    key={topic.id}
                    onClick={() => setSelectedTopic(topic)}
                    className={`p-4 rounded-xl border-2 transition-all group hover:shadow-md ${
                      selectedTopic?.id === topic.id
                        ? `border-${topic.color}-500 bg-${topic.color}-50 dark:bg-${topic.color}-900/20 text-${topic.color}-700`
                        : "border-gray-200 dark:border-[#3B82F6]/30 hover:border-[#3B82F6]/40"
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-2xl">{topic.icon}</span>
                      <span className="font-semibold text-sm">{topic.title}</span>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Quick Actions */}
            <div className="p-6 bg-gradient-to-r from-emerald-50 to-green-50 dark:from-[#013243] dark:to-[#022633] rounded-xl border border-emerald-200/50 shadow-sm space-y-4">
              <h3 className="font-semibold text-gray-800 dark:text-gray-100 flex items-center gap-2">
                <span className="h-3 w-3 rounded-full bg-emerald-500" />
                Quick Actions
              </h3>
              <div className="grid grid-cols-1 gap-2 text-sm">
                <button className="flex items-center gap-2 p-3 bg-white/70 dark:bg-[#1D1A17]/50 rounded-xl hover:bg-white dark:hover:bg-[#1D1A17]">
                  📞 Call Support: +91 1800-XXX-XXXX
                </button>
                <button className="flex items-center gap-2 p-3 bg-white/70 dark:bg-[#1D1A17]/50 rounded-xl hover:bg-white dark:hover:bg-[#1D1A17]">
                  💬 Live Chat (9 AM - 9 PM)
                </button>
                <a href="mailto:support@proctoai.com" className="flex items-center gap-2 p-3 bg-white/70 dark:bg-[#1D1A17]/50 rounded-xl hover:bg-white dark:hover:bg-[#1D1A17]">
                  ✉️ Email Support
                </a>
              </div>
            </div>
          </div>

          {/* Contact Form */}
          <div>
            <div className="p-6 bg-white dark:bg-[#0f1724] rounded-xl shadow border border-[#E5E7EB] dark:border-[#3B82F6]/40">
              <div className="flex items-center gap-3 mb-6 p-4 bg-gradient-to-r from-[#EEF2FF] to-[#E0E7FF] dark:from-[#013243] dark:to-[#022633] rounded-2xl border border-[#3B82F6]/30">
                {selectedTopic && (
                  <>
                    <span className={`text-2xl ${selectedTopic.icon}`}></span>
                    <div>
                      <h3 className="font-semibold text-gray-900 dark:text-gray-100">{selectedTopic.title}</h3>
                      <p className="text-xs text-gray-600 dark:text-gray-400">Describe your issue below</p>
                    </div>
                  </>
                )}
              </div>

              {selectedTopic ? (
                <>
                  <textarea
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    placeholder="Tell us more about your issue..."
                    rows={8}
                    className="w-full p-4 border border-[#E5E7EB] rounded-xl focus:ring-2 focus:ring-[#3B82F6] focus:border-transparent dark:bg-[#1D1A17] dark:border-[#3B82F6]/40 resize-vertical"
                  />
                  <button className="mt-4 w-full bg-gradient-to-r from-[#4F46E5] to-[#7C3AED] text-white py-3 px-6 rounded-xl font-semibold shadow-lg hover:shadow-xl transition-all">
                    Send Message
                  </button>
                </>
              ) : (
                <div className="text-center py-12">
                  <div className="w-20 h-20 bg-gray-100 dark:bg-[#1D1A17] rounded-3xl flex items-center justify-center mx-auto mb-4">
                    <span className="text-3xl">💬</span>
                  </div>
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
                    How can we help?
                  </h3>
                  <p className="text-gray-600 dark:text-gray-400 mb-6">
                    Select a topic from the left to get started
                  </p>
                </div>
              )}
            </div>
          </div>
        </section>
      </div>
  );
}
