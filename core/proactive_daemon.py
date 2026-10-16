"""
Motor de Alertas Proativos de Pista (Proactive Edge Daemon) - P3-2.
Vigia a pista e a retaguarda em segundo plano 24/7 com zero intervencao manual:
1. Monitor de criticidade de tanques: estoque e autonomia (< 24h ou < 20% vol) com sugestao de bocas de 5.000 L.
2. Monitor de sangrias e retencao de caixa: caixas com dinheiro > teto (R$ 1.500) sem sangria ha > 45 min.
3. Monitor de fechamento e conciliacao de turnos com notificacao executiva de fechamento.
4. Deduplicacao e Cooldown de Alertas persistente em memoria e SQLite local.
5. Despacho assincrono via Webhooks n8n e Evolution API (WhatsApp) para tanques, sangrias e turnos.
6. Historico persistente em SQLite local com paginacao e filtros (get_recent_alerts).
7. Integracao direta com eventos Change Data Capture (CDC) via handle_cdc_event.
8. Ciclo de avaliacao evaluate_rules() e loop em background start() / stop() resiliente e thread-safe.
Zero travessoes em todo o arquivo.
"""
# ruff: noqa: BLE001

from __future__ import annotations

import asyncio
import json
import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from config.settings import BASE_DIR
from core.logger import logger
from core.webhook_dispatcher import (
    AlertaSangriaPayload,
    AlertaTanquePayload,
    TurnoResumoPayload,
    notify_alerta_sangria,
    notify_alerta_tanque,
    notify_fechamento_turno,
)

DEFAULT_COOLDOWN_SECONDS: dict[str, float] = {
    "TANQUE_CRITICO": 7200.0,     # 2 horas de cooldown para o mesmo tanque
    "SANGRIA_PENDENTE": 2700.0,   # 45 minutos de cooldown para o mesmo caixa
    "FECHAMENTO_TURNO": 3600.0,   # 1 hora de cooldown para resumo de turno
}


def _format_brl(val: float) -> str:
    """Formata valor monetario em padrao brasileiro com virgula decimal."""
    s = f"{val:,.2f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def _format_litros(val: float) -> str:
    """Formata volume em litros no padrao brasileiro com ponto de milhar."""
    s = f"{val:,.0f}"
    return s.replace(",", ".")


@dataclass
class ProactiveAlert:
    """Entidade que representa um alerta proativo gerado pelo daemon."""

    alert_id: str
    alert_type: str
    filial_id: str
    entity_id: str
    severity: str
    title: str
    message: str
    suggested_action: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    dispatched: bool = False
    dispatch_results: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Converte a entidade para dicionario serializavel."""
        return asdict(self)


class AuraProactiveDaemon:
    """
    Daemon de Vigilancia e Alertas Proativos da AURA (P3-2).
    Opera em segundo plano de forma autonoma, thread-safe e resiliente.
    """

    def __init__(
        self,
        db_path: str | Path | None = None,
        filial_id: str = "posto_01",
        tenant_id: str = "default_tenant",
        tank_autonomy_threshold_hours: float = 24.0,
        tank_volume_pct_threshold: float = 0.20,
        cashier_max_cash_drawer: float = 1500.0,
        cashier_idle_bleed_minutes: int = 45,
        turno_max_quebra_caixa: float = 50.0,
        cooldown_seconds_by_type: dict[str, float] | None = None,
        evaluation_interval_seconds: float = 60.0,
        dispatch_enabled: bool = True,
        phone: str | None = None,
        webhook_url: str | None = None,
        erp_adapter: Any | None = None,
    ) -> None:
        self.filial_id = filial_id
        self.tenant_id = tenant_id
        self.tank_autonomy_threshold_hours = float(tank_autonomy_threshold_hours)
        self.tank_volume_pct_threshold = float(tank_volume_pct_threshold)
        self.cashier_max_cash_drawer = float(cashier_max_cash_drawer)
        self.cashier_idle_bleed_minutes = int(cashier_idle_bleed_minutes)
        self.turno_max_quebra_caixa = float(turno_max_quebra_caixa)
        self.cooldown_seconds_by_type = dict(cooldown_seconds_by_type or DEFAULT_COOLDOWN_SECONDS)
        self.evaluation_interval_seconds = float(evaluation_interval_seconds)
        self.dispatch_enabled = dispatch_enabled
        self.phone = phone
        self.webhook_url = webhook_url
        self.erp_adapter = erp_adapter

        # Sincronizacao de threads
        self._lock = threading.RLock()

        # Estado operacional
        self._running: bool = False
        self._task: asyncio.Task | None = None
        self._rules_evaluated_count: int = 0
        self._last_evaluation_timestamp: str | None = None
        self._active_alerts_count: int = 0
        self._last_error: str | None = None

        # Cache de cooldown em memoria: dedup_key -> timestamp float
        self._cooldown_cache: dict[str, float] = {}
        # Historico em memoria limitado aos ultimos 500 registros
        self._alerts_memory: list[dict[str, Any]] = []

        # Inicializacao do SQLite
        if db_path is None:
            data_dir = BASE_DIR / "data"
            data_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = str(data_dir / "aura_proactive_alerts.db")
            self._shared_conn: sqlite3.Connection | None = None
        elif str(db_path) == ":memory:":
            self.db_path = ":memory:"
            self._shared_conn = sqlite3.connect(":memory:", check_same_thread=False)
            self._shared_conn.row_factory = sqlite3.Row
        else:
            self.db_path = str(db_path)
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            self._shared_conn = None

        self._init_db()

    # =========================================================================
    # PERSISTENCIA SQLITE E CONEXAO
    # =========================================================================

    @contextmanager
    def _connection(self):
        """Context manager thread-safe para acesso ao SQLite local."""
        with self._lock:
            if self._shared_conn is not None:
                with self._shared_conn:
                    yield self._shared_conn
            else:
                conn = sqlite3.connect(self.db_path, timeout=15.0)
                conn.row_factory = sqlite3.Row
                try:
                    with conn:
                        yield conn
                finally:
                    conn.close()

    def _init_db(self) -> None:
        """Cria tabelas e indices no banco SQLite local."""
        with self._lock, self._connection() as conn:
            try:
                conn.execute("PRAGMA journal_mode = WAL;")
                conn.execute("PRAGMA synchronous = NORMAL;")
            except sqlite3.OperationalError:
                pass
            conn.execute("""
                CREATE TABLE IF NOT EXISTS aura_proactive_alerts (
                    alert_id TEXT PRIMARY KEY,
                    alert_type TEXT NOT NULL,
                    filial_id TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    suggested_action TEXT,
                    payload_json TEXT NOT NULL,
                    dispatched INTEGER NOT NULL,
                    dispatch_results_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_proactive_type 
                ON aura_proactive_alerts(alert_type);
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_proactive_filial 
                ON aura_proactive_alerts(filial_id);
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_proactive_created 
                ON aura_proactive_alerts(created_at);
            """)

    def _save_alert(self, alert: ProactiveAlert) -> None:
        """Salva alerta gerado no SQLite e no buffer rapido em memoria."""
        alert_dict = alert.to_dict()
        with self._lock:
            self._alerts_memory.insert(0, alert_dict)
            if len(self._alerts_memory) > 500:
                self._alerts_memory.pop()

        try:
            with self._connection() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO aura_proactive_alerts (
                        alert_id,
                        alert_type,
                        filial_id,
                        entity_id,
                        severity,
                        title,
                        message,
                        suggested_action,
                        payload_json,
                        dispatched,
                        dispatch_results_json,
                        created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        alert.alert_id,
                        alert.alert_type,
                        alert.filial_id,
                        alert.entity_id,
                        alert.severity,
                        alert.title,
                        alert.message,
                        alert.suggested_action,
                        json.dumps(alert.payload, ensure_ascii=False),
                        1 if alert.dispatched else 0,
                        json.dumps(alert.dispatch_results, ensure_ascii=False),
                        alert.created_at,
                    ),
                )
        except Exception as exc:
            logger.error(f"Erro ao salvar alerta proativo no SQLite: {exc}", exc_info=True)

    def get_recent_alerts(
        self,
        limit: int = 50,
        offset: int = 0,
        alert_type: str | None = None,
        severity: str | None = None,
        filial_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Recupera historico recente de alertas com suporte a paginacao e filtros."""
        limit = max(1, min(limit, 200))
        offset = max(0, offset)

        try:
            query = "SELECT * FROM aura_proactive_alerts WHERE 1=1"
            params: list[Any] = []
            if alert_type:
                query += " AND UPPER(alert_type) = ?"
                params.append(alert_type.upper().strip())
            if severity:
                query += " AND UPPER(severity) = ?"
                params.append(severity.upper().strip())
            if filial_id:
                query += " AND LOWER(filial_id) = ?"
                params.append(filial_id.lower().strip())

            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            with self._connection() as conn:
                rows = conn.execute(query, tuple(params)).fetchall()

            result: list[dict[str, Any]] = []
            for row in rows:
                p_json = row["payload_json"]
                d_json = row["dispatch_results_json"]
                try:
                    p_val = json.loads(p_json) if p_json else {}
                except Exception:
                    p_val = {}
                try:
                    d_val = json.loads(d_json) if d_json else {}
                except Exception:
                    d_val = {}

                result.append({
                    "alert_id": row["alert_id"],
                    "alert_type": row["alert_type"],
                    "filial_id": row["filial_id"],
                    "entity_id": row["entity_id"],
                    "severity": row["severity"],
                    "title": row["title"],
                    "message": row["message"],
                    "suggested_action": row["suggested_action"],
                    "payload": p_val,
                    "dispatched": bool(row["dispatched"]),
                    "dispatch_results": d_val,
                    "created_at": row["created_at"],
                })
            return result
        except Exception as exc:
            logger.warning(f"Fallback para memoria no get_recent_alerts: {exc}")
            with self._lock:
                filtered = list(self._alerts_memory)
            if alert_type:
                filtered = [a for a in filtered if a.get("alert_type") == alert_type.upper().strip()]
            if severity:
                filtered = [a for a in filtered if a.get("severity") == severity.upper().strip()]
            if filial_id:
                filtered = [a for a in filtered if a.get("filial_id") == filial_id.strip()]
            return filtered[offset : offset + limit]

    # =========================================================================
    # DEDUPLICACAO E COOLDOWN
    # =========================================================================

    def _build_dedup_key(self, alert_type: str, filial_id: str, entity_id: str) -> str:
        """Gera chave deterministica de coalescencia por tipo, filial e entidade."""
        return f"{alert_type.upper().strip()}:{filial_id.lower().strip()}:{str(entity_id).upper().strip()}"

    def _get_last_dispatch_timestamp_from_db(
        self,
        alert_type: str,
        entity_id: str,
        filial_id: str,
    ) -> float | None:
        """Busca no SQLite local a hora do ultimo alerta emitido nao suprimido."""
        try:
            with self._connection() as conn:
                rows = conn.execute(
                    """
                    SELECT created_at, dispatch_results_json FROM aura_proactive_alerts
                    WHERE UPPER(alert_type) = ? AND LOWER(filial_id) = ? AND UPPER(entity_id) = ?
                    ORDER BY created_at DESC LIMIT 5
                    """,
                    (alert_type.upper().strip(), filial_id.lower().strip(), entity_id.upper().strip()),
                ).fetchall()
                for r in rows:
                    d_json = r["dispatch_results_json"] or ""
                    if '"status": "cooldown_suppressed"' in d_json:
                        continue
                    ts_str = r["created_at"]
                    if ts_str:
                        dt = None
                        try:
                            dt = datetime.fromisoformat(ts_str)
                        except (ValueError, TypeError):
                            try:
                                dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
                            except (ValueError, TypeError) as exc:
                                logger.debug(f"Falha ao converter timestamp {ts_str}: {exc}")
                        if dt is not None:
                            return dt.timestamp()
        except Exception as exc:
            logger.debug(f"Falha ao consultar historico de cooldown no SQLite: {exc}")
        return None

    def is_in_cooldown(
        self,
        alert_type: str,
        entity_id: str,
        filial_id: str | None = None,
    ) -> bool:
        """Verifica se a entidade ainda esta em periodo de cooldown para o alerta."""
        effective_filial = filial_id or self.filial_id
        key = self._build_dedup_key(alert_type, effective_filial, entity_id)

        with self._lock:
            last_time = self._cooldown_cache.get(key)
            if last_time is None:
                # Consulta persistente no SQLite caso o processo tenha reiniciado
                last_time = self._get_last_dispatch_timestamp_from_db(
                    alert_type, str(entity_id), effective_filial
                )
                if last_time is not None:
                    self._cooldown_cache[key] = last_time

        if last_time is None:
            return False

        cooldown_sec = self.cooldown_seconds_by_type.get(
            alert_type.upper().strip(), 3600.0
        )
        elapsed = time.time() - last_time
        return elapsed < cooldown_sec

    def record_cooldown(
        self,
        alert_type: str,
        entity_id: str,
        filial_id: str | None = None,
        custom_time: float | None = None,
    ) -> None:
        """Registra novo disparo na tabela de cooldown em memoria."""
        key = self._build_dedup_key(alert_type, filial_id or self.filial_id, entity_id)
        with self._lock:
            self._cooldown_cache[key] = custom_time if custom_time is not None else time.time()

    def clear_cooldown(
        self,
        alert_type: str | None = None,
        entity_id: str | None = None,
    ) -> None:
        """Limpa todo o cache de cooldown ou itens especificos em memoria e no SQLite."""
        with self._lock:
            if alert_type is None and entity_id is None:
                self._cooldown_cache.clear()
            else:
                to_remove = []
                for k in self._cooldown_cache:
                    parts = k.split(":")
                    k_type = parts[0]
                    k_entity = parts[2] if len(parts) > 2 else ""
                    match_type = (alert_type is None) or (k_type == alert_type.upper().strip())
                    match_entity = (entity_id is None) or (k_entity == str(entity_id).upper().strip())
                    if match_type and match_entity:
                        to_remove.append(k)

                for k in to_remove:
                    self._cooldown_cache.pop(k, None)

            # Evita recarga imediata do banco marcando created_at no passado remoto
            try:
                with self._connection() as conn:
                    query = "UPDATE aura_proactive_alerts SET created_at = '2000-01-01T00:00:00' WHERE 1=1"
                    params: list[Any] = []
                    if alert_type:
                        query += " AND UPPER(alert_type) = ?"
                        params.append(alert_type.upper().strip())
                    if entity_id:
                        query += " AND UPPER(entity_id) = ?"
                        params.append(str(entity_id).upper().strip())
                    conn.execute(query, tuple(params))
            except Exception as exc:
                logger.debug(f"Erro ao limpar cooldown no SQLite: {exc}")

    # =========================================================================
    # REGRAS OPERACIONAIS
    # =========================================================================

    def evaluate_tank_rules(
        self,
        tanques: list[dict[str, Any] | Any] | None = None,
    ) -> list[ProactiveAlert]:
        """
        Avalia criticidade volumetrica e autonomia de tanques de combustivel.
        Dispara alerta se:
        - Autonomia estimada < tank_autonomy_threshold_hours (ex: 24h) OU
        - Volume atual < tank_volume_pct_threshold da capacidade nominal (ex: 20%).
        Calcula sugestao de pedido fracionado em compartimentos padrao de 5.000 L.
        """
        alerts: list[ProactiveAlert] = []
        tanques_data = tanques

        # Fallback para ERP adapter se nenhum dado for injetado
        if tanques_data is None and self.erp_adapter is not None:
            try:
                readings = self.erp_adapter.get_tank_inventory()
                tanques_data = [
                    {
                        "tanque_id": t.identificador_tanque,
                        "combustivel": t.combustivel or f"COMBUSTIVEL {t.identificador_tanque}",
                        "capacidade_total_litros": float(t.capacidade_nominal_litros),
                        "volume_atual_litros": float(t.volume_atual_litros),
                        "filial_id": self.filial_id,
                    }
                    for t in readings
                ]
            except Exception as exc:
                logger.error(f"Erro ao buscar inventario de tanques via ERP: {exc}")
                tanques_data = []

        if not tanques_data:
            return alerts

        for item in tanques_data:
            if hasattr(item, "model_dump"):
                d = item.model_dump()
            elif isinstance(item, dict):
                d = dict(item)
            else:
                d = getattr(item, "__dict__", {})

            tanque_id = str(d.get("tanque_id") or d.get("codtan") or d.get("id") or "0")
            combustivel = str(d.get("combustivel") or d.get("descricao") or "COMBUSTIVEL DIVERSO").strip()
            filial = str(d.get("filial_id") or self.filial_id).strip()

            cap = max(0.0, float(d.get("capacidade_total_litros") or d.get("capacidade_nominal_litros") or d.get("capacidade_litros") or 0.0))
            vol = max(0.0, float(d.get("volume_atual_litros") or d.get("volume_atual") or d.get("saldo_atual_litros") or 0.0))

            # Calculo de autonomia em horas
            auto_h: float | None = None
            if d.get("autonomia_horas") is not None:
                auto_h = max(0.0, float(d["autonomia_horas"]))
            elif d.get("autonomia_runout_horas") is not None:
                auto_h = max(0.0, float(d["autonomia_runout_horas"]))
            elif d.get("consumo_diario_litros") and float(d["consumo_diario_litros"]) > 0:
                consumo_dia = float(d["consumo_diario_litros"])
                auto_h = round(vol / (consumo_dia / 24.0), 1)
            elif d.get("consumo_horario_litros") and float(d["consumo_horario_litros"]) > 0:
                consumo_hora = float(d["consumo_horario_litros"])
                auto_h = round(vol / consumo_hora, 1)

            pct_volume = (vol / cap) if cap > 0.0 else 0.0

            # Criterios de gatilho
            trigger_autonomia = (auto_h is not None) and (auto_h < self.tank_autonomy_threshold_hours)
            trigger_volume = (cap > 0.0) and (pct_volume < self.tank_volume_pct_threshold)

            if trigger_autonomia or trigger_volume:
                # Calculo de ullage e sugestao de carretas em bocas de 5.000 L
                ullage = max(0.0, cap - vol)
                compartimentos_5k = int(ullage // 5000.0) if cap > 0.0 else 0
                vol_sugerido = float(compartimentos_5k * 5000.0)

                # Definicao de severidade
                is_extreme = (auto_h is not None and auto_h < 12.0) or (pct_volume < 0.10)
                severity = "CRITICAL" if is_extreme else "HIGH"
                urgencia = "CRITICA" if is_extreme else "ALTA"

                if compartimentos_5k > 0:
                    sugestao = (
                        f"Autorizar pedido fracionado de {compartimentos_5k} compartimento(s) "
                        f"de 5.000 L ({_format_litros(vol_sugerido)} L)."
                    )
                else:
                    sugestao = "Espaco livre insuficiente para boca de 5.000 L. Monitorar de perto."

                auto_label = f"{auto_h:.1f}h" if auto_h is not None else "N/D"
                title = f"Ruptura Critica: Tanque {tanque_id} ({combustivel})"
                message = (
                    f"Tanque {tanque_id} ({combustivel}): saldo {_format_litros(vol)} L / {_format_litros(cap)} L "
                    f"({pct_volume * 100:.1f}%), autonomia estimada de {auto_label}. {sugestao}"
                )

                if auto_h is not None and auto_h == 0.0:
                    previsao_esgotamento = "Esgotado / Imediata"
                elif auto_h is not None and auto_h < 999.0:
                    prev_dt = datetime.now(UTC) + timedelta(hours=auto_h)
                    previsao_esgotamento = prev_dt.strftime("%d/%m/%Y %H:%M UTC")
                else:
                    previsao_esgotamento = "Indeterminada (sem taxa horaria)"

                alert = ProactiveAlert(
                    alert_id=str(uuid.uuid4()),
                    alert_type="TANQUE_CRITICO",
                    filial_id=filial,
                    entity_id=tanque_id,
                    severity=severity,
                    title=title,
                    message=message,
                    suggested_action=sugestao,
                    payload={
                        "tanque_id": tanque_id,
                        "combustivel": combustivel,
                        "volume_atual_litros": vol,
                        "capacidade_total_litros": cap,
                        "ocupacao_pct": round(pct_volume * 100, 2),
                        "autonomia_horas": auto_h if auto_h is not None else 0.0,
                        "previsao_esgotamento": previsao_esgotamento,
                        "urgencia": urgencia,
                        "espaco_livre_ullage_litros": round(ullage, 2),
                        "compartimentos_5k": compartimentos_5k,
                        "volume_sugerido_litros": vol_sugerido,
                    },
                )
                alerts.append(alert)

        return alerts

    def evaluate_cashier_rules(
        self,
        caixas: list[dict[str, Any] | Any] | None = None,
    ) -> list[ProactiveAlert]:
        """
        Avalia caixas abertos e retencao excessiva de numerario em gaveta.
        Dispara alerta se:
        - Saldo em dinheiro > cashier_max_cash_drawer (ex: R$ 1.500) E
        - Tempo sem sangria > cashier_idle_bleed_minutes (ex: 45 min).
        """
        alerts: list[ProactiveAlert] = []
        caixas_data = caixas

        if not caixas_data:
            return alerts

        for item in caixas_data:
            if hasattr(item, "model_dump"):
                d = item.model_dump()
            elif isinstance(item, dict):
                d = dict(item)
            else:
                d = getattr(item, "__dict__", {})

            caixa_id = str(d.get("caixa_id") or d.get("pdv_id") or d.get("terminal_id") or "0")
            filial = str(d.get("filial_id") or self.filial_id).strip()
            saldo_dinh = max(0.0, float(d.get("saldo_dinheiro") or d.get("cash_in_drawer") or d.get("valor_em_especie") or 0.0))
            minutos = max(0, int(d.get("minutos_sem_sangria") or d.get("tempo_sem_sangria_minutos") or 0))
            teto = max(0.0, float(d.get("teto_tolerancia") or self.cashier_max_cash_drawer))
            operador = d.get("operador_id") or d.get("operador")

            if saldo_dinh > teto and minutos > self.cashier_idle_bleed_minutes:
                excesso = round(saldo_dinh - teto, 2)
                severity = "CRITICAL" if excesso > 1000.0 or minutos > 90 else "HIGH"
                urgencia = "CRITICA" if severity == "CRITICAL" else "ALTA"

                sugestao = f"Forcar sangria imediata de no minimo R$ {_format_brl(excesso)} para o cofre seguro de retaguarda."
                title = f"Sangria Pendente: Caixa {caixa_id} (R$ {_format_brl(saldo_dinh)})"
                message = (
                    f"Caixa {caixa_id} acumula R$ {_format_brl(saldo_dinh)} em especie ha {minutos} min sem sangria "
                    f"(excesso de R$ {_format_brl(excesso)} acima do teto de R$ {_format_brl(teto)}). {sugestao}"
                )

                alert = ProactiveAlert(
                    alert_id=str(uuid.uuid4()),
                    alert_type="SANGRIA_PENDENTE",
                    filial_id=filial,
                    entity_id=caixa_id,
                    severity=severity,
                    title=title,
                    message=message,
                    suggested_action=sugestao,
                    payload={
                        "caixa_id": caixa_id,
                        "saldo_dinheiro": saldo_dinh,
                        "teto_seguro": teto,
                        "excesso_dinheiro": excesso,
                        "minutos_sem_sangria": minutos,
                        "urgencia": urgencia,
                        "operador_id": operador,
                    },
                )
                alerts.append(alert)

        return alerts

    def evaluate_turn_rules(
        self,
        turnos: list[dict[str, Any] | Any] | None = None,
    ) -> list[ProactiveAlert]:
        """
        Avalia fechamento e conciliacao de turnos operacionais.
        Dispara alerta se:
        - Status da conciliacao for ALERTA OU
        - Diferenca ou quebra de caixa for superior a turno_max_quebra_caixa (ex: R$ 50,00) OU
        - Turno consolidado com flag de fechamento/notificacao for enviado.
        """
        alerts: list[ProactiveAlert] = []
        turnos_data = turnos

        if not turnos_data:
            return alerts

        for item in turnos_data:
            if hasattr(item, "model_dump"):
                d = item.model_dump()
            elif isinstance(item, dict):
                d = dict(item)
            else:
                d = getattr(item, "__dict__", {})

            turno_id = str(d.get("turno_id") or d.get("id") or d.get("identificador") or "TURNO-01").strip()
            filial = str(d.get("filial_id") or self.filial_id).strip()
            fat_total = float(d.get("faturamento_total") or d.get("faturamento") or 0.0)
            litros = float(d.get("litros_vendidos") or d.get("volume_litros") or 0.0)
            quebra = float(d.get("quebra_caixa") or 0.0)
            status_conc = str(d.get("status_conciliacao") or "CONCILIADO").strip().upper()
            bicos = int(d.get("bicos_analisados") or 0)
            obs = d.get("observacoes") or d.get("obs")
            data_str = str(d.get("data") or datetime.now(UTC).strftime("%Y-%m-%d"))

            trigger_alerta = status_conc == "ALERTA"
            trigger_quebra = abs(quebra) > self.turno_max_quebra_caixa
            trigger_fechado = bool(d.get("fechado") or d.get("forcar_despacho"))

            if trigger_alerta or trigger_quebra or trigger_fechado:
                is_severe = trigger_alerta or abs(quebra) > 200.0
                severity = "CRITICAL" if is_severe else "HIGH"
                urgencia = "CRITICA" if is_severe else "ALTA"

                if abs(quebra) > 0.0:
                    sugestao = f"Auditar gaveta e sangrias do turno {turno_id} devido a diferenca de R$ {_format_brl(abs(quebra))}."
                else:
                    sugestao = f"Homologar fechamento do turno {turno_id} no painel de retaguarda."

                title = f"Fechamento de Turno: {turno_id} ({status_conc})"
                message = (
                    f"Turno {turno_id} (Filial {filial}): Faturamento R$ {_format_brl(fat_total)}, "
                    f"{_format_litros(litros)} L vendidos, quebra de caixa R$ {_format_brl(quebra)} ({status_conc}). {sugestao}"
                )

                alert = ProactiveAlert(
                    alert_id=str(uuid.uuid4()),
                    alert_type="FECHAMENTO_TURNO",
                    filial_id=filial,
                    entity_id=turno_id,
                    severity=severity,
                    title=title,
                    message=message,
                    suggested_action=sugestao,
                    payload={
                        "turno_id": turno_id,
                        "filial_id": filial,
                        "data": data_str,
                        "faturamento_total": fat_total,
                        "litros_vendidos": litros,
                        "quebra_caixa": quebra,
                        "status_conciliacao": status_conc,
                        "bicos_analisados": bicos,
                        "observacoes": obs,
                        "urgencia": urgencia,
                    },
                )
                alerts.append(alert)

        return alerts

    # =========================================================================
    # CICLO PRINCIPAL DE AVALIACAO E DESPACHO
    # =========================================================================

    async def evaluate_rules(
        self,
        tanques: list[dict[str, Any] | Any] | None = None,
        caixas: list[dict[str, Any] | Any] | None = None,
        turnos: list[dict[str, Any] | Any] | None = None,
        force: bool = False,
    ) -> list[ProactiveAlert]:
        """
        Executa uma rodada completa de avaliacao de regras analiticas.
        Aplica filtro de cooldown para evitar spam e despacha alertas novos.
        """
        with self._lock:
            self._last_evaluation_timestamp = datetime.now(UTC).isoformat()
            self._rules_evaluated_count += 3

        generated_alerts: list[ProactiveAlert] = []

        try:
            # 1. Regra de tanques
            tank_alerts = self.evaluate_tank_rules(tanques=tanques)
            for alert in tank_alerts:
                in_cooldown = self.is_in_cooldown(alert.alert_type, alert.entity_id, alert.filial_id)
                if not force and in_cooldown:
                    alert.dispatched = False
                    alert.dispatch_results = {
                        "status": "cooldown_suppressed",
                        "reason": f"Alerta recente para tanque {alert.entity_id} em cooldown.",
                    }
                    logger.debug(
                        f"Alerta {alert.alert_type} para {alert.entity_id} suprimido por cooldown."
                    )
                else:
                    if self.dispatch_enabled:
                        payload = AlertaTanquePayload(
                            tanque_id=alert.entity_id,
                            combustivel=alert.payload.get("combustivel", "COMBUSTIVEL"),
                            filial_id=alert.filial_id,
                            volume_atual_litros=alert.payload.get("volume_atual_litros", 0.0),
                            capacidade_total_litros=alert.payload.get("capacidade_total_litros", 0.0),
                            autonomia_horas=alert.payload.get("autonomia_horas", 0.0),
                            previsao_esgotamento=alert.payload.get("previsao_esgotamento", ""),
                            urgencia=alert.payload.get("urgencia", "ALTA"),
                            compartimentos_5k=alert.payload.get("compartimentos_5k"),
                            volume_sugerido_litros=alert.payload.get("volume_sugerido_litros"),
                        )
                        res = await notify_alerta_tanque(
                            payload=payload,
                            phone=self.phone,
                            webhook_url=self.webhook_url,
                        )
                        alert.dispatched = True
                        alert.dispatch_results = res
                    else:
                        alert.dispatched = False
                        alert.dispatch_results = {"status": "dispatch_disabled"}

                    self.record_cooldown(alert.alert_type, alert.entity_id, alert.filial_id)

                self._save_alert(alert)
                generated_alerts.append(alert)

            # 2. Regra de sangrias de caixa
            cashier_alerts = self.evaluate_cashier_rules(caixas=caixas)
            for alert in cashier_alerts:
                in_cooldown = self.is_in_cooldown(alert.alert_type, alert.entity_id, alert.filial_id)
                if not force and in_cooldown:
                    alert.dispatched = False
                    alert.dispatch_results = {
                        "status": "cooldown_suppressed",
                        "reason": f"Alerta recente para caixa {alert.entity_id} em cooldown.",
                    }
                    logger.debug(
                        f"Alerta {alert.alert_type} para {alert.entity_id} suprimido por cooldown."
                    )
                else:
                    if self.dispatch_enabled:
                        payload_caixa = AlertaSangriaPayload(
                            caixa_id=alert.entity_id,
                            filial_id=alert.filial_id,
                            saldo_dinheiro=alert.payload.get("saldo_dinheiro", 0.0),
                            teto_seguro=alert.payload.get("teto_seguro", 0.0),
                            excesso_dinheiro=alert.payload.get("excesso_dinheiro", 0.0),
                            minutos_sem_sangria=alert.payload.get("minutos_sem_sangria", 0),
                            urgencia=alert.payload.get("urgencia", "ALTA"),
                            operador_id=alert.payload.get("operador_id"),
                        )
                        res = await notify_alerta_sangria(
                            payload=payload_caixa,
                            phone=self.phone,
                            webhook_url=self.webhook_url,
                        )
                        alert.dispatched = True
                        alert.dispatch_results = res
                    else:
                        alert.dispatched = False
                        alert.dispatch_results = {"status": "dispatch_disabled"}

                    self.record_cooldown(alert.alert_type, alert.entity_id, alert.filial_id)

                self._save_alert(alert)
                generated_alerts.append(alert)

            # 3. Regra de fechamento de turno
            turn_alerts = self.evaluate_turn_rules(turnos=turnos)
            for alert in turn_alerts:
                in_cooldown = self.is_in_cooldown(alert.alert_type, alert.entity_id, alert.filial_id)
                if not force and in_cooldown:
                    alert.dispatched = False
                    alert.dispatch_results = {
                        "status": "cooldown_suppressed",
                        "reason": f"Alerta recente para turno {alert.entity_id} em cooldown.",
                    }
                    logger.debug(
                        f"Alerta {alert.alert_type} para {alert.entity_id} suprimido por cooldown."
                    )
                else:
                    if self.dispatch_enabled:
                        payload_turno = TurnoResumoPayload(
                            turno_id=alert.entity_id,
                            filial_id=alert.filial_id,
                            data=alert.payload.get("data", datetime.now(UTC).strftime("%Y-%m-%d")),
                            faturamento_total=alert.payload.get("faturamento_total", 0.0),
                            litros_vendidos=alert.payload.get("litros_vendidos", 0.0),
                            quebra_caixa=alert.payload.get("quebra_caixa", 0.0),
                            status_conciliacao=alert.payload.get("status_conciliacao", "CONCILIADO"),
                            bicos_analisados=alert.payload.get("bicos_analisados", 0),
                            observacoes=alert.payload.get("observacoes"),
                        )
                        res = await notify_fechamento_turno(
                            payload=payload_turno,
                            phone=self.phone,
                            webhook_url=self.webhook_url,
                        )
                        alert.dispatched = True
                        alert.dispatch_results = res
                    else:
                        alert.dispatched = False
                        alert.dispatch_results = {"status": "dispatch_disabled"}

                    self.record_cooldown(alert.alert_type, alert.entity_id, alert.filial_id)

                self._save_alert(alert)
                generated_alerts.append(alert)

            with self._lock:
                self._active_alerts_count = sum(
                    1 for a in generated_alerts if a.severity in ("HIGH", "CRITICAL")
                )
                self._last_error = None
        except Exception as exc:
            with self._lock:
                self._last_error = str(exc)
            logger.error(f"Erro ao avaliar regras no AuraProactiveDaemon: {exc}", exc_info=True)

        return generated_alerts

    async def handle_cdc_event(self, event: Any) -> list[ProactiveAlert]:
        """
        Processa mutacao de CDC (PostgreSQL NOTIFY) e dispara avaliacao imediata correspondente.
        Compativel com CDCEvent de core/cdc_listener.py ou dicionarios brutos.
        """
        table = ""
        payload: dict[str, Any] = {}
        if hasattr(event, "table"):
            table = str(event.table).strip().lower()
            payload = getattr(event, "raw_payload", {}) or {}
        elif isinstance(event, dict):
            table = str(event.get("table") or "").strip().lower()
            payload = event.get("payload") or event

        if table in ("tanques", "estoque", "leitura_tanques"):
            return await self.evaluate_rules(tanques=[payload] if payload else None)
        elif table in ("caixas", "sangrias", "movimento_caixa"):
            return await self.evaluate_rules(caixas=[payload] if payload else None)
        elif table in ("turnos", "fechamento_turno", "dre"):
            return await self.evaluate_rules(turnos=[payload] if payload else None)
        else:
            return await self.evaluate_rules()

    # =========================================================================
    # LOOP EM BACKGROUND E CICLO DE VIDA THREAD-SAFE
    # =========================================================================

    async def start(self) -> None:
        """Inicia a execucao continua do daemon em background de forma thread-safe."""
        with self._lock:
            if self._running:
                return
            self._running = True
            self._task = asyncio.create_task(self._run_loop())
            logger.info("AuraProactiveDaemon iniciado com sucesso em background.")

    async def stop(self) -> None:
        """Para graciosamente a execucao do daemon de forma thread-safe."""
        task_to_cancel = None
        with self._lock:
            if not self._running and (self._task is None or self._task.done()):
                return
            self._running = False
            if self._task and not self._task.done():
                task_to_cancel = self._task
                self._task = None

        if task_to_cancel:
            task_to_cancel.cancel()
            try:
                await task_to_cancel
            except asyncio.CancelledError:
                pass
        logger.info("AuraProactiveDaemon parado com sucesso.")

    async def _run_loop(self) -> None:
        """Loop resiliente de avaliacao periodica."""
        while self._running:
            try:
                await self.evaluate_rules()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                with self._lock:
                    self._last_error = str(exc)
                logger.error(f"Excecao no ciclo do daemon proativo: {exc}", exc_info=True)

            try:
                await asyncio.sleep(self.evaluation_interval_seconds)
            except asyncio.CancelledError:
                break

    def get_status(self) -> dict[str, Any]:
        """Retorna o estado operacional corrente do daemon proativo."""
        with self._lock:
            return {
                "active": self._running,
                "rules_evaluated_count": self._rules_evaluated_count,
                "last_evaluation_timestamp": self._last_evaluation_timestamp,
                "active_alerts_count": self._active_alerts_count,
                "cooldown_cache_size": len(self._cooldown_cache),
                "evaluation_interval_seconds": self.evaluation_interval_seconds,
                "filial_id": self.filial_id,
                "status": "healthy" if (self._last_error is None) else "degraded",
                "last_error": self._last_error,
            }
