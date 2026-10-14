"""
Gerenciador de Configuracoes de Automacao e Monitoramento Configuravel da AURA.
Permite ativar/desativar em tempo real rotinas de monitoramento de turnos,
alertas de tanques e auditorias de pista, com persistencia local em JSON.
Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from core.logger import logger

# Caminho padrao do arquivo de configuracoes persistentes
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "automation_settings.json"


class ShiftAuditConfig(BaseModel):
    """Configuracao de auditoria automatica de fechamento de turnos."""
    enabled: bool = Field(default=False, description="Ativar auditoria automatica nos fechamentos")
    schedules: list[str] = Field(
        default_factory=lambda: ["06:05", "14:05", "22:05"],
        description="Horarios programados para auditoria dos turnos (HH:MM)",
    )
    notify_cash_divergence: bool = Field(
        default=True, description="Notificar quando houver diferenca no fechamento do caixa"
    )
    cash_tolerance_reais: float = Field(
        default=50.0, description="Tolerancia maxima de diferenca de caixa em R$ antes de emitir alerta"
    )


class TankAlertConfig(BaseModel):
    """Configuracao de alertas de autonomia e nivel critico de tanques."""
    enabled: bool = Field(default=False, description="Ativar alertas de risco de ruptura de combustivel")
    min_autonomy_hours: int = Field(
        default=12, description="Alerta quando a autonomia estimada for menor que este valor em horas"
    )
    min_volume_percentage: float = Field(
        default=15.0, description="Alerta quando o volume restante for menor que este percentual da capacidade"
    )
    check_interval_minutes: int = Field(
        default=60, description="Intervalo entre verificacoes automaticas de tanques em minutos"
    )


class PumpsAuditConfig(BaseModel):
    """Configuracao de auditoria de bicos e telemetria Companytec CBC04."""
    enabled: bool = Field(default=False, description="Ativar auditoria automatica de pista e bicos")
    alert_slow_flow: bool = Field(
        default=True, description="Alertar quando bicos apresentarem vazao lenta (< 25 L/min)"
    )
    alert_encerrante_divergence: bool = Field(
        default=True, description="Alertar divergencias entre encerrantes da automacao e ERP"
    )


class NotificationChannelsConfig(BaseModel):
    """Configuracao dos canais de saida de notificacoes."""
    web_banner: bool = Field(default=True, description="Exibir alertas visuais no cockpit da AURA")
    webhook_enabled: bool = Field(default=False, description="Encaminhar alertas para webhook externo")
    webhook_url: str = Field(default="", description="URL de destino para disparo de webhooks")


class AutomationSettings(BaseModel):
    """Contrato mestre de configuracoes de automacao e monitoramento."""
    master_enabled: bool = Field(
        default=False,
        description="Interruptor mestre: quando False, nenhuma rotina em background e executada (100% sob demanda)",
    )
    shift_audit: ShiftAuditConfig = Field(default_factory=ShiftAuditConfig)
    tank_alerts: TankAlertConfig = Field(default_factory=TankAlertConfig)
    pumps_audit: PumpsAuditConfig = Field(default_factory=PumpsAuditConfig)
    notifications: NotificationChannelsConfig = Field(default_factory=NotificationChannelsConfig)
    updated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_by: str = Field(default="gestor", description="Identificacao de quem realizou a ultima alteracao")


class AutomationSettingsManager:
    """
    Gerenciador thread-safe de configuracoes de automacao da AURA.
    Garante persistencia atomica em arquivo JSON e sincronizacao no runtime.
    """

    def __init__(self, file_path: Path | str | None = None):
        self.file_path = Path(file_path) if file_path else DEFAULT_CONFIG_PATH
        self._lock = threading.Lock()
        self._cached_settings: AutomationSettings | None = None
        self._init_storage()

    def _init_storage(self) -> None:
        """Inicializa o arquivo de configuracao caso nao exista."""
        with self._lock:
            if not self.file_path.exists():
                self.file_path.parent.mkdir(parents=True, exist_ok=True)
                default_settings = AutomationSettings(
                    master_enabled=False,
                    updated_at=datetime.now(UTC).isoformat(),
                    updated_by="sistema_inicializacao",
                )
                self._save_to_disk_locked(default_settings)
                self._cached_settings = default_settings
            else:
                try:
                    data = json.loads(self.file_path.read_text(encoding="utf-8"))
                    self._cached_settings = AutomationSettings(**data)
                except (json.JSONDecodeError, OSError, ValueError) as exc:
                    logger.error(f"Erro ao carregar configuracoes de automacao de {self.file_path}: {exc}")
                    self._cached_settings = AutomationSettings(master_enabled=False)

    def _save_to_disk_locked(self, settings: AutomationSettings) -> None:
        """Salva as configuracoes no disco de forma atomica (escreve em arquivo temp e renomeia)."""
        settings_dict = settings.model_dump()
        target_dir = self.file_path.parent
        target_dir.mkdir(parents=True, exist_ok=True)

        # Gravacao atomica segura
        with tempfile.NamedTemporaryFile("w", dir=target_dir, delete=False, encoding="utf-8") as tf:
            json.dump(settings_dict, tf, indent=2, ensure_ascii=False)
            temp_name = tf.name

        os.replace(temp_name, self.file_path)

    def get_settings(self) -> AutomationSettings:
        """Retorna uma copia das configuracoes ativas."""
        with self._lock:
            if self._cached_settings is None:
                self._init_storage()
            return self._cached_settings.model_copy(deep=True)

    def update_settings(
        self, updates: dict[str, Any] | AutomationSettings, updated_by: str = "gestor"
    ) -> AutomationSettings:
        """
        Atualiza as configuracoes com validacao parcial ou total.
        Persiste no disco e sincroniza com o runtime da aplicacao.
        """
        with self._lock:
            current_dict = (
                self._cached_settings.model_dump()
                if self._cached_settings
                else AutomationSettings().model_dump()
            )

            if isinstance(updates, AutomationSettings):
                new_dict = updates.model_dump()
            elif isinstance(updates, dict):
                new_dict = self._deep_merge(current_dict, updates)
            else:
                raise TypeError("Payload de atualizacao invalido")

            new_dict["updated_at"] = datetime.now(UTC).isoformat()
            new_dict["updated_by"] = updated_by

            validated = AutomationSettings(**new_dict)
            self._save_to_disk_locked(validated)
            self._cached_settings = validated

            # Sincroniza Feature Flag global de automacao se aplicavel
            try:
                from core.config import update_feature_flags
                update_feature_flags({
                    "ENABLE_AUTOMATED_MONITORING": validated.master_enabled,
                    "ENABLE_SHIFT_AUDIT": validated.shift_audit.enabled and validated.master_enabled,
                    "ENABLE_TANK_ALERTS": validated.tank_alerts.enabled and validated.master_enabled,
                })
            except Exception as e:
                logger.warning(f"Nao foi possivel sincronizar feature flags globais: {e}")

            logger.info(
                f"Configuracoes de automacao atualizadas por '{updated_by}'. Master: {validated.master_enabled}"
            )
            return validated.model_copy(deep=True)

    def _deep_merge(self, base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
        """Mescla dicionarios aninhados preservando valores nao especificados."""
        merged = dict(base)
        for key, value in patch.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = self._deep_merge(merged[key], value)
            else:
                merged[key] = value
        return merged

    def is_monitoring_active(self) -> bool:
        """Retorna True se o monitoramento mestre estiver ativado."""
        with self._lock:
            if self._cached_settings is None:
                return False
            return bool(self._cached_settings.master_enabled)


# Instancia singleton global do gerenciador
automation_manager = AutomationSettingsManager()


def get_automation_settings() -> AutomationSettings:
    """Funcao utilitaria para obter as configuracoes atuais."""
    return automation_manager.get_settings()


def update_automation_settings(
    updates: dict[str, Any] | AutomationSettings, updated_by: str = "gestor"
) -> AutomationSettings:
    """Funcao utilitaria para atualizar as configuracoes."""
    return automation_manager.update_settings(updates, updated_by=updated_by)
