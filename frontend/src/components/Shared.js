import React, { useEffect, useState } from "react";
import { Moon, Sun } from "lucide-react";

export function Logo({ size = 36 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 40 40"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden
    >
      <path
        d="M4 4 H30 L36 10 V36 H4 Z"
        stroke="var(--accent)"
        strokeWidth="1.4"
        strokeLinejoin="miter"
        fill="var(--accent-dim)"
      />
      <line x1="10" y1="14" x2="26" y2="14" stroke="var(--accent)" strokeWidth="1.6" />
      <line x1="10" y1="20" x2="22" y2="20" stroke="var(--accent)" strokeWidth="1.6" />
      <line x1="10" y1="26" x2="18" y2="26" stroke="var(--accent)" strokeWidth="1.6" />
      <circle cx="28" cy="30" r="2.2" fill="var(--accent)" />
    </svg>
  );
}

export function useTheme() {
  const [theme, setTheme] = useState(() =>
    typeof window === "undefined" ? "dark" : localStorage.getItem("fc-theme") || "dark"
  );
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("fc-theme", theme);
  }, [theme]);
  return { theme, toggle: () => setTheme((t) => (t === "dark" ? "light" : "dark")) };
}

export function ThemeToggle({ theme, onToggle }) {
  const isDark = theme === "dark";
  return (
    <button
      onClick={onToggle}
      data-testid="theme-toggle"
      aria-label={`Alternar para tema ${isDark ? "claro" : "escuro"}`}
      title={`Tema atual: ${isDark ? "escuro" : "claro"}`}
      className="relative w-11 h-6 rounded-full border border-border bg-elev hover:border-accent transition-colors flex items-center px-0.5"
    >
      <span
        className="absolute w-[18px] h-[18px] rounded-full bg-accent flex items-center justify-center transition-transform duration-300 ease-out"
        style={{
          transform: isDark ? "translateX(0px)" : "translateX(22px)",
          color: "var(--accent-text)",
        }}
      >
        {isDark ? (
          <Moon className="w-3 h-3" strokeWidth={2.5} />
        ) : (
          <Sun className="w-3 h-3" strokeWidth={2.5} />
        )}
      </span>
    </button>
  );
}

export function Metric({ label, value, sub }) {
  return (
    <div className="border border-border bg-bg rounded-md p-3">
      <div className="text-[9.5px] uppercase tracking-[0.25em] text-muted mb-1.5">{label}</div>
      <div className="big-num text-lg text-strong">{value}</div>
      {sub && <div className="font-mono text-[10.5px] text-muted mt-0.5">{sub}</div>}
    </div>
  );
}
