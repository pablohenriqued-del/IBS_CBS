# FiscalCore — Vídeo Explicativo LinkedIn

**Arquivo pronto para upload:** `/app/video/FiscalCore-LinkedIn.mp4`

**Especificações**
- Resolução: **1920 × 1080** (Landscape · LinkedIn native video)
- Duração: **88.8 segundos**
- Vídeo: H.264 · 30fps · CRF 20 · 602 kbps
- Áudio: AAC 192 kbps · stereo · voz "onyx" (OpenAI TTS-1-HD)
- Tamanho: **6.5 MB** (LinkedIn limite: 5 GB / 10 min — folgado)
- Legendas: burned-in (Fraunces Bold Italic, paleta bronze da marca)

## Roteiro (7 cenas × ~13s)

| # | Cena | Legenda principal | Página |
|---|---|---|---|
| 1 | Hook / problema fiscal | "A regra da nota emitida em julho é a regra de julho." | `/sobre` |
| 2 | Playground calculando | "Os três casos-ouro, ao vivo." | `/` |
| 3 | Simulador delta | "Quanto vai mudar?" | `/simulador` |
| 4 | Auditoria hash chain | "Trilha imutável." | `/auditoria` |
| 5 | SAP KOMV modal | "Motor externo autoritativo." | `/` (modal) |
| 6 | SAP Reconciliação divergente | "Onde o ERP errou — e por quantos centavos." | `/sap` |
| 7 | Assinatura Pablo | "Pablo Duarte — Gerente de Inovação e TI" | `/sobre` |

## Copy sugerida para o post (acompanhando o vídeo)

```
Construí um motor de IBS/CBS deterministico em ~4 semanas.

Cinco decisões arquiteturais que separam um motor fiscal
de uma calculadora com skin fiscal:

▪ Cálculos em Decimal (não float) — zero arredondamento silencioso
▪ Base "por fora", com Imposto Seletivo compondo a base
▪ Regras são dado versionado — resolvidas pela dataOperacao
▪ Trilha de auditoria imutável com hash SHA-256 encadeado
▪ 64 testes automatizados travando cada centavo antes de qualquer refactor

E provei que dá pra conversar com SAP S/4HANA como motor externo
autoritativo — sem ABAP crítico. No vídeo: KOMV nativo,
IDOC INVOIC02 parseado, e o painel de reconciliação apontando
onde o ERP errou (e por quantos centavos).

Feito com disciplina de engenharia. Base para levar essa
mesma abordagem para folha, previdenciário, IRPJ — qualquer
domínio onde regra é dado.

Comenta "FiscalCore" que envio o link do repositório.

#ReformaTributária #IBSCBS #SAP #FiscalTech #Arquitetura
```

## Checklist de upload no LinkedIn

1. Fazer upload do MP4 no **feed** (não Reels — vídeo é landscape).
2. Adicionar **legenda SRT** opcionalmente (LinkedIn gera auto-caption, mas voz
   TTS com sotaque inglês pode confundir — considere burnar SRT PT-BR ou
   desativar auto-caption).
3. Adicionar thumbnail customizada (usar `/app/carousel/slide-1-hero.jpg` ou
   um dos frames do próprio vídeo).
4. Postar **na terça 8h** ou **hoje 00h50** (conforme estratégia definida).
5. **Não editar nas primeiras 4h** (cada edição corta ~15% do alcance).
6. Responder os primeiros 5 comentários em ≤ 30 min (dobra o alcance).

## Aviso sobre a voz TTS

A voz `onyx` do OpenAI TTS é otimizada para inglês, então narra o português com
um leve sotaque americano. É compreensível e funciona bem para o público de TI
brasileiro, mas se quiser voz nativa PT-BR, a upgrade path é **ElevenLabs
`eleven_multilingual_v2` com voice ID nativo em português** (requer API key
própria — Emergent LLM Key não cobre ElevenLabs).

## Como regerar (opcional)

Todos os assets intermediários ficam em `/app/video/`:
- `audio/*.mp3` — narração por cena
- `raw/*/*.webm` — gravações Playwright originais
- `scenes/*.mp4` — cenas compostas individuais
- `FiscalCore-LinkedIn.mp4` — vídeo final concatenado

Rerodar do zero: `python3 /app/scripts/gen_video.py`.
Recompor com legenda ajustada: editar `SCENES` em `gen_video.py`
e rodar só a fase 3 (o script pula TTS/gravação se caches existem).
