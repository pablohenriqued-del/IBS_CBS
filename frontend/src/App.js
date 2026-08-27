import React from "react";
import { BrowserRouter, Link, Route, Routes } from "react-router-dom";
import { Linkedin } from "lucide-react";
import { AuthProvider } from "./AuthContext";
import { Header } from "./components/Header";
import { LoginPage, ProtectedRoute } from "./components/Login";
import { PlaygroundPage } from "./components/PlaygroundPage";
import { DocumentosPage } from "./components/DocumentosPage";
import { ApuracaoPage } from "./components/ApuracaoPage";
import { AuditoriaPage } from "./components/AuditoriaPage";
import { SimuladorPage } from "./components/SimuladorPage";
import { SobrePage } from "./components/SobrePage";
import { UsuariosPage } from "./components/UsuariosPage";
import { SapReconciliarPage } from "./components/SapReconciliarPage";
import { Logo, useTheme } from "./components/Shared";

function Shell({ children }) {
  const { theme, toggle } = useTheme();
  return (
    <div className="grain min-h-screen relative">
      <Header theme={theme} onToggleTheme={toggle} />
      {children}
      <footer className="border-t border-border py-10 relative mt-8">
        <div className="max-w-[1400px] mx-auto px-6">
          <div className="flex flex-wrap items-start justify-between gap-6 pb-8">
            <div className="flex items-center gap-3">
              <Logo size={26} />
              <div>
                <div className="font-heading text-sm text-strong">FiscalCore Motor</div>
                <div className="font-mono text-[10px] uppercase tracking-[0.25em] text-muted">
                  IBS · CBS · IS · trilha imutável
                </div>
              </div>
            </div>

            <div className="text-right">
              <div className="text-[9px] font-mono uppercase tracking-[0.3em] text-muted mb-1">
                Arquitetura &amp; implementação
              </div>
              <Link
                to="/sobre"
                data-testid="footer-signature"
                className="group inline-flex items-center gap-2 hover:text-accent transition-colors"
              >
                <span className="font-heading text-base text-strong group-hover:text-accent">
                  Pablo Duarte
                </span>
                <span className="font-mono text-[10px] text-muted group-hover:text-accent">
                  · Gerente de Inovação &amp; TI
                </span>
              </Link>
              <div className="mt-1.5">
                <a
                  href="https://www.linkedin.com/in/pablo-henrique-duarte-77415b5/"
                  target="_blank"
                  rel="noreferrer"
                  data-testid="footer-linkedin"
                  className="inline-flex items-center gap-1.5 text-[11px] font-mono text-muted hover:text-accent transition-colors"
                >
                  <Linkedin className="w-3 h-3" /> linkedin.com/in/pablo-henrique-duarte
                </a>
              </div>
            </div>
          </div>

          <div className="pt-4 border-t border-border flex flex-wrap items-center justify-between gap-2 font-mono text-[10.5px] text-muted">
            <span>Decimal · base por fora · resolvido por dataOperacao · hash SHA-256 encadeado</span>
            <span>v0.2.0 · Jan/2026 · MVP MongoDB</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/sobre" element={<Shell><SobrePage /></Shell>} />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <Shell><PlaygroundPage /></Shell>
              </ProtectedRoute>
            }
          />
          <Route
            path="/documentos"
            element={
              <ProtectedRoute>
                <Shell><DocumentosPage /></Shell>
              </ProtectedRoute>
            }
          />
          <Route
            path="/apuracao"
            element={
              <ProtectedRoute>
                <Shell><ApuracaoPage /></Shell>
              </ProtectedRoute>
            }
          />
          <Route
            path="/simulador"
            element={
              <ProtectedRoute>
                <Shell><SimuladorPage /></Shell>
              </ProtectedRoute>
            }
          />
          <Route
            path="/sap"
            element={
              <ProtectedRoute>
                <Shell><SapReconciliarPage /></Shell>
              </ProtectedRoute>
            }
          />
          <Route
            path="/sobre"
            element={
              <ProtectedRoute>
                <Shell><SobrePage /></Shell>
              </ProtectedRoute>
            }
          />
          <Route
            path="/auditoria"
            element={
              <ProtectedRoute roles={["auditoria", "admin"]}>
                <Shell><AuditoriaPage /></Shell>
              </ProtectedRoute>
            }
          />
          <Route
            path="/usuarios"
            element={
              <ProtectedRoute roles={["admin"]}>
                <Shell><UsuariosPage /></Shell>
              </ProtectedRoute>
            }
          />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
