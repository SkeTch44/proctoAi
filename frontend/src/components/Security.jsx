import React, { useState, useEffect } from "react";

export default function Security({ token }) {
  const [passwordForm, setPasswordForm] = useState({
    current: "",
    new: "",
    confirm: "",
    loading: false,
    error: "",
    success: ""
  });
  
  const [passwordChangedAt, setPasswordChangedAt] = useState(null);

  // Password visibility states
  const [showCurrent, setShowCurrent] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  // Fetch profile data including password_changed_at
  useEffect(() => {
    async function fetchProfile() {
      try {
        const res = await fetch("http://localhost:5000/api/me", {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const data = await res.json();
          setPasswordChangedAt(data.password_changed_at);
        }
      } catch (e) {
        console.error("Failed to fetch profile:", e);
      }
    }
    if (token) fetchProfile();
  }, [token]);

  const handlePasswordSubmit = async (e) => {
    e.preventDefault();
    
    // Validation
    if (passwordForm.new !== passwordForm.confirm) {
      setPasswordForm(prev => ({...prev, error: "New passwords don't match"}));
      return;
    }
    
    if (passwordForm.new.length < 6) {
      setPasswordForm(prev => ({...prev, error: "New password must be at least 6 characters"}));
      return;
    }

    setPasswordForm(prev => ({...prev, loading: true, error: "", success: ""}));

    try {
      const res = await fetch("http://localhost:5000/api/me/password", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          current_password: passwordForm.current,
          new_password: passwordForm.new,
        }),
      });

      const result = await res.json();
      
      if (!res.ok) throw new Error(result.message || "Password change failed");

      // Update timestamp immediately
      setPasswordChangedAt(new Date().toISOString());
      
      setPasswordForm({
        current: "",
        new: "",
        confirm: "",
        loading: false,
        error: "",
        success: "Password updated successfully!"
      });
      
      // Clear success message after 3 seconds
      setTimeout(() => {
        setPasswordForm(prev => ({...prev, success: ""}));
      }, 3000);

    } catch (error) {
      setPasswordForm(prev => ({
        ...prev, 
        loading: false, 
        error: error.message
      }));
    }
  };

  // Password visibility toggles
  const toggleCurrentVisibility = () => setShowCurrent(!showCurrent);
  const toggleNewVisibility = () => setShowNew(!showNew);
  const toggleConfirmVisibility = () => setShowConfirm(!showConfirm);

  // Format timestamp for display
  const formatDate = (timestamp) => {
    if (!timestamp) return "Never";
    return new Date(timestamp).toLocaleString('en-IN', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: true
    });
  };

  // Reusable Password Input Component
  const PasswordInput = ({ 
    label, 
    value, 
    onChange, 
    showPassword, 
    toggleVisibility,
    placeholder = "",
    minLength = 0
  }) => (
    <div className="relative">
      <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
        {label} *
      </label>
      <input
        type={showPassword ? "text" : "password"}
        value={value}
        onChange={onChange}
        required
        minLength={minLength}
        placeholder={placeholder}
        className="w-full pl-12 pr-12 py-3 rounded-xl border-2 border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:border-orange-500 focus:ring-2 focus:ring-orange-500/20 transition-all"
      />
      <button
        type="button"
        onClick={toggleVisibility}
        className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition-colors"
        tabIndex={-1}
      >
        {showPassword ? (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
          </svg>
        ) : (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.878 9.878L3 3m6.878 6.878L21 21" />
          </svg>
        )}
      </button>
    </div>
  );

  return (
    <div className="bg-gradient-to-r from-orange-50 to-red-50 dark:from-orange-900/20 dark:to-red-900/20 rounded-2xl border p-8">
      <h2 className="text-2xl font-bold text-gray-800 dark:text-white mb-8">Account Security</h2>
      
      <div className="space-y-6">
        {/* Password Change Form */}
        <div className="p-6 bg-white/60 dark:bg-gray-700/50 rounded-xl border">
          <div className="flex items-center justify-between mb-6 pb-4 border-b border-gray-200 dark:border-gray-600">
            <div>
              <p className="font-semibold text-lg text-gray-900 dark:text-white">Change Password</p>
              <p className="text-sm text-gray-600 dark:text-gray-400">Update your account password securely</p>
            </div>
          </div>

          {/* Error/Success Messages */}
          {passwordForm.error && (
            <div className="mb-4 p-3 bg-red-100 dark:bg-red-900/30 border border-red-300 dark:border-red-700 rounded-xl text-red-700 dark:text-red-200 text-sm">
              {passwordForm.error}
            </div>
          )}
          {passwordForm.success && (
            <div className="mb-4 p-3 bg-green-100 dark:bg-green-900/30 border border-green-300 dark:border-green-700 rounded-xl text-green-700 dark:text-green-200 text-sm">
              {passwordForm.success}
            </div>
          )}

          {/* Password Form */}
          <form onSubmit={handlePasswordSubmit} className="space-y-4">
            <PasswordInput
              label="Current Password"
              value={passwordForm.current}
              onChange={(e) => setPasswordForm(prev => ({...prev, current: e.target.value}))}
              showPassword={showCurrent}
              toggleVisibility={toggleCurrentVisibility}
            />

            <PasswordInput
              label="New Password"
              value={passwordForm.new}
              onChange={(e) => setPasswordForm(prev => ({...prev, new: e.target.value}))}
              showPassword={showNew}
              toggleVisibility={toggleNewVisibility}
              placeholder="At least 6 characters"
              minLength={6}
            />

            <PasswordInput
              label="Confirm New Password"
              value={passwordForm.confirm}
              onChange={(e) => setPasswordForm(prev => ({...prev, confirm: e.target.value}))}
              showPassword={showConfirm}
              toggleVisibility={toggleConfirmVisibility}
              placeholder="Re-enter new password"
            />

            <button
              type="submit"
              disabled={passwordForm.loading}
              className="w-full mt-6 bg-gradient-to-r from-orange-500 to-orange-600 hover:from-orange-600 hover:to-orange-700 text-white py-3 px-6 rounded-xl font-semibold shadow-lg hover:shadow-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {passwordForm.loading ? "Updating Password..." : "Update Password"}
            </button>
          </form>

          {/* ✅ PASSWORD CHANGE TIMESTAMP */}
          <div className="mt-8 pt-6 border-t border-gray-200 dark:border-gray-600">
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">
              Password History
            </p>
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-600 dark:text-gray-300">Last changed:</span>
              <span className="font-semibold text-gray-900 dark:text-white">
                {formatDate(passwordChangedAt)}
              </span>
            </div>
          </div>
        </div>

        {/* 2FA Placeholder */}
        <div className="p-6 bg-white/60 dark:bg-gray-700/50 rounded-xl border opacity-60">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-semibold text-lg text-gray-900 dark:text-white">Two-Factor Authentication</p>
              <p className="text-sm text-gray-600 dark:text-gray-400">Add extra layer of security</p>
            </div>
            <div className="px-4 py-2 bg-gray-100 dark:bg-gray-700 rounded-lg text-sm font-medium text-gray-600 dark:text-gray-400">
              Coming Soon
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
