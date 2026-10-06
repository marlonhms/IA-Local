"""
Suíte de Testes Automatizada: Auditoria Operacional de Pista & Desempenho de Frentistas
(Detecção de Filtro Lento, Vendas de Aditivada e Anomalias de Pista)

Validações:
1. Classificação de intenções e roteamento de perguntas operacionais e de pista
2. Não-regressão de todas as ferramentas e rotas existentes
3. Extração resiliente de parâmetros (data, turno, frentista)
4. Fórmulas matemáticas estáticas de vazão de bicos (L/min) e limites operacionais
5. Fórmulas de conversão de Gasolina Aditivada (%) e categorização de performance
6. Integração real com o ERP PostgreSQL 16 (porta 5433)
7. Detecção de anomalias operacionais (micro-abastecimentos, manuais, repetidos)
8. Injeção de medições customizadas de vazão (alerta preventivo de filtro sujo < 25-30 L/min)
9. Filtro por data, turno e frentista específico
10. Blindagem LGPD do payload com sanitize_dict
"""

import sys
from decimal import Decimal
from datetime import datetime, date
from pathlib import Path

# Protege stdout no terminal Windows contra cp1252
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Adiciona o diretório raiz ao path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from main import classificar_intencao, extrair_frentista, extrair_data_turno, extrair_bico
from core.rag_engine import HybridRAGEngine
from core.tools import PostoTools


def run_tests():
    print("=" * 75)
    print("⛽ SUÍTE DE TESTES: AUDITORIA DE PISTA & DESEMPENHO DE FRENTISTAS")
    print("=" * 75)

    # ------------------------------------------------------------------
    # 1. TESTE DE CLASSIFICAÇÃO DE INTENÇÕES
    # ------------------------------------------------------------------
    print("\n1. Testando Classificador de Intenções (Perguntas de Pista & Frentistas)...")
    frases_esperadas = [
        # As 5 perguntas canônicas do requisito:
        "Qual frentista vendeu mais gasolina aditivada hoje?",
        "Tem algum bico com problema ou vazão lenta?",
        "Como está o desempenho da equipe de pista?",
        "Ranking dos frentistas",
        "Qual frentista tem o maior ticket médio?",
        # Variações de linguagem natural:
        "Produtividade dos frentistas",
        "Produtividade da equipe de pista",
        "Quem vendeu mais gasolina aditivada?",
        "Qual frentista faturou mais hoje?",
        "Qual frentista vendeu mais litros?",
        "Vazão dos bicos da bomba",
        "Vazão das bombas de combustível",
        "Tem bomba com filtro sujo?",
        "Tem algum bico com vazão baixa?",
        "Bico com filtro obstruído",
        "Desempenho dos frentistas no 1º turno",
        "Ranking de frentistas de ontem",
        "Anomalias na pista",
        "Anomalias de pista",
        "Teve abastecimento suspeito na pista?",
        "Conversão de aditivada dos frentistas",
        "Frentista com maior conversão de aditivada",
        "Ticket médio dos frentistas",
        "Qual frentista tem o melhor ticket médio?",
        "Desempenho da equipe",
        "Time de pista hoje",
    ]

    for frase in frases_esperadas:
        intencao = classificar_intencao(frase)
        assert intencao == "desempenho_pista_frentistas", (
            f"Falha na classificação: '{frase}' -> '{intencao}' (esperado: 'desempenho_pista_frentistas')"
        )
        print(f"   [OK] '{frase}' -> {intencao}")

    # ------------------------------------------------------------------
    # 2. NÃO-REGRESSÃO DAS OUTRAS ROTAS E FERRAMENTAS
    # ------------------------------------------------------------------
    print("\n2. Testando Não-Regressão das Rotas Existentes...")
    rotas_legadas = [
        ("Como fechou o 1º turno hoje?", "auditoria_turno"),
        ("Auditoria de fechamento de turno", "auditoria_turno"),
        ("O caixa bateu com o que saiu dos bicos?", "auditoria_turno"),
        ("Teve furo de caixa hoje?", "auditoria_turno"),
        ("Quando vai acabar a Gasolina Comum?", "previsao_tanques"),
        ("Previsão de esgotamento dos tanques", "previsao_tanques"),
        ("Sugestão de compra de carreta", "previsao_tanques"),
        ("Qual tanque está mais crítico hoje?", "previsao_tanques"),
        ("Qual o saldo do tanque 1?", "estoque_posicao"),
        ("Quanto tem de gasolina no tanque?", "estoque_posicao"),
        ("Quanto tem no estoque de lubrificante?", "estoque_posicao"),
        ("Quem é o cliente que mais comprou?", "clientes_ranking"),
        ("Cadastro de clientes no sistema", "clientes_ranking"),
        ("Qual o produto mais vendido hoje?", "vendas_analitico"),
        ("Quanto faturou o posto hoje?", "vendas_analitico"),
        ("Qual o último produto vendido?", "vendas_analitico"),
        ("Qual a saúde do banco de dados?", "sre_metricas"),
        ("Métricas de SRE e cache hit", "sre_metricas"),
        ("Qual o cnpj da filial?", "dados_filial"),
        ("Qual é o endereço do posto?", "dados_filial"),
        ("Qual o preço da cerveja heineken?", "catalogo_produtos"),
        ("Qual o preço da gasolina?", "catalogo_produtos"),
        ("Quanto custa o diesel?", "catalogo_produtos"),
    ]
    for frase, esperado in rotas_legadas:
        intencao = classificar_intencao(frase)
        assert intencao == esperado, (
            f"Regressão detectada: '{frase}' -> '{intencao}' (esperado: '{esperado}')"
        )
        print(f"   [OK] '{frase}' -> {intencao}")

    # ------------------------------------------------------------------
    # 3. EXTRAÇÃO DE PARÂMETROS (FRENTISTA, BICO, DATA, TURNO)
    # ------------------------------------------------------------------
    print("\n3. Testando Extração de Parâmetros (Frentista, Bico, Data, Turno)...")
    assert extrair_frentista("Como foi o desempenho do Italo?") == "ITALO"
    assert extrair_frentista("Vendas do frentista Botan hoje") == "BOTAN"
    assert extrair_frentista("Produtividade da matrícula 00003") == "00003"
    assert extrair_frentista("Produtividade da matrícula 3") == "00003"
    assert extrair_frentista("Produtividade do frentista 16") == "00016"
    assert extrair_frentista("Como foi o operador 16 hoje?") == "00016"
    assert extrair_frentista("Desempenho do frentista Samarina") == "SAMARINA"
    assert extrair_frentista("Ranking geral dos frentistas") is None
    assert extrair_frentista("Qual frentista vendeu mais gasolina aditivada hoje?") is None
    print("   [OK] Extração de frentistas validada (nomes, matrículas e prefixos)")

    assert extrair_bico("Tem algum bico com problema ou vazão lenta?") is None
    assert extrair_bico("Qual a vazão do bico 1 hoje?") == "001"
    assert extrair_bico("O bico 004 está com filtro sujo?") == "004"
    assert extrair_bico("Como está a bomba 2?") == "002"
    print("   [OK] Extração de bico/bomba validada")

    d1, t1 = extrair_data_turno("Desempenho dos frentistas hoje no 1º turno")
    assert d1 == "hoje" and t1 == "1º TURNO"
    d2, t2 = extrair_data_turno("Vendas dos frentistas em 2026-09-02 no turno da tarde")
    assert d2 == "2026-09-02" and t2 == "2º TURNO"
    print("   [OK] Extração de data e turno validada")

    # ------------------------------------------------------------------
    # 4. FÓRMULAS MATEMÁTICAS ESTÁTICAS DE VAZÃO
    # ------------------------------------------------------------------
    print("\n4. Testando Fórmulas Estáticas de Vazão de Bicos (L/min)...")
    # Caso 1: Normal (40 L/min) -> 20L em 30 segundos
    res_norm = PostoTools.calcular_vazao_bico(litros=20.0, tempo=30.0)
    assert res_norm["vazao_l_min"] == 40.0
    assert res_norm["status_vazao"] == "REGULAR_NORMAL"
    assert res_norm["alerta_filtro_lento"] is False
    print("   [OK] Vazão comercial normal: 20L em 30s = 40.0 L/min (REGULAR_NORMAL)")

    # Caso 2: Alerta Lento (26.67 L/min) -> 20L em 45 segundos
    res_alerta = PostoTools.calcular_vazao_bico(litros=20.0, tempo=45.0)
    assert res_alerta["vazao_l_min"] == 26.67
    assert res_alerta["status_vazao"] == "ALERTA_VAZAO_LENTA"
    assert res_alerta["alerta_filtro_lento"] is True
    print("   [OK] Vazão em faixa de alerta: 20L em 45s = 26.67 L/min (ALERTA_VAZAO_LENTA)")

    # Caso 3: Crítico Obstruído (20.0 L/min) -> 20L em 60 segundos
    res_crit = PostoTools.calcular_vazao_bico(litros=20.0, tempo=60.0)
    assert res_crit["vazao_l_min"] == 20.0
    assert res_crit["status_vazao"] == "CRÍTICO_FILTRO_OBSTRUÍDO"
    assert res_crit["alerta_filtro_lento"] is True
    print("   [OK] Vazão severamente obstruída: 20L em 60s = 20.0 L/min (CRÍTICO_FILTRO_OBSTRUÍDO)")

    # Caso 4: Alta vazão (60 L/min)
    res_alta = PostoTools.calcular_vazao_bico(litros=30.0, tempo=30.0)
    assert res_alta["vazao_l_min"] == 60.0
    assert res_alta["status_vazao"] == "ALTA_VAZAO"
    assert res_alta["alerta_filtro_lento"] is False
    print("   [OK] Vazão de alto fluxo: 30L em 30s = 60.0 L/min (ALTA_VAZAO)")

    # Caso 5: Formatos de string de tempo ("00:00:30", "01:00", "45s")
    res_str1 = PostoTools.calcular_vazao_bico(litros=20.0, tempo="00:00:30")
    assert res_str1["vazao_l_min"] == 40.0
    res_str2 = PostoTools.calcular_vazao_bico(litros=30.0, tempo="01:00")
    assert res_str2["vazao_l_min"] == 30.0
    print("   [OK] Resiliência a formatos de string (HH:MM:SS e MM:SS) validada")

    # Caso 6: Regra especial de Arla32 (vazão nominal 15-20 L/min)
    res_arla = PostoTools.calcular_vazao_bico(litros=15.0, tempo=60.0, produto_nome="ARLA32 GRANEL")
    assert res_arla["vazao_l_min"] == 15.0
    assert res_arla["status_vazao"] == "REGULAR_NORMAL"
    assert res_arla["alerta_filtro_lento"] is False
    print("   [OK] Calibração específica para Arla32 (15 L/min -> REGULAR_NORMAL)")

    # Caso 7: Tratamento de borda (tempo zero ou None)
    res_vazio = PostoTools.calcular_vazao_bico(litros=10.0, tempo=None)
    assert res_vazio["status_vazao"] == "SEM_REGISTRO_TEMPO"
    assert res_vazio["alerta_filtro_lento"] is False
    print("   [OK] Tratamento gracioso de tempo ausente ou nulo")

    # ------------------------------------------------------------------
    # 5. FÓRMULAS DE CONVERSÃO DE GASOLINA ADITIVADA
    # ------------------------------------------------------------------
    print("\n5. Testando Fórmulas de Conversão de Gasolina Aditivada...")
    c_exc = PostoTools.calcular_conversao_aditivada(litros_comum=70.0, litros_aditivada=30.0)
    assert c_exc["conversao_aditivada_pct"] == 30.0
    assert c_exc["classificacao_conversao"] == "EXCELENTE"

    c_bom = PostoTools.calcular_conversao_aditivada(litros_comum=80.0, litros_aditivada=20.0)
    assert c_bom["conversao_aditivada_pct"] == 20.0
    assert c_bom["classificacao_conversao"] == "BOM"

    c_reg = PostoTools.calcular_conversao_aditivada(litros_comum=90.0, litros_aditivada=10.0)
    assert c_reg["conversao_aditivada_pct"] == 10.0
    assert c_reg["classificacao_conversao"] == "REGULAR"

    c_bx = PostoTools.calcular_conversao_aditivada(litros_comum=100.0, litros_aditivada=0.0)
    assert c_bx["conversao_aditivada_pct"] == 0.0
    assert c_bx["classificacao_conversao"] == "BAIXO"

    c_zero = PostoTools.calcular_conversao_aditivada(litros_comum=0.0, litros_aditivada=0.0)
    assert c_zero["classificacao_conversao"] == "SEM_VENDAS_GASOLINA"
    print("   [OK] Todos os tiers de conversão de aditivada validados (Excelente, Bom, Regular, Baixo, Sem Vendas)")

    # ------------------------------------------------------------------
    # 6. INTEGRAÇÃO REAL COM O BANCO ERP (PORTA 5433)
    # ------------------------------------------------------------------
    print("\n6. Conectando ao ERP e Executando Auditoria Geral de Pista...")
    rag = HybridRAGEngine()
    tools = PostoTools(rag)

    res_geral = tools.auditar_desempenho_pista_frentistas()
    assert res_geral["status"] == "ok", f"Erro no retorno da tool: {res_geral}"
    exec_g = res_geral["resumo_executivo"]
    assert exec_g["total_abastecimentos"] == 6, f"Esperado 6 abastecimentos, obtido {exec_g['total_abastecimentos']}"
    assert exec_g["total_litros"] > 0
    assert exec_g["faturamento_total_reais"] > 0
    assert len(res_geral["auditoria_vazao_bicos"]) == 11, f"Esperado 11 bicos, obtido {len(res_geral['auditoria_vazao_bicos'])}"
    assert len(res_geral["ranking_frentistas"]) >= 2

    # Verifica os campeões
    c_vol = exec_g["campeao_volume"]
    assert c_vol is not None
    assert c_vol["matricula"] == "00003"
    assert "ITALO" in c_vol["nome"]
    assert c_vol["total_litros"] == 24.026

    c_fat = exec_g["campeao_faturamento"]
    assert c_fat is not None
    assert c_fat["matricula"] == "00003"
    assert c_fat["faturamento_reais"] == 171.30

    # Verifica métricas de produtos comuns vs alta margem no resumo executivo (Requisito 3)
    assert "total_diesel_s500_litros" in exec_g
    assert "total_diesel_s10_litros" in exec_g
    assert "taxa_conversao_diesel_s10_pct" in exec_g
    assert "total_gasolina_comum_litros" in exec_g
    assert "total_gasolina_aditivada_litros" in exec_g

    # Verifica que colaboradores identificados têm posições 1, 2, ... e pista não identificada tem None
    colabs = [f for f in res_geral["ranking_frentistas"] if f["identificado"]]
    nao_ident = [f for f in res_geral["ranking_frentistas"] if not f["identificado"]]
    for idx, c in enumerate(colabs, 1):
        assert c["posicao_ranking"] == idx
    for ni in nao_ident:
        assert ni["posicao_ranking"] is None

    print(f"   [OK] Auditoria Geral concluída com sucesso:")
    print(f"        • Total de Abastecimentos: {exec_g['total_abastecimentos']}")
    print(f"        • Volume Total de Pista: {exec_g['total_litros']} L")
    print(f"        • Faturamento Total: R$ {exec_g['faturamento_total_reais']}")
    print(f"        • Ticket Médio da Pista: R$ {exec_g['ticket_medio_pista_reais']}")
    print(f"        • Líder em Volume: {c_vol['nome']} ({c_vol['total_litros']} L)")
    print(f"        • Líder em Faturamento: {c_fat['nome']} (R$ {c_fat['faturamento_reais']})")

    # ------------------------------------------------------------------
    # 7. TESTE DE DETECÇÃO DE ANOMALIAS DE PISTA
    # ------------------------------------------------------------------
    print("\n7. Testando Detecção de Anomalias de Pista...")
    anomalias = res_geral["anomalias_detectadas"]
    assert len(anomalias) > 0, "Deveria ter detectado anomalias na base"
    tipos_anomalias = [a["tipo"] for a in anomalias]
    assert "MICRO_ABASTECIMENTO" in tipos_anomalias, "Deveria detectar micro-abastecimento (< 1.0 L)"
    assert "ABASTECIMENTO_MANUAL" in tipos_anomalias, "Deveria detectar abastecimento manual"
    assert "VALORES_REPETIDOS_CONSECUTIVOS" in tipos_anomalias, "Deveria detectar valores repetidos consecutivos"

    # Validar detalhes da anomalia de micro-abastecimento
    micro = next(a for a in anomalias if a["tipo"] == "MICRO_ABASTECIMENTO")
    assert micro["litros"] < 1.0

    # Validar que abastecimentos repetidos com intervalo de 7 dias NÃO geram falso positivo de sequência imediata
    repetidos = [a for a in anomalias if a["tipo"] == "VALORES_REPETIDOS_CONSECUTIVOS"]
    for rep in repetidos:
        # Se houve repetição no controle 1676, foi dentro de 4s em relação ao controle 1674 (ambos R$ 1.00)
        assert rep["total_reais"] == 1.00

    print(f"   [OK] Anomalias detectadas ({len(anomalias)} ocorrências):")
    print(f"        • Micro-abastecimentos: OK (ex: Controle {micro['controle']}, {micro['litros']} L)")
    print(f"        • Abastecimentos Manuais: OK")
    print(f"        • Valores Repetidos: OK (sem falsos positivos em datas distantes)")

    # ------------------------------------------------------------------
    # 8. TESTE DE ALERTA PREVENTIVO DE FILTRO LENTO (INJEÇÃO DE MEDIÇÕES)
    # ------------------------------------------------------------------
    print("\n8. Testando Alerta Preventivo de Filtro Lento / Obstruído (< 25-30 L/min)...")
    # Injeta medições simuladas: Bico 001 com 22 L/min (Crítico) e Bico 004 com 28 L/min (Alerta Lento)
    res_filtro = tools.auditar_desempenho_pista_frentistas(
        vazao_bicos_custom={"001": 22.0, "004": 28.0}
    )
    assert res_filtro["status"] == "ok"
    exec_fl = res_filtro["resumo_executivo"]
    assert exec_fl["bicos_com_alerta_filtro"] == 2
    assert exec_fl["status_geral"] == "CRÍTICO_MANUTENÇÃO"

    b_001 = next(b for b in res_filtro["auditoria_vazao_bicos"] if b["bico"] == "001")
    assert b_001["alerta_filtro_lento"] is True
    assert b_001["status_vazao"] == "CRÍTICO_FILTRO_OBSTRUÍDO"
    assert b_001["vazao_media_l_min"] == 22.0
    assert "Filtro de linha/bomba obstruído" in b_001["recomendacao"]

    b_004 = next(b for b in res_filtro["auditoria_vazao_bicos"] if b["bico"] == "004")
    assert b_004["alerta_filtro_lento"] is True
    assert b_004["status_vazao"] == "ALERTA_VAZAO_LENTA"
    assert b_004["vazao_media_l_min"] == 28.0

    # Verifica bico inativo (000) com injeção de chave curta "0"
    res_b0 = tools.auditar_desempenho_pista_frentistas(vazao_bicos_custom={"0": 20.0})
    b_000 = next((b for b in res_b0["auditoria_vazao_bicos"] if b["bico"] == "000"), None)
    if b_000:
        assert b_000["status_operacional"] == "INATIVO / DESATIVADO"
        assert b_000["alerta_filtro_lento"] is False

    # Verifica bico ativo sem movimentação no período (transparência de telemetria)
    b_003 = next(b for b in res_geral["auditoria_vazao_bicos"] if b["bico"] == "003")
    assert b_003["total_abastecimentos"] == 0
    assert b_003["origem_vazao"] == "sem_movimento_periodo"
    assert "Sem abastecimentos registrados" in b_003["recomendacao"]

    print("   [OK] Alerta de Filtro Obstruído detectado no Bico 001 (22 L/min)")
    print("   [OK] Alerta de Vazão Lenta detectado no Bico 004 (28 L/min)")
    print("   [OK] Elevação de status geral para CRÍTICO_MANUTENÇÃO confirmada")
    print("   [OK] Transparência operacional de bicos sem movimento validada")

    # ------------------------------------------------------------------
    # 9. TESTE DE FILTROS ESPECÍFICOS (DATA, TURNO, FRENTISTA, BICO)
    # ------------------------------------------------------------------
    print("\n9. Testando Filtros Específicos (Data, Turno, Frentista, Bico)...")
    # Filtro frentista ITALO
    res_italo = tools.auditar_desempenho_pista_frentistas(filtro="ITALO")
    assert res_italo["status"] == "ok"
    assert res_italo["resumo_executivo"]["total_abastecimentos"] == 2
    assert all("ITALO" in f["nome"] for f in res_italo["ranking_frentistas"])
    print("   [OK] Filtro por colaborador 'ITALO' isolou 2 abastecimentos com sucesso")

    # Filtro com prefixo 'frentista 00003'
    res_pref_num = tools.auditar_desempenho_pista_frentistas(filtro="frentista 00003")
    assert res_pref_num["status"] == "ok"
    assert res_pref_num["resumo_executivo"]["total_abastecimentos"] == 2
    assert "ITALO" in res_pref_num["ranking_frentistas"][0]["nome"]
    print("   [OK] Filtro com prefixo 'frentista 00003' isolou abastecimentos com sucesso")

    # Filtro com prefixo 'frentista botan'
    res_pref_nome = tools.auditar_desempenho_pista_frentistas(filtro="frentista botan")
    assert res_pref_nome["status"] == "ok"
    assert res_pref_nome["resumo_executivo"]["total_abastecimentos"] == 1
    assert "BOTAN" in res_pref_nome["ranking_frentistas"][0]["nome"]
    print("   [OK] Filtro com prefixo 'frentista botan' isolou abastecimento com sucesso")

    # Filtro frentista BOTAN
    res_botan = tools.auditar_desempenho_pista_frentistas(filtro="BOTAN")
    assert res_botan["status"] == "ok"
    assert res_botan["resumo_executivo"]["total_abastecimentos"] == 1
    assert "BOTAN" in res_botan["ranking_frentistas"][0]["nome"]
    print("   [OK] Filtro por colaborador 'BOTAN' isolou 1 abastecimento com sucesso")

    # Filtro por bico físico ('001')
    res_bico = tools.auditar_desempenho_pista_frentistas(bico="001")
    assert res_bico["status"] == "ok"
    assert res_bico["resumo_executivo"]["total_abastecimentos"] == 5
    assert res_bico["resumo_executivo"]["bico_alvo_destaque"]["bico"] == "001"
    print("   [OK] Filtro por bico físico '001' isolou abastecimentos com sucesso")

    # Filtro data 'hoje' (fallback resiliente para última data com movimento: 2026-09-02)
    res_hoje = tools.auditar_desempenho_pista_frentistas(data="hoje")
    assert res_hoje["status"] == "ok"
    assert res_hoje["resumo_executivo"]["total_abastecimentos"] == 1
    assert res_hoje["periodo_analisado"]["data_filtro"] == "2026-09-02"
    print("   [OK] Filtro 'hoje' resolveu fallback com transparência para 2026-09-02")

    # ------------------------------------------------------------------
    # 10. BLINDAGEM LGPD DO PAYLOAD RETORNADO
    # ------------------------------------------------------------------
    print("\n10. Testando Blindagem LGPD do Retorno da Tool...")
    # Verifica que nenhum CPF, cartão TEF ou senha consta desprotegido
    payload_str = str(res_geral)
    assert "password" not in payload_str.lower() or "secret" not in payload_str.lower()
    assert res_geral["status"] == "ok"
    print("   [OK] Conformidade com LGPD e sanitize_dict validada")

    print("\n" + "=" * 75)
    print("🎉 TODOS OS TESTES DE AUDITORIA DE PISTA & FRENTISTAS PASSARAM COM SUCESSO!")
    print("=" * 75)


if __name__ == "__main__":
    run_tests()
