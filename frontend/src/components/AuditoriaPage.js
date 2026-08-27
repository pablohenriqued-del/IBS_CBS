import React, { useEffect, useState } from "react";
import { CheckCircle2, XCircle, RefreshCw, ShieldCheck, ShieldAlert, Link2 } from "lucide-react";
import { api, formatApiError } from "../api";

export function AuditoriaPage() {
  const [eventos, setEventos] = useState([]);
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [verifying, setVerifying] = useState(false);
  const [error, setError] = useState(null);

  const carregar = async () => {
    setLoading(true);
    try {
      const [ev, st] = await Promise.all([
        api.get("/v1/auditoria/ledger?limit=100"),
        api.get("/v1/auditoria/verificar"),
      ]);
      setEventos(ev.data.eventos);
      setStatus(st.data);
    } catch (e) {
      setError(formatApiError(e));
    } finally {
      setLoading(false);
    }
  };

  const verificar = async () => {
    setVerifying(true);
    try {
      const { data } = await api.get("/v1/auditoria/verificar");
      setStatus(data);
    } finally { setVerifying(false); }
  };

  useEffect(() => { carregar(); }, []);

  return (
    <div className="max-w-[1400px] mx-auto px-6 py-12">
      <div className="mb-8">
        <div className="text-[11px] font-mono uppercase tracking-[0.3em] text-muted mb-2">
          GET /api/v1/auditoria/ledger · GET /api/v1/auditoria/verificar
        </div>
        <h1 className="font-heading text-4xl tracking-tight text-strong mb-2">
          Trilha <span className="serif-italic text-accent">imutável</span>.
        </h1>
        <p className="text-muted max-w-2xl">
          Ledger append-only com <span className="font-mono text-text">SHA-256</span> encadeado.
          Cada evento aponta para o hash do anterior. Uma quebra na cadeia é evidência de
          adulteração — e o verificador aponta o exato ponto de ruptura.
        </p>
      </div>

      {error && (
        <div className="mb-6 border border-error/30 bg-error/5 rounded-md p-4 text-error font-mono text-sm">
          ⨯ {error}
        </div>
      )}

      {/* Status */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <div
          className={`border rounded-md p-5 ${
            status?.ok ? "border-success/40 bg-success/5" : status ? "border-error/40 bg-error/5" : "border-border bg-surface"
          }`}
          data-testid="integridade-card"
        >
          <div className="flex items-center gap-2 mb-2">
            {status?.ok ? (
              <CheckCircle2 className="w-5 h-5 text-success" />
            ) : status ? (
              <XCircle className="w-5 h-5 text-error" />
            ) : (
              <ShieldCheck className="w-5 h-5 text-muted" />
            )}
            <span className="text-[10px] uppercase tracking-[0.25em] text-muted">Integridade</span>
          </div>
          <div className={`font-heading text-2xl ${status?.ok ? "text-success" : status ? "text-error" : "text-muted"}`}>
            {status?.ok ? "íntegra" : status ? "quebrada" : "…"}
          </div>
          {status?.motivo && (
            <div className="text-[11.5px] text-error mt-2 font-mono">
              seq {status.broken_at}: {status.motivo}
            </div>
          )}
        </div>
        <div className="border border-border rounded-md p-5 bg-surface">
          <div className="text-[10px] uppercase tracking-[0.25em] text-muted mb-2">Total de eventos</div>
          <div className="font-heading text-2xl text-strong big-num">{status?.total ?? "—"}</div>
        </div>
        <div className="border border-border rounded-md p-5 bg-surface flex flex-col justify-between">
          <div className="text-[10px] uppercase tracking-[0.25em] text-muted mb-2">Ações</div>
          <button
            onClick={verificar}
            disabled={verifying}
            data-testid="reverificar"
            className="mt-2 border border-border rounded-md px-3 py-2 text-[12px] font-mono text-strong hover:border-accent flex items-center justify-center gap-1.5 disabled:opacity-60"
          >
            <ShieldAlert className={`w-3.5 h-3.5 ${verifying ? "animate-pulse" : ""}`} />
            re-verificar cadeia
          </button>
        </div>
      </div>

      {/* Ledger */}
      <div className="flex items-baseline justify-between mb-4">
        <h2 className="font-heading text-2xl text-strong">Eventos (mais recentes primeiro)</h2>
        <button onClick={carregar} className="text-[11px] font-mono text-muted hover:text-strong flex items-center gap-1" data-testid="reload-ledger">
          <RefreshCw className={`w-3 h-3 ${loading ? "animate-spin" : ""}`} /> recarregar
        </button>
      </div>

      <div className="border border-border rounded-md overflow-hidden bg-surface" data-testid="ledger-table">
        <div className="grid grid-cols-12 gap-3 px-4 py-2.5 border-b border-border text-[10px] uppercase tracking-[0.25em] text-muted">
          <div className="col-span-1 text-right">seq</div>
          <div className="col-span-2">timestamp</div>
          <div className="col-span-2">actor</div>
          <div className="col-span-2">action</div>
          <div className="col-span-3">payload</div>
          <div className="col-span-2 font-mono">hash</div>
        </div>
        {eventos.length === 0 && !loading && (
          <div className="p-10 text-center text-muted text-sm">
            ledger vazio
          </div>
        )}
        {eventos.map((e) => (
          <div key={e.seq} className="grid grid-cols-12 gap-3 px-4 py-2.5 border-b border-border/50 hover:bg-elev/50 text-[12px] items-start" data-testid={`event-${e.seq}`}>
            <div className="col-span-1 text-right font-mono text-[11px] text-accent tabular-nums">#{e.seq}</div>
            <div className="col-span-2 font-mono text-[10.5px] text-muted">{e.ts?.slice(0, 19).replace("T", " ")}</div>
            <div className="col-span-2 font-mono text-[11px] text-muted truncate">
              {e.actor?.email || <span className="italic">sistema</span>}
              {e.actor?.role && <span className="ml-1 text-[9px] text-accent">({e.actor.role})</span>}
            </div>
            <div className="col-span-2 font-mono text-[11px] text-strong">{e.action}</div>
            <div className="col-span-3 font-mono text-[10.5px] text-muted truncate" title={JSON.stringify(e.payload)}>
              {JSON.stringify(e.payload).slice(0, 60)}
            </div>
            <div className="col-span-2 font-mono text-[9.5px] text-muted flex items-center gap-1">
              <Link2 className="w-2.5 h-2.5 flex-shrink-0" />
              {e.hash?.slice(7, 19)}…
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
