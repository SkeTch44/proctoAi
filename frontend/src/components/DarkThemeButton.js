const DarkThemeButton = ({ theme }) => {
  return (
    <button
      className={`px-4 py-2 rounded-lg transition duration-300 ${
        theme === "dark" ? "bg-gray-700 text-white" : "bg-blue-500 text-black"
      }`}
    >
      Click Me
    </button>
  );
};

export default DarkThemeButton;