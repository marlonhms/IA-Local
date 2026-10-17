# Core Package - AURA Engine (Autonomous Unified Retail Assistant)
"""
Pacote central da AURA com carregamento sob demanda (PEP 562) para garantir
que utilitarios de borda e o host de servico Windows SCM (core.service) iniciem
em sub-segundo sem carregar modelos pesados de NLP/RAG desnecessariamente.
"""

from __future__ import annotations

import importlib
from typing import Any

_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    "create_aura_app": (".aura_api", "create_aura_app"),
    "aura_router": (".aura_api", "router"),
    "AuraChunk": (".aura_engine", "AuraChunk"),
    "AuraChunkType": (".aura_engine", "AuraChunkType"),
    "AuraEngine": (".aura_engine", "AuraEngine"),
    "AuraResponse": (".aura_engine", "AuraResponse"),
    "AuraSessionMemory": (".aura_engine", "AuraSessionMemory"),
    "StationStatus": (".aura_engine", "StationStatus"),
    "classificar_intencao": (".aura_engine", "classificar_intencao"),
    "extrair_bico": (".aura_engine", "extrair_bico"),
    "extrair_combustivel": (".aura_engine", "extrair_combustivel"),
    "extrair_data_turno": (".aura_engine", "extrair_data_turno"),
    "extrair_frentista": (".aura_engine", "extrair_frentista"),
    "extrair_grupo": (".aura_engine", "extrair_grupo"),
    "extrair_produto_cesta": (".aura_engine", "extrair_produto_cesta"),
    "limpar_termo_produto": (".aura_engine", "limpar_termo_produto"),
    "ComplianceManager": (".compliance_manager", "ComplianceManager"),
    "ENABLE_GENUI": (".config", "ENABLE_GENUI"),
    "get_feature_flags": (".config", "get_feature_flags"),
    "is_genui_enabled": (".config", "is_genui_enabled"),
    "set_genui_enabled": (".config", "set_genui_enabled"),
    "update_feature_flags": (".config", "update_feature_flags"),
    "HybridRAGEngine": (".rag_engine", "HybridRAGEngine"),
    "CentralLogSanitizer": (".sanitizer", "CentralLogSanitizer"),
    "DataSanitizer": (".sanitizer", "DataSanitizer"),
    "central_log_sanitizer": (".sanitizer", "central_log_sanitizer"),
    "data_sanitizer": (".sanitizer", "data_sanitizer"),
    "sanitize_dict": (".sanitizer", "sanitize_dict"),
    "sanitize_text": (".sanitizer", "sanitize_text"),
    "AuraSRETelemetry": (".telemetry", "AuraSRETelemetry"),
    "PostoTools": (".tools", "PostoTools"),
    "AuraWatchdogSentinel": (".watchdog", "AuraWatchdogSentinel"),
    "WatchdogHealthResult": (".watchdog", "WatchdogHealthResult"),
    "WatchdogIncidentEvent": (".watchdog", "WatchdogIncidentEvent"),
    "CircuitState": (".resource_watchdog", "CircuitState"),
    "HardwareCircuitBreaker": (".resource_watchdog", "HardwareCircuitBreaker"),
    "ResourceWatchdog": (".resource_watchdog", "ResourceWatchdog"),
    "get_resource_watchdog": (".resource_watchdog", "get_resource_watchdog"),
    "DesktopNotifier": (".desktop_notifier", "DesktopNotifier"),
    "get_desktop_notifier": (".desktop_notifier", "get_desktop_notifier"),
    "DesktopNotificationResult": (".desktop_notifier", "DesktopNotificationResult"),
    "DesktopConfirmationResult": (".desktop_notifier", "DesktopConfirmationResult"),
    "AuraTransactionalOutbox": (".outbox", "AuraTransactionalOutbox"),
    "OutboxMessage": (".outbox", "OutboxMessage"),
    "OutboxStatus": (".outbox", "OutboxStatus"),
    "OutboxBatchResult": (".outbox", "OutboxBatchResult"),
    "get_transactional_outbox": (".outbox", "get_transactional_outbox"),
    "AuraWebhookDispatcher": (".webhook_dispatcher", "AuraWebhookDispatcher"),
    "get_webhook_dispatcher": (".webhook_dispatcher", "get_webhook_dispatcher"),
    "AuraCommandJournal": (".command_journal", "AuraCommandJournal"),
    "CommandJournalEntry": (".command_journal", "CommandJournalEntry"),
    "CommandJournalStatus": (".command_journal", "CommandJournalStatus"),
    "CommandAcquisitionResult": (".command_journal", "CommandAcquisitionResult"),
    "get_command_journal": (".command_journal", "get_command_journal"),
    "set_command_journal": (".command_journal", "set_command_journal"),
    "reset_command_journal": (".command_journal", "reset_command_journal"),
}

__all__ = [
    "ENABLE_GENUI",
    "AuraChunk",
    "AuraChunkType",
    "AuraCommandJournal",
    "AuraEngine",
    "AuraResponse",
    "AuraSRETelemetry",
    "AuraSessionMemory",
    "AuraTransactionalOutbox",
    "AuraWatchdogSentinel",
    "AuraWebhookDispatcher",
    "CentralLogSanitizer",
    "CircuitState",
    "CommandAcquisitionResult",
    "CommandJournalEntry",
    "CommandJournalStatus",
    "ComplianceManager",
    "DataSanitizer",
    "DesktopConfirmationResult",
    "DesktopNotificationResult",
    "DesktopNotifier",
    "HardwareCircuitBreaker",
    "HybridRAGEngine",
    "OutboxBatchResult",
    "OutboxMessage",
    "OutboxStatus",
    "PostoTools",
    "ResourceWatchdog",
    "StationStatus",
    "WatchdogHealthResult",
    "WatchdogIncidentEvent",
    "aura_router",
    "central_log_sanitizer",
    "classificar_intencao",
    "create_aura_app",
    "data_sanitizer",
    "extrair_bico",
    "extrair_combustivel",
    "extrair_data_turno",
    "extrair_frentista",
    "extrair_grupo",
    "extrair_produto_cesta",
    "get_command_journal",
    "get_desktop_notifier",
    "get_feature_flags",
    "get_resource_watchdog",
    "get_transactional_outbox",
    "get_webhook_dispatcher",
    "is_genui_enabled",
    "limpar_termo_produto",
    "reset_command_journal",
    "sanitize_dict",
    "sanitize_text",
    "set_command_journal",
    "set_genui_enabled",
    "update_feature_flags",
]


def __getattr__(name: str) -> Any:
    if name in _LAZY_EXPORTS:
        mod_name, attr_name = _LAZY_EXPORTS[name]
        mod = importlib.import_module(mod_name, __name__)
        val = getattr(mod, attr_name)
        globals()[name] = val
        return val
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
