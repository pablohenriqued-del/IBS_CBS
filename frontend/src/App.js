import React, { useEffect, useMemo, useState } from "react";
import axios from "axios";
import {
  Check,
  Copy,
  Play,
  RefreshCw,
  ShieldCheck,
  Layers,
  FileText,
  ChevronRight,
  ArrowUpRight,
  Calendar,
  Hash,
  Fingerprint,
} from "lucide-react";

const BACKEND = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND}/api/v1`;

// -------------------------------------------------------------------------
// Logotipo custom
// -------------------------------------------------------------------------
function Logo({ size = 36 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 40 40"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden
    >
      {/* Contorno com corner-cut (evoca papel de nota fiscal) */}
      <path
        d="M4 4 H30 L36 10 V36 H4 Z"
        stroke="#D4A574"
        strokeWidth="1.4"
        strokeLinejoin="miter"
        fill="rgba(212,165,116,0.04)"
      />
      {/* Linhas horizontais evocando itens de uma nota */}
      <line x1="10" y1="14" x2="26" y2="14" stroke="#D4A574" strokeWidth="1.6" />
      <line x1="10" y1="20" x2="22" y2="20" stroke="#D4A574" strokeWidth="1.6" />
      <line x1="10" y1="26" x2="18" y2="26" stroke="#D4A574" strokeWidth="1.6" />
      {/* Ponto de decisão / hash (determinismo) */}
      <circle cx="28" cy="30" r="2.2" fill="#D4A574" />
    </svg>
  );
}

// -------------------------------------------------------------------------
// Golden request
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
// JSON viewer
// -------------------------------------------------------------------------
function JsonView({ data }) {
  const render = (v, indent = 0) => {
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
      className="inline-flex items-center gap-1.5 text-[11px] font-mono text-muted hover:text-accent transition-colors duration-150"
    >
      {copied ? <Check className="w-3.5 h-3.5 text-accent" /> : <Copy className="w-3.5 h-3.5" />}
      {copied ? "copiado" : "copiar"}
    </button>
  );
}

// -------------------------------------------------------------------------
// Rulesets panel
// -------------------------------------------------------------------------
function RulesetsPanel({ rulesets, current }) {
  return (
    <div
      className="border border-border rounded-md bg-surface overflow-hidden"
      data-testid="rulesets-panel"
    >
      <div className="px-4 py-3 border-b border-border flex items-center gap-2">
        <Layers className="w-3.5 h-3.5 text-muted" />
        <span className="text-[10px] uppercase tracking-[0.25em] font-medium text-muted">
          Rulesets versionados
        </span>
      </div>
      <div className="divide-y divide-border">
        {rulesets.length === 0 && <div className="p-4 text-sm text-muted">Carregando…</div>}
        {rulesets.map((r) => {
          const active = current === r.id;
          return (
            <div
              key={r.id}
              data-testid={`ruleset-${r.id.replace(/[:.]/g, "-")}`}
              className={`p-4 transition-colors ${active ? "bg-accentDim" : ""}`}
            >
              <div className="flex items-center justify-between gap-2 mb-1.5">
                <span className="font-mono text-xs text-strong">{r.id}</span>
                {active && (
                  <span className="text-[9px] font-mono uppercase tracking-[0.25em] text-accent flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-accent" />
                    vigente
                  </span>
                )}
              </div>
              <div className="text-[13px] text-muted mb-2">{r.descricao}</div>
              <div className="flex flex-wrap gap-x-4 gap-y-1 text-[10.5px] font-mono text-muted">
                <span>
                  {r.vigenciaInicio} → {r.vigenciaFim || "∞"}
                </span>
                <span>
                  CBS <span className="text-strong">{r.cbs.aliquotaNominal}%</span>
                </span>
                <span>
                  UF <span className="text-strong">{r.ibs.aliquotaUF}%</span>
                </span>
                <span>
                  Mun <span className="text-strong">{r.ibs.aliquotaMunicipio}%</span>
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// -------------------------------------------------------------------------
// Item editor
// -------------------------------------------------------------------------
function ItemEditor({ item, onChange, onRemove, idx }) {
  const upd = (k, v) => onChange({ ...item, [k]: v });
  const updIS = (k, v) => {
    const is = item.impostoSeletivo || { aliquota: "0.0000", cst: "01" };
    onChange({ ...item, impostoSeletivo: { ...is, [k]: v } });
  };
  const toggleIS = (on) => {
    if (on) onChange({ ...item, impostoSeletivo: { aliquota: "10.0000", cst: "01" } });
    else {
      const { impostoSeletivo, ...rest } = item;
      onChange(rest);
    }
  };
  return (
    <div
      className="group border border-border rounded-md p-4 bg-surface hover:border-borderHover transition-colors"
      data-testid={`item-editor-${idx}`}
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-baseline gap-2">
          <span className="font-heading text-lg text-strong tabular-nums">
            {String(item.numero).padStart(2, "0")}
          </span>
          <span className="text-[10px] uppercase tracking-[0.25em] text-muted">item</span>
        </div>
        <button
          onClick={onRemove}
          className="text-[11px] font-mono text-muted hover:text-error transition-colors opacity-0 group-hover:opacity-100"
          data-testid={`remove-item-${idx}`}
        >
          remover
        </button>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <label className="col-span-2">
          <span className="text-[10px] uppercase tracking-[0.2em] text-muted">Descrição</span>
          <input
            data-testid={`item-${idx}-descricao`}
            value={item.descricao || ""}
            onChange={(e) => upd("descricao", e.target.value)}
            className="mt-1 w-full bg-bg border border-border rounded-md px-3 py-2 text-sm focus:border-accent focus:outline-none transition-colors"
          />
        </label>
        <label>
          <span className="text-[10px] uppercase tracking-[0.2em] text-muted">cClassTrib</span>
          <input
            data-testid={`item-${idx}-cclasstrib`}
            value={item.cClassTrib}
            onChange={(e) => upd("cClassTrib", e.target.value)}
            className="mt-1 w-full bg-bg border border-border rounded-md px-3 py-2 text-sm font-mono focus:border-accent focus:outline-none transition-colors"
          />
        </label>
        <label>
          <span className="text-[10px] uppercase tracking-[0.2em] text-muted">NCM</span>
          <input
            data-testid={`item-${idx}-ncm`}
            value={item.ncm || ""}
            onChange={(e) => upd("ncm", e.target.value)}
            className="mt-1 w-full bg-bg border border-border rounded-md px-3 py-2 text-sm font-mono focus:border-accent focus:outline-none transition-colors"
          />
        </label>
        <label>
          <span className="text-[10px] uppercase tracking-[0.2em] text-muted">Quantidade</span>
          <input
            data-testid={`item-${idx}-quantidade`}
            value={item.quantidade}
            onChange={(e) => upd("quantidade", e.target.value)}
            className="mt-1 w-full bg-bg border border-border rounded-md px-3 py-2 text-sm font-mono focus:border-accent focus:outline-none transition-colors"
          />
        </label>
        <label>
          <span className="text-[10px] uppercase tracking-[0.2em] text-muted">Valor Unit.</span>
          <input
            data-testid={`item-${idx}-valor-unit`}
            value={item.valorUnitario}
            onChange={(e) => upd("valorUnitario", e.target.value)}
            className="mt-1 w-full bg-bg border border-border rounded-md px-3 py-2 text-sm font-mono focus:border-accent focus:outline-none transition-colors"
          />
        </label>
        <label className="col-span-2">
          <span className="text-[10px] uppercase tracking-[0.2em] text-muted">Valor Item</span>
          <input
            data-testid={`item-${idx}-valor-item`}
            value={item.valorItem}
            onChange={(e) => upd("valorItem", e.target.value)}
            className="mt-1 w-full bg-bg border border-border rounded-md px-3 py-2 text-sm font-mono focus:border-accent focus:outline-none transition-colors"
          />
        </label>
      </div>
      <div className="mt-4 border-t border-border pt-3">
        <label className="flex items-center gap-2 cursor-pointer group/is">
          <input
            type="checkbox"
            data-testid={`item-${idx}-is-toggle`}
            checked={!!item.impostoSeletivo}
            onChange={(e) => toggleIS(e.target.checked)}
            className="accent-accent"
          />
          <span className="text-[11px] uppercase tracking-[0.2em] text-muted group-hover/is:text-strong transition-colors">
            Imposto Seletivo (entra na base)
          </span>
        </label>
        {item.impostoSeletivo && (
          <div className="grid grid-cols-2 gap-3 mt-3">
            <label>
              <span className="text-[10px] uppercase tracking-[0.2em] text-muted">
                Alíquota IS (%)
              </span>
              <input
                data-testid={`item-${idx}-is-aliquota`}
                value={item.impostoSeletivo.aliquota}
                onChange={(e) => updIS("aliquota", e.target.value)}
                className="mt-1 w-full bg-bg border border-border rounded-md px-3 py-2 text-sm font-mono focus:border-accent focus:outline-none transition-colors"
              />
            </label>
            <label>
              <span className="text-[10px] uppercase tracking-[0.2em] text-muted">CST IS</span>
              <input
                data-testid={`item-${idx}-is-cst`}
                value={item.impostoSeletivo.cst || ""}
                onChange={(e) => updIS("cst", e.target.value)}
                className="mt-1 w-full bg-bg border border-border rounded-md px-3 py-2 text-sm font-mono focus:border-accent focus:outline-none transition-colors"
              />
            </label>
          </div>
        )}
      </div>
    </div>
  );
}

function Metric({ label, value, sub }) {
  return (
    <div className="border border-border bg-bg rounded-md p-3">
      <div className="text-[9.5px] uppercase tracking-[0.25em] text-muted mb-1.5">{label}</div>
      <div className="big-num text-lg text-strong">R$ {value}</div>
      {sub && <div className="font-mono text-[10.5px] text-muted mt-0.5">{sub}</div>}
    </div>
  );
}

function ItemResult({ item, idx }) {
  const [open, setOpen] = useState(idx === 0);
  return (
    <div
      className="border border-border rounded-md bg-surface reveal overflow-hidden"
      data-testid={`result-item-${item.numero}`}
      style={{ "--i": idx }}
    >
      <button
        onClick={() => setOpen(!open)}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-elev transition-colors"
      >
        <div className="flex items-center gap-3">
          <span className="font-heading text-base text-strong tabular-nums">
            {String(item.numero).padStart(2, "0")}
          </span>
          <span className="text-[10px] uppercase tracking-[0.25em] text-muted">
            base R$ <span className="big-num text-strong ml-0.5">{item.base}</span>
          </span>
          {item.impostoSeletivo && (
            <span className="text-[9.5px] font-mono uppercase tracking-[0.25em] text-accent border border-accent/40 rounded px-1.5 py-0.5">
              IS
            </span>
          )}
        </div>
        <div className="flex items-center gap-5">
          <span className="text-[10.5px] font-mono text-muted">
            CBS <span className="text-strong">{item.cbs.valor}</span>
          </span>
          <span className="text-[10.5px] font-mono text-muted">
            IBS <span className="text-strong">{item.ibs.valor}</span>
          </span>
          <span className="big-num text-sm text-accent">Σ {item.totalItem}</span>
          <ChevronRight
            className={`w-4 h-4 text-muted transition-transform duration-200 ${
              open ? "rotate-90" : ""
            }`}
          />
        </div>
      </button>
      {open && (
        <div className="border-t border-border p-4 space-y-4 bg-bg/40">
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
            <div className="text-[10px] uppercase tracking-[0.25em] text-muted mb-2 flex items-center gap-2">
              <span className="rule-accent" />
              Memória de cálculo
            </div>
            <ol className="space-y-1 font-mono text-[12px] text-text/90 border-l border-border pl-4">
              {item.memoriaCalculo.map((linha, i) => (
                <li key={i} className="flex gap-3">
                  <span className="text-muted select-none tabular-nums">
                    {String(i + 1).padStart(2, "0")}
                  </span>
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

// -------------------------------------------------------------------------
// Features strip
// -------------------------------------------------------------------------
function Features() {
  const items = [
    {
      k: "01",
      title: "Decimal, nunca float",
      body: "Todos os cálculos monetários usam Decimal com ROUND_HALF_UP a 2 casas. Zero arredondamento binário silencioso.",
    },
    {
      k: "02",
      title: "Base por fora",
      body: 'IBS e CBS incidem sobre uma base que não inclui os próprios tributos nem um ao outro — diferente do "por dentro" do ICMS.',
    },
    {
      k: "03",
      title: "IS compõe a base",
      body: "Quando há Imposto Seletivo, ele é apurado antes e entra na base de IBS/CBS. O motor faz isso sem exceções.",
    },
    {
      k: "04",
      title: "Regra é dado, não código",
      body: "Rulesets versionados com hash SHA-256 e vigência. A dataOperacao resolve a regra — nunca o dia em que foi processada.",
    },
  ];
  return (
    <section className="max-w-[1400px] mx-auto px-6 py-16 border-y border-border relative">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-x-8 gap-y-10">
        {items.map((it, i) => (
          <div key={it.k} className="reveal stagger" style={{ "--i": i }}>
            <div className="font-heading text-3xl text-accent mb-3 tabular-nums">{it.k}</div>
            <div className="font-heading text-lg text-strong mb-2 leading-snug">{it.title}</div>
            <p className="text-[13.5px] text-muted leading-relaxed">{it.body}</p>
          </div>
        ))}
      </div>
    </section>
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
  const [viewMode, setViewMode] = useState("visual");

  useEffect(() => {
    axios
      .get(`${API}/rulesets`)
      .then((r) => {
        const map = new Map();
        for (const rs of r.data.rulesets) map.set(rs.id, rs);
        setRulesets(Array.from(map.values()));
      })
      .catch(() => setRulesets([]));
  }, []);

  const buildPayload = () => ({ ...GOLDEN_REQUEST, dataOperacao, itens });

  const calcular = async () => {
    setLoading(true);
    setError(null);
    setResponse(null);
    try {
      const { data } = await axios.post(`${API}/calcular`, buildPayload());
      setResponse(data);
      // Scroll to response on mobile
      setTimeout(() => {
        const el = document.querySelector("[data-testid='response-viewer']");
        if (el && window.innerWidth < 1024) el.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 100);
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
  const payload = useMemo(() => buildPayload(), [dataOperacao, itens]); // eslint-disable-line

  return (
    <div className="grain min-h-screen relative">
      {/* HEADER */}
      <header className="sticky top-0 z-20 backdrop-blur-md bg-bg/85 border-b border-border">
        <div className="max-w-[1400px] mx-auto px-6 py-3.5 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Logo size={30} />
            <div className="flex items-baseline gap-2">
              <span className="font-heading font-semibold text-[18px] text-strong tracking-tight">
                FiscalCore
              </span>
              <span className="font-mono text-[10px] uppercase tracking-[0.3em] text-muted">
                motor
              </span>
            </div>
          </div>
          <div className="flex items-center gap-5">
            <a
              href={`${API}/health`}
              target="_blank"
              rel="noreferrer"
              className="text-[12px] font-mono text-muted hover:text-strong transition-colors flex items-center gap-1.5"
              data-testid="health-link"
            >
              /health
              <ArrowUpRight className="w-3 h-3" />
            </a>
            <a
              href={`${API}/rulesets`}
              target="_blank"
              rel="noreferrer"
              className="text-[12px] font-mono text-muted hover:text-strong transition-colors flex items-center gap-1.5"
            >
              /rulesets
              <ArrowUpRight className="w-3 h-3" />
            </a>
            <span className="hidden md:flex text-[11px] font-mono text-accent items-center gap-1.5 border border-accent/25 rounded-full px-2.5 py-1 bg-accentDim">
              <ShieldCheck className="w-3 h-3" />
              determinístico · auditável
            </span>
          </div>
        </div>
      </header>

      {/* HERO */}
      <section className="relative hero-glow max-w-[1400px] mx-auto px-6 pt-20 pb-16">
        <div className="relative z-10 max-w-4xl">
          <div className="flex items-center gap-2 mb-8 reveal">
            <span className="rule-accent" />
            <span className="text-[11px] font-mono uppercase tracking-[0.35em] text-accent">
              POST /api/v1/calcular
            </span>
          </div>
          <h1 className="font-heading font-medium text-[52px] md:text-[68px] leading-[1.02] tracking-tightest text-strong reveal">
            O cálculo de{" "}
            <span className="text-accent">IBS &amp; CBS</span>
            {" "}que uma{" "}
            <span className="serif-italic">fiscalização</span>
            {" "}aceita.
          </h1>
          <div className="mt-8 space-y-4 max-w-2xl reveal" style={{ animationDelay: "120ms" }}>
            <p className="text-[17px] leading-[1.65] text-text">
              Uma nota emitida em julho é calculada com a{" "}
              <span className="text-strong">regra de julho</span> — hoje, amanhã
              ou numa fiscalização daqui a cinco anos. Rulesets são dado versionado,
              resolvidos pela <span className="font-mono text-strong">dataOperacao</span>.
            </p>
            <p className="text-[15px] leading-[1.65] text-muted">
              Base <span className="dot-underline text-text">por fora</span>. Imposto
              Seletivo compondo a base correta. Memória de cálculo linha a linha,
              hash do ruleset e <span className="text-text">trilha de auditoria imutável</span>{" "}
              em cada resposta. Tudo em <span className="font-mono text-text">Decimal</span>,
              nunca em <span className="font-mono line-through text-muted/70">float</span>.
            </p>
          </div>
          <div className="mt-10 flex flex-wrap items-center gap-3 reveal" style={{ animationDelay: "220ms" }}>
            <a
              href="#playground"
              className="group inline-flex items-center gap-2 bg-accent text-bg font-medium rounded-md px-5 py-2.5 hover:bg-accentHover hover:-translate-y-0.5 transition-transform duration-150"
              data-testid="cta-testar"
            >
              <Play className="w-4 h-4" strokeWidth={2.5} />
              Testar contra os casos-ouro
            </a>
            <span className="text-[12px] font-mono text-muted flex items-center gap-2">
              <span className="kbd">3</span>
              itens · <span className="text-strong">R$ 1.720,00</span> base ·{" "}
              <span className="text-strong">R$ 376,30</span> em tributos
            </span>
          </div>
        </div>
      </section>

      <Features />

      {/* PLAYGROUND */}
      <section
        id="playground"
        className="max-w-[1400px] mx-auto px-6 py-20 relative"
      >
        <div className="flex items-baseline justify-between mb-8">
          <div>
            <div className="text-[11px] font-mono uppercase tracking-[0.3em] text-muted mb-2">
              Playground
            </div>
            <h2 className="font-heading text-3xl md:text-4xl tracking-tight text-strong">
              Os três <span className="serif-italic text-accent">casos-ouro</span>, ao vivo.
            </h2>
          </div>
          <div className="hidden md:flex text-[12px] font-mono text-muted items-center gap-2">
            <Calendar className="w-3.5 h-3.5" />
            {new Date().toISOString().slice(0, 10)}
          </div>
        </div>

        <div className="grid grid-cols-12 gap-6">
          {/* LEFT — Config */}
          <div className="col-span-12 lg:col-span-5 space-y-4">
            <div className="flex items-center justify-between mb-1">
              <div className="text-[10px] uppercase tracking-[0.3em] text-muted">
                Configuração
              </div>
              <button
                onClick={resetGolden}
                className="text-[11px] font-mono text-muted hover:text-accent flex items-center gap-1.5 transition-colors"
                data-testid="reset-golden"
              >
                <RefreshCw className="w-3 h-3" />
                golden default
              </button>
            </div>

            <div className="border border-border rounded-md p-4 bg-surface">
              <label className="block">
                <span className="text-[10px] uppercase tracking-[0.25em] text-muted">
                  dataOperacao (resolve o ruleset)
                </span>
                <input
                  data-testid="data-operacao-input"
                  type="date"
                  value={dataOperacao}
                  onChange={(e) => setDataOperacao(e.target.value)}
                  className="mt-1.5 w-full bg-bg border border-border rounded-md px-3 py-2 text-sm font-mono focus:border-accent focus:outline-none transition-colors"
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
                className="w-full border border-dashed border-border rounded-md py-3 text-[11px] uppercase tracking-[0.25em] text-muted hover:border-accent hover:text-accent transition-colors"
                data-testid="add-item"
              >
                + adicionar item
              </button>
            </div>

            <button
              onClick={calcular}
              disabled={loading}
              data-testid="calcular-btn"
              className="w-full mt-2 bg-accent text-bg font-semibold rounded-md py-4 flex items-center justify-center gap-2 hover:bg-accentHover hover:-translate-y-0.5 transition-transform duration-150 disabled:opacity-60 disabled:hover:translate-y-0"
            >
              <Play className="w-4 h-4" strokeWidth={2.5} />
              {loading ? "Calculando…" : "Calcular"}
            </button>
          </div>

          {/* RIGHT — Response */}
          <div className="col-span-12 lg:col-span-7">
            <div className="flex items-center justify-between mb-3">
              <div className="text-[10px] uppercase tracking-[0.3em] text-muted">
                {response ? "Resposta" : "Preview do request"}
              </div>
              <div className="flex items-center gap-1 border border-border rounded-md p-0.5 bg-surface">
                <button
                  onClick={() => setViewMode("visual")}
                  className={`text-[10px] font-mono uppercase tracking-[0.2em] px-2.5 py-1 rounded transition-colors ${
                    viewMode === "visual"
                      ? "bg-accent text-bg"
                      : "text-muted hover:text-strong"
                  }`}
                  data-testid="view-visual"
                >
                  visual
                </button>
                <button
                  onClick={() => setViewMode("json")}
                  className={`text-[10px] font-mono uppercase tracking-[0.2em] px-2.5 py-1 rounded transition-colors ${
                    viewMode === "json"
                      ? "bg-accent text-bg"
                      : "text-muted hover:text-strong"
                  }`}
                  data-testid="view-json"
                >
                  json
                </button>
              </div>
            </div>

            <div
              className="border border-border rounded-md bg-[#060708] min-h-[560px] p-5 relative overflow-auto"
              data-testid="response-viewer"
              style={{ boxShadow: "inset 0 1px 0 rgba(255,255,255,0.03)" }}
            >
              {!response && !error && !loading && (
                <div>
                  <div className="text-[10px] uppercase tracking-[0.25em] text-muted mb-3 flex items-center gap-2">
                    <span className="rule-accent" />
                    request
                  </div>
                  <JsonView data={payload} />
                </div>
              )}

              {loading && (
                <div className="flex items-center gap-2 text-muted font-mono text-sm cursor">
                  <span>› resolvendo ruleset e calculando</span>
                </div>
              )}

              {error && (
                <div className="reveal">
                  <div className="text-error font-mono text-[10px] uppercase tracking-[0.3em] mb-3">
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
                <div className="reveal space-y-5">
                  {/* Header info */}
                  <div className="border-b border-border pb-4 space-y-3">
                    <div>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-[10px] uppercase tracking-[0.25em] text-muted flex items-center gap-1.5">
                          <Layers className="w-3 h-3" />
                          rulesetId
                        </span>
                        <CopyBtn text={response.rulesetId} testid="copy-ruleset-id" />
                      </div>
                      <div className="font-mono text-[13px] text-accent break-all">
                        {response.rulesetId}
                      </div>
                    </div>

                    <div>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-[10px] uppercase tracking-[0.25em] text-muted flex items-center gap-1.5">
                          <Hash className="w-3 h-3" />
                          rulesetHash
                        </span>
                        <CopyBtn text={response.rulesetHash} testid="copy-ruleset-hash" />
                      </div>
                      <div className="font-mono text-[11.5px] text-muted break-all">
                        {response.rulesetHash}
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-3 pt-2">
                      <div>
                        <div className="text-[10px] uppercase tracking-[0.25em] text-muted mb-1">
                          motorVersao
                        </div>
                        <div className="font-mono text-[12px] text-strong">
                          {response.motorVersao}
                        </div>
                      </div>
                      <div>
                        <div className="text-[10px] uppercase tracking-[0.25em] text-muted mb-1">
                          calculadoEm
                        </div>
                        <div className="font-mono text-[12px] text-strong">
                          {response.calculadoEm}
                        </div>
                      </div>
                    </div>

                    <div>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-[10px] uppercase tracking-[0.25em] text-muted flex items-center gap-1.5">
                          <Fingerprint className="w-3 h-3" />
                          auditoriaId
                        </span>
                        <CopyBtn text={response.auditoriaId} testid="copy-auditoria-id" />
                      </div>
                      <div className="font-mono text-[12px] flex items-center gap-2">
                        <FileText className="w-3 h-3 text-muted" />
                        <a
                          href={`${API}/auditoria/${response.auditoriaId}`}
                          target="_blank"
                          rel="noreferrer"
                          className="text-text hover:text-accent underline underline-offset-2 decoration-dotted decoration-accent/50 transition-colors"
                          data-testid="auditoria-link"
                        >
                          {response.auditoriaId}
                        </a>
                      </div>
                    </div>
                  </div>

                  {/* Items */}
                  <div className="space-y-3">
                    {response.itens.map((it, i) => (
                      <ItemResult key={i} item={it} idx={i} />
                    ))}
                  </div>

                  {/* Totais */}
                  <div
                    className="border border-accent/40 rounded-md bg-gradient-to-br from-accentDim to-transparent p-5"
                    data-testid="totais"
                  >
                    <div className="text-[10px] uppercase tracking-[0.3em] text-accent mb-4 flex items-center gap-2">
                      <span className="rule-accent" />
                      Totais consolidados
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
                      <Metric label="Base total" value={response.totais.baseTotal} />
                      <Metric label="CBS" value={response.totais.cbs} />
                      <Metric label="IBS-UF" value={response.totais.ibsUF} />
                      <Metric label="IBS-Mun" value={response.totais.ibsMunicipio} />
                      <Metric label="IBS total" value={response.totais.ibs} />
                      <Metric label="Imp. Seletivo" value={response.totais.impostoSeletivo} />
                    </div>
                    <div className="border border-accent bg-bg rounded-md p-4">
                      <div className="text-[10px] uppercase tracking-[0.3em] text-accent mb-2">
                        Tributos totais (CBS + IBS)
                      </div>
                      <div className="big-num text-3xl text-strong">
                        R$ {response.totais.tributosTotais}
                      </div>
                    </div>
                  </div>

                  {response.avisos && response.avisos.length > 0 && (
                    <div className="border border-border rounded-md p-4 bg-surface">
                      <div className="text-[10px] uppercase tracking-[0.25em] text-muted mb-2">
                        Avisos
                      </div>
                      <ul className="space-y-1.5 text-[12.5px] text-muted">
                        {response.avisos.map((a, i) => (
                          <li key={i} className="flex gap-2">
                            <span className="text-accent flex-shrink-0">›</span>
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
      <footer className="border-t border-border py-10 relative">
        <div className="max-w-[1400px] mx-auto px-6 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <Logo size={22} />
            <div>
              <div className="font-heading text-sm text-strong">FiscalCore Motor</div>
              <div className="font-mono text-[10px] uppercase tracking-[0.25em] text-muted">
                MVP · MongoDB → PostgreSQL na virada de produção
              </div>
            </div>
          </div>
          <div className="font-mono text-[11px] text-muted">
            Decimal · auditoria append-only · resolvido por dataOperacao
          </div>
        </div>
      </footer>
    </div>
  );
}
