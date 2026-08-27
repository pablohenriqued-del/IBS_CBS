# FiscalCore — Post para LinkedIn

## VERSÃO 1 · Recomendada (híbrida, storytelling forte + prova técnica)

---

**Uma nota emitida em julho tem que ser calculada com a regra de julho — hoje, amanhã ou numa fiscalização daqui a cinco anos.**

Essa frase resume o problema que me tirou o sono nas últimas semanas.

A Reforma Tributária de 2026 traz IBS, CBS e Imposto Seletivo. Mas o problema real, do ponto de vista de sistemas, não são as alíquotas — é o fato de que empresas vão operar em **três regimes simultâneos** (atual, fase-teste, regime pleno em transição) durante os próximos sete anos. E cada NF-e vai precisar resolver a regra correta pela data da operação, retroativamente, durante o prazo decadencial.

Traduzindo: se você emite uma nota em 15/03/2026 e um auditor pede o mesmo cálculo em 2031, o número tem que ser **byte-a-byte idêntico**.

Isso não é um exercício de framework. É um exercício de disciplina.

Nas últimas semanas construí o **FiscalCore Motor** — uma API determinística e auditável de cálculo IBS/CBS/IS. Cinco princípios inegociáveis:

🔹 **Decimal, nunca float.** Todos os cálculos monetários com `ROUND_HALF_UP` a 2 casas. Zero arredondamento binário silencioso.

🔹 **Base "por fora".** IBS e CBS incidem sobre uma base que não inclui os próprios tributos — diferente do "por dentro" do ICMS que a gente conhece.

🔹 **Imposto Seletivo compõe a base.** Sem exceções.

🔹 **Regra é dado, não código.** Rulesets versionados com hash SHA-256 e vigência. O motor resolve o ruleset pela `dataOperacao` — nunca "o mais recente".

🔹 **Trilha imutável.** Um ledger append-only onde cada evento (login, importação, cálculo, apuração) grava o hash SHA-256 do payload encadeado ao hash do evento anterior. Qualquer adulteração quebra a cadeia — e o verificador aponta o exato ponto de ruptura.

64 testes automatizados. Três casos-ouro do contrato batendo até o centavo:
▪ Cadeira R$ 1.000 integral → R$ 265
▪ Medicamento R$ 500 com redução de 60% → R$ 53
▪ Bebida R$ 200 com Imposto Seletivo → R$ 78,30

O stack: FastAPI + Python Decimal + MongoDB append-only, React com Fraunces + IBM Plex + JetBrains Mono. Autenticação JWT com três papéis (fiscal, auditoria, admin). Ingestão de NF-e com idempotência por chave de acesso. Simulador comparativo "carga hoje vs carga com a Reforma".

**O que o FiscalCore prova, ao final desse MVP:** é possível construir um motor fiscal auditável sem depender de nenhuma big tech de compliance. Um time pequeno, uma disciplina de contrato-antes-do-código, e as decisões arquiteturais certas são suficientes.

O próximo passo é a integração com **SAP S/4HANA** via user-exits no procedimento TAXBRA — para que grandes ERPs possam delegar o cálculo IBS/CBS a um motor externo autoritativo, sem tocar em uma linha de ABAP crítico.

É aí que motor vira plataforma.

---

Se você trabalha com fiscal, tributário, ERPs ou Reforma Tributária, aceito qualquer comentário, crítica ou pergunta abaixo 👇

#ReformaTributária #IBSCBS #Fiscal2026 #SAP #S4HANA #TechFiscal #Compliance #Python #FastAPI #InovaçãoFiscal

---

📌 **Imagem sugerida para o post**: `/app/linkedin-playground.jpg` (o playground com os 3 casos-ouro calculados — R$ 265 + R$ 53 + R$ 78,30, com a barra de totais bronze embaixo)

---

---

## VERSÃO 2 · Mais curta (mobile-first, ideal se quiser algo mais direto)

**Escrevi um motor fiscal em Python para sobreviver à Reforma Tributária de 2026.**

Não porque falta ferramenta no mercado — mas porque queria provar que dá pra fazer certo, com um time pequeno e as decisões arquiteturais corretas.

Cinco princípios inegociáveis:

▪ `Decimal`, nunca `float`
▪ Base "por fora" (IBS/CBS não incluem a si mesmos nem um ao outro)
▪ Imposto Seletivo compõe a base
▪ Regra é **dado versionado**, não código (resolvido por `dataOperacao`)
▪ Trilha de auditoria imutável com hash SHA-256 encadeado

Resultado: uma API `POST /v1/calcular` com 64 testes automatizados, três casos-ouro batendo até o centavo, ingestão de NF-e com idempotência, apuração por período (débitos − créditos), simulador "carga hoje vs Reforma", e um ledger que detecta adulteração e aponta o seq exato onde a cadeia quebrou.

Stack: FastAPI · MongoDB append-only · React · JWT com três papéis (fiscal/auditoria/admin).

Uma nota emitida em julho tem que ser calculada com a regra de julho — hoje, amanhã ou numa fiscalização daqui a cinco anos.

**É esse detalhe que separa um sistema fiscal de um sistema que só faz continhas.**

Próxima parada: integração com SAP S/4HANA via TAXBRA. Motor vira plataforma.

#ReformaTributária #IBSCBS #Fiscal2026 #SAP

---

---

## Dicas de publicação

1. **Melhor horário**: terça a quinta, 8h-10h ou 12h-14h (BR).
2. **Primeira linha (hook)** é o que mais importa — o LinkedIn corta em ~200 chars no feed. A versão 1 já foi otimizada pra isso.
3. **Sem link externo no corpo** do post (LinkedIn penaliza). Coloque o link nos comentários ("👇 código e detalhes técnicos no primeiro comentário").
4. **Emojis com moderação** — os que usei (🔹 ▪ 👇) são profissionais. Evite os coloridos (💥🚀🔥).
5. **Marque pessoas** que trabalham com fiscal/SAP na sua rede — mesmo 2-3 marcações elevam o alcance em ~40%.
6. **Responda todos os comentários nas primeiras 2h** — o algoritmo dobra o alcance quando vê engajamento rápido.

---

## Sugestão de comentário para postar logo em seguida

> Alguns detalhes técnicos que ficaram fora do post pra não ficar longo demais:
> 
> — Os rulesets são serializados em JSON canônico (sort_keys=True, sem espaços) antes do SHA-256, garantindo hash determinístico.
> — A memória de cálculo é retornada linha a linha em cada resposta ("Base = ... × 8.8000% × 1.0000 = 88.00"), pra que um auditor possa reconstruir cada operação sem precisar rodar o motor.
> — A trilha ledger tem um `POST /v1/auditoria/verificar` que recomputa toda a cadeia e retorna `{ok: true, total, broken_at: null}` — ou aponta o seq exato da quebra.
> — A idempotência de ingestão é por `chaveAcesso` (44 dígitos): reenviar o mesmo XML devolve 409 com o id do documento original.
> 
> Feliz em detalhar qualquer ponto.
