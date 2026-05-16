// src/pages/AdminPages/InterviewManager.jsx
import React, { useState, useEffect } from "react";
import { API_BASE, getAuthHeader } from "../../utils/apiConfig";

export default function InterviewManager() {
  const [interviews, setInterviews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ title: "", candidate_name: "", scheduled_at: "" });
  const [copiedId, setCopiedId] = useState(null);

  const fetchInterviews = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/interviews`, { headers: getAuthHeader() });
      if (res.ok) {
        const data = await res.json();
        setInterviews(data.interviews || []);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchInterviews(); }, []);

  const handleCreate = async () => {
    if (!form.title) return alert("Title is required");
    setCreating(true);
    try {
      const res = await fetch(`${API_BASE}/api/interviews`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...getAuthHeader() },
        body: JSON.stringify(form),
      });
      const data = await res.json();
      if (data.success) {
        alert(`Interview created!\n\nSession ID: ${data.session_id}\n\nShare this with the candidate.`);
        setForm({ title: "", candidate_name: "", scheduled_at: "" });
        fetchInterviews();
      } else {
        alert(data.message || "Failed to create");
      }
    } catch (err) {
      alert("Error creating interview");
    } finally {
      setCreating(false);
    }
  };

  const copyToClipboard = (id) => {
    navigator.clipboard.writeText(id);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const statusColor = (status) => {
    if (status === "active") return "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300";
    if (status === "completed") return "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400";
    return "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300";
  };

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-8">
      {/* Header */}
      <div className="text-center">
        <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
          🎥 Interview Manager
        </h2>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Create interview sessions and share the ID with candidates
        </p>
      </div>

      {/* Create Form */}
      <div className="bg-white dark:bg-[#171A1D] border border-gray-200 dark:border-gray-700 rounded-2xl p-6 shadow-xl">
        <h3 className="text-lg font-bold text-gray-800 dark:text-gray-100 mb-4">Create New Interview</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Title</label>
            <input
              type="text"
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
              placeholder="e.g. Frontend Developer Interview"
              className="w-full px-4 py-3 rounded-xl border-2 border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-gray-100"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Candidate Name</label>
            <input
              type="text"
              value={form.candidate_name}
              onChange={(e) => setForm({ ...form, candidate_name: e.target.value })}
              placeholder="e.g. John Doe"
              className="w-full px-4 py-3 rounded-xl border-2 border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-gray-100"
            />
          </div>
          <div className="flex items-end">
            <button
              onClick={handleCreate}
              disabled={creating}
              className="w-full px-6 py-3 bg-purple-600 hover:bg-purple-700 text-white font-bold rounded-xl shadow-lg transition-all disabled:opacity-50"
            >
              {creating ? "Creating..." : "🎥 Create Interview"}
            </button>
          </div>
        </div>
      </div>

      {/* Interview List */}
      <div className="bg-white dark:bg-[#171A1D] border border-gray-200 dark:border-gray-700 rounded-2xl shadow-xl overflow-hidden">
        <div className="p-4 border-b border-gray-200 dark:border-gray-700">
          <h3 className="font-bold text-gray-800 dark:text-gray-100">
            All Interviews ({interviews.length})
          </h3>
        </div>
        <div className="divide-y divide-gray-100 dark:divide-gray-800">
          {loading ? (
            <div className="p-8 text-center text-gray-500">Loading...</div>
          ) : interviews.length === 0 ? (
            <div className="p-8 text-center text-gray-500">No interviews yet. Create one above.</div>
          ) : (
            interviews.map((iv) => (
              <div key={iv.id} className="p-4 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-800/50 transition">
                <div>
                  <div className="flex items-center gap-3">
                    <h4 className="font-bold text-gray-800 dark:text-gray-100">{iv.title}</h4>
                    <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${statusColor(iv.status)}`}>
                      {iv.status}
                    </span>
                  </div>
                  <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                    {iv.candidate_name && `Candidate: ${iv.candidate_name} • `}
                    Participants: {iv.participants?.length || 0}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <code className="px-3 py-1 bg-gray-100 dark:bg-gray-800 rounded-lg text-sm font-mono text-gray-700 dark:text-gray-300">
                    {iv.id}
                  </code>
                  <button
                    onClick={() => copyToClipboard(iv.id)}
                    className="px-3 py-1.5 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-lg text-xs font-bold hover:bg-blue-200 transition"
                  >
                    {copiedId === iv.id ? "✓ Copied" : "📋 Copy ID"}
                  </button>
                  <button
                    onClick={() => window.open(`/student/interview/${iv.id}`, '_blank')}
                    className="px-3 py-1.5 bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 rounded-lg text-xs font-bold hover:bg-purple-200 transition"
                  >
                    🎥 Join
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Instructions */}
      <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-2xl p-6">
        <h4 className="font-bold text-blue-800 dark:text-blue-200 mb-2">How it works</h4>
        <ol className="list-decimal list-inside text-sm text-blue-700 dark:text-blue-300 space-y-1">
          <li>Create an interview session above</li>
          <li>Copy the Session ID and share it with the candidate</li>
          <li>Candidate enters the ID on their Student Dashboard → "Online Interview" card</li>
          <li>Both of you join the same room — AI proctoring monitors the candidate</li>
          <li>After the interview, click "End Interview" to close the session</li>
        </ol>
      </div>
    </div>
  );
}
