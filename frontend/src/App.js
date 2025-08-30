import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Home from "./pages/Home";
import { useState, useEffect, createContext, useContext } from "react";
import ThemeToggle from "./components/ThemeToggle";

// Create Theme Context
const ThemeContext = createContext();

export function useTheme() {
  return useContext(ThemeContext);
}

function App() {
  const [theme, setTheme] = useState(localStorage.getItem("theme") || "system");

  // Apply theme globally to <html>
  useEffect(() => {
    if (
      theme === "dark" ||
      (theme === "system" &&
        window.matchMedia("(prefers-color-scheme: dark)").matches)
    ) {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
    localStorage.setItem("theme", theme);
  }, [theme]);

  return (
    <ThemeContext.Provider value={{ theme, setTheme }}>
      <div
        className={`min-h-screen transition duration-300 ${
          theme === "dark"
            ? "bg-[#2A2623]"
            : "bg-[#FAF7F3]"
        }`}
      >
        <div className="fixed top-4 right-4 z-50">
          <ThemeToggle />
        </div>
        <Router>
          <main className="flex-grow p-6">
            <Routes>
              <Route path="/" element={<Home />} />
            </Routes>
          </main>
        </Router>
      </div>
    </ThemeContext.Provider>
  );
}

export default App;