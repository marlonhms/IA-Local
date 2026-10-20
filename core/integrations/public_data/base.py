"""
Modulo base para o Hub de Conectores de Dados Abertos Governamentais da AURA.
Fornece Circuit Breaker nativo, enumeracao de estados e contrato abstrato base.
"""

import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class CircuitState(str, Enum):
    """Estados possiveis do Circuit Breaker de borda."""
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class PublicDataCircuitBreaker:
    """
    Circuit Breaker nativo para chamadas externas a servicos governamentais.
    Monitora falhas consecutivas e isola chamadas de rede durante cooldown.
    """

    def __init__(
        self,
        name: str = "default",
        failure_threshold: int = 3,
        cooldown_seconds: float = 3600.0,
        time_provider: Callable[[], float] | None = None,
    ):
        self.name = name
        self.failure_threshold = max(1, failure_threshold)
        self.cooldown_seconds = cooldown_seconds
        self._time_provider = time_provider or time.time
        self.state = CircuitState.CLOSED
        self.consecutive_failures = 0
        self.last_failure_time: float | None = None
        self.last_error: str | None = None
        self._half_open_trial_dispatched: bool = False

    def _get_time(self) -> float:
        return self._time_provider()

    def _check_cooldown(self) -> None:
        if self.state == CircuitState.OPEN and self.last_failure_time is not None:
            now = self._get_time()
            if (now - self.last_failure_time) >= self.cooldown_seconds:
                self.state = CircuitState.HALF_OPEN
                self._half_open_trial_dispatched = False

    def can_execute(self) -> bool:
        """
        Informa se uma requisicao de rede externa pode ser disparada.
        Transita de OPEN para HALF_OPEN se o tempo de cooldown expirou.
        Em HALF_OPEN, permite exatamente 1 requisicao de teste canario
        ate que o resultado (sucesso ou falha) seja registrado.
        """
        self._check_cooldown()
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.HALF_OPEN:
            if not self._half_open_trial_dispatched:
                self._half_open_trial_dispatched = True
                return True
            return False
        return False

    def record_success(self) -> None:
        """Registra requisicao concluida com exito, restabelecendo o circuito para CLOSED."""
        self.state = CircuitState.CLOSED
        self.consecutive_failures = 0
        self.last_failure_time = None
        self.last_error = None
        self._half_open_trial_dispatched = False

    def record_failure(self, error_msg: Any = "") -> None:
        """
        Registra falha de comunicacao de rede.
        Se em HALF_OPEN, retorna imediatamente para OPEN.
        Se em CLOSED, atinge OPEN apos atingir o limiar de falhas consecutivas.
        """
        self.consecutive_failures += 1
        self.last_failure_time = self._get_time()
        self.last_error = str(error_msg)
        self._half_open_trial_dispatched = False

        if self.state == CircuitState.HALF_OPEN or (
            self.state == CircuitState.CLOSED and self.consecutive_failures >= self.failure_threshold
        ):
            self.state = CircuitState.OPEN

    def get_state(self) -> str:
        """Retorna o estado textual atual do circuito apos avaliacao de cooldown."""
        self._check_cooldown()
        return self.state.value

    def reset(self) -> None:
        """Reinicializa o circuito para o estado original CLOSED."""
        self.state = CircuitState.CLOSED
        self.consecutive_failures = 0
        self.last_failure_time = None
        self.last_error = None
        self._half_open_trial_dispatched = False


class ConnectorFetchResult(BaseModel):
    """Resultado canonico padronizado para coletas de dados publicos."""
    success: bool
    source_name: str
    records_count: int = 0
    data: list[dict[str, Any]] = Field(default_factory=list)
    raw_bytes_size: int = 0
    latency_ms: float = 0.0
    cached: bool = False
    error_message: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class BasePublicDataConnector(ABC):
    """Contrato base abstrato para integracao com fontes publicas governamentais."""

    source_name: str = "base_public_connector"
    base_url: str = ""

    def __init__(
        self,
        timeout_sec: float = 15.0,
        circuit_breaker: PublicDataCircuitBreaker | None = None,
        session: Any | None = None,
    ):
        self.timeout_sec = timeout_sec
        self.session = session
        self._circuit_breaker = circuit_breaker or PublicDataCircuitBreaker(
            name=self.source_name
        )

    @property
    def circuit_breaker(self) -> PublicDataCircuitBreaker:
        return self._circuit_breaker

    @property
    def is_healthy(self) -> bool:
        if self._circuit_breaker is not None:
            return self._circuit_breaker.can_execute()
        return True

    @abstractmethod
    def fetch_latest_data(self, **kwargs) -> ConnectorFetchResult:
        """Coleta o lote mais recente da fonte governamental externa."""

    @abstractmethod
    def parse_payload(self, payload_bytes: bytes, **kwargs) -> list[dict[str, Any]]:
        """Efetua o parsing e sanitizacao do payload bruto em registros dicionario."""

    @abstractmethod
    def check_health(self) -> dict[str, Any]:
        """Realiza verificacao rapida de disponibilidade e estado do conector."""
