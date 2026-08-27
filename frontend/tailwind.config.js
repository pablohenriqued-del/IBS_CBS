module.exports = {
  content: ["./src/**/*.{js,jsx}", "./public/index.html"],
  theme: {
    extend: {
      colors: {
        bg: "#09090B",
        surface: "#121214",
        elev: "#18181B",
        border: "#27272A",
        borderHover: "#3F3F46",
        muted: "#A1A1AA",
        text: "#FAFAFA",
        accent: "#E2FF3D",
        accentHover: "#D4F02D",
        success: "#10B981",
        error: "#EF4444",
      },
      fontFamily: {
        sans: ["'IBM Plex Sans'", "system-ui", "sans-serif"],
        heading: ["'Chivo'", "system-ui", "sans-serif"],
        mono: ["'JetBrains Mono'", "monospace"],
      },
    },
  },
  plugins: [],
};
