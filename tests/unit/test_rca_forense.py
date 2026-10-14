"""
Testes Unitarios do Motor Forense de Causa-Raiz (RCA Forense v1.0).
Valida contratos Pydantic, deteccao dos 4 padroes matematicos,
barreira de tolerancia anti-fadiga e conformidade estrita Human-in-the-Loop (HITL).
Zero travessoes em todo o arquivo.
"""

from decimal import Decimal
from unittest.mock import MagicMock, patch
import pytest

from core.schemas.rca import (
    RCAEvidenceItem,
    RCAHypothesis,
    RCARecommendation,
    RCAReport,
)
from core.tools import PostoTools
from core.semantic_router import SemanticRouter
from core.aura_engine import AuraEngine


class TestRCAContracts:
    """Valida a integridade dos contratos e schemas Pydantic de RCA."""

    def test_rca_evidence_item_creation(self):
        item = RCAEvidenceItem(
            evidence_id="EV-001",
            pattern_type="abastecimento_orfao",
            source_table="abastecimentos",
            description="Abastecimento no Bico 01 de R$ 150.00 sem cupom fiscal no PDV.",
            occurred_at="14:32:00",
            amount_reais=150.0,
            volume_liters=25.0,
            bico="01",
            tanque="01",
            combustivel="GASOLINA COMUM",
        )
        assert item.evidence_id == "EV-001"
        assert item.pattern_type == "abastecimento_orfao"
        assert item.amount_reais == 150.0
        assert item.source_table == "abastecimentos"

    def test_rca_hypothesis_immutability(self):
        hyp = RCAHypothesis(
            hypothesis_id="HYP-01",
            pattern_code="ABASTECIMENTO_ORFAO",
            title="Abastecimento Orfao no Bico 01",
            confidence_score=0.95,
            explained_amount_reais=150.0,
            explained_volume_liters=25.0,
            severity="high",
            summary="Abastecimento fisico sem cupom no PDV.",
            evidences=[],
            recommended_action="Conferir cameras da pista as 14:32.",
        )
        assert hyp.confidence_score == 0.95
        with pytest.raises(Exception):
            hyp.confidence_score = 0.50  # type: ignore

    def test_rca_report_full_validation(self):
        report = RCAReport(
            schema_version="1.0",
            report_id="rca-2026-10-14-t1",
            intent="investigar_causa_raiz",
            generated_at="2026-10-14T11:00:00Z",
            unit_id="posto_01",
            target_date="2026-10-14",
            target_shift="1",
            cash_tolerance_reais=50.0,
            total_divergence_reais=-150.0,
            divergence_type="furo_caixa",
            total_explained_reais=150.0,
            unexplained_reais=0.0,
            confidence_overall=0.95,
            hypotheses=[],
            recommendations=[],
            human_in_the_loop=True,
            execution_mode="on_demand",
            summary_markdown="Laudo concluido com 95% de certeza.",
        )
        assert report.human_in_the_loop is True
        assert report.execution_mode == "on_demand"
        assert report.unexplained_reais == 0.0


class TestRCAPatternsDetection:
    """Valida a logica matematica dos 4 padroes forenses no PostoTools."""

    @pytest.fixture
    def tools_instance(self):
        mock_rag = MagicMock()
        return PostoTools(rag_engine=mock_rag)

    def test_anti_fatigue_tolerance_barrier(self, tools_instance):
        """Divergencia inferior a cash_tolerance nao gera alarmes falsos."""
        mock_conciliacao = {
            "status": "ok",
            "data_auditada": "2026-10-14",
            "metrics": {"difference": -23.47},
            "resumo_executivo": {"diferenca_financeira_caixa": -23.47},
            "triangulacao_pista": {"diferenca_litros_pista": 0.0, "detalhamento_bicos": []},
            "triangulacao_caixa": {"caixas": []},
        }
        with patch.object(tools_instance, "auditar_fechamento_turno", return_value=mock_conciliacao):
            res = tools_instance.investigar_causa_raiz_turno(data="2026-10-14")
            assert res["status"] == "ok"
            assert res["diagnostico"] == "conforme"
            assert res["confidence_overall"] == 1.0
            assert "Conforme" in res["summary_markdown"]

    def test_orphan_fueling_pattern_detection(self, tools_instance):
        """Detecta abastecimento orfao com valor aderente a quebra de caixa."""
        mock_conciliacao = {
            "status": "ok",
            "data_auditada": "2026-10-14",
            "metrics": {"difference": -150.00},
            "resumo_executivo": {"diferenca_financeira_caixa": -150.00},
            "triangulacao_pista": {"diferenca_litros_pista": 25.0, "detalhamento_bicos": []},
            "triangulacao_caixa": {"caixas": []},
        }

        mock_orfaos = [
            {
                "idabast": "4128",
                "bico": "03",
                "tanque": "01",
                "codpro": "1",
                "nompro": "GASOLINA COMUM",
                "litros": Decimal("25.000"),
                "total": Decimal("150.00"),
                "data": "2026-10-14",
                "hora": "14:22:10",
                "ei": Decimal("1000.0"),
                "encerrante": Decimal("1025.0"),
                "turno": "1",
            }
        ]

        with patch.object(tools_instance, "auditar_fechamento_turno", return_value=mock_conciliacao), \
             patch("core.tools.get_erp_connection") as mock_conn:
            mock_cur = MagicMock()
            # Primeira chamada: orfaos, segunda: estornos, terceira: formas
            mock_cur.fetchall.side_effect = [mock_orfaos, [], []]
            mock_conn.return_value.cursor.return_value.__enter__.return_value = mock_cur

            res = tools_instance.investigar_causa_raiz_turno(data="2026-10-14")
            assert res["status"] == "ok"
            assert res["total_explained_reais"] >= 150.0
            assert len(res["hipoteses"]) >= 1

            hyp_orfao = next(h for h in res["hipoteses"] if h["pattern_code"] == "ABASTECIMENTO_ORFAO")
            assert hyp_orfao["confidence_score"] >= 0.90
            assert "Bico 03" in hyp_orfao["title"]
            assert hyp_orfao["explained_amount_reais"] == 150.0

    def test_inmetro_bucket_calibration_pattern(self, tools_instance):
        """Detecta variacao compativel com balde de 20L Inmetro nao lancado no fechabomba."""
        mock_conciliacao = {
            "status": "ok",
            "data_auditada": "2026-10-14",
            "metrics": {"difference": -119.80},
            "resumo_executivo": {"diferenca_financeira_caixa": -119.80},
            "triangulacao_pista": {
                "diferenca_litros_pista": 20.0,
                "detalhamento_bicos": [
                    {
                        "bico": "02",
                        "tanque": "01",
                        "combustivel": "GASOLINA COMUM",
                        "afericao_litros": 0.0,
                        "diferenca_litros": 20.02,
                        "preco_unitario": 5.99,
                    }
                ],
            },
            "triangulacao_caixa": {"caixas": []},
        }

        with patch.object(tools_instance, "auditar_fechamento_turno", return_value=mock_conciliacao), \
             patch("core.tools.get_erp_connection") as mock_conn:
            mock_cur = MagicMock()
            mock_cur.fetchall.side_effect = [[], [], []]
            mock_conn.return_value.cursor.return_value.__enter__.return_value = mock_cur

            res = tools_instance.investigar_causa_raiz_turno(data="2026-10-14")
            assert res["status"] == "ok"
            assert len(res["hipoteses"]) >= 1

            hyp_inmetro = next(h for h in res["hipoteses"] if h["pattern_code"] == "AFERICAO_INMETRO_NAO_LANCADA")
            assert hyp_inmetro["confidence_score"] >= 0.90
            assert hyp_inmetro["explained_volume_liters"] == 20.0
            assert "20L" in hyp_inmetro["title"]

    def test_cancelled_sale_descompassado_pattern(self, tools_instance):
        """Detecta cancelamento no PDV coincidente com quebra de caixa."""
        mock_conciliacao = {
            "status": "ok",
            "data_auditada": "2026-10-14",
            "metrics": {"difference": -85.50},
            "resumo_executivo": {"diferenca_financeira_caixa": -85.50},
            "triangulacao_pista": {"diferenca_litros_pista": 0.0, "detalhamento_bicos": []},
            "triangulacao_caixa": {"caixas": []},
        }

        mock_estornos = [
            {
                "codi": "10023",
                "cupom": "9921",
                "pdv": "1",
                "turno": "1",
                "vendedor": "JOAO",
                "valortotal": Decimal("85.50"),
                "dtem": "2026-10-14",
                "hsmov": "10:15:00",
                "dtcanc": "2026-10-14",
                "ven_ts_cancelamento": "2026-10-14 10:16:00",
                "motivo": "Cliente desistiu da compra",
                "situ": "C",
            }
        ]

        with patch.object(tools_instance, "auditar_fechamento_turno", return_value=mock_conciliacao), \
             patch("core.tools.get_erp_connection") as mock_conn:
            mock_cur = MagicMock()
            mock_cur.fetchall.side_effect = [[], mock_estornos, []]
            mock_conn.return_value.cursor.return_value.__enter__.return_value = mock_cur

            res = tools_instance.investigar_causa_raiz_turno(data="2026-10-14")
            assert res["status"] == "ok"
            hyp_estorno = next(h for h in res["hipoteses"] if h["pattern_code"] == "ESTORNO_DESCOMPASSADO")
            assert hyp_estorno["confidence_score"] >= 0.90
            assert hyp_estorno["explained_amount_reais"] == 85.50

    def test_payment_inversion_pattern(self, tools_instance):
        """Detecta falta em dinheiro compensada por sobra em cartao/pix."""
        mock_conciliacao = {
            "status": "ok",
            "data_auditada": "2026-10-14",
            "metrics": {"difference": -100.00},
            "resumo_executivo": {"diferenca_financeira_caixa": -100.00},
            "triangulacao_pista": {"diferenca_litros_pista": 0.0, "detalhamento_bicos": []},
            "triangulacao_caixa": {
                "caixas": [
                    {
                        "caixa_id": 1,
                        "dinheiro": 200.00,
                        "cartao": 800.00,
                        "total_declarado": 1000.00,
                    }
                ]
            },
        }

        # PDV esperava 300 em dinheiro e 700 em cartao (ou seja dif_dinh = -100, dif_cart = +100)
        mock_formas = [
            {"pdv": "1", "forma_grupo": "DINHEIRO", "qtd": 10, "total_faturado": Decimal("300.00")},
            {"pdv": "1", "forma_grupo": "CARTAO_PIX", "qtd": 20, "total_faturado": Decimal("700.00")},
        ]

        with patch.object(tools_instance, "auditar_fechamento_turno", return_value=mock_conciliacao), \
             patch("core.tools.get_erp_connection") as mock_conn:
            mock_cur = MagicMock()
            mock_cur.fetchall.side_effect = [[], [], mock_formas]
            mock_conn.return_value.cursor.return_value.__enter__.return_value = mock_cur

            res = tools_instance.investigar_causa_raiz_turno(data="2026-10-14")
            assert res["status"] == "ok"
            hyp_inv = next(h for h in res["hipoteses"] if h["pattern_code"] == "INVERSAO_FORMA_PAGAMENTO")
            assert hyp_inv["confidence_score"] >= 0.90
            assert hyp_inv["explained_amount_reais"] == 100.0


class TestRCARouterAndEngineIntegration:
    """Valida o roteamento semantico e execucao no AuraEngine."""

    def test_semantic_router_rca_intent(self):
        router = SemanticRouter()
        queries = [
            "Investigar causa raiz da quebra",
            "Por que deu furo no caixa hoje?",
            "Analisar hipótese da quebra de caixa",
            "Fazer perícia forense no fechamento",
            "investigar a quebra de turno",
        ]
        for q in queries:
            intent, conf, method = router.route(q)
            assert intent == "investigar_causa_raiz", f"Query '{q}' deveria rotear para investigar_causa_raiz, obteve {intent}"

    @pytest.mark.asyncio
    async def test_aura_engine_execute_tool_rca(self):
        engine = AuraEngine()
        res = await engine.execute_tool("investigar_causa_raiz", {"data": "hoje"})
        assert res["status"] == "success"
        data = res["data"]
        assert data["intent"] == "investigar_causa_raiz"
        assert "report" in data
        assert "contrato" in data
        assert data["report"]["human_in_the_loop"] is True
