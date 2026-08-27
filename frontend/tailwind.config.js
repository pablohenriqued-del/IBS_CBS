module.exports = {
  content: ["./src/**/*.{js,jsx}", "./public/index.html"],
  theme: {
    extend: {
      colors: {
        bg: "var(--bg)",
        surface: "var(--surface)",
        elev: "var(--elev)",
        border: "var(--border)",
        borderHover: "var(--border-hover)",
        muted: "var(--muted)",
        text: "var(--text)",
        strong: "var(--strong)",
        accent: "var(--accent)",
        accentHover: "var(--accent-hover)",
        accentDim: "var(--accent-dim)",
        success: "var(--success)",
        error: "var(--error)",
        codeBg: "var(--code-bg)",
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
