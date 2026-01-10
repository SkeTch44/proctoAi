// src/App.jsx
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { useState, useEffect, createContext, useContext } from "react";
import Home from "./pages/Home";
import LanderPage from "./pages/LanderPage";
import ThemeToggle from "./components/ThemeToggle";
import SkeletonLoader from "./components/Loader";
import Layout from "./pages/AdminPages/Layout";
import AdminRoute from "./routes/AdminRoute";
import Login from "./pages/Login";
import NotFound from "./pages/NotFound";
import Register from "./pages/Register";
// Admin pages
import DragNdrop from "./pages/AdminPages/DragNdrop";
import AIQuestionGenerator from "./pages/AdminPages/AIQuestionGenerator";
import TestCreator from "./pages/AdminPages/TestCreator";
import LiveMonitoring from "./pages/AdminPages/LiveMonitoring";
import ProctoringLogs from "./pages/AdminPages/ProctoringLogs";
import Analytics from "./pages/AdminPages/Analytics";
import Reports from "./pages/AdminPages/Reports";
import AdminDashboard from "./pages/AdminPages/AdminDashboard";
import StudentDashboard from "./pages/StudentPages/StudentDashboard";
import StudentRoute from "./routes/StudentRoute";
// Student Pages
import StartExam from "./pages/StudentPages/StartExam";
import Results from "./pages/StudentPages/Results";
import Profile from "./pages/StudentPages/Profile";
import Support from "./pages/StudentPages/Support";
import ExamRoom from './pages/StudentPages/ExamRoom';
import About from "./pages/About";


const ThemeContext = createContext();
export function useTheme() {
  return useContext(ThemeContext);
}

function App() {
  const [theme, setTheme] = useState(localStorage.getItem("theme") || "system");
  const [loading, setLoading] = useState(true);
  const [fadeOut, setFadeOut] = useState(false);

  // Simulate loading and control animation
  useEffect(() => {
    const timer = setTimeout(() => {
      setFadeOut(true);
      setTimeout(() => setLoading(false), 300);
    }, 1000);
    return () => clearTimeout(timer);
  }, []);

  // Apply theme globally
  useEffect(() => {
    const prefersDark = window.matchMedia(
      "(prefers-color-scheme: dark)"
    ).matches;
    const isDark = theme === "dark" || (theme === "system" && prefersDark);

    document.documentElement.classList.toggle("dark", isDark);
    localStorage.setItem("theme", theme);
  }, [theme]);

  return (
    <ThemeContext.Provider value={{ theme, setTheme }}>
      {loading ? (
        <div
          className={`fixed inset-0 z-50 transition-opacity duration-300 ${
            fadeOut ? "opacity-0 pointer-events-none" : "opacity-100"
          }`}
        >
          <SkeletonLoader />
        </div>
      ) : (
        <div
          className={`min-h-screen transition duration-300 ${
            theme === "dark" ? "bg-[#2A2623]" : "bg-[#FAF7F3]"
          }`}
        >
          <div className="fixed top-4 right-4 z-50">
            <ThemeToggle />
          </div>

          <Router>
            <Routes>
              {/* Public pages */}
              <Route path="/" element={<LanderPage />} />
              <Route path="/home" element={<Home />} />
              <Route path="/login" element={<Login />} />
              <Route path="/register" element={<Register />} />
              <Route path="/about" element={<About/>}/>

              {/* Admin dashboard layout with sidebar + nested pages */}
              <Route
                path="/AdminDashboard"
                element={
                  <AdminRoute>
                    <Layout />
                  </AdminRoute>
                }
              >
                <Route index element={<AdminDashboard />} />
                <Route path="documentUpload" element={<DragNdrop />} />
                <Route path="analyzer" element={<AIQuestionGenerator />} />
                <Route path="test-creator" element={<TestCreator />} />
                <Route path="admin-monitoring" element={<LiveMonitoring />} />
                <Route path="admin-logs" element={<ProctoringLogs />} />
                <Route path="admin-analytics" element={<Analytics />} />
                <Route path="compiled-reports" element={<Reports />} />
              </Route>

              {/* Student dashboard (protected) */}
              <Route
                path="/student/dashboard"
                element={
                  <StudentRoute>
                    <StudentDashboard />
                  </StudentRoute>
                }
              />

              <Route path="/student/start" element={<StudentRoute><StartExam /></StudentRoute>} />
              <Route path="/student/results" element={<StudentRoute><Results /></StudentRoute>} />
              <Route path="/student/profile" element={<StudentRoute><Profile /></StudentRoute>} />
              <Route path="/student/support" element={<StudentRoute><Support /></StudentRoute>} />
              {/* <Route path="/student/Exam-room" element={<StudentRoute><ExamRoom /></StudentRoute>} /> */}

              {/* Fallback */}
              <Route path="/student/Exam-room" element = {<ExamRoom/>}/>
              <Route path="*" element={<NotFound />} />
            </Routes>
          </Router>
        </div>
      )}
    </ThemeContext.Provider>
  );
}

export default App;
