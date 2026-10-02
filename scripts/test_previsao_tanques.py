"""
Suíte de Testes Automatizada: Motor de Previsão de Esgotamento de Combustível
(Run-Out Forecast) & Sugestão Inteligente de Pedidos de Caminhão-Tanque.

Validações:
1. Classificação de intenções e roteamento de perguntas preditivas
2. Não-regressão de intenções anteriores (auditoria_turno, estoque, vendas, clientes, catálogo)
3. Extração resiliente de combustível e tanque em linguagem natural
4. Fórmulas matemáticas de autonomia crítica (15%) e autonomia run-out (0L)
5. Casos de borda: saldo zero, saldo < 15%, saldo > 15%, consumo zero, ullage < 5k
6. Cálculo de espaço livre (Ullage) e compartimentos de carreta (múltiplos padrão de 5.000 L)
7. Projeção precisa de data e hora de esgotamento (Run-Out)
8. Integração real com o ERP PostgreSQL (porta 5433) e fallback gracioso de mercado
9. Filtro por combustível e por tanque
10. Alerta preventivo de fim de semana e blindagem LGPD (sanitize_dict)
"""

import sys
from decimal import Decimal
from datetime import datetime
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

from main import classificar_intencao, extrair_combustivel
from core.rag_engine import HybridRAGEngine
from core.tools import PostoTools


def run_tests():
    print("=" * 75)
    print("🔮 SUÍTE DE TESTES: MOTOR DE PREVISÃO DE ESGOTAMENTO & SUGESTÃO DE PEDIDOS")
    print("=" * 75)

    # ------------------------------------------------------------------
    # 1. TESTE DE CLASSIFICAÇÃO DE INTENÇÕES
    # ------------------------------------------------------------------
    print("\n1. Testando Classificador de Intenções (Previsão de Esgotamento)...")
    frases_previsao = [
        "Quando vai acabar a Gasolina Comum?",
        "Previsão de esgotamento dos tanques",
        "Qual tanque está mais crítico hoje?",
        "Preciso pedir combustível para o fim de semana?",
        "Qual a autonomia dos tanques de combustível?",
        "Quando vai acabar o diesel?",
        "Quando acaba a gasolina aditivada?",
        "Quando seca o tanque de etanol?",
        "Qual a previsão de run-out dos tanques?",
        "Quanto tempo dura o estoque de gasolina?",
        "Quanto tempo resta de diesel s10?",
        "Sugestão de pedido de combustível",
        "Sugestão de compra de carreta",
        "Preciso pedir combustível hoje?",
        "Qual o espaço livre para descarga nos tanques?",
        "Qual o espaço livre de descarga da gasolina?",
        "Quantos litros de diesel s10 cabem no tanque?",
        "Qual tanque tem risco de secar no fim de semana?",
        "Previsão dos tanques para sábado",
        "Autonomia de combustível do posto",
        "Quando o diesel acaba?",
        "Quando o etanol acaba?",
        "Quanto tempo vai durar o diesel?",
        "Quanto vai durar a gasolina?",
        "Quanto tempo ainda temos de gasolina?",
        "Quanto tempo de estoque de gasolina temos?",
        "Previsão de término do diesel",
        "Quando termina a gasolina comum?",
        "Quando que acaba o diesel?",
        "Quando que vai secar o tanque?",
    ]
    for frase in frases_previsao:
        intencao = classificar_intencao(frase)
        assert intencao == "previsao_tanques", (
            f"Falha na classificação: '{frase}' -> '{intencao}' (esperado: 'previsao_tanques')"
        )
        print(f"   [OK] '{frase}' -> {intencao}")

    # Não-regressão de intenções prévias
    assert classificar_intencao("Como fechou o 1º turno hoje?") == "auditoria_turno"
    assert classificar_intencao("Auditoria de fechamento de turno") == "auditoria_turno"
    assert classificar_intencao("Qual o saldo do tanque 1?") == "estoque_posicao"
    assert classificar_intencao("Quanto tem de gasolina no tanque?") == "estoque_posicao"
    assert classificar_intencao("Quanto tem no estoque de lubrificante?") == "estoque_posicao"
    assert classificar_intencao("Quem é o cliente que mais comprou?") == "clientes_ranking"
    assert classificar_intencao("Qual o produto mais vendido hoje?") == "vendas_analitico"
    assert classificar_intencao("Qual o preço da cerveja heineken?") == "catalogo_produtos"
    assert classificar_intencao("Qual o preço da gasolina?") == "catalogo_produtos"
    assert classificar_intencao("Quanto custa o diesel?") == "catalogo_produtos"
    assert classificar_intencao("Qual a saúde do banco de dados?") == "sre_metricas"
    assert classificar_intencao("Qual o cnpj da filial?") == "dados_filial"
    print("   [OK] Não-regressão de todas as rotas existentes (auditoria, estoque, vendas, clientes, catálogo, SRE, filial)")

    # ------------------------------------------------------------------
    # 2. TESTE DE EXTRAÇÃO DE COMBUSTÍVEL / TANQUE
    # ------------------------------------------------------------------
    print("\n2. Testando Extração de Combustível e Tanque...")
    casos_extracao = [
        ("Quando vai acabar a Gasolina Comum?", "GASOLINA COMUM"),
        ("Quando acaba a Gasolina Aditivada?", "GASOLINA ADITIVADA"),
        ("Quando acaba a Gasolina Grid?", "GASOLINA ADITIVADA"),
        ("Qual a previsão das gasolinas?", "GASOLINA"),
        ("Qual a autonomia do Diesel S10?", "DIESEL S10"),
        ("Qual a autonomia do Diesel S500?", "DIESEL S500"),
        ("Autonomia do Diesel Comum", "DIESEL S500"),
        ("Quando vai secar o diesel?", "DIESEL"),
        ("Quanto tempo dura o etanol?", "ETANOL"),
        ("Quanto tempo dura o álcool?", "ETANOL"),
        ("Previsão do Arla", "ARLA"),
        ("Previsão de esgotamento do Tanque 1", "001"),
        ("Previsão do TQ 01", "001"),
        ("Previsão do TQ-02", "002"),
        ("Previsão do Tanque 001 de Gasolina", "001"),
        ("Qual o nível do tanque 002?", "002"),
        ("Previsão de esgotamento dos tanques", None),
        ("Preciso pedir combustível para o fim de semana?", None),
    ]
    for frase, esperado in casos_extracao:
        res = extrair_combustivel(frase)
        assert res == esperado, f"Falha na extração de '{frase}': obteve '{res}', esperado '{esperado}'"
        print(f"   [OK] '{frase}' -> {res}")

    # ------------------------------------------------------------------
    # 3. TESTE DE FÓRMULAS MATEMÁTICAS PURAS (PostoTools Static Methods)
    # ------------------------------------------------------------------
    print("\n3. Testando Métodos Matemáticos Estáticos de Autonomia e Carreta...")

    # 3.1 Benchmark de mercado
    assert PostoTools.obter_consumo_benchmark("GASOLINA COMUM") == 3000.0
    assert PostoTools.obter_consumo_benchmark("GASOLINA ADITIVADA") == 1200.0
    assert PostoTools.obter_consumo_benchmark("ETANOL") == 1500.0
    assert PostoTools.obter_consumo_benchmark("DIESEL S10") == 4000.0
    assert PostoTools.obter_consumo_benchmark("DIESEL S500") == 1800.0
    assert PostoTools.obter_consumo_benchmark("ARLA") == 150.0
    assert PostoTools.obter_consumo_benchmark("OUTRO") == 1000.0
    print("   [OK] Taxas diárias de benchmark de mercado validadas")

    # 3.2 Fórmula física: Autonomia = (Saldo Atual - Estoque Crítico 15%) / Consumo Médio Diário
    # Cenário Normal: Cap 50.000 L, Saldo 20.000 L, Consumo 1.000 L/dia
    # Estoque Crítico (15%) = 7.500 L
    # Saldo Útil Crítico = 12.500 L
    # Autonomia Crítica = 12.5 dias (300 horas)
    # Autonomia Run-Out = 20.0 dias (480 horas)
    dt_ref = datetime(2026, 9, 2, 12, 0)
    res_normal = PostoTools.calcular_autonomia_tanque(
        saldo=Decimal("20000.0"),
        capacidade=Decimal("50000.0"),
        consumo_diario=Decimal("1000.0"),
        margem_critica_pct=Decimal("0.15"),
        data_referencia=dt_ref
    )
    assert res_normal["capacidade_litros"] == 50000.0
    assert res_normal["saldo_atual_litros"] == 20000.0
    assert res_normal["ocupacao_pct"] == 40.0
    assert res_normal["estoque_critico_15pct_litros"] == 7500.0
    assert res_normal["saldo_util_critico_litros"] == 12500.0
    assert res_normal["autonomia_critica_dias"] == 12.5
    assert res_normal["autonomia_critica_horas"] == 300.0
    assert res_normal["autonomia_runout_dias"] == 20.0
    assert res_normal["autonomia_runout_horas"] == 480.0
    assert res_normal["alerta_critico"] is False
    assert res_normal["status_operacional"] == "OPERACIONAL NORMAL"
    assert res_normal["data_hora_critico"] == "2026-09-15 00:00"
    assert res_normal["data_hora_runout"] == "2026-09-22 12:00"
    print("   [OK] Cálculo matemático em condição operacional normal (40% saldo, 12.5 dias até crítico)")

    # 3.3 Cenário Crítico: Saldo abaixo de 15% (Cap 50.000, Saldo 5.000 L, Consumo 1.000 L/dia)
    # 5.000 < 7.500 -> Saldo útil crítico = 0 -> Autonomia Crítica = 0.0 dias
    # Autonomia Run-Out = 5.000 / 1.000 = 5.0 dias (120 horas)
    res_critico = PostoTools.calcular_autonomia_tanque(
        saldo=Decimal("5000.0"),
        capacidade=Decimal("50000.0"),
        consumo_diario=Decimal("1000.0"),
        margem_critica_pct=Decimal("0.15"),
        data_referencia=dt_ref
    )
    assert res_critico["autonomia_critica_dias"] == 0.0
    assert res_critico["autonomia_critica_horas"] == 0.0
    assert res_critico["alerta_critico"] is True
    assert res_critico["status_operacional"] == "NÍVEL CRÍTICO"
    assert "JÁ EM NÍVEL CRÍTICO" in res_critico["data_hora_critico"]
    assert res_critico["autonomia_runout_dias"] == 5.0
    assert res_critico["autonomia_runout_horas"] == 120.0
    assert res_critico["data_hora_runout"] == "2026-09-07 12:00"
    print("   [OK] Tratamento matemático de estoque em nível crítico (< 15%, autonomia crítica = 0)")

    # 3.4 Cenário Tanque Seco (Saldo = 0 L)
    res_seco = PostoTools.calcular_autonomia_tanque(
        saldo=Decimal("0.0"),
        capacidade=Decimal("50000.0"),
        consumo_diario=Decimal("1000.0"),
        data_referencia=dt_ref
    )
    assert res_seco["autonomia_critica_dias"] == 0.0
    assert res_seco["autonomia_runout_dias"] == 0.0
    assert res_seco["status_operacional"] == "ESGOTADO (SECO)"
    assert "ESGOTADO" in res_seco["data_hora_runout"]
    print("   [OK] Tratamento de tanque seco (0 L, status ESGOTADO)")

    # 3.5 Cenário Guarda contra Divisão por Zero (Consumo = 0 L/dia)
    res_sem_consumo = PostoTools.calcular_autonomia_tanque(
        saldo=Decimal("10000.0"),
        capacidade=Decimal("50000.0"),
        consumo_diario=Decimal("0.0"),
        data_referencia=dt_ref
    )
    assert res_sem_consumo["autonomia_critica_dias"] == 0.0
    assert res_sem_consumo["autonomia_runout_dias"] == 0.0
    assert res_sem_consumo["status_operacional"] == "SEM CONSUMO"
    assert res_sem_consumo["alerta_critico"] is False

    # 3.5.1 Saldo abaixo de 15% com consumo 0 (deve sinalizar alerta crítico de reserva)
    res_crit_sem_consumo = PostoTools.calcular_autonomia_tanque(
        saldo=Decimal("5000.0"),
        capacidade=Decimal("50000.0"),
        consumo_diario=Decimal("0.0"),
        data_referencia=dt_ref
    )
    assert res_crit_sem_consumo["alerta_critico"] is True
    assert res_crit_sem_consumo["status_operacional"] == "NÍVEL CRÍTICO"
    print("   [OK] Proteção contra divisão por zero e alerta crítico sem consumo garantidos")

    # 3.6 Espaço Livre para Descarga (Ullage) e Compartimentos de Carreta (Múltiplos de 5.000 L)
    # Caso 1: Cap 50.000 L, Saldo 4.624,36 L -> Ullage = 45.375,64 L -> 9 compartimentos de 5k (45.000 L)
    res_carreta_1 = PostoTools.calcular_sugestao_carreta(
        capacidade=Decimal("50000.0"),
        saldo=Decimal("4624.36"),
        multiplo_compartimento=Decimal("5000.0")
    )
    assert res_carreta_1["espaco_livre_ullage_litros"] == 45375.64
    assert res_carreta_1["compartimentos_5k"] == 9
    assert res_carreta_1["volume_sugerido_litros"] == 45000.0
    assert res_carreta_1["percentual_livre_pct"] == 90.75

    # Caso 2: Cap 50.000 L, Saldo 19.824,60 L -> Ullage = 30.175,40 L -> 6 compartimentos de 5k (30.000 L)
    res_carreta_2 = PostoTools.calcular_sugestao_carreta(
        capacidade=Decimal("50000.0"),
        saldo=Decimal("19824.60"),
        multiplo_compartimento=Decimal("5000.0")
    )
    assert res_carreta_2["compartimentos_5k"] == 6
    assert res_carreta_2["volume_sugerido_litros"] == 30000.0

    # Caso 3: Tanque quase cheio (Ullage < 5.000 L) -> não cabe compartimento de 5k
    res_carreta_3 = PostoTools.calcular_sugestao_carreta(
        capacidade=Decimal("50000.0"),
        saldo=Decimal("47000.0"),
        multiplo_compartimento=Decimal("5000.0")
    )
    assert res_carreta_3["espaco_livre_ullage_litros"] == 3000.0
    assert res_carreta_3["compartimentos_5k"] == 0
    assert res_carreta_3["volume_sugerido_litros"] == 0.0

    # Caso 4: Saldo contábil negativo (-500 L) limitado à capacidade física estrita (sem transbordo)
    res_carreta_4 = PostoTools.calcular_sugestao_carreta(
        capacidade=Decimal("50000.0"),
        saldo=Decimal("-500.0"),
        multiplo_compartimento=Decimal("5000.0")
    )
    assert res_carreta_4["espaco_livre_ullage_litros"] == 50000.0
    assert res_carreta_4["volume_sugerido_litros"] == 50000.0
    assert res_carreta_4["percentual_livre_pct"] == 100.0
    print("   [OK] Espaço livre (ullage) e múltiplos de compartimento de carreta (5k/10k/15k) validados")

    # ------------------------------------------------------------------
    # 4. TESTE DA TOOL NO ERP REAL (Porta 5433)
    # ------------------------------------------------------------------
    print("\n4. Conectando ao ERP e Executando Previsão Completa...")
    rag = HybridRAGEngine()
    tools = PostoTools(rag)

    # 4.1 Execução Padrão Global (Todos os Tanques)
    previsao_geral = tools.prever_esgotamento_tanques(data_referencia=dt_ref)
    assert previsao_geral.get("status") == "ok", f"Erro na consulta geral: {previsao_geral}"
    assert "resumo_executivo" in previsao_geral
    assert "previsao_por_combustivel" in previsao_geral
    assert "detalhamento_tanques" in previsao_geral
    assert "sugestoes_pedidos_carreta" in previsao_geral
    assert "telemetria_consumo" in previsao_geral

    tanques = previsao_geral["detalhamento_tanques"]
    assert len(tanques) == 10, f"Esperado 10 tanques no ERP, obteve {len(tanques)}"
    combustiveis = previsao_geral["previsao_por_combustivel"]
    assert len(combustiveis) == 6, f"Esperado 6 combustíveis consolidados, obteve {len(combustiveis)}"

    exec_sum = previsao_geral["resumo_executivo"]
    assert exec_sum["status_geral"] == "ALERTA_ESTOQUE_CRITICO"
    assert exec_sum["tanque_mais_critico"] is not None
    assert exec_sum["alerta_fim_de_semana"] is True
    assert len(exec_sum["combustiveis_em_risco_fim_de_semana"]) >= 3
    assert "tanque_operacional_mais_critico" in exec_sum
    assert exec_sum["tanque_operacional_mais_critico"]["codtan"] == "006"
    assert exec_sum["tanques_zerados_secos"] == ["010"]
    print(f"   [OK] Previsão Global executada:")
    print(f"        • Status Geral: {exec_sum['status_geral']}")
    print(f"        • Tanque Mais Crítico (Seco): {exec_sum['tanque_mais_critico']['codtan']} ({exec_sum['tanque_mais_critico']['combustivel']})")
    print(f"        • Tanque Operacional Mais Crítico: {exec_sum['tanque_operacional_mais_critico']['codtan']} ({exec_sum['tanque_operacional_mais_critico']['combustivel']})")
    print(f"        • Volume Total Sugerido: {exec_sum['total_volume_sugerido_litros']:.0f} L ({exec_sum['total_compartimentos_5k']} compartimentos de 5k)")
    print(f"        • Alerta Fim de Semana: {exec_sum['alerta_fim_de_semana']} ({', '.join(exec_sum['combustiveis_em_risco_fim_de_semana'])})")

    # 4.2 Execução com Filtro de Gasolina Comum
    previsao_gasolina = tools.prever_esgotamento_tanques(filtro_combustivel="GASOLINA COMUM", data_referencia=dt_ref)
    assert previsao_gasolina.get("status") == "ok"
    tanques_gas = previsao_gasolina["detalhamento_tanques"]
    assert len(tanques_gas) == 4, f"Esperado 4 tanques de Gasolina Comum (000, 001, 007, 008), obteve {len(tanques_gas)}"
    combs_gas = previsao_gasolina["previsao_por_combustivel"]
    assert len(combs_gas) == 1
    assert combs_gas[0]["combustivel"] == "GASOLINA COMUM"
    assert combs_gas[0]["capacidade_total_litros"] == 150000.0
    assert combs_gas[0]["saldo_total_litros"] == 18285.28
    assert combs_gas[0]["autonomia_critica_dias"] == 0.0
    assert combs_gas[0]["autonomia_runout_dias"] == 6.1
    assert combs_gas[0]["volume_sugerido_compra_litros"] == 130000.0
    print(f"   [OK] Filtro 'GASOLINA COMUM' validado com precisão volumétrica:")
    print(f"        • Capacidade Consolidada: {combs_gas[0]['capacidade_total_litros']} L")
    print(f"        • Saldo Consolidado: {combs_gas[0]['saldo_total_litros']} L")
    print(f"        • Autonomia Crítica: {combs_gas[0]['autonomia_critica_dias']} dias (Abaixo de 15%)")
    print(f"        • Autonomia Run-Out: {combs_gas[0]['autonomia_runout_dias']} dias ({combs_gas[0]['autonomia_runout_horas']} h)")
    print(f"        • Sugestão de Compra: {combs_gas[0]['volume_sugerido_compra_litros']} L ({combs_gas[0]['compartimentos_5k_sugeridos']} bocas de 5k)")

    # 4.3 Execução com Filtro de Diesel S10
    previsao_s10 = tools.prever_esgotamento_tanques(filtro_combustivel="DIESEL S10", data_referencia=dt_ref)
    assert previsao_s10.get("status") == "ok"
    tanques_s10 = previsao_s10["detalhamento_tanques"]
    assert len(tanques_s10) == 2, f"Esperado 2 tanques de Diesel S10 (005 e 006), obteve {len(tanques_s10)}"
    t006 = next(t for t in tanques_s10 if t["codtan"] == "006")
    assert t006["saldo_atual_litros"] == 755.43
    assert t006["alerta_critico"] is True
    assert t006["volume_sugerido_litros"] == 45000.0
    assert t006["compartimentos_5k"] == 9
    print(f"   [OK] Filtro 'DIESEL S10' validado (Tanque 006 crítico: 755.43 L, sugestão 45.000 L)")

    # 4.4 Execução com Filtro de Etanol
    previsao_etanol = tools.prever_esgotamento_tanques(filtro_combustivel="ETANOL", data_referencia=dt_ref)
    assert previsao_etanol.get("status") == "ok"
    t_etanol = previsao_etanol["detalhamento_tanques"][0]
    assert t_etanol["codtan"] == "003"
    assert t_etanol["capacidade_litros"] == 50000.0
    assert t_etanol["saldo_atual_litros"] == 11285.63
    assert t_etanol["volume_sugerido_litros"] == 35000.0
    # Escopo executivo estritamente filtrado para Etanol
    assert previsao_etanol["resumo_executivo"]["tanque_mais_critico"]["codtan"] == "003"
    assert previsao_etanol["resumo_executivo"]["combustivel_mais_urgente"] == "ETANOL"
    print(f"   [OK] Filtro 'ETANOL' validado (Tanque 003: 11.285.63 L, sugestão 35.000 L, escopo executivo preservado)")

    # 4.5 Execução com Filtro de Tanque Específico ('001')
    previsao_t1 = tools.prever_esgotamento_tanques(filtro_combustivel="001", data_referencia=dt_ref)
    assert previsao_t1.get("status") == "ok"
    assert len(previsao_t1["detalhamento_tanques"]) == 1
    assert previsao_t1["detalhamento_tanques"][0]["codtan"] == "001"
    assert len(previsao_t1["previsao_por_combustivel"]) == 1
    assert previsao_t1["previsao_por_combustivel"][0]["combustivel"] == "GASOLINA COMUM"
    assert previsao_t1["resumo_executivo"]["tanque_mais_critico"]["codtan"] == "001"
    print("   [OK] Filtro por código de tanque ('001') preserva categoria de combustível vinculada")

    # 4.6 Execução com Override de Consumo Customizado
    previsao_custom = tools.prever_esgotamento_tanques(
        filtro_combustivel="ETANOL",
        consumo_diario_custom={"ETANOL": 3000.0},
        data_referencia=dt_ref
    )
    t_custom = previsao_custom["detalhamento_tanques"][0]
    assert t_custom["consumo_diario_litros"] == 3000.0
    # Com 3000 L/dia, autonomia de 11.285,63 L = 3.76 dias (90.28h)
    assert round(t_custom["autonomia_runout_dias"], 2) == 3.76

    # 4.7 Execução com Consumo Zero Customizado (sem ZeroDivisionError)
    previsao_zero = tools.prever_esgotamento_tanques(
        filtro_combustivel="GASOLINA COMUM",
        consumo_diario_custom={"GASOLINA COMUM": 0.0},
        data_referencia=dt_ref
    )
    assert previsao_zero.get("status") == "ok"
    assert previsao_zero["detalhamento_tanques"][0]["consumo_diario_litros"] == 0.0
    print("   [OK] Calibração de consumo customizado e resiliência a taxa zero validadas")

    # 4.8 Execução com Filtro Inexistente
    previsao_xyz = tools.prever_esgotamento_tanques(filtro_combustivel="XYZ", data_referencia=dt_ref)
    assert previsao_xyz.get("status") == "ok"
    assert len(previsao_xyz["detalhamento_tanques"]) == 0
    assert previsao_xyz["resumo_executivo"]["tanque_mais_critico"] is None
    assert previsao_xyz["resumo_executivo"]["status_geral"] == "SEM_REGISTROS"
    print("   [OK] Tratamento gracioso de filtro inexistente ('XYZ') sem exceções")

    # ------------------------------------------------------------------
    # 5. TESTE DE BLINDAGEM LGPD E SANITIZAÇÃO
    # ------------------------------------------------------------------
    print("\n5. Testando Blindagem LGPD do Retorno da Tool...")
    assert "password" not in str(previsao_geral)
    assert isinstance(previsao_geral["resumo_executivo"]["total_volume_sugerido_litros"], (int, float))
    print("   [OK] Conformidade LGPD e integridade de tipos numéricos preservada")

    print("\n" + "=" * 75)
    print("🎉 TODOS OS TESTES DO MOTOR DE PREVISÃO PASSARAM COM 100% DE SUCESSO!")
    print("=" * 75)


if __name__ == "__main__":
    run_tests()
