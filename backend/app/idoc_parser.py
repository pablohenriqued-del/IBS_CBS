"""Parser IDOC INVOIC02 (inbound SAP → FiscalCore).

Suporta o formato XML do IDOC INVOIC02 exportado pelo S/4HANA (WE60/WE19).
Segmentos aceitos:

- EDI_DC40           control record (docnum, mestyp, idoctp)
- E1EDK01            invoice header (currency, docnum, exchange rate)
- E1EDK14            organizational reference (qualifier + org value)
- E1EDP01            invoice line item (POSEX, MENGE, MENEE, NETWR, VPREI)
- E1EDP19            item reference / material (QUALF=001 → IDTNR)
- E1EDP04            item taxes (MWSKZ tax code, MSATZ rate, MWSBT value)
- E1EDS01            summary segment (SUMID=001 net, 010 tax, 011 gross)
- Z1FISC_CLASTRIB    (extensão custom)  cClassTrib do FiscalCore

O parser é tolerante: campos ausentes viram None; nunca lança se o XML for
válido. `parse_idoc_bytes` retorna dict canônico consumível pelo /reconciliar.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from xml.etree import ElementTree as ET

_NS_RE = re.compile(r"^\{.*?\}")


def _strip_ns(tag: str) -> str:
    return _NS_RE.sub("", tag)


def _text(elem: Optional[ET.Element], name: str) -> Optional[str]:
    if elem is None:
        return None
    for c in elem:
        if _strip_ns(c.tag) == name:
            return (c.text or "").strip() or None
    return None


def _children(elem: ET.Element, name: str) -> List[ET.Element]:
    return [c for c in elem if _strip_ns(c.tag) == name]


class IdocParseError(Exception):
    pass


def parse_idoc_bytes(xml_bytes: bytes) -> Dict[str, Any]:
    """Parse de IDOC INVOIC02 XML → dict canônico.

    Estrutura devolvida:
      {
        "mestyp": "INVOIC",
        "idoctp": "INVOIC02",
        "docnum": "0000000012345",
        "currency": "BRL",
        "belnr": "0001234567",
        "itens": [
          {
            "kposn": 10, "matnr": "MAT-001", "arktx": "...",
            "menge": "1.000", "meins": "PC",
            "netwr": "1000.00", "vprei": "1000.00",
            "cClassTrib": "000001",
            "taxes": [
              {"mwskz": "Z1", "msatz": "8.80", "mwsbt": "88.00", "kschl": "ZCBS"},
              ...
            ]
          }
        ],
        "summary": {"net": "...", "tax": "...", "gross": "..."}
      }
    """
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        raise IdocParseError(f"XML inválido: {e}") from e

    # Aceita <INVOIC02> como root ou envelope
    if _strip_ns(root.tag) == "INVOIC02":
        idoc = None
        for c in root:
            if _strip_ns(c.tag) == "IDOC":
                idoc = c
                break
        if idoc is None:
            raise IdocParseError("Elemento <IDOC> não encontrado em <INVOIC02>")
    elif _strip_ns(root.tag) == "IDOC":
        idoc = root
    else:
        raise IdocParseError(
            f"raiz inesperada: <{_strip_ns(root.tag)}> (esperado INVOIC02 ou IDOC)"
        )

    control = None
    header = None
    for c in idoc:
        tag = _strip_ns(c.tag)
        if tag == "EDI_DC40":
            control = c
        elif tag == "E1EDK01":
            header = c

    mestyp = _text(control, "MESTYP") if control is not None else None
    idoctp = _text(control, "IDOCTP") if control is not None else None
    docnum = _text(control, "DOCNUM") if control is not None else None
    currency = _text(header, "CURCY") if header is not None else None
    belnr = _text(header, "BELNR") if header is not None else None

    # Itens
    itens: List[Dict[str, Any]] = []
    for p01 in _children(idoc, "E1EDP01"):
        # Ref material
        matnr = None
        arktx = None
        for p19 in _children(p01, "E1EDP19"):
            qualf = _text(p19, "QUALF")
            if qualf == "001" and matnr is None:
                matnr = _text(p19, "IDTNR")
                arktx = _text(p19, "KTEXT") or arktx
            elif arktx is None:
                arktx = _text(p19, "KTEXT")

        # Impostos (múltiplos E1EDP04)
        taxes: List[Dict[str, Any]] = []
        for p04 in _children(p01, "E1EDP04"):
            taxes.append(
                {
                    "mwskz": _text(p04, "MWSKZ"),
                    "msatz": _text(p04, "MSATZ"),
                    "mwsbt": _text(p04, "MWSBT"),
                    # Extensão nossa: TXJCD carrega a kschl real (ZCBS/ZIBU/ZIBM/ZISE)
                    "kschl": _text(p04, "TXJCD") or _text(p04, "MWSKZ"),
                }
            )

        # Extensão custom Z1FISC_CLASTRIB
        cclasstrib = None
        for ext in _children(p01, "Z1FISC_CLASTRIB"):
            cclasstrib = _text(ext, "CCLASSTRIB") or cclasstrib

        # KPOSN normalmente "000010" → int 10
        posex_raw = _text(p01, "POSEX") or "0"
        try:
            kposn = int(posex_raw)
        except ValueError:
            kposn = 0

        itens.append(
            {
                "kposn": kposn,
                "matnr": matnr,
                "arktx": arktx,
                "menge": _text(p01, "MENGE"),
                "meins": _text(p01, "MENEE"),
                "netwr": _text(p01, "NETWR"),
                "vprei": _text(p01, "VPREI"),
                "cClassTrib": cclasstrib,
                "taxes": taxes,
            }
        )

    # Summary (E1EDS01)
    summary: Dict[str, str] = {}
    _SUMID_MAP = {"001": "net", "010": "tax", "011": "gross"}
    for s01 in _children(idoc, "E1EDS01"):
        sumid = _text(s01, "SUMID")
        summe = _text(s01, "SUMME")
        key = _SUMID_MAP.get(sumid or "")
        if key and summe:
            summary[key] = summe

    if not itens:
        raise IdocParseError("nenhum item encontrado (<E1EDP01>)")

    return {
        "mestyp": mestyp,
        "idoctp": idoctp,
        "docnum": docnum,
        "currency": currency,
        "belnr": belnr,
        "itens": itens,
        "summary": summary,
    }
