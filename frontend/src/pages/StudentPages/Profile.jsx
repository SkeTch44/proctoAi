import React, { useState, useEffect } from "react";
import Security from "../../components/Security";

export default function Profile() {
  const [activeTab, setActiveTab] = useState("info");
  const [userInfo, setUserInfo] = useState(null);
  const [form, setForm] = useState({
    name: "",
    fullName: "",
    studentId: "",
    phone: "",
    institution: "",
    program: "",
    year: "",
  });
  const [loading, setLoading] = useState(true);

  // FETCH USER DATA
  useEffect(() => {
    async function fetchUser() {
      try {
        const token = localStorage.getItem("token");
        if (!token) {
          setLoading(false);
          return;
        }

        const res = await fetch("http://localhost:5000/api/me", {
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
        });

        if (!res.ok) return;

        const data = await res.json();
        console.log("User data:", data);

        const mapped = {
          name: data.name || data.fullName,
          fullName: data.fullName || data.name,
          studentId: `STU${String(data.id).padStart(7, "0")}`,
          phone: data.phone || "",
          institution: data.institution || "",
          program: data.program || "",
          year: data.year || "",
        };

        setUserInfo(mapped);
        setForm(mapped);
      } catch (e) {
        console.error("Fetch error:", e);
      } finally {
        setLoading(false);
      }
    }
    fetchUser();
  }, []);

  // HANDLE INPUT CHANGE
  const handleChange = (field) => (e) => {
    setForm((prev) => ({ ...prev, [field]: e.target.value }));
  };

  // UPDATE PROFILE
  const handleUpdate = async () => {
    try {
      const token = localStorage.getItem("token");
      const res = await fetch("http://localhost:5000/api/me", {
        method: "PUT",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          fullName: form.fullName,
          phone: form.phone,
          institution: form.institution,
          program: form.program,
          year: form.year,
        }),
      });

      const result = await res.json();
      if (!res.ok) throw new Error(result.message || "Update failed");

      setUserInfo(form);
      console.log("✅ Profile updated:", result);
      alert("Profile updated successfully!");
    } catch (e) {
      console.error("Update error:", e);
      alert("Update failed: " + e.message);
    }
  };

  // Get token for Security component
  const token = localStorage.getItem("token");

  if (loading) return <div className="max-w-2xl mx-auto p-8">Loading...</div>;
  if (!userInfo)
    return <div className="max-w-2xl mx-auto p-8">No user data</div>;

  return (
    <div className="max-w-2xl mx-auto p-6">
      {/* HEADER */}
      <div className="text-center mb-12">
        <div className="w-24 h-24 bg-gradient-to-r from-blue-500 to-purple-600 rounded-3xl mx-auto mb-6 shadow-2xl border-4 border-white/50 flex items-center justify-center">
          <span className="text-3xl font-bold text-white">
            {userInfo.name.charAt(0).toUpperCase()}
          </span>
        </div>
        <h1 className="text-4xl font-bold text-gray-800 dark:text-white mb-2">
          {userInfo.name}
        </h1>
        <p className="text-lg text-gray-600 dark:text-gray-400">
          {userInfo.studentId}
        </p>
      </div>

      {/* TABS */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg border p-1 mb-8">
        <div className="flex">
          {["info", "security"].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`flex-1 py-4 px-6 text-sm font-semibold rounded-lg transition-all ${
                activeTab === tab
                  ? "bg-gradient-to-r from-blue-500 to-purple-600 text-white shadow-lg"
                  : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
              }`}
            >
              {tab === "info" ? "Profile Info" : "Security"}
            </button>
          ))}
        </div>
      </div>

      {/* INFO TAB */}
      {activeTab === "info" && (
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg border p-8 space-y-8">
          {/* READONLY INFO */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 p-6 bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-gray-700 dark:to-gray-600 rounded-2xl">
            <div>
              <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                Student ID
              </label>
              <p className="text-xl font-bold text-gray-900 dark:text-white">
                {form.studentId}
              </p>
            </div>
            <div>
              <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                Full Name
              </label>
              <input
                type="text"
                value={form.fullName}
                onChange={handleChange("fullName")}
                className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:border-gray-600 dark:text-white font-semibold"
              />
            </div>
          </div>

          {/* EDITABLE FIELDS */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
                Phone
              </label>
              <input
                type="tel"
                value={form.phone}
                onChange={handleChange("phone")}
                className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:border-gray-600 dark:text-white"
              />
            </div>
            <div>
              <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
                Institution
              </label>
              <input
                type="text"
                value={form.institution}
                onChange={handleChange("institution")}
                className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:border-gray-600 dark:text-white"
              />
            </div>
            <div>
              <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
                Program
              </label>
              <input
                type="text"
                value={form.program}
                onChange={handleChange("program")}
                className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:border-gray-600 dark:text-white"
              />
            </div>
            <div>
              <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
                Year
              </label>
              <input
                type="text"
                value={form.year}
                onChange={handleChange("year")}
                className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:border-gray-600 dark:text-white"
              />
            </div>
          </div>
          <div className="bg-gradient-to-r from-red-50 to-orange-50 dark:from-red-900/20 dark:to-orange-900/20 rounded-xl shadow-lg border border-red-200/50 dark:border-red-800/50 p-6 mt-8">
            <div className="flex items-center justify-center">
              <span className="text-red-800 dark:text-red-200 font-semibold text-sm text-center px-4">
                ⚠️ Wrong data will lead to your termination.
              </span>
            </div>
          </div>
          {/* BUTTONS */}
          <div className="flex gap-4 pt-6 border-t border-gray-200 dark:border-gray-600">
            <button
              onClick={handleUpdate}
              className="flex-1 bg-gradient-to-r from-blue-500 to-purple-600 text-white py-4 px-8 rounded-xl font-semibold shadow-lg hover:shadow-xl transition-all"
            >
              Update Profile
            </button>
            <button
              onClick={() => setForm(userInfo)}
              className="px-8 py-4 border border-blue-500 text-blue-600 bg-white hover:bg-blue-50 dark:bg-gray-700 dark:border-blue-400 dark:text-blue-400 rounded-xl font-semibold transition-all"
            >
              Reset
            </button>
          </div>
        </div>
      )}

      {/* SECURITY TAB - WORKING COMPONENT */}
      {activeTab === "security" && <Security token={token} />}
    </div>
  );
}
