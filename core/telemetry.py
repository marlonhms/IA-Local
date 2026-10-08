"""
Modulo de Telemetria de Desempenho, UX e Observabilidade SRE da AURA.
Coleta e consolidacao de SLIs criticos:
- TTFT (Time-to-First-Token)
- Tempo de Hidratacao de Micro-Widgets GenUI (ms entre ui_skeleton e ui_complete)
- Contadores transacionais de Acoes (solicitadas, aprovadas, rollbacks)
- Bloqueios de Seguranca (RBAC e OWASP LLM03)
Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

import threading
import statistics
from collections import deque
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Union

from core.config import get_feature_flags


class AuraSRETelemetry:
    """
    Coletor central de telemetria SRE em memoria com suporte a persistencia duravel.
    Mapeia os SLIs de desempenho percebido, confiabilidade transacional e seguranca.
    """

    _instance: Optional[AuraSRETelemetry] = None
    _instance_lock = threading.Lock()

    def __init__(self, session_memory=None, max_samples: int = 1000):
        self._lock = threading.Lock()
        self.session_memory = session_memory
        self.max_samples = max_samples

        self._ttft_samples: deque[float] = deque(maxlen=max_samples)
        self._hydration_samples: deque[float] = deque(maxlen=max_samples)
        self._total_actions_requested: int = 0
        self._total_actions_approved: int = 0
        self._total_actions_rolled_back: int = 0
        self._security_blocks: int = 0

    @classmethod
    def get_instance(cls, session_memory=None) -> AuraSRETelemetry:
        """Retorna a instancia singleton do coletor de telemetria."""
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls(session_memory=session_memory)
            elif session_memory is not None and cls._instance.session_memory is None:
                cls._instance.session_memory = session_memory
            return cls._instance

    def reset(self) -> None:
        """Reinicia os contadores e amostras em memoria (util para suites de teste)."""
        with self._lock:
            self._ttft_samples.clear()
            self._hydration_samples.clear()
            self._total_actions_requested = 0
            self._total_actions_approved = 0
            self._total_actions_rolled_back = 0
            self._security_blocks = 0

    def record_ttft(self, ms: float, session_id: Optional[str] = None) -> None:
        """Registra amostra de Time-to-First-Token em milissegundos."""
        if ms is None or ms < 0:
            return
        val = float(ms)
        with self._lock:
            self._ttft_samples.append(val)

        if self.session_memory is not None:
            try:
                self.session_memory.save_telemetry_metric(
                    metric_type="ttft_ms",
                    metric_value=val,
                    session_id=session_id,
                )
            except Exception:
                pass

    def record_hydration(
        self,
        ms: float,
        session_id: Optional[str] = None,
        tool_call_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Registra tempo de hidratacao do micro-widget (ms entre skeleton e complete)."""
        if ms is None or ms < 0:
            return
        val = float(ms)
        with self._lock:
            self._hydration_samples.append(val)

        if self.session_memory is not None:
            try:
                self.session_memory.save_telemetry_metric(
                    metric_type="hydration_ms",
                    metric_value=val,
                    session_id=session_id,
                    tool_call_id=tool_call_id,
                    details=details,
                )
            except Exception:
                pass

    def record_action_requested(
        self,
        action_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> None:
        """Incrementa o total de acoes transacionais solicitadas."""
        with self._lock:
            self._total_actions_requested += 1

        if self.session_memory is not None:
            try:
                self.session_memory.save_telemetry_metric(
                    metric_type="action_requested",
                    metric_value=1.0,
                    session_id=session_id,
                    details={"action_id": action_id},
                )
            except Exception:
                pass

    def record_action_approved(
        self,
        action_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> None:
        """Incrementa o total de acoes transacionais aprovadas com voucher."""
        with self._lock:
            self._total_actions_approved += 1

        if self.session_memory is not None:
            try:
                self.session_memory.save_telemetry_metric(
                    metric_type="action_approved",
                    metric_value=1.0,
                    session_id=session_id,
                    details={"action_id": action_id},
                )
            except Exception:
                pass

    def record_action_rolled_back(
        self,
        action_id: Optional[str] = None,
        session_id: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> None:
        """Incrementa o total de acoes que sofreram rollback por erro ou timeout."""
        with self._lock:
            self._total_actions_rolled_back += 1

        if self.session_memory is not None:
            try:
                self.session_memory.save_telemetry_metric(
                    metric_type="action_rolled_back",
                    metric_value=1.0,
                    session_id=session_id,
                    details={"action_id": action_id, "reason": reason},
                )
            except Exception:
                pass

    def record_security_block(
        self,
        reason: Optional[str] = None,
        session_id: Optional[str] = None,
        tool_call_id: Optional[str] = None,
    ) -> None:
        """Incrementa o total de bloqueios por RBAC ou OWASP LLM03."""
        with self._lock:
            self._security_blocks += 1

        if self.session_memory is not None:
            try:
                self.session_memory.save_telemetry_metric(
                    metric_type="security_block",
                    metric_value=1.0,
                    session_id=session_id,
                    tool_call_id=tool_call_id,
                    details={"reason": reason},
                )
            except Exception:
                pass

    def record_client_report(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processa relatorio de metricas enviado pelo frontend (cliente).
        Trata hidratacao, TTFT percebido, rollbacks e bloqueios de seguranca.
        """
        if not isinstance(report, dict):
            return {"status": "ignored", "reason": "invalid_payload"}

        session_id = report.get("session_id")
        tool_call_id = report.get("tool_call_id")
        action_id = report.get("action_id")
        details = report.get("details") or {}

        # 1. Hidratacao reportada pelo cliente
        if report.get("hydration_ms") is not None:
            try:
                h_ms = float(report["hydration_ms"])
                self.record_hydration(
                    ms=h_ms,
                    session_id=session_id,
                    tool_call_id=tool_call_id,
                    details={"source": "client", **details},
                )
            except (ValueError, TypeError):
                pass

        # 2. TTFT percebido no cliente
        if report.get("ttft_ms") is not None:
            try:
                t_ms = float(report["ttft_ms"])
                self.record_ttft(ms=t_ms, session_id=session_id)
            except (ValueError, TypeError):
                pass

        # 3. Rollback de acao ocorrido no frontend
        is_rollback = bool(report.get("is_rollback") or report.get("action_status") == "rolled_back")
        if is_rollback:
            self.record_action_rolled_back(
                action_id=action_id,
                session_id=session_id,
                reason=report.get("reason") or details.get("reason"),
            )

        # 4. Bloqueio de seguranca detectado no cliente
        is_sec_block = bool(report.get("is_security_block"))
        if is_sec_block:
            self.record_security_block(
                reason=report.get("reason") or details.get("reason") or "Client security block",
                session_id=session_id,
                tool_call_id=tool_call_id,
            )

        return {"status": "ok", "result": "recorded"}

    def get_metrics_summary(self) -> Dict[str, Any]:
        """
        Retorna relatorio consolidado dos SLIs de SRE para consumo do endpoint de observabilidade.
        """
        with self._lock:
            ttft_list = list(self._ttft_samples)
            hyd_list = list(self._hydration_samples)
            req = self._total_actions_requested
            appr = self._total_actions_approved
            roll = self._total_actions_rolled_back
            sec = self._security_blocks

        # Calculo estatistico de TTFT
        if ttft_list:
            ttft_avg = statistics.mean(ttft_list)
            ttft_min = min(ttft_list)
            ttft_max = max(ttft_list)
            ttft_last = ttft_list[-1]
        else:
            ttft_avg = ttft_min = ttft_max = ttft_last = 0.0

        # Calculo estatistico de Hidratacao
        if hyd_list:
            hyd_avg = statistics.mean(hyd_list)
            hyd_min = min(hyd_list)
            hyd_max = max(hyd_list)
            hyd_last = hyd_list[-1]
        else:
            hyd_avg = hyd_min = hyd_max = hyd_last = 0.0

        # Taxa de sucesso de acoes
        total_finished_actions = appr + roll
        if total_finished_actions > 0:
            success_rate_pct = round((appr / total_finished_actions) * 100.0, 2)
        else:
            success_rate_pct = 100.0 if req == 0 else 0.0

        return {
            "status": "ok",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "ttft_ms": {
                "avg": round(ttft_avg, 2),
                "min": round(ttft_min, 2),
                "max": round(ttft_max, 2),
                "last": round(ttft_last, 2),
                "count": len(ttft_list),
            },
            "hydration_ms": {
                "avg": round(hyd_avg, 2),
                "min": round(hyd_min, 2),
                "max": round(hyd_max, 2),
                "last": round(hyd_last, 2),
                "count": len(hyd_list),
            },
            "total_actions_requested": req,
            "total_actions_approved": appr,
            "total_actions_rolled_back": roll,
            "security_blocks": sec,
            "action_success_rate_pct": success_rate_pct,
            "feature_flags": get_feature_flags(),
        }
