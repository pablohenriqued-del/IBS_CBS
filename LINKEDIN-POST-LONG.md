# FiscalCore — Post Explicativo Longo (LinkedIn)

**Autor:** Pablo Duarte — Gerente de Inovação e TI
**Formato:** Texto principal do post + copy resumida (LinkedIn limita a 3.000 caracteres visíveis antes do "ver mais"). Este arquivo traz a versão completa; você pode publicar inteiro ou cortar até o "ver mais" na quebra sugerida.
**Data alvo:** [inserir]
**Anexos sugeridos:** vídeo `/app/video/FiscalCore-LinkedIn.mp4` + carrossel PDF `/app/FiscalCore-LinkedIn-Carousel.pdf`.

---

## POST COMPLETO (versão longa · ~2.400 caracteres visíveis + expansão)

---

**Toda empresa que emite nota fiscal vai precisar recalcular o passado. E nós ainda não estamos preparados para isso.**

Nas últimas semanas eu resolvi provar, em código e não em slide, uma tese que tem me perseguido desde que a Reforma Tributária foi promulgada: **compliance fiscal, entre 2026 e 2033, deixa de ser um problema de alíquota e vira um problema de arquitetura de software.**

O resultado é o *FiscalCore Motor*. Deixa eu explicar por que ele existe.

---

**O QUE VAI MUDAR NA PRÁTICA**

A Reforma Tributária brasileira, aprovada pela EC 132/2023 e regulamentada pela LC 214/2025, substitui cinco tributos (ICMS, ISS, IPI, PIS e Cofins) por três: **IBS**, **CBS** e **Imposto Seletivo**. Simples de descrever, cataclísmico de operacionalizar.

*Por três motivos que a maioria dos ERPs ainda não digeriu:*

**1. Sete anos de transição — com três regimes convivendo ao mesmo tempo.**
2026 é ano de teste (CBS 0,9% + IBS 0,1%, sem efeito fiscal real). 2027 já entra a CBS cheia. De 2029 a 2032, o ICMS/ISS vão sendo drenados enquanto o IBS enche o copo. Cada NF-e emitida em 2026 precisa ser calculável, retroativamente, com a regra vigente **na data da operação** — durante todo o prazo decadencial de cinco anos. Uma nota emitida em julho de 2026 tem que produzir o mesmo tributo em janeiro de 2027, em 2029 e numa fiscalização em 2031. **Byte a byte.**

**2. Base "por fora" — e o Imposto Seletivo compondo a base.**
Diferente do ICMS "por dentro" que a gente conhece há 30 anos, IBS e CBS incidem sobre uma base que **não inclui os próprios tributos**, nem um ao outro. Mas quando existe Imposto Seletivo (o "imposto do pecado" sobre bebida açucarada, cigarro, veículo poluente), ele é apurado antes e **entra na base** de IBS/CBS. Isso quebra qualquer motor de cálculo que usa float, que arredonda no final ou que trata os tributos como camadas independentes.

**3. Split-payment e cashback.**
O IBS/CBS é recolhido *no ato do pagamento*, com repasse automático ao Fisco. Consumidor final PF ainda tem direito a cashback. Isso pressupõe uma reconciliação em tempo real que o modelo mensal do ICMS nunca precisou fazer.

Traduzindo para a linguagem do balanço: **compliance fiscal deixa de ser um relatório mensal e vira um serviço distribuído, transacional, reversível e auditável.**

---

**POR QUE A MAIORIA DOS ERPs VAI FALHAR**

Porque ERP nasceu com uma premissa que a Reforma quebra: **regras fiscais são código.** Alíquotas em tabela `T007A`. Fórmulas de base em `MM_TAX_RATE`. `MWSKZ` engessado no cliente. Toda mudança fiscal vira transporte, teste em QAS, homologação em PRD, semanas de janela.

O problema é que, em 2026, a regra do dia 15 pode não ser a mesma regra do dia 16. E daqui a cinco anos, uma auditoria vai pedir a nota **exatamente como ela deveria ter sido calculada em 2026**, com a regra daquele dia — não com a regra "mais recente".

**Regra fiscal não é código. Regra fiscal é dado versionado com vigência.**

Essa foi a virada de chave.

---

**A SOLUÇÃO: FISCALCORE MOTOR — CINCO PRINCÍPIOS INEGOCIÁVEIS**

Ao invés de escrever "mais um" adaptador tributário, eu tratei o motor como se fosse um subsistema crítico bancário. Cinco decisões arquiteturais, cada uma travada em teste automatizado antes de escrever a próxima linha de código:

**01. Decimal, jamais float.**
Toda operação monetária passa por `Decimal` com `ROUND_HALF_UP` a 2 casas. Alíquotas com 4 casas. Nada de `0.1 + 0.2 = 0.30000000000000004`. Isso vira teste: `test_precisao_decimal_sem_float` falha o CI se algum PR introduzir um `float` no caminho crítico.

**02. Base "por fora", com IS na base — sem exceções.**
O motor calcula o Imposto Seletivo primeiro, soma na base, e só então aplica CBS + IBS-UF + IBS-Município. Nada de "atalho" que arredonda por camada.

**03. Regra é dado, não código.**
Rulesets versionados em MongoDB append-only, cada um com `id`, `vigenciaInicio`, `vigenciaFim` e **hash SHA-256** do JSON canônico. O motor resolve o ruleset pela `dataOperacao` da requisição — nunca "o mais recente". Duas rulesets já pré-carregadas: `2026-fase-teste` e `2026-regime-pleno-v1`.

**04. Trilha de auditoria imutável com hash encadeado.**
Cada evento (login, importação de NF-e, cálculo, apuração, chamada SAP) grava no ledger:

```
{seq, timestamp, actor, action, payload, prev_hash}
hash = sha256(canonical_json({...}))
```

`GET /v1/auditoria/verificar` recomputa a cadeia inteira e retorna `{ok: true, total, broken_at: null}` — ou o `seq` exato onde a integridade quebrou. Detecção de adulteração em O(n). É evidência forense de contestação em juízo.

**05. Contrato antes do código.**
Antes de escrever uma linha, escrevi 62 linhas de contrato com três casos-ouro e resultados esperados até o centavo: cadeira R$ 1.000 integral → R$ 265 de tributo; medicamento R$ 500 com redução de 60% → R$ 53; bebida R$ 200 com IS 10% → R$ 78,30. **Se o motor não bate byte-a-byte, o motor está errado.** 80 testes automatizados garantem isso em cada PR.

---

**E O SAP? A INTEGRAÇÃO QUE PROVA A TESE**

Motor bonito no papel não vale nada se não conversa com o S/4HANA, onde grande parte do mercado brasileiro roda pricing. Então implementei o loop completo:

▪ **`POST /v1/sap/pricing`** aceita payload no formato KOMV nativo do SAP (VBELN, KPOSN, MATNR, KBETR, KWERT) e devolve tabela KOMV com condition types no namespace Z: **ZCBS**, **ZIBU** (IBS-UF), **ZIBM** (IBS-Município), **ZISE** (Imposto Seletivo). Nos STUNR corretos do pricing schema. Sem ABAP crítico.

▪ **`POST /v1/sap/idoc/parse`** faz o inbound de IDOC INVOIC02 (segmentos EDI_DC40, E1EDK01, E1EDP01, E1EDP19, E1EDP04, E1EDS01 + extensão custom Z1FISC_CLASTRIB).

▪ **`POST /v1/sap/reconciliar`** compara o cálculo que o SAP mandou contra o que o motor autoritativo diz — condição por condição, com delta em centavos e status por (KPOSN, KSCHL). No demo, um IDOC "com bug" é detectado automaticamente: 4 divergências apontadas, incluindo o erro clássico onde o ERP esqueceu de somar o IS na base do CBS.

**Motor externo, autoritativo, plugável. É esse o modelo que faz sentido daqui pra frente.**

---

**O QUE ISSO SIGNIFICA EM VALOR DE NEGÓCIO**

→ **Redução do risco fiscal em auditorias**: a evidência é reproduzível e verificável, com hash encadeado. Não é "confie no ERP" — é "reprocesse a nota e valide o hash".

→ **Base para levar a mesma disciplina para outros domínios**: folha, previdenciário, IRPJ, contribuições. Todo domínio onde *regra é dado versionado* pode ser modelado assim.

→ **Independência das "big techs de compliance"** que cobram por transação. Motor próprio, deterministico, código aberto para o time interno.

→ **Contrato claro entre TI e Fiscal**: se a regra mudou, muda-se o ruleset. Se o motor errou, mostra-se o teste que passou. Zero interpretação, zero "acho que é assim".

---

**A CONCLUSÃO QUE EU CARREGO DESSA SEMANA**

A Reforma Tributária vai transformar o compliance tributário em problema de engenharia. **As empresas que reconhecerem isso primeiro vão ter uma vantagem estrutural até 2033.**

Se você é CFO, CIO, líder fiscal ou arquiteto rodando SAP no Brasil e está pensando esse problema seriamente — vamos conversar. Comenta *FiscalCore* nos comentários que eu envio o link do repositório e a documentação de arquitetura completa.

---

Feito com Python 3.11, FastAPI, MongoDB, React 19, disciplina de contrato-antes-do-código e paciência para não usar `float`.

Pablo Duarte
Gerente de Inovação e TI
linkedin.com/in/pablo-henrique-duarte

#ReformaTributária #IBSCBS #ImpostoSeletivo #SAP #S4HANA #TAXBRA #FiscalTech #Arquitetura #Compliance #CFO #CIO #GovernançaFiscal #Fiscal2026

---
---

## POST MÉDIO (versão intermediária ~1.500 caracteres — se o longo cansar)

**Toda empresa que emite nota fiscal vai precisar recalcular o passado.**

A Reforma Tributária cria três regimes fiscais convivendo entre 2026 e 2033. Uma nota emitida em julho tem que ser recalculada, byte a byte, com a regra vigente na data da operação — durante todo o prazo decadencial de cinco anos.

Isso não é problema de alíquota. É problema arquitetural — e é onde a maioria dos ERPs vai falhar.

Passei as últimas semanas construindo o *FiscalCore Motor* para provar que dá pra resolver isso com disciplina de engenharia. Cinco decisões arquiteturais que separam um motor fiscal de uma "calculadora com skin fiscal":

▪ **Decimal, nunca float** — zero arredondamento silencioso em milhões de operações
▪ **Base "por fora"** com Imposto Seletivo compondo a base — sem exceções
▪ **Regras como dado versionado** com hash SHA-256 — o motor resolve pela `dataOperacao`, nunca "a mais recente"
▪ **Trilha de auditoria imutável** com hash encadeado — evidência forense em O(n)
▪ **Contrato antes do código** — 80 testes travam cada centavo antes de qualquer refactor

E pra fechar o loop com o mundo real: adaptador **SAP S/4HANA via KOMV nativo**, parser de **IDOC INVOIC02**, e um painel de reconciliação que aponta, condição por condição, onde o ERP errou — com delta em centavos.

**Motor externo autoritativo. Zero ABAP crítico. Base para levar a mesma abordagem para folha, previdenciário e IRPJ.**

A Reforma vai transformar compliance tributário em problema de engenharia. As empresas que reconhecerem isso primeiro terão vantagem estrutural até 2033.

Comenta "FiscalCore" que envio o link do repositório.

Pablo Duarte — Gerente de Inovação e TI

#ReformaTributária #IBSCBS #SAP #FiscalTech #Arquitetura #GovernançaFiscal

---
---

## POST CURTO (versão mobile ~150 palavras — já entregue em `LINKEDIN-POST-SHORT.md`)

Ver arquivo `/app/LINKEDIN-POST-SHORT.md`.

---

## OBSERVAÇÕES DE PUBLICAÇÃO

**Onde cortar o "ver mais":**
No post longo, corte o expand no fim do parágrafo **"O resultado é o FiscalCore Motor. Deixa eu explicar por que ele existe."** — assim quem clica em "ver mais" já se comprometeu com o gancho. LinkedIn mostra ~210 caracteres antes do fold no mobile.

**Sequência sugerida:**
- Semana 1, terça 8h: **post curto** + vídeo `/app/video/FiscalCore-LinkedIn.mp4` (máximo alcance)
- Semana 1, quinta: **carrossel PDF** (deep visual)
- Semana 2, terça: **post longo** (a versão deste arquivo) sem anexo — texto puro tende a engajar audiência técnica (dev/arquiteto)
- Semana 2, sábado 10h: **versão média** com slide 4 (a "prova" — R$ 376,30 byte a byte)

**Métricas para acompanhar nas primeiras 24h:**
- Impressões: ≥ 3.000 (rede de 500-1.500 conexões, com vídeo)
- Dwell time no vídeo: ≥ 30s (janela de retenção do algoritmo)
- Comentários qualificados (não emojis): ≥ 8
- DMs de C-level ou arquiteto: sinal forte de conversão

**Regra de ouro:**
Não editar o post nas primeiras 4 horas. Cada edição corta ~15% do alcance orgânico. Respostas nos primeiros 30 minutos dobram o alcance — bloqueie a agenda de 8h às 9h30.
