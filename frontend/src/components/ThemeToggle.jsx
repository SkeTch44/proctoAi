import React from "react";
import { FaToggleOn, FaToggleOff } from "react-icons/fa6";
import { useTheme } from "../App";

export default function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  return (<>
    <button
      className="text-2xl p-2 rounded-full hover:bg-gray-200 dark:hover:bg-gray-700 transition"
      title="Toggle theme"
      onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
    >
      {theme === "dark" ? <FaToggleOn className="text-[#bcbbb0]"/> : <FaToggleOff />}
    </button>
      </>
    );
}
