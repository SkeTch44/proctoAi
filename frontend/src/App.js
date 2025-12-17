import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { useState, useEffect, createContext, useContext } from "react";
import Home from "./pages/Home";
import LanderPage from "./pages/LanderPage";
import ThemeToggle from "./components/ThemeToggle";
import SkeletonLoader from "./components/Loader";
import AdminDashboard from "./pages/AdminDashboard";

// Create Theme Context
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
      setFadeOut(true); // trigger fade-out
      setTimeout(() => setLoading(false), 300); // wait for fade-out to finish
    }, 1000); // simulate load time

    return () => clearTimeout(timer);
  }, []);

  // Apply theme globally
  useEffect(() => {
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
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
            <main className="flex-grow p-6">
              <Routes>
                <Route path="/" element={<LanderPage />} />
                <Route path="/home" element={<Home />} />
                <Route path="/AdminDashboard" element = {<AdminDashboard/>}/>
              </Routes>
            </main>
          </Router>
        </div>
      )}
    </ThemeContext.Provider>
  );
}

export default App;
