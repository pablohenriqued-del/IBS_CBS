import React, { useEffect, useRef, useState } from "react";
import {
  Upload, GitCompare, CheckCircle2, AlertTriangle, FileCode2, Server, Loader2, Download,
} from "lucide-react";
import { api, formatApiError } from "../api";
import { Metric } from "./Shared";

const CONTEXTO_PADRAO = {
  dataOperacao: "2026-08-26",
  cnpjEmitente: "12345678000190",
  ufEmitente: "SP",
  municipioIBGEEmitente: "3550308",
  ufDestino: "RJ",
  municipioIBGEDestino: "3304557",
  consumidorFinal: true,
  contribuinte: false,
};

function StatusBadge({ status }) {
  const map = {
    match: {
      label: "match", cls: "text-success border-success/40 bg-success/5",
    },
    diverge: {
      label: "diverge", cls: "text-error border-error/40 bg-error/5",
    },
    sap_faltante: {
      label: "SAP faltante", cls: "text-accent border-accent/40 bg-accentDim",
    },
    fiscalcore_faltante: {
      label: "FC faltante", cls: "text-accent border-accent/40 bg-accentDim",
    },
  };
  const m = map[status] || map.diverge;
  return (
    <span className={`text-[9.5px] font-mono uppercase tracking-[0.2em] border rounded px-1.5 py-0.5 ${m.cls}`}>
      {m.label}
    </span>
  );
}

export function SapReconciliarPage() {
  const [contexto, setContexto] = useState(CONTEXTO_PADRAO);
  const [file, setFile] = useState(null);
  const [idoc, setIdoc] = useState(null);
  const [rec, setRec] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const [samples, setSamples] = useState([]);
  const inputRef = useRef(null);

  useEffect(() => {
    api.get("/v1/sap/idoc/samples").then((r) => setSamples(r.data.samples || [])).catch(() => {});
  }, []);

  const upd = (k, v) => setContexto({ ...contexto, [k]: v });

  const upload = async (fileObj) => {
    setLoading(true); setError(null); setIdoc(null); setRec(null);
    try {
      const form = new FormData();
      form.append("file", fileObj);
      const { data: parsed } = await api.post("/v1/sap/idoc/parse", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setIdoc(parsed);
      // Automaticamente reconcilia com contexto padrão
      const { data: recResp } = await api.post("/v1/sap/reconciliar", {
        idoc: parsed,
        ...contexto,
      });
      setRec(recResp);
    } catch (e) {
      setError(formatApiError(e));
    } finally { setLoading(false); }
  };

  const onDrop = (e) => {
    e.preventDefault(); setDragOver(false);
    const f = e.dataTransfer.files?.[0];
    if (f) { setFile(f); upload(f); }
  };

  const onSelect = (e) => {
    const f = e.target.files?.[0];
    if (f) { setFile(f); upload(f); }
  };

  const carregarSample = async (sampleId) => {
    try {
      const resp = await api.get(`/v1/sap/idoc/samples/${sampleId}`, { responseType: "blob" });
      const blob = resp.data;
      const nome = sampleId === "diverge" ? "idoc_diverge.xml" : "idoc_ok.xml";
      const f = new File([blob], nome, { type: "application/xml" });
      setFile(f); await upload(f);
    } catch (e) {
      setError(formatApiError(e));
    }
  };

  const reReconciliar = async () => {
    if (!idoc) return;
    setLoading(true); setError(null); setRec(null);
    try {
      const { data } = await api.post("/v1/sap/reconciliar", { idoc, ...contexto });
      setRec(data);
    } catch (e) {
      setError(formatApiError(e));
    } finally { setLoading(false); }
  };

  return (
    <div className="max-w-[1400px] mx-auto px-6 py-12">
      <div className="mb-8">
        <div className="flex items-center gap-2 mb-3">
          <Server className="w-4 h-4 text-accent" />
          <span className="text-[11px] font-mono uppercase tracking-[0.3em] text-accent">
            POST /api/v1/sap/idoc/parse · /sap/reconciliar
          </span>
        </div>
        <h1 className="font-heading text-4xl tracking-tight text-strong mb-2">
          Reconciliação <span className="serif-italic text-accent">SAP vs FiscalCore</span>.
        </h1>
        <p className="text-muted max-w-3xl leading-relaxed">
          Envie um IDOC <span className="font-mono text-text">INVOIC02</span> saído do S/4HANA.
          O motor recalcula os mesmos itens e mostra, condição por condição, onde SAP e FiscalCore
          convergem — e onde divergem, com o delta exato em reais.
        </p>
      </div>

      {/* Contexto fiscal */}
      <div className="border border-border rounded-md p-5 bg-surface mb-6" data-testid="sap-rec-contexto">
        <div className="text-[10px] uppercase tracking-[0.25em] text-muted mb-4">
          contexto fiscal (usado para o recálculo do FiscalCore)
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <label className="col-span-2 md:col-span-1"><span className="text-[10px] uppercase tracking-[0.2em] text-muted">dataOperacao</span>
            <input type="date" value={contexto.dataOperacao} onChange={(e) => upd("dataOperacao", e.target.value)}
              className="mt-1 w-full bg-bg border border-border rounded-md px-3 py-2 text-sm font-mono focus:border-accent focus:outline-none" /></label>
          <label><span className="text-[10px] uppercase tracking-[0.2em] text-muted">CNPJ emit.</span>
            <input value={contexto.cnpjEmitente} onChange={(e) => upd("cnpjEmitente", e.target.value)}
              className="mt-1 w-full bg-bg border border-border rounded-md px-3 py-2 text-sm font-mono focus:border-accent focus:outline-none" /></label>
          <label><span className="text-[10px] uppercase tracking-[0.2em] text-muted">UF emit.</span>
            <input value={contexto.ufEmitente} onChange={(e) => upd("ufEmitente", e.target.value.toUpperCase())} maxLength={2}
              className="mt-1 w-full bg-bg border border-border rounded-md px-3 py-2 text-sm font-mono focus:border-accent focus:outline-none" /></label>
          <label><span className="text-[10px] uppercase tracking-[0.2em] text-muted">UF destino</span>
            <input value={contexto.ufDestino} onChange={(e) => upd("ufDestino", e.target.value.toUpperCase())} maxLength={2}
              className="mt-1 w-full bg-bg border border-border rounded-md px-3 py-2 text-sm font-mono focus:border-accent focus:outline-none" /></label>
        </div>
      </div>

      {/* Dropzone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        data-testid="idoc-dropzone"
        className={`border-2 border-dashed rounded-md p-10 mb-6 text-center cursor-pointer transition-colors ${
          dragOver ? "border-accent bg-accentDim" : "border-border bg-surface hover:border-borderHover"
        }`}
      >
        <input ref={inputRef} type="file" accept=".xml" onChange={onSelect} className="hidden" data-testid="idoc-file-input" />
        <div className="flex flex-col items-center gap-3">
          {loading ? (
            <Loader2 className="w-8 h-8 text-accent animate-spin" />
          ) : (
            <Upload className="w-8 h-8 text-muted" />
          )}
          <div className="font-heading text-lg text-strong">
            {file ? file.name : "Arraste um IDOC INVOIC02 (.xml) aqui"}
          </div>
          <div className="font-mono text-[11px] text-muted uppercase tracking-[0.2em]">
            ou clique para selecionar
          </div>
        </div>
      </div>

      {samples.length > 0 && (
        <div className="flex flex-wrap items-center gap-3 mb-6" data-testid="idoc-samples">
          <span className="text-[10px] font-mono uppercase tracking-[0.25em] text-muted">amostras:</span>
          {samples.map((s) => (
            <button
              key={s.id}
              onClick={() => carregarSample(s.id)}
              data-testid={`load-sample-${s.id}`}
              className="inline-flex items-center gap-2 border border-border hover:border-accent text-text hover:text-accent rounded-md px-3 py-1.5 text-[11px] font-mono transition-colors"
            >
              <Download className="w-3 h-3" /> {s.nome}
            </button>
          ))}
        </div>
      )}

      {error && (
        <div className="mb-6 border border-error/30 bg-error/5 rounded-md p-4 text-error font-mono text-sm" data-testid="sap-rec-error">
          ⨯ {error}
        </div>
      )}

      {/* Painel IDOC + Reconciliação */}
      {idoc && (
        <div className="grid grid-cols-12 gap-6" data-testid="sap-rec-results">
          <div className="col-span-12 lg:col-span-4">
            <div className="border border-border rounded-md bg-surface p-5 sticky top-20">
              <div className="flex items-center gap-2 mb-4">
                <FileCode2 className="w-4 h-4 text-muted" />
                <span className="text-[10px] uppercase tracking-[0.25em] text-muted">IDOC parseado</span>
              </div>
              <dl className="space-y-2 text-[12.5px]">
                <div className="flex justify-between border-b border-border pb-1.5">
                  <dt className="font-mono text-[10px] text-muted uppercase tracking-[0.2em]">DOCNUM</dt>
                  <dd className="font-mono text-strong">{idoc.docnum || "—"}</dd>
                </div>
                <div className="flex justify-between border-b border-border pb-1.5">
                  <dt className="font-mono text-[10px] text-muted uppercase tracking-[0.2em]">MESTYP / IDOCTP</dt>
                  <dd className="font-mono text-text/80">{idoc.mestyp} / {idoc.idoctp}</dd>
                </div>
                <div className="flex justify-between border-b border-border pb-1.5">
                  <dt className="font-mono text-[10px] text-muted uppercase tracking-[0.2em]">CURCY / BELNR</dt>
                  <dd className="font-mono text-text/80">{idoc.currency} · {idoc.belnr}</dd>
                </div>
                <div className="flex justify-between border-b border-border pb-1.5">
                  <dt className="font-mono text-[10px] text-muted uppercase tracking-[0.2em]">itens</dt>
                  <dd className="font-mono text-strong">{idoc.itens?.length ?? 0}</dd>
                </div>
              </dl>
              {idoc.summary && (
                <div className="mt-4 pt-4 border-t border-border">
                  <div className="text-[10px] font-mono uppercase tracking-[0.25em] text-muted mb-2">summary (E1EDS01)</div>
                  <div className="grid grid-cols-3 gap-2 font-mono text-[11.5px]">
                    <div><div className="text-muted text-[9px] uppercase tracking-[0.2em]">net</div><div className="text-strong">{idoc.summary.net || "—"}</div></div>
                    <div><div className="text-muted text-[9px] uppercase tracking-[0.2em]">tax</div><div className="text-strong">{idoc.summary.tax || "—"}</div></div>
                    <div><div className="text-muted text-[9px] uppercase tracking-[0.2em]">gross</div><div className="text-strong">{idoc.summary.gross || "—"}</div></div>
                  </div>
                </div>
              )}
              <button onClick={reReconciliar} disabled={loading} data-testid="sap-re-reconciliar"
                className="mt-5 w-full border border-accent/40 text-accent hover:bg-accentDim rounded-md py-2 text-[11px] font-mono uppercase tracking-[0.22em] flex items-center justify-center gap-2 disabled:opacity-60">
                <GitCompare className="w-3.5 h-3.5" /> reconciliar novamente
              </button>
            </div>
          </div>

          {/* Reconciliação */}
          <div className="col-span-12 lg:col-span-8 space-y-5">
            {rec && (
              <>
                {/* Veredicto */}
                <div className={`border rounded-md p-6 ${
                  rec.veredicto === "convergente"
                    ? "border-success/40 bg-success/5"
                    : "border-error/40 bg-error/5"
                }`} data-testid="sap-rec-veredicto">
                  <div className="flex items-center gap-3 mb-3">
                    {rec.veredicto === "convergente" ? (
                      <CheckCircle2 className="w-5 h-5 text-success" />
                    ) : (
                      <AlertTriangle className="w-5 h-5 text-error" />
                    )}
                    <div className={`text-[10px] font-mono uppercase tracking-[0.3em] ${
                      rec.veredicto === "convergente" ? "text-success" : "text-error"
                    }`}>
                      veredicto
                    </div>
                  </div>
                  <div className="font-heading text-3xl text-strong mb-1 capitalize">{rec.veredicto}</div>
                  <div className="font-mono text-[12px] text-muted">
                    {rec.resumo.matches} match · {rec.resumo.divergencias} divergência{rec.resumo.divergencias !== 1 && "s"} · tolerância ±R$ {rec.toleranciaCentavos}
                  </div>
                </div>

                {/* Totais SAP vs FiscalCore */}
                <div className="grid grid-cols-3 gap-4">
                  <Metric label="Tributos (SAP)" value={`R$ ${rec.totais.sap}`} />
                  <Metric label="Tributos (FiscalCore)" value={`R$ ${rec.totais.fiscalcore}`} />
                  <div className={`border rounded-md p-3 ${
                    rec.totais.delta === "0.00" ? "border-border bg-bg" : "border-error/40 bg-error/5"
                  }`}>
                    <div className="text-[9.5px] uppercase tracking-[0.25em] text-muted mb-1.5">Δ (FC − SAP)</div>
                    <div className={`big-num text-lg ${rec.totais.delta === "0.00" ? "text-strong" : "text-error"}`}>
                      R$ {rec.totais.delta}
                    </div>
                  </div>
                </div>

                {/* Tabela linha a linha */}
                <div className="border border-border rounded-md overflow-hidden">
                  <div className="px-4 py-2.5 border-b border-border bg-elev/50 text-[10px] uppercase tracking-[0.25em] text-muted">
                    condições por (KPOSN, KSCHL)
                  </div>
                  <table className="w-full font-mono text-[12px]" data-testid="sap-rec-tabela">
                    <thead className="bg-elev text-muted uppercase tracking-[0.18em] text-[10px]">
                      <tr>
                        <th className="text-left px-3 py-2">KPOSN</th>
                        <th className="text-left px-3 py-2">KSCHL</th>
                        <th className="text-right px-3 py-2">SAP</th>
                        <th className="text-right px-3 py-2">FiscalCore</th>
                        <th className="text-right px-3 py-2">Δ</th>
                        <th className="text-center px-3 py-2">status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {rec.linhas.map((L, i) => (
                        <tr key={i}
                          data-testid={`sap-rec-row-${L.kposn}-${L.kschl}`}
                          className={L.status === "match" ? "" : "bg-error/5"}>
                          <td className="px-3 py-2 tabular-nums">{L.kposn}</td>
                          <td className="px-3 py-2 text-accent">{L.kschl}</td>
                          <td className="px-3 py-2 text-right tabular-nums">{L.sap || "—"}</td>
                          <td className="px-3 py-2 text-right tabular-nums text-strong">{L.fiscalcore || "—"}</td>
                          <td className={`px-3 py-2 text-right tabular-nums ${
                            L.status === "match" ? "text-muted" : "text-error"
                          }`}>{L.delta || "—"}</td>
                          <td className="px-3 py-2 text-center"><StatusBadge status={L.status} /></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                <div className="text-[10.5px] font-mono text-muted flex items-center justify-between pt-1">
                  <span>ruleset: <span className="text-text/70">{rec.rulesetId}</span></span>
                  <span className="text-text/60 truncate max-w-[420px]">{rec.rulesetHash}</span>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
