import React from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./AuthContext";
import { Header } from "./components/Header";
import { LoginPage, ProtectedRoute } from "./components/Login";
import { PlaygroundPage } from "./components/PlaygroundPage";
import { DocumentosPage } from "./components/DocumentosPage";
import { ApuracaoPage } from "./components/ApuracaoPage";
import { AuditoriaPage } from "./components/AuditoriaPage";
import { SimuladorPage } from "./components/SimuladorPage";
import { UsuariosPage } from "./components/UsuariosPage";
import { Logo, useTheme } from "./components/Shared";

function Shell({ children }) {
  const { theme, toggle } = useTheme();
  return (
    <div className="grain min-h-screen relative">
      <Header theme={theme} onToggleTheme={toggle} />
      {children}
      <footer className="border-t border-border py-8 relative">
        <div className="max-w-[1400px] mx-auto px-6 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <Logo size={20} />
            <div>
              <div className="font-heading text-sm text-strong">FiscalCore Motor</div>
              <div className="font-mono text-[10px] uppercase tracking-[0.25em] text-muted">
                MVP · MongoDB · trilha append-only com hash encadeado
              </div>
            </div>
          </div>
          <div className="font-mono text-[11px] text-muted">
            Decimal · base por fora · resolvido por dataOperacao
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
