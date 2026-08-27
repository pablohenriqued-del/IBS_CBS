import React, { useState } from "react";
import { useNavigate, Navigate } from "react-router-dom";
import { LogIn, ShieldCheck } from "lucide-react";
import { Logo } from "./Shared";
import { useAuth } from "../AuthContext";

export function LoginPage() {
  const { user, loading, login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("admin@fiscalcore.local");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  if (loading) return <div className="p-8 text-muted">Carregando…</div>;
  if (user) return <Navigate to="/" replace />;

  const onSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError("");
    const res = await login(email, password);
    setSubmitting(false);
    if (res.ok) navigate("/");
    else setError(res.error);
  };

  return (
    <div className="grain min-h-screen relative flex items-center justify-center px-6">
      <div className="hero-glow absolute inset-0 pointer-events-none" />
      <div className="relative z-10 max-w-sm w-full">
        <div className="flex items-center gap-3 mb-8">
          <Logo size={36} />
          <div>
            <div className="font-heading font-semibold text-xl text-strong tracking-tight">
              FiscalCore
            </div>
            <div className="font-mono text-[10px] uppercase tracking-[0.3em] text-muted">
              motor · v0.2.0
            </div>
          </div>
        </div>

        <h1 className="font-heading text-3xl tracking-tight text-strong mb-2">
          Bem-vindo de volta.
        </h1>
        <p className="text-[13.5px] text-muted mb-8 leading-relaxed">
          Entre com sua conta para calcular tributos, importar NF-e ou consultar a trilha
          de auditoria imutável.
        </p>

        <form onSubmit={onSubmit} className="space-y-4" data-testid="login-form">
          <label className="block">
            <span className="text-[10px] uppercase tracking-[0.25em] text-muted">E-mail</span>
            <input
              type="text"
              data-testid="login-email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 w-full bg-surface border border-border rounded-md px-3 py-2.5 text-sm font-mono focus:border-accent focus:outline-none transition-colors"
              autoComplete="email"
            />
          </label>
          <label className="block">
            <span className="text-[10px] uppercase tracking-[0.25em] text-muted">Senha</span>
            <input
              type="password"
              data-testid="login-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 w-full bg-surface border border-border rounded-md px-3 py-2.5 text-sm font-mono focus:border-accent focus:outline-none transition-colors"
              autoComplete="current-password"
            />
          </label>

          {error && (
            <div
              className="text-[12px] font-mono text-error border border-error/30 bg-error/5 rounded-md px-3 py-2"
              data-testid="login-error"
            >
              ⨯ {error}
            </div>
          )}

          <button
            type="submit"
            disabled={submitting || !password}
            data-testid="login-submit"
            className="w-full bg-accent text-bg font-semibold rounded-md py-3 flex items-center justify-center gap-2 hover:bg-accentHover hover:-translate-y-0.5 transition-transform duration-150 disabled:opacity-60 disabled:hover:translate-y-0"
          >
            <LogIn className="w-4 h-4" strokeWidth={2.5} />
            {submitting ? "Entrando…" : "Entrar"}
          </button>
        </form>

        <div className="mt-8 pt-6 border-t border-border">
          <div className="text-[10px] uppercase tracking-[0.3em] text-muted mb-2 flex items-center gap-2">
            <ShieldCheck className="w-3 h-3 text-accent" />
            credenciais MVP
          </div>
          <div className="font-mono text-[11.5px] text-muted space-y-0.5">
            <div>admin@fiscalcore.local · FiscalCore@2026</div>
          </div>
        </div>
      </div>
    </div>
  );
}

export function ProtectedRoute({ children, roles }) {
  const { user, loading } = useAuth();
  if (loading)
    return (
      <div className="p-10 text-muted font-mono text-sm cursor">verificando sessão</div>
    );
  if (!user) return <Navigate to="/login" replace />;
  if (roles && !roles.includes(user.role))
    return (
      <div className="p-10 max-w-2xl mx-auto">
        <div className="border border-error/30 bg-error/5 rounded-md p-4 text-error font-mono text-sm">
          ⨯ acesso negado — restrito a: {roles.join(", ")}
        </div>
      </div>
    );
  return children;
}
