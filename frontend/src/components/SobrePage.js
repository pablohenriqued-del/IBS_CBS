import React, { useState } from "react";
import { Link } from "react-router-dom";
import { Linkedin, ExternalLink, Sparkles, ShieldCheck, Database, GitBranch, Zap, TrendingUp, Layers, Mail, Send, CheckCircle2 } from "lucide-react";
import { api, formatApiError } from "../api";
import { Logo } from "./Shared";

const AUTHOR = {
  name: "Pablo Duarte",
  role: "Gerente de Inovação & TI",
  linkedin: "https://www.linkedin.com/in/pablo-henrique-duarte-77415b5/",
  extra: "https://claude.ai/code/artifact/50cfb559-0416-4ccd-8a9c-9c34a4cea2a3?org=4908bbfb-26cc-4793-a98a-f8f7fa52d994",
};

function Section({ eyebrow, title, children }) {
  return (
    <section className="max-w-3xl mx-auto py-14 reveal">
      <div className="text-[11px] font-mono uppercase tracking-[0.3em] text-accent mb-3 flex items-center gap-2">
        <span className="rule-accent" /> {eyebrow}
      </div>
      <h2 className="font-heading text-3xl md:text-4xl tracking-tight text-strong mb-6 leading-tight">
        {title}
      </h2>
      <div className="prose-fc space-y-4 text-[15px] leading-[1.75] text-text">
        {children}
      </div>
    </section>
  );
}

function ContatoForm() {
  const [form, setForm] = useState({ nome: "", email: "", empresa: "", mensagem: "" });
  const [sent, setSent] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const upd = (k, v) => setForm({ ...form, [k]: v });

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true); setError(null);
    try {
      const { data } = await api.post("/public/contato", { ...form, origem: "sobre" });
      setSent(data);
    } catch (err) {
      setError(formatApiError(err));
    } finally { setLoading(false); }
  };

  if (sent) {
    return (
      <section className="max-w-3xl mx-auto py-14 reveal" data-testid="contato-ok">
        <div className="border border-success/40 bg-success/5 rounded-md p-8 flex items-start gap-4">
          <CheckCircle2 className="w-6 h-6 text-success shrink-0 mt-0.5" />
          <div>
            <div className="font-heading text-2xl text-strong mb-2">Recebido.</div>
            <p className="text-[14.5px] text-text leading-relaxed">
              {sent.mensagem} Anotei também no ledger auditável — o mesmo que
              garante integridade dos cálculos. Referência interna:{" "}
              <span className="font-mono text-[11px] text-muted">{sent.id}</span>
            </p>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="max-w-3xl mx-auto py-14 reveal" data-testid="contato-form-section">
      <div className="text-[11px] font-mono uppercase tracking-[0.3em] text-accent mb-3 flex items-center gap-2">
        <span className="rule-accent" /> Conversar direto
      </div>
      <h2 className="font-heading text-3xl md:text-4xl tracking-tight text-strong mb-4 leading-tight">
        Curto conversas <span className="serif-italic text-accent">assíncronas</span>. Sem LinkedIn DM.
      </h2>
      <p className="text-[14.5px] text-muted leading-relaxed mb-8">
        Se você é CFO, CIO, líder fiscal ou arquiteto pensando essa transição
        seriamente, escreva aqui. Respondo por e-mail em até 48h.
      </p>

      <form onSubmit={submit} className="space-y-4" data-testid="contato-form">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <label>
            <span className="text-[10px] uppercase tracking-[0.22em] text-muted">Seu nome</span>
            <input
              type="text" required minLength={2} maxLength={120}
              value={form.nome} onChange={(e) => upd("nome", e.target.value)}
              data-testid="contato-nome"
              className="mt-1 w-full bg-bg border border-border rounded-md px-3 py-2.5 text-sm focus:border-accent focus:outline-none"
            />
          </label>
          <label>
            <span className="text-[10px] uppercase tracking-[0.22em] text-muted">E-mail</span>
            <input
              type="email" required
              value={form.email} onChange={(e) => upd("email", e.target.value)}
              data-testid="contato-email"
              className="mt-1 w-full bg-bg border border-border rounded-md px-3 py-2.5 text-sm font-mono focus:border-accent focus:outline-none"
            />
          </label>
        </div>
        <label className="block">
          <span className="text-[10px] uppercase tracking-[0.22em] text-muted">Empresa (opcional)</span>
          <input
            type="text" maxLength={120}
            value={form.empresa} onChange={(e) => upd("empresa", e.target.value)}
            data-testid="contato-empresa"
            className="mt-1 w-full bg-bg border border-border rounded-md px-3 py-2.5 text-sm focus:border-accent focus:outline-none"
          />
        </label>
        <label className="block">
          <span className="text-[10px] uppercase tracking-[0.22em] text-muted">Contexto e pergunta</span>
          <textarea
            required minLength={4} maxLength={1200} rows={5}
            value={form.mensagem} onChange={(e) => upd("mensagem", e.target.value)}
            data-testid="contato-mensagem"
            placeholder="Ex: estamos rodando S/4HANA, migração planejada para 2027, gostaria de entender como o FiscalCore lida com o TAXBRA na fase de transição..."
            className="mt-1 w-full bg-bg border border-border rounded-md px-3 py-2.5 text-sm leading-relaxed focus:border-accent focus:outline-none resize-y"
          />
        </label>

        {error && (
          <div className="border border-error/30 bg-error/5 rounded-md p-3 text-error font-mono text-[12px]" data-testid="contato-error">
            ⨯ {error}
          </div>
        )}

        <div className="flex items-center justify-between pt-2">
          <div className="text-[10.5px] font-mono text-muted flex items-center gap-2">
            <Mail className="w-3 h-3" />
            registrado no ledger auditável · sem newsletter · sem spam
          </div>
          <button
            type="submit" disabled={loading}
            data-testid="contato-submit"
            className="bg-accent text-bg font-semibold rounded-md px-5 py-2.5 flex items-center gap-2 hover:bg-accentHover transition-colors disabled:opacity-60"
          >
            {loading ? "Enviando…" : (<>
              <Send className="w-3.5 h-3.5" strokeWidth={2.5} /> Enviar
            </>)}
          </button>
        </div>
      </form>
    </section>
  );
}


function Pillar({ icon: Icon, title, body }) {
  return (
    <div className="border border-border rounded-md p-5 bg-surface hover:border-accent/50 transition-colors">
      <Icon className="w-5 h-5 text-accent mb-3" strokeWidth={1.75} />
      <div className="font-heading text-base text-strong mb-2 leading-snug">{title}</div>
      <p className="text-[13px] text-muted leading-relaxed">{body}</p>
    </div>
  );
}

export function SobrePage() {
  return (
    <div className="max-w-[1400px] mx-auto px-6 pb-24">
      {/* Hero */}
      <section className="relative hero-glow py-20 text-center max-w-3xl mx-auto">
        <div className="relative z-10">
          <div className="flex justify-center mb-6">
            <Logo size={56} />
          </div>
          <div className="text-[11px] font-mono uppercase tracking-[0.3em] text-accent mb-4">
            construído por Pablo Duarte · Jan/2026
          </div>
          <h1 className="font-heading text-5xl md:text-6xl tracking-tightest text-strong leading-[0.98] mb-6">
            Um motor fiscal que uma <span className="serif-italic text-accent">fiscalização</span> aceita.
          </h1>
          <p className="text-[17px] leading-[1.65] text-muted">
            Determinístico, auditável, versionado por data. Feito para sobreviver à
            Reforma Tributária de 2026 — e a qualquer auditor que peça a mesma nota
            recalculada daqui a cinco anos.
          </p>
        </div>
      </section>

      {/* Pilares */}
      <section className="max-w-5xl mx-auto py-8">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Pillar icon={ShieldCheck} title="Decimal, nunca float"
            body="Cálculos monetários em Decimal com ROUND_HALF_UP. Zero arredondamento binário silencioso." />
          <Pillar icon={Layers} title="Base 'por fora'"
            body="IBS e CBS incidem sobre base que não inclui os próprios tributos. IS entra na base. Sem exceções." />
          <Pillar icon={GitBranch} title="Regra é dado, não código"
            body="Rulesets versionados com hash SHA-256. dataOperacao resolve a regra — nunca 'a mais recente'." />
          <Pillar icon={Database} title="Ledger imutável"
            body="Cada evento com hash encadeado do anterior. Adulteração é detectada — e localizada." />
        </div>
      </section>

      {/* Story: Como foi feito */}
      <Section eyebrow="Como foi feito" title="Cinco princípios inegociáveis. E um contrato antes do código.">
        <p>
          Escrever um motor fiscal em 2026 não é um exercício de framework —
          é um exercício de <strong>disciplina</strong>. A Reforma Tributária traz
          IBS, CBS e Imposto Seletivo, mas o problema real não são as alíquotas:
          é o fato de que <em>a mesma nota, emitida em julho, tem que ser
          recalculada com a regra de julho</em> — hoje, amanhã, ou numa
          fiscalização daqui a cinco anos.
        </p>
        <p>
          O FiscalCore nasceu de um contrato antes do código: um documento de
          62 linhas descrevendo <span className="font-mono text-strong">POST /v1/calcular</span>{" "}
          com três casos-ouro e resultados esperados até o centavo. Cadeira R$ 1.000
          integral → R$ 265. Medicamento R$ 500 com redução 60% → R$ 53. Bebida R$ 200
          com Imposto Seletivo 10% → R$ 78,30. <strong>Se o motor não bate
          byte-a-byte, o motor está errado.</strong>
        </p>
        <p>
          O <strong>stack</strong> foi escolhido pela precisão que exige: FastAPI +
          Python <span className="font-mono text-strong">Decimal</span>, MongoDB
          append-only para rulesets e auditoria, PostgreSQL na virada de
          produção AWS. React com Fraunces + IBM Plex + JetBrains Mono para uma
          identidade editorial séria — nada de gradiente roxo genérico de SaaS.
        </p>
        <p>
          A camada de <strong>trilha de auditoria</strong> foi implementada como
          um ledger inspirado em blockchain: cada evento (login, importação,
          cálculo, apuração) grava um hash SHA-256 do payload{" "}
          <em>encadeado ao hash do evento anterior</em>. Qualquer adulteração
          quebra a cadeia — e o endpoint{" "}
          <span className="font-mono text-strong">/auditoria/verificar</span>{" "}
          aponta o exato <span className="font-mono">seq</span> onde a integridade
          se rompeu.
        </p>
        <p>
          <strong>64 testes automatizados</strong> validam cada uma dessas
          decisões — os três casos-ouro do contrato, redução de 60% aplicada
          via <span className="font-mono">cClassTrib</span>, Imposto Seletivo
          entrando na base, ruleset resolvido pela{" "}
          <span className="font-mono">dataOperacao</span>, papéis distintos
          (fiscal, auditoria, admin), idempotência por chave de acesso, e a
          detecção de adulteração no ledger.
        </p>
      </Section>

      {/* Importância no futuro */}
      <div className="border-t border-border" />
      <Section eyebrow="Por que isso importa" title="A Reforma vai obrigar todo ERP a repensar sua tributação. O FiscalCore é a resposta.">
        <p>
          A Reforma Tributária brasileira é a maior alteração no sistema
          desde 1988. Entre 2026 e 2033, empresas vão calcular tributos em{" "}
          <strong>três regimes simultâneos</strong> (atual, fase-teste, e regime
          pleno em transição). Cada NF-e emitida precisará resolver a regra
          correta pela data — retroativamente, se necessário — durante o prazo
          decadencial de cinco anos.
        </p>
        <p>
          Isso significa que <em>toda</em> empresa que emite nota fiscal —
          das indústrias aos e-commerces, dos escritórios de contabilidade aos
          órgãos públicos — vai precisar de um <strong>motor determinístico e
          versionado</strong>. Não é opcional. É requisito para sobreviver a
          uma auditoria que pode pedir o mesmo cálculo em 2031 e esperar o
          mesmo resultado.
        </p>
        <p>
          O que FiscalCore prova, ao final do MVP: <strong>é possível construir
          esse motor sem depender de nenhuma big tech de compliance</strong>.
          Um time pequeno, uma disciplina de contrato-primeiro, e as decisões
          arquiteturais certas (Decimal, base por fora, hash encadeado,
          rulesets como dado) são suficientes. E o mesmo padrão se estende
          para folha, previdenciário, IRPJ — qualquer domínio onde{" "}
          <em>regra é dado versionado</em>.
        </p>
        <p>
          O próximo passo é a integração com <strong>SAP S/4HANA</strong> via
          user-exits no procedimento TAXBRA — para que grandes ERPs possam
          delegar o cálculo IBS/CBS a um motor externo autoritativo, sem tocar
          em uma linha de ABAP crítico. É aí que motor vira plataforma.
        </p>
      </Section>

      {/* Contato inline */}
      <div className="border-t border-border" />
      <ContatoForm />

      {/* Assinatura */}
      <div className="border-t border-border" />
      <section className="max-w-3xl mx-auto py-16 text-center reveal">
        <div className="inline-block border border-accent/30 rounded-md bg-accentDim px-6 py-2 mb-6">
          <span className="text-[10px] font-mono uppercase tracking-[0.3em] text-accent">
            arquitetura & implementação
          </span>
        </div>
        <div className="font-heading text-3xl text-strong mb-2">{AUTHOR.name}</div>
        <div className="text-[14px] text-muted mb-6 font-mono">{AUTHOR.role}</div>
        <div className="flex flex-wrap items-center justify-center gap-3">
          <a
            href={AUTHOR.linkedin}
            target="_blank"
            rel="noreferrer"
            data-testid="sobre-linkedin"
            className="inline-flex items-center gap-2 border border-border rounded-full px-4 py-2 text-[12px] font-medium text-text hover:border-accent hover:text-accent transition-colors"
          >
            <Linkedin className="w-3.5 h-3.5" />
            LinkedIn
            <ExternalLink className="w-3 h-3 opacity-60" />
          </a>
          <a
            href={AUTHOR.extra}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-2 border border-border rounded-full px-4 py-2 text-[12px] font-mono text-muted hover:border-accent hover:text-accent transition-colors"
          >
            <Sparkles className="w-3.5 h-3.5" />
            artefato original
            <ExternalLink className="w-3 h-3 opacity-60" />
          </a>
          <Link
            to="/"
            className="inline-flex items-center gap-2 bg-accent text-bg font-medium rounded-full px-4 py-2 text-[12px] hover:bg-accentHover transition-colors"
          >
            <Zap className="w-3.5 h-3.5" strokeWidth={2.5} />
            testar o motor
          </Link>
        </div>
        <div className="mt-10 pt-8 border-t border-border font-mono text-[11px] text-muted">
          FiscalCore Motor · v0.2.0 · Janeiro/2026 · MIT-style, uso interno
        </div>
      </section>
    </div>
  );
}
