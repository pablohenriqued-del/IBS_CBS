import React from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { ArrowUpRight, LogOut, ShieldCheck } from "lucide-react";
import { BrandLockup, ThemeToggle } from "./Shared";
import { useAuth, roleAllowed } from "../AuthContext";
import { API } from "../api";

export function Header({ theme, onToggleTheme }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const doLogout = async () => {
    await logout();
    navigate("/login");
  };

  const navItems = [
    { to: "/", label: "Playground", roles: ["fiscal", "auditoria", "admin"] },
    { to: "/documentos", label: "Documentos", roles: ["fiscal", "auditoria", "admin"] },
    { to: "/apuracao", label: "Apuração", roles: ["fiscal", "auditoria", "admin"] },
    { to: "/simulador", label: "Simulador", roles: ["fiscal", "auditoria", "admin"] },
    { to: "/sap", label: "SAP", roles: ["fiscal", "auditoria", "admin"] },
    { to: "/auditoria", label: "Auditoria", roles: ["auditoria", "admin"] },
    { to: "/usuarios", label: "Usuários", roles: ["admin"] },
    { to: "/sobre", label: "Sobre", roles: ["fiscal", "auditoria", "admin"] },
  ].filter((it) => (user ? roleAllowed(user, it.roles) : false));

  return (
    <header className="sticky top-0 z-20 backdrop-blur-md bg-bg/85 border-b border-border">
      <div className="max-w-[1400px] mx-auto px-6 py-3 flex items-center justify-between gap-6">
        <NavLink to="/" className="flex items-center gap-3 shrink-0" data-testid="header-brand">
          <BrandLockup size={26} showWordmark verbose />
        </NavLink>

        {user && (
          <nav className="hidden md:flex items-center gap-1 flex-1 justify-center">
            {navItems.map((it) => (
              <NavLink
                key={it.to}
                to={it.to}
                end={it.to === "/"}
                data-testid={`nav-${it.label.toLowerCase()}`}
                className={({ isActive }) =>
                  `text-[12.5px] font-medium px-3 py-1.5 rounded-md transition-colors ${
                    isActive
                      ? "text-accent bg-accentDim"
                      : "text-muted hover:text-strong hover:bg-elev"
                  }`
                }
              >
                {it.label}
              </NavLink>
            ))}
          </nav>
        )}

        <div className="flex items-center gap-3 shrink-0">
          <a
            href={`${API}/v1/health`}
            target="_blank"
            rel="noreferrer"
            className="hidden lg:flex text-[11px] font-mono text-muted hover:text-strong transition-colors items-center gap-1"
            data-testid="health-link"
          >
            /health
            <ArrowUpRight className="w-3 h-3" />
          </a>
          {user && (
            <>
              <span className="hidden lg:flex text-[11px] font-mono text-accent items-center gap-1.5 border border-accent/30 rounded-full px-2.5 py-1 bg-accentDim">
                <ShieldCheck className="w-3 h-3" />
                {user.role}
              </span>
              <button
                onClick={doLogout}
                data-testid="logout-btn"
                title={`Sair (${user.email})`}
                className="text-[11px] font-mono text-muted hover:text-error transition-colors flex items-center gap-1"
              >
                <LogOut className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">sair</span>
              </button>
            </>
          )}
          <ThemeToggle theme={theme} onToggle={onToggleTheme} />
        </div>
      </div>
    </header>
  );
}
