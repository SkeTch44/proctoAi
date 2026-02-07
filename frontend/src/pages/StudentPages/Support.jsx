<<<<<<< HEAD
import React, { useState, useEffect } from "react";
import { getToken } from "../../utils/authStorage";

export default function Support() {
  const [activeCategory, setActiveCategory] = useState("faq");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedArticle, setSelectedArticle] = useState(null);
  const [tickets, setTickets] = useState([]);
  const [ticketForm, setTicketForm] = useState({
    type: "general",
    subject: "",
    message: ""
  });
  const [submitting, setSubmitting] = useState(false);
  const [submitStatus, setSubmitStatus] = useState("");

  // Fetch user tickets
  useEffect(() => {
    fetchTickets();
  }, []);

  const fetchTickets = async () => {
    try {
      const token = getToken();
      const res = await fetch("http://localhost:5000/api/support/tickets", {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setTickets(data.tickets || []);
      }
    } catch (e) {
      console.error("Failed to fetch tickets:", e);
    }
  };

  const handleSubmitTicket = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setSubmitStatus("");

    try {
      const token = getToken();
      const res = await fetch("http://localhost:5000/api/support/tickets", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify(ticketForm)
      });

      if (res.ok) {
        setSubmitStatus("✅ Ticket submitted successfully! We'll respond within 24 hours.");
        setTicketForm({ type: "general", subject: "", message: "" });
        fetchTickets(); // Refresh tickets list
        setTimeout(() => setSubmitStatus(""), 5000);
      } else {
        setSubmitStatus("❌ Failed to submit ticket. Please try again.");
      }
    } catch (e) {
      setSubmitStatus("❌ Network error. Please check your connection.");
    } finally {
      setSubmitting(false);
    }
  };

  // Static FAQ (same as before)
  const faqCategories = {
    faq: { title: "Frequently Asked Questions", articles: [/* ... same FAQ data ... */] },
    technical: { title: "Technical Issues", articles: [/* ... */] },
    policy: { title: "Exam Policies", articles: [/* ... */] }
  };

  const filteredArticles = faqCategories[activeCategory]?.articles.filter(article =>
    article.question.toLowerCase().includes(searchQuery.toLowerCase())
  ) || [];

  return (
    <div className="max-w-4xl mx-auto p-6">
      {/* Header */}
      <div className="text-center mb-12">
        <div className="w-20 h-20 bg-gradient-to-r from-blue-500 to-purple-600 rounded-3xl mx-auto mb-6 shadow-2xl flex items-center justify-center">
          <svg className="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <h1 className="text-4xl font-black bg-gradient-to-r from-gray-900 via-blue-900 to-purple-900 bg-clip-text text-transparent dark:from-blue-400 dark:via-purple-400 dark:to-pink-400 mb-3">
          Help & Support
        </h1>
      </div>

      {/* Submit Report Form */}
      <div className="bg-gradient-to-r from-orange-50 to-red-50 dark:from-orange-900/20 dark:to-red-900/20 rounded-2xl border border-orange-200/50 p-8 mb-8 shadow-xl">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-6 flex items-center gap-3">
          📝 Submit Support Request
        </h2>
        
        {submitStatus && (
          <div className={`p-4 rounded-xl mb-6 text-sm font-semibold ${
            submitStatus.includes("✅") 
              ? "bg-green-100 dark:bg-green-900/30 border border-green-300 dark:border-green-700 text-green-700 dark:text-green-200"
              : "bg-red-100 dark:bg-red-900/30 border border-red-300 dark:border-red-700 text-red-700 dark:text-red-200"
          }`}>
            {submitStatus}
          </div>
        )}

        <form onSubmit={handleSubmitTicket} className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
              Issue Type *
            </label>
            <select
              value={ticketForm.type}
              onChange={(e) => setTicketForm({...ticketForm, type: e.target.value})}
              className="w-full px-4 py-3 border-2 border-gray-300 dark:border-gray-600 rounded-xl focus:ring-2 focus:ring-orange-500 focus:border-transparent dark:bg-gray-700 dark:text-white font-semibold"
              required
            >
              <option value="technical">Technical Issue</option>
              <option value="policy">Exam Policy</option>
              <option value="general">General Support</option>
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
              Subject *
            </label>
            <input
              type="text"
              value={ticketForm.subject}
              onChange={(e) => setTicketForm({...ticketForm, subject: e.target.value})}
              className="w-full px-4 py-3 border-2 border-gray-300 dark:border-gray-600 rounded-xl focus:ring-2 focus:ring-orange-500 focus:border-transparent dark:bg-gray-700 dark:text-white font-semibold"
              placeholder="e.g. Camera not working"
              required
            />
          </div>
          
          <div className="md:col-span-2">
            <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
              Description *
            </label>
            <textarea
              rows={4}
              value={ticketForm.message}
              onChange={(e) => setTicketForm({...ticketForm, message: e.target.value})}
              className="w-full px-4 py-3 border-2 border-gray-300 dark:border-gray-600 rounded-xl focus:ring-2 focus:ring-orange-500 focus:border-transparent dark:bg-gray-700 dark:text-white font-semibold resize-vertical"
              placeholder="Describe your issue in detail..."
              required
            />
          </div>
          
          <button
            type="submit"
            disabled={submitting || !ticketForm.subject || !ticketForm.message}
            className="md:col-span-2 bg-gradient-to-r from-orange-500 to-orange-600 hover:from-orange-600 hover:to-orange-700 text-white py-4 px-8 rounded-2xl font-bold text-lg shadow-xl hover:shadow-2xl transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {submitting ? "Submitting..." : "Submit Support Request"}
          </button>
        </form>
      </div>

      {/* Recent Tickets */}
      {tickets.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-lg border p-6 mb-8">
          <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
            Your Recent Tickets ({tickets.length})
          </h3>
          <div className="space-y-3 max-h-64 overflow-y-auto">
            {tickets.slice(0, 5).map((ticket) => (
              <div key={ticket.id} className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-xl border-l-4 border-blue-500">
                <div className="flex justify-between items-start mb-2">
                  <h4 className="font-semibold text-gray-900 dark:text-white">{ticket.subject}</h4>
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                    ticket.status === 'open' ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/50 dark:text-yellow-200' :
                    ticket.status === 'resolved' ? 'bg-green-100 text-green-800 dark:bg-green-900/50 dark:text-green-200' :
                    'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200'
                  }`}>
                    {ticket.status}
                  </span>
                </div>
                <p className="text-sm text-gray-600 dark:text-gray-300 mb-2 line-clamp-2">
                  {ticket.message}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {new Date(ticket.created_at).toLocaleDateString()}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Quick Actions - WORKING BUTTONS */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {[
          // {
          //   icon: "📞",
          //   title: "Live Chat",
          //   description: "Instant help 24/7",
          //   onClick: () => window.open("https://tawk.to/your-chat-id", "_blank")
          // },
          {
            icon: "📧", 
            title: "Email Support",
            description: "Detailed assistance",
            onClick: () => window.location.href = "mailto:support@examplatform.com"
            // the mail id where we will receive the Data, we need to update that 
          },
          {
            icon: "📱",
            title: "Call Support",
            description: "Phone assistance",
            onClick: () => window.open("tel:+911234567890")
          }
        ].map((action, idx) => (
          <button
            key={idx}
            onClick={action.onClick}
            className="group w-full p-6 bg-gradient-to-r from-emerald-50 to-blue-50 dark:from-emerald-900/20 dark:to-blue-900/20 rounded-2xl border border-emerald-200/50 shadow-sm hover:shadow-xl hover:-translate-y-2 transition-all cursor-pointer h-full flex flex-col items-center text-center"
          >
            <div className="text-4xl mb-4 group-hover:scale-110 transition-transform">{action.icon}</div>
            <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-2 group-hover:text-emerald-600">
              {action.title}
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-6 flex-1">
              {action.description}
            </p>
            <span className="px-4 py-2 bg-gradient-to-r from-emerald-500 to-blue-600 text-white rounded-xl font-semibold text-sm shadow-lg hover:shadow-xl transition-all">
              Connect Now
            </span>
          </button>
        ))}
      </div>
    </div>
=======
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
>>>>>>> rohan
  );
}
