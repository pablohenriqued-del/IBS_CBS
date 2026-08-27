import React, { useEffect, useState } from "react";
import { Moon, Sun } from "lucide-react";

/**
 * FiscalCore Mark — Monograma "FC" dentro de moldura de carimbo oficial.
 * Sensação: selo institucional / fortaleza fiscal.
 */
export function Logo({ size = 36 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 40 40"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-label="FiscalCore"
    >
      {/* Cantos de carimbo (4 L-brackets) */}
      <path d="M4 8 L4 4 L8 4" stroke="var(--accent)" strokeWidth="1" strokeLinecap="square" />
      <path d="M32 4 L36 4 L36 8" stroke="var(--accent)" strokeWidth="1" strokeLinecap="square" />
      <path d="M4 32 L4 36 L8 36" stroke="var(--accent)" strokeWidth="1" strokeLinecap="square" />
      <path d="M32 36 L36 36 L36 32" stroke="var(--accent)" strokeWidth="1" strokeLinecap="square" />

      {/* Sombra sutil no fundo (accent-dim) */}
      <rect x="9" y="9" width="22" height="22" fill="var(--accent-dim)" opacity="0.4" />

      {/* F: spine + duas barras */}
      <path d="M12 12 L12 30" stroke="var(--accent)" strokeWidth="2.6" strokeLinecap="square" />
      <path d="M12 12 L22 12" stroke="var(--accent)" strokeWidth="2.6" strokeLinecap="square" />
      <path d="M12 20 L19 20" stroke="var(--accent)" strokeWidth="2.6" strokeLinecap="square" />

      {/* C: arco entrelaçado à direita */}
      <path
        d="M30 15 A6 6 0 0 0 24 20 A6 6 0 0 0 30 25"
        stroke="var(--accent)"
        strokeWidth="2.6"
        fill="none"
        strokeLinecap="square"
      />
    </svg>
  );
}

/**
 * Pablo Duarte Mark — Monograma "PD" serifado com regra de assinatura e
 * ponto-selo. Sensação: atelier / firma autoral / senior architect.
 */
export function PabloMark({ size = 36 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 40 40"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-label="Pablo Duarte"
    >
      {/* Moldura fina superior (linha de topo — sinaliza selo autoral) */}
      <line x1="6" y1="6" x2="16" y2="6" stroke="var(--accent)" strokeWidth="1" />
      <line x1="30" y1="6" x2="34" y2="6" stroke="var(--accent)" strokeWidth="1" />

      {/* Monograma PD — serifado, itálico, Fraunces */}
      <text
        x="20"
        y="27"
        fontFamily="'Fraunces', Georgia, serif"
        fontWeight="700"
        fontStyle="italic"
        fontSize="21"
        fill="var(--accent)"
        textAnchor="middle"
        letterSpacing="-1.5"
      >
        PD
      </text>

      {/* Regra de assinatura + ponto-selo à direita */}
      <line x1="6" y1="33" x2="30" y2="33" stroke="var(--accent)" strokeWidth="0.9" />
      <circle cx="32.5" cy="33" r="1.6" fill="var(--accent)" />
    </svg>
  );
}

/**
 * BrandLockup — combinação Pablo × FiscalCore para header/footer.
 * Ordem: marca autoral primeiro, divisor, marca do produto, wordmark.
 */
export function BrandLockup({ size = 26, showWordmark = true, verbose = false }) {
  return (
    <div className="flex items-center gap-3">
      <PabloMark size={size} />
      <span
        className="h-5 w-px bg-border/80"
        style={{ height: size * 0.6 }}
        aria-hidden
      />
      <Logo size={size} />
      {showWordmark && (
        <div className="flex items-baseline gap-2 pl-1">
          <span className="font-heading font-semibold text-[17px] text-strong tracking-tight leading-none">
            FiscalCore
          </span>
          <span className="font-mono text-[10px] uppercase tracking-[0.3em] text-muted">
            motor
          </span>
        </div>
      )}
      {verbose && (
        <span className="hidden xl:inline-block font-mono text-[9px] uppercase tracking-[0.28em] text-muted pl-1 border-l border-border ml-1 pl-3">
          arquitetado por Pablo Duarte
        </span>
      )}
    </div>
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
