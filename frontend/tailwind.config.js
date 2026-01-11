module.exports = {
  darkMode: "class",
  content: ["./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        "outline-light": "#desiredLightColorHex",
        "outline-dark": "#desiredDarkColorHex",
      },
      keyframes: {
        drop: {
          "0%": { transform: "translateY(-50px)", opacity: 0 },
          "100%": { transform: "translateY(0)", opacity: 1 },
        },
      },
      animation: {
        drop: "drop 0.3s ease-out forwards",
      },
    },
  },
  plugins: [],
};