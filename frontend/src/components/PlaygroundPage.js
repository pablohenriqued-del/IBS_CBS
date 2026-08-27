import React, { useEffect, useMemo, useState } from "react";
import {
  Play, RefreshCw, Layers, FileText, ChevronRight, Hash, Fingerprint,
  Check, Copy, Server, X,
} from "lucide-react";
import { api, formatApiError } from "../api";
import { Metric } from "./Shared";

// ---------- Golden request ----------
const GOLDEN_REQUEST = {
  referencia: "pedido-2026-000123",
  dataOperacao: "2026-08-26",
  modo: "producao",
  estabelecimento: { cnpj: "12345678000190", uf: "SP", municipioIBGE: "3550308", regime: "regular" },
  destinatario: { uf: "RJ", municipioIBGE: "3304557", consumidorFinal: true, contribuinte: false },
  operacao: { tipo: "venda" },
  itens: [
    { numero: 1, descricao: "Cadeira de escritório", ncm: "94013000", cClassTrib: "000001", quantidade: "1.00", valorUnitario: "1000.00", valorItem: "1000.00" },
    { numero: 2, descricao: "Medicamento (lista com redução de 60%)", ncm: "30049099", cClassTrib: "200052", quantidade: "1.00", valorUnitario: "500.00", valorItem: "500.00" },
    { numero: 3, descricao: "Bebida açucarada (sujeita ao IS)", ncm: "22021000", cClassTrib: "000001", quantidade: "1.00", valorUnitario: "200.00", valorItem: "200.00", impostoSeletivo: { aliquota: "10.0000", cst: "01" } },
  ],
};

function JsonView({ data }) {
  const render = (v, indent = 0) => {
    if (v === null) return <span className="jnull">null</span>;
    if (typeof v === "boolean") return <span className="jbool">{String(v)}</span>;
    if (typeof v === "number") return <span className="jnum">{v}</span>;
    if (typeof v === "string") return <span className="jstr">"{v}"</span>;
    if (Array.isArray(v)) {
      if (v.length === 0) return <span className="jpunc">[]</span>;
      return (<>
        <span className="jpunc">[</span>
        {v.map((el, i) => (<div key={i} style={{ paddingLeft: (indent + 1) * 12 }}>{render(el, indent + 1)}{i < v.length - 1 && <span className="jpunc">,</span>}</div>))}
        <div style={{ paddingLeft: indent * 12 }}><span className="jpunc">]</span></div>
      </>);
    }
    if (typeof v === "object") {
      const keys = Object.keys(v);
      if (keys.length === 0) return <span className="jpunc">{"{}"}</span>;
      return (<>
        <span className="jpunc">{"{"}</span>
        {keys.map((k, i) => (<div key={k} style={{ paddingLeft: (indent + 1) * 12 }}><span className="jkey">"{k}"</span><span className="jpunc">: </span>{render(v[k], indent + 1)}{i < keys.length - 1 && <span className="jpunc">,</span>}</div>))}
        <div style={{ paddingLeft: indent * 12 }}><span className="jpunc">{"}"}</span></div>
      </>);
    }
    return String(v);
  };
  return <div className="font-mono text-[13px] leading-6">{render(data)}</div>;
}

function CopyBtn({ text, testid }) {
  const [copied, setCopied] = useState(false);
  return (
    <button data-testid={testid} onClick={() => { navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 1200); }}
      className="inline-flex items-center gap-1.5 text-[11px] font-mono text-muted hover:text-accent transition-colors">
      {copied ? <Check className="w-3.5 h-3.5 text-accent" /> : <Copy className="w-3.5 h-3.5" />}
      {copied ? "copiado" : "copiar"}
    </button>
  );
}

function ItemEditor({ item, onChange, onRemove, idx }) {
  const upd = (k, v) => onChange({ ...item, [k]: v });
  const updIS = (k, v) => { const is = item.impostoSeletivo || { aliquota: "0.0000", cst: "01" }; onChange({ ...item, impostoSeletivo: { ...is, [k]: v } }); };
  const toggleIS = (on) => { if (on) onChange({ ...item, impostoSeletivo: { aliquota: "10.0000", cst: "01" } }); else { const { impostoSeletivo, ...rest } = item; onChange(rest); } };
  return (
    <div className="group border border-border rounded-md p-4 bg-surface hover:border-borderHover transition-colors" data-testid={`item-editor-${idx}`}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-baseline gap-2">
          <span className="font-heading text-lg text-strong tabular-nums">{String(item.numero).padStart(2, "0")}</span>
          <span className="text-[10px] uppercase tracking-[0.25em] text-muted">item</span>
        </div>
        <button onClick={onRemove} className="text-[11px] font-mono text-muted hover:text-error opacity-0 group-hover:opacity-100" data-testid={`remove-item-${idx}`}>remover</button>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <label className="col-span-2"><span className="text-[10px] uppercase tracking-[0.2em] text-muted">Descrição</span>
          <input value={item.descricao || ""} onChange={(e) => upd("descricao", e.target.value)} className="mt-1 w-full bg-bg border border-border rounded-md px-3 py-2 text-sm focus:border-accent focus:outline-none" /></label>
        <label><span className="text-[10px] uppercase tracking-[0.2em] text-muted">cClassTrib</span>
          <input value={item.cClassTrib} onChange={(e) => upd("cClassTrib", e.target.value)} className="mt-1 w-full bg-bg border border-border rounded-md px-3 py-2 text-sm font-mono focus:border-accent focus:outline-none" /></label>
        <label><span className="text-[10px] uppercase tracking-[0.2em] text-muted">NCM</span>
          <input value={item.ncm || ""} onChange={(e) => upd("ncm", e.target.value)} className="mt-1 w-full bg-bg border border-border rounded-md px-3 py-2 text-sm font-mono focus:border-accent focus:outline-none" /></label>
        <label><span className="text-[10px] uppercase tracking-[0.2em] text-muted">Quantidade</span>
          <input value={item.quantidade} onChange={(e) => upd("quantidade", e.target.value)} className="mt-1 w-full bg-bg border border-border rounded-md px-3 py-2 text-sm font-mono focus:border-accent focus:outline-none" /></label>
        <label><span className="text-[10px] uppercase tracking-[0.2em] text-muted">Valor Unit.</span>
          <input value={item.valorUnitario} onChange={(e) => upd("valorUnitario", e.target.value)} className="mt-1 w-full bg-bg border border-border rounded-md px-3 py-2 text-sm font-mono focus:border-accent focus:outline-none" /></label>
        <label className="col-span-2"><span className="text-[10px] uppercase tracking-[0.2em] text-muted">Valor Item</span>
          <input value={item.valorItem} onChange={(e) => upd("valorItem", e.target.value)} className="mt-1 w-full bg-bg border border-border rounded-md px-3 py-2 text-sm font-mono focus:border-accent focus:outline-none" /></label>
      </div>
      <div className="mt-4 border-t border-border pt-3">
        <label className="flex items-center gap-2 cursor-pointer">
          <input type="checkbox" checked={!!item.impostoSeletivo} onChange={(e) => toggleIS(e.target.checked)} className="accent-accent" />
          <span className="text-[11px] uppercase tracking-[0.2em] text-muted">Imposto Seletivo (entra na base)</span>
        </label>
        {item.impostoSeletivo && (
          <div className="grid grid-cols-2 gap-3 mt-3">
            <label><span className="text-[10px] uppercase tracking-[0.2em] text-muted">Alíquota IS (%)</span>
              <input value={item.impostoSeletivo.aliquota} onChange={(e) => updIS("aliquota", e.target.value)} className="mt-1 w-full bg-bg border border-border rounded-md px-3 py-2 text-sm font-mono focus:border-accent focus:outline-none" /></label>
            <label><span className="text-[10px] uppercase tracking-[0.2em] text-muted">CST IS</span>
              <input value={item.impostoSeletivo.cst || ""} onChange={(e) => updIS("cst", e.target.value)} className="mt-1 w-full bg-bg border border-border rounded-md px-3 py-2 text-sm font-mono focus:border-accent focus:outline-none" /></label>
          </div>
        )}
      </div>
    </div>
  );
}

function ItemResult({ item, idx }) {
  const [open, setOpen] = useState(idx === 0);
  return (
    <div className="border border-border rounded-md bg-surface reveal overflow-hidden" data-testid={`result-item-${item.numero}`} style={{ "--i": idx }}>
      <button onClick={() => setOpen(!open)} className="w-full px-4 py-3 flex items-center justify-between hover:bg-elev transition-colors">
        <div className="flex items-center gap-3">
          <span className="font-heading text-base text-strong tabular-nums">{String(item.numero).padStart(2, "0")}</span>
          <span className="text-[10px] uppercase tracking-[0.25em] text-muted">base R$ <span className="big-num text-strong ml-0.5">{item.base}</span></span>
          {item.impostoSeletivo && <span className="text-[9.5px] font-mono uppercase tracking-[0.25em] text-accent border border-accent/40 rounded px-1.5 py-0.5">IS</span>}
        </div>
        <div className="flex items-center gap-5">
          <span className="text-[10.5px] font-mono text-muted">CBS <span className="text-strong">{item.cbs.valor}</span></span>
          <span className="text-[10.5px] font-mono text-muted">IBS <span className="text-strong">{item.ibs.valor}</span></span>
          <span className="big-num text-sm text-accent">Σ {item.totalItem}</span>
          <ChevronRight className={`w-4 h-4 text-muted transition-transform ${open ? "rotate-90" : ""}`} />
        </div>
      </button>
      {open && (
        <div className="border-t border-border p-4 space-y-4 bg-bg/40">
          <div className="grid grid-cols-3 gap-3">
            <Metric label="Base IBS/CBS" value={`R$ ${item.base}`} />
            <Metric label="CBS" value={`R$ ${item.cbs.valor}`} sub={`${item.cbs.aliquotaEfetiva}%`} />
            <Metric label="IBS total" value={`R$ ${item.ibs.valor}`} />
            {item.impostoSeletivo && <Metric label="Imp. Seletivo" value={`R$ ${item.impostoSeletivo.valor}`} sub={`${item.impostoSeletivo.aliquota}%`} />}
            <Metric label="IBS-UF" value={`R$ ${item.ibs.uf.valor}`} sub={`${item.ibs.uf.aliquota}%`} />
            <Metric label="IBS-Mun" value={`R$ ${item.ibs.municipio.valor}`} sub={`${item.ibs.municipio.aliquota}%`} />
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-[0.25em] text-muted mb-2 flex items-center gap-2"><span className="rule-accent" />Memória de cálculo</div>
            <ol className="space-y-1 font-mono text-[12px] text-text/90 border-l border-border pl-4">
              {item.memoriaCalculo.map((linha, i) => (<li key={i} className="flex gap-3"><span className="text-muted select-none tabular-nums">{String(i + 1).padStart(2, "0")}</span><span>{linha}</span></li>))}
            </ol>
          </div>
        </div>
      )}
    </div>
  );
}

function Features() {
  const items = [
    { k: "01", title: "Decimal, nunca float", body: "Todos os cálculos monetários usam Decimal com ROUND_HALF_UP a 2 casas. Zero arredondamento binário silencioso." },
    { k: "02", title: "Base por fora", body: 'IBS e CBS incidem sobre uma base que não inclui os próprios tributos nem um ao outro — diferente do "por dentro" do ICMS.' },
    { k: "03", title: "IS compõe a base", body: "Quando há Imposto Seletivo, ele é apurado antes e entra na base de IBS/CBS. O motor faz isso sem exceções." },
    { k: "04", title: "Regra é dado, não código", body: "Rulesets versionados com hash SHA-256 e vigência. A dataOperacao resolve a regra — nunca o dia em que foi processada." },
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

function RulesetsPanel({ rulesets, current }) {
  return (
    <div className="border border-border rounded-md bg-surface overflow-hidden" data-testid="rulesets-panel">
      <div className="px-4 py-3 border-b border-border flex items-center gap-2"><Layers className="w-3.5 h-3.5 text-muted" />
        <span className="text-[10px] uppercase tracking-[0.25em] font-medium text-muted">Rulesets versionados</span></div>
      <div className="divide-y divide-border">
        {rulesets.length === 0 && <div className="p-4 text-sm text-muted">Carregando…</div>}
        {rulesets.map((r) => {
          const active = current === r.id;
          return (
            <div key={r.id} className={`p-4 transition-colors ${active ? "bg-accentDim" : ""}`}>
              <div className="flex items-center justify-between gap-2 mb-1.5">
                <span className="font-mono text-xs text-strong">{r.id}</span>
                {active && <span className="text-[9px] font-mono uppercase tracking-[0.25em] text-accent flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-accent" />vigente</span>}
              </div>
              <div className="text-[13px] text-muted mb-2">{r.descricao}</div>
              <div className="flex flex-wrap gap-x-4 gap-y-1 text-[10.5px] font-mono text-muted">
                <span>{r.vigenciaInicio} → {r.vigenciaFim || "∞"}</span>
                <span>CBS <span className="text-strong">{r.cbs.aliquotaNominal}%</span></span>
                <span>UF <span className="text-strong">{r.ibs.aliquotaUF}%</span></span>
                <span>Mun <span className="text-strong">{r.ibs.aliquotaMunicipio}%</span></span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function PlaygroundPage() {
  const [dataOperacao, setDataOperacao] = useState(GOLDEN_REQUEST.dataOperacao);
  const [itens, setItens] = useState(GOLDEN_REQUEST.itens);
  const [rulesets, setRulesets] = useState([]);
  const [response, setResponse] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [viewMode, setViewMode] = useState("visual");
  const [sapOpen, setSapOpen] = useState(false);
  const [sapLoading, setSapLoading] = useState(false);
  const [sapResp, setSapResp] = useState(null);
  const [sapErr, setSapErr] = useState(null);

  useEffect(() => {
    api.get("/v1/rulesets").then((r) => {
      const map = new Map();
      for (const rs of r.data.rulesets) map.set(rs.id, rs);
      setRulesets(Array.from(map.values()));
    }).catch(() => setRulesets([]));
  }, []);

  const buildPayload = () => ({ ...GOLDEN_REQUEST, dataOperacao, itens });
  const payload = useMemo(() => buildPayload(), [dataOperacao, itens]); // eslint-disable-line

  const calcular = async () => {
    setLoading(true); setError(null); setResponse(null);
    try {
      const { data } = await api.post("/v1/calcular", buildPayload());
      setResponse(data);
    } catch (e) {
      setError({ erro: formatApiError(e) });
    } finally { setLoading(false); }
  };

  const resetGolden = () => { setDataOperacao(GOLDEN_REQUEST.dataOperacao); setItens(GOLDEN_REQUEST.itens); setResponse(null); setError(null); };

  const simularSap = async () => {
    setSapLoading(true); setSapErr(null); setSapResp(null); setSapOpen(true);
    try {
      // pega o payload KOMV exemplo pré-montado e substitui pelos itens atuais do playground
      const { data: exemplo } = await api.get("/v1/sap/exemplo");
      exemplo.dataOperacao = dataOperacao;
      exemplo.itens = itens.map((it, idx) => ({
        kposn: (idx + 1) * 10,
        matnr: `MAT-${String(idx + 1).padStart(3, "0")}`,
        arktx: it.descricao || `Item ${idx + 1}`,
        ncm: it.ncm || "",
        cClassTrib: it.cClassTrib,
        menge: it.quantidade,
        meins: "PC",
        kbetr: it.valorUnitario,
        kwert: it.valorItem,
        ...(it.impostoSeletivo ? { impostoSeletivo: it.impostoSeletivo } : {}),
      }));
      const { data } = await api.post("/v1/sap/pricing", exemplo);
      setSapResp(data);
    } catch (e) {
      setSapErr(formatApiError(e));
    } finally { setSapLoading(false); }
  };

  return (
    <div className="grain">
      <section className="relative hero-glow max-w-[1400px] mx-auto px-6 pt-16 pb-14">
        <div className="relative z-10 max-w-4xl">
          <div className="flex items-center gap-2 mb-6"><span className="rule-accent" />
            <span className="text-[11px] font-mono uppercase tracking-[0.35em] text-accent">POST /api/v1/calcular</span></div>
          <h1 className="font-heading font-medium text-[46px] md:text-[60px] leading-[1.02] tracking-tightest text-strong">
            O cálculo de <span className="text-accent">IBS &amp; CBS</span> que uma <span className="serif-italic">fiscalização</span> aceita.
          </h1>
          <div className="mt-7 space-y-3 max-w-2xl">
            <p className="text-[16px] leading-[1.65] text-text">
              Uma nota emitida em julho é calculada com a <span className="text-strong">regra de julho</span> — hoje, amanhã ou numa fiscalização daqui a cinco anos. Rulesets são dado versionado, resolvidos pela <span className="font-mono text-strong">dataOperacao</span>.
            </p>
            <p className="text-[14.5px] leading-[1.65] text-muted">
              Base <span className="dot-underline text-text">por fora</span>. Imposto Seletivo compondo a base correta. Memória de cálculo linha a linha, hash do ruleset e <span className="text-text">trilha de auditoria imutável</span> em cada resposta.
            </p>
          </div>
        </div>
      </section>

      <Features />

      <section className="max-w-[1400px] mx-auto px-6 py-16 relative">
        <div className="flex items-baseline justify-between mb-8">
          <div>
            <div className="text-[11px] font-mono uppercase tracking-[0.3em] text-muted mb-2">Playground</div>
            <h2 className="font-heading text-3xl md:text-4xl tracking-tight text-strong">Os três <span className="serif-italic text-accent">casos-ouro</span>, ao vivo.</h2>
          </div>
        </div>

        <div className="grid grid-cols-12 gap-6">
          <div className="col-span-12 lg:col-span-5 space-y-4">
            <div className="flex items-center justify-between"><div className="text-[10px] uppercase tracking-[0.3em] text-muted">Configuração</div>
              <button onClick={resetGolden} className="text-[11px] font-mono text-muted hover:text-accent flex items-center gap-1.5" data-testid="reset-golden"><RefreshCw className="w-3 h-3" />golden default</button></div>
            <div className="border border-border rounded-md p-4 bg-surface">
              <label className="block"><span className="text-[10px] uppercase tracking-[0.25em] text-muted">dataOperacao (resolve o ruleset)</span>
                <input data-testid="data-operacao-input" type="date" value={dataOperacao} onChange={(e) => setDataOperacao(e.target.value)}
                  className="mt-1.5 w-full bg-bg border border-border rounded-md px-3 py-2 text-sm font-mono focus:border-accent focus:outline-none" /></label>
            </div>
            <RulesetsPanel rulesets={rulesets} current={response?.rulesetId} />
            <div className="space-y-3">
              {itens.map((it, idx) => (
                <ItemEditor key={idx} idx={idx} item={it}
                  onChange={(n) => { const cp = [...itens]; cp[idx] = n; setItens(cp); }}
                  onRemove={() => { const cp = itens.filter((_, i) => i !== idx); setItens(cp.map((x, i) => ({ ...x, numero: i + 1 }))); }} />
              ))}
              <button onClick={() => setItens([...itens, { numero: itens.length + 1, descricao: "Novo item", cClassTrib: "000001", quantidade: "1.00", valorUnitario: "100.00", valorItem: "100.00" }])}
                className="w-full border border-dashed border-border rounded-md py-3 text-[11px] uppercase tracking-[0.25em] text-muted hover:border-accent hover:text-accent"
                data-testid="add-item">+ adicionar item</button>
            </div>
            <button onClick={calcular} disabled={loading} data-testid="calcular-btn"
              className="w-full mt-2 bg-accent text-bg font-semibold rounded-md py-4 flex items-center justify-center gap-2 hover:bg-accentHover hover:-translate-y-0.5 transition-transform duration-150 disabled:opacity-60 disabled:hover:translate-y-0">
              <Play className="w-4 h-4" strokeWidth={2.5} />{loading ? "Calculando…" : "Calcular"}
            </button>
            <button onClick={simularSap} disabled={sapLoading} data-testid="sap-simular-btn"
              className="w-full border border-accent/40 text-accent bg-transparent hover:bg-accentDim rounded-md py-3 flex items-center justify-center gap-2 transition-colors font-mono text-[12px] uppercase tracking-[0.22em] disabled:opacity-60">
              <Server className="w-3.5 h-3.5" />{sapLoading ? "chamando S/4HANA…" : "simular chamada S/4HANA"}
            </button>
          </div>

          <div className="col-span-12 lg:col-span-7">
            <div className="flex items-center justify-between mb-3">
              <div className="text-[10px] uppercase tracking-[0.3em] text-muted">{response ? "Resposta" : "Preview do request"}</div>
              <div className="flex items-center gap-1 border border-border rounded-md p-0.5 bg-surface">
                <button onClick={() => setViewMode("visual")} data-testid="view-visual"
                  className={`text-[10px] font-mono uppercase tracking-[0.2em] px-2.5 py-1 rounded transition-colors ${viewMode === "visual" ? "bg-accent text-bg" : "text-muted hover:text-strong"}`}>visual</button>
                <button onClick={() => setViewMode("json")} data-testid="view-json"
                  className={`text-[10px] font-mono uppercase tracking-[0.2em] px-2.5 py-1 rounded transition-colors ${viewMode === "json" ? "bg-accent text-bg" : "text-muted hover:text-strong"}`}>json</button>
              </div>
            </div>
            <div className="border border-border rounded-md bg-codeBg min-h-[560px] p-5 relative overflow-auto" data-testid="response-viewer"
              style={{ boxShadow: "inset 0 1px 0 var(--code-shadow)" }}>
              {!response && !error && !loading && (<div><div className="text-[10px] uppercase tracking-[0.25em] text-muted mb-3 flex items-center gap-2"><span className="rule-accent" />request</div><JsonView data={payload} /></div>)}
              {loading && (<div className="flex items-center gap-2 text-muted font-mono text-sm cursor"><span>› resolvendo ruleset e calculando</span></div>)}
              {error && (<div className="reveal"><div className="text-error font-mono text-[10px] uppercase tracking-[0.3em] mb-3">⨯ erro</div><JsonView data={error} /></div>)}
              {response && viewMode === "json" && (<div className="reveal"><JsonView data={response} /></div>)}
              {response && viewMode === "visual" && (<div className="reveal space-y-5">
                <div className="border-b border-border pb-4 space-y-3">
                  <div><div className="flex items-center justify-between mb-1"><span className="text-[10px] uppercase tracking-[0.25em] text-muted flex items-center gap-1.5"><Layers className="w-3 h-3" />rulesetId</span><CopyBtn text={response.rulesetId} /></div><div className="font-mono text-[13px] text-accent break-all">{response.rulesetId}</div></div>
                  <div><div className="flex items-center justify-between mb-1"><span className="text-[10px] uppercase tracking-[0.25em] text-muted flex items-center gap-1.5"><Hash className="w-3 h-3" />rulesetHash</span><CopyBtn text={response.rulesetHash} /></div><div className="font-mono text-[11.5px] text-muted break-all">{response.rulesetHash}</div></div>
                  <div className="grid grid-cols-2 gap-3 pt-2"><div><div className="text-[10px] uppercase tracking-[0.25em] text-muted mb-1">motorVersao</div><div className="font-mono text-[12px] text-strong">{response.motorVersao}</div></div><div><div className="text-[10px] uppercase tracking-[0.25em] text-muted mb-1">calculadoEm</div><div className="font-mono text-[12px] text-strong">{response.calculadoEm}</div></div></div>
                  <div><div className="flex items-center justify-between mb-1"><span className="text-[10px] uppercase tracking-[0.25em] text-muted flex items-center gap-1.5"><Fingerprint className="w-3 h-3" />auditoriaId</span><CopyBtn text={response.auditoriaId} /></div><div className="font-mono text-[12px] flex items-center gap-2"><FileText className="w-3 h-3 text-muted" /><span className="text-text">{response.auditoriaId}</span></div></div>
                </div>
                <div className="space-y-3">{response.itens.map((it, i) => (<ItemResult key={i} item={it} idx={i} />))}</div>
                <div className="border border-accent/40 rounded-md bg-gradient-to-br from-accentDim to-transparent p-5" data-testid="totais">
                  <div className="text-[10px] uppercase tracking-[0.3em] text-accent mb-4 flex items-center gap-2"><span className="rule-accent" />Totais consolidados</div>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
                    <Metric label="Base total" value={`R$ ${response.totais.baseTotal}`} />
                    <Metric label="CBS" value={`R$ ${response.totais.cbs}`} />
                    <Metric label="IBS-UF" value={`R$ ${response.totais.ibsUF}`} />
                    <Metric label="IBS-Mun" value={`R$ ${response.totais.ibsMunicipio}`} />
                    <Metric label="IBS total" value={`R$ ${response.totais.ibs}`} />
                    <Metric label="Imp. Seletivo" value={`R$ ${response.totais.impostoSeletivo}`} />
                  </div>
                  <div className="border border-accent bg-bg rounded-md p-4">
                    <div className="text-[10px] uppercase tracking-[0.3em] text-accent mb-2">Tributos totais (CBS + IBS)</div>
                    <div className="big-num text-3xl text-strong">R$ {response.totais.tributosTotais}</div>
                  </div>
                </div>
              </div>)}
            </div>
          </div>
        </div>
      </section>

      {sapOpen && (
        <div className="fixed inset-0 z-50 bg-bg/80 backdrop-blur-sm flex items-center justify-center p-6" data-testid="sap-modal">
          <div className="relative w-full max-w-5xl max-h-[85vh] overflow-auto border border-border rounded-lg bg-surface shadow-2xl">
            <div className="sticky top-0 z-10 border-b border-border bg-surface/95 backdrop-blur px-6 py-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Server className="w-4 h-4 text-accent" />
                <div>
                  <div className="font-heading text-lg text-strong">POST /api/v1/sap/pricing</div>
                  <div className="text-[10px] font-mono uppercase tracking-[0.25em] text-muted">SAP S/4HANA · pricing schema ZFISC01 · KOMV in/out</div>
                </div>
              </div>
              <button onClick={() => setSapOpen(false)} data-testid="sap-modal-close" className="text-muted hover:text-strong">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-5">
              {sapLoading && (
                <div className="font-mono text-sm text-muted cursor">› chamando motor externo, montando condition types…</div>
              )}
              {sapErr && (
                <div className="border border-error/30 bg-error/5 rounded-md p-4 text-error font-mono text-[12px]">⨯ {sapErr}</div>
              )}
              {sapResp && (
                <>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    <Metric label="VBELN (documento)" value={sapResp.vbeln} />
                    <Metric label="Ruleset" value={sapResp.rulesetId} />
                    <Metric label="Schema pricing" value={sapResp.schemaPricing} />
                    <Metric label="Moeda (WAERK)" value={sapResp.waerk} />
                  </div>

                  <div className="border border-accent/40 bg-gradient-to-br from-accentDim to-transparent rounded-md p-5">
                    <div className="text-[10px] uppercase tracking-[0.3em] text-accent mb-3 flex items-center gap-2"><span className="rule-accent" />Totais do documento</div>
                    <div className="grid grid-cols-3 gap-4">
                      <div>
                        <div className="text-[10px] uppercase tracking-[0.25em] text-muted mb-1">Net (base)</div>
                        <div className="big-num text-xl text-strong">R$ {sapResp.totals.netVal}</div>
                      </div>
                      <div>
                        <div className="text-[10px] uppercase tracking-[0.25em] text-muted mb-1">Tributos</div>
                        <div className="big-num text-xl text-accent">R$ {sapResp.totals.taxAmount}</div>
                      </div>
                      <div>
                        <div className="text-[10px] uppercase tracking-[0.25em] text-muted mb-1">Gross (documento)</div>
                        <div className="big-num text-xl text-strong">R$ {sapResp.totals.grossVal}</div>
                      </div>
                    </div>
                  </div>

                  <div>
                    <div className="text-[10px] uppercase tracking-[0.25em] text-muted mb-3 flex items-center gap-2"><span className="rule-accent" />Tabela KOMV devolvida</div>
                    <div className="border border-border rounded-md overflow-hidden">
                      <table className="w-full font-mono text-[12px]" data-testid="sap-komv-table">
                        <thead className="bg-elev text-muted uppercase tracking-[0.18em] text-[10px]">
                          <tr>
                            <th className="text-left px-3 py-2">KPOSN</th>
                            <th className="text-left px-3 py-2">STUNR</th>
                            <th className="text-left px-3 py-2">KSCHL</th>
                            <th className="text-left px-3 py-2">Descrição</th>
                            <th className="text-right px-3 py-2">KBETR (%)</th>
                            <th className="text-right px-3 py-2">KAWRT</th>
                            <th className="text-right px-3 py-2">KWERT</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-border">
                          {sapResp.conditions.map((c, i) => (
                            <tr key={i} className="hover:bg-elev/40" data-testid={`sap-row-${c.kposn}-${c.kschl}`}>
                              <td className="px-3 py-2 tabular-nums">{c.kposn}</td>
                              <td className="px-3 py-2 tabular-nums text-muted">{c.stunr}</td>
                              <td className="px-3 py-2 text-accent">{c.kschl}</td>
                              <td className="px-3 py-2 text-text/80">{c.vtext}</td>
                              <td className="px-3 py-2 text-right tabular-nums">{c.kbetr}</td>
                              <td className="px-3 py-2 text-right tabular-nums">{c.kawrt}</td>
                              <td className="px-3 py-2 text-right tabular-nums text-strong">{c.kwert}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    <div className="mt-2 text-[10.5px] font-mono text-muted">
                      Motor externo autoritativo. Zero ABAP crítico. Cada linha grava evento <span className="text-strong">sap.pricing</span> no ledger.
                    </div>
                  </div>

                  <div className="flex items-center justify-between pt-2">
                    <div className="text-[10px] font-mono uppercase tracking-[0.25em] text-muted flex items-center gap-2">
                      <Hash className="w-3 h-3" />
                      <span className="normal-case tracking-normal text-text/70">{sapResp.rulesetHash}</span>
                    </div>
                    <CopyBtn text={JSON.stringify(sapResp, null, 2)} testid="sap-copy-json" />
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
