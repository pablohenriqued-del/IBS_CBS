"""Rulesets seed — dados versionados de regras fiscais.

Um ruleset é um artefato imutável identificado por (id, hash, vigência).
O motor NUNCA "adivinha" alíquotas: ele resolve cClassTrib → tratamento no
ruleset vigente na dataOperacao.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date
from typing import Any, Dict, List, Optional

# --------------------------------------------------------------------------
# DEFINIÇÕES DE RULESETS
# --------------------------------------------------------------------------
# Cada ruleset é um dict determinístico. O hash SHA-256 é calculado a partir
# do JSON canônico (chaves ordenadas) — assim o mesmo artefato produz sempre
# o mesmo hash, e qualquer alteração muda o hash.
#
# Alíquotas são armazenadas como STRING para preservar precisão decimal
# (ex.: "8.8000"). O motor converte para Decimal na hora do cálculo.
#
# Vigência é resolvida por dataOperacao: um ruleset está vigente se
# vigenciaInicio <= dataOperacao <= (vigenciaFim ou +infinito).
# --------------------------------------------------------------------------

RULESETS_SEED: List[Dict[str, Any]] = [
    {
        "id": "ruleset:2026-fase-teste",
        "descricao": "Fase de teste 2026 — CBS 0,9% + IBS 0,1%",
        "vigenciaInicio": "2026-01-01",
        "vigenciaFim": "2026-06-30",
        "cbs": {"aliquotaNominal": "0.9000"},
        # Durante a fase de teste, o IBS total é 0,1%, atribuído integralmente
        # à parcela da UF (a divisão UF/Município será regulamentada no
        # regime pleno). Documentado explicitamente em `avisos`.
        "ibs": {
            "aliquotaUF": "0.1000",
            "aliquotaMunicipio": "0.0000",
        },
        "cClassTrib": {
            "000001": {
                "descricao": "tributação integral",
                "cst": "000",
                "reducao": "0.0000",
                # Carga tributária média do regime atual (ICMS + PIS/Cofins).
                # Fonte: estimativa para produtos de consumo padrão (SP).
                "cargaAtualPct": "27.2500",
            },
        },
        "avisos": [
            "Fase de teste 2026: IBS de 0,1% atribuído integralmente à parcela da UF (divisão UF/Município ainda não regulamentada).",
        ],
    },
    {
        "id": "ruleset:2026-regime-pleno-v1",
        "descricao": "Regime pleno projetado — CBS 8,8% + IBS 17,7% (UF 12% + Mun 5,7%)",
        "vigenciaInicio": "2026-07-01",
        "vigenciaFim": None,
        "cbs": {"aliquotaNominal": "8.8000"},
        "ibs": {
            "aliquotaUF": "12.0000",
            "aliquotaMunicipio": "5.7000",
        },
        "cClassTrib": {
            "000001": {
                "descricao": "tributação integral",
                "cst": "000",
                "reducao": "0.0000",
                # ICMS 18% (SP) + PIS 1,65% + COFINS 7,6% = 27,25% (não-cumulativo agregado)
                "cargaAtualPct": "27.2500",
            },
            "200052": {
                "descricao": "redução de 60%",
                "cst": "200",
                "reducao": "60.0000",
                # Medicamentos: regime específico, carga média ~10% (ICMS reduzido + PIS/Cofins zerado em muitos)
                "cargaAtualPct": "10.0000",
            },
        },
        "avisos": [
            "Alíquotas de regime pleno são projeções carregadas no ruleset e podem mudar por norma.",
        ],
    },
]


def canonical_json(obj: Any) -> str:
    """Serializa em JSON canônico (chaves ordenadas, sem espaços supérfluos)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def compute_ruleset_hash(ruleset: Dict[str, Any]) -> str:
    """SHA-256 do JSON canônico do ruleset (sem o campo `hash`)."""
    payload = {k: v for k, v in ruleset.items() if k != "hash"}
    raw = canonical_json(payload).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def resolver_ruleset(rulesets: List[Dict[str, Any]], data_operacao: date) -> Optional[Dict[str, Any]]:
    """Resolve o ruleset vigente para a dataOperacao.

    Retorna None se nenhum estiver vigente. Se houver mais de um vigente
    (não deveria acontecer), retorna o que tem vigenciaInicio mais recente
    (mas isso é um erro operacional que deveria ser prevenido no seed).
    """
    candidatos = []
    for r in rulesets:
        inicio = date.fromisoformat(r["vigenciaInicio"])
        fim = date.fromisoformat(r["vigenciaFim"]) if r.get("vigenciaFim") else None
        if inicio <= data_operacao and (fim is None or data_operacao <= fim):
            candidatos.append(r)
    if not candidatos:
        return None
    # Determinístico: mais recente por vigenciaInicio (defensive; overlaps não devem ocorrer)
    candidatos.sort(key=lambda r: r["vigenciaInicio"], reverse=True)
    return candidatos[0]
