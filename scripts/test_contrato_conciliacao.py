"""
Suíte de Testes Automatizada: Validação End-to-End do Contrato Estruturado de Conciliação
e Renderização Visual AURA Precision Glass v1.0 (Marco 1 / Fases 0 a 3)

Validações:
1. Contrato oficial v1.0 com contexto temporal estrito (queried_at ISO-8601).
2. Distinção rigorosa entre dado ausente (null), zero real registrado e medido:
   - Encerrante pendente -> physical_volume_liters is None, physical_volume_state == 'not_reported'
   - Encerrante zero medido -> physical_volume_liters == 0.0, physical_volume_state == 'zero_registered'
   - Encerrante medido -> physical_volume_liters > 0, physical_volume_state == 'measured'
3. Semântica de status e severidade:
   - Caixas abertos ou encerrantes pendentes -> finality == 'partial', is_provisional == True,
     badge_label == 'Análise parcial (provisória)', nunca 'furo definitivo'.
4. Presença de centavos inteiros tipados (automation_revenue_cents, pos_revenue_cents, difference_cents).
5. Lista de fontes com disponibilidade e proveniência explicitadas.
6. Ações recomendadas restritas a ações manuais externas no ERP (segurança e somente leitura).
7. Tratamento gracioso de sem_movimento e indisponibilidade com conformidade ao schema.
8. Execução de testes de frontend no Node.js cobrindo:
   - Renderização pt-BR de moedas e volumes
   - Fallback seguro contra versões desconhecidas de schema (sem inventar validação financeira)
   - Proteção XSS estrita
   - Aba 'formula' sem subtração de zero falso
   - Fallback do Evidence Drawer contra payloads vazios
   - Rótulos humanos de caixas e sessões
"""
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime

# Protege stdout no Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.rag_engine import HybridRAGEngine
from core.tools import PostoTools
from core.schemas.reconciliation import (
    ShiftReconciliationContract,
    ReconciliationContext,
    ReconciliationAssessment,
    ReconciliationMetrics,
    ReconciliationExplanation,
    PendingItem,
    DataSource,
    RecommendedAction,
)


def run_tests():
    print("=" * 78)
    print("🧪 SUÍTE DE TESTES: CONTRATO SEMÂNTICO & RENDERIZAÇÃO AURA PRECISION GLASS")
    print("=" * 78)

    rag = HybridRAGEngine()
    tools = PostoTools(rag)

    # ------------------------------------------------------------------
    # 1. Teste do Fluxo Piloto Real (2026-09-02, Turno 1)
    # ------------------------------------------------------------------
    print("\n1. Testando Contrato Estruturado para o Piloto Real (2026-09-02)...")
    res = tools.auditar_fechamento_turno(data="2026-09-02", turno=1)

    assert res.get("status") == "ok", f"Status inesperado: {res}"
    assert res.get("schema_version") == "1.0", "schema_version ausente ou diferente de '1.0'"
    assert "assessment" in res, "Campo 'assessment' ausente"
    assert "metrics" in res, "Campo 'metrics' ausente"
    assert "pending_items" in res, "Campo 'pending_items' ausente"
    assert "sources" in res, "Campo 'sources' ausente"
    assert "recommended_action" in res, "Campo 'recommended_action' ausente"
    assert "contrato" in res, "Campo 'contrato' completo ausente"

    # Validação Pydantic estrita
    contrato = ShiftReconciliationContract.model_validate(res["contrato"])
    assert contrato.schema_version == "1.0"
    print("   [OK] Payload validado com sucesso pelo schema Pydantic ShiftReconciliationContract")

    # ------------------------------------------------------------------
    # 2. Contexto Temporal e Isolamento da Consulta (F1-07 e F1-11)
    # ------------------------------------------------------------------
    print("\n2. Validando Contexto da Consulta e Timestamp ISO (queried_at)...")
    ctx = contrato.context
    assert isinstance(ctx, ReconciliationContext)
    assert ctx.unit_id == "posto_01"
    assert ctx.queried_at is not None, "queried_at não pode ser nulo"
    # Valida se é um ISO timestamp parseável
    dt = datetime.fromisoformat(ctx.queried_at)
    assert dt.year >= 2026
    assert ctx.data_auditada == "2026-09-02"
    print(f"   [OK] Contexto validado: queried_at='{ctx.queried_at}', data_auditada='{ctx.data_auditada}'")

    # ------------------------------------------------------------------
    # 3. Regra Semântica: Análise Parcial vs Furo Definitivo
    # ------------------------------------------------------------------
    print("\n3. Validando Semântica de Análise Parcial (Caixa Aberto / Encerrante Pendente)...")
    ass = contrato.assessment
    met = contrato.metrics

    assert ass.finality == "partial", f"Esperado finality == 'partial', obteve '{ass.finality}'"
    assert met.is_provisional is True, "is_provisional deveria ser True para análise parcial"
    assert ass.badge_label == "Análise parcial (provisória)", f"Badge incorreto: {ass.badge_label}"
    assert "provisória" in ass.badge_label.lower() or "parcial" in ass.badge_label.lower()
    assert ass.limitation is not None, "limitation deve explicitar o que impede o fechamento definitivo"
    print(f"   [OK] Análise Parcial classificada corretamente: {ass.title} | {ass.badge_label}")
    print(f"        • Limitação explícita: '{ass.limitation}'")

    # ------------------------------------------------------------------
    # 4. Regra Semântica: Distinção entre Null e Zero (Encerrante Ausente)
    # ------------------------------------------------------------------
    print("\n4. Validando Distinção entre Dado Ausente (Null), Zero Registrado e Medido...")
    # No piloto real, automação registrou saídas mas encerrantes não foram digitados:
    assert met.physical_volume_liters is None, (
        f"Encerrante pendente não pode ser 0.0! Esperava None, obteve {met.physical_volume_liters}"
    )
    assert met.physical_volume_state == "not_reported", (
        f"Estado esperado 'not_reported', obteve '{met.physical_volume_state}'"
    )

    # Teste sintético de zero_registered e measured
    m_zero = ReconciliationMetrics(
        automation_revenue=0.0,
        automation_revenue_cents=0,
        pos_revenue=0.0,
        pos_revenue_cents=0,
        difference=0.0,
        difference_cents=0,
        physical_volume_liters=0.0,
        physical_volume_state="zero_registered",
        automation_volume_liters=0.0,
        is_provisional=False,
    )
    assert m_zero.physical_volume_liters == 0.0
    assert m_zero.physical_volume_state == "zero_registered"

    m_medido = ReconciliationMetrics(
        automation_revenue=100.0,
        automation_revenue_cents=10000,
        pos_revenue=100.0,
        pos_revenue_cents=10000,
        difference=0.0,
        difference_cents=0,
        physical_volume_liters=100.0,
        physical_volume_state="measured",
        automation_volume_liters=100.0,
        is_provisional=False,
    )
    assert m_medido.physical_volume_liters == 100.0
    assert m_medido.physical_volume_state == "measured"
    print("   [OK] Estados not_reported (None), zero_registered (0.0) e measured (>0) validados rigorosamente.")

    # ------------------------------------------------------------------
    # 5. Métricas Tipadas e Centavos Inteiros
    # ------------------------------------------------------------------
    print("\n5. Validando Métricas Financeiras e Centavos Inteiros...")
    assert met.automation_revenue == 71.30
    assert met.automation_revenue_cents == 7130
    assert met.pos_revenue == 62.98
    assert met.pos_revenue_cents == 6298
    assert met.difference == -8.32
    assert met.difference_cents == -832
    assert met.difference_definition == "pos_minus_automation"
    print(f"   [OK] Centavos inteiros e floats validados com precisão contábil ({met.difference_cents}¢)")

    # ------------------------------------------------------------------
    # 6. Pendências e Fontes
    # ------------------------------------------------------------------
    print("\n6. Validando Lista de Pendências e Proveniência de Fontes...")
    codes = [p.code for p in contrato.pending_items]
    assert "physical_readings_missing" in codes, "Pendência de encerrantes ausente"
    assert "registers_open" in codes, "Pendência de caixas abertos ausente"

    source_ids = {s.id: s.availability for s in contrato.sources}
    assert source_ids.get("automation") == "available"
    assert source_ids.get("pos") == "available"
    assert source_ids.get("physical_readings") == "missing"
    print("   [OK] Fontes e pendências mapeadas com precisão")

    # ------------------------------------------------------------------
    # 7. Ação Recomendada Somente Leitura / Externa
    # ------------------------------------------------------------------
    print("\n7. Validando Ação Recomendada (Acesso Somente Leitura)...")
    act = contrato.recommended_action
    assert act.execution == "external_manual", f"Ação deve ser external_manual, obteve {act.execution}"
    assert "ERP" in act.label or "encerrantes" in act.label.lower()
    print(f"   [OK] Ação segura: '{act.label}' (execução: {act.execution})")

    # ------------------------------------------------------------------
    # 8. Tratamento de Sem Movimento e Indisponibilidade
    # ------------------------------------------------------------------
    print("\n8. Validando Resposta de Data Sem Movimento (1999-01-01)...")
    res_vazio = tools.auditar_fechamento_turno(data="1999-01-01", turno=1)
    assert res_vazio.get("status") == "sem_movimento"
    assert res_vazio.get("schema_version") == "1.0"
    contrato_vazio = ShiftReconciliationContract.model_validate(res_vazio["contrato"])
    assert contrato_vazio.assessment.finality == "no_movement"
    assert contrato_vazio.assessment.badge_label == "Sem movimentação"
    assert contrato_vazio.context.queried_at is not None
    print("   [OK] Data sem movimento possui contrato estruturado válido com finality='no_movement'")

    # Teste de contrato estruturado para fonte indisponível (erro de ERP)
    contrato_erro = ShiftReconciliationContract(
        schema_version="1.0",
        response_id="reconcil-indisponivel",
        intent="shift_reconciliation",
        context=ReconciliationContext(
            unit_id="posto_01",
            shift_id="1",
            queried_at=datetime.now().astimezone().isoformat(),
            error="Simulated DB Error"
        ),
        assessment=ReconciliationAssessment(
            finality="unavailable",
            severity="critical",
            status_code="FONTE_INDISPONIVEL",
            title="Fonte de dados ERP indisponível",
            limitation="Falha de conexão simulada",
            badge_label="Fonte indisponível",
        ),
        metrics=ReconciliationMetrics(
            automation_revenue=0.0,
            automation_revenue_cents=0,
            pos_revenue=0.0,
            pos_revenue_cents=0,
            difference=0.0,
            difference_cents=0,
            difference_definition="pos_minus_automation",
            physical_volume_liters=None,
            physical_volume_state="not_reported",
            automation_volume_liters=0.0,
            is_provisional=False,
        ),
        pending_items=[PendingItem(code="erp_unavailable", label="Falha ERP", severity="critical")],
        sources=[DataSource(id="erp", label="PostgreSQL ERP", availability="unavailable")],
        recommended_action=RecommendedAction(
            label="Verificar conexão com ERP",
            execution="external_manual",
            detail="Checar porta 5433"
        ),
        explanation=ReconciliationExplanation(text="Erro de conexão."),
    )
    assert contrato_erro.assessment.finality == "unavailable"
    assert contrato_erro.assessment.severity == "critical"
    print("   [OK] Contrato para fonte indisponível (unavailable) validado rigorosamente.")

    # ------------------------------------------------------------------
    # 9. Testes de Renderização Frontend (web/js/aura-chat.js via Node.js)
    # ------------------------------------------------------------------
    print("\n9. Executando Suíte de Testes Frontend no Node.js (AURA Precision Glass)...")

    node_test_script = f"""
    const {{ AuraChatController }} = require('./web/js/aura-chat.js');
    const chat = new AuraChatController();

    const pilotData = {json.dumps(res, ensure_ascii=False)};

    // A. Teste de Renderização do DecisionCard
    const cardHtml = chat.renderTurnoWidget(pilotData);

    // 1. Deve formatar moeda em pt-BR (R$ 8,32 com vírgula, não R$ 8.32 com ponto)
    if (!cardHtml.includes('R$ 8,32') && !cardHtml.includes('-R$ 8,32')) {{
      console.error('FALHA: Diferença não formatada em pt-BR no hero:', cardHtml);
      process.exit(1);
    }}
    if (!cardHtml.includes('R$ 71,30') || !cardHtml.includes('R$ 62,98')) {{
      console.error('FALHA: Faturamento não formatado em pt-BR:', cardHtml);
      process.exit(1);
    }}

    // 2. Deve ter botão de atalho para pendências
    if (!cardHtml.includes('Ver pendências')) {{
      console.error('FALHA: Botão Ver pendências ausente no card');
      process.exit(1);
    }}

    // B. Teste de Fallback Seguro para Versão de Contrato Desconhecida
    const unknownData = {{
      schema_version: '99.0',
      assessment: {{ finality: 'final', title: 'Versão Futura' }},
      metrics: {{ difference: 0 }}
    }};
    const unknownHtml = chat.renderTurnoWidget(unknownData);
    if (!unknownHtml.includes('Versão de Contrato Não Suportada') || unknownHtml.includes('100% Batido')) {{
      console.error('FALHA: Fallback de versão desconhecida fabricou conciliação validada:', unknownHtml);
      process.exit(1);
    }}

    // C. Teste de Blindagem XSS no DecisionCard
    const xssData = {{
      schema_version: '1.0',
      assessment: {{
        finality: 'partial',
        title: '<script>alert(1)</script>Titulo',
        limitation: '<img src=x onerror=alert(2)>Limitacao',
        badge_label: '<b onclick=alert(3)>Badge</b>'
      }},
      metrics: {{ difference: -10, automation_revenue: 100, pos_revenue: 90 }},
      pending_items: [{{ code: 'test', label: '<svg onload=alert(4)>' }}]
    }};
    const xssHtml = chat.renderTurnoWidget(xssData);
    if (xssHtml.includes('<script>') || xssHtml.includes('<img src=x') || xssHtml.includes('<svg onload=')) {{
      console.error('FALHA: Injeção XSS não neutralizada no DecisionCard:', xssHtml);
      process.exit(1);
    }}

    // D. Teste do Evidence Drawer: Aba Formula com Encerrantes Pendentes
    const formulaHtml = chat.renderEvidenceTabContent(pilotData, 'formula');
    // NUNCA pode subtrair 0.000 L fechabomba gerando +10.000 L medidos falsos
    if (formulaHtml.includes('0.000 L (fechabomba)') || formulaHtml.includes('0,000 L (fechabomba)')) {{
      console.error('FALHA: Aba formula substituiu encerrante pendente por 0.000 L falso:', formulaHtml);
      process.exit(1);
    }}
    if (!formulaHtml.includes('Pendente / Não digitado no módulo fechabomba')) {{
      console.error('FALHA: Pendência de encerrante ausente na triangulação volumétrica');
      process.exit(1);
    }}

    // E. Teste do Evidence Drawer: Aba Formula com Sem Movimento
    const semMovData = {json.dumps(res_vazio, ensure_ascii=False)};
    const semMovFormula = chat.renderEvidenceTabContent(semMovData, 'formula');
    if (semMovFormula.includes('Diferença Definitiva') || semMovFormula.includes('batidos com a telemetria')) {{
      console.error('FALHA: Sem movimento inventou Diferença Definitiva:', semMovFormula);
      process.exit(1);
    }}

    // F. Teste do Evidence Drawer: Fallback com Payload Vazio
    const emptyDrawer = chat.renderEvidenceTabContent({{}}, 'formula');
    if (!emptyDrawer.includes('Dados de evidência indisponíveis')) {{
      console.error('FALHA: Payload vazio no drawer não gerou fallback seguro:', emptyDrawer);
      process.exit(1);
    }}

    // G. Teste do Evidence Drawer: Aba Caixas e Identificação de Sessão/PDV
    const caixasHtml = chat.renderEvidenceTabContent(pilotData, 'caixas');
    if (!caixasHtml.includes('Sessão #57 • Terminal PDV 007') || !caixasHtml.includes('MARLON HENRIQUE')) {{
      console.error('FALHA: Aba caixas não exibiu identificadores humanos precisos:', caixasHtml);
      process.exit(1);
    }}

    // H. Teste de Blindagem de escapeHtml contra Primitivos Numéricos / Booleanos (Bug Fixo)
    if (chat.escapeHtml(0) !== '0' || chat.escapeHtml(1) !== '1' || chat.escapeHtml(false) !== 'false' || chat.escapeHtml(null) !== '' || chat.escapeHtml(undefined) !== '') {{
      console.error('FALHA: escapeHtml falhou na sanitização de primitivos');
      process.exit(1);
    }}

    // I. Teste de Formatação de Turno Numérico no Card Executivo (1 -> 1º Turno)
    const numericTurnoData = JSON.parse(JSON.stringify(pilotData));
    numericTurnoData.turno_auditado = 1;
    const numericTurnoHtml = chat.renderTurnoWidget(numericTurnoData);
    if (!numericTurnoHtml.includes('1º Turno')) {{
      console.error('FALHA: Turno numérico 1 não foi formatado amigavelmente para 1º Turno:', numericTurnoHtml);
      process.exit(1);
    }}

    // J. Teste de Preservação de Sessão Caixa ID 0 (Não vira N/D)
    const zeroCaixaData = JSON.parse(JSON.stringify(pilotData));
    zeroCaixaData.triangulacao_caixa.caixas[0].caixa_id = 0;
    const zeroCaixaHtml = chat.renderEvidenceTabContent(zeroCaixaData, 'caixas');
    if (!zeroCaixaHtml.includes('Sessão #0')) {{
      console.error('FALHA: Caixa com id 0 foi substituído por N/D falsamente:', zeroCaixaHtml);
      process.exit(1);
    }}

    // K. Teste de Renderização de Fonte Indisponível (unavailable)
    const unavailData = {{
      status: 'indisponivel',
      schema_version: '1.0',
      intent: 'shift_reconciliation',
      assessment: {{
        finality: 'unavailable',
        severity: 'critical',
        status_code: 'FONTE_INDISPONIVEL',
        title: 'Fonte de dados ERP indisponível',
        badge_label: 'Fonte indisponível',
        limitation: 'Falha de conexão com PostgreSQL'
      }},
      metrics: {{
        automation_revenue: 0,
        pos_revenue: 0,
        difference: 0,
        is_provisional: false
      }}
    }};
    const unavailWidget = chat.renderTurnoWidget(unavailData);
    if (!unavailWidget.includes('Fonte indisponível') || unavailWidget.includes('100% Batido') || unavailWidget.includes('R$ 0,00')) {{
      console.error('FALHA: Card de fonte indisponível inventou métricas ou conciliação validada:', unavailWidget);
      process.exit(1);
    }}
    const unavailFormula = chat.renderEvidenceTabContent(unavailData, 'formula');
    if (!unavailFormula.includes('Fonte Indisponível') || !unavailFormula.includes('A conexão com o banco de dados ERP não pôde ser estabelecida')) {{
      console.error('FALHA: Drawer formula para fonte indisponível não exibiu aviso adequado:', unavailFormula);
      process.exit(1);
    }}

    console.log('NODE_TESTS_OK');
    """

    res_node = subprocess.run(
        ["node", "-e", node_test_script],
        capture_output=True,
        text=True,
        cwd=str(BASE_DIR),
        timeout=15,
    )

    if res_node.returncode != 0:
        print(f"❌ ERRO NOS TESTES NODE.JS:\nSTDOUT: {res_node.stdout}\nSTDERR: {res_node.stderr}")
        sys.exit(1)

    assert "NODE_TESTS_OK" in res_node.stdout
    print("   [OK] Testes de renderização pt-BR, blindagem XSS, fallback de schema e drawer aprovados no Node.js!")

    print("\n" + "=" * 78)
    print("🎉 TODOS OS TESTES DO PRIMEIRO MARCO PASSARAM COM 100% DE SUCESSO!")
    print("=" * 78)


if __name__ == "__main__":
    run_tests()
