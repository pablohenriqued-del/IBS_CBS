import React, { useState } from "react";
import { Calculator, ArrowDownToLine, ArrowUpFromLine, Equal } from "lucide-react";
import { api, formatApiError } from "../api";
import { Metric } from "./Shared";

export function ApuracaoPage() {
  const today = new Date();
  const firstDay = new Date(today.getFullYear(), today.getMonth(), 1).toISOString().slice(0, 10);
  const lastDay = new Date(today.getFullYear(), today.getMonth() + 1, 0).toISOString().slice(0, 10);

  const [dataInicio, setDataInicio] = useState("2026-08-01");
  const [dataFim, setDataFim] = useState("2026-08-31");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const apurar = async () => {
    setLoading(true); setError(null); setResult(null);
    try {
      const { data } = await api.post("/v1/apuracao/periodo", { dataInicio, dataFim });
      setResult(data);
    } catch (e) {
      setError(formatApiError(e));
    } finally { setLoading(false); }
  };

  return (
    <div className="max-w-[1400px] mx-auto px-6 py-12">
      <div className="mb-8">
        <div className="text-[11px] font-mono uppercase tracking-[0.3em] text-muted mb-2">
          POST /api/v1/apuracao/periodo
        </div>
        <h1 className="font-heading text-4xl tracking-tight text-strong mb-2">
          Apuração por <span className="serif-italic text-accent">período</span>.
        </h1>
        <p className="text-muted max-w-2xl">
          Débitos das saídas menos créditos das entradas, por competência.
          Todos os documentos com <span className="font-mono text-text">dataOperacao</span> no
          intervalo entram na conta.
        </p>
      </div>

      <div className="border border-border rounded-md p-5 bg-surface mb-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
          <label>
            <span className="text-[10px] uppercase tracking-[0.25em] text-muted">Data início</span>
            <input
              type="date" value={dataInicio} onChange={(e) => setDataInicio(e.target.value)}
              data-testid="apuracao-inicio"
              className="mt-1 w-full bg-bg border border-border rounded-md px-3 py-2 text-sm font-mono focus:border-accent focus:outline-none" />
          </label>
          <label>
            <span className="text-[10px] uppercase tracking-[0.25em] text-muted">Data fim</span>
            <input
              type="date" value={dataFim} onChange={(e) => setDataFim(e.target.value)}
              data-testid="apuracao-fim"
              className="mt-1 w-full bg-bg border border-border rounded-md px-3 py-2 text-sm font-mono focus:border-accent focus:outline-none" />
          </label>
          <button
            onClick={apurar} disabled={loading} data-testid="apurar-btn"
            className="bg-accent text-bg font-semibold rounded-md py-2.5 flex items-center justify-center gap-2 hover:bg-accentHover hover:-translate-y-0.5 transition-transform duration-150 disabled:opacity-60 disabled:hover:translate-y-0">
            <Calculator className="w-4 h-4" strokeWidth={2.5} />
            {loading ? "Apurando…" : "Apurar período"}
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-6 border border-error/30 bg-error/5 rounded-md p-4 text-error font-mono text-sm">
          ⨯ {error}
        </div>
      )}

      {result && (
        <div className="space-y-6 reveal">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Débitos */}
            <div className="border border-border rounded-md bg-surface p-5" data-testid="debitos-card">
              <div className="flex items-center gap-2 mb-4">
                <ArrowUpFromLine className="w-4 h-4 text-accent" />
                <span className="text-[10px] uppercase tracking-[0.3em] text-accent">Débitos (saídas)</span>
                <span className="ml-auto text-[11px] font-mono text-muted">
                  {result.debitos.documentos} doc{result.debitos.documentos !== 1 && "s"}
                </span>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <Metric label="Base" value={`R$ ${result.debitos.base}`} />
                <Metric label="CBS" value={`R$ ${result.debitos.cbs}`} />
                <Metric label="IBS-UF" value={`R$ ${result.debitos.ibsUF}`} />
                <Metric label="IBS-Mun" value={`R$ ${result.debitos.ibsMunicipio}`} />
                <Metric label="IBS total" value={`R$ ${result.debitos.ibs}`} />
                <Metric label="IS" value={`R$ ${result.debitos.impostoSeletivo}`} />
              </div>
            </div>
            {/* Créditos */}
            <div className="border border-border rounded-md bg-surface p-5" data-testid="creditos-card">
              <div className="flex items-center gap-2 mb-4">
                <ArrowDownToLine className="w-4 h-4 text-success" />
                <span className="text-[10px] uppercase tracking-[0.3em] text-success">Créditos (entradas)</span>
                <span className="ml-auto text-[11px] font-mono text-muted">
                  {result.creditos.documentos} doc{result.creditos.documentos !== 1 && "s"}
                </span>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <Metric label="Base" value={`R$ ${result.creditos.base}`} />
                <Metric label="CBS" value={`R$ ${result.creditos.cbs}`} />
                <Metric label="IBS-UF" value={`R$ ${result.creditos.ibsUF}`} />
                <Metric label="IBS-Mun" value={`R$ ${result.creditos.ibsMunicipio}`} />
                <Metric label="IBS total" value={`R$ ${result.creditos.ibs}`} />
                <Metric label="IS" value={`R$ ${result.creditos.impostoSeletivo}`} />
              </div>
            </div>
          </div>

          {/* Apurado */}
          <div className="border border-accent/40 rounded-md bg-gradient-to-br from-accentDim to-transparent p-6" data-testid="apurado-card">
            <div className="flex items-center gap-2 mb-4">
              <Equal className="w-4 h-4 text-accent" />
              <span className="text-[10px] uppercase tracking-[0.3em] text-accent">
                A apurar (débitos − créditos)
              </span>
              <span className="ml-auto text-[11px] font-mono text-muted">
                {result.periodo.inicio} → {result.periodo.fim}
              </span>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
              <Metric label="CBS a apurar" value={`R$ ${result.apurado.cbs}`} />
              <Metric label="IBS-UF a apurar" value={`R$ ${result.apurado.ibsUF}`} />
              <Metric label="IBS-Mun a apurar" value={`R$ ${result.apurado.ibsMunicipio}`} />
              <Metric label="IBS total a apurar" value={`R$ ${result.apurado.ibs}`} />
            </div>
            <div className="border border-accent bg-bg rounded-md p-4">
              <div className="text-[10px] uppercase tracking-[0.3em] text-accent mb-2">
                Total a apurar (CBS + IBS)
              </div>
              <div className="big-num text-3xl text-strong">R$ {result.apurado.total}</div>
            </div>
          </div>

          {/* Documentos do período */}
          <div className="border border-border rounded-md overflow-hidden bg-surface">
            <div className="px-4 py-3 border-b border-border text-[10px] uppercase tracking-[0.25em] text-muted">
              {result.totalDocumentos} documento{result.totalDocumentos !== 1 && "s"} no período
            </div>
            <div className="grid grid-cols-12 gap-3 px-4 py-2.5 border-b border-border text-[10px] uppercase tracking-[0.25em] text-muted">
              <div className="col-span-1">dir</div>
              <div className="col-span-3">chave</div>
              <div className="col-span-2">data</div>
              <div className="col-span-2">emitente</div>
              <div className="col-span-2 text-right">cbs</div>
              <div className="col-span-1 text-right">ibs</div>
              <div className="col-span-1 text-right">total</div>
            </div>
            {result.documentos.map((d) => (
              <div key={d.id} className="grid grid-cols-12 gap-3 px-4 py-2.5 border-b border-border/50 text-[12px] items-center">
                <div className="col-span-1">
                  <span className={`text-[9px] font-mono uppercase tracking-[0.2em] rounded px-1.5 py-0.5 border ${d.direcao === "saida" ? "text-accent border-accent/40" : "text-success border-success/40"}`}>
                    {d.direcao}
                  </span>
                </div>
                <div className="col-span-3 font-mono text-[11px] text-strong">…{d.chaveAcesso.slice(-16)}</div>
                <div className="col-span-2 font-mono text-[11.5px] text-muted">{d.dataOperacao}</div>
                <div className="col-span-2 truncate text-[11.5px] text-muted">{d.emitente || "—"}</div>
                <div className="col-span-2 text-right font-mono text-[11.5px]">{d.cbs}</div>
                <div className="col-span-1 text-right font-mono text-[11.5px]">{d.ibs}</div>
                <div className="col-span-1 text-right font-mono text-[12px] text-accent">{d.tributosTotais}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
