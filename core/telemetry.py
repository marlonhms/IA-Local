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


def calculate_percentile(data: List[float], percentile: float) -> float:
    """
    Calcula percentil com interpolacao linear deterministica.
    Suporta P50, P90, P95, P99 e listas de qualquer tamanho.
    Zero travessoes no docstring.
    """
    if not data:
        return 0.0
    sorted_data = sorted(data)
    n = len(sorted_data)
    if n == 1:
        return float(sorted_data[0])
    k = (n - 1) * (percentile / 100.0)
    f = int(k)
    c = min(f + 1, n - 1)
    d = k - f
    return float(sorted_data[f] + d * (sorted_data[c] - sorted_data[f]))


class AuraSRETelemetry:
    """
    Coletor central de telemetria SRE em memoria com suporte a persistencia duravel.
    Mapeia os SLIs de desempenho percebido, confiabilidade transacional e seguranca.
    """

    _instance: Optional[AuraSRETelemetry] = None
    _instance_lock = threading.RLock()

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

        with AuraSRETelemetry._instance_lock:
            if AuraSRETelemetry._instance is None:
                AuraSRETelemetry._instance = self

        if self.session_memory is not None:
            self.load_persisted_metrics()

    @classmethod
    def set_instance(cls, instance: AuraSRETelemetry) -> None:
        """Define explicitamente a instancia singleton ativa."""
        with cls._instance_lock:
            cls._instance = instance

    @classmethod
    def get_instance(cls, session_memory=None) -> AuraSRETelemetry:
        """Retorna a instancia singleton do coletor de telemetria."""
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls(session_memory=session_memory)
            elif session_memory is not None and cls._instance.session_memory is None:
                cls._instance.session_memory = session_memory
                cls._instance.load_persisted_metrics()
            return cls._instance

    def load_persisted_metrics(self) -> None:
        """
        Carrega agregacoes e amostras recentes salvas no SQLite para memoria.
        Garante persistencia e durabilidade mesmo apos reinicio do servidor.
        """
        if not self.session_memory:
            return

        try:
            if hasattr(self.session_memory, "get_telemetry_metric_counts"):
                counts = self.session_memory.get_telemetry_metric_counts()
                with self._lock:
                    if "action_requested" in counts:
                        self._total_actions_requested = counts["action_requested"]
                    if "action_approved" in counts:
                        self._total_actions_approved = counts["action_approved"]
                    if "action_rolled_back" in counts:
                        self._total_actions_rolled_back = counts["action_rolled_back"]
                    if "security_block" in counts:
                        self._security_blocks = counts["security_block"]

            if hasattr(self.session_memory, "get_telemetry_metrics_records"):
                recent_ttft = self.session_memory.get_telemetry_metrics_records(metric_type="ttft_ms", limit=self.max_samples)
                recent_hyd = self.session_memory.get_telemetry_metrics_records(metric_type="hydration_ms", limit=self.max_samples)

                with self._lock:
                    if recent_ttft:
                        self._ttft_samples.clear()
                        for r in reversed(recent_ttft):
                            self._ttft_samples.append(float(r["metric_value"]))
                    if recent_hyd:
                        self._hydration_samples.clear()
                        for r in reversed(recent_hyd):
                            self._hydration_samples.append(float(r["metric_value"]))
        except Exception:
            pass

    def reset(self, clear_db: bool = False) -> None:
        """Reinicia os contadores e amostras em memoria (util para suites de teste)."""
        with self._lock:
            self._ttft_samples.clear()
            self._hydration_samples.clear()
            self._total_actions_requested = 0
            self._total_actions_approved = 0
            self._total_actions_rolled_back = 0
            self._security_blocks = 0

        if clear_db and self.session_memory is not None and hasattr(self.session_memory, "clear_telemetry"):
            try:
                self.session_memory.clear_telemetry()
            except Exception:
                pass

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
        Trata hidratacao, TTFT percebido, rollbacks, aprovacoes e bloqueios de seguranca.
        """
        if not isinstance(report, dict):
            return {"status": "ignored", "reason": "invalid_payload"}

        session_id = report.get("session_id")
        tool_call_id = report.get("tool_call_id")
        action_id = report.get("action_id")
        details = report.get("details") or {}
        m_type = str(report.get("metric_type") or "").strip().lower()
        m_val = report.get("metric_value")

        # 1. Hidratacao reportada pelo cliente
        h_ms = report.get("hydration_ms")
        if h_ms is None and m_type in ("hydration", "hydration_ms") and m_val is not None:
            h_ms = m_val
        if h_ms is not None:
            try:
                self.record_hydration(
                    ms=float(h_ms),
                    session_id=session_id,
                    tool_call_id=tool_call_id,
                    details={"source": "client", **details},
                )
            except (ValueError, TypeError):
                pass

        # 2. TTFT percebido no cliente
        t_ms = report.get("ttft_ms")
        if t_ms is None and m_type in ("ttft", "ttft_ms") and m_val is not None:
            t_ms = m_val
        if t_ms is not None:
            try:
                self.record_ttft(ms=float(t_ms), session_id=session_id)
            except (ValueError, TypeError):
                pass

        # 3. Rollback de acao ocorrido no frontend
        is_rollback = bool(
            report.get("is_rollback") or
            report.get("action_status") == "rolled_back" or
            m_type == "action_rolled_back"
        )
        if is_rollback:
            self.record_action_rolled_back(
                action_id=action_id,
                session_id=session_id,
                reason=report.get("reason") or details.get("reason"),
            )

        # 4. Acao aprovada reportada
        is_approved = bool(
            report.get("action_status") == "approved" or
            m_type == "action_approved"
        )
        if is_approved:
            self.record_action_approved(action_id=action_id, session_id=session_id)

        # 5. Acao solicitada reportada
        is_requested = bool(
            report.get("action_status") == "requested" or
            m_type == "action_requested"
        )
        if is_requested:
            self.record_action_requested(action_id=action_id, session_id=session_id)

        # 6. Bloqueio de seguranca detectado no cliente
        is_sec_block = bool(
            report.get("is_security_block") or
            m_type in ("security_block", "security_blocks")
        )
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
        Inclui percentis estatisticos P50, P90, P95 e P99 para latencias.
        """
        with self._lock:
            ttft_list = list(self._ttft_samples)
            hyd_list = list(self._hydration_samples)
            req = self._total_actions_requested
            appr = self._total_actions_approved
            roll = self._total_actions_rolled_back
            sec = self._security_blocks

        # Calculo estatistico de TTFT (incluindo percentis SRE)
        if ttft_list:
            ttft_avg = statistics.mean(ttft_list)
            ttft_min = min(ttft_list)
            ttft_max = max(ttft_list)
            ttft_last = ttft_list[-1]
            ttft_p50 = calculate_percentile(ttft_list, 50.0)
            ttft_p90 = calculate_percentile(ttft_list, 90.0)
            ttft_p95 = calculate_percentile(ttft_list, 95.0)
            ttft_p99 = calculate_percentile(ttft_list, 99.0)
        else:
            ttft_avg = ttft_min = ttft_max = ttft_last = 0.0
            ttft_p50 = ttft_p90 = ttft_p95 = ttft_p99 = 0.0

        # Calculo estatistico de Hidratacao (incluindo percentis SRE)
        if hyd_list:
            hyd_avg = statistics.mean(hyd_list)
            hyd_min = min(hyd_list)
            hyd_max = max(hyd_list)
            hyd_last = hyd_list[-1]
            hyd_p50 = calculate_percentile(hyd_list, 50.0)
            hyd_p90 = calculate_percentile(hyd_list, 90.0)
            hyd_p95 = calculate_percentile(hyd_list, 95.0)
            hyd_p99 = calculate_percentile(hyd_list, 99.0)
        else:
            hyd_avg = hyd_min = hyd_max = hyd_last = 0.0
            hyd_p50 = hyd_p90 = hyd_p95 = hyd_p99 = 0.0

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
                "p50": round(ttft_p50, 2),
                "p90": round(ttft_p90, 2),
                "p95": round(ttft_p95, 2),
                "p99": round(ttft_p99, 2),
                "last": round(ttft_last, 2),
                "count": len(ttft_list),
            },
            "hydration_ms": {
                "avg": round(hyd_avg, 2),
                "min": round(hyd_min, 2),
                "max": round(hyd_max, 2),
                "p50": round(hyd_p50, 2),
                "p90": round(hyd_p90, 2),
                "p95": round(hyd_p95, 2),
                "p99": round(hyd_p99, 2),
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
