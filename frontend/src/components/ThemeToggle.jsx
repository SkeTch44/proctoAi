import React from "react";
import { FaSun, FaMoon } from "react-icons/fa";
import { useTheme } from "../App";

export default function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  return (
    <button
      className="text-xl p-2 rounded-full hover:bg-gray-200 dark:hover:bg-gray-700 transition"
      title="Toggle theme"
      onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
    >
      {theme === "dark" ? <FaSun /> : <FaMoon />}
    </button>
  );
}
