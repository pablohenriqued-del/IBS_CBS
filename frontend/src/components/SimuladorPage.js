import React, { useState } from "react";
import { GitCompareArrows, TrendingUp, TrendingDown, Equal } from "lucide-react";
import { api, formatApiError } from "../api";
import { Metric } from "./Shared";

const DEFAULT_REQUEST = {
  referencia: "sim-2026-000123",
  dataOperacao: "2026-08-26",
  modo: "producao",
  estabelecimento: { cnpj: "12345678000190", uf: "SP", municipioIBGE: "3550308", regime: "regular" },
  destinatario: { uf: "RJ", municipioIBGE: "3304557", consumidorFinal: true, contribuinte: false },
  operacao: { tipo: "venda" },
  itens: [
    { numero: 1, descricao: "Cadeira de escritório", cClassTrib: "000001", quantidade: "1.00", valorUnitario: "1000.00", valorItem: "1000.00" },
    { numero: 2, descricao: "Medicamento", cClassTrib: "200052", quantidade: "1.00", valorUnitario: "500.00", valorItem: "500.00" },
    { numero: 3, descricao: "Bebida açucarada", cClassTrib: "000001", quantidade: "1.00", valorUnitario: "200.00", valorItem: "200.00", impostoSeletivo: { aliquota: "10.0000", cst: "01" } },
  ],
};

export function SimuladorPage() {
  const [dataOperacao, setDataOperacao] = useState(DEFAULT_REQUEST.dataOperacao);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const simular = async () => {
    setLoading(true); setError(null); setResult(null);
    try {
      const { data } = await api.post("/v1/simular", { ...DEFAULT_REQUEST, dataOperacao });
      setResult(data);
    } catch (e) {
      setError(formatApiError(e));
    } finally { setLoading(false); }
  };

  const isUp = result && parseFloat(result.delta.totais.delta) > 0;
  const isDown = result && parseFloat(result.delta.totais.delta) < 0;

  return (
    <div className="max-w-[1400px] mx-auto px-6 py-12">
      <div className="mb-8">
        <div className="text-[11px] font-mono uppercase tracking-[0.3em] text-muted mb-2">
          POST /api/v1/simular
        </div>
        <h1 className="font-heading text-4xl tracking-tight text-strong mb-2">
          Quanto vai <span className="serif-italic text-accent">mudar?</span>
        </h1>
        <p className="text-muted max-w-2xl">
          Compara a carga tributária no regime atual (ICMS + PIS/Cofins agregados,
          aproximação) com a Reforma (motor real: CBS + IBS + IS). Para os 3 casos-ouro
          do contrato, na data escolhida.
        </p>
      </div>

      <div className="border border-border rounded-md p-5 bg-surface mb-6 flex items-end gap-4">
        <label className="flex-1">
          <span className="text-[10px] uppercase tracking-[0.25em] text-muted">dataOperacao</span>
          <input
            type="date" value={dataOperacao} onChange={(e) => setDataOperacao(e.target.value)}
            data-testid="sim-data-operacao"
            className="mt-1 w-full bg-bg border border-border rounded-md px-3 py-2 text-sm font-mono focus:border-accent focus:outline-none" />
        </label>
        <button
          onClick={simular} disabled={loading} data-testid="simular-btn"
          className="bg-accent text-bg font-semibold rounded-md px-5 py-2.5 flex items-center gap-2 hover:bg-accentHover hover:-translate-y-0.5 transition-transform disabled:opacity-60">
          <GitCompareArrows className="w-4 h-4" strokeWidth={2.5} />
          {loading ? "Simulando…" : "Simular comparativo"}
        </button>
      </div>

      {error && (
        <div className="mb-6 border border-error/30 bg-error/5 rounded-md p-4 text-error font-mono text-sm">⨯ {error}</div>
      )}

      {result && (
        <div className="space-y-6 reveal" data-testid="sim-result">
          {/* Highlight de delta */}
          <div className={`border rounded-md p-6 ${isUp ? "border-error/40 bg-error/5" : isDown ? "border-success/40 bg-success/5" : "border-accent/40 bg-accentDim"}`}>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 items-center">
              <div>
                <div className="text-[10px] uppercase tracking-[0.3em] text-muted mb-1">Regime atual</div>
                <div className="big-num text-2xl text-strong">R$ {result.delta.totais.tributoAtual}</div>
                <div className="text-[11px] font-mono text-muted mt-1">ICMS + PIS/Cofins (agregado)</div>
              </div>
              <div className="flex items-center justify-center">
                {isUp && <TrendingUp className="w-8 h-8 text-error" />}
                {isDown && <TrendingDown className="w-8 h-8 text-success" />}
                {!isUp && !isDown && <Equal className="w-8 h-8 text-muted" />}
              </div>
              <div>
                <div className="text-[10px] uppercase tracking-[0.3em] text-muted mb-1">Reforma</div>
                <div className="big-num text-2xl text-strong">R$ {result.delta.totais.tributoNovo}</div>
                <div className="text-[11px] font-mono text-muted mt-1">CBS + IBS + IS</div>
              </div>
              <div className={`border rounded-md p-3 ${isUp ? "border-error bg-bg" : isDown ? "border-success bg-bg" : "border-accent bg-bg"}`}>
                <div className={`text-[10px] uppercase tracking-[0.3em] mb-1 ${isUp ? "text-error" : isDown ? "text-success" : "text-accent"}`}>Delta</div>
                <div className={`big-num text-2xl ${isUp ? "text-error" : isDown ? "text-success" : "text-strong"}`} data-testid="delta-total">
                  {parseFloat(result.delta.totais.delta) >= 0 ? "+" : ""}R$ {result.delta.totais.delta}
                </div>
                <div className={`text-[11px] font-mono mt-1 ${isUp ? "text-error" : isDown ? "text-success" : "text-muted"}`}>
                  {parseFloat(result.delta.totais.deltaPct) >= 0 ? "+" : ""}{result.delta.totais.deltaPct}%
                </div>
              </div>
            </div>
          </div>

          {/* Side-by-side por item */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Regime atual */}
            <div className="border border-border rounded-md bg-surface p-5" data-testid="sim-atual">
              <div className="flex items-center gap-2 mb-4">
                <span className="text-[10px] uppercase tracking-[0.3em] text-muted">Regime atual</span>
                <span className="ml-auto text-[11px] font-mono text-muted">
                  carga média {result.atual.totais.cargaMediaPct}%
                </span>
              </div>
              <div className="space-y-2">
                {result.atual.itens.map((it) => (
                  <div key={it.numero} className="border border-border rounded-md p-3 bg-bg">
                    <div className="flex items-baseline justify-between mb-1">
                      <span className="font-heading text-sm text-strong">Item {String(it.numero).padStart(2, "0")}</span>
                      <span className="font-mono text-[10.5px] text-muted">{it.cargaEfetivaPct}%</span>
                    </div>
                    <div className="flex items-center justify-between text-[12.5px]">
                      <span className="font-mono text-muted">base R$ {it.base}</span>
                      <span className="big-num text-strong">R$ {it.tributoAtual}</span>
                    </div>
                  </div>
                ))}
              </div>
              <div className="mt-3 border-t border-border pt-3 flex justify-between">
                <span className="text-[10px] uppercase tracking-[0.25em] text-muted">Total tributos</span>
                <span className="big-num text-lg text-strong">R$ {result.atual.totais.tributos}</span>
              </div>
            </div>

            {/* Reforma */}
            <div className="border border-accent/40 rounded-md bg-gradient-to-br from-accentDim to-transparent p-5" data-testid="sim-nova">
              <div className="flex items-center gap-2 mb-4">
                <span className="text-[10px] uppercase tracking-[0.3em] text-accent">Reforma (motor)</span>
                <span className="ml-auto text-[10px] font-mono text-muted truncate max-w-[200px]">{result.rulesetId}</span>
              </div>
              <div className="space-y-2">
                {result.nova.itens.map((it) => (
                  <div key={it.numero} className="border border-border rounded-md p-3 bg-bg">
                    <div className="flex items-baseline justify-between mb-1">
                      <span className="font-heading text-sm text-strong">Item {String(it.numero).padStart(2, "0")}</span>
                      {it.impostoSeletivo && (
                        <span className="text-[9px] font-mono uppercase tracking-[0.2em] text-accent border border-accent/40 rounded px-1.5 py-0.5">IS</span>
                      )}
                    </div>
                    <div className="grid grid-cols-3 gap-2 text-[11px] font-mono text-muted">
                      <div>CBS <span className="text-strong">{it.cbs.valor}</span></div>
                      <div>IBS <span className="text-strong">{it.ibs.valor}</span></div>
                      {it.impostoSeletivo ? (
                        <div>IS <span className="text-strong">{it.impostoSeletivo.valor}</span></div>
                      ) : <div />}
                    </div>
                    <div className="flex items-center justify-between text-[12.5px] mt-1">
                      <span className="font-mono text-muted">base R$ {it.base}</span>
                      <span className="big-num text-accent">R$ {it.totalItem}</span>
                    </div>
                  </div>
                ))}
              </div>
              <div className="mt-3 border-t border-border pt-3 flex justify-between">
                <span className="text-[10px] uppercase tracking-[0.25em] text-accent">Total tributos</span>
                <span className="big-num text-lg text-accent">R$ {result.delta.totais.tributoNovo}</span>
              </div>
            </div>
          </div>

          {/* Delta por item */}
          <div className="border border-border rounded-md overflow-hidden bg-surface" data-testid="sim-delta-itens">
            <div className="px-4 py-3 border-b border-border text-[10px] uppercase tracking-[0.3em] text-muted">
              Delta por item
            </div>
            <div className="grid grid-cols-12 gap-3 px-4 py-2 border-b border-border text-[10px] uppercase tracking-[0.25em] text-muted">
              <div className="col-span-1">nº</div>
              <div className="col-span-3 text-right">base</div>
              <div className="col-span-3 text-right">atual</div>
              <div className="col-span-2 text-right">reforma</div>
              <div className="col-span-2 text-right">delta</div>
              <div className="col-span-1 text-right">%</div>
            </div>
            {result.delta.itens.map((it) => {
              const up = parseFloat(it.delta) > 0;
              const down = parseFloat(it.delta) < 0;
              return (
                <div key={it.numero} className="grid grid-cols-12 gap-3 px-4 py-2 border-b border-border/50 text-[12px] items-center">
                  <div className="col-span-1 font-heading text-strong tabular-nums">{String(it.numero).padStart(2, "0")}</div>
                  <div className="col-span-3 text-right font-mono text-muted">R$ {it.base}</div>
                  <div className="col-span-3 text-right font-mono text-strong">R$ {it.tributoAtual}</div>
                  <div className="col-span-2 text-right font-mono text-accent">R$ {it.tributoNovo}</div>
                  <div className={`col-span-2 text-right font-mono ${up ? "text-error" : down ? "text-success" : "text-muted"}`}>
                    {parseFloat(it.delta) >= 0 ? "+" : ""}R$ {it.delta}
                  </div>
                  <div className={`col-span-1 text-right font-mono ${up ? "text-error" : down ? "text-success" : "text-muted"}`}>
                    {parseFloat(it.deltaPct) >= 0 ? "+" : ""}{it.deltaPct}%
                  </div>
                </div>
              );
            })}
          </div>

          {result.avisos && result.avisos.length > 0 && (
            <div className="border border-border rounded-md p-4 bg-surface text-[12.5px] text-muted">
              <div className="text-[10px] uppercase tracking-[0.25em] text-muted mb-2">Avisos</div>
              <ul className="space-y-1">
                {result.avisos.map((a, i) => (<li key={i} className="flex gap-2"><span className="text-accent">›</span>{a}</li>))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
