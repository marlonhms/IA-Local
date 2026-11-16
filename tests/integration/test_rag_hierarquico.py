"""
Suíte de Testes Automatizada: RAG Hierárquico Multi-Filial & MapReduce (Fase 3.5).
Valida:
1. Contratos Pydantic v2 (validação de schemas, tipos, limites e JSON compacto).
2. Simulação de Fan-Out concorrente com asyncio para 50 filiais.
3. Resiliência com SLA de 5.0s e Degradação Graciosa (Graceful Degradation de nós offline).
4. Agregação Fan-In e ranqueamento de criticidade (Crítico -> Confortável).
5. Economia drástica de tokens (>85% em relação a texto livre).
"""
import asyncio
import sys
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path

# Protege stdout no terminal Windows contra cp1252
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Ajusta path para importar módulos locais
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.schemas.network import (
    BranchStatus,
    MetricUrgency,
    BranchConfig,
    NetworkQueryRequest,
    BranchProbeRequest,
    BranchMetricPayload,
    NetworkConsolidatedReport,
    rank_branches_by_urgency,
    calculate_token_savings,
)


class TestRAGHierarquicoMultiFilial(unittest.TestCase):
    """Testes unitários e de concorrência assíncrona para a arquitetura de rede."""

    def test_01_pydantic_contracts_validation(self):
        """Valida integridade estrutural dos contratos Pydantic v2."""
        # Payload válido do Posto Centro
        payload_data = {
            "filial_id": "posto_centro_01",
            "filial_nome": "Posto Centro",
            "status_conexao": "ONLINE",
            "combustivel": "Gasolina Comum",
            "saldo_litros": 2450.0,
            "capacidade_litros": 30000.0,
            "status": "Critico",
            "autonomia_horas": 14.2,
            "consumo_medio_dia": 4140.0,
            "alerta_fim_de_semana": True,
            "tempo_resposta_ms": 120.5,
        }
        payload = BranchMetricPayload(**payload_data)
        self.assertEqual(payload.filial_id, "posto_centro_01")
        self.assertEqual(payload.status, MetricUrgency.CRITICO)
        self.assertEqual(payload.status_conexao, BranchStatus.ONLINE)
        self.assertTrue(payload.alerta_fim_de_semana)

        # Serialização compacta (JSON enxuto)
        json_str = payload.model_dump_json(exclude_none=True)
        self.assertIn("posto_centro_01", json_str)
        # O payload deve ser compacto (< 400 bytes, gerando menos de 100 tokens)
        self.assertLess(len(json_str.encode("utf-8")), 400)

    def test_02_graceful_degradation_offline_fallback(self):
        """Valida geração determinística do payload de fallback para nós offline."""
        cfg = BranchConfig(
            filial_id="posto_sul_03",
            filial_nome="Posto Sul",
            endpoint_url="http://192.168.1.103:8000",
            timeout_segundos=5.0,
        )
        fallback = BranchMetricPayload.criar_fallback_offline(cfg)
        self.assertEqual(fallback.filial_id, "posto_sul_03")
        self.assertEqual(fallback.status_conexao, BranchStatus.OFFLINE)
        self.assertEqual(fallback.status, MetricUrgency.ALERTA)
        self.assertIn("offline", fallback.aviso.lower())
        self.assertIn("sem resposta em 5.0s", fallback.aviso)
        self.assertIsNone(fallback.saldo_litros)

    def test_03_ranking_by_urgency(self):
        """Valida algoritmo de ordenação: Crítico -> Alerta -> Offline -> Regular -> Confortável."""
        p_critico_1 = BranchMetricPayload(
            filial_id="p_critico_urgente",
            filial_nome="Posto Urgente",
            status=MetricUrgency.CRITICO,
            autonomia_horas=4.5,
        )
        p_critico_2 = BranchMetricPayload(
            filial_id="p_critico_medio",
            filial_nome="Posto Médio",
            status=MetricUrgency.CRITICO,
            autonomia_horas=18.0,
        )
        p_offline = BranchMetricPayload(
            filial_id="p_offline",
            filial_nome="Posto Sem Net",
            status_conexao=BranchStatus.OFFLINE,
            status=MetricUrgency.ALERTA,
            aviso="Offline",
        )
        p_alerta = BranchMetricPayload(
            filial_id="p_alerta",
            filial_nome="Posto Alerta",
            status=MetricUrgency.ALERTA,
            autonomia_horas=36.0,
        )
        p_regular = BranchMetricPayload(
            filial_id="p_regular",
            filial_nome="Posto Regular",
            status=MetricUrgency.REGULAR,
            autonomia_horas=72.0,
        )
        p_confortavel = BranchMetricPayload(
            filial_id="p_confortavel",
            filial_nome="Posto Confortável",
            status=MetricUrgency.CONFORTAVEL,
            autonomia_horas=150.0,
        )

        lista = [p_confortavel, p_regular, p_critico_2, p_offline, p_alerta, p_critico_1]
        ranking = rank_branches_by_urgency(lista)

        self.assertEqual(ranking[0], "p_critico_urgente", "Posto com menor autonomia crítica deve vir em 1º")
        self.assertEqual(ranking[1], "p_critico_medio", "Posto com segunda menor autonomia deve vir em 2º")
        self.assertEqual(ranking[2], "p_alerta", "Posto em alerta deve vir antes de regulares")
        self.assertIn("p_offline", ranking)
        self.assertEqual(ranking[-1], "p_confortavel", "Posto mais confortável deve vir em último")

    def test_04_token_savings_calculation(self):
        """Valida que o retorno enxuto Pydantic JSON economiza > 85% de tokens contra texto puro."""
        payloads = []
        for i in range(50):
            payloads.append(
                BranchMetricPayload(
                    filial_id=f"posto_{i:02d}",
                    filial_nome=f"Posto Filial {i}",
                    combustivel="Gasolina Comum",
                    saldo_litros=15000.0,
                    capacidade_litros=30000.0,
                    status=MetricUrgency.REGULAR,
                    autonomia_horas=48.0,
                    consumo_medio_dia=7500.0,
                )
            )

        # Baseline: 1.000 tokens por filial em texto livre
        savings_pct = calculate_token_savings(payloads, baseline_tokens_per_branch=1000)
        self.assertGreater(savings_pct, 85.0, f"Economia de tokens calculada: {savings_pct}%, esperava > 85%")

    def test_05_concurrent_fanout_sla_resilience(self):
        """
        Simula execução Fan-Out concorrente de 50 filiais com asyncio:
        - 46 filiais respondem rapidamente (< 150ms).
        - 2 filiais com latência excessiva (estouram SLA de 5.0s).
        - 2 filiais com conexão recusada (queda de link).
        Garante que a agregação Fan-In consolida os dados sem quebrar e cumpre o SLA global.
        """
        async def run_simulation():
            # Cria 50 filiais
            configs = [
                BranchConfig(
                    filial_id=f"filial_{i:02d}",
                    filial_nome=f"Posto {i}",
                    endpoint_url=f"http://10.0.0.{i}:8000",
                    timeout_segundos=5.0,
                )
                for i in range(1, 51)
            ]

            async def simular_chamada_borda(cfg: BranchConfig) -> BranchMetricPayload:
                idx = int(cfg.filial_id.split("_")[1])
                try:
                    if idx in (13, 27):
                        # Simula nó com timeout severo (6.0s)
                        await asyncio.sleep(6.0)
                        return BranchMetricPayload(
                            filial_id=cfg.filial_id,
                            filial_nome=cfg.filial_nome,
                            status=MetricUrgency.REGULAR,
                            autonomia_horas=50.0,
                        )
                    elif idx in (40, 48):
                        # Simula nó com queda de link imediata
                        raise ConnectionRefusedError(f"Link down em {cfg.filial_nome}")
                    else:
                        # Nó saudável responde em 30-100ms
                        await asyncio.sleep(0.05)
                        urgencia = MetricUrgency.CRITICO if idx == 5 else MetricUrgency.REGULAR
                        autonomia = 8.0 if idx == 5 else 72.0
                        return BranchMetricPayload(
                            filial_id=cfg.filial_id,
                            filial_nome=cfg.filial_nome,
                            combustivel="Gasolina Comum",
                            saldo_litros=12000.0,
                            capacidade_litros=30000.0,
                            status=urgencia,
                            autonomia_horas=autonomia,
                            consumo_medio_dia=4000.0,
                            tempo_resposta_ms=50.0,
                        )
                except (asyncio.TimeoutError, ConnectionRefusedError, Exception) as exc:
                    return BranchMetricPayload.criar_fallback_offline(cfg, aviso=f"Filial {cfg.filial_nome} offline ({str(exc)})")

            # Fan-Out assíncrono com timeout individual de 5.0s por nó
            async def wrapped_probe(cfg: BranchConfig) -> BranchMetricPayload:
                try:
                    return await asyncio.wait_for(simular_chamada_borda(cfg), timeout=cfg.timeout_segundos)
                except asyncio.TimeoutError:
                    return BranchMetricPayload.criar_fallback_offline(cfg, aviso=f"Filial {cfg.filial_nome} offline (timeout > {cfg.timeout_segundos:.1f}s)")

            start_t = time.perf_counter()
            tarefas = [wrapped_probe(cfg) for cfg in configs]
            resultados = await asyncio.gather(*tarefas)
            elapsed_s = time.perf_counter() - start_t

            # Validações Fan-In
            total_nós = len(resultados)
            online = sum(1 for r in resultados if r.status_conexao == BranchStatus.ONLINE)
            offline = sum(1 for r in resultados if r.status_conexao != BranchStatus.ONLINE)
            avisos = [r.aviso for r in resultados if r.aviso]
            ranking = rank_branches_by_urgency(resultados)
            savings = calculate_token_savings(resultados)

            report = NetworkConsolidatedReport(
                total_filiais=total_nós,
                filiais_online=online,
                filiais_offline=offline,
                payloads=resultados,
                avisos_degradacao=avisos,
                ranking_criticidade=ranking,
                latencia_total_ms=elapsed_s * 1000.0,
                economia_tokens_pct=savings,
            )

            return report, elapsed_s

        report, elapsed_s = asyncio.run(run_simulation())

        # Asserções críticas de resiliência e concorrência
        self.assertEqual(report.total_filiais, 50)
        self.assertEqual(report.filiais_online, 46, "46 filiais saudáveis devem responder com sucesso")
        self.assertEqual(report.filiais_offline, 4, "4 filiais (2 timeouts + 2 erros de rede) devem estar em contingência")
        self.assertEqual(len(report.avisos_degradacao), 4)

        # O tempo total deve respeitar o SLA de 5.0s (com pequena margem de agendamento do SO < 5.5s)
        self.assertLess(elapsed_s, 5.5, f"O Fan-Out concorrente demorou {elapsed_s:.2f}s, excedendo o SLA de 5s!")

        # O posto crítico (filial_05) deve figurar no topo do ranking
        self.assertEqual(report.ranking_criticidade[0], "filial_05", "Filial 05 (crítica) deve liderar o ranking")

        # Economia de tokens deve ser > 85%
        self.assertGreater(report.economia_tokens_pct, 85.0)


if __name__ == "__main__":
    print("=" * 75)
    print("🌐 SUÍTE DE TESTES: RAG HIERÁRQUICO MULTI-FILIAL & MAPREDUCE (FASE 3.5)")
    print("=" * 75)
    unittest.main(verbosity=2)
