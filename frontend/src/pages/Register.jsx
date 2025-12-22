import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { registerUser } from "../services/Auth";

export default function Register() {
  const navigate = useNavigate();

  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState(localStorage.getItem("selected_role") || "student");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const handleRegister = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");
    setLoading(true);

    try {
      const res = await registerUser({ username, email, password, role });
      setSuccess(res.message || "Registration successful");

      // Redirect to login after short delay
      // clear selected role
      localStorage.removeItem("selected_role");
      setTimeout(() => {
        navigate("/login");
      }, 1200);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100 dark:bg-[#0F1115]">
      <div className="w-full max-w-md bg-white dark:bg-[#171A1D] p-8 rounded-2xl shadow-xl border border-gray-200 dark:border-gray-700">
        <h2 className="text-2xl font-bold text-center text-gray-900 dark:text-white mb-2">
          Create Account
        </h2>
        <p className="text-sm text-center text-gray-500 dark:text-gray-400 mb-6">
          Register to access the platform
        </p>

        {error && (
          <div className="mb-4 text-sm text-red-600 bg-red-100 dark:bg-red-900/30 p-3 rounded-lg">
            {error}
          </div>
        )}

        {success && (
          <div className="mb-4 text-sm text-green-600 bg-green-100 dark:bg-green-900/30 p-3 rounded-lg">
            {success}
          </div>
        )}

        <form onSubmit={handleRegister} className="space-y-5">
          {/* Selected role display */}
          <div className="text-sm text-gray-600 dark:text-gray-300 text-center">
            Registering as: <span className="font-semibold">{role}</span>
          </div>

          {/* Username */}
          <div>
            <label className="block text-sm font-semibold text-gray-700 dark:text-gray-100 mb-2">
              Username
            </label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              className="w-full px-4 py-3 rounded-xl border-2 border-gray-300 dark:border-gray-600
                         bg-gray-50 dark:bg-[#1A1D21]
                         text-gray-900 dark:text-gray-100
                         focus:border-[#6D28D9] dark:focus:border-[#10B981]
                         focus:ring-2 focus:ring-[#6D28D9]/20 dark:focus:ring-[#10B981]/20
                         transition-all"
            />
          </div>

          {/* Email */}
          <div>
            <label className="block text-sm font-semibold text-gray-700 dark:text-gray-100 mb-2">
              Email
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full px-4 py-3 rounded-xl border-2 border-gray-300 dark:border-gray-600
                         bg-gray-50 dark:bg-[#1A1D21]
                         text-gray-900 dark:text-gray-100
                         focus:border-[#6D28D9] dark:focus:border-[#10B981]
                         focus:ring-2 focus:ring-[#6D28D9]/20 dark:focus:ring-[#10B981]/20
                         transition-all"
            />
          </div>

          {/* Password */}
          <div>
            <label className="block text-sm font-semibold text-gray-700 dark:text-gray-100 mb-2">
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full px-4 py-3 rounded-xl border-2 border-gray-300 dark:border-gray-600
                         bg-gray-50 dark:bg-[#1A1D21]
                         text-gray-900 dark:text-gray-100
                         focus:border-[#6D28D9] dark:focus:border-[#10B981]
                         focus:ring-2 focus:ring-[#6D28D9]/20 dark:focus:ring-[#10B981]/20
                         transition-all"
            />
          </div>

          {/* Register Button */}
          <div className="bg-gradient-to-r from-purple-700 via-teal-500 to-white dark:from-green-500 dark:via-blue-500 dark:to-green-400 p-[3px] rounded-xl">
            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 rounded-2xl text-lg font-semibold
                         bg-blue-500 hover:bg-blue-600 text-white
                         dark:bg-blue-700 dark:hover:bg-blue-500
                         disabled:opacity-50 disabled:cursor-not-allowed
                         transition-all"
            >
              {loading ? "Creating account..." : "Register"}
            </button>
          </div>
        </form>

        {/* Redirect to login */}
        <p className="text-sm text-center text-gray-500 dark:text-gray-400 mt-6">
          Already have an account?{" "}
          <span
            onClick={() => navigate("/login")}
            className="text-blue-600 dark:text-blue-400 font-semibold cursor-pointer hover:underline"
          >
            Login
          </span>
        </p>
      </div>
    </div>
  );
}
