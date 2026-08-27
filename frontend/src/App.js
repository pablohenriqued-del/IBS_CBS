import React, { useEffect, useMemo, useState } from "react";
import axios from "axios";
import {
  Check,
  Copy,
  Play,
  RefreshCw,
  Terminal,
  ShieldCheck,
  Layers,
  FileText,
  ChevronRight,
} from "lucide-react";

const BACKEND = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND}/api/v1`;

// -------------------------------------------------------------------------
// Golden request — exatamente o exemplo do contrato api-calcular-ibs-cbs.md
// -------------------------------------------------------------------------
const GOLDEN_REQUEST = {
  referencia: "pedido-2026-000123",
  dataOperacao: "2026-08-26",
  modo: "producao",
  estabelecimento: {
    cnpj: "12345678000190",
    uf: "SP",
    municipioIBGE: "3550308",
    regime: "regular",
  },
  destinatario: {
    uf: "RJ",
    municipioIBGE: "3304557",
    consumidorFinal: true,
    contribuinte: false,
  },
  operacao: { tipo: "venda" },
  itens: [
    {
      numero: 1,
      descricao: "Cadeira de escritório",
      ncm: "94013000",
      cClassTrib: "000001",
      quantidade: "1.00",
      valorUnitario: "1000.00",
      valorItem: "1000.00",
    },
    {
      numero: 2,
      descricao: "Medicamento (lista com redução de 60%)",
      ncm: "30049099",
      cClassTrib: "200052",
      quantidade: "1.00",
      valorUnitario: "500.00",
      valorItem: "500.00",
    },
    {
      numero: 3,
      descricao: "Bebida açucarada (sujeita ao IS)",
      ncm: "22021000",
      cClassTrib: "000001",
      quantidade: "1.00",
      valorUnitario: "200.00",
      valorItem: "200.00",
      impostoSeletivo: { aliquota: "10.0000", cst: "01" },
    },
  ],
};

// -------------------------------------------------------------------------
// JSON viewer com syntax highlighting simples
// -------------------------------------------------------------------------
function JsonView({ data }) {
  const render = (v, indent = 0) => {
    const pad = "  ".repeat(indent);
    if (v === null) return <span className="jnull">null</span>;
    if (typeof v === "boolean") return <span className="jbool">{String(v)}</span>;
    if (typeof v === "number") return <span className="jnum">{v}</span>;
    if (typeof v === "string") return <span className="jstr">"{v}"</span>;
    if (Array.isArray(v)) {
      if (v.length === 0) return <span className="jpunc">[]</span>;
      return (
        <>
          <span className="jpunc">[</span>
          {v.map((el, i) => (
            <div key={i} style={{ paddingLeft: (indent + 1) * 12 }}>
              {render(el, indent + 1)}
              {i < v.length - 1 && <span className="jpunc">,</span>}
            </div>
          ))}
          <div style={{ paddingLeft: indent * 12 }}>
            <span className="jpunc">]</span>
          </div>
        </>
      );
    }
    if (typeof v === "object") {
      const keys = Object.keys(v);
      if (keys.length === 0) return <span className="jpunc">{"{}"}</span>;
      return (
        <>
          <span className="jpunc">{"{"}</span>
          {keys.map((k, i) => (
            <div key={k} style={{ paddingLeft: (indent + 1) * 12 }}>
              <span className="jkey">"{k}"</span>
              <span className="jpunc">: </span>
              {render(v[k], indent + 1)}
              {i < keys.length - 1 && <span className="jpunc">,</span>}
            </div>
          ))}
          <div style={{ paddingLeft: indent * 12 }}>
            <span className="jpunc">{"}"}</span>
          </div>
        </>
      );
    }
    return String(v);
  };
  return <div className="font-mono text-[13px] leading-6">{render(data)}</div>;
}

// -------------------------------------------------------------------------
// Copy button
// -------------------------------------------------------------------------
function CopyBtn({ text, testid }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      data-testid={testid}
      onClick={() => {
        navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 1200);
      }}
      className="inline-flex items-center gap-1.5 text-xs font-mono text-muted hover:text-text transition-colors duration-150"
    >
      {copied ? <Check className="w-3.5 h-3.5 text-accent" /> : <Copy className="w-3.5 h-3.5" />}
      {copied ? "copiado" : "copiar"}
    </button>
  );
}

// -------------------------------------------------------------------------
// Ruleset panel
// -------------------------------------------------------------------------
function RulesetsPanel({ rulesets, current }) {
  return (
    <div className="border border-border rounded-md bg-surface" data-testid="rulesets-panel">
      <div className="px-4 py-3 border-b border-border flex items-center gap-2">
        <Layers className="w-4 h-4 text-muted" />
        <span className="text-xs uppercase tracking-[0.2em] font-semibold text-muted">
          Rulesets carregados
        </span>
      </div>
      <div className="divide-y divide-border">
        {rulesets.length === 0 && (
          <div className="p-4 text-sm text-muted">Carregando…</div>
        )}
        {rulesets.map((r) => {
          const active = current === r.id;
          return (
            <div
              key={r.id}
              data-testid={`ruleset-${r.id.replace(/[:.]/g, "-")}`}
              className={`p-4 ${active ? "bg-elev" : ""}`}
            >
              <div className="flex items-center justify-between gap-2 mb-1">
                <span className="font-mono text-xs text-text">{r.id}</span>
                {active && (
                  <span className="text-[10px] font-mono uppercase tracking-widest text-accent">
                    vigente
                  </span>
                )}
              </div>
              <div className="text-xs text-muted mb-2">{r.descricao}</div>
              <div className="flex flex-wrap gap-x-4 gap-y-1 text-[11px] font-mono text-muted">
                <span>vigência: {r.vigenciaInicio} → {r.vigenciaFim || "aberta"}</span>
                <span>CBS: {r.cbs.aliquotaNominal}%</span>
                <span>IBS-UF: {r.ibs.aliquotaUF}%</span>
                <span>IBS-Mun: {r.ibs.aliquotaMunicipio}%</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// -------------------------------------------------------------------------
// Item row — configurável
// -------------------------------------------------------------------------
function ItemEditor({ item, onChange, onRemove, idx }) {
  const upd = (k, v) => onChange({ ...item, [k]: v });
  const updIS = (k, v) => {
    const is = item.impostoSeletivo || { aliquota: "0.0000", cst: "01" };
    onChange({ ...item, impostoSeletivo: { ...is, [k]: v } });
  };
  const toggleIS = (on) => {
    if (on) {
      onChange({ ...item, impostoSeletivo: { aliquota: "10.0000", cst: "01" } });
    } else {
      const { impostoSeletivo, ...rest } = item;
      onChange(rest);
    }
  };
  return (
    <div className="border border-border rounded-md p-4 bg-elev" data-testid={`item-editor-${idx}`}>
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs uppercase tracking-[0.2em] font-semibold text-muted">
          Item {item.numero}
        </span>
        <button
          onClick={onRemove}
          className="text-xs text-muted hover:text-error transition-colors"
          data-testid={`remove-item-${idx}`}
        >
          remover
        </button>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <label className="col-span-2">
          <span className="text-[11px] uppercase tracking-widest text-muted">Descrição</span>
          <input
            data-testid={`item-${idx}-descricao`}
            value={item.descricao || ""}
            onChange={(e) => upd("descricao", e.target.value)}
            className="mt-1 w-full bg-bg border border-border rounded-md px-3 py-2 text-sm font-mono focus:border-accent focus:outline-none"
          />
        </label>
        <label>
          <span className="text-[11px] uppercase tracking-widest text-muted">cClassTrib</span>
          <input
            data-testid={`item-${idx}-cclasstrib`}
            value={item.cClassTrib}
            onChange={(e) => upd("cClassTrib", e.target.value)}
            className="mt-1 w-full bg-bg border border-border rounded-md px-3 py-2 text-sm font-mono focus:border-accent focus:outline-none"
          />
        </label>
        <label>
          <span className="text-[11px] uppercase tracking-widest text-muted">NCM</span>
          <input
            data-testid={`item-${idx}-ncm`}
            value={item.ncm || ""}
            onChange={(e) => upd("ncm", e.target.value)}
            className="mt-1 w-full bg-bg border border-border rounded-md px-3 py-2 text-sm font-mono focus:border-accent focus:outline-none"
          />
        </label>
        <label>
          <span className="text-[11px] uppercase tracking-widest text-muted">Quantidade</span>
          <input
            data-testid={`item-${idx}-quantidade`}
            value={item.quantidade}
            onChange={(e) => upd("quantidade", e.target.value)}
            className="mt-1 w-full bg-bg border border-border rounded-md px-3 py-2 text-sm font-mono focus:border-accent focus:outline-none"
          />
        </label>
        <label>
          <span className="text-[11px] uppercase tracking-widest text-muted">Valor Unit.</span>
          <input
            data-testid={`item-${idx}-valor-unit`}
            value={item.valorUnitario}
            onChange={(e) => upd("valorUnitario", e.target.value)}
            className="mt-1 w-full bg-bg border border-border rounded-md px-3 py-2 text-sm font-mono focus:border-accent focus:outline-none"
          />
        </label>
        <label className="col-span-2">
          <span className="text-[11px] uppercase tracking-widest text-muted">Valor Item</span>
          <input
            data-testid={`item-${idx}-valor-item`}
            value={item.valorItem}
            onChange={(e) => upd("valorItem", e.target.value)}
            className="mt-1 w-full bg-bg border border-border rounded-md px-3 py-2 text-sm font-mono focus:border-accent focus:outline-none"
          />
        </label>
      </div>
      <div className="mt-3 border-t border-border pt-3">
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            data-testid={`item-${idx}-is-toggle`}
            checked={!!item.impostoSeletivo}
            onChange={(e) => toggleIS(e.target.checked)}
            className="accent-accent"
          />
          <span className="text-xs uppercase tracking-widest text-muted">
            Sujeito ao Imposto Seletivo
          </span>
        </label>
        {item.impostoSeletivo && (
          <div className="grid grid-cols-2 gap-3 mt-3">
            <label>
              <span className="text-[11px] uppercase tracking-widest text-muted">
                Alíquota IS (%)
              </span>
              <input
                data-testid={`item-${idx}-is-aliquota`}
                value={item.impostoSeletivo.aliquota}
                onChange={(e) => updIS("aliquota", e.target.value)}
                className="mt-1 w-full bg-bg border border-border rounded-md px-3 py-2 text-sm font-mono focus:border-accent focus:outline-none"
              />
            </label>
            <label>
              <span className="text-[11px] uppercase tracking-widest text-muted">CST IS</span>
              <input
                data-testid={`item-${idx}-is-cst`}
                value={item.impostoSeletivo.cst || ""}
                onChange={(e) => updIS("cst", e.target.value)}
                className="mt-1 w-full bg-bg border border-border rounded-md px-3 py-2 text-sm font-mono focus:border-accent focus:outline-none"
              />
            </label>
          </div>
        )}
      </div>
    </div>
  );
}

// -------------------------------------------------------------------------
// Item result card
// -------------------------------------------------------------------------
function ItemResult({ item, idx }) {
  const [open, setOpen] = useState(idx === 0);
  return (
    <div className="border border-border rounded-md bg-surface reveal" data-testid={`result-item-${item.numero}`}>
      <button
        onClick={() => setOpen(!open)}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-elev transition-colors"
      >
        <div className="flex items-center gap-3">
          <span className="text-[10px] font-mono uppercase tracking-widest text-muted">
            item {item.numero}
          </span>
          <span className="font-mono text-sm text-text">base R$ {item.base}</span>
          {item.impostoSeletivo && (
            <span className="text-[10px] font-mono uppercase tracking-widest text-accent">
              IS
            </span>
          )}
        </div>
        <div className="flex items-center gap-4">
          <span className="text-[11px] font-mono text-muted">
            CBS <span className="text-text">{item.cbs.valor}</span>
          </span>
          <span className="text-[11px] font-mono text-muted">
            IBS <span className="text-text">{item.ibs.valor}</span>
          </span>
          <span className="font-mono text-sm text-accent">Σ {item.totalItem}</span>
          <ChevronRight
            className={`w-4 h-4 text-muted transition-transform duration-150 ${
              open ? "rotate-90" : ""
            }`}
          />
        </div>
      </button>
      {open && (
        <div className="border-t border-border p-4 space-y-4">
          <div className="grid grid-cols-3 gap-3">
            <Metric label="Base IBS/CBS" value={item.base} />
            <Metric label="CBS" value={item.cbs.valor} sub={`${item.cbs.aliquotaEfetiva}%`} />
            <Metric label="IBS total" value={item.ibs.valor} />
            {item.impostoSeletivo && (
              <Metric
                label="Imp. Seletivo"
                value={item.impostoSeletivo.valor}
                sub={`${item.impostoSeletivo.aliquota}%`}
              />
            )}
            <Metric label="IBS-UF" value={item.ibs.uf.valor} sub={`${item.ibs.uf.aliquota}%`} />
            <Metric
              label="IBS-Mun"
              value={item.ibs.municipio.valor}
              sub={`${item.ibs.municipio.aliquota}%`}
            />
          </div>
          <div>
            <div className="text-[11px] uppercase tracking-widest text-muted mb-2">
              Memória de cálculo
            </div>
            <ol className="space-y-1 font-mono text-[12px] text-text/90">
              {item.memoriaCalculo.map((linha, i) => (
                <li key={i} className="flex gap-2">
                  <span className="text-muted select-none">{String(i + 1).padStart(2, "0")}</span>
                  <span>{linha}</span>
                </li>
              ))}
            </ol>
          </div>
        </div>
      )}
    </div>
  );
}

function Metric({ label, value, sub }) {
  return (
    <div className="border border-border bg-bg rounded-md p-3">
      <div className="text-[10px] uppercase tracking-[0.2em] text-muted mb-1">{label}</div>
      <div className="font-mono text-lg text-text">R$ {value}</div>
      {sub && <div className="font-mono text-[11px] text-muted mt-0.5">{sub}</div>}
    </div>
  );
}

// -------------------------------------------------------------------------
// App
// -------------------------------------------------------------------------
export default function App() {
  const [dataOperacao, setDataOperacao] = useState(GOLDEN_REQUEST.dataOperacao);
  const [itens, setItens] = useState(GOLDEN_REQUEST.itens);
  const [rulesets, setRulesets] = useState([]);
  const [response, setResponse] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [viewMode, setViewMode] = useState("visual"); // visual | json

  useEffect(() => {
    axios
      .get(`${API}/rulesets`)
      .then((r) => {
        // Dedupe por id (append-only pode ter revisões antigas do mesmo id)
        const map = new Map();
        for (const rs of r.data.rulesets) map.set(rs.id, rs);
        setRulesets(Array.from(map.values()));
      })
      .catch(() => setRulesets([]));
  }, []);

  const buildPayload = () => ({
    ...GOLDEN_REQUEST,
    dataOperacao,
    itens,
  });

  const calcular = async () => {
    setLoading(true);
    setError(null);
    setResponse(null);
    try {
      const { data } = await axios.post(`${API}/calcular`, buildPayload());
      setResponse(data);
    } catch (e) {
      const detail = e.response?.data?.detail || e.response?.data || { erro: e.message };
      setError(detail);
    } finally {
      setLoading(false);
    }
  };

  const resetGolden = () => {
    setDataOperacao(GOLDEN_REQUEST.dataOperacao);
    setItens(GOLDEN_REQUEST.itens);
    setResponse(null);
    setError(null);
  };

  const currentRulesetId = response?.rulesetId;

  const payload = useMemo(() => buildPayload(), [dataOperacao, itens]);

  return (
    <div className="grain min-h-screen relative">
      {/* HEADER */}
      <header className="sticky top-0 z-10 backdrop-blur-md bg-bg/80 border-b border-border">
        <div className="max-w-[1400px] mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-accent rounded-md flex items-center justify-center">
              <Terminal className="w-4 h-4 text-bg" strokeWidth={2.5} />
            </div>
            <div>
              <div className="font-heading font-black text-lg leading-none tracking-tight">
                FiscalCore
              </div>
              <div className="font-mono text-[10px] uppercase tracking-[0.3em] text-muted">
                motor · v0.1.0
              </div>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <a
              href={`${API}/health`}
              target="_blank"
              rel="noreferrer"
              className="text-xs font-mono text-muted hover:text-text transition-colors"
              data-testid="health-link"
            >
              /health
            </a>
            <a
              href={`${API}/rulesets`}
              target="_blank"
              rel="noreferrer"
              className="text-xs font-mono text-muted hover:text-text transition-colors"
            >
              /rulesets
            </a>
            <span className="text-xs font-mono text-success flex items-center gap-1.5">
              <ShieldCheck className="w-3.5 h-3.5" />
              determinístico
            </span>
          </div>
        </div>
      </header>

      {/* HERO */}
      <section className="max-w-[1400px] mx-auto px-6 pt-16 pb-12 relative">
        <div className="max-w-3xl">
          <div className="text-[11px] font-mono uppercase tracking-[0.3em] text-accent mb-4">
            POST /api/v1/calcular
          </div>
          <h1 className="font-heading font-black text-4xl sm:text-5xl md:text-6xl tracking-tighter leading-[0.95] mb-6">
            Cálculo <span className="text-accent">IBS/CBS</span> determinístico,
            <br />
            auditável, versionado por data.
          </h1>
          <p className="text-muted text-lg leading-relaxed max-w-2xl">
            Base "por fora". Imposto Seletivo entra na base de IBS/CBS. Regras são{" "}
            <span className="text-text">dado versionado</span>, resolvidas pela{" "}
            <span className="font-mono text-text">dataOperacao</span>. Cada resposta traz
            memória de cálculo, hash do ruleset e trilha de auditoria.
          </p>
        </div>
      </section>

      {/* PLAYGROUND */}
      <section className="max-w-[1400px] mx-auto px-6 pb-24 relative">
        <div className="grid grid-cols-12 gap-6">
          {/* LEFT — Config */}
          <div className="col-span-12 lg:col-span-5 space-y-4">
            <div className="flex items-center justify-between mb-1">
              <div className="text-[11px] uppercase tracking-[0.3em] text-muted">
                Configuração
              </div>
              <button
                onClick={resetGolden}
                className="text-xs font-mono text-muted hover:text-text flex items-center gap-1.5"
                data-testid="reset-golden"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                golden default
              </button>
            </div>

            <div className="border border-border rounded-md p-4 bg-surface">
              <label className="block">
                <span className="text-[11px] uppercase tracking-widest text-muted">
                  dataOperacao (resolve o ruleset)
                </span>
                <input
                  data-testid="data-operacao-input"
                  type="date"
                  value={dataOperacao}
                  onChange={(e) => setDataOperacao(e.target.value)}
                  className="mt-1 w-full bg-bg border border-border rounded-md px-3 py-2 text-sm font-mono focus:border-accent focus:outline-none"
                />
              </label>
            </div>

            <RulesetsPanel rulesets={rulesets} current={currentRulesetId} />

            <div className="space-y-3">
              {itens.map((it, idx) => (
                <ItemEditor
                  key={idx}
                  idx={idx}
                  item={it}
                  onChange={(newItem) => {
                    const cp = [...itens];
                    cp[idx] = newItem;
                    setItens(cp);
                  }}
                  onRemove={() => {
                    const cp = itens.filter((_, i) => i !== idx);
                    setItens(cp.map((x, i) => ({ ...x, numero: i + 1 })));
                  }}
                />
              ))}
              <button
                onClick={() => {
                  setItens([
                    ...itens,
                    {
                      numero: itens.length + 1,
                      descricao: "Novo item",
                      cClassTrib: "000001",
                      quantidade: "1.00",
                      valorUnitario: "100.00",
                      valorItem: "100.00",
                    },
                  ]);
                }}
                className="w-full border border-dashed border-border rounded-md py-3 text-xs uppercase tracking-widest text-muted hover:border-accent hover:text-accent transition-colors"
                data-testid="add-item"
              >
                + adicionar item
              </button>
            </div>

            <button
              onClick={calcular}
              disabled={loading}
              data-testid="calcular-btn"
              className="w-full mt-2 bg-accent text-bg font-bold rounded-md py-4 flex items-center justify-center gap-2 hover:-translate-y-0.5 transition-transform duration-150 disabled:opacity-60 disabled:hover:translate-y-0"
            >
              <Play className="w-4 h-4" strokeWidth={3} />
              {loading ? "Calculando…" : "Calcular"}
            </button>
          </div>

          {/* RIGHT — Response */}
          <div className="col-span-12 lg:col-span-7">
            <div className="flex items-center justify-between mb-3">
              <div className="text-[11px] uppercase tracking-[0.3em] text-muted">
                {response ? "Resposta" : "Preview do request"}
              </div>
              <div className="flex items-center gap-1 border border-border rounded-md p-0.5 bg-surface">
                <button
                  onClick={() => setViewMode("visual")}
                  className={`text-[10px] font-mono uppercase tracking-widest px-2 py-1 rounded ${
                    viewMode === "visual" ? "bg-accent text-bg" : "text-muted hover:text-text"
                  }`}
                  data-testid="view-visual"
                >
                  visual
                </button>
                <button
                  onClick={() => setViewMode("json")}
                  className={`text-[10px] font-mono uppercase tracking-widest px-2 py-1 rounded ${
                    viewMode === "json" ? "bg-accent text-bg" : "text-muted hover:text-text"
                  }`}
                  data-testid="view-json"
                >
                  json
                </button>
              </div>
            </div>

            <div
              className="border border-border rounded-md bg-[#050505] min-h-[500px] p-5 relative overflow-auto"
              data-testid="response-viewer"
              style={{
                boxShadow: "inset 0 1px 0 rgba(255,255,255,0.03)",
              }}
            >
              {!response && !error && !loading && (
                <div>
                  <div className="text-[11px] uppercase tracking-widest text-muted mb-3">
                    request
                  </div>
                  <JsonView data={payload} />
                </div>
              )}

              {loading && (
                <div className="flex items-center gap-2 text-muted font-mono text-sm cursor">
                  <span>› calculando</span>
                </div>
              )}

              {error && (
                <div className="reveal">
                  <div className="text-error font-mono text-xs uppercase tracking-widest mb-3">
                    ⨯ erro
                  </div>
                  <JsonView data={error} />
                </div>
              )}

              {response && viewMode === "json" && (
                <div className="reveal">
                  <JsonView data={response} />
                </div>
              )}

              {response && viewMode === "visual" && (
                <div className="reveal space-y-4">
                  {/* Header info */}
                  <div className="grid grid-cols-2 gap-2 pb-4 border-b border-border">
                    <div className="col-span-2 flex items-center justify-between">
                      <span className="text-[10px] uppercase tracking-widest text-muted">
                        rulesetId
                      </span>
                      <CopyBtn text={response.rulesetId} testid="copy-ruleset-id" />
                    </div>
                    <div className="col-span-2 font-mono text-xs text-accent break-all">
                      {response.rulesetId}
                    </div>
                    <div className="col-span-2 flex items-center justify-between mt-2">
                      <span className="text-[10px] uppercase tracking-widest text-muted">
                        rulesetHash
                      </span>
                      <CopyBtn text={response.rulesetHash} testid="copy-ruleset-hash" />
                    </div>
                    <div className="col-span-2 font-mono text-xs text-muted break-all">
                      {response.rulesetHash}
                    </div>
                    <div>
                      <div className="text-[10px] uppercase tracking-widest text-muted">
                        motorVersao
                      </div>
                      <div className="font-mono text-xs text-text">{response.motorVersao}</div>
                    </div>
                    <div>
                      <div className="text-[10px] uppercase tracking-widest text-muted">
                        calculadoEm
                      </div>
                      <div className="font-mono text-xs text-text">{response.calculadoEm}</div>
                    </div>
                    <div className="col-span-2 mt-2 flex items-center justify-between">
                      <span className="text-[10px] uppercase tracking-widest text-muted">
                        auditoriaId
                      </span>
                      <CopyBtn text={response.auditoriaId} testid="copy-auditoria-id" />
                    </div>
                    <div className="col-span-2 font-mono text-xs text-text break-all flex items-center gap-2">
                      <FileText className="w-3 h-3 text-muted" />
                      <a
                        href={`${API}/auditoria/${response.auditoriaId}`}
                        target="_blank"
                        rel="noreferrer"
                        className="hover:text-accent underline underline-offset-2 decoration-dotted"
                        data-testid="auditoria-link"
                      >
                        {response.auditoriaId}
                      </a>
                    </div>
                  </div>

                  {/* Items */}
                  <div className="space-y-3">
                    {response.itens.map((it, i) => (
                      <ItemResult key={i} item={it} idx={i} />
                    ))}
                  </div>

                  {/* Totais */}
                  <div className="border border-accent/40 rounded-md bg-elev p-4" data-testid="totais">
                    <div className="text-[11px] uppercase tracking-widest text-accent mb-3">
                      Totais
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                      <Metric label="Base total" value={response.totais.baseTotal} />
                      <Metric label="CBS" value={response.totais.cbs} />
                      <Metric label="IBS-UF" value={response.totais.ibsUF} />
                      <Metric label="IBS-Mun" value={response.totais.ibsMunicipio} />
                      <Metric label="IBS total" value={response.totais.ibs} />
                      <Metric label="Imp. Seletivo" value={response.totais.impostoSeletivo} />
                      <div className="col-span-2 border border-accent bg-accent/5 rounded-md p-3">
                        <div className="text-[10px] uppercase tracking-[0.2em] text-accent mb-1">
                          Tributos totais (CBS + IBS)
                        </div>
                        <div className="font-mono text-2xl text-accent">
                          R$ {response.totais.tributosTotais}
                        </div>
                      </div>
                    </div>
                  </div>

                  {response.avisos && response.avisos.length > 0 && (
                    <div className="border border-border rounded-md p-4">
                      <div className="text-[11px] uppercase tracking-widest text-muted mb-2">
                        avisos
                      </div>
                      <ul className="space-y-1 text-xs text-muted">
                        {response.avisos.map((a, i) => (
                          <li key={i} className="flex gap-2">
                            <span className="text-accent">›</span>
                            <span>{a}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="border-t border-border py-8 relative">
        <div className="max-w-[1400px] mx-auto px-6 flex flex-wrap items-center justify-between gap-4">
          <div className="font-mono text-xs text-muted">
            fiscalcore-motor · Decimal · auditoria append-only · resolvido por dataOperacao
          </div>
          <div className="flex items-center gap-4 text-xs font-mono text-muted">
            <span>MVP · MongoDB → PostgreSQL na virada de produção</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
