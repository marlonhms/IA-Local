"""
Testes Unitarios: Cesta de Compras & Cross-Selling da Conveniencia (Market Basket Analysis & Apriori).
Valida o motor analitico deterministico de mineracao de regras de associacao,
combos de alto Lift no PDV, contratos Pydantic (BasketUpsellStrategyProps e UpsellComboItem),
fallback deterministico offline, integracao ao SemanticRouter, AuraEngine e gerador de sintese.
Regra inegociavel: ZERO travessoes em todo o arquivo.
"""

import json
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from core.aura_engine import AuraEngine
from core.schemas.genui import BasketUpsellStrategyProps, UpsellComboItem
from core.schemas.market_basket import MarketBasketComboItem
from core.semantic_router import classificar_intencao_heuristica
from core.tools import PostoTools


@pytest.fixture
def posto_tools():
    return PostoTools(rag_engine=MagicMock())


@pytest.fixture
def aura_engine(posto_tools):
    mock_rag = MagicMock()
    mock_router = MagicMock()
    return AuraEngine(rag_engine=mock_rag, router=mock_router, tools=posto_tools)


def test_auditar_cesta_conveniencia_real_erp(posto_tools):
    """Valida a consulta do motor deterministico de cesta de compras no ERP PostgreSQL real."""
    resultado = posto_tools.auditar_cesta_conveniencia_vendas_cruzadas()

    assert resultado["status"] == "ok"
    assert resultado["intent"] == "conveniencia_vendas_cruzadas"
    assert resultado["component_name"] == "render_BasketUpsellStrategyUI"
    assert resultado["client_component"] == "BasketUpsellStrategyUI"
    assert resultado["fonte_dados"] in ("ERP_POSTGRESQL", "AUDITORIA_CALIBRADA")

    # Validacao estrita do contrato Pydantic canônico
    props = BasketUpsellStrategyProps(**resultado["props"])
    assert props.confidence_score >= 0.85
    assert props.confidence_score <= 1.0
    assert len(props.diagnosis) > 0
    assert len(props.suggested_actions) == 3
    assert len(props.limitations) >= 2
    assert props.total_transacoes is not None and props.total_transacoes > 0
    assert props.pct_multiplos_itens is not None and props.pct_multiplos_itens >= 0.0
    assert props.maior_lift is not None and props.maior_lift >= 0.0

    # Verifica integridade dos combos minerados no ERP
    assert len(props.top_combos) > 0
    for combo in props.top_combos:
        assert isinstance(combo, UpsellComboItem)
        assert len(combo.anchor_product) > 0
        assert len(combo.recommended_product) > 0
        assert combo.lift >= 0.0
        assert 0.0 <= combo.confidence_pct <= 100.0
        assert 0.0 <= combo.support_pct <= 100.0
        assert len(combo.script_pitch) > 0

    # Verifica presenca das 3 acoes HITL mandatorias
    action_labels = [a.label for a in props.suggested_actions]
    assert any("Ativar Combo no PDV" in label for label in action_labels)
    assert any("Lancar Campanha Frentistas" in label or "Lançar Campanha Frentistas" in label for label in action_labels)
    assert any("Simular no Canvas" in label for label in action_labels)

    # Verifica chaves analiticas preservadas
    assert "metrics" in resultado
    assert "detailed_rules" in resultado
    assert "assessment" in resultado
    assert "context" in resultado


def test_auditar_cesta_conveniencia_fallback_offline(posto_tools):
    """Valida a execucao deterministica em cenario de banco indisponivel (offline)."""
    with patch("core.tools.get_erp_connection", side_effect=Exception("DB Offline")):
        resultado = posto_tools.auditar_cesta_conveniencia_vendas_cruzadas()

    assert resultado["status"] == "ok"
    assert resultado["intent"] == "conveniencia_vendas_cruzadas"
    assert resultado["component_name"] == "render_BasketUpsellStrategyUI"
    assert resultado["client_component"] == "BasketUpsellStrategyUI"
    assert resultado["fonte_dados"] == "AUDITORIA_CALIBRADA"

    props = BasketUpsellStrategyProps(**resultado["props"])
    assert props.confidence_score >= 0.85
    assert len(props.diagnosis) > 0
    assert len(props.top_combos) >= 3
    assert len(props.suggested_actions) == 3
    assert len(props.limitations) >= 2
    assert props.total_transacoes == 1250
    assert props.maior_lift >= 2.0


def test_basket_upsell_pydantic_contracts_and_normalizers():
    """Valida schemas Pydantic v2 UpsellComboItem e BasketUpsellStrategyProps com aliases e normalizacao."""
    # 1. Instanciacao canonica com nomes em ingles
    item_direct = UpsellComboItem(
        anchor_product="Cafe Expresso",
        recommended_product="Pao de Queijo",
        lift=3.5,
        confidence_pct=45.0,
        support_pct=12.5,
        additional_ticket_reais=7.50,
        script_pitch="Ofereca pao de queijo quentinho.",
        category="Balcao PDV"
    )
    assert item_direct.anchor_product == "Cafe Expresso"
    assert item_direct.recommended_product == "Pao de Queijo"

    # 2. Instanciacao via aliases do MarketBasketComboItem (compatibilidade retroativa)
    item_alias = UpsellComboItem(
        produto_origem="Gasolina Aditivada",
        produto_recomendado="Aditivo STP",
        lift=2.8,
        confianca_pct=38.0,
        suporte_conjunto_pct=10.0,
        ticket_recomendado_reais=25.0,
        script_sugerido_caixa="Ofereca aditivo na pista."
    )
    assert item_alias.anchor_product == "Gasolina Aditivada"
    assert item_alias.recommended_product == "Aditivo STP"
    assert item_alias.confidence_pct == 38.0
    assert item_alias.support_pct == 10.0
    assert item_alias.additional_ticket_reais == 25.0
    assert item_alias.script_pitch == "Ofereca aditivo na pista."

    # 3. Normalizacao automatica em BasketUpsellStrategyProps recebendo dicionarios mistos
    props = BasketUpsellStrategyProps(
        diagnosis="Diagnostico de vendas cruzadas",
        confidence_score=0.92,
        projected_ticket_increase=10.50,
        top_combos=[
            {
                "produto_origem": {"nompro": "Cerveja 6-pack"},
                "produto_recomendado": {"nompro": "Gelo 5kg"},
                "lift": 3.1,
                "confianca_pct": 55.0,
                "suporte_conjunto_pct": 18.0,
                "ticket_recomendado_reais": 15.0,
                "script_sugerido_caixa": "Sugira saco de gelo."
            },
            item_direct,
        ]
    )
    assert len(props.top_combos) == 2
    assert props.top_combos[0].anchor_product == "Cerveja 6-pack"
    assert props.top_combos[0].recommended_product == "Gelo 5kg"
    assert props.top_combos[1].anchor_product == "Cafe Expresso"

    # 4. Validacao de campos obrigatorios e limites
    with pytest.raises(ValidationError):
        BasketUpsellStrategyProps(
            diagnosis="",  # Diagnosis vazio rejeitado
            confidence_score=0.90,
            projected_ticket_increase=5.0
        )

    with pytest.raises(ValidationError):
        UpsellComboItem(
            anchor_product="Item A",
            recommended_product="Item B",
            lift=-1.0,  # Lift negativo invalido
            confidence_pct=50.0,
            support_pct=10.0,
            script_pitch="Teste"
        )


def test_gerar_diagnostico_mentoria_executiva_delegation(posto_tools):
    """Valida delegacao direta de gerar_diagnostico_mentoria_executiva sem dados mock hardcoded."""
    aliases = [
        "conveniencia_vendas_cruzadas",
        "vendas_cruzadas",
        "basket_upsell",
        "cross_selling",
        "market_basket",
        "cesta_compras",
    ]
    for tipo_alias in aliases:
        res = posto_tools.gerar_diagnostico_mentoria_executiva(tipo=tipo_alias)
        assert res["status"] == "ok"
        assert res["component_name"] == "render_BasketUpsellStrategyUI"
        assert res["client_component"] == "BasketUpsellStrategyUI"
        assert "props" in res
        props = BasketUpsellStrategyProps(**res["props"])
        assert len(props.diagnosis) > 0
        assert len(props.top_combos) > 0


def test_semantic_router_cesta_conveniencia_queries():
    """Valida a classificacao heuristica do SemanticRouter para intencoes de cesta e vendas cruzadas."""
    frases_teste = [
        "market basket analysis da conveniencia",
        "analisar cesta de compras da loja",
        "quais produtos vendem juntos no pdv?",
        "quais itens saem juntos com cerveja?",
        "rodar algoritmo apriori nos cupons",
        "regras de associacao e afinidade de produtos",
        "sugestoes de cross-selling no caixa",
        "basket upsell da conveniencia",
        "o que mais vende junto com cafe?",
        "vendas cruzadas para aumentar o ticket medio",
        "combos da conveniencia recomendados",
    ]
    for frase in frases_teste:
        intencao = classificar_intencao_heuristica(frase)
        assert intencao == "conveniencia_vendas_cruzadas", f"Frase '{frase}' roteou para '{intencao}'"


@pytest.mark.asyncio
async def test_aura_engine_execute_tool_direct_basket(posto_tools):
    """Valida a execucao direta de ferramenta no AuraEngine para cesta de compras e seus aliases."""
    engine = AuraEngine(tools=posto_tools)

    # 1. Execucao direta com nome oficial
    res = await engine.execute_tool_direct(
        tool_name="conveniencia_vendas_cruzadas",
        params={"min_lift": 1.2, "limit": 5},
    )
    assert res["status"] == "success"
    assert res["tool_name"] == "conveniencia_vendas_cruzadas"
    assert "data" in res
    data_res = res["data"]
    assert data_res["component_name"] == "render_BasketUpsellStrategyUI"
    assert data_res["client_component"] == "BasketUpsellStrategyUI"
    assert "props" in data_res

    # 2. Execucao de todos os aliases registrados
    aliases = [
        "market_basket",
        "cesta_compras",
        "basket_upsell",
        "cross_selling",
        "auditar_cesta_conveniencia_vendas_cruzadas",
        "vendas_cruzadas",
    ]
    for alias in aliases:
        res_alias = await engine.execute_tool_direct(tool_name=alias, params={})
        assert res_alias["status"] == "success"
        assert res_alias["data"]["component_name"] == "render_BasketUpsellStrategyUI"


def test_aura_engine_sintese_contingencia_and_build_response_text(posto_tools):
    """Valida a formatacao da sintese executiva deterministica no AuraEngine."""
    engine = AuraEngine(tools=posto_tools)
    resultado = posto_tools.auditar_cesta_conveniencia_vendas_cruzadas()

    sintese = engine._gerar_sintese_contingencia_ferramenta(
        intencao="conveniencia_vendas_cruzadas",
        resultado_bruto=resultado,
        pergunta="Quais sao as melhores vendas cruzadas da conveniencia?",
    )
    assert sintese is not None
    assert "Inteligência de Vendas Cruzadas" in sintese or "Inteligencia de Vendas Cruzadas" in sintese
    assert "Maior Lift Apurado" in sintese
    assert "Combos Minerados" in sintese

    # Valida _build_response_text
    resp_text = engine._build_response_text("market_basket", resultado)
    assert resp_text is not None
    assert "Maior Lift Apurado" in resp_text


def test_no_em_dash_or_en_dash_in_cesta_artifacts(posto_tools):
    """Regra inegociavel: ZERO travessoes em todos os payloads e textos gerados."""
    resultado = posto_tools.auditar_cesta_conveniencia_vendas_cruzadas()
    json_str = json.dumps(resultado, ensure_ascii=False)

    assert "\u2014" not in json_str, "Payload contem travessao em-dash proibido!"
    assert "\u2013" not in json_str, "Payload contem travessao en-dash proibido!"

    engine = AuraEngine(tools=posto_tools)
    sintese = engine._gerar_sintese_contingencia_ferramenta(
        intencao="conveniencia_vendas_cruzadas",
        resultado_bruto=resultado,
        pergunta="Quais combos oferecer no caixa?",
    )
    assert sintese is not None
    assert "\u2014" not in sintese, "Sintese contem travessao em-dash proibido!"
    assert "\u2013" not in sintese, "Sintese contem travessao en-dash proibido!"


def test_auditar_cesta_conveniencia_filtro_produto(posto_tools):
    """Valida a mineracao direcionada por SKU/nome de produto."""
    resultado = posto_tools.auditar_cesta_conveniencia_vendas_cruzadas(filtro_produto="cerveja")
    assert resultado["status"] == "ok"
    assert "top_combos" in resultado
    props = BasketUpsellStrategyProps(**resultado["props"])
    assert len(props.top_combos) > 0
    for c in props.top_combos:
        comb_text = f"{c.anchor_product} {c.recommended_product}".lower()
        assert "cerveja" in comb_text


def test_auditar_cesta_conveniencia_periodo_sem_vendas(posto_tools):
    """Valida comportamento defensivo para periodo sem transacoes emitidas."""
    resultado = posto_tools.auditar_cesta_conveniencia_vendas_cruzadas(
        data_inicio="2000-01-01",
        data_fim="2000-01-02"
    )
    assert resultado["status"] == "ok"
    props = BasketUpsellStrategyProps(**resultado["props"])
    assert props.total_transacoes == 0
    assert len(props.top_combos) == 0
    assert "Nenhuma venda registrada" in props.diagnosis


def test_auditar_cesta_conveniencia_min_lift_elevado(posto_tools):
    """Valida comportamento com limiar de Lift inatingivel."""
    resultado = posto_tools.auditar_cesta_conveniencia_vendas_cruzadas(min_lift=100.0)
    assert resultado["status"] == "ok"
    props = BasketUpsellStrategyProps(**resultado["props"])
    assert len(props.top_combos) == 0


def test_auditar_cesta_conveniencia_limit_restrito(posto_tools):
    """Valida parametro limit restringindo a quantidade de combos retornados."""
    resultado = posto_tools.auditar_cesta_conveniencia_vendas_cruzadas(limit=2)
    assert resultado["status"] == "ok"
    props = BasketUpsellStrategyProps(**resultado["props"])
    assert len(props.top_combos) <= 2


def test_auditar_cesta_conveniencia_fallback_offline_com_filtro(posto_tools):
    """Valida fallback offline aplicando filtro de produto."""
    with patch("core.tools.get_erp_connection", side_effect=Exception("DB Offline")):
        resultado = posto_tools.auditar_cesta_conveniencia_vendas_cruzadas(filtro_produto="aditivo")
    assert resultado["status"] == "ok"
    props = BasketUpsellStrategyProps(**resultado["props"])
    assert len(props.top_combos) >= 1
    assert any("aditivo" in f"{c.anchor_product} {c.recommended_product}".lower() for c in props.top_combos)


def test_basket_upsell_raw_dict_and_model_validate():
    """Valida normalizacao de dicionarios brutos da mineracao Apriori e compatibilidade Pydantic v2."""
    raw_apriori = {
        "produto_origem": {"codpro": "00002", "nompro": "Gasolina Aditivada", "preco": 7.29},
        "produto_recomendado": {"codpro": "00088", "nompro": "Aditivo Flex STP", "preco": 29.90},
        "metricas": {"suporte": 0.158, "confianca": 0.420, "lift": 3.45, "frequencia_conjunta": 197},
        "impacto_financeiro": {"preco_origem": 7.29, "preco_recomendado": 29.90, "incremento_ticket_reais": 29.90, "incremento_ticket_pct": 52.3},
        "script_sugerido_caixa": "Cliente abastecendo aditivada: ofereca descarbonizante de bicos na promocao.",
        "categoria": "Pista + Aditivo",
    }
    mb_item = MarketBasketComboItem(
        produto_origem="Cafe Espresso",
        produto_recomendado="Pao de Queijo Tradicional",
        suporte_conjunto_pct=28.4,
        confianca_pct=68.5,
        lift=4.12,
        cupons_conjuntos=355,
        ticket_origem_reais=5.50,
        ticket_recomendado_reais=7.50,
        script_sugerido_caixa="Ofereca combo matinal.",
        forte_sinergia=True,
    )

    # 1. Validacao direta do dicionario bruto
    item_from_raw = UpsellComboItem.model_validate(raw_apriori)
    assert item_from_raw.anchor_product == "Gasolina Aditivada"
    assert item_from_raw.recommended_product == "Aditivo Flex STP"
    assert item_from_raw.lift == 3.45
    assert item_from_raw.confidence_pct == 42.0
    assert item_from_raw.support_pct == 15.8
    assert item_from_raw.additional_ticket_reais == 29.90
    assert item_from_raw.category == "Pista + Aditivo"

    # 2. Validacao do schema oficial MarketBasketComboItem
    item_from_mb = UpsellComboItem.model_validate(mb_item)
    assert item_from_mb.anchor_product == "Cafe Espresso"
    assert item_from_mb.recommended_product == "Pao de Queijo Tradicional"
    assert item_from_mb.lift == 4.12
    assert item_from_mb.confidence_pct == 68.5

    # 3. Propriedades completas com apelidos e tipos mistos
    props = BasketUpsellStrategyProps(
        diagnostico="Excelente sinergia apurada",
        confianca=0.96,
        incremento_ticket_medio=12.50,
        top_combos_cross_selling=[raw_apriori, mb_item, item_from_raw],
    )
    assert len(props.top_combos) == 3
    assert props.diagnosis == "Excelente sinergia apurada"
    assert props.confidence_score == 0.96
    assert props.projected_ticket_increase == 12.50


def test_build_canonical_genui_envelope_legacy_preserves_kpis():
    """Valida que build_canonical_genui_envelope propaga os KPIs sinteticos mesmo a partir de payloads legados."""
    import uuid
    from core.aura_engine import build_canonical_genui_envelope

    legacy_payload = {
        "top_combos_cross_selling": [
            {
                "produto_origem": {"codpro": "00002", "nompro": "Gasolina Aditivada", "preco": 7.29},
                "produto_recomendado": {"codpro": "00088", "nompro": "Aditivo Flex STP", "preco": 29.90},
                "metricas": {"suporte": 0.158, "confianca": 0.420, "lift": 3.45, "frequencia_conjunta": 197},
                "impacto_financeiro": {"preco_origem": 7.29, "preco_recomendado": 29.90, "incremento_ticket_reais": 29.90, "incremento_ticket_pct": 52.3},
                "script_sugerido_caixa": "Ofereca aditivo.",
                "categoria": "Pista + Aditivo",
            }
        ],
        "resumo_executivo": {
            "total_transacoes_analisadas": 1250,
            "total_transacoes_multiplos_itens": 812,
            "pct_cestas_multiplos_itens": 64.96,
            "maior_lift_encontrado": 3.45,
            "regras_com_forte_sinergia_lift_2": 1,
            "diagnostico_estrategico": "Diagnostico de teste",
        }
    }

    envelope = build_canonical_genui_envelope(
        intencao="conveniencia_vendas_cruzadas",
        tool_call_id=str(uuid.uuid4()),
        resultado_bruto=legacy_payload,
        executive_summary="Resumo de auditoria executiva",
    )

    assert envelope is not None
    assert envelope.client_component == "BasketUpsellStrategyUI"
    assert envelope.props.get("total_transacoes") == 1250
    assert envelope.props.get("pct_multiplos_itens") == 64.96
    assert envelope.props.get("maior_lift") == 3.45
    assert envelope.props.get("regras_forte_sinergia_count") == 1


def test_aura_engine_sintese_contingencia_with_pydantic_props(posto_tools):
    """Valida geracao de sintese textual quando resultado_bruto e um modelo Pydantic BasketUpsellStrategyProps."""
    engine = AuraEngine(tools=posto_tools)
    resultado = posto_tools.auditar_cesta_conveniencia_vendas_cruzadas()
    props_obj = BasketUpsellStrategyProps(**resultado["props"])

    sintese = engine._gerar_sintese_contingencia_ferramenta(
        intencao="conveniencia_vendas_cruzadas",
        resultado_bruto=props_obj,
        pergunta="Como aumentar vendas cruzadas no PDV?",
    )
    assert sintese is not None
    assert "Inteligência de Vendas Cruzadas" in sintese or "Inteligencia de Vendas Cruzadas" in sintese
    assert "Maior Lift Apurado" in sintese
    assert "Combos Minerados" in sintese


def test_auditar_cesta_conveniencia_filtro_produto_inexistente(posto_tools):
    """Valida comportamento defensivo para filtro de produto que nao existe no cadastro."""
    resultado = posto_tools.auditar_cesta_conveniencia_vendas_cruzadas(filtro_produto="produto_inexistente_xyz_999")
    assert resultado["status"] == "ok"
    assert resultado["intent"] == "conveniencia_vendas_cruzadas"
    props = BasketUpsellStrategyProps(**resultado["props"])
    assert len(props.top_combos) == 0
    assert len(props.suggested_actions) == 3
