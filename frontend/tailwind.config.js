module.exports = {
  content: ["./src/**/*.{js,jsx}", "./public/index.html"],
  theme: {
    extend: {
      colors: {
        bg: "#0A0B0D",
        surface: "#111316",
        elev: "#171A1E",
        border: "#22262A",
        borderHover: "#333941",
        muted: "#7E8288",
        text: "#ECECEC",
        strong: "#FAFAFA",
        accent: "#D4A574",
        accentHover: "#E0B586",
        accentDim: "rgba(212,165,116,0.12)",
        success: "#67B885",
        error: "#E76F63",
        paper: "#F5EFE4",
      },
      fontFamily: {
        sans: ["'IBM Plex Sans'", "system-ui", "sans-serif"],
        heading: ["'Fraunces'", "Georgia", "serif"],
        display: ["'Chivo'", "system-ui", "sans-serif"],
        mono: ["'JetBrains Mono'", "monospace"],
      },
      letterSpacing: {
        tightest: "-0.045em",
      },
    },
  },
  plugins: [],
};
