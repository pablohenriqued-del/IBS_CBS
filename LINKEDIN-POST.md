# FiscalCore — Kit de Publicação LinkedIn

3 versões do post + carrossel de 5 slides.
Escolha uma versão ou publique todas em sequência (a cada 3-4 dias).

---
---

## 📌 VERSÃO A · C-LEVEL / EXECUTIVA
*Para: diretores, CFOs, líderes de TI e conselheiros. Foco em risco, valor de mercado e agenda estratégica.*

---

**Toda empresa que emite nota fiscal vai precisar recalcular o passado. Nós ainda estamos preparados para isso?**

A Reforma Tributária brasileira, entre 2026 e 2033, criará um cenário inédito: **três regimes fiscais convivendo ao mesmo tempo** (atual, fase-teste e regime pleno em transição). Cada NF-e emitida precisará ser calculável, retroativamente, com a regra vigente na data da operação — durante todo o prazo decadencial de cinco anos.

Traduzindo para a linguagem do balanço: **uma nota emitida em julho tem que produzir o mesmo tributo em janeiro, em 2027 e em 2031**. Byte-a-byte. Em qualquer auditoria.

Isso não é um problema de alíquota. É um problema arquitetural — e é onde a maioria dos ERPs vai falhar.

Nas últimas semanas, construí um piloto do **FiscalCore Motor**: uma API determinística e auditável para IBS/CBS/Imposto Seletivo. Cinco decisões arquiteturais que separam um motor fiscal de uma "calculadora com skin fiscal":

▪ Cálculos em Decimal (não float) — zero risco de arredondamento silencioso em milhões de operações
▪ Base "por fora" e Imposto Seletivo compondo a base do IBS/CBS — como determina a legislação, sem "atalhos"
▪ **Regras são dado versionado**, com hash SHA-256 e vigência — o motor resolve a regra pela data da operação, nunca "a mais recente"
▪ Trilha de auditoria imutável com hash encadeado — evidência forense em caso de contestação
▪ Contrato-antes-do-código: 64 testes automatizados travam a lógica antes de qualquer refatoração

**O que isso significa em impacto de negócio:**

→ Redução do risco fiscal em auditorias (a evidência é reproduzível e verificável)
→ Base para integração com SAP S/4HANA como motor externo autoritativo, sem tocar no core do ERP
→ Fundação para levar a mesma disciplina para folha, previdenciário, IRPJ — qualquer domínio onde regra é dado
→ Independência de "big techs de compliance" que hoje cobram por transação

A Reforma vai transformar o compliance tributário em problema de engenharia. As empresas que reconhecerem isso primeiro terão uma vantagem estrutural até 2033.

Próximos passos: integração SAP via TAXBRA + adaptadores para NF-e/NFC-e/NFS-e.

Aberto a conversas com times de fiscal, TI ou compliance que estão pensando esse problema seriamente.

#ReformaTributária #IBSCBS #CFO #CIO #SAP #Compliance #Fiscal2026 #GovernançaFiscal

---
---

## 📌 VERSÃO B · TÉCNICA / DEEP-DIVE
*Para: engenheiros, arquitetos, devs de fiscal. Foco em código, decisões e trade-offs.*

---

**Escrevendo um motor de IBS/CBS em Python: cinco decisões arquiteturais que travam a lógica fiscal antes que ela derrape.**

Nas últimas semanas construí o FiscalCore Motor — API `POST /v1/calcular` para IBS, CBS e Imposto Seletivo. Compartilho as decisões que fizeram diferença.

**1. `Decimal`, jamais `float`**

Toda operação monetária passa por `Decimal` com `ROUND_HALF_UP` a 2 casas. Alíquotas com 4 casas. `str(Decimal("0.1") + Decimal("0.2")) == "0.3"` — não `"0.30000000000000004"`. Isso vira teste automatizado: `test_precisao_decimal_sem_float`.

**2. Base "por fora" (e o Imposto Seletivo dentro)**

IBS/CBS incidem sobre uma base que NÃO inclui os próprios tributos nem um ao outro — diferente do "por dentro" do ICMS. Quando há Imposto Seletivo, ele é apurado primeiro e entra na base:

```python
if item.impostoSeletivo:
    valor_is = q2(base_sem_is * aliq_is / CEM)
    base = base_sem_is + valor_is  # ← IS compõe a base
```

**3. Regra é dado, não código**

Rulesets versionados em MongoDB append-only, com id, `vigenciaInicio`, `vigenciaFim` e hash SHA-256 do JSON canônico (sort_keys=True). O motor resolve o ruleset pela `dataOperacao` da requisição — nunca "o mais recente":

```python
def resolver_ruleset(rulesets, data_operacao):
    for r in rulesets:
        if r.vigenciaInicio <= data_operacao <= (r.vigenciaFim or infinito):
            return r
```

Duas rulesets pré-carregadas: `2026-fase-teste` (CBS 0,9% + IBS 0,1%) e `2026-regime-pleno-v1` (CBS 8,8% + IBS-UF 12% + IBS-Mun 5,7%).

**4. Ledger de auditoria com hash encadeado**

Cada evento (login, importação NF-e, cálculo, apuração) grava:

```
{seq, ts, actor, action, payload, prev_hash}
hash = sha256(canonical_json({...}))
```

`GET /v1/auditoria/verificar` recomputa toda a cadeia e retorna `{ok: true, total, broken_at: null}` — ou o seq exato onde a integridade quebrou. Detecção de adulteração em O(n).

**5. Contrato-antes-do-código**

Antes de escrever uma linha, escrevi 62 linhas de contrato com três casos-ouro e resultados esperados até o centavo:

- Cadeira R$ 1.000 integral → CBS 88 + IBS 177 = **R$ 265**
- Medicamento R$ 500 com redução 60% → CBS 17,60 + IBS 35,40 = **R$ 53**
- Bebida R$ 200 com IS 10% → IS 20 + CBS 19,36 + IBS 38,94 = **R$ 78,30**

**Se o motor não bate byte-a-byte, o motor está errado.** 64 testes automatizados garantem que qualquer PR que quebre um centavo falha o CI.

**Stack:**
- FastAPI + Motor async MongoDB + Pydantic v2 + bcrypt/PyJWT
- React + react-router + axios com Bearer fallback (o ingress K8s reescreve `Access-Control-Allow-Origin: *`, cookies cross-site quebram)
- Fraunces + IBM Plex + JetBrains Mono. Paleta bronze editorial, dark/light theme com CSS variables

**Próximo passo:** adaptador para o procedimento TAXBRA do SAP S/4HANA. Endpoint `POST /v1/sap/pricing` que aceita KOMV e devolve condition types já preenchidos. Motor externo autoritativo, zero ABAP crítico.

Feliz em debater qualquer decisão nos comentários 👇

#Python #FastAPI #MongoDB #FiscalTech #Arquitetura #Decimal #SAP #ReformaTributária

---
---

## 📌 VERSÃO C · HÍBRIDA (a que já entreguei antes)
*70% storytelling + 30% técnica. Melhor equilíbrio para audiência mista.*

Ver arquivo `LINKEDIN-POST.md` — versão 1.

---
---

# 🎠 CARROSSEL DE 5 SLIDES

**Formato**: 1080×1080 (quadrado). LinkedIn aceita PDF com múltiplas páginas — cada página vira um slide navegável. Upload como "documento".

**Ferramenta sugerida para montar o PDF**: cole cada imagem em uma página do Canva/Figma/PowerPoint com o overlay de texto proposto abaixo, exporte como PDF.

## SLIDE 1 · Hook

**Imagem base**: `/app/slide-1-hero.jpg`
**Overlay** (grande, canto superior esquerdo, tipografia serifada branca):

> **Uma nota emitida em julho**
> **tem que ser calculada**
> **com a regra de julho.**
> — Hoje, amanhã ou numa fiscalização em 2031.

**Rodapé**: FiscalCore Motor · v0.2.0

## SLIDE 2 · O problema

**Imagem base**: `/app/slide-2-pilares.jpg` OU fundo dark simples com texto
**Título** (Fraunces, bronze): *"Três regimes ao mesmo tempo. Sete anos de transição."*
**Corpo**:

> A Reforma Tributária cria um cenário inédito:
> Atual · Fase-teste 2026 · Regime pleno
>
> Cada NF-e precisa ser calculada com a regra vigente **na data da operação**, retroativamente, durante todo o prazo decadencial.
>
> Isso não é problema de alíquota.
> É problema **arquitetural**.

## SLIDE 3 · Os 5 princípios

**Imagem base**: `/app/slide-2-pilares.jpg` (o grid 01-02-03-04 já pronto)
**Overlay título**: *"Cinco princípios inegociáveis"*
**Corpo já visível no print** (os 4 pilares) — adicionar o 5º embaixo:

> **05. Contrato antes do código.** Três casos-ouro, resultados esperados até o centavo. 64 testes travando cada decisão.

## SLIDE 4 · A prova (números batendo)

**Imagem base**: `/app/slide-3-totais.jpg` (playground com o card R$ 376,30 em destaque)
**Overlay título**: *"Os três casos-ouro do contrato"*
**Corpo** (canto inferior):

> Cadeira integral → **R$ 265**
> Medicamento (redução 60%) → **R$ 53**
> Bebida com IS 10% → **R$ 78,30**
>
> **Total: R$ 376,30 — byte a byte.**

## SLIDE 5 · Ledger imutável

**Imagem base**: `/app/slide-4-ledger.jpg` (a tela `/auditoria` com "íntegra · 380 eventos")
**Overlay título**: *"Trilha de auditoria com hash encadeado"*
**Corpo**:

> Cada evento (login, cálculo, importação, apuração) referencia o hash SHA-256 do anterior.
>
> Adulteração quebra a cadeia.
> O verificador aponta o **seq exato** da ruptura.
>
> Evidência forense reproduzível.

## SLIDE 6 · CTA + Assinatura

**Imagem base**: `/app/slide-6-assinatura.jpg` (a página `/sobre` com sua assinatura)
**Overlay** já embutido — só reforçar no rodapé do slide:

> **Próxima parada:** SAP S/4HANA via TAXBRA. Motor vira plataforma.
>
> Feito por **Pablo Duarte** · Gerente de Inovação & TI
> linkedin.com/in/pablo-henrique-duarte

---
---

# 🎯 ESTRATÉGIA DE PUBLICAÇÃO

**Plano recomendado para 2 semanas:**

| Dia | Ação | Formato |
|---|---|---|
| D+0 (terça, 8h) | **Versão C (híbrida)** | Post texto + imagem `/app/linkedin-playground.jpg` |
| D+2 (quinta) | **Carrossel 5 slides** | Upload PDF com os 5 slides montados |
| D+7 (terça) | **Versão B (técnica)** | Post texto puro (audiência de dev engaja mais em texto longo) |
| D+11 (sábado, 10h) | **Versão A (executiva)** | Post texto + slide 4 (a prova) — sábado tem menos ruído, C-level lê |

**Regra de ouro do algoritmo LinkedIn (2026):**
1. Zero links externos no corpo — só nos comentários.
2. Responda os primeiros 5 comentários em ≤ 30 min (dobra o alcance).
3. Peça uma pergunta específica no final ("qual foi a decisão mais controversa?" gera mais reply que "o que acharam?").
4. Marque 2-3 pessoas relevantes (mas só se fizer sentido — marcação genérica é penalizada).
5. Não edite o post nas primeiras 4h — cada edição reduz alcance em ~15%.

**Métrica de sucesso pra medir:**
- Impressões nas primeiras 24h (meta: ≥ 3.000 pra uma rede de 500-1.500 conexões)
- Dwell time no carrossel (LinkedIn mostra na análise — meta: ≥ 4s por slide)
- Comentários qualificados (não emojis) — meta: ≥ 8

**Arquivos disponíveis em `/app/`:**
- `linkedin-hero.jpg` (1920×1080) — hero page do site
- `linkedin-playground.jpg` (1920×1080) — playground com resultado
- `linkedin-sobre.jpg` (1920×1080) — página /sobre
- `linkedin-footer.jpg` (1920×1080) — footer com assinatura
- `slide-1-hero.jpg` (1080×1080) — hook / capa
- `slide-2-pilares.jpg` (1080×1080) — 4 pilares
- `slide-3-totais.jpg` (1080×1080) — playground com R$ 376,30
- `slide-4-ledger.jpg` (1080×1080) — /auditoria íntegra
- `slide-5-delta.jpg` (1080×1080) — simulador delta atual vs Reforma
- `slide-6-assinatura.jpg` (1080×1080) — sobre + assinatura Pablo
