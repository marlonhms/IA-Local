"""
Motor Fiscal, Tributario e Contabil Determinístico da AURA (core/fiscal_engine.py).
Integrado a partir do Agent Sefaz com principios de Zero Alucinacao:
1. Validador de Chaves de Acesso de NF-e e NFC-e (Modulo 11 e decomposicao de 44 digitos)
2. Motor Matematico ABNT NBR 5891:2014 (ROUND_HALF_UP com tolerancia de R$ 0,01)
3. Auditoria de Regras Fiscais e Tributarias de Postos e Combustiveis:
   - Regra I08-10 / Rejeicao 629 (Multiplicacao qCom * vUnCom no bico de abastecimento)
   - Regra W07-10 / Rejeicao 531 (Somatorio de itens vs vProd) e Projecao de Cascata
   - Regra W16-10 / Rejeicao 535 (Composicao do vNF)
   - Regra SEFAZ-VAL-NEG (Bloqueio de valores monetarios negativos no ACBr)
   - Regra I08-180 / Rejeicao 375 (CFOP 5929/6929 x NFC-e mod 65 x webPosto versao 26.9)
   - Regra BA02 / Rejeicao 701 (Documento referenciado x SPED C113)
   - Rejeicoes 508, 600, 529 e 805 (indIEDest x CST/CSOSN x UFs que vedam Isento)
   - Rejeicoes 694, 695, 697 e 698 (DIFAL x Excecoes de combustiveis derivados de petroleo ANP)
   - Rejeicao 960 (Combustivel monofasico LC 192/2022 exigindo CST 61)
   - Rejeicao 958 (CFOP incompativel com combustivel monofasico)
   - Rejeicao 959 (Etanol hidratado vedado em CST 61)
   - Rejeicao 806 (CEST compulsorio para produtos com ST/Monofasico)
   - Alerta Contabil Bitributacao PIS/COFINS (Tabela 4.3.10 EFD-Contribuicoes : CST 04)
   - Protocolo SEFAZ (SEFAZ-PROT-01: identificacao de notas em rascunho sem autorizacao)

Regra inegociavel: ZERO travessoes em todo o arquivo.
"""

from __future__ import annotations

import html
import logging
import re
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import defusedxml.minidom
from lxml import etree
from pydantic import BaseModel, Field

logger = logging.getLogger("aura.fiscal_engine")

TOLERANCIA_CENTAVO = Decimal("0.01")
ROUND_2 = Decimal("0.01")
ROUND_4 = Decimal("0.0001")

UF_IBGE_CODES: Dict[str, str] = {
    "11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP", "17": "TO",
    "21": "MA", "22": "PI", "23": "CE", "24": "RN", "25": "PB", "26": "PE", "27": "AL",
    "28": "SE", "29": "BA", "31": "MG", "32": "ES", "33": "RJ", "35": "SP",
    "41": "PR", "42": "SC", "43": "RS", "50": "MS", "51": "MT", "52": "GO", "53": "DF",
}

UFS_VEDAM_ISENTO = {
    "AM", "BA", "CE", "GO", "MG", "MS", "MT", "PA", "PE", "RN", "SE", "SP"
}

UFS_SUL_SUDESTE_EXCETO_ES = {"PR", "RS", "SC", "SP", "MG", "RJ"}
UFS_NORTE_NORDESTE_CENTROOESTE_ES = {
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA",
    "MS", "MT", "PA", "PB", "PE", "PI", "RN", "RO", "RR", "SE", "TO"
}

ORIGENS_IMPORTADAS = {"1", "2", "3", "8"}
ORIGENS_NACIONAIS = {"0", "4", "5", "6", "7"}

ANP_NAO_DERIVADOS_PETROLEO = {
    "810101001", "810101002", "810101003", "810102001", "810102002", "810102003",
    "810102004", "820101001", "820101010", "220101001", "220101002", "220101003",
    "220101004", "220101005", "220101006"
}

ANP_COMBUSTIVEIS_MONOFASICOS_ICMS = {
    "320102001",  # Gasolina Comum
    "320102002",  # Gasolina Aditivada
    "320102003",  # Gasolina Premium
    "320102005",  # Gasolina de Aviacao
    "820101034",  # Diesel S10
    "820101033",  # Diesel S500
    "820101012",  # Diesel Maritimo
    "820101013",  # Diesel S10 Maritimo
    "820101014",  # Diesel S500 Maritimo
    "210203001",  # GLP
}

ANP_ETANOL_HIDRATADO = {
    "810101001",  # Etanol Hidratado Comum
    "810101002",  # Etanol Hidratado Aditivado
}

# NCMs com Tributacao Monofasica de PIS/COFINS (Tabela 4.3.10 EFD-Contribuicoes e combustiveis)
# O revendedor varejista (posto/conveniencia) deve aplicar CST 04 (Aliquota Zero no Varejo)
NCMS_MONOFASICOS_PIS_COFINS = {
    # Bebidas Frias (Lei 13.097/2015)
    "22011000",  # Aguas minerais e potaveis
    "22021000",  # Refrigerantes e aguas aromatizadas
    "22029900",  # Energeticos, chas prontos, isotonicos
    "22030000",  # Cervejas de malte
    # Cigarros e Tabacos (Lei 9.532/1997)
    "24022000",  # Cigarros de tabaco
    # Combustiveis Automotivos (Lei 9.718/1998 e Lei 9.990/2000)
    "27101259",  # Gasolinas
    "27101921",  # Oleo Diesel
    "22071090",  # Etanol combustivel
    "27111910",  # GLP
    # Lubrificantes
    "27101932",  # Oleos lubrificantes
}

# Tabela de CESTs compulsorios para produtos com ST e Monofasico em postos (Convenio 142/2018)
CESTS_OBRIGATORIOS_POSTO: Dict[str, str] = {
    "27101259": "06.001.00",  # Gasolinas
    "27101921": "06.002.00",  # Oleo Diesel
    "22071090": "06.004.00",  # Etanol
    "27111910": "06.006.00",  # GLP
    "27101932": "06.007.00",  # Oleos lubrificantes
    "22011000": "03.001.00",  # Aguas minerais
    "22021000": "03.003.00",  # Refrigerantes
    "22030000": "03.010.00",  # Cervejas
}


class StatusApontamento(str, Enum):
    VALID = "VALID"
    INVALID = "INVALID"
    WARNING = "WARNING"


class GravidadeApontamento(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    INFO = "INFO"


class ApontamentoFiscal(BaseModel):
    """Contrato universal de diagnostico com explicabilidade dupla (executiva e tecnica)."""
    status: StatusApontamento
    gravidade: GravidadeApontamento
    regra_id: str
    titulo: str
    explicacao_executiva: str = Field(description="Explicacao direta e clara para o dono do posto tomar decisao.")
    explicacao_tecnica: str = Field(description="Explicacao tecnica com tags XML para o contador ou suporte.")
    campos_afetados: List[str] = Field(default_factory=list)
    valor_esperado: Optional[str] = None
    valor_observado: Optional[str] = None
    base_legal: List[str] = Field(default_factory=list)
    acoes_recomendadas: List[str] = Field(default_factory=list)
    confianca: float = 1.0


def round_abnt(val: Decimal, precision: Decimal = ROUND_2) -> Decimal:
    """Arredondamento aritmetico decimal aderente a ABNT NBR 5891:2014 e SEFAZ."""
    return val.quantize(precision, rounding=ROUND_HALF_UP)


def calcular_dv_modulo_11(base_43: str) -> int:
    """
    Calcula o Digito Verificador (DV) da chave de acesso da NF-e por modulo 11.
    Pesos 2 a 9 da direita para a esquerda sobre os primeiros 43 digitos.
    """
    clean_base = re.sub(r"[^0-9]", "", str(base_43))
    if len(clean_base) != 43:
        raise ValueError(f"Base para calculo de DV da NF-e deve ter 43 digitos, recebido {len(clean_base)}.")

    pesos = [2, 3, 4, 5, 6, 7, 8, 9]
    soma = 0
    for idx, digito in enumerate(reversed(clean_base)):
        peso = pesos[idx % len(pesos)]
        soma += int(digito) * peso

    resto = soma % 11
    return 0 if resto in (0, 1) else 11 - resto


def decompor_chave_acesso(chave: str) -> Dict[str, Any]:
    """Decompoe chave de 44 digitos nos campos oficiais SEFAZ."""
    clean_key = re.sub(r"[^0-9]", "", str(chave))
    if len(clean_key) != 44:
        raise ValueError(f"Chave de acesso deve conter exatamente 44 digitos, recebido {len(clean_key)}.")

    base_43 = clean_key[:43]
    dv_observado = clean_key[43]
    calc_dv = calcular_dv_modulo_11(base_43)

    c_uf = clean_key[0:2]
    aamm = clean_key[2:6]
    ano = aamm[0:2]
    mes = aamm[2:4]
    cnpj = clean_key[6:20]
    modelo = clean_key[20:22]
    serie = clean_key[22:25]
    n_nf = clean_key[25:34]
    tp_emis = clean_key[34:35]
    c_nf = clean_key[35:43]

    uf_sigla = UF_IBGE_CODES.get(c_uf)
    is_dv_valido = int(dv_observado) == calc_dv

    return {
        "chave_completa": clean_key,
        "c_uf": c_uf,
        "uf_sigla": uf_sigla,
        "aamm": aamm,
        "ano": ano,
        "mes": mes,
        "cnpj_emitente": cnpj,
        "modelo": modelo,
        "tipo_documento": "NF-e (modelo 55)" if modelo == "55" else ("NFC-e (modelo 65)" if modelo == "65" else f"Modelo {modelo}"),
        "serie": serie,
        "numero_nfe": n_nf,
        "tipo_emissao": tp_emis,
        "codigo_numerico": c_nf,
        "digito_verificador": dv_observado,
        "dv_calculado": calc_dv,
        "is_dv_valido": is_dv_valido,
    }


def validar_chave_acesso(chave: str) -> List[ApontamentoFiscal]:
    """Valida integridade e digito verificador de chave de acesso."""
    findings: List[ApontamentoFiscal] = []
    clean_key = re.sub(r"[^0-9]", "", str(chave))

    if len(clean_key) != 44:
        findings.append(
            ApontamentoFiscal(
                status=StatusApontamento.INVALID,
                gravidade=GravidadeApontamento.CRITICAL,
                regra_id="SEFAZ-CHAVE-LEN",
                titulo="Tamanho invalido para Chave de Acesso da NF-e/NFC-e",
                explicacao_executiva=f"A chave informada possui {len(clean_key)} digitos, quando o padrao oficial da SEFAZ exige exatamente 44 numeros.",
                explicacao_tecnica=f"Tamanho da chave de acesso: {len(clean_key)} caracteres. Falha de mascara ou truncamento.",
                campos_afetados=["infNFe/@Id", "chNFe"],
                valor_esperado="44 digitos",
                valor_observado=f"{len(clean_key)} digitos",
                base_legal=["MOC 7.0 - Visao Geral do Documento Fiscal Eletronico"],
                acoes_recomendadas=["Verificar a integridade do XML de origem ou o leitor de codigo de barras."],
            )
        )
        return findings

    decomp = decompor_chave_acesso(clean_key)

    if not decomp["uf_sigla"]:
        findings.append(
            ApontamentoFiscal(
                status=StatusApontamento.INVALID,
                gravidade=GravidadeApontamento.HIGH,
                regra_id="SEFAZ-REJ-226",
                titulo="Rejeicao 226: Codigo da UF do Emitente invalido na Chave de Acesso",
                explicacao_executiva=f"O codigo de estado '{decomp['c_uf']}' nos primeiros digitos da chave nao existe no Brasil.",
                explicacao_tecnica=f"Codigo IBGE cUF '{decomp['c_uf']}' invalido.",
                campos_afetados=["cUF"],
                valor_esperado="Codigo IBGE valido (ex: 35 para SP, 31 para MG)",
                valor_observado=decomp["c_uf"],
                base_legal=["MOC 7.0 Anexo I - Tabela de UF do IBGE"],
            )
        )

    if not decomp["is_dv_valido"]:
        findings.append(
            ApontamentoFiscal(
                status=StatusApontamento.INVALID,
                gravidade=GravidadeApontamento.CRITICAL,
                regra_id="SEFAZ-REJ-253",
                titulo="Rejeicao 253: Digito Verificador da Chave de Acesso invalido",
                explicacao_executiva=(
                    f"O digito final da chave informado ({decomp['digito_verificador']}) esta incorreto. "
                    f"Pela regra matematica oficial da SEFAZ (Modulo 11), o digito correto e {decomp['dv_calculado']}."
                ),
                explicacao_tecnica=(
                    f"Digito Verificador observado: {decomp['digito_verificador']}, "
                    f"mas o calculo ponderado por Modulo 11 sobre os primeiros 43 digitos resultou em {decomp['dv_calculado']}."
                ),
                campos_afetados=["infNFe/@Id", "cDV"],
                valor_esperado=str(decomp["dv_calculado"]),
                valor_observado=str(decomp["digito_verificador"]),
                base_legal=["MOC 7.0 - Calculo do Digito Verificador (Modulo 11)"],
                acoes_recomendadas=["Recalcular o digito verificador ou reemitir o arquivo XML."],
            )
        )
    else:
        findings.append(
            ApontamentoFiscal(
                status=StatusApontamento.VALID,
                gravidade=GravidadeApontamento.INFO,
                regra_id="SEFAZ-CHAVE-01",
                titulo="Chave de Acesso Valida e Autentica (Modulo 11 SEFAZ)",
                explicacao_executiva=(
                    f"Chave autentica de {decomp['tipo_documento']} emitida em {decomp['mes']}/{decomp['ano']} "
                    f"no estado de {decomp['uf_sigla']}. Numero: {decomp['numero_nfe']}, Serie: {decomp['serie']}."
                ),
                explicacao_tecnica=(
                    f"Chave de 44 digitos validada com sucesso. DV {decomp['digito_verificador']} confere com modulo 11. "
                    f"CNPJ Emitente: {decomp['cnpj_emitente']}, Modelo: {decomp['modelo']}."
                ),
                campos_afetados=["infNFe/@Id"],
                valor_esperado=str(decomp["dv_calculado"]),
                valor_observado=str(decomp["digito_verificador"]),
                base_legal=["MOC 7.0 - Calculo do Digito Verificador (Modulo 11)"],
            )
        )

    return findings


def auditar_matematica_item(
    n_item: int,
    c_prod: str,
    x_prod: str,
    q_com: Decimal,
    v_un_com: Decimal,
    v_prod: Decimal,
    v_desc: Decimal = Decimal("0.00"),
    v_outro: Decimal = Decimal("0.00"),
) -> Tuple[bool, Optional[ApontamentoFiscal]]:
    """
    Audita multiplicacao do item conforme SEFAZ Regra I08-10 (Rejeicao 629)
    e detecta valores monetarios negativos proibidos (SEFAZ-VAL-NEG).
    """
    # 1. Checagem de valores negativos
    if v_outro < Decimal("0.00") or v_prod < Decimal("0.00") or v_desc < Decimal("0.00"):
        return False, ApontamentoFiscal(
            status=StatusApontamento.INVALID,
            gravidade=GravidadeApontamento.CRITICAL,
            regra_id="SEFAZ-VAL-NEG",
            titulo=f"Falha de Schema (XSD): Valor Monetario Negativo no Item {n_item}",
            explicacao_executiva=(
                f"No item {n_item} ({x_prod}), foi informado um valor negativo. "
                "A SEFAZ e o componente ACBr proíbem expressamente qualquer sinal negativo no XML. "
                "Descontos e vouchers de aplicativos devem ser somados no campo de Desconto (vDesc), nunca como acrescimo negativo."
            ),
            explicacao_tecnica=(
                f"Item {n_item} possui valor negativo (vOutro={v_outro:.2f}, vProd={v_prod:.2f}). "
                "O tipo TDec_1302 da SEFAZ rejeita numeros com sinal de menos."
            ),
            campos_afetados=[f"det[{n_item}]/prod/vOutro"],
            valor_esperado=">= 0.00",
            valor_observado=f"{v_outro:.2f}",
            base_legal=["MOC 7.0 - Tipos Basicos (TDec_1302)"],
            acoes_recomendadas=["Transferir o valor do cupom ou desconto para o campo vDesc."],
        )

    # 2. Multiplicacao qCom * vUnCom == vProd (Regra I08-10 / Rejeicao 629)
    v_prod_esperado = round_abnt(q_com * v_un_com, ROUND_2)
    diff = abs(v_prod - v_prod_esperado)

    if diff > TOLERANCIA_CENTAVO:
        return False, ApontamentoFiscal(
            status=StatusApontamento.INVALID,
            gravidade=GravidadeApontamento.HIGH,
            regra_id="SEFAZ-I08-10",
            titulo="Rejeicao 629: Valor do Produto difere de Quantidade vezes Valor Unitario",
            explicacao_executiva=(
                f"No item {n_item} ({x_prod}), a quantidade ({q_com:.3f}) multiplicada pelo preco unitario "
                f"(R$ {v_un_com:.3f}) deveria resultar em R$ {v_prod_esperado:.2f}, mas a nota declara R$ {v_prod:.2f}. "
                f"Essa diferenca de R$ {diff:.2f} gerara rejeicao imediata na SEFAZ."
            ),
            explicacao_tecnica=(
                f"Multiplicacao qCom ({q_com:.4f}) * vUnCom ({v_un_com:.4f}) = {v_prod_esperado:.2f}, "
                f"mas a tag <vProd> declarou {v_prod:.2f} (divergencia de R$ {diff:.2f})."
            ),
            campos_afetados=[f"det[{n_item}]/prod/vProd", f"det[{n_item}]/prod/qCom", f"det[{n_item}]/prod/vUnCom"],
            valor_esperado=f"{v_prod_esperado:.2f}",
            valor_observado=f"{v_prod:.2f}",
            base_legal=[
                "Manual de Orientacao do Contribuinte (MOC) 7.0 - Regra I08-10",
                "ABNT NBR 5891:2014 - Regras de Arredondamento Decimal",
            ],
            acoes_recomendadas=[
                f"Ajustar a tag <vProd> do item {n_item} para {v_prod_esperado:.2f} ou recalcular o valor unitario no webPosto.",
            ],
        )

    return True, None


def auditar_totais_documento(
    v_prod_total_declarado: Decimal,
    itens_v_prod: List[Decimal],
    v_nf_declarado: Decimal,
    v_desc: Decimal = Decimal("0.00"),
    v_outro: Decimal = Decimal("0.00"),
    v_frete: Decimal = Decimal("0.00"),
    v_seg: Decimal = Decimal("0.00"),
    v_st: Decimal = Decimal("0.00"),
) -> List[ApontamentoFiscal]:
    """
    Audita totais do documento:
    - Regra W07-10 (Rejeicao 531): vProd total vs somatorio dos itens
    - Regra W16-10 (Rejeicao 535): composicao do vNF
    - Projecao de cascata
    """
    findings: List[ApontamentoFiscal] = []

    # Checar valores negativos nos totais
    if v_outro < Decimal("0.00") or v_desc < Decimal("0.00") or v_nf_declarado < Decimal("0.00"):
        findings.append(
            ApontamentoFiscal(
                status=StatusApontamento.INVALID,
                gravidade=GravidadeApontamento.CRITICAL,
                regra_id="SEFAZ-VAL-NEG",
                titulo="Falha de Schema (XSD): Valor Monetario Negativo nos Totais (<total>/<ICMSTot>)",
                explicacao_executiva=(
                    "Nos totais da nota foram encontrados valores negativos. A SEFAZ proíbe expressamente "
                    "valores negativos no cabecalho. Cupons de aplicativos devem ser somados em vDesc (Desconto)."
                ),
                explicacao_tecnica=f"Campo totalizador com valor negativo: vOutro={v_outro:.2f}.",
                campos_afetados=["total/ICMSTot/vOutro"],
                valor_esperado=">= 0.00",
                valor_observado=f"{v_outro:.2f}",
                base_legal=["MOC 7.0 - Tipos Basicos (TDec_1302)"],
                acoes_recomendadas=["Zerar vOutro e transferir o valor para vDesc."],
            )
        )

    # Regra W07-10: soma dos itens vs total
    soma_itens = sum(itens_v_prod)
    diff_prod = abs(v_prod_total_declarado - soma_itens)

    if diff_prod > TOLERANCIA_CENTAVO:
        findings.append(
            ApontamentoFiscal(
                status=StatusApontamento.INVALID,
                gravidade=GravidadeApontamento.HIGH,
                regra_id="SEFAZ-W07-10",
                titulo="Rejeicao 531: Total do Valor dos Produtos difere do somatorio dos itens",
                explicacao_executiva=(
                    f"A soma dos produtos dos itens resulta em R$ {soma_itens:.2f}, "
                    f"mas o total geral de produtos informado no cabecalho e R$ {v_prod_total_declarado:.2f}."
                ),
                explicacao_tecnica=(
                    f"Campo <total><ICMSTot><vProd> declarado e {v_prod_total_declarado:.2f}, "
                    f"mas o somatorio dos itens e {soma_itens:.2f} (diferenca de R$ {diff_prod:.2f})."
                ),
                campos_afetados=["total/ICMSTot/vProd", "det/prod/vProd"],
                valor_esperado=f"{soma_itens:.2f}",
                valor_observado=f"{v_prod_total_declarado:.2f}",
                base_legal=["MOC 7.0 - Regra W07-10"],
                acoes_recomendadas=["Ajustar a tag <vProd> no totalizador para coincidir com a soma exata dos itens."],
            )
        )
    else:
        findings.append(
            ApontamentoFiscal(
                status=StatusApontamento.VALID,
                gravidade=GravidadeApontamento.INFO,
                regra_id="SEFAZ-W07-10",
                titulo="Total de Produtos Conforme com a Soma dos Itens (Regra W07-10)",
                explicacao_executiva="O total dos produtos informado bate perfeitamente com a soma dos itens.",
                explicacao_tecnica=f"vProd ({v_prod_total_declarado:.2f}) confere com somatorio dos {len(itens_v_prod)} itens.",
                campos_afetados=["total/ICMSTot/vProd"],
                valor_esperado=f"{v_prod_total_declarado:.2f}",
                valor_observado=f"{v_prod_total_declarado:.2f}",
                base_legal=["MOC 7.0 - Regra W07-10"],
            )
        )

    # Regra W16-10: composicao do vNF
    vnf_esperado = v_prod_total_declarado - v_desc + v_st + v_frete + v_seg + v_outro
    diff_vnf = abs(v_nf_declarado - vnf_esperado)

    if diff_vnf > TOLERANCIA_CENTAVO:
        findings.append(
            ApontamentoFiscal(
                status=StatusApontamento.INVALID,
                gravidade=GravidadeApontamento.HIGH,
                regra_id="SEFAZ-W16-10",
                titulo="Rejeicao 535: Total da NF-e difere do somatorio dos valores que compoem o total",
                explicacao_executiva=(
                    f"O valor total da nota fiscal (R$ {v_nf_declarado:.2f}) nao confere com a soma dos produtos "
                    f"mais adicionais menos descontos (esperado: R$ {vnf_esperado:.2f})."
                ),
                explicacao_tecnica=(
                    f"vNF declarado = {v_nf_declarado:.2f}, composicao esperada = {vnf_esperado:.2f} "
                    f"(divergencia de R$ {diff_vnf:.2f})."
                ),
                campos_afetados=["total/ICMSTot/vNF"],
                valor_esperado=f"{vnf_esperado:.2f}",
                valor_observado=f"{v_nf_declarado:.2f}",
                base_legal=["MOC 7.0 - Regra W16-10"],
                acoes_recomendadas=["Ajustar o total <vNF> para coincidir com a soma exata das parcelas."],
            )
        )
    else:
        findings.append(
            ApontamentoFiscal(
                status=StatusApontamento.VALID,
                gravidade=GravidadeApontamento.INFO,
                regra_id="SEFAZ-W16-10",
                titulo="Total da Nota Fiscal Conforme (Regra W16-10)",
                explicacao_executiva="O valor total da nota esta matematicamente correto segundo as regras da SEFAZ.",
                explicacao_tecnica=f"vNF ({v_nf_declarado:.2f}) coincide com a composicao financeira das parcelas.",
                campos_afetados=["total/ICMSTot/vNF"],
                valor_esperado=f"{v_nf_declarado:.2f}",
                valor_observado=f"{v_nf_declarado:.2f}",
                base_legal=["MOC 7.0 - Regra W16-10"],
            )
        )

    return findings


def validar_tributacao_combustivel_monofasico(
    anp_code: str,
    cst: Optional[str],
    cfop: str = "5656",
    crt: str = "3",
) -> List[ApontamentoFiscal]:
    """
    Valida enquadramento no ICMS Monofasico sobre combustiveis (LC 192/2022).
    - Gasolina, Diesel e GLP exigem CST 61 e CFOP especifico (5656/5655/5929)
    - Etanol Hidratado permanece em Substituicao Tributaria (CST 60) e veda CST 61
    """
    findings: List[ApontamentoFiscal] = []
    anp_clean = re.sub(r"[^0-9]", "", str(anp_code or ""))
    cfop_clean = re.sub(r"[^0-9]", "", str(cfop or ""))
    cst_clean = (cst or "").strip()

    if not anp_clean:
        return findings

    # Combustiveis monofasicos: Gasolina, Diesel, GLP
    if anp_clean in ANP_COMBUSTIVEIS_MONOFASICOS_ICMS:
        # Rejeicao 960: Exigencia de CST 61 (para regime normal CRT 3 ou com CST)
        if crt != "1" and cst_clean and cst_clean != "61":
            findings.append(
                ApontamentoFiscal(
                    status=StatusApontamento.INVALID,
                    gravidade=GravidadeApontamento.CRITICAL,
                    regra_id="SEFAZ-REJ-960",
                    titulo="Rejeicao 960: Combustivel sujeito ao ICMS Monofasico exige CST 61",
                    explicacao_executiva=(
                        "Gasolina, Diesel e GLP estao sob regime monofasico de ICMS (LC 192/2022). "
                        "O uso do antigo CST 60 e expressamente proibido pela SEFAZ e trava a emissao. "
                        "O produto deve ser cadastrado com CST 61 no webPosto."
                    ),
                    explicacao_tecnica=(
                        f"Codigo ANP {anp_clean} com CST {cst_clean}. A SEFAZ exige CST 61 "
                        "(ICMS monofasico sobre combustiveis cobrado anteriormente) e rejeita com cStat 960."
                    ),
                    campos_afetados=["det/imposto/ICMS/*/CST", "det/prod/comb/cProdANP"],
                    valor_esperado="CST 61",
                    valor_observado=f"CST {cst_clean}",
                    base_legal=[
                        "LC 192/2022",
                        "Convenio CONFAZ 199/2022",
                        "Convenio CONFAZ 15/2023",
                        "MOC 7.0 - Rejeicao 960",
                    ],
                    acoes_recomendadas=[
                        "Alterar o CST do combustivel de 60 para 61 no cadastro de produtos do webPosto.",
                        "Garantir a geracao das tags <qBCMonoRet> e <adRemICMSRet> no XML.",
                    ],
                )
            )

        # Rejeicao 958: CFOP incompativel com ICMS Monofasico
        cfops_permitidos = {"5656", "5655", "5929", "6656", "6655", "6929"}
        if cfop_clean and cfop_clean not in cfops_permitidos:
            findings.append(
                ApontamentoFiscal(
                    status=StatusApontamento.INVALID,
                    gravidade=GravidadeApontamento.HIGH,
                    regra_id="SEFAZ-REJ-958",
                    titulo="Rejeicao 958: CFOP incompativel com ICMS Monofasico de Combustivel",
                    explicacao_executiva=(
                        f"Combustivel monofasico (ANP {anp_clean}) emitido com CFOP {cfop_clean}. "
                        "A SEFAZ exige CFOP especifico como 5656 (ou 5655/5929). "
                        "CFOPs genericos de revenda como 5102 geram rejeicao imediata."
                    ),
                    explicacao_tecnica=(
                        f"CFOP {cfop_clean} incompativel com combustivel sob ICMS monofasico "
                        "(Regra N12-90 da NT 2023.001 / Rejeicao 958)."
                    ),
                    campos_afetados=["det/prod/CFOP", "det/prod/comb/cProdANP"],
                    valor_esperado="CFOP 5656, 5655 ou 5929",
                    valor_observado=f"CFOP {cfop_clean}",
                    base_legal=["NT 2023.001 v1.50 - Regra N12-90 / Rejeicao 958"],
                    acoes_recomendadas=[
                        "Corrigir o CFOP do item no webPosto para 5656 (venda de combustivel monofasico).",
                    ],
                )
            )

    # Etanol Hidratado: Nao faz parte da monofasia do ICMS (permanece em ST CST 60)
    elif anp_clean in ANP_ETANOL_HIDRATADO:
        if cst_clean == "61":
            findings.append(
                ApontamentoFiscal(
                    status=StatusApontamento.INVALID,
                    gravidade=GravidadeApontamento.CRITICAL,
                    regra_id="SEFAZ-REJ-959",
                    titulo="Rejeicao 959: Etanol Hidratado nao admite CST 61 (Monofasico)",
                    explicacao_executiva=(
                        "O Etanol Hidratado (ANP 810101001/810101002) permanece sob o regime de Substituicao "
                        "Tributaria (CST 60) e nao entrou no ICMS Monofasico da LC 192/2022. O uso de CST 61 e indevido."
                    ),
                    explicacao_tecnica=(
                        f"Codigo ANP {anp_clean} (Etanol) com CST 61. Violacao da Regra da NT 2023.001 (Rejeicao 959)."
                    ),
                    campos_afetados=["det/imposto/ICMS/*/CST", "det/prod/comb/cProdANP"],
                    valor_esperado="CST 60",
                    valor_observado="CST 61",
                    base_legal=["LC 192/2022", "Convenio CONFAZ 199/2022", "NT 2023.001"],
                    acoes_recomendadas=[
                        "Ajustar o cadastro de Etanol Hidratado no webPosto para CST 60.",
                    ],
                )
            )

    return findings


def validar_pis_cofins_monofasico(
    ncm: str,
    cst_pis_cofins: Optional[str],
    produto_nome: str = "",
) -> List[ApontamentoFiscal]:
    """
    Audita tributacao de PIS/COFINS para produtos da cadeia monofasica (Tabela 4.3.10 EFD-Contribuicoes).
    Evita bitributacao: postos e lojas de conveniencia devem aplicar CST 04 (Aliquota Zero no Varejo).
    """
    findings: List[ApontamentoFiscal] = []
    ncm_clean = re.sub(r"[^0-9]", "", str(ncm or ""))
    cst_clean = re.sub(r"[^0-9]", "", str(cst_pis_cofins or ""))

    if not ncm_clean or not cst_clean:
        return findings

    if ncm_clean in NCMS_MONOFASICOS_PIS_COFINS:
        # CSTs tributaveis indevidos no varejo (01, 02, 03, 99)
        if cst_clean in ("01", "02", "03", "99"):
            findings.append(
                ApontamentoFiscal(
                    status=StatusApontamento.WARNING,
                    gravidade=GravidadeApontamento.HIGH,
                    regra_id="SPED-RISCO-BITRIBUTACAO-PISCOFINS",
                    titulo="Alerta Contabil: Risco de Bitributacao de PIS/COFINS Monofasico",
                    explicacao_executiva=(
                        f"O item '{produto_nome or ncm_clean}' (NCM {ncm_clean}) pertence a cadeia monofasica de PIS/COFINS. "
                        "No posto e na loja de conveniencia, esse imposto ja foi recolhido antecipadamente pela refinaria "
                        f"ou fabricante. Manter cadastrado com CST {cst_clean} faz a empresa recolher imposto em dobro "
                        "(bitributacao de 9,25% no Lucro Real ou 3,65% no Lucro Presumido). O correto e CST 04 (Aliquota Zero no Varejo)."
                    ),
                    explicacao_tecnica=(
                        f"NCM {ncm_clean} listado na Tabela 4.3.10 da EFD-Contribuicoes cadastrado com CST PIS/COFINS {cst_clean}. "
                        "Gera apuracao indevida no Bloco M da EFD-Contribuicoes e recolhimento duplicado via DARF."
                    ),
                    campos_afetados=["det/imposto/PIS/*/CST", "det/imposto/COFINS/*/CST", "det/prod/NCM"],
                    valor_esperado="CST 04 (Operacao Tributavel Monofasica - Aliquota Zero)",
                    valor_observado=f"CST {cst_clean}",
                    base_legal=[
                        "Lei 13.097/2015 art. 28 (Bebidas Frias)",
                        "Lei 10.833/2003 e Lei 9.718/1998 (Combustiveis)",
                        "Tabela 4.3.10 EFD-Contribuicoes",
                    ],
                    acoes_recomendadas=[
                        "Alterar imediatamente a tributacao de PIS e COFINS no webPosto para CST 04.",
                        "Solicitar a contabilidade a segregacao dessas receitas no SPED Contribuicoes.",
                    ],
                )
            )

    return findings


def validar_ncm_e_cest(
    ncm: str,
    cest: Optional[str] = None,
    produto_nome: str = "",
) -> List[ApontamentoFiscal]:
    """
    Valida presenca compulsoria do codigo CEST para NCMs sujeitos a ST e Monofasico (Convenio ICMS 142/2018).
    Evita a Rejeicao 806 da SEFAZ.
    """
    findings: List[ApontamentoFiscal] = []
    ncm_clean = re.sub(r"[^0-9]", "", str(ncm or ""))
    cest_clean = re.sub(r"[^0-9]", "", str(cest or ""))

    if not ncm_clean:
        return findings

    if ncm_clean in CESTS_OBRIGATORIOS_POSTO:
        expected_cest = CESTS_OBRIGATORIOS_POSTO[ncm_clean]
        expected_clean = re.sub(r"[^0-9]", "", expected_cest)

        if not cest_clean:
            findings.append(
                ApontamentoFiscal(
                    status=StatusApontamento.INVALID,
                    gravidade=GravidadeApontamento.HIGH,
                    regra_id="SEFAZ-REJ-806",
                    titulo="Rejeicao 806: Falta do CEST obrigatorio para produto com ICMS-ST / Monofasico",
                    explicacao_executiva=(
                        f"O produto '{produto_nome or ncm_clean}' (NCM {ncm_clean}) esta sujeito a Substituicao Tributaria "
                        f"ou regime Monofasico e exige codigo CEST correspondente ({expected_cest}). "
                        "A emissao do documento sera rejeitada pela SEFAZ caso o campo CEST esteja em branco."
                    ),
                    explicacao_tecnica=(
                        f"NCM {ncm_clean} sem codigo CEST informado. Violacao da Regra I08-01 / I08-02 da NT 2015.003 "
                        "e Convenio ICMS 142/2018 (Rejeicao 806)."
                    ),
                    campos_afetados=["det/prod/CEST", "det/prod/NCM"],
                    valor_esperado=f"CEST {expected_cest}",
                    valor_observado="Ausente",
                    base_legal=["Convenio ICMS 142/2018", "MOC 7.0 - Rejeicao 806"],
                    acoes_recomendadas=[
                        f"Cadastrar o codigo CEST {expected_cest} no cadastro do item no webPosto.",
                    ],
                )
            )

    return findings


def auditar_regras_tributarias_posto(
    mod: str,
    cfop: str,
    ref_chaves: List[str],
    ind_ie_dest: str = "9",
    dest_uf: str = "SP",
    cst: Optional[str] = None,
    csosn: Optional[str] = None,
    crt: str = "3",
    anp_code: Optional[str] = None,
    id_dest: str = "1",
    ind_final: str = "1",
    p_icms_inter: Optional[Decimal] = None,
    orig: str = "0",
    emit_uf: str = "SP",
    ncm: Optional[str] = None,
    cest: Optional[str] = None,
    cst_pis_cofins: Optional[str] = None,
    produto_nome: Optional[str] = None,
) -> List[ApontamentoFiscal]:
    """
    Audita regras de negocio e tributacao especificas de postos:
    - CFOP 5929/6929 x NFC-e mod 65 (Rejeicao 375 vs Rejeicao 701 e SPED C113)
    - Cadastro cliente: indIEDest x CST x CSOSN (Rejeicoes 508, 600, 529, 805)
    - DIFAL e excecoes de combustiveis ANP (Rejeicoes 694, 695, 697, 698)
    """
    findings: List[ApontamentoFiscal] = []
    cfop_clean = re.sub(r"[^0-9]", "", str(cfop))

    # 1. Regra I08-180 / Rejeicao 375: Cupom Fiscal referenciando NFC-e (mod 65)
    if mod == "55" and cfop_clean in ("5929", "6929"):
        chaves_65 = [k for k in ref_chaves if len(re.sub(r"[^0-9]", "", k)) == 44 and re.sub(r"[^0-9]", "", k)[20:22] == "65"]
        if chaves_65:
            findings.append(
                ApontamentoFiscal(
                    status=StatusApontamento.INVALID,
                    gravidade=GravidadeApontamento.HIGH,
                    regra_id="SEFAZ-I08-180",
                    titulo="Rejeicao 375: NF-e com lancamento de Cupom Fiscal referencia uma NFC-e",
                    explicacao_executiva=(
                        "A NF-e modelo 55 utiliza CFOP 5929/6929 e referencia chaves de NFC-e (modelo 65) no grupo NFref. "
                        "A SEFAZ bloqueia essa estrutura pela Regra I08-180 (Rejeicao 375). "
                        "No webPosto 26.9+, essa situacao e contornada removendo o grupo NFref do XML e informando "
                        "os cupons apenas nas Informacoes Complementares (infCpl)."
                    ),
                    explicacao_tecnica=(
                        f"CFOP {cfop_clean} em NF-e mod 55 referencia {len(chaves_65)} NFC-e(s) mod 65 em <NFref>. "
                        "Violacao da Regra I08-180 (NT 2026.002 / NT 2020.006)."
                    ),
                    campos_afetados=["ide/NFref/refNFe", "det/prod/CFOP"],
                    valor_esperado="Nao referenciar NFC-e (mod 65) em NFref ao utilizar CFOP 5929/6929",
                    valor_observado=f"{len(chaves_65)} chaves de modelo 65 referenciadas",
                    base_legal=["MOC 7.0 - Anexo I - Regra I08-180 / Rejeicao 375", "NT 2026.002"],
                    acoes_recomendadas=[
                        "Remover as tags <refNFe> de modelo 65 do grupo <NFref>.",
                        "Informar as chaves e numeros dos cupons exclusivamente em <infCpl> (comportamento nativo do webPosto 26.9).",
                    ],
                )
            )
        elif not ref_chaves:
            # Regra BA02 / Alerta Rejeicao 701 e SPED C113
            findings.append(
                ApontamentoFiscal(
                    status=StatusApontamento.WARNING,
                    gravidade=GravidadeApontamento.MEDIUM,
                    regra_id="SEFAZ-BA02",
                    titulo="Alerta Fiscal: Operacao com CFOP 5929 sem NFref (Risco Rejeicao 701 e SPED C113)",
                    explicacao_executiva=(
                        "A nota fiscal utiliza CFOP 5929/6929 sem documento referenciado no grupo NFref. "
                        "Embora a SEFAZ de SP autorize esse formato (contorno da Rejeicao 375), estados como MG, RS, MT e BA "
                        "rejeitam com codigo 701. Alem disso, os cupons precisam ser escriturados no Registro C113 do SPED Fiscal."
                    ),
                    explicacao_tecnica=(
                        f"CFOP {cfop_clean} sem tag <NFref>. Em UFs que validam a Regra BA02 do MOC 7.0, gerara cStat 701. "
                        "Exige atencao contabil para amarração no Registro C113 da EFD ICMS/IPI."
                    ),
                    campos_afetados=["ide/NFref", "det/prod/CFOP"],
                    valor_esperado="Grupo <NFref> preenchido ou chaves escrituradas no SPED C113",
                    valor_observado="Grupo <NFref> ausente",
                    base_legal=["MOC 7.0 - Regra BA02 / Rejeicao 701", "Guia Pratico da EFD ICMS/IPI - Registro C113"],
                    acoes_recomendadas=[
                        "Verificar se o estado destinatario ou emissor ativa a Regra BA02.",
                        "Garantir a escrituracao dos cupons no Registro C113 do SPED da contabilidade.",
                    ],
                )
            )

    # 2. Regra 805: UFs que vedam Contribuinte Isento de IE (indIEDest=2)
    dest_uf_clean = (dest_uf or "").upper().strip()
    if ind_ie_dest == "2" and dest_uf_clean in UFS_VEDAM_ISENTO:
        findings.append(
            ApontamentoFiscal(
                status=StatusApontamento.INVALID,
                gravidade=GravidadeApontamento.HIGH,
                regra_id="SEFAZ-REJ-805",
                titulo="Rejeicao 805: A SEFAZ do destinatario nao permite Contribuinte Isento de IE",
                explicacao_executiva=(
                    f"O estado do cliente ({dest_uf_clean}) nao permite emissao de notas fiscais com cliente marcado "
                    "como Isento de Inscricao Estadual (indIEDest=2). O faturamento ficara travado."
                ),
                explicacao_tecnica=(
                    f"Destinatario na UF '{dest_uf_clean}' com indIEDest=2. "
                    "A SEFAZ veda expressamente essa combinacao pela Regra E16a-30 da NT 2015.003."
                ),
                campos_afetados=["dest/indIEDest", "dest/enderDest/UF"],
                valor_esperado="indIEDest=1 (com IE informada) ou indIEDest=9 (Nao Contribuinte)",
                valor_observado=f"indIEDest=2 para UF={dest_uf_clean}",
                base_legal=["NT 2015.003 v1.60 - Regra E16a-30 / Rejeicao 805"],
                acoes_recomendadas=[
                    f"Consultar o Sintegra de {dest_uf_clean}. Se tiver IE, informe-a e marque indIEDest=1 no webPosto.",
                    "Se nao tiver IE ou for consumidor final, altere para indIEDest=9 (Nao Contribuinte).",
                ],
            )
        )

    # 3. Regra 508 / 600: Incompatibilidade de CST / CSOSN com Nao Contribuinte (indIEDest=9)
    if ind_ie_dest == "9":
        if crt != "1" and cst:
            cst_clean = cst.strip()
            cst_permitidos = {"00", "20", "40", "41", "60"}
            if cst_clean not in cst_permitidos:
                findings.append(
                    ApontamentoFiscal(
                        status=StatusApontamento.INVALID,
                        gravidade=GravidadeApontamento.HIGH,
                        regra_id="SEFAZ-REJ-508",
                        titulo="Rejeicao 508: CST incompativel na operacao com Nao Contribuinte (indIEDest=9)",
                        explicacao_executiva=(
                            f"O produto esta com CST {cst_clean}, mas para clientes Nao Contribuintes (indIEDest=9) "
                            "a SEFAZ so autoriza os CSTs 00, 20, 40, 41 ou 60."
                        ),
                        explicacao_tecnica=(
                            f"CST '{cst_clean}' informado para indIEDest=9 em operacao de saida. "
                            "Violacao da Regra N12-70 da NT 2015.003."
                        ),
                        campos_afetados=["dest/indIEDest", "det/imposto/ICMS/*/CST"],
                        valor_esperado="CST 00, 20, 40, 41 ou 60",
                        valor_observado=f"CST {cst_clean}",
                        base_legal=["NT 2015.003 v1.60 - Regra N12-70 / Rejeicao 508"],
                        acoes_recomendadas=["Alterar o CST do produto no webPosto para 60 (se combustivel ST) ou 00/20."],
                    )
                )

        if crt == "1" and csosn:
            csosn_clean = csosn.strip()
            csosn_permitidos = {"102", "103", "300", "400", "500"}
            if csosn_clean not in csosn_permitidos:
                findings.append(
                    ApontamentoFiscal(
                        status=StatusApontamento.INVALID,
                        gravidade=GravidadeApontamento.HIGH,
                        regra_id="SEFAZ-REJ-600",
                        titulo="Rejeicao 600: CSOSN incompativel na operacao com Nao Contribuinte (indIEDest=9)",
                        explicacao_executiva=(
                            f"O produto esta com CSOSN {csosn_clean}. No Simples Nacional com cliente Nao Contribuinte, "
                            "a SEFAZ aceita apenas CSOSN 102, 103, 300, 400 ou 500."
                        ),
                        explicacao_tecnica=f"CSOSN {csosn_clean} incompativel com indIEDest=9 (Regra N12a-10 da NT 2015.003).",
                        campos_afetados=["dest/indIEDest", "det/imposto/ICMS/*/CSOSN"],
                        valor_esperado="CSOSN 102, 103, 300, 400 ou 500",
                        valor_observado=f"CSOSN {csosn_clean}",
                        base_legal=["NT 2015.003 v1.60 - Regra N12a-10 / Rejeicao 600"],
                        acoes_recomendadas=["Corrigir o CSOSN do produto no cadastro do webPosto para 500 (ST) ou 102."],
                    )
                )

    # 4. Regra 760: NFC-e de Pista com CST proibido
    if mod == "65" and cst:
        cst_clean = cst.strip()
        cst_permitidos_nfce = {"00", "20", "40", "41", "60", "90"}
        if cst_clean not in cst_permitidos_nfce:
            findings.append(
                ApontamentoFiscal(
                    status=StatusApontamento.INVALID,
                    gravidade=GravidadeApontamento.HIGH,
                    regra_id="SEFAZ-REJ-760",
                    titulo="Rejeicao 760: Item com CST indevido na NFC-e (Modelo 65)",
                    explicacao_executiva=(
                        f"O produto de pista/conveniencia esta configurado com CST {cst_clean}. "
                        "A NFC-e de pista rejeita produtos com CST diferente de 00, 20, 40, 41 ou 60."
                    ),
                    explicacao_tecnica=f"CST '{cst_clean}' indevido para modelo 65 (Regra da NT 2015.002).",
                    campos_afetados=["det/imposto/ICMS/*/CST", "ide/mod"],
                    valor_esperado="CST 00, 20, 40, 41 ou 60",
                    valor_observado=f"CST {cst_clean}",
                    base_legal=["MOC 7.0 - Rejeicao 760", "NT 2015.002"],
                    acoes_recomendadas=["Alterar o cadastro do produto no webPosto para CST 60 (ICMS-ST retido)."],
                )
            )

    # 5. DIFAL e Excecao de Combustiveis Derivados de Petroleo (Rejeicoes 694 e 695)
    if id_dest == "2" and ind_final == "1" and ind_ie_dest == "9":
        if anp_code:
            anp_clean = re.sub(r"[^0-9]", "", str(anp_code))
            is_derivado_petroleo = anp_clean not in ANP_NAO_DERIVADOS_PETROLEO
            if is_derivado_petroleo:
                # Se for combustivel derivado de petroleo, DIFAL e proibido no grupo ICMSUFDest
                findings.append(
                    ApontamentoFiscal(
                        status=StatusApontamento.VALID,
                        gravidade=GravidadeApontamento.INFO,
                        regra_id="SEFAZ-ANP-DIFAL-EXC",
                        titulo="Excecao Legal de Combustivel Derivado de Petroleo (Dispensa de DIFAL)",
                        explicacao_executiva=(
                            f"Combustivel com codigo ANP {anp_clean} e derivado de petroleo e possui regime tributario "
                            "monofasico/proprio, sendo legalmente dispensado do grupo de partilha de DIFAL (ICMSUFDest)."
                        ),
                        explicacao_tecnica=(
                            f"Codigo ANP {anp_clean} enquadrado na excecao da Regra NA01-20 da NT 2015.003 v1.70: "
                            "operacoes interestaduais com combustiveis derivados de petroleo nao admitem ICMSUFDest."
                        ),
                        campos_afetados=["det/prod/comb/cProdANP", "det/imposto/ICMSUFDest"],
                        base_legal=["NT 2015.003 v1.70 - Regra NA01-20 (Excecao para combustiveis)"],
                    )
                )

    # 6. Regra ICMS Monofasico de Combustiveis (LC 192/2022 - Rejeicoes 958, 959, 960)
    if anp_code:
        findings.extend(
            validar_tributacao_combustivel_monofasico(
                anp_code=anp_code,
                cst=cst,
                cfop=cfop_clean,
                crt=crt,
            )
        )

    # 7. Regra PIS/COFINS Monofasico - Alerta de Bitributacao (Tabela 4.3.10 EFD-Contribuicoes)
    if ncm:
        findings.extend(
            validar_pis_cofins_monofasico(
                ncm=ncm,
                cst_pis_cofins=cst_pis_cofins,
                produto_nome=produto_nome or "",
            )
        )

    # 8. Regra CEST Obrigatorio para itens de ST / Monofasico (Rejeicao 806 / Convenio 142/2018)
    if ncm:
        findings.extend(
            validar_ncm_e_cest(
                ncm=ncm,
                cest=cest,
                produto_nome=produto_nome or "",
            )
        )

    return findings


def auditar_documento_xml(xml_texto: str) -> Dict[str, Any]:
    """
    Executa auditoria completa e determinística de um documento XML (NF-e/NFC-e).
    Extrai cabecalho, itens, totais, protocolo e roda todas as regras matematicas e fiscais.
    """
    clean_xml = (xml_texto or "").strip()
    if not clean_xml:
        return {"valido": False, "erro": "Conteudo XML vazio."}

    try:
        root = etree.fromstring(clean_xml.encode("utf-8"))
    except Exception as exc:
        return {"valido": False, "erro": f"Falha no parser do XML: {str(exc)}"}

    # Extrair infNFe
    inf = root.find(".//{*}infNFe")
    if inf is None and root.tag.endswith("infNFe"):
        inf = root

    if inf is None:
        return {"valido": False, "erro": "Tag <infNFe> nao encontrada no XML."}

    chave_acesso = re.sub(r"[^0-9]", "", inf.attrib.get("Id", ""))
    ide = inf.find("{*}ide")
    emit = inf.find("{*}emit")
    dest = inf.find("{*}dest")
    total = inf.find("{*}total/{*}ICMSTot")

    mod = ide.findtext("{*}mod") if ide is not None else "55"
    emit_uf = emit.findtext("{*}enderEmit/{*}UF") if emit is not None else "SP"
    dest_uf = dest.findtext("{*}enderDest/{*}UF") if dest is not None else emit_uf
    ind_ie_dest = dest.findtext("{*}indIEDest") if dest is not None else "9"
    id_dest = ide.findtext("{*}idDest") if ide is not None else "1"
    ind_final = ide.findtext("{*}indFinal") if ide is not None else "1"
    crt = emit.findtext("{*}CRT") if emit is not None else "3"

    # Chaves referenciadas em NFref
    ref_chaves = []
    if ide is not None:
        for ref in ide.findall(".//{*}refNFe"):
            if ref.text:
                ref_chaves.append(ref.text.strip())

    findings: List[ApontamentoFiscal] = []

    # 1. Auditoria da Chave de Acesso
    if chave_acesso:
        findings.extend(validar_chave_acesso(chave_acesso))

    # 2. Auditoria do Protocolo
    prot = root.find(".//{*}protNFe")
    if prot is None:
        findings.append(
            ApontamentoFiscal(
                status=StatusApontamento.WARNING,
                gravidade=GravidadeApontamento.MEDIUM,
                regra_id="SEFAZ-PROT-01",
                titulo="Documento fiscal sem protocolo de autorizacao de uso (protNFe)",
                explicacao_executiva=(
                    "Este arquivo XML nao possui o protocolo oficial de autorizacao da SEFAZ. "
                    "Ele representa um rascunho ou espelho antes do envio. Nao utilize como comprovante fiscal final."
                ),
                explicacao_tecnica="Ausencia do no <protNFe> com cStat=100. Documento nao homologado.",
                campos_afetados=["protNFe", "nfeProc"],
                valor_esperado="<protNFe> com cStat=100",
                valor_observado="Ausente",
                base_legal=["MOC 7.0 - Padrao de Distribuicao", "Ajuste SINIEF 07/05"],
                acoes_recomendadas=["Para notas ja autorizadas, exportar o XML completo de distribuicao (procNFe) no webPosto."],
            )
        )
    else:
        cstat = prot.findtext(".//{*}cStat")
        if cstat == "100":
            findings.append(
                ApontamentoFiscal(
                    status=StatusApontamento.VALID,
                    gravidade=GravidadeApontamento.INFO,
                    regra_id="SEFAZ-PROT-01",
                    titulo="Documento Homologado e Autorizado pela SEFAZ (cStat=100)",
                    explicacao_executiva="O documento possui protocolo oficial valido e foi formalmente autorizado pela SEFAZ.",
                    explicacao_tecnica=f"Protocolo autorizado com cStat=100. nProt={prot.findtext('.//{*}nProt')}.",
                    campos_afetados=["protNFe/infProt/cStat"],
                    valor_esperado="100",
                    valor_observado="100",
                    base_legal=["MOC 7.0"],
                )
            )

    # 3. Auditoria dos Itens (Matematica e Tributacao)
    itens_vprod: List[Decimal] = []
    cfops_encontrados = set()

    for det in inf.findall("{*}det"):
        n_item_str = det.attrib.get("nItem", "1")
        try:
            n_item = int(n_item_str)
        except ValueError:
            n_item = 1

        prod = det.find("{*}prod")
        if prod is None:
            continue

        c_prod = prod.findtext("{*}cProd") or ""
        x_prod = prod.findtext("{*}xProd") or ""
        cfop_item = prod.findtext("{*}CFOP") or ""
        cfops_encontrados.add(cfop_item)

        q_com = Decimal(prod.findtext("{*}qCom") or "1.00")
        v_un_com = Decimal(prod.findtext("{*}vUnCom") or "0.00")
        v_prod_declared = Decimal(prod.findtext("{*}vProd") or "0.00")
        v_desc = Decimal(prod.findtext("{*}vDesc") or "0.00")
        v_outro = Decimal(prod.findtext("{*}vOutro") or "0.00")
        itens_vprod.append(v_prod_declared)

        # Matematica item (I08-10)
        _, math_finding = auditar_matematica_item(n_item, c_prod, x_prod, q_com, v_un_com, v_prod_declared, v_desc, v_outro)
        if math_finding:
            findings.append(math_finding)

        # Tributacao do item
        icms_elem = det.find(".//{*}imposto/{*}ICMS")
        cst_item = None
        csosn_item = None
        if icms_elem is not None:
            for child in icms_elem:
                if child.find("{*}CST") is not None:
                    cst_item = child.findtext("{*}CST")
                if child.find("{*}CSOSN") is not None:
                    csosn_item = child.findtext("{*}CSOSN")

        comb_elem = prod.find("{*}comb")
        anp_code = comb_elem.findtext("{*}cProdANP") if comb_elem is not None else None

        # Extrair NCM e CEST
        ncm_item = prod.findtext("{*}NCM")
        cest_item = prod.findtext("{*}CEST")

        # Extrair CST PIS
        pis_elem = det.find(".//{*}imposto/{*}PIS")
        pis_cst = None
        if pis_elem is not None:
            for child in pis_elem:
                if child.find("{*}CST") is not None:
                    pis_cst = child.findtext("{*}CST")
                    break

        # Auditar regras do posto para cada item
        item_tax_findings = auditar_regras_tributarias_posto(
            mod=mod,
            cfop=cfop_item,
            ref_chaves=ref_chaves,
            ind_ie_dest=ind_ie_dest,
            dest_uf=dest_uf,
            cst=cst_item,
            csosn=csosn_item,
            crt=crt,
            anp_code=anp_code,
            id_dest=id_dest,
            ind_final=ind_final,
            emit_uf=emit_uf,
            ncm=ncm_item,
            cest=cest_item,
            cst_pis_cofins=pis_cst,
            produto_nome=x_prod,
        )
        findings.extend(item_tax_findings)

    # 4. Auditoria de Totais
    if total is not None:
        v_prod_total = Decimal(total.findtext("{*}vProd") or "0.00")
        v_nf_total = Decimal(total.findtext("{*}vNF") or "0.00")
        v_desc_tot = Decimal(total.findtext("{*}vDesc") or "0.00")
        v_outro_tot = Decimal(total.findtext("{*}vOutro") or "0.00")
        v_frete_tot = Decimal(total.findtext("{*}vFrete") or "0.00")
        v_seg_tot = Decimal(total.findtext("{*}vSeg") or "0.00")
        v_st_tot = Decimal(total.findtext("{*}vST") or "0.00")

        tot_findings = auditar_totais_documento(
            v_prod_total_declarado=v_prod_total,
            itens_v_prod=itens_vprod,
            v_nf_declarado=v_nf_total,
            v_desc=v_desc_tot,
            v_outro=v_outro_tot,
            v_frete=v_frete_tot,
            v_seg=v_seg_tot,
            v_st=v_st_tot,
        )
        findings.extend(tot_findings)

    # Consolidar estatisticas
    invalidos = [f for f in findings if f.status == StatusApontamento.INVALID]
    alertas = [f for f in findings if f.status == StatusApontamento.WARNING]
    conformes = [f for f in findings if f.status == StatusApontamento.VALID]

    return {
        "valido": len(invalidos) == 0,
        "total_apontamentos": len(findings),
        "erros_impeditivos": len(invalidos),
        "alertas_fiscais": len(alertas),
        "conformidades": len(conformes),
        "chave_acesso": chave_acesso,
        "modelo": mod,
        "emit_uf": emit_uf,
        "dest_uf": dest_uf,
        "apontamentos": [f.model_dump() for f in findings],
    }
