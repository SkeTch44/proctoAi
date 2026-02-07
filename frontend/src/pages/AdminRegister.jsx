import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { registerUser } from "../services/Auth";

export default function Register() {
  const navigate = useNavigate();

  const [formData, setFormData] = useState({
    username: "",
    full_name: "",  // ✅ Backend expects "full_name" (snake_case)
    email: "",
    password: "",
    role: "admin"
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [confirmAdmin, setConfirmAdmin] = useState(false);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
    // Clear error when user types
    if (error) setError("");
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");
    setLoading(true);

    // Frontend validation
    if (!formData.full_name.trim()) {
      setError("Full name is required");
      setLoading(false);
      return;
    }

    try {
      // ✅ Send EXACTLY what backend expects
      const res = await registerUser(formData); 
      setSuccess(res.message || "Registration successful");

      setTimeout(() => {
        navigate("/admin-login");
      }, 1200);
    } catch (err) {
      setError(err.message || "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100 dark:bg-[#0F1115]">
      <div className="w-full max-w-md bg-white dark:bg-[#171A1D] p-8 rounded-2xl shadow-xl border border-gray-200 dark:border-gray-700">
        <h2 className="text-2xl font-bold text-center text-gray-900 dark:text-white mb-2">
          Create Admin Account
        </h2>
        <p className="text-sm text-center text-gray-500 dark:text-gray-400 mb-6">
          Register to access admin panel
        </p>

        {error && (
          <div className="mb-4 text-sm text-red-600 bg-red-100 dark:bg-red-900/30 p-3 rounded-lg border-l-4 border-red-400">
            {error}
          </div>
        )}

        {success && (
          <div className="mb-4 text-sm text-green-600 bg-green-100 dark:bg-green-900/30 p-3 rounded-lg border-l-4 border-green-400">
            {success}
          </div>
        )}

        <form onSubmit={handleRegister} className="space-y-5">
          {/* Admin Role Badge */}
          <div className="px-4 sm:px-6 py-2 sm:py-3 bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 text-white font-semibold rounded-xl shadow-lg hover:shadow-xl transition-all text-xs border border-red-100 dark:bg-transparent dark:text-red-400 dark:border-red-100 hover:dark:bg-red-100/50 text-center">
            Registering as: <span className="font-bold">ADMIN</span>
          </div>

          {/* Username */}
          <div>
            <label className="block text-sm font-semibold text-gray-700 dark:text-gray-100 mb-2">
              Username *
            </label>
            <input
              name="username"
              type="text"
              value={formData.username}
              onChange={handleInputChange}
              required
              className="w-full px-4 py-3 rounded-xl border-2 border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-[#1A1D21] text-gray-900 dark:text-gray-100 focus:border-[#6D28D9] dark:focus:border-[#10B981] focus:ring-2 focus:ring-[#6D28D9]/20 dark:focus:ring-[#10B981]/20 transition-all font-semibold"
            />
          </div>

          {/* Full Name - BACKEND MATCH ✅ */}
          <div>
            <label className="block text-sm font-semibold text-gray-700 dark:text-gray-100 mb-2">
              Full Name * 
              <span className="text-xs text-gray-500 ml-1">(as in ID)</span>
            </label>
            <input
              name="full_name"  // ✅ Exact backend field name
              type="text"
              value={formData.full_name}
              onChange={handleInputChange}
              required
              placeholder="John Doe"
              className="w-full px-4 py-3 rounded-xl border-2 border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-[#1A1D21] text-gray-900 dark:text-gray-100 focus:border-[#6D28D9] dark:focus:border-[#10B981] focus:ring-2 focus:ring-[#6D28D9]/20 dark:focus:ring-[#10B981]/20 transition-all font-semibold"
            />
          </div>

          {/* Email */}
          <div>
            <label className="block text-sm font-semibold text-gray-700 dark:text-gray-100 mb-2">
              Email *
            </label>
            <input
              name="email"
              type="email"
              value={formData.email}
              onChange={handleInputChange}
              required
              className="w-full px-4 py-3 rounded-xl border-2 border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-[#1A1D21] text-gray-900 dark:text-gray-100 focus:border-[#6D28D9] dark:focus:border-[#10B981] focus:ring-2 focus:ring-[#6D28D9]/20 dark:focus:ring-[#10B981]/20 transition-all font-semibold"
            />
          </div>

          {/* Password */}
          <div>
            <label className="block text-sm font-semibold text-gray-700 dark:text-gray-100 mb-2">
              Password *
            </label>
            <input
              name="password"
              type="password"
              value={formData.password}
              onChange={handleInputChange}
              required
              minLength={6}
              className="w-full px-4 py-3 rounded-xl border-2 border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-[#1A1D21] text-gray-900 dark:text-gray-100 focus:border-[#6D28D9] dark:focus:border-[#10B981] focus:ring-2 focus:ring-[#6D28D9]/20 dark:focus:ring-[#10B981]/20 transition-all font-semibold"
            />
          </div>

          {/* Admin Confirmation */}
          <div className="flex items-center p-3 bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-700 rounded-xl">
            <input
              type="checkbox"
              id="confirmAdmin"
              checked={confirmAdmin}
              onChange={(e) => setConfirmAdmin(e.target.checked)}
              className="w-5 h-5 text-orange-600 bg-gray-100 border-gray-300 rounded focus:ring-orange-500 dark:focus:ring-orange-400"
            />
            <label htmlFor="confirmAdmin" className="ml-3 text-sm font-semibold text-gray-900 dark:text-gray-100 cursor-pointer select-none">
              ✅ I confirm registering as <span className="text-orange-700 font-bold">Admin</span> with institutional authority
            </label>
          </div>

          {/* Submit Button */}
          <div className="bg-gradient-to-r from-purple-700 via-teal-500 to-white dark:from-green-500 dark:via-blue-500 dark:to-green-400 p-[3px] rounded-xl">
            <button
              type="submit"
              disabled={loading || !confirmAdmin || !formData.full_name.trim()}
              className="w-full py-3 rounded-2xl text-lg font-bold bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white shadow-xl hover:shadow-2xl transition-all disabled:opacity-50 disabled:cursor-not-allowed transform disabled:transform-none hover:-translate-y-0.5"
            >
              {loading ? (
                <>
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white inline" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Creating Account...
                </>
              ) : (
                "🚀 Register Admin Account"
              )}
            </button>
          </div>
        </form>

        <p className="text-sm text-center text-gray-500 dark:text-gray-400 mt-6 pt-4 border-t border-gray-200 dark:border-gray-600">
          Already have an account?{" "}
          <button
            onClick={() => navigate("/admin-login")}
            className="text-blue-600 dark:text-blue-400 font-semibold hover:underline transition-all"
          >
            Login Now →
          </button>
        </p>
      </div>
    </div>
  );
}
