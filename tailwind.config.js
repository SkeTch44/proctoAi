module.exports = {
  darkMode: 'class', // Use class strategy for dark mode
  theme: {
    extend: {
      colors: {
        // Custom light theme colors
        blue: {
          600: '#2563eb', // your desired light blue
          700: '#1d4ed8',
        },
        // Custom dark theme colors
        // Use CSS variables for dark mode overrides
      },
      backgroundColor: {
        // Custom backgrounds
        'light-bg': '#FAF7F3',
        'dark-bg': '#2A2623',
      },
    },
  },
  plugins: [],
}
