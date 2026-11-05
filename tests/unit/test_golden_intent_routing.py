"""
Golden Dataset de Testes de Regressao de Roteamento Semantico e Fast-Path (Fase 5).
Valida 35 perguntas reais de operadores cobrindo Fiscal, Pista, Turnos, Tanques, LMC e TEF.
Assegura que nenhuma melhoria fiscal cause regressao em consultas de pista ou vice-versa.
Regra inegociavel: ZERO travessoes em todo o modulo.
"""

import pytest

from core.semantic_router import SemanticRouter

# Golden Dataset de 35 Casos de Teste Reais de Posto
GOLDEN_DATASET_QUERIES = [
    # 1. Auditoria Fiscal e Regras SEFAZ (10 casos obrigatorios)
    (
        "Quais os pontos criticos de ICMS Monofasico CST 61, PIS/COFINS CST 04 na conveniencia e rejeicoes SEFAZ?",
        ["auditoria_fiscal_sefaz"],
        ["mentoria_decisao", "previsao_tanques", "estoque_posicao"],
    ),
    (
        "Minha nota deu rejeicao 960 na SEFAZ, o que e?",
        ["auditoria_fiscal_sefaz"],
        ["mentoria_decisao", "ajuda_sistema"],
    ),
    (
        "Qual o CST e CFOP correto para revenda de Gasolina Monofasica segundo a LC 192?",
        ["auditoria_fiscal_sefaz"],
        ["mentoria_decisao", "previsao_tanques"],
    ),
    (
        "Como funciona PIS e COFINS monofasico na loja de conveniencia?",
        ["auditoria_fiscal_sefaz"],
        ["conveniencia_vendas_cruzadas", "mentoria_decisao"],
    ),
    (
        "Rejeicao 806 falta do codigo CEST obrigatorio",
        ["auditoria_fiscal_sefaz"],
        ["ajuda_sistema", "procedimento_erp"],
    ),
    (
        "Auditar chave de acesso 35261001173538000160550040000039571624115433",
        ["auditoria_fiscal_sefaz"],
        ["ajuda_sistema", "catalogo_produtos"],
    ),
    (
        "Como calcular o DIFAL interestadual para combustiveis?",
        ["auditoria_fiscal_sefaz"],
        ["mentoria_decisao", "previsao_tanques"],
    ),
    (
        "O que significa a Rejeicao 958 de CFOP incompativel em combustivel?",
        ["auditoria_fiscal_sefaz"],
        ["mentoria_decisao", "estoque_posicao"],
    ),
    (
        "Nota fiscal de frota travada na SEFAZ com erro 375",
        ["auditoria_fiscal_sefaz"],
        ["auditoria_turno", "ajuda_sistema"],
    ),
    (
        "Regime monofasico de IBS e CBS na reforma tributaria LC 214",
        ["auditoria_fiscal_sefaz"],
        ["mentoria_decisao", "catalogo_produtos"],
    ),

    # 2. Procedimentos Operacionais do ERP (5 casos)
    (
        "Como dar entrada de nota fiscal de mercadoria no erp?",
        ["procedimento_erp"],
        ["auditoria_fiscal_sefaz"],
    ),
    (
        "Passo a passo para emitir nfe de frota no sistema",
        ["procedimento_erp"],
        ["auditoria_fiscal_sefaz"],
    ),
    (
        "Como fazer a importacao do xml de compra de combustivel?",
        ["procedimento_erp"],
        ["auditoria_fiscal_sefaz"],
    ),
    (
        "Onde configuro o rateio de frete na entrada de nota?",
        ["procedimento_erp"],
        ["auditoria_fiscal_sefaz"],
    ),
    (
        "Como funciona a tela de cadastro de produto no retaguarda?",
        ["procedimento_erp"],
        ["auditoria_fiscal_sefaz"],
    ),

    # 3. Tanques, Estoque e Autonomia (5 casos)
    (
        "Quantos dias de autonomia de Gasolina Comum restam nos tanques?",
        ["previsao_tanques", "previsao_runout_estoque", "estoque_posicao"],
        ["auditoria_fiscal_sefaz"],
    ),
    (
        "Qual o volume atual do tanque 2 de Diesel S10?",
        ["previsao_tanques", "previsao_runout_estoque", "estoque_posicao"],
        ["auditoria_fiscal_sefaz"],
    ),
    (
        "Previsao de runout e esgotamento dos tanques de combustivel",
        ["previsao_tanques", "previsao_runout_estoque"],
        ["auditoria_fiscal_sefaz"],
    ),
    (
        "Quanto sobrou no tanque 1 de etanol hoje?",
        ["previsao_tanques", "previsao_runout_estoque", "estoque_posicao"],
        ["auditoria_fiscal_sefaz"],
    ),
    (
        "Nivel fisico dos tanques medido pela sonda",
        ["previsao_tanques", "previsao_runout_estoque", "estoque_posicao"],
        ["auditoria_fiscal_sefaz"],
    ),

    # 4. Auditoria de Fechamento de Turno e Caixa (5 casos)
    (
        "Como ficou o fechamento do 1o turno de ontem?",
        ["auditoria_turno", "auditoria_turno_caixa"],
        ["auditoria_fiscal_sefaz"],
    ),
    (
        "Teve diferenca de caixa ou furo no turno da manha?",
        ["auditoria_turno", "auditoria_turno_caixa", "auditoria_fuga_financeira"],
        ["auditoria_fiscal_sefaz"],
    ),
    (
        "Auditoria de sangria e diferencas de fechamento de pista",
        ["auditoria_turno", "auditoria_turno_caixa", "pos_audit"],
        ["auditoria_fiscal_sefaz"],
    ),
    (
        "Conferencia de faturamento e encerramentos do turno 2",
        ["auditoria_turno", "auditoria_turno_caixa"],
        ["auditoria_fiscal_sefaz"],
    ),
    (
        "Relatorio de caixa fechado pelo operador do PDV 1",
        ["auditoria_turno", "auditoria_turno_caixa", "procedimento_erp", "formas_pagamento"],
        ["auditoria_fiscal_sefaz"],
    ),

    # 5. LMC e Tolerancia Regulamentar ANP (4 casos)
    (
        "O LMC de ontem fechou dentro da tolerancia de 0,6% da ANP?",
        ["lmc_anp", "auditar_conformidade_lmc_anp"],
        ["auditoria_fiscal_sefaz", "mentoria_decisao"],
    ),
    (
        "Relatorio do Livro de Movimentacao de Combustiveis da Portaria 26",
        ["lmc_anp", "auditar_conformidade_lmc_anp"],
        ["auditoria_fiscal_sefaz"],
    ),
    (
        "Qual foi a variacao volumetrica escriturada do LMC?",
        ["lmc_anp", "auditar_conformidade_lmc_anp"],
        ["auditoria_fiscal_sefaz"],
    ),
    (
        "Teve ganho termico ou quebra no LMC acima de 0.6 por cento?",
        ["lmc_anp", "auditar_conformidade_lmc_anp"],
        ["auditoria_fiscal_sefaz"],
    ),

    # 6. Mentoria Executiva e Margem (3 casos)
    (
        "Qual o impacto do diesel S10 na margem bruta do posto?",
        ["mentoria_decisao", "raio_x_causal_margem", "investigar_causa_raiz", "catalogo_produtos"],
        ["auditoria_fiscal_sefaz"],
    ),
    (
        "Diagnostico de rentabilidade e pontos de atencao da pista",
        ["mentoria_decisao", "raio_x_causal_margem"],
        ["auditoria_fiscal_sefaz"],
    ),
    (
        "Qual a projecao de retorno e diagnostico de ROI da operacao?",
        ["roi_diagnostic", "mentoria_decisao"],
        ["auditoria_fiscal_sefaz"],
    ),

    # 7. Formas de Pagamento e Meios de Captura (3 casos)
    (
        "Quais foram as formas de pagamento do dia de hoje?",
        ["formas_pagamento"],
        ["auditoria_fiscal_sefaz"],
    ),
    (
        "Quanto entrou em dinheiro, debito, credito e pix no caixa?",
        ["formas_pagamento"],
        ["auditoria_fiscal_sefaz"],
    ),
    (
        "Detalhamento de vendas por forma de pagamento e operador",
        ["formas_pagamento"],
        ["auditoria_fiscal_sefaz"],
    ),
]


@pytest.fixture(scope="module")
def router_instance():
    """Instancia compartilhada do SemanticRouter para a suite de testes."""
    return SemanticRouter()


@pytest.mark.parametrize("query,expected_intents,forbidden_intents", GOLDEN_DATASET_QUERIES)
def test_golden_dataset_intent_routing(router_instance, query, expected_intents, forbidden_intents):
    """
    Executa validacao estrita de cada uma das 35 perguntas do Golden Dataset.
    Garante que a intencao casada esteja na lista esperada e NUNCA na lista proibida.
    """
    intencao, confianca, telemetria = router_instance.route(query, use_cache=False)

    assert intencao not in forbidden_intents, (
        f"Regressao detectada! Pergunta '{query}' casou com intencao PROIBIDA '{intencao}'. "
        f"Esperadas: {expected_intents} | Telemetria: {telemetria}"
    )

    assert intencao in expected_intents, (
        f"Falha de roteamento! Pergunta '{query}' casou com '{intencao}', "
        f"mas era esperado um de: {expected_intents}. Confianca: {confianca} | Telemetria: {telemetria}"
    )

    # Perguntas fiscais devem ter alta confianca (>= 0.90)
    if "auditoria_fiscal_sefaz" in expected_intents:
        assert confianca >= 0.90, (
            f"Confianca fiscal insuficiente ({confianca}) para '{query}'"
        )
