"""Squad de Micro-Bots de Operacao e Curadoria Continua (AURA).

Inspirado na arquitetura do estudo 'Bots in Production' (Emergent.sh):
Micro-bots autonomos especializados que operam com Zero-Token Gate:
1. RagMissTrackerBot: Curadoria de gaps de conhecimento do RAG com zero tokens quando sem miss.
2. PartnerSyncContractBot: Auditoria de schema drift e contratos de dados B2B.
3. WeeklyRetailRoiDigestBot: Consolidacao deterministica de ROI e retencao executiva (zero tokens).
Regra estrita: Zero travessoes Unicode em todo o arquivo.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from core.retail_roi_engine import compute_universal_retail_roi

logger = logging.getLogger("aura.ops_micro_bots")


@dataclass
class MicroBotResult:
    """Resultado da execucao de um micro-bot operacional."""

    bot_name: str
    executed_at: str
    status: str
    zero_token_gate_triggered: bool
    llm_called: bool
    tokens_used: int
    summary_message: str
    payload: dict[str, Any] = field(default_factory=dict)


class RagMissTrackerBot:
    """Micro-bot de curadoria de lacunas no RAG (Miss-Tracker).

    Analisa logs de consultas locais. Se nenhuma consulta ficou abaixo do threshold (score < 0.45),
    o Zero-Token Gate encerra a execucao em < 2ms com zero chamadas ao LLM.
    """

    def __init__(self, score_threshold: float = 0.45) -> None:
        self.score_threshold = score_threshold

    def run(self, query_logs: list[dict[str, Any]] | None = None) -> MicroBotResult:
        """Executa a varredura de lacunas de RAG."""
        now_iso = datetime.now(UTC).isoformat()
        logs = query_logs or []

        # Zero-Token Gate: Se nao ha queries ou nenhuma abaixo do limiar, encerra imediatamente
        low_score_queries = [
            q for q in logs if float(q.get("rag_score") or 1.0) < self.score_threshold
        ]

        if not low_score_queries:
            return MicroBotResult(
                bot_name="RagMissTrackerBot",
                executed_at=now_iso,
                status="NO_MISS_DETECTED",
                zero_token_gate_triggered=True,
                llm_called=False,
                tokens_used=0,
                summary_message="Zero-Token Gate ativo: nenhuma consulta abaixo do limiar de 0.45 detectada.",
                payload={"inspected_count": len(logs), "low_score_count": 0},
            )

        # Agrupamento deterministico por vertical sem chamar LLM
        gaps_by_vertical: dict[str, list[str]] = {}
        for q in low_score_queries:
            vert = str(q.get("vertical") or "general_retail")
            q_text = str(q.get("query") or "consulta desconhecida")
            gaps_by_vertical.setdefault(vert, []).append(q_text)

        return MicroBotResult(
            bot_name="RagMissTrackerBot",
            executed_at=now_iso,
            status="GAPS_IDENTIFIED",
            zero_token_gate_triggered=False,
            llm_called=False,  # Agrupamento deterministico dispensa LLM
            tokens_used=0,
            summary_message=f"Identificadas {len(low_score_queries)} consultas com score abaixo de {self.score_threshold}.",
            payload={
                "inspected_count": len(logs),
                "low_score_count": len(low_score_queries),
                "gaps_by_vertical": gaps_by_vertical,
            },
        )


class PartnerSyncContractBot:
    """Micro-bot de auditoria de contratos B2B e schema drift de parceiros.

    Verifica violacoes fisicas e desvios de campos nos lotes raw-sync.
    Zero-Token Gate ativo se nao houver rejeicoes.
    """

    def run(
        self,
        quarantined_count: int = 0,
        warnings: list[str] | None = None,
        station_id: str = "default_station",
    ) -> MicroBotResult:
        """Audita integridade dos lotes recebidos."""
        now_iso = datetime.now(UTC).isoformat()
        warn_list = warnings or []

        # Zero-Token Gate: Se nao ha linhas em quarentena ou avisos, lote e 100% compativel
        if quarantined_count == 0 and not warn_list:
            return MicroBotResult(
                bot_name="PartnerSyncContractBot",
                executed_at=now_iso,
                status="CONTRACT_CLEAN",
                zero_token_gate_triggered=True,
                llm_called=False,
                tokens_used=0,
                summary_message=f"Zero-Token Gate ativo: lote de {station_id} sem violacoes de contrato ou schema drift.",
                payload={"station_id": station_id, "quarantined_count": 0, "warnings": []},
            )

        # Monta parecer tecnico deterministico para o desenvolvedor parceiro
        corrective_advice = [
            f"- Alerta de contrato: {w}" for w in warn_list[:5]
        ]
        if quarantined_count > 0:
            corrective_advice.append(
                f"- Foram postas em quarentena {quarantined_count} linhas violando invariantes fisicas."
            )

        return MicroBotResult(
            bot_name="PartnerSyncContractBot",
            executed_at=now_iso,
            status="CONTRACT_VIOLATION_DETECTED",
            zero_token_gate_triggered=False,
            llm_called=False,
            tokens_used=0,
            summary_message=f"Lote de {station_id} apresentou {len(warn_list)} alertas e {quarantined_count} quarentenas.",
            payload={
                "station_id": station_id,
                "quarantined_count": quarantined_count,
                "warnings": warn_list,
                "corrective_guidance": corrective_advice,
            },
        )


class WeeklyRetailRoiDigestBot:
    """Micro-bot deterministico de fechamento semanal de ROI e retencao de clientes.

    Calcula quanto cada filial/loja economizou e gera o resumo executivo de Risk-Reversal (3x ROI).
    Zero tokens de LLM utilizados (100% deterministico em Python).
    """

    def run(
        self,
        store_ids: list[str],
        staging_store: Any,
        domain_pack: str = "retail_supermarket",
        monthly_subscription_brl: float = 490.0,
    ) -> MicroBotResult:
        """Executa consolidacao semanal de ROI para todas as lojas ativas."""
        now_iso = datetime.now(UTC).isoformat()
        stores = store_ids or ["default_store"]
        results: list[dict[str, Any]] = []

        total_net_roi = 0.0
        all_guarantees_met = True

        for s_id in stores:
            roi_data = compute_universal_retail_roi(
                store_id=s_id,
                staging_store=staging_store,
                domain_pack=domain_pack,
                monthly_subscription_brl=monthly_subscription_brl,
            )
            net_90d = roi_data["summary"]["roi_90_days_net_brl"]
            total_net_roi += net_90d
            if not roi_data["summary"]["guarantee_3x_met"]:
                all_guarantees_met = False

            results.append({
                "store_id": s_id,
                "vertical": roi_data.get("vertical"),
                "roi_multiple": roi_data["summary"]["roi_multiple"],
                "roi_90_days_net_brl": net_90d,
                "guarantee_3x_met": roi_data["summary"]["guarantee_3x_met"],
            })

        summary_msg = (
            f"Relatorio semanal de retencao processado para {len(stores)} lojas. "
            f"Retorno liquido acumulado: R$ {total_net_roi:,.2f} em 90 dias. "
            f"Garantia minima de 3x atingida: {'SIM' if all_guarantees_met else 'PARCIAL'}."
        )

        return MicroBotResult(
            bot_name="WeeklyRetailRoiDigestBot",
            executed_at=now_iso,
            status="DIGEST_GENERATED",
            zero_token_gate_triggered=True,
            llm_called=False,
            tokens_used=0,
            summary_message=summary_msg,
            payload={
                "stores_count": len(stores),
                "total_net_roi_90d_brl": round(total_net_roi, 2),
                "all_guarantees_met": all_guarantees_met,
                "store_breakdowns": results,
            },
        )
