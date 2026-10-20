"""
Conector de Series Temporais do BACEN SGS (Sistema Gerenciador de Series Temporais).
Fornece integracao com indicadores macroeconomicos oficiais:
Selic diaria anualizada (Serie 11), Cambio PTAX Dolar Venda (Serie 10813) e IPCA mensal (Serie 433).
"""

import json
import time
from typing import Any, ClassVar

import httpx

from core.integrations.public_data.base import (
    BasePublicDataConnector,
    ConnectorFetchResult,
    PublicDataCircuitBreaker,
)


class BacenSgsConnector(BasePublicDataConnector):
    """
    Conector oficial para a API REST do Banco Central do Brasil (BACEN SGS).
    Coleta Selic, PTAX Dolar e IPCA para calculo de custo financeiro de estoque.
    """

    source_name: str = "bacen_sgs_api"
    base_url: str = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo_serie}/dados?formato=json"

    SERIE_SELIC_DIARIA: int = 11
    SERIE_PTAX_DOLAR_VENDA: int = 10813
    SERIE_IPCA_MENSAL: int = 433

    SERIES_CANONICAS: ClassVar[dict[str, int]] = {
        "selic_diaria": SERIE_SELIC_DIARIA,
        "ptax_dolar_venda": SERIE_PTAX_DOLAR_VENDA,
        "ipca_mensal": SERIE_IPCA_MENSAL,
    }

    def __init__(
        self,
        timeout_sec: float = 15.0,
        circuit_breaker: PublicDataCircuitBreaker | None = None,
        session: Any | None = None,
    ):
        super().__init__(
            timeout_sec=timeout_sec,
            circuit_breaker=circuit_breaker,
            session=session,
        )

    @staticmethod
    def _convert_date_to_iso(date_str: str) -> str:
        """Converte DD/MM/AAAA para AAAA-MM-DD mantendo compatibilidade."""
        parts = date_str.strip().split("/")
        if len(parts) == 3:
            day, month, year = parts
            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        return date_str.strip()

    @staticmethod
    def calcular_custo_carregamento(
        volume_litros: Any,
        custo_unitario: Any,
        taxa_selic_anual: Any,
        dias_estoque: Any = 30,
    ) -> float:
        """
        Calcula o custo financeiro de oportunidade de capital retido em estoque:
        Custo = Volume * Custo_Unitario * (Selic_Anual / 100 / 252) * Dias_Estoque.
        """
        try:
            v = float(volume_litros)
            c = float(custo_unitario)
            s = float(taxa_selic_anual)
            d = int(dias_estoque)
        except (ValueError, TypeError):
            return 0.0

        if v <= 0 or c <= 0 or s <= 0 or d <= 0:
            return 0.0
        taxa_diaria = (s / 100.0) / 252.0
        custo = v * c * taxa_diaria * d
        return round(custo, 2)

    def parse_sgs_json(
        self,
        payload_bytes_or_str: Any,
        codigo_serie: int = 0,
    ) -> list[dict[str, Any]]:
        """
        Parser de JSON oficial do BACEN SGS com validacao numerica e temporal.
        Suporta decodificacao com BOM UTF-8 (utf-8-sig).
        """
        if isinstance(payload_bytes_or_str, bytes):
            text = payload_bytes_or_str.decode("utf-8-sig")
        else:
            text = str(payload_bytes_or_str).lstrip("\ufeff")

        try:
            raw_list = json.loads(text)
        except Exception:  # noqa: BLE001
            return []

        if not isinstance(raw_list, list):
            return []

        records: list[dict[str, Any]] = []
        for item in raw_list:
            if not isinstance(item, dict):
                continue

            raw_data = str(item.get("data", "")).strip()
            raw_valor = item.get("valor", 0)

            try:
                clean_valor = str(raw_valor).replace(",", ".").strip()
                valor_float = float(clean_valor)
            except (ValueError, TypeError):
                valor_float = 0.0

            records.append({
                "data": raw_data,
                "data_iso": self._convert_date_to_iso(raw_data),
                "valor": valor_float,
                "codigo_serie": codigo_serie,
            })

        return records

    def fetch_serie(
        self,
        codigo_serie: int,
        data_inicio: str | None = None,
        data_fim: str | None = None,
        mock_payload: bytes | None = None,
    ) -> ConnectorFetchResult:
        """
        Coleta serie temporal especifica do BACEN SGS.
        Se mock_payload for fornecido, executa parsing isolado sem requisicao externa.
        Se mock_payload for None, consulta endpoint oficial com protecao por Circuit Breaker.
        """
        if mock_payload is not None:
            t0 = time.perf_counter()
            data = self.parse_sgs_json(mock_payload, codigo_serie=codigo_serie)
            latency_ms = (time.perf_counter() - t0) * 1000.0
            return ConnectorFetchResult(
                success=True,
                source_name=self.source_name,
                records_count=len(data),
                data=data,
                raw_bytes_size=len(mock_payload),
                latency_ms=latency_ms,
                cached=False,
                metadata={
                    "codigo_serie": codigo_serie,
                    "modo": "mock_payload",
                },
            )

        if not self.circuit_breaker.can_execute():
            return ConnectorFetchResult(
                success=False,
                source_name=self.source_name,
                records_count=0,
                data=[],
                raw_bytes_size=0,
                latency_ms=0.0,
                cached=True,
                error_message=(
                    f"Circuito {self.circuit_breaker.get_state()} para {self.source_name}: "
                    "requisicoes externas bloqueadas pelo cooldown"
                ),
                metadata={"circuit_state": self.circuit_breaker.get_state()},
            )

        t0 = time.perf_counter()
        target_url = self.base_url.format(codigo_serie=codigo_serie)

        params: dict[str, str] = {}
        if data_inicio:
            params["dataInicial"] = data_inicio
        if data_fim:
            params["dataFinal"] = data_fim

        try:
            if self.session is not None and hasattr(self.session, "get"):
                response = self.session.get(target_url, params=params, timeout=self.timeout_sec)
            else:
                with httpx.Client(timeout=self.timeout_sec) as client:
                    response = client.get(target_url, params=params)

            if response.status_code >= 400:
                raise httpx.HTTPStatusError(
                    f"Erro HTTP {response.status_code}",
                    request=getattr(response, "request", None),
                    response=response,
                )

            raw_bytes = response.content
            latency_ms = (time.perf_counter() - t0) * 1000.0
            self.circuit_breaker.record_success()

            data = self.parse_sgs_json(raw_bytes, codigo_serie=codigo_serie)

            return ConnectorFetchResult(
                success=True,
                source_name=self.source_name,
                records_count=len(data),
                data=data,
                raw_bytes_size=len(raw_bytes),
                latency_ms=latency_ms,
                cached=False,
                metadata={
                    "codigo_serie": codigo_serie,
                    "status_code": response.status_code,
                },
            )

        except Exception as exc:  # noqa: BLE001
            latency_ms = (time.perf_counter() - t0) * 1000.0
            self.circuit_breaker.record_failure(str(exc))
            return ConnectorFetchResult(
                success=False,
                source_name=self.source_name,
                records_count=0,
                data=[],
                raw_bytes_size=0,
                latency_ms=latency_ms,
                cached=False,
                error_message=str(exc),
                metadata={"circuit_state": self.circuit_breaker.get_state()},
            )

    def fetch_indicadores_financeiros(
        self,
        data_inicio: str | None = None,
        data_fim: str | None = None,
        mock_payloads: dict[int, bytes] | None = None,
        volume_litros: float = 50000.0,
        custo_unitario: float = 5.0,
        dias_estoque: int = 30,
    ) -> ConnectorFetchResult:
        """
        Retorna snapshot consolidado dos 3 indicadores macroeconomicos canonicos:
        Selic diaria (11), PTAX Dolar Venda (10813) e IPCA mensal (433),
        juntamente com o custo de carregamento financeiro de estoque projetado.
        Aplica fail-fast para evitar multiplos timeouts em cascata quando a rede falha.
        """
        t0 = time.perf_counter()

        if mock_payloads is None and not self.circuit_breaker.can_execute():
            return ConnectorFetchResult(
                success=False,
                source_name=self.source_name,
                records_count=0,
                data=[],
                raw_bytes_size=0,
                latency_ms=0.0,
                cached=True,
                error_message=(
                    f"Circuito {self.circuit_breaker.get_state()} para {self.source_name}: "
                    "requisicoes externas bloqueadas pelo cooldown"
                ),
                metadata={"circuit_state": self.circuit_breaker.get_state()},
            )

        if mock_payloads is not None:
            mock_selic = mock_payloads.get(self.SERIE_SELIC_DIARIA, b"[]")
            mock_ptax = mock_payloads.get(self.SERIE_PTAX_DOLAR_VENDA, b"[]")
            mock_ipca = mock_payloads.get(self.SERIE_IPCA_MENSAL, b"[]")
        else:
            mock_selic = None
            mock_ptax = None
            mock_ipca = None

        res_selic = self.fetch_serie(
            self.SERIE_SELIC_DIARIA,
            data_inicio=data_inicio,
            data_fim=data_fim,
            mock_payload=mock_selic,
        )
        if not res_selic.success:
            latency_ms = (time.perf_counter() - t0) * 1000.0
            return ConnectorFetchResult(
                success=False,
                source_name=self.source_name,
                records_count=0,
                data=[],
                raw_bytes_size=res_selic.raw_bytes_size,
                latency_ms=latency_ms,
                cached=res_selic.cached,
                error_message=res_selic.error_message,
                metadata={"circuit_state": self.circuit_breaker.get_state()},
            )

        res_ptax = self.fetch_serie(
            self.SERIE_PTAX_DOLAR_VENDA,
            data_inicio=data_inicio,
            data_fim=data_fim,
            mock_payload=mock_ptax,
        )
        if not res_ptax.success:
            latency_ms = (time.perf_counter() - t0) * 1000.0
            return ConnectorFetchResult(
                success=False,
                source_name=self.source_name,
                records_count=0,
                data=[],
                raw_bytes_size=res_selic.raw_bytes_size + res_ptax.raw_bytes_size,
                latency_ms=latency_ms,
                cached=res_ptax.cached,
                error_message=res_ptax.error_message,
                metadata={"circuit_state": self.circuit_breaker.get_state()},
            )

        res_ipca = self.fetch_serie(
            self.SERIE_IPCA_MENSAL,
            data_inicio=data_inicio,
            data_fim=data_fim,
            mock_payload=mock_ipca,
        )
        if not res_ipca.success:
            latency_ms = (time.perf_counter() - t0) * 1000.0
            return ConnectorFetchResult(
                success=False,
                source_name=self.source_name,
                records_count=0,
                data=[],
                raw_bytes_size=res_selic.raw_bytes_size + res_ptax.raw_bytes_size + res_ipca.raw_bytes_size,
                latency_ms=latency_ms,
                cached=res_ipca.cached,
                error_message=res_ipca.error_message,
                metadata={"circuit_state": self.circuit_breaker.get_state()},
            )

        # Extrai os valores mais recentes
        selic_val = res_selic.data[-1]["valor"] if res_selic.data else 0.0
        ptax_val = res_ptax.data[-1]["valor"] if res_ptax.data else 0.0
        ipca_val = res_ipca.data[-1]["valor"] if res_ipca.data else 0.0

        data_ref = (
            res_selic.data[-1]["data_iso"]
            if res_selic.data
            else time.strftime("%Y-%m-%d")
        )

        custo_carregamento = self.calcular_custo_carregamento(
            volume_litros=volume_litros,
            custo_unitario=custo_unitario,
            taxa_selic_anual=selic_val,
            dias_estoque=dias_estoque,
        )

        snapshot = {
            "selic_anual": selic_val,
            "ptax_dolar_venda": ptax_val,
            "ipca_mensal": ipca_val,
            "data_referencia": data_ref,
            "custo_carregamento_estoque": custo_carregamento,
            "parametros_simulacao": {
                "volume_litros": volume_litros,
                "custo_unitario": custo_unitario,
                "dias_estoque": dias_estoque,
            },
            "detalhes": {
                "serie_11_selic": res_selic.data,
                "serie_10813_ptax": res_ptax.data,
                "serie_433_ipca": res_ipca.data,
            },
        }

        total_bytes = (
            res_selic.raw_bytes_size + res_ptax.raw_bytes_size + res_ipca.raw_bytes_size
        )
        latency_ms = (time.perf_counter() - t0) * 1000.0

        return ConnectorFetchResult(
            success=True,
            source_name=self.source_name,
            records_count=1,
            data=[snapshot],
            raw_bytes_size=total_bytes,
            latency_ms=latency_ms,
            cached=False,
            metadata={"status": "consolidado_ok"},
        )

    def fetch_latest_data(self, **kwargs) -> ConnectorFetchResult:
        """Implementacao do contrato abstrato de coleta."""
        return self.fetch_indicadores_financeiros(
            data_inicio=kwargs.get("data_inicio"),
            data_fim=kwargs.get("data_fim"),
            mock_payloads=kwargs.get("mock_payloads"),
            volume_litros=kwargs.get("volume_litros", 50000.0),
            custo_unitario=kwargs.get("custo_unitario", 5.0),
            dias_estoque=kwargs.get("dias_estoque", 30),
        )

    def parse_payload(self, payload_bytes: bytes, **kwargs) -> list[dict[str, Any]]:
        """Implementacao do contrato abstrato de parsing."""
        codigo = kwargs.get("codigo_serie", 0)
        return self.parse_sgs_json(payload_bytes, codigo_serie=codigo)

    def check_health(self) -> dict[str, Any]:
        """Verifica a saude operacional do conector BACEN SGS."""
        t0 = time.perf_counter()
        can_exec = self.circuit_breaker.can_execute()
        latency_ms = (time.perf_counter() - t0) * 1000.0
        return {
            "source_name": self.source_name,
            "is_healthy": can_exec,
            "circuit_state": self.circuit_breaker.get_state(),
            "latency_ms": latency_ms,
            "base_url": self.base_url,
        }
