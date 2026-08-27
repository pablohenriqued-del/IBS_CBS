"""Modelos Pydantic para o contrato POST /v1/calcular.

Todos os valores monetários trafegam como string decimal.
Internamente, o motor converte para Decimal.
"""
from __future__ import annotations

from datetime import date
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class Estabelecimento(BaseModel):
    cnpj: str
    uf: str
    municipioIBGE: str
    regime: Literal["regular", "simples", "mei"]


class Destinatario(BaseModel):
    uf: str
    municipioIBGE: str
    consumidorFinal: bool
    contribuinte: bool


class Operacao(BaseModel):
    tipo: Literal["venda", "transferencia", "devolucao", "servico"]


class Acrescimos(BaseModel):
    frete: Optional[str] = "0.00"
    seguro: Optional[str] = "0.00"
    outrasDespesas: Optional[str] = "0.00"


class ImpostoSeletivoIn(BaseModel):
    aliquota: str
    cst: Optional[str] = None


class Item(BaseModel):
    numero: int
    descricao: Optional[str] = None
    ncm: Optional[str] = None
    nbs: Optional[str] = None
    cClassTrib: str
    cst: Optional[str] = None
    quantidade: str
    valorUnitario: str
    valorItem: str
    descontoIncondicional: Optional[str] = "0.00"
    acrescimos: Optional[Acrescimos] = None
    impostoSeletivo: Optional[ImpostoSeletivoIn] = None


class CalcularRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    referencia: str
    dataOperacao: date
    modo: Literal["producao", "homologacao"]
    estabelecimento: Estabelecimento
    destinatario: Destinatario
    operacao: Operacao
    itens: List[Item] = Field(min_length=1)


# ------------------- Response -------------------


class CBSOut(BaseModel):
    cst: str
    aliquotaNominal: str
    reducao: str
    aliquotaEfetiva: str
    valor: str


class IBSComponente(BaseModel):
    aliquota: str
    valor: str


class IBSOut(BaseModel):
    cst: str
    reducao: str
    uf: IBSComponente
    municipio: IBSComponente
    valor: str


class ISOut(BaseModel):
    base: str
    aliquota: str
    valor: str


class ItemOut(BaseModel):
    numero: int
    base: str
    impostoSeletivo: Optional[ISOut] = None
    cbs: CBSOut
    ibs: IBSOut
    totalItem: str
    memoriaCalculo: List[str]


class Totais(BaseModel):
    baseTotal: str
    impostoSeletivo: str
    cbs: str
    ibsUF: str
    ibsMunicipio: str
    ibs: str
    tributosTotais: str


class CalcularResponse(BaseModel):
    referencia: str
    rulesetId: str
    rulesetHash: str
    motorVersao: str
    calculadoEm: str
    moeda: str = "BRL"
    arredondamento: str = "2 casas, meio-para-cima"
    itens: List[ItemOut]
    totais: Totais
    avisos: List[str] = []
    auditoriaId: str


# ------------------- Erros -------------------


class ErroDetalhe(BaseModel):
    campo: str
    codigo: str
    mensagem: str


class ErroResponse(BaseModel):
    erro: str
    detalhes: List[ErroDetalhe]
