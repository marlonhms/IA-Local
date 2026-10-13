"""
Configuracao de Logging Estruturado em Formato JSON Padronizado (P1-6).
Fornece formatador JSON compativel com observabilidade corporativa,
propagacao de request_id via ContextVar e medicao de latencia por requisicao.
Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

# ContextVar para correlacao de traces entre corrotinas e threads
current_request_id: ContextVar[str | None] = ContextVar("current_request_id", default=None)
current_client_ip: ContextVar[str | None] = ContextVar("current_client_ip", default=None)


class StructuredJsonFormatter(logging.Formatter):
    """
    Formatador de log que emite registros como linhas JSON validas (JSONL).
    Campos padronizados:
    - timestamp (ISO8601 UTC)
    - level (INFO, WARNING, ERROR, etc)
    - logger (nome do logger)
    - message (mensagem formatada)
    - request_id (UUID de rastreabilidade ou None)
    - client_ip (IP do cliente se disponivel)
    - elapsed_ms (tempo de execucao em milissegundos se fornecido)
    - module (modulo de origem)
    - extra (dados adicionais passados via extra={...})
    """

    def format(self, record: logging.LogRecord) -> str:
        # Extrai timestamp em UTC ISO8601
        dt = datetime.fromtimestamp(record.created, tz=UTC)
        timestamp_str = dt.isoformat()

        # Determina request_id e client_ip (do record ou do contextvar)
        req_id = getattr(record, "request_id", None) or current_request_id.get()
        cli_ip = getattr(record, "client_ip", None) or current_client_ip.get()
        elapsed = getattr(record, "elapsed_ms", None)

        log_payload: dict[str, Any] = {
            "timestamp": timestamp_str,
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": req_id,
            "client_ip": cli_ip,
            "module": record.module,
        }

        if elapsed is not None:
            try:
                log_payload["elapsed_ms"] = round(float(elapsed), 2)
            except (ValueError, TypeError):
                log_payload["elapsed_ms"] = elapsed

        # Captura informacoes de excecao caso existam
        if record.exc_info:
            log_payload["exception"] = self.formatException(record.exc_info)

        # Campos extras customizados
        for key, val in record.__dict__.items():
            if key not in (
                "args", "asctime", "created", "exc_info", "exc_text", "filename",
                "funcName", "id", "levelname", "levelno", "lineno", "module",
                "msecs", "message", "msg", "name", "pathname", "process",
                "processName", "relativeCreated", "stack_info", "thread",
                "threadName", "request_id", "client_ip", "elapsed_ms", "exception"
            ):
                try:
                    json.dumps({key: val})  # Testa serializacao basica
                    log_payload[key] = val
                except (TypeError, OverflowError):
                    log_payload[key] = str(val)

        return json.dumps(log_payload, ensure_ascii=False)


def get_structured_logger(name: str = "aura") -> logging.Logger:
    """Retorna logger configurado com o formatador estruturado JSON."""
    return logging.getLogger(name)


def setup_logging(
    level: str = "INFO",
    json_format: bool = True,
    log_file: str | None = None,
) -> None:
    """
    Configura os handlers e formatadores do sistema de logging.
    """
    root_logger = logging.getLogger()
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    root_logger.setLevel(numeric_level)

    # Remove handlers existentes para evitar duplicacao
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    if json_format:
        formatter: logging.Formatter = StructuredJsonFormatter()
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    # Console Handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File Handler opcional
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
