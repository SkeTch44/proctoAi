// src/components/NotificationBar.jsx
import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { FaBell } from "react-icons/fa";

const NotificationBar = () => {
  const [notifications, setNotifications] = useState([]);
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef(null);

  // Sample notifications (replace with your StatusDoodle data)
  useEffect(() => {
    // Simulate notifications
    const interval = setInterval(() => {
      const types = ["proctoring", "time_warning", "permission", "system"];
      const newNotif = {
        id: Date.now(),
        type: types[Math.floor(Math.random() * types.length)],
        message: getRandomMessage(),
        timestamp: new Date().toLocaleTimeString(),
      };
      setNotifications((prev) => [newNotif, ...prev.slice(0, 4)]); // Max 5
    }, 8000);

    return () => clearInterval(interval);
  }, []);

  const getRandomMessage = () => {
    const messages = {
      proctoring: "👁️ Proctoring active - Clear view detected",
      time_warning: "⏰ 15 minutes remaining",
      permission: "✅ Camera & mic permissions active",
      system: "🛡️ Secure session maintained",
    };
    return messages[Math.floor(Math.random() * Object.keys(messages).length)];
  };

  const dismissNotification = (id) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  };

  const toggleBar = () => setIsOpen(!isOpen);

  return (
    <div
      ref={containerRef}
      className="fixed right-16 z-[9999] w-80  pointer-events-auto flex flex-col items-end"
    >
      {/* FAB Button */}
      <motion.button
        onClick={toggleBar}
        className="w-8 h-6 border-2 border-black rounded-3xl bg-gradient-to-r from-gray-100 via-blue-400 to-purple-300  dark:bg-gradient-to-br dark:from-emerald-500 dark:via-teal-500 dark:to-blue-500 hover:shadow-emerald-500/50 border-white/20 backdrop-blur-xl flex items-center justify-center text-white text-xl font-bold shadow-xl hover:from-emerald-100 hover:via-teal-600 hover:to-blue-600 dark:hover:from-emerald-100 dark:hover:via-teal-200 dark:hover:to-blue-300 transition-all duration-300 hover:scale-110 active:scale-95"
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.98 }}
      >
        {notifications.length > 0 ? `${notifications.length}` : "Ⱉ"}
      </motion.button>

      {/* Notification Panel */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            className="mt-3 w-80 max-h-[450px] origin-bottom-right overflow-hidden rounded-3xl bg-white/95 dark:bg-slate-900/95 backdrop-blur-2xl shadow-2xl border border-emerald-200/50 dark:border-slate-700/50 -mr-2"
          >
            {/* Header */}
            <div className="p-4 border-b border-emerald-200/50 dark:border-slate-700/50 bg-gradient-to-r from-emerald-500/10 to-teal-500/10">
              <div className="flex items-center justify-between">
                <h4 className="font-bold text-lg text-gray-900 dark:text-gray-100 flex items-center gap-2">
                  Notification..!
                  <FaBell />
                </h4>
                <button
                  onClick={toggleBar}
                  className="p-1 hover:bg-emerald-200/50 rounded-full transition-colors"
                >
                  ✕
                </button>
              </div>
            </div>

            {/* Notifications List */}
            <div className="max-h-[350px] overflow-y-auto custom-scrollbar p-4 space-y-3">
              <AnimatePresence>
                {notifications.map((notif) => (
                  <motion.div
                    key={notif.id}
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -20, scale: 0.95 }}
                    className={`
          border-2 dark:border-white rounded-2xl shadow-md backdrop-blur-sm flex items-center justify-between gap-3 p-4 hover:shadow-xl transition-all duration-200 cursor-pointer group text-gray-900 dark:text-gray-100
          ${getNotifStyle(notif.type)}
        `}
                  >
                    <div className="flex items-center gap-3 flex-1 min-w-0">
                      <div className="flex-shrink-0 w-10 h-10 rounded-xl bg-white/60 dark:bg-slate-800/60 backdrop-blur flex items-center justify-center shadow-lg">
                        {getNotifIcon(notif.type)}
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="font-semibold text-sm leading-tight truncate text-gray-900 dark:text-gray-100">
                          {notif.message}
                        </p>
                        <p className="text-xs opacity-75 mt-1 text-gray-600 dark:text-gray-400">
                          {notif.timestamp}
                        </p>
                      </div>
                    </div>

                    <motion.button
                      whileHover={{ scale: 1.2 }}
                      whileTap={{ scale: 0.9 }}
                      onClick={(e) => {
                        e.stopPropagation(); // Prevent whole div click
                        dismissNotification(notif.id);
                      }}
                      className="p-2 ml-auto opacity-0 group-hover:opacity-100 hover:bg-white/50 dark:hover:bg-slate-800/50 rounded-full shadow-md hover:shadow-lg transition-all duration-200 flex-shrink-0"
                    >
                      <span className="text-lg leading-none font-bold">×</span>
                    </motion.button>
                  </motion.div>
                ))}
              </AnimatePresence>

              {notifications.length === 0 && (
                <div className="text-center py-12 opacity-50">
                  <div className="w-16 h-16 mx-auto mb-3 bg-gradient-to-br from-emerald-400/20 to-teal-400/20 rounded-2xl flex items-center justify-center">
                    <FaBell />
                  </div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    No notifications
                  </p>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

const getNotifStyle = (type) => {
  const styles = {
    proctoring:
      "border-emerald-200/50 bg-emerald-50/80 dark:bg-emerald-900/30 dark:border-emerald-400/50 dark:text-emerald-200",
    time_warning:
      "border-amber-200/50 bg-amber-50/80 dark:bg-amber-900/30 dark:border-amber-400/50 dark:text-amber-200",
    permission:
      "border-blue-200/50 bg-blue-50/80 dark:bg-blue-900/30 dark:border-blue-400/50 dark:text-blue-200",
    system:
      "border-slate-200/50 bg-slate-50/80 dark:bg-slate-800/50 dark:border-slate-600/50 dark:text-slate-200",
  };
  return styles[type] || styles.system;
};

const getNotifIcon = (type) => {
  const icons = {
    proctoring: "👁️",
    time_warning: "⏰",
    permission: "✅",
    system: "🛡️",
  };
  return icons[type] || "🔔";
};

export default NotificationBar;
