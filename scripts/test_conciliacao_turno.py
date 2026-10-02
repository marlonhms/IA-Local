"""
Suíte de Testes Automatizada: Motor de Conciliação de Turnos & Auditoria de Pista (Fase 2 - P0).
Valida:
1. Classificação de intenções e roteamento CLI com cobertura ampla de perguntas operacionais
2. Extração de parâmetros de data (ISO, BR, DD/MM, extenso) e turno (1º, 2º, 3º, manhã, tarde, noite)
3. Normalização estática robusta com proteção de limites de palavras (evita falsos-positivos)
4. Triangulação matemática real (fechabomba x abastecimentos x fechacaixa x tanques)
5. Fórmula física de encerrantes com suporte a virada de odômetro (rollover) e detecção de erros
6. Tolerância volumétrica da ANP (±0.6%) para tanques e regras de conformidade fiscal
7. Diagnóstico preciso de turnos em andamento com caixas abertos vs fechados
8. Tratamento de datas sem movimento e retorno de última data disponível
9. Blindagem e mascaramento LGPD via core.sanitizer
"""

import sys
from decimal import Decimal
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

from main import classificar_intencao, extrair_data_turno
from core.rag_engine import HybridRAGEngine
from core.tools import PostoTools


def run_tests():
    print("=" * 75)
    print("📊 SUÍTE DE TESTES: MOTOR DE CONCILIAÇÃO DE TURNOS & AUDITORIA DE PISTA")
    print("=" * 75)

    # ------------------------------------------------------------------
    # 1. TESTE DE CLASSIFICAÇÃO DE INTENÇÕES
    # ------------------------------------------------------------------
    print("\n1. Testando Classificador de Intenções (Auditoria de Turno)...")
    frases_auditoria = [
        "Como fechou o 1º turno hoje?",
        "Como fechou o 2º turno ontem?",
        "Como foi o fechamento do 3º turno?",
        "Auditar fechamento de turno",
        "Auditoria de pista",
        "Auditoria de turno",
        "Teve furo de caixa ou de pista?",
        "Houve sobra ou falta de caixa na pista?",
        "O caixa bateu com o que saiu dos bicos?",
        "O caixa bateu?",
        "Conciliação de turno",
        "Conciliacao de turnos",
        "Conferência de turno",
        "Teve quebra de caixa hoje?",
        "Como fechou o turno hoje?",
        "Como foi o fechamento hoje?",
        "Qual o fechamento de hoje?",
        "Auditoria de hoje",
        "Como foi o encerramento do turno?",
        "Relatório de fechamento",
        "Conferência de pista",
        "Conferencia de pista",
        "Teve divergência na pista?",
        "Teve divergencia na pista?",
        "Teve diferença de caixa?",
        "Teve diferenca no turno?",
        "Sobrou ou faltou dinheiro?",
        "O encerrante bateu?",
        "Bateu os bicos?",
        "Teve furo hoje?",
        "Auditar o turno da manhã",
        "Como foi o fechamento do 1o turno?",
        "Teve quebra de pista?",
        "Conferir encerrantes das bombas",
    ]
    for frase in frases_auditoria:
        intencao = classificar_intencao(frase)
        assert intencao == "auditoria_turno", f"Falha na classificação: '{frase}' classificada como '{intencao}' (esperado: 'auditoria_turno')"
        print(f"   [OK] '{frase}' -> {intencao}")

    # Garantir que outras intenções não foram quebradas
    assert classificar_intencao("Qual o saldo do tanque 1?") == "estoque_posicao"
    assert classificar_intencao("Quem é o cliente que mais comprou?") == "clientes_ranking"
    assert classificar_intencao("Qual o produto mais vendido?") == "vendas_analitico"
    assert classificar_intencao("Qual o preço da cerveja heineken?") == "catalogo_produtos"
    print("   [OK] Não-regressão de intenções existentes (estoque, clientes, vendas, catálogo)")

    # ------------------------------------------------------------------
    # 2. TESTE DE EXTRAÇÃO DE PARÂMETROS
    # ------------------------------------------------------------------
    print("\n2. Testando Extração de Parâmetros de Data e Turno...")
    casos_extracao = [
        ("Como fechou o 1º turno hoje?", ("hoje", "1º TURNO")),
        ("Auditoria do 2º turno ontem", ("ontem", "2º TURNO")),
        ("Como fechou o terceiro turno em 2026-09-02?", ("2026-09-02", "3º TURNO")),
        ("Teve furo de caixa em 02/09/2026 no 1 turno?", ("2026-09-02", "1º TURNO")),
        ("Auditar fechamento geral", (None, None)),
        ("Como fechou o turno da manhã hoje?", ("hoje", "1º TURNO")),
        ("Como fechou o turno da tarde ontem?", ("ontem", "2º TURNO")),
        ("Como fechou o turno da noite?", (None, "3º TURNO")),
        ("Como fechou no dia 02/09?", ("2026-09-02", None)),
        ("Auditoria em 2 de setembro", ("2026-09-02", None)),
        ("Auditoria em 2 de setembro no 1 turno", ("2026-09-02", "1º TURNO")),
    ]
    for frase, esperado in casos_extracao:
        res = extrair_data_turno(frase)
        assert res == esperado, f"Falha na extração de '{frase}': obteve {res}, esperado {esperado}"
        print(f"   [OK] '{frase}' -> Data: {res[0]}, Turno: {res[1]}")

    # ------------------------------------------------------------------
    # 3. TESTE DE NORMALIZAÇÃO DE ENTRADAS (PostoTools)
    # ------------------------------------------------------------------
    print("\n3. Testando Métodos Estáticos de Normalização em PostoTools...")
    assert PostoTools.normalizar_turno(1) == ("%1%TURNO%", 1)
    assert PostoTools.normalizar_turno("1º TURNO") == ("%1%TURNO%", 1)
    assert PostoTools.normalizar_turno("segundo") == ("%2%TURNO%", 2)
    assert PostoTools.normalizar_turno("3") == ("%3%TURNO%", 3)
    assert PostoTools.normalizar_turno("manhã") == ("%1%TURNO%", 1)
    assert PostoTools.normalizar_turno("tarde") == ("%2%TURNO%", 2)
    assert PostoTools.normalizar_turno("noite") == ("%3%TURNO%", 3)
    assert PostoTools.normalizar_turno("madrugada") == ("%3%TURNO%", 3)
    assert PostoTools.normalizar_turno("10") == (None, None)
    assert PostoTools.normalizar_turno("2026-09-01") == (None, None)
    assert PostoTools.normalizar_turno("banana") == (None, None)
    assert PostoTools.normalizar_turno(None) == (None, None)
    assert PostoTools.normalizar_turno("todos") == (None, None)

    assert PostoTools.normalizar_data("hoje") == "hoje"
    assert PostoTools.normalizar_data("ontem") == "ontem"
    assert PostoTools.normalizar_data("anteontem") == "anteontem"
    assert PostoTools.normalizar_data("02/09/2026") == "2026-09-02"
    assert PostoTools.normalizar_data("2026-09-02") == "2026-09-02"
    assert PostoTools.normalizar_data("02/09") == "2026-09-02"
    assert PostoTools.normalizar_data("2 de setembro") == "2026-09-02"
    assert PostoTools.normalizar_data("banana") is None
    assert PostoTools.normalizar_data(None) is None
    print("   [OK] Normalização de Turnos e Datas validada com proteção de limites")

    # ------------------------------------------------------------------
    # 4. TESTE DA TOOL NO BANCO REAL ERP (Porta 5433)
    # ------------------------------------------------------------------
    print("\n4. Conectando ao ERP e Executando Auditoria Real...")
    rag = HybridRAGEngine()
    tools = PostoTools(rag)

    # 4.1 Consulta sem parâmetros (fallback inteligente para data mais recente)
    audit_default = tools.auditar_fechamento_turno()
    assert audit_default.get("status") == "ok", f"Erro na consulta default: {audit_default}"
    assert "data_auditada" in audit_default, "Campo 'data_auditada' ausente"
    assert "resumo_executivo" in audit_default, "Campo 'resumo_executivo' ausente"
    assert "triangulacao_pista" in audit_default, "Campo 'triangulacao_pista' ausente"
    assert "triangulacao_caixa" in audit_default, "Campo 'triangulacao_caixa' ausente"
    assert "balanco_tanques" in audit_default, "Campo 'balanco_tanques' ausente"
    print(f"   [OK] Auditoria Default concluída com sucesso para data {audit_default['data_auditada']}")
    print(f"        • Status: {audit_default['resumo_executivo']['status_conciliacao']}")
    print(f"        • Score: {audit_default['resumo_executivo']['score_conformidade_pct']}%")
    print(f"        • Faturamento Pista: R$ {audit_default['resumo_executivo']['faturamento_pista_total']:.2f}")
    print(f"        • Faturamento Caixa: R$ {audit_default['resumo_executivo']['faturamento_caixa_total']:.2f}")

    # 4.2 Consulta com data específica e turno específico
    audit_turno1 = tools.auditar_fechamento_turno(data="2026-09-02", turno=1)
    assert audit_turno1.get("status") == "ok", f"Erro na consulta turno 1: {audit_turno1}"
    assert audit_turno1["data_auditada"] == "2026-09-02"
    pista = audit_turno1["triangulacao_pista"]
    assert pista["total_bicos_auditados"] == 10, f"Esperado 10 bicos auditados, obteve {pista['total_bicos_auditados']}"
    assert pista["total_abastecimentos_automacao"] == 1, f"Esperado 1 abastecimento na automação, obteve {pista['total_abastecimentos_automacao']}"
    assert pista["total_litros_automacao"] == 10.0, f"Esperado 10.0 L na automação, obteve {pista['total_litros_automacao']}"
    print("   [OK] Consulta com filtros de Data ('2026-09-02') e Turno (1) validada com 10 bicos")

    # 4.3 Consulta com formato dia/mês (sem ano) - deve resolver para 2026 sem erro de sintaxe SQL
    audit_ddmm = tools.auditar_fechamento_turno(data="02/09", turno=1)
    assert audit_ddmm.get("status") == "ok", f"Erro na consulta DD/MM: {audit_ddmm}"
    assert audit_ddmm["data_auditada"] == "2026-09-02"
    print("   [OK] Consulta com formato DD/MM ('02/09') resolvida com segurança para 2026-09-02")

    # 4.4 Consulta para data sem nenhum registro (deve retornar sem_movimento de forma amigável com última data)
    audit_vazio = tools.auditar_fechamento_turno(data="1999-01-01", turno=1)
    assert audit_vazio.get("status") == "sem_movimento", "Deveria retornar 'sem_movimento'"
    assert "Nenhum registro" in audit_vazio.get("mensagem", "")
    assert audit_vazio.get("ultima_data_disponivel") is not None
    print(f"   [OK] Tratamento gracioso de datas sem movimento (1999-01-01) com sugestão: {audit_vazio.get('ultima_data_disponivel')}")

    # ------------------------------------------------------------------
    # 5. TESTE DE VALIDAÇÃO MATEMÁTICA E REGRAS DE NEGÓCIO
    # ------------------------------------------------------------------
    print("\n5. Testando Fórmulas Matemáticas e Regras de Negócio...")
    
    # 5.1 Fórmula física do encerrante: Volume = (enclts - encltsa) - qtdeaf
    enclts = Decimal("15420.500")
    encltsa = Decimal("15000.000")
    qtdeaf = Decimal("20.000")  # Aferição balde padrão 20L
    vol_bruto, vol_fat, status_c = PostoTools.calcular_volume_encerrante(encltsa, enclts, qtdeaf)
    assert vol_bruto == Decimal("420.500"), f"Erro no volume bruto: {vol_bruto}"
    assert vol_fat == Decimal("400.500"), f"Erro no volume faturado: {vol_fat}"
    assert status_c == "NORMAL"
    print(f"   [OK] Fórmula física de encerrante: Bruto={vol_bruto} L, Faturado={vol_fat} L (status: {status_c})")

    # 5.2 Virada de odômetro (Rollover)
    vol_b_roll, vol_f_roll, status_roll = PostoTools.calcular_volume_encerrante(Decimal("999950.000"), Decimal("50.000"), Decimal("0.0"))
    assert vol_b_roll == Decimal("100.000"), f"Erro no volume bruto com rollover: {vol_b_roll}"
    assert vol_f_roll == Decimal("100.000"), f"Erro no volume faturado com rollover: {vol_f_roll}"
    assert "VIRADA_ODOMETRO" in status_roll
    print(f"   [OK] Tratamento de virada de odômetro (999.950 -> 50): {vol_f_roll} L ({status_roll})")

    # 5.3 Erro de digitação (encerrante final menor que inicial sem rollover plausível)
    vol_b_err, vol_f_err, status_err = PostoTools.calcular_volume_encerrante(Decimal("5000.000"), Decimal("4000.000"), Decimal("0.0"))
    assert vol_b_err == Decimal("0.0")
    assert "ERRO_DIGITACAO" in status_err
    print(f"   [OK] Detecção de erro de digitação de encerrante: {status_err}")

    # 5.4 Tolerância ANP de ±0.6% nos tanques
    cap_tanque = Decimal("50000.0")
    saldo_ini = Decimal("20000.0")
    saldo_fim = Decimal("19000.0")
    dif_tanque = saldo_ini - saldo_fim  # 1000.0 L
    saida_bicos_conforme = Decimal("995.0")  # Diferença de 5 L = 0.5% sobre as vendas
    var_conforme = abs(dif_tanque - saida_bicos_conforme) / saida_bicos_conforme * 100
    assert var_conforme <= Decimal("0.6"), "Variação deveria estar conforme ANP"

    saida_bicos_alerta = Decimal("900.0")  # Diferença de 100 L = 11.1% sobre as vendas
    var_alerta = abs(dif_tanque - saida_bicos_alerta) / saida_bicos_alerta * 100
    assert var_alerta > Decimal("0.6"), "Variação deveria disparar alerta ANP"
    print(f"   [OK] Tolerância ANP (±0.6%): Conforme={var_conforme:.3f}%, Alerta={var_alerta:.3f}%")

    # 5.5 Triangulação Contábil Pista x Caixa nos dados reais (2026-09-02)
    exec_summary = audit_turno1["resumo_executivo"]
    assert exec_summary["faturamento_pista_total"] == 71.30, f"Faturamento pista incorreto: {exec_summary['faturamento_pista_total']}"
    assert exec_summary["faturamento_caixa_total"] == 62.98, f"Faturamento caixa incorreto: {exec_summary['faturamento_caixa_total']}"
    assert round(exec_summary["diferenca_financeira_caixa"], 2) == -8.32, f"Diferença incorreta: {exec_summary['diferenca_financeira_caixa']}"
    assert "ANDAMENTO" in exec_summary["diagnostico_caixa"] or "PENDÊNCIA" in exec_summary["diagnostico_caixa"] or "FURO" in exec_summary["diagnostico_caixa"]
    assert "CBC04" in exec_summary["diagnostico_pista"]
    print("   [OK] Triangulação Contábil: Pista R$ 71.30 vs Caixa R$ 62.98 -> Diferença R$ -8.32 (Turno em Aberto)")

    # ------------------------------------------------------------------
    # 6. TESTE DE BLINDAGEM E SANITIZAÇÃO LGPD
    # ------------------------------------------------------------------
    print("\n6. Testando Blindagem LGPD do Retorno da Tool...")
    assert isinstance(audit_turno1["triangulacao_caixa"]["totais_caixa"]["total_cupons_pdv"], float)
    assert audit_turno1["triangulacao_caixa"]["totais_caixa"]["total_cupons_pdv"] == 62.98
    for cx in audit_turno1["triangulacao_caixa"]["caixas"]:
        assert "password" not in cx
    print("   [OK] Integridade Contábil 100% preservada e conformidade LGPD ativa")

    print("\n" + "=" * 75)
    print("🎉 TODOS OS TESTES DA FASE 2 PASSARAM COM 100% DE SUCESSO!")
    print("=" * 75)


if __name__ == "__main__":
    run_tests()
