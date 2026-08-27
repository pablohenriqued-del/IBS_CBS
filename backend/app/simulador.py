"""Simulador comparativo — regime atual (ICMS/PIS/Cofins/IS aproximado) vs Reforma.

Para cada item, calcula a carga tributária no regime atual como
`base × cargaAtualPct` (do ruleset, por cClassTrib), e compara com a saída do
motor no regime da Reforma. O delta mostra "quanto vai mudar".

Aviso: `cargaAtualPct` é uma estimativa média (SP, produtos padrão). Regimes
específicos (Simples, MEI, imunidades) precisam de rulesets dedicados.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List

from .models import CalcularRequest, ItemOut, Totais
from .motor import calcular, d, q2, TWO_PLACES, CEM


def calcular_atual(req: CalcularRequest, ruleset: Dict[str, Any]) -> Dict[str, Any]:
    """Calcula a carga tributária no regime atual (aproximação por cargaAtualPct)."""
    itens_atual: List[Dict[str, Any]] = []
    base_total = Decimal("0")
    tributos_total = Decimal("0")

    for item in req.itens:
        classe = ruleset["cClassTrib"].get(item.cClassTrib)
        if classe is None:
            raise ValueError(
                f"cClassTrib {item.cClassTrib} não encontrado (necessário para simulação atual)"
            )
        carga_pct = d(classe.get("cargaAtualPct", "0"))

        valor_item = d(item.valorItem)
        desconto = d(item.descontoIncondicional or "0")
        if item.acrescimos:
            frete = d(item.acrescimos.frete or "0")
            seguro = d(item.acrescimos.seguro or "0")
            outras = d(item.acrescimos.outrasDespesas or "0")
        else:
            frete = seguro = outras = Decimal("0")

        base = valor_item - desconto + frete + seguro + outras
        tributo = q2(base * carga_pct / CEM)

        itens_atual.append(
            {
                "numero": item.numero,
                "base": f"{q2(base):.2f}",
                "cargaEfetivaPct": f"{carga_pct:.4f}",
                "tributoAtual": f"{tributo:.2f}",
            }
        )
        base_total += q2(base)
        tributos_total += tributo

    carga_media = (
        (tributos_total / base_total * CEM) if base_total > 0 else Decimal("0")
    )

    return {
        "itens": itens_atual,
        "totais": {
            "base": f"{q2(base_total):.2f}",
            "tributos": f"{q2(tributos_total):.2f}",
            "cargaMediaPct": f"{carga_media.quantize(Decimal('0.0001')):.4f}",
        },
    }


def simular(req: CalcularRequest, ruleset: Dict[str, Any]) -> Dict[str, Any]:
    """Roda os dois cenários e produz o delta."""
    atual = calcular_atual(req, ruleset)
    itens_nova, totais_nova, _avisos = calcular(req, ruleset)

    # Deltas por item
    itens_delta = []
    for a, n in zip(atual["itens"], itens_nova):
        t_atual = d(a["tributoAtual"])
        t_nova = q2(d(n.cbs.valor) + d(n.ibs.valor) + (d(n.impostoSeletivo.valor) if n.impostoSeletivo else Decimal("0")))
        delta = t_nova - t_atual
        pct = (delta / t_atual * CEM) if t_atual > 0 else Decimal("0")
        itens_delta.append(
            {
                "numero": a["numero"],
                "base": a["base"],
                "tributoAtual": a["tributoAtual"],
                "tributoNovo": f"{t_nova:.2f}",
                "delta": f"{delta:.2f}",
                "deltaPct": f"{pct.quantize(Decimal('0.01')):.2f}",
            }
        )

    # Totais delta
    t_atual = d(atual["totais"]["tributos"])
    # Reforma: CBS + IBS + IS
    t_nova_total = q2(d(totais_nova.cbs) + d(totais_nova.ibs) + d(totais_nova.impostoSeletivo))
    delta_total = t_nova_total - t_atual
    delta_pct_total = (delta_total / t_atual * CEM) if t_atual > 0 else Decimal("0")

    return {
        "atual": atual,
        "nova": {
            "itens": [i.model_dump() for i in itens_nova],
            "totais": totais_nova.model_dump(),
        },
        "delta": {
            "itens": itens_delta,
            "totais": {
                "tributoAtual": f"{t_atual:.2f}",
                "tributoNovo": f"{t_nova_total:.2f}",
                "delta": f"{delta_total:.2f}",
                "deltaPct": f"{delta_pct_total.quantize(Decimal('0.01')):.2f}",
            },
        },
    }
