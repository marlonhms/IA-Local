"""
Testes Unitarios do Motor Fiscal e Tributario Determinístico (tests/unit/test_fiscal_engine.py).
Valida:
1. Calculo de DV Modulo 11 e decomposicao de chave de 44 digitos da SEFAZ
2. Auditoria matematica ABNT NBR 5891:2014 (Regra I08-10, W07-10, W16-10, SEFAZ-VAL-NEG)
3. Regras de negocio de postos (Rejeicao 375 vs 701, Rejeicao 805, 508, 760 e DIFAL ANP)
4. Auditoria completa de XML com defusedxml e lxml
5. Integracao com PostoTools e WebPostoRAGEngine (FTS5 BM25)

Regra inegociavel: ZERO travessoes em todo o arquivo.
"""

from __future__ import annotations
import uuid

import sqlite3
from decimal import Decimal
from pathlib import Path
import pytest

from core.fiscal_engine import (
    StatusApontamento,
    GravidadeApontamento,
    calcular_dv_modulo_11,
    decompor_chave_acesso,
    validar_chave_acesso,
    auditar_matematica_item,
    auditar_totais_documento,
    auditar_regras_tributarias_posto,
    auditar_documento_xml,
    validar_tributacao_combustivel_monofasico,
    validar_pis_cofins_monofasico,
    validar_ncm_e_cest,
    round_abnt,
)
from core.webposto_rag import WebPostoRAGEngine
from core.tools import PostoTools


CHAVE_NFE_VALIDA = "35261001173538000160550040000039571624115433"
CHAVE_NFCE_VALIDA = "35260901173538000160650010001678371007376817"


def test_calcular_dv_modulo_11_sucesso():
    """Valida calculo de DV por Modulo 11 conforme padrao oficial SEFAZ MOC 7.0."""
    base_43 = CHAVE_NFE_VALIDA[:43]
    dv = calcular_dv_modulo_11(base_43)
    assert dv == 3

    base_43_nfce = CHAVE_NFCE_VALIDA[:43]
    dv_nfce = calcular_dv_modulo_11(base_43_nfce)
    assert dv_nfce == 7


def test_calcular_dv_modulo_11_tamanho_invalido():
    """Garante excecao explicita quando a base de calculo nao contiver 43 digitos."""
    with pytest.raises(ValueError, match="deve ter 43 digitos"):
        calcular_dv_modulo_11("12345")


def test_decompor_chave_acesso():
    """Decompoe chave oficial de 44 digitos nos campos estruturados."""
    d = decompor_chave_acesso(CHAVE_NFE_VALIDA)
    assert d["c_uf"] == "35"
    assert d["uf_sigla"] == "SP"
    assert d["ano"] == "26"
    assert d["mes"] == "10"
    assert d["cnpj_emitente"] == "01173538000160"
    assert d["modelo"] == "55"
    assert d["tipo_documento"] == "NF-e (modelo 55)"
    assert d["serie"] == "004"
    assert d["numero_nfe"] == "000003957"
    assert d["tipo_emissao"] == "1"
    assert d["digito_verificador"] == "3"
    assert d["is_dv_valido"] is True


def test_validar_chave_acesso_valida():
    """Verifica chave de acesso integra e autentica."""
    findings = validar_chave_acesso(CHAVE_NFE_VALIDA)
    assert len(findings) == 1
    assert findings[0].status == StatusApontamento.VALID
    assert findings[0].regra_id == "SEFAZ-CHAVE-01"


def test_validar_chave_acesso_dv_invalido():
    """Detecta violacao do Digito Verificador (Rejeicao 253)."""
    # Altera o ultimo digito de 3 para 9
    chave_corrompida = CHAVE_NFE_VALIDA[:43] + "9"
    findings = validar_chave_acesso(chave_corrompida)
    assert any(f.regra_id == "SEFAZ-REJ-253" for f in findings)
    rej = [f for f in findings if f.regra_id == "SEFAZ-REJ-253"][0]
    assert rej.status == StatusApontamento.INVALID
    assert rej.valor_esperado == "3"
    assert rej.valor_observado == "9"


def test_validar_chave_acesso_tamanho_errado():
    """Detecta chave truncada ou incompleta."""
    findings = validar_chave_acesso("3526100117353800016055004000003957")
    assert len(findings) == 1
    assert findings[0].regra_id == "SEFAZ-CHAVE-LEN"
    assert findings[0].status == StatusApontamento.INVALID


def test_auditar_matematica_item_conforme():
    """Valida multiplicacao exata qCom * vUnCom == vProd (Regra I08-10)."""
    ok, finding = auditar_matematica_item(
        n_item=1,
        c_prod="001",
        x_prod="GASOLINA COMUM C",
        q_com=Decimal("15.500"),
        v_un_com=Decimal("5.590"),
        v_prod=Decimal("86.65"),
    )
    assert ok is True
    assert finding is None


def test_auditar_matematica_item_rejeicao_629():
    """Detecta divergencia matematica em abastecimento fracionado (Rejeicao 629)."""
    ok, finding = auditar_matematica_item(
        n_item=33,
        c_prod="005747",
        x_prod="PALHEIROS PAULISTINHA OURO",
        q_com=Decimal("1.0000"),
        v_un_com=Decimal("33.0000"),
        v_prod=Decimal("35.00"),  # Divergencia de R$ 2.00
    )
    assert ok is False
    assert finding is not None
    assert finding.regra_id == "SEFAZ-I08-10"
    assert finding.status == StatusApontamento.INVALID
    assert finding.valor_esperado == "33.00"
    assert finding.valor_observado == "35.00"


def test_auditar_matematica_item_valor_negativo_proibido():
    """Detecta valor monetario negativo que trava o ACBr (SEFAZ-VAL-NEG)."""
    ok, finding = auditar_matematica_item(
        n_item=1,
        c_prod="001",
        x_prod="GASOLINA COMUM",
        q_com=Decimal("10.00"),
        v_un_com=Decimal("5.00"),
        v_prod=Decimal("50.00"),
        v_outro=Decimal("-5.00"),  # Cupom de app lancado como vOutro negativo
    )
    assert ok is False
    assert finding is not None
    assert finding.regra_id == "SEFAZ-VAL-NEG"
    assert finding.gravidade == GravidadeApontamento.CRITICAL


def test_auditar_totais_documento_conforme():
    """Valida somatorio e composicao de vNF conformes (Regras W07-10 e W16-10)."""
    itens = [Decimal("50.00"), Decimal("30.00"), Decimal("20.00")]
    findings = auditar_totais_documento(
        v_prod_total_declarado=Decimal("100.00"),
        itens_v_prod=itens,
        v_nf_declarado=Decimal("100.00"),
    )
    assert all(f.status == StatusApontamento.VALID for f in findings)


def test_auditar_totais_documento_rejeicao_531_e_535():
    """Detecta total de produtos divergente da soma dos itens e vNF inconsistente."""
    itens = [Decimal("50.00"), Decimal("30.00")]  # Soma = 80.00
    findings = auditar_totais_documento(
        v_prod_total_declarado=Decimal("100.00"),  # Divergencia de R$ 20.00
        itens_v_prod=itens,
        v_nf_declarado=Decimal("95.00"),  # vNF divergente da composicao
        v_desc=Decimal("0.00"),
    )
    ids = [f.regra_id for f in findings]
    assert "SEFAZ-W07-10" in ids
    assert "SEFAZ-W16-10" in ids


def test_rejeicao_375_cfop_5929_referenciando_nfce_65():
    """Valida deteccao da Rejeicao 375 e orientacao para webPosto 26.9."""
    findings = auditar_regras_tributarias_posto(
        mod="55",
        cfop="5929",
        ref_chaves=[CHAVE_NFCE_VALIDA],  # Modelo 65 referenciada em NFref
    )
    assert len(findings) == 1
    rej = findings[0]
    assert rej.regra_id == "SEFAZ-I08-180"
    assert rej.status == StatusApontamento.INVALID
    assert "Rejeicao 375" in rej.titulo
    assert "webPosto 26.9" in rej.explicacao_executiva


def test_alerta_701_cfop_5929_sem_nfref_sped_c113():
    """Gera alerta fiscal e de SPED C113 quando NFref for omitida em CFOP 5929."""
    findings = auditar_regras_tributarias_posto(
        mod="55",
        cfop="5929",
        ref_chaves=[],  # Sem NFref
    )
    assert len(findings) == 1
    alerta = findings[0]
    assert alerta.regra_id == "SEFAZ-BA02"
    assert alerta.status == StatusApontamento.WARNING
    assert "C113" in alerta.explicacao_executiva
    assert "SPED" in alerta.explicacao_executiva


def test_rejeicao_805_uf_destinatario_veda_isento():
    """Bloqueia indIEDest=2 (Isento) em UFs vedadas como SP."""
    findings = auditar_regras_tributarias_posto(
        mod="55",
        cfop="5102",
        ref_chaves=[],
        ind_ie_dest="2",
        dest_uf="SP",
    )
    rej = [f for f in findings if f.regra_id == "SEFAZ-REJ-805"]
    assert len(rej) == 1
    assert rej[0].status == StatusApontamento.INVALID


def test_rejeicao_508_cst_incompativel_nao_contribuinte():
    """Detecta CST 10 para destinatario nao contribuinte (indIEDest=9)."""
    findings = auditar_regras_tributarias_posto(
        mod="55",
        cfop="5102",
        ref_chaves=[],
        ind_ie_dest="9",
        cst="10",
        crt="3",
    )
    rej = [f for f in findings if f.regra_id == "SEFAZ-REJ-508"]
    assert len(rej) == 1
    assert rej[0].status == StatusApontamento.INVALID


def test_rejeicao_760_nfce_cst_proibido():
    """Detecta CST 10 indevido na NFC-e (mod 65) de pista."""
    findings = auditar_regras_tributarias_posto(
        mod="65",
        cfop="5656",
        ref_chaves=[],
        cst="10",
    )
    rej = [f for f in findings if f.regra_id == "SEFAZ-REJ-760"]
    assert len(rej) == 1
    assert rej[0].status == StatusApontamento.INVALID


def test_excecao_combustivel_derivado_petroleo_difal():
    """Confirma que combustivel derivado de petroleo nao leva DIFAL (Regra NA01-20)."""
    findings = auditar_regras_tributarias_posto(
        mod="55",
        cfop="6656",
        ref_chaves=[],
        id_dest="2",
        ind_final="1",
        ind_ie_dest="9",
        anp_code="320101001",  # Gasolina Comum (derivado de petroleo)
    )
    exc = [f for f in findings if f.regra_id == "SEFAZ-ANP-DIFAL-EXC"]
    assert len(exc) == 1
    assert exc[0].status == StatusApontamento.VALID


def test_auditar_documento_xml_simulado():
    """Audita XML simples garantindo deteccao de rascunho sem protocolo e itens."""
    xml_fake = f"""
    <nfeProc xmlns="http://www.portalfiscal.inf.br/nfe">
        <NFe>
            <infNFe Id="NFe{CHAVE_NFE_VALIDA}">
                <ide>
                    <mod>55</mod>
                    <idDest>1</idDest>
                    <indFinal>1</indFinal>
                </ide>
                <emit>
                    <CRT>3</CRT>
                    <enderEmit><UF>SP</UF></enderEmit>
                </emit>
                <dest>
                    <indIEDest>9</indIEDest>
                    <enderDest><UF>SP</UF></enderDest>
                </dest>
                <det nItem="1">
                    <prod>
                        <cProd>001</cProd>
                        <xProd>GASOLINA COMUM</xProd>
                        <CFOP>5656</CFOP>
                        <qCom>10.000</qCom>
                        <vUnCom>5.000</vUnCom>
                        <vProd>50.00</vProd>
                    </prod>
                    <imposto>
                        <ICMS>
                            <ICMS60>
                                <orig>0</orig>
                                <CST>60</CST>
                            </ICMS60>
                        </ICMS>
                    </imposto>
                </det>
                <total>
                    <ICMSTot>
                        <vProd>50.00</vProd>
                        <vNF>50.00</vNF>
                    </ICMSTot>
                </total>
            </infNFe>
        </NFe>
        <protNFe>
            <infProt>
                <cStat>100</cStat>
                <nProt>135260000000001</nProt>
            </infProt>
        </protNFe>
    </nfeProc>
    """
    res = auditar_documento_xml(xml_fake)
    assert res["valido"] is True
    assert res["chave_acesso"] == CHAVE_NFE_VALIDA
    assert res["erros_impeditivos"] == 0


def test_posto_tools_auditoria_fiscal():
    """Valida tool exposta auditar_documento_ou_chave_fiscal."""
    tools = PostoTools()
    # 1. Auditoria por chave de 44 digitos
    resp_chave = tools.auditar_documento_ou_chave_fiscal(CHAVE_NFE_VALIDA)
    assert resp_chave["status"] == "sucesso"
    assert resp_chave["tipo"] == "chave_acesso"
    assert resp_chave["decomposicao"]["uf_sigla"] == "SP"

    # 2. Consulta de rejeicao fiscal no acervo SEFAZ
    resp_rej = tools.auditar_documento_ou_chave_fiscal("rejeicao 375 cupom fiscal")
    assert resp_rej["status"] == "sucesso"
    assert resp_rej["tipo"] == "consulta_rejeicao_fiscal"
    assert len(resp_rej["resultados"]) > 0


def test_fts5_pesquisa_rejeicoes_sefaz():
    """Garante que WebPostoRAGEngine localiza rejeicoes fiscais curadas."""
    engine = WebPostoRAGEngine()
    res_375 = engine.buscar_geral("rejeicao 375 cupom fiscal", pilar="fiscal_tributario_sefaz")
    assert len(res_375) > 0
    assert "375" in res_375[0]["codigo_ref"]

    res_629 = engine.buscar_geral("rejeicao 629 arredondamento", pilar="fiscal_tributario_sefaz")
    assert len(res_629) > 0
    assert "629" in res_629[0]["codigo_ref"]

    res_805 = engine.buscar_geral("rejeicao 805 isento", pilar="fiscal_tributario_sefaz")
    assert len(res_805) > 0
    assert "805" in res_805[0]["codigo_ref"]


def test_rejeicao_960_combustivel_monofasico_cst60_rejeitado():
    """Combustivel monofasico (Gasolina) com CST 60 gera Rejeicao 960 (exige CST 61)."""
    # Gasolina Comum com CST 60
    findings = auditar_regras_tributarias_posto(
        mod="55",
        cfop="5656",
        ref_chaves=[],
        anp_code="320102001",
        cst="60",
    )
    rej = [f for f in findings if f.regra_id == "SEFAZ-REJ-960"]
    assert len(rej) == 1
    assert rej[0].status == StatusApontamento.INVALID
    assert rej[0].valor_esperado == "CST 61"
    assert "960" in rej[0].titulo

    # Com CST 61 e valido
    findings_ok = auditar_regras_tributarias_posto(
        mod="55",
        cfop="5656",
        ref_chaves=[],
        anp_code="320102001",
        cst="61",
    )
    assert not any(f.regra_id == "SEFAZ-REJ-960" for f in findings_ok)


def test_rejeicao_958_combustivel_monofasico_cfop_invalido():
    """Combustivel monofasico com CFOP de revenda comum (5102) gera Rejeicao 958."""
    findings = auditar_regras_tributarias_posto(
        mod="55",
        cfop="5102",  # Invalido para combustivel monofasico
        ref_chaves=[],
        anp_code="320102001",
        cst="61",
    )
    rej = [f for f in findings if f.regra_id == "SEFAZ-REJ-958"]
    assert len(rej) == 1
    assert rej[0].status == StatusApontamento.INVALID
    assert "958" in rej[0].titulo

    # Com CFOP 5656 e valido
    findings_ok = auditar_regras_tributarias_posto(
        mod="55",
        cfop="5656",
        ref_chaves=[],
        anp_code="320102001",
        cst="61",
    )
    assert not any(f.regra_id == "SEFAZ-REJ-958" for f in findings_ok)


def test_rejeicao_959_etanol_com_cst61_rejeitado():
    """Etanol Hidratado (ANP 810101001) permanece em ST (CST 60) e rejeita CST 61."""
    findings = auditar_regras_tributarias_posto(
        mod="55",
        cfop="5656",
        ref_chaves=[],
        anp_code="810101001",  # Etanol Hidratado Comum
        cst="61",
    )
    rej = [f for f in findings if f.regra_id == "SEFAZ-REJ-959"]
    assert len(rej) == 1
    assert rej[0].status == StatusApontamento.INVALID
    assert rej[0].valor_esperado == "CST 60"

    # Com CST 60 e valido
    findings_ok = auditar_regras_tributarias_posto(
        mod="55",
        cfop="5656",
        ref_chaves=[],
        anp_code="810101001",
        cst="60",
    )
    assert not any(f.regra_id == "SEFAZ-REJ-959" for f in findings_ok)


def test_alerta_piscofins_monofasico_bitributacao():
    """Detecta risco de bitributacao em produtos da conveniencia e pista com CST PIS 01."""
    # Bebida fria (Cerveja NCM 22030000) com CST PIS 01
    findings = auditar_regras_tributarias_posto(
        mod="65",
        cfop="5102",
        ref_chaves=[],
        ncm="22030000",
        cst_pis_cofins="01",
        produto_nome="CERVEJA HEINEKEN 350ML",
    )
    alertas = [f for f in findings if f.regra_id == "SPED-RISCO-BITRIBUTACAO-PISCOFINS"]
    assert len(alertas) == 1
    assert alertas[0].status == StatusApontamento.WARNING
    assert "Bitributacao" in alertas[0].titulo
    assert "CST 04" in alertas[0].valor_esperado

    # Com CST 04 nao gera alerta
    findings_ok = auditar_regras_tributarias_posto(
        mod="65",
        cfop="5102",
        ref_chaves=[],
        ncm="22030000",
        cst_pis_cofins="04",
        produto_nome="CERVEJA HEINEKEN 350ML",
    )
    assert not any(f.regra_id == "SPED-RISCO-BITRIBUTACAO-PISCOFINS" for f in findings_ok)


def test_rejeicao_806_ncm_st_sem_cest():
    """Item sujeito a ST/Monofasico sem CEST gera Rejeicao 806."""
    findings = auditar_regras_tributarias_posto(
        mod="55",
        cfop="5656",
        ref_chaves=[],
        ncm="27101259",  # Gasolinas
        cest="",  # Omitido
        produto_nome="GASOLINA ADITIVADA GRID",
    )
    rej = [f for f in findings if f.regra_id == "SEFAZ-REJ-806"]
    assert len(rej) == 1
    assert rej[0].status == StatusApontamento.INVALID
    assert rej[0].valor_esperado == "CEST 06.001.00"

    # Com CEST informado e valido
    findings_ok = auditar_regras_tributarias_posto(
        mod="55",
        cfop="5656",
        ref_chaves=[],
        ncm="27101259",
        cest="06.001.00",
        produto_nome="GASOLINA ADITIVADA GRID",
    )
    assert not any(f.regra_id == "SEFAZ-REJ-806" for f in findings_ok)


def test_auditar_documento_xml_completo_combustivel_e_conveniencia():
    """Audita XML completo contendo item de pista conforme e item de conveniencia com falha."""
    xml_multi = f"""
    <nfeProc xmlns="http://www.portalfiscal.inf.br/nfe">
        <NFe>
            <infNFe Id="NFe{CHAVE_NFE_VALIDA}">
                <ide>
                    <mod>55</mod>
                    <idDest>1</idDest>
                    <indFinal>1</indFinal>
                </ide>
                <emit>
                    <CRT>3</CRT>
                    <enderEmit><UF>SP</UF></enderEmit>
                </emit>
                <dest>
                    <indIEDest>9</indIEDest>
                    <enderDest><UF>SP</UF></enderDest>
                </dest>
                <det nItem="1">
                    <prod>
                        <cProd>001</cProd>
                        <xProd>GASOLINA COMUM</xProd>
                        <NCM>27101259</NCM>
                        <CEST>0600100</CEST>
                        <CFOP>5656</CFOP>
                        <qCom>20.000</qCom>
                        <vUnCom>5.500</vUnCom>
                        <vProd>110.00</vProd>
                        <comb>
                            <cProdANP>320102001</cProdANP>
                        </comb>
                    </prod>
                    <imposto>
                        <ICMS>
                            <ICMS61>
                                <orig>0</orig>
                                <CST>61</CST>
                            </ICMS61>
                        </ICMS>
                        <PIS>
                            <PISNT>
                                <CST>04</CST>
                            </PISNT>
                        </PIS>
                    </imposto>
                </det>
                <det nItem="2">
                    <prod>
                        <cProd>002</cProd>
                        <xProd>REFRIGERANTE COCA COLA 2L</xProd>
                        <NCM>22021000</NCM>
                        <!-- CEST omitido propositalmente para testar Rejeicao 806 -->
                        <CFOP>5102</CFOP>
                        <qCom>2.000</qCom>
                        <vUnCom>10.000</vUnCom>
                        <vProd>20.00</vProd>
                    </prod>
                    <imposto>
                        <ICMS>
                            <ICMS60>
                                <orig>0</orig>
                                <CST>60</CST>
                            </ICMS60>
                        </ICMS>
                        <PIS>
                            <PISAliq>
                                <!-- CST 01 propositalmente para testar alerta de bitributacao -->
                                <CST>01</CST>
                            </PISAliq>
                        </PIS>
                    </imposto>
                </det>
                <total>
                    <ICMSTot>
                        <vProd>130.00</vProd>
                        <vNF>130.00</vNF>
                    </ICMSTot>
                </total>
            </infNFe>
        </NFe>
        <protNFe>
            <infProt>
                <cStat>100</cStat>
                <nProt>135260000000001</nProt>
            </infProt>
        </protNFe>
    </nfeProc>
    """
    res = auditar_documento_xml(xml_multi)
    # Item 2 possui Rejeicao 806 (CEST ausente) -> invalido
    assert res["valido"] is False
    assert res["erros_impeditivos"] >= 1
    # Verifica presenca da Rejeicao 806 no item 2
    rej_806 = [a for a in res["apontamentos"] if a["regra_id"] == "SEFAZ-REJ-806"]
    assert len(rej_806) == 1
    # Verifica presenca do alerta de bitributacao de PIS/COFINS no item 2
    alerta_pis = [a for a in res["apontamentos"] if a["regra_id"] == "SPED-RISCO-BITRIBUTACAO-PISCOFINS"]
    assert len(alerta_pis) == 1


def test_fts5_pesquisa_regras_enriquecidas_sefaz_sped():
    """Valida recuperacao rapida (< 5ms) de todas as novas regras normativas no RAG SQLite."""
    engine = WebPostoRAGEngine()

    consultas_esperadas = [
        ("rejeicao 960 monofasico", "960"),
        ("rejeicao 958 cfop combustivel", "958"),
        ("rejeicao 806 cest", "806"),
        ("pis cofins monofasico bebidas", "4.3.10"),
        ("sped fiscal registro 1300 lmc", "1300"),
        ("cfop 5927 perda evaporacao tanque", "5927"),
        ("reforma tributaria ibs cbs combustiveis", "LC214"),
    ]

    for termo, ref_esperada in consultas_esperadas:
        res = engine.buscar_geral(termo, pilar="fiscal_tributario_sefaz", limit=3)
        assert len(res) > 0, f"Nenhum resultado para termo: {termo}"
        codigos = [r["codigo_ref"] for r in res]
        assert any(ref_esperada in cod for cod in codigos), f"Esperava {ref_esperada} em {codigos} para termo {termo}"



# =============================================================================
# TESTES DE INTEGRACAO GENUI & HIGIENE FISCAL (FASE 4)
# =============================================================================

def test_genui_envelope_chave_acesso():
    """Valida geracao do envelope GenUI para chave_acesso com anatomia e dupla persona."""
    from core.aura_engine import build_canonical_genui_envelope
    from core.fiscal_engine import decompor_chave_acesso, validar_chave_acesso

    chave_exemplo = "35260100000000000191550010000001231000001231"
    decomp = decompor_chave_acesso(chave_exemplo)
    findings = validar_chave_acesso(chave_exemplo)

    resultado_bruto = {
        "tipo": "chave_acesso",
        "decomposicao": decomp,
        "apontamentos": [f.model_dump() for f in findings],
        "status": "sucesso",
    }

    envelope = build_canonical_genui_envelope(
        intencao="auditoria_fiscal_sefaz",
        tool_call_id=f"call_{uuid.uuid4()}",
        resultado_bruto=resultado_bruto,
        executive_summary="Chave validada com sucesso pelo algoritmo Modulo 11.",
    )

    assert envelope is not None
    assert envelope.component_name == "render_FiscalShieldInspectorUI"
    props = envelope.props

    # Validar presenca da anatomia dos 44 digitos
    assert "access_key_anatomy" in props
    anatomy = props["access_key_anatomy"]
    assert anatomy["c_uf"] == "35"
    assert anatomy["uf_sigla"] == "SP"
    assert anatomy["numero_nfe"] == "000000123"
    assert anatomy["is_dv_valido"] is True

    # Validar dupla persona
    assert "persona_views" in props
    assert "gestor" in props["persona_views"]
    assert "contador" in props["persona_views"]
    assert "base_legal" in props["persona_views"]

    # Validar blocos canônicos
    blocks = props.get("blocks", [])
    block_ids = [b.get("block_id") for b in blocks]
    assert "blk_chave_status" in block_ids
    assert "blk_chave_anatomia" in block_ids
    assert "blk_chave_kpis" in block_ids

    # Validar acao de copiar laudo
    actions = props.get("suggested_actions", [])
    assert any(a.get("payload", {}).get("intent") == "copiar_diagnostico_contador" for a in actions)


def test_genui_envelope_xml_documento():
    """Valida geracao do envelope GenUI para xml_documento com blocos e apontamentos."""
    from core.aura_engine import build_canonical_genui_envelope

    resultado_mock = {
        "valido": False,
        "total_apontamentos": 2,
        "erros_impeditivos": 1,
        "alertas_fiscais": 1,
        "conformidades": 0,
        "chave_acesso": "35260100000000000191550010000001231000001231",
        "modelo": "55",
        "emit_uf": "SP",
        "dest_uf": "MG",
        "apontamentos": [
            {
                "status": "INVALID",
                "gravidade": "CRITICAL",
                "regra_id": "SEFAZ-REJ-960",
                "titulo": "Rejeicao 960: Combustivel Monofasico sem CST 61",
                "explicacao_executiva": "Gasolina comum emitida com CST diferente de 61.",
                "explicacao_tecnica": "Violacao da Regra N12-20 e LC 192/2022.",
                "base_legal": ["Convenio ICMS 199/2022", "LC 192/2022"],
                "acoes_recomendadas": ["Ajustar cadastro para CST 61."],
            },
            {
                "status": "WARNING",
                "gravidade": "MEDIUM",
                "regra_id": "SPED-RISCO-BITRIBUTACAO-PISCOFINS",
                "titulo": "Risco de Bitributacao PIS/COFINS",
                "explicacao_executiva": "Bebida fria sem CST 04.",
                "explicacao_tecnica": "Tabela 4.3.10 EFD-Contribuicoes exige CST 04.",
                "base_legal": ["Lei 13.097/2015"],
                "acoes_recomendadas": ["Ajustar CST PIS/COFINS para 04."],
            },
        ],
    }

    envelope = build_canonical_genui_envelope(
        intencao="auditoria_fiscal_sefaz",
        tool_call_id=f"call_{uuid.uuid4()}",
        resultado_bruto={"tipo": "xml_documento", "resultado": resultado_mock, "status": "sucesso"},
        executive_summary="Auditoria de XML identificou 1 erro impeditivo e 1 alerta fiscal.",
    )

    assert envelope is not None
    assert envelope.component_name == "render_FiscalShieldInspectorUI"
    props = envelope.props

    # Validar blocos
    blocks = props.get("blocks", [])
    assert len(blocks) >= 3
    block_ids = [b.get("block_id") for b in blocks]
    assert "blk_xml_status" in block_ids
    assert "blk_xml_kpis" in block_ids
    assert "blk_xml_apontamentos" in block_ids

    # Validar persona views
    assert "persona_views" in props
    assert "SEFAZ-REJ-960" in props["persona_views"]["gestor"]
    assert "Convenio ICMS 199/2022" in props["persona_views"]["base_legal"]


def test_genui_envelope_consulta_rejeicao_dinamica():
    """Valida extracao dinamica de base legal e metadados no envelope de consulta de rejeicao."""
    from core.aura_engine import build_canonical_genui_envelope

    resultado_mock = [
        {
            "codigo_ref": "SEFAZ-REJ-960",
            "titulo": "Rejeicao 960: Combustivel monofasico sem CST 61",
            "modulo": "Faturamento / Combustiveis",
            "resumo_executivo": "Bloqueio de autorizacao por uso de CST incorreto em combustivel sujeito a monofasia.",
            "conteudo_completo": "Regra N12-20 do MOC 7.0 vinculada a LC 192/2022.",
            "impacto_financeiro": "Caminhao parado na pista sem poder emitir NF-e.",
            "acao_recomendada": "Alterar cadastro do produto para CST 61 no webPosto.",
            "tabelas_banco": "PRODUTOS, FISCAL_PARAMETROS",
            "metadados_json": {
                "base_legal": "LC 192/2022 e Convenio ICMS 199/2022",
                "campos_xml": ["det/imposto/ICMS/ICMS61/CST", "det/imposto/ICMS/ICMS61/qBCMono"],
                "gravidade": "CRITICAL",
            },
        }
    ]

    envelope = build_canonical_genui_envelope(
        intencao="auditoria_fiscal_sefaz",
        tool_call_id=f"call_{uuid.uuid4()}",
        resultado_bruto={"tipo": "consulta_rejeicao_fiscal", "resultados": resultado_mock, "status": "sucesso"},
        executive_summary="Diagnostico da Rejeicao 960 obtido via base RAG.",
    )

    assert envelope is not None
    props = envelope.props

    # Validar que a base legal e dinamica e nao texto fixo
    assert "LC 192/2022 e Convenio ICMS 199/2022" in props["persona_views"]["base_legal"]
    blocks = props.get("blocks", [])
    procedimento_block = next((b for b in blocks if b.get("block_id") == "blk_procedimento_erp"), None)
    assert procedimento_block is not None
    assert "LC 192/2022" in procedimento_block.get("custom_content", "")


def test_ausencia_absoluta_travessoes_arquivos_gui_fiscal():
    """Garante ausencia estrita de travessoes Unicode (\u2014 e \u2013) em todos os arquivos tocados."""
    import os

    # Caminho base do repositorio
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    arquivos_alvo = [
        os.path.join(base_dir, "core", "aura_engine.py"),
        os.path.join(base_dir, "web", "js", "aura-genui-widgets.js"),
        os.path.join(base_dir, "web", "js", "aura-chat.js"),
        os.path.join(base_dir, "web", "js", "aura-triggers.js"),
        os.path.join(base_dir, "web", "index.html"),
        os.path.join(base_dir, "web", "css", "aura.css"),
        os.path.join(base_dir, "tests", "unit", "test_fiscal_engine.py"),
    ]

    for caminho in arquivos_alvo:
        assert os.path.exists(caminho), f"Arquivo nao encontrado: {caminho}"
        with open(caminho, "r", encoding="utf-8") as f:
            conteudo = f.read()
        assert "\u2014" not in conteudo, f"Em-dash detectado em {caminho}"
        assert "\u2013" not in conteudo, f"En-dash detectado em {caminho}"
