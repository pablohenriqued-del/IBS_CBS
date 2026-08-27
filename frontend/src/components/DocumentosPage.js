import React, { useEffect, useRef, useState } from "react";
import { Upload, FileCheck, AlertCircle, ArrowDownToLine, ArrowUpFromLine, RefreshCw, Sparkles, Download, X } from "lucide-react";
import { api, formatApiError } from "../api";
import { useAuth, roleAllowed } from "../AuthContext";

export function DocumentosPage() {
  const { user } = useAuth();
  const [docs, setDocs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [direcao, setDirecao] = useState("saida");
  const [filter, setFilter] = useState("todos");
  const [message, setMessage] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [samples, setSamples] = useState([]);
  const [samplesLoading, setSamplesLoading] = useState({});
  const [queue, setQueue] = useState([]); // {name, size, status: 'pending'|'uploading'|'success'|'error', message?}
  const fileRef = useRef(null);

  const canUpload = roleAllowed(user, ["fiscal", "admin"]);

  const reload = async () => {
    setLoading(true);
    try {
      const params = filter !== "todos" ? { direcao: filter } : {};
      const { data } = await api.get("/v1/documentos", { params });
      setDocs(data.documentos);
    } catch (e) {
      setMessage({ type: "error", text: formatApiError(e) });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { reload(); /* eslint-disable-next-line */ }, [filter]);
  useEffect(() => {
    api.get("/v1/samples").then((r) => setSamples(r.data.amostras)).catch(() => setSamples([]));
  }, []);

  // Faz upload de UM arquivo. Retorna {ok, message}
  const uploadOne = async (file, dir, extra = {}) => {
    const fd = new FormData();
    fd.append("arquivo", file);
    fd.append("direcao", dir || direcao);
    if (extra.origem) fd.append("origem", extra.origem);
    try {
      const { data } = await api.post("/v1/documentos/importar", fd);
      return {
        ok: true,
        message: `CBS R$ ${data.totais.cbs} · IBS R$ ${data.totais.ibs}`,
      };
    } catch (e) {
      return { ok: false, message: formatApiError(e) };
    }
  };

  // Bulk upload — processa a fila sequencialmente com progresso por arquivo
  const uploadMany = async (files, dir) => {
    const items = files.map((f) => ({
      name: f.name,
      size: f.size,
      status: "pending",
      _file: f,
    }));
    setQueue(items);
    setUploading(true);
    setMessage(null);

    let ok = 0, err = 0;
    for (let i = 0; i < items.length; i++) {
      setQueue((q) => q.map((it, j) => (j === i ? { ...it, status: "uploading" } : it)));
      const res = await uploadOne(items[i]._file, dir);
      setQueue((q) =>
        q.map((it, j) =>
          j === i
            ? { ...it, status: res.ok ? "success" : "error", message: res.message, _file: undefined }
            : it
        )
      );
      if (res.ok) ok++; else err++;
    }
    setUploading(false);
    setMessage({
      type: err === 0 ? "success" : "error",
      text: `${ok}/${items.length} importadas${err ? ` · ${err} com erro` : ""}`,
    });
    reload();
    if (fileRef.current) fileRef.current.value = "";
  };

  const upload = async (fileOrList, dir) => {
    if (!fileOrList) return;
    const files = Array.isArray(fileOrList) ? fileOrList : Array.from(fileOrList.length !== undefined ? fileOrList : [fileOrList]);
    if (files.length === 0) return;
    if (files.length === 1) {
      // Fluxo simples para 1 arquivo (mantém mensagem inline)
      setUploading(true);
      const res = await uploadOne(files[0], dir);
      setUploading(false);
      setMessage({
        type: res.ok ? "success" : "error",
        text: res.ok ? `✓ ${files[0].name} · ${res.message}` : res.message,
      });
      reload();
      if (fileRef.current) fileRef.current.value = "";
    } else {
      await uploadMany(files, dir);
    }
  };

  const importarAmostra = async (sample) => {
    setSamplesLoading((s) => ({ ...s, [sample.arquivo]: true }));
    setMessage(null);
    try {
      const { data: blob } = await api.get(`/v1/samples/${sample.arquivo}`, { responseType: "blob" });
      const file = new File([blob], sample.arquivo, { type: "application/xml" });
      // Chama uploadOne diretamente com origem=sample:{nome} para o ledger
      setUploading(true);
      const res = await uploadOne(file, sample.direcao, { origem: `sample:${sample.arquivo}` });
      setUploading(false);
      setMessage({
        type: res.ok ? "success" : "error",
        text: res.ok ? `✓ Amostra ${sample.arquivo} · ${res.message}` : res.message,
      });
      reload();
    } finally {
      setSamplesLoading((s) => ({ ...s, [sample.arquivo]: false }));
    }
  };

  const baixarAmostra = (nome) => {
    api.get(`/v1/samples/${nome}`, { responseType: "blob" }).then((res) => {
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = nome;
      a.click();
      URL.revokeObjectURL(url);
    });
  };

  const onDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const files = Array.from(e.dataTransfer.files || []);
    if (files.length) upload(files);
  };

  const onFileChange = (e) => {
    const files = Array.from(e.target.files || []);
    if (files.length) upload(files);
  };

  return (
    <div className="max-w-[1400px] mx-auto px-6 py-12">
      <div className="mb-8">
        <div className="text-[11px] font-mono uppercase tracking-[0.3em] text-muted mb-2">
          POST /api/v1/documentos/importar
        </div>
        <h1 className="font-heading text-4xl tracking-tight text-strong mb-2">
          Ingestão de <span className="serif-italic text-accent">NF-e</span>.
        </h1>
        <p className="text-muted max-w-2xl">
          Envie um XML de NF-e. O parser extrai chave de acesso, itens e grupo IBS/CBS;
          o motor resolve o ruleset pela <span className="font-mono text-text">dataEmissao</span> e
          persiste com idempotência por chave.
        </p>
      </div>

      {canUpload && (
        <div className="grid grid-cols-12 gap-6 mb-8">
          <div className="col-span-12 lg:col-span-8">
            <div
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={onDrop}
              onClick={() => fileRef.current?.click()}
              data-testid="dropzone"
              className={`border-2 border-dashed rounded-md p-10 cursor-pointer text-center transition-colors ${
                dragOver ? "border-accent bg-accentDim" : "border-border hover:border-accent/60 bg-surface"
              }`}
            >
              <Upload className="w-8 h-8 mx-auto mb-3 text-accent" strokeWidth={1.5} />
              <div className="font-heading text-lg text-strong mb-1">
                Arraste XMLs aqui, ou clique para selecionar
              </div>
              <div className="text-[12.5px] text-muted">
                Aceita <span className="font-mono text-text">nfeProc</span> ou{" "}
                <span className="font-mono text-text">NFe</span> — até 5 MB por arquivo · múltiplos ao mesmo tempo
              </div>
              <input
                ref={fileRef}
                type="file"
                accept=".xml,application/xml,text/xml"
                multiple
                onChange={onFileChange}
                className="hidden"
                data-testid="file-input"
              />
              {uploading && queue.length === 0 && (
                <div className="mt-4 text-[12px] font-mono text-muted cursor">› enviando</div>
              )}
            </div>

            {/* Fila de bulk upload */}
            {queue.length > 0 && (
              <div className="mt-4 border border-border rounded-md bg-surface overflow-hidden" data-testid="upload-queue">
                <div className="px-4 py-2.5 border-b border-border flex items-center justify-between">
                  <div className="text-[10px] uppercase tracking-[0.25em] text-muted">
                    Fila · {queue.filter((q) => q.status === "success").length}/{queue.length} concluídas
                  </div>
                  {!uploading && (
                    <button
                      onClick={() => setQueue([])}
                      className="text-[11px] font-mono text-muted hover:text-error flex items-center gap-1"
                      data-testid="clear-queue"
                    >
                      <X className="w-3 h-3" /> limpar
                    </button>
                  )}
                </div>
                {/* Progress bar geral */}
                <div className="h-1 bg-bg relative">
                  <div
                    className="h-full bg-accent transition-all duration-300"
                    style={{
                      width: `${(queue.filter((q) => q.status !== "pending" && q.status !== "uploading").length / queue.length) * 100}%`,
                    }}
                  />
                </div>
                {/* Items */}
                <div className="max-h-64 overflow-auto">
                  {queue.map((q, i) => (
                    <div
                      key={i}
                      data-testid={`queue-item-${i}`}
                      className={`px-4 py-2 border-b border-border/50 flex items-center gap-3 text-[12px] ${
                        q.status === "uploading" ? "bg-accentDim" : ""
                      }`}
                    >
                      <span className="font-mono text-muted w-6 tabular-nums">
                        {String(i + 1).padStart(2, "0")}
                      </span>
                      <span className="font-mono text-strong flex-1 truncate">{q.name}</span>
                      <span className="font-mono text-[10.5px] text-muted">
                        {(q.size / 1024).toFixed(1)} KB
                      </span>
                      {q.status === "pending" && (
                        <span className="text-[10px] font-mono uppercase tracking-widest text-muted">aguardando</span>
                      )}
                      {q.status === "uploading" && (
                        <span className="text-[10px] font-mono uppercase tracking-widest text-accent cursor">enviando</span>
                      )}
                      {q.status === "success" && (
                        <span className="text-[10.5px] font-mono text-success flex items-center gap-1">
                          <FileCheck className="w-3 h-3" /> {q.message}
                        </span>
                      )}
                      {q.status === "error" && (
                        <span className="text-[10.5px] font-mono text-error flex items-center gap-1 truncate max-w-xs" title={q.message}>
                          <AlertCircle className="w-3 h-3 flex-shrink-0" /> {q.message}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="col-span-12 lg:col-span-4">
            <div className="border border-border rounded-md p-4 bg-surface">
              <div className="text-[10px] uppercase tracking-[0.25em] text-muted mb-3">
                Direção da operação
              </div>
              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={() => setDirecao("saida")}
                  data-testid="direcao-saida"
                  className={`flex items-center justify-center gap-1.5 rounded-md py-2.5 text-[12px] font-medium transition-colors ${
                    direcao === "saida"
                      ? "bg-accent text-bg"
                      : "bg-elev text-muted hover:text-strong border border-border"
                  }`}
                >
                  <ArrowUpFromLine className="w-3.5 h-3.5" />
                  Saída (débito)
                </button>
                <button
                  onClick={() => setDirecao("entrada")}
                  data-testid="direcao-entrada"
                  className={`flex items-center justify-center gap-1.5 rounded-md py-2.5 text-[12px] font-medium transition-colors ${
                    direcao === "entrada"
                      ? "bg-accent text-bg"
                      : "bg-elev text-muted hover:text-strong border border-border"
                  }`}
                >
                  <ArrowDownToLine className="w-3.5 h-3.5" />
                  Entrada (crédito)
                </button>
              </div>
              <div className="mt-3 text-[11px] text-muted leading-relaxed">
                Saída gera <span className="text-accent">débito</span>. Entrada gera{" "}
                <span className="text-accent">crédito</span>. A apuração compensa.
              </div>
            </div>
          </div>
        </div>
      )}

      {message && (
        <div
          data-testid="upload-msg"
          className={`mb-6 rounded-md px-4 py-3 text-[13px] font-mono flex items-start gap-2 ${
            message.type === "success"
              ? "border border-accent/30 bg-accentDim text-strong"
              : "border border-error/30 bg-error/5 text-error"
          }`}
        >
          {message.type === "success" ? (
            <FileCheck className="w-4 h-4 flex-shrink-0 mt-0.5" />
          ) : (
            <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
          )}
          {message.text}
        </div>
      )}

      {/* Amostras */}
      {samples.length > 0 && (
        <div className="mb-8" data-testid="samples-panel">
          <div className="flex items-baseline justify-between mb-3">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-accent" />
              <h3 className="font-heading text-lg text-strong">
                Amostras para <span className="serif-italic text-accent">testar</span>
              </h3>
            </div>
            <span className="text-[11px] font-mono text-muted">
              {samples.length} XMLs · clique para importar, ou baixe
            </span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {samples.map((s) => (
              <div
                key={s.arquivo}
                data-testid={`sample-${s.arquivo}`}
                className="border border-border rounded-md bg-surface p-3.5 hover:border-accent/60 transition-colors group"
              >
                <div className="flex items-center gap-2 mb-1.5">
                  <span
                    className={`text-[9px] font-mono uppercase tracking-[0.2em] border rounded px-1.5 py-0.5 ${
                      s.direcao === "saida"
                        ? "text-accent border-accent/40"
                        : "text-success border-success/40"
                    }`}
                  >
                    {s.direcao}
                  </span>
                  <span className="text-[9px] font-mono uppercase tracking-[0.2em] text-muted">
                    {s.ruleset}
                  </span>
                  <span className="ml-auto text-[10px] font-mono text-muted">
                    {s.dataOperacao}
                  </span>
                </div>
                <div className="font-heading text-sm text-strong mb-1 leading-tight">
                  {s.titulo}
                </div>
                <div className="text-[11.5px] text-muted mb-3 leading-relaxed">
                  {s.resumo}
                </div>
                <div className="flex items-center gap-2">
                  {canUpload && (
                    <button
                      onClick={() => importarAmostra(s)}
                      disabled={samplesLoading[s.arquivo] || uploading}
                      data-testid={`sample-import-${s.arquivo}`}
                      className="flex-1 text-[11px] font-medium bg-accent text-bg rounded-md py-1.5 hover:bg-accentHover flex items-center justify-center gap-1.5 disabled:opacity-60"
                    >
                      <Upload className="w-3 h-3" strokeWidth={2.5} />
                      {samplesLoading[s.arquivo] ? "…" : "importar"}
                    </button>
                  )}
                  <button
                    onClick={() => baixarAmostra(s.arquivo)}
                    data-testid={`sample-download-${s.arquivo}`}
                    title="Baixar XML"
                    className="text-[11px] font-mono text-muted hover:text-accent border border-border rounded-md p-1.5 hover:border-accent transition-colors"
                  >
                    <Download className="w-3 h-3" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="flex items-baseline justify-between mb-4">
        <h2 className="font-heading text-2xl text-strong">Documentos</h2>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1 border border-border rounded-md p-0.5 bg-surface">
            {["todos", "saida", "entrada"].map((v) => (
              <button
                key={v}
                data-testid={`filter-${v}`}
                onClick={() => setFilter(v)}
                className={`text-[10px] font-mono uppercase tracking-[0.2em] px-2.5 py-1 rounded transition-colors ${
                  filter === v ? "bg-accent text-bg" : "text-muted hover:text-strong"
                }`}
              >
                {v}
              </button>
            ))}
          </div>
          <button
            onClick={reload}
            className="text-[11px] font-mono text-muted hover:text-strong flex items-center gap-1"
            data-testid="reload-docs"
          >
            <RefreshCw className={`w-3 h-3 ${loading ? "animate-spin" : ""}`} /> recarregar
          </button>
        </div>
      </div>

      <div className="border border-border rounded-md overflow-hidden bg-surface" data-testid="docs-table">
        <div className="grid grid-cols-12 gap-3 px-4 py-2.5 border-b border-border text-[10px] uppercase tracking-[0.25em] text-muted">
          <div className="col-span-1">dir</div>
          <div className="col-span-3">chave (…último 8)</div>
          <div className="col-span-2">data op.</div>
          <div className="col-span-2">emitente</div>
          <div className="col-span-2 text-right font-mono">cbs</div>
          <div className="col-span-1 text-right font-mono">ibs</div>
          <div className="col-span-1 text-right font-mono">total</div>
        </div>
        {docs.length === 0 && !loading && (
          <div className="p-10 text-center text-muted text-sm">
            nenhum documento — importe uma NF-e acima
          </div>
        )}
        {docs.map((d) => (
          <div
            key={d.id}
            className="grid grid-cols-12 gap-3 px-4 py-2.5 border-b border-border/50 hover:bg-elev/50 text-[12px] items-center"
            data-testid={`doc-${d.chaveAcesso.slice(-8)}`}
          >
            <div className="col-span-1">
              {d.direcao === "saida" ? (
                <span className="text-[9px] font-mono uppercase tracking-[0.2em] text-accent border border-accent/40 rounded px-1.5 py-0.5">
                  saída
                </span>
              ) : (
                <span className="text-[9px] font-mono uppercase tracking-[0.2em] text-success border border-success/40 rounded px-1.5 py-0.5">
                  entrada
                </span>
              )}
            </div>
            <div className="col-span-3 font-mono text-[11px] text-strong">
              …{d.chaveAcesso.slice(-16)}
            </div>
            <div className="col-span-2 font-mono text-[11.5px] text-muted">{d.dataOperacao}</div>
            <div className="col-span-2 truncate text-[11.5px] text-muted">
              {d.emitente?.xNome || d.emitente?.cnpj || "—"}
            </div>
            <div className="col-span-2 text-right font-mono text-[11.5px] text-strong">
              {d.totais?.cbs}
            </div>
            <div className="col-span-1 text-right font-mono text-[11.5px] text-strong">
              {d.totais?.ibs}
            </div>
            <div className="col-span-1 text-right font-mono text-[12px] text-accent">
              {d.totais?.tributosTotais}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
