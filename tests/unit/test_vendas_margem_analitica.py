from core.tools import PostoTools
from core.aura_engine import extrair_intervalo_datas, build_canonical_genui_envelope

def test_extrair_intervalo_datas():
    ini, fim = extrair_intervalo_datas("Qual o panorama de faturamento de 01/09/2026 a 30/09/2026?")
    assert ini == "2026-09-01"
    assert fim == "2026-09-30"

    ini, fim = extrair_intervalo_datas("faturamento de setembro")
    assert ini == "2026-09-01"
    assert fim == "2026-09-30"

    ini, fim = extrair_intervalo_datas("faturamento geral no periodo?")
    assert ini is None
    assert fim is None

def test_consultar_analise_vendas_erp_estrutura():
    tools = PostoTools()
    res = tools.consultar_analise_vendas_erp()
    assert res["status"] == "ok"
    assert "periodo" in res
    assert "metricas_consolidadas" in res
    assert "produtos_mais_vendidos" in res
    assert "combustiveis_margem" in res
    assert "meios_pagamento_impacto" in res

    metricas = res["metricas_consolidadas"]
    assert metricas["faturamento_bruto"] > 0
    assert metricas["custo_total"] > 0
    assert metricas["taxas_tef_total"] >= 0
    assert isinstance(metricas["margem_liquida_consolidada_pct"], float)

def test_envelope_genui_vendas_analitico():
    tools = PostoTools()
    res = tools.consultar_analise_vendas_erp()
    env = build_canonical_genui_envelope(
        intencao="vendas_analitico",
        resultado_bruto=res,
        tool_call_id="call_12345678-1234-4234-8234-123456789012",
        executive_summary="Resumo executivo de teste",
    )
    assert env is not None
    props = env.props
    assert props["gross_revenue"] > 0
    assert props["net_profit"] > 0
    assert props["consolidated_margin_pct"] is not None
    assert props["periodo_analisado"] != ""
    assert len(props["top_produtos_margem"]) > 0
    assert len(props["payment_fee_impact"]) > 0
