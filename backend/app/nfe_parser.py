"""Parser mínimo de NF-e (extração de itens IBS/CBS + chave de acesso).

Foco no MVP: entender um subset realista do layout NF-e 2026 (NT 2024.002)
com grupos `IBSCBS`, `IS`, `emit`, `dest`, `det/prod`. Formatos ausentes são
tolerados; a validação real é feita pelo motor de cálculo depois.
"""
from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from xml.etree import ElementTree as ET

_NS_RE = re.compile(r"^\{.*?\}")


def _strip_ns(tag: str) -> str:
    return _NS_RE.sub("", tag)


def _find(elem: ET.Element, path: List[str]) -> Optional[ET.Element]:
    cur: Optional[ET.Element] = elem
    for name in path:
        if cur is None:
            return None
        found = None
        for child in cur:
            if _strip_ns(child.tag) == name:
                found = child
                break
        cur = found
    return cur


def _text(elem: Optional[ET.Element], path: List[str]) -> Optional[str]:
    if elem is None:
        return None
    node = _find(elem, path)
    return node.text.strip() if node is not None and node.text else None


def _all(elem: ET.Element, name: str) -> List[ET.Element]:
    return [c for c in elem if _strip_ns(c.tag) == name]


class NFeParseError(Exception):
    pass


def parse_nfe(xml_bytes: bytes) -> Dict[str, Any]:
    """Parse de um XML de NF-e e retorna um dict "canônico" para persistência
    e uso pelo motor de cálculo. Estrutura:
      {
        chaveAcesso, dataEmissao, natOp,
        emitente: {cnpj, xNome, uf},
        destinatario: {cnpj|cpf, xNome, uf, ie},
        itens: [
          {
            numero, cProd, xProd, ncm, cst?, quantidade, valorUnitario, valorItem,
            impostoSeletivo?: {aliquota, valor},
            ibscbs?: {vBC, pCBS?, vCBS?, pIBSUF?, vIBSUF?, pIBSMun?, vIBSMun?}
          }
        ]
      }
    """
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        raise NFeParseError(f"XML inválido: {e}") from e

    # NFe pode vir "nua" (<NFe>) ou envelopada em <nfeProc>
    if _strip_ns(root.tag) == "nfeProc":
        nfe = _find(root, ["NFe"])
    elif _strip_ns(root.tag) == "NFe":
        nfe = root
    else:
        raise NFeParseError(f"raiz inesperada: <{_strip_ns(root.tag)}>")

    if nfe is None:
        raise NFeParseError("elemento <NFe> não encontrado")
    inf = _find(nfe, ["infNFe"])
    if inf is None:
        raise NFeParseError("elemento <infNFe> não encontrado")

    # Chave de acesso: infNFe/@Id = "NFe" + 44 dígitos
    chave = inf.attrib.get("Id", "")
    if chave.startswith("NFe"):
        chave = chave[3:]
    if not re.fullmatch(r"\d{44}", chave):
        raise NFeParseError(f"chave de acesso inválida (esperado 44 dígitos): {chave!r}")

    ide = _find(inf, ["ide"])
    dh = _text(ide, ["dhEmi"]) or _text(ide, ["dEmi"])
    if not dh:
        raise NFeParseError("data de emissão ausente")
    try:
        data_emissao = _parse_datetime(dh)
    except Exception as e:
        raise NFeParseError(f"data de emissão inválida: {dh!r}") from e
    nat_op = _text(ide, ["natOp"])

    emit = _find(inf, ["emit"])
    dest = _find(inf, ["dest"])

    emitente = {
        "cnpj": _text(emit, ["CNPJ"]) or _text(emit, ["CPF"]),
        "xNome": _text(emit, ["xNome"]),
        "uf": _text(emit, ["enderEmit", "UF"]),
    }
    destinatario = {
        "cnpj": _text(dest, ["CNPJ"]) or _text(dest, ["CPF"]),
        "xNome": _text(dest, ["xNome"]),
        "uf": _text(dest, ["enderDest", "UF"]),
    }

    itens = []
    for det in _all(inf, "det"):
        prod = _find(det, ["prod"])
        imposto = _find(det, ["imposto"])
        item = {
            "numero": int(det.attrib.get("nItem", "0") or 0),
            "cProd": _text(prod, ["cProd"]),
            "xProd": _text(prod, ["xProd"]),
            "ncm": _text(prod, ["NCM"]),
            "quantidade": _text(prod, ["qCom"]) or "1.00",
            "valorUnitario": _text(prod, ["vUnCom"]) or "0.00",
            "valorItem": _text(prod, ["vProd"]) or "0.00",
        }

        # Grupo IBS/CBS (NT 2024.002) — pode vir como <IBSCBS> ou grupos <CBS>/<IBS>
        ibscbs_group = _find(imposto, ["IBSCBS"])
        ibscbs = {}
        if ibscbs_group is not None:
            ibscbs["vBC"] = _text(ibscbs_group, ["vBC"])
            cbs = _find(ibscbs_group, ["CBS"])
            if cbs is not None:
                ibscbs["pCBS"] = _text(cbs, ["pCBS"])
                ibscbs["vCBS"] = _text(cbs, ["vCBS"])
            ibs = _find(ibscbs_group, ["IBS"])
            if ibs is not None:
                ibsuf = _find(ibs, ["gIBSUF"]) or ibs
                ibsmun = _find(ibs, ["gIBSMun"]) or ibs
                ibscbs["pIBSUF"] = _text(ibsuf, ["pIBSUF"]) or _text(ibsuf, ["pIBS"])
                ibscbs["vIBSUF"] = _text(ibsuf, ["vIBSUF"]) or _text(ibsuf, ["vIBS"])
                ibscbs["pIBSMun"] = _text(ibsmun, ["pIBSMun"])
                ibscbs["vIBSMun"] = _text(ibsmun, ["vIBSMun"])
                ibscbs["cst"] = _text(ibs, ["CST"]) or _text(ibscbs_group, ["CST"])
                ibscbs["cClassTrib"] = _text(ibs, ["cClassTrib"]) or _text(
                    ibscbs_group, ["cClassTrib"]
                )
        if ibscbs:
            item["ibscbs"] = ibscbs
            if ibscbs.get("cst"):
                item["cst"] = ibscbs["cst"]
            if ibscbs.get("cClassTrib"):
                item["cClassTrib"] = ibscbs["cClassTrib"]

        # Imposto Seletivo (grupo IS)
        is_group = _find(imposto, ["IS"])
        if is_group is not None:
            aliq = _text(is_group, ["pIS"])
            valor = _text(is_group, ["vIS"])
            if aliq or valor:
                item["impostoSeletivo"] = {
                    "aliquota": aliq or "0.0000",
                    "valor": valor or "0.00",
                    "cst": _text(is_group, ["CST"]),
                }
        itens.append(item)

    if not itens:
        raise NFeParseError("nenhum item encontrado (<det>)")

    total = _find(inf, ["total"])
    valor_total = _text(total, ["ICMSTot", "vNF"]) or _text(total, ["IBSCBSTot", "vNF"])

    return {
        "chaveAcesso": chave,
        "dataEmissao": data_emissao.isoformat(),
        "dataOperacao": data_emissao.date().isoformat(),
        "natOp": nat_op,
        "emitente": emitente,
        "destinatario": destinatario,
        "itens": itens,
        "valorTotal": valor_total,
    }


def _parse_datetime(s: str) -> datetime:
    # Aceita 2026-08-26T10:00:00-03:00, 2026-08-26T10:00:00, 2026-08-26
    s = s.strip()
    if len(s) == 10:
        return datetime.fromisoformat(s + "T00:00:00")
    return datetime.fromisoformat(s)
