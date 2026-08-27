"""Motor de cálculo IBS/CBS.

Princípios inegociáveis:
  1. Tudo em Decimal — NUNCA float.
  2. Base "por fora": IBS e CBS incidem sobre uma base que NÃO inclui os
     próprios tributos, nem um ao outro.
  3. Imposto Seletivo ENTRA na base de IBS/CBS quando houver.
  4. Regras são dado versionado; o motor recebe o ruleset já resolvido.
  5. Arredondamento monetário: 2 casas, meio-para-cima (ROUND_HALF_UP).
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Tuple

from .models import (
    CBSOut,
    CalcularRequest,
    IBSComponente,
    IBSOut,
    ISOut,
    Item,
    ItemOut,
    Totais,
)

TWO_PLACES = Decimal("0.01")
FOUR_PLACES = Decimal("0.0001")
CEM = Decimal("100")


def d(x: str | int | float | Decimal | None) -> Decimal:
    """Converte input em Decimal de forma segura. Aceita None → 0."""
    if x is None:
        return Decimal("0")
    if isinstance(x, Decimal):
        return x
    # NUNCA passar por float: se vier float por acidente, str(float) preserva
    # o texto exato do input; mas o contrato exige string decimal, então
    # aqui aceitamos apenas str/int/Decimal em uso real.
    return Decimal(str(x))


def q2(x: Decimal) -> Decimal:
    """Arredonda para 2 casas, meio-para-cima."""
    return x.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def q4(x: Decimal) -> Decimal:
    """Arredonda alíquota para 4 casas."""
    return x.quantize(FOUR_PLACES, rounding=ROUND_HALF_UP)


def _fmt2(x: Decimal) -> str:
    return f"{q2(x):.2f}"


def _fmt4(x: Decimal) -> str:
    return f"{q4(x):.4f}"


# --------------------------------------------------------------------------
# Núcleo de cálculo por item
# --------------------------------------------------------------------------


def calcular_item(item: Item, ruleset: Dict[str, Any]) -> Tuple[ItemOut, List[str]]:
    """Calcula os tributos de um item.

    Retorna (ItemOut, avisos_do_item).
    """
    avisos_item: List[str] = []
    memoria: List[str] = []

    # --- 1. Componentes da base "por fora" ---
    valor_item = d(item.valorItem)
    desconto = d(item.descontoIncondicional or "0")
    if item.acrescimos:
        frete = d(item.acrescimos.frete or "0")
        seguro = d(item.acrescimos.seguro or "0")
        outras = d(item.acrescimos.outrasDespesas or "0")
    else:
        frete = seguro = outras = Decimal("0")
    acrescimos_total = frete + seguro + outras

    base_sem_is = valor_item - desconto + acrescimos_total

    # --- 2. Imposto Seletivo (se houver) ENTRA na base ---
    is_out = None
    if item.impostoSeletivo is not None:
        aliq_is = d(item.impostoSeletivo.aliquota)
        valor_is = q2(base_sem_is * aliq_is / CEM)
        is_out = ISOut(
            base=_fmt2(base_sem_is),
            aliquota=_fmt4(aliq_is),
            valor=_fmt2(valor_is),
        )
        base = base_sem_is + valor_is
        memoria.append(
            f"Imposto Seletivo = {_fmt2(base_sem_is)} × {_fmt4(aliq_is)}% = {_fmt2(valor_is)}"
        )
        memoria.append(
            f"Base IBS/CBS = {_fmt2(base_sem_is)} (valor) + {_fmt2(valor_is)} (IS) = {_fmt2(base)}   ← IS entra na base"
        )
    else:
        base = base_sem_is
        memoria.append(
            f"Base = {_fmt2(valor_item)} − {_fmt2(desconto)} (desc.) + {_fmt2(acrescimos_total)} (acresc.) + 0.00 (IS) = {_fmt2(base)}"
        )

    # --- 3. Resolve cClassTrib no ruleset ---
    classe = ruleset["cClassTrib"].get(item.cClassTrib)
    if classe is None:
        # Regra de ouro: em dúvida, falhar explicitamente.
        raise CClassTribDesconhecido(item.numero, item.cClassTrib, ruleset["id"])

    cst = item.cst or classe["cst"]
    reducao_pct = d(classe["reducao"])  # ex.: "60.0000"
    fator = (CEM - reducao_pct) / CEM  # ex.: 0.4000

    if item.impostoSeletivo is None:
        memoria.append(
            f"cClassTrib {item.cClassTrib} → {classe['descricao']} (CST {cst}), fator de redução {_fmt4(fator)}"
        )

    # --- 4. CBS ---
    cbs_nominal = d(ruleset["cbs"]["aliquotaNominal"])
    cbs_efetiva = cbs_nominal * fator  # em %
    valor_cbs = q2(base * cbs_efetiva / CEM)

    if reducao_pct > 0:
        memoria.append(
            f"CBS: {_fmt4(cbs_nominal)}% × {_fmt4(fator)} = {_fmt4(cbs_efetiva)}% → {_fmt2(base)} × {_fmt4(cbs_efetiva)}% = {_fmt2(valor_cbs)}"
        )
    else:
        memoria.append(
            f"CBS = {_fmt2(base)} × {_fmt4(cbs_nominal)}% × {_fmt4(fator)} = {_fmt2(valor_cbs)}"
        )

    cbs_out = CBSOut(
        cst=cst,
        aliquotaNominal=_fmt4(cbs_nominal),
        reducao=_fmt4(reducao_pct),
        aliquotaEfetiva=_fmt4(cbs_efetiva),
        valor=_fmt2(valor_cbs),
    )

    # --- 5. IBS (partilhado UF + Município) ---
    aliq_uf_nominal = d(ruleset["ibs"]["aliquotaUF"])
    aliq_mun_nominal = d(ruleset["ibs"]["aliquotaMunicipio"])

    aliq_uf_ef = aliq_uf_nominal * fator
    aliq_mun_ef = aliq_mun_nominal * fator

    valor_ibs_uf = q2(base * aliq_uf_ef / CEM)
    valor_ibs_mun = q2(base * aliq_mun_ef / CEM)
    valor_ibs = valor_ibs_uf + valor_ibs_mun

    if reducao_pct > 0:
        memoria.append(
            f"IBS-UF: {_fmt4(aliq_uf_nominal)}% × {_fmt4(fator)} = {_fmt4(aliq_uf_ef)}% → {_fmt2(base)} × {_fmt4(aliq_uf_ef)}% = {_fmt2(valor_ibs_uf)}"
        )
        memoria.append(
            f"IBS-Mun: {_fmt4(aliq_mun_nominal)}% × {_fmt4(fator)} = {_fmt4(aliq_mun_ef)}% → {_fmt2(base)} × {_fmt4(aliq_mun_ef)}% = {_fmt2(valor_ibs_mun)}"
        )
    else:
        memoria.append(f"IBS-UF = {_fmt2(base)} × {_fmt4(aliq_uf_ef)}% = {_fmt2(valor_ibs_uf)}")
        memoria.append(f"IBS-Mun = {_fmt2(base)} × {_fmt4(aliq_mun_ef)}% = {_fmt2(valor_ibs_mun)}")
    memoria.append(f"IBS total = {_fmt2(valor_ibs_uf)} + {_fmt2(valor_ibs_mun)} = {_fmt2(valor_ibs)}")

    ibs_out = IBSOut(
        cst=cst,
        reducao=_fmt4(reducao_pct),
        uf=IBSComponente(aliquota=_fmt4(aliq_uf_ef), valor=_fmt2(valor_ibs_uf)),
        municipio=IBSComponente(aliquota=_fmt4(aliq_mun_ef), valor=_fmt2(valor_ibs_mun)),
        valor=_fmt2(valor_ibs),
    )

    # --- 6. Total do item = base "por fora" + tributos ---
    # No modelo "por fora", o total pago pelo consumidor é base + CBS + IBS
    # (o IS já está dentro da base, então some-se apenas o excedente de
    # tributos "por fora"). Reproduzimos o que o exemplo do contrato mostra:
    # item 3 → 220 (base) − 200 (valorItem) + 19.36 + 38.94 = 78.30 → aqui
    # totalItem representa a soma de tributos + IS do item (a "carga"),
    # não o "gross-up" da mercadoria.
    total_item = q2(valor_cbs + valor_ibs)
    if is_out is not None:
        total_item = q2(total_item + d(is_out.valor))

    item_out = ItemOut(
        numero=item.numero,
        base=_fmt2(base),
        impostoSeletivo=is_out,
        cbs=cbs_out,
        ibs=ibs_out,
        totalItem=_fmt2(total_item),
        memoriaCalculo=memoria,
    )
    return item_out, avisos_item


# --------------------------------------------------------------------------
# Motor completo (todos os itens + totais)
# --------------------------------------------------------------------------


def calcular(req: CalcularRequest, ruleset: Dict[str, Any]) -> Tuple[List[ItemOut], Totais, List[str]]:
    itens_out: List[ItemOut] = []
    avisos: List[str] = list(ruleset.get("avisos", []))

    base_total = Decimal("0")
    is_total = Decimal("0")
    cbs_total = Decimal("0")
    ibs_uf_total = Decimal("0")
    ibs_mun_total = Decimal("0")

    for item in req.itens:
        item_out, avisos_item = calcular_item(item, ruleset)
        itens_out.append(item_out)
        avisos.extend(avisos_item)

        base_total += d(item_out.base)
        if item_out.impostoSeletivo:
            is_total += d(item_out.impostoSeletivo.valor)
        cbs_total += d(item_out.cbs.valor)
        ibs_uf_total += d(item_out.ibs.uf.valor)
        ibs_mun_total += d(item_out.ibs.municipio.valor)

    ibs_total = ibs_uf_total + ibs_mun_total
    # tributosTotais = CBS + IBS (o IS é apresentado separadamente nos totais,
    # conforme o contrato — apesar de já compor a base de IBS/CBS via item).
    tributos_totais = cbs_total + ibs_total

    totais = Totais(
        baseTotal=_fmt2(base_total),
        impostoSeletivo=_fmt2(is_total),
        cbs=_fmt2(cbs_total),
        ibsUF=_fmt2(ibs_uf_total),
        ibsMunicipio=_fmt2(ibs_mun_total),
        ibs=_fmt2(ibs_total),
        tributosTotais=_fmt2(tributos_totais),
    )
    return itens_out, totais, avisos


# --------------------------------------------------------------------------
# Exceções de domínio
# --------------------------------------------------------------------------


class CClassTribDesconhecido(Exception):
    def __init__(self, numero_item: int, codigo: str, ruleset_id: str):
        self.numero_item = numero_item
        self.codigo = codigo
        self.ruleset_id = ruleset_id
        super().__init__(
            f"cClassTrib {codigo} não encontrado no ruleset {ruleset_id} (item {numero_item})."
        )


class SemRulesetVigente(Exception):
    def __init__(self, data_operacao: str):
        self.data_operacao = data_operacao
        super().__init__(f"Nenhum ruleset vigente para a data {data_operacao}.")
