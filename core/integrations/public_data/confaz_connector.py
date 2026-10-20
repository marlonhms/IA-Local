"""
Conector de Atos COTEPE e Tabelas PMPF do CONFAZ (Conselho Nacional de Politica Fazendaria).
Permite ingestao e normalizacao de pautas fiscais de Preco Medio Ponderado ao Consumidor Final
para auditoria de ICMS-ST e ICMS Monofasico em postos revendedores.
"""

import re
import time
from typing import Any, ClassVar

import httpx

from core.integrations.public_data.base import (
    BasePublicDataConnector,
    ConnectorFetchResult,
    PublicDataCircuitBreaker,
)


class ConfazPmpfConnector(BasePublicDataConnector):
    """
    Conector resiliente para pautas de PMPF do CONFAZ e Atos COTEPE.
    Normaliza tabelas publicadas no DOU ou portal CONFAZ por Unidade Federativa.
    """

    source_name: str = "confaz_cotepe_pmpf"
    base_url: str = "https://www.confaz.fazenda.gov.br/legislacao/atos/atos_cotepe"

    VALID_UFS: ClassVar[set[str]] = {
        "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA",
        "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN",
        "RO", "RR", "RS", "SC", "SE", "SP", "TO",
    }

    CANONICAL_PRODUCTS: ClassVar[list[str]] = [
        "gasolina_comum",
        "gasolina_aditivada",
        "etanol_hidratado",
        "diesel_s10",
        "diesel_s500",
        "glp",
    ]

    PRODUCT_ALIASES: ClassVar[dict[str, str]] = {
        "gasolina_comum": "gasolina_comum",
        "gasolina_c": "gasolina_comum",
        "gasolina": "gasolina_comum",
        "gasolina_aditivada": "gasolina_aditivada",
        "gasolina_adit": "gasolina_aditivada",
        "etanol_hidratado": "etanol_hidratado",
        "etanol_hidratado_combustivel": "etanol_hidratado",
        "ehc": "etanol_hidratado",
        "etanol": "etanol_hidratado",
        "alcool": "etanol_hidratado",
        "diesel_s10": "diesel_s10",
        "diesel_s_10": "diesel_s10",
        "oleo_diesel_s10": "diesel_s10",
        "oleo_diesel_s_10": "diesel_s10",
        "s10": "diesel_s10",
        "s_10": "diesel_s10",
        "diesel_s500": "diesel_s500",
        "diesel_s_500": "diesel_s500",
        "oleo_diesel_s500": "diesel_s500",
        "oleo_diesel_s_500": "diesel_s500",
        "s500": "diesel_s500",
        "s_500": "diesel_s500",
        "glp": "glp",
        "gas_glp": "glp",
        "glp_p13": "glp",
        "gas_liquefeito": "glp",
        "gas_liquefeito_de_petroleo": "glp",
        "gas_liquefeito_petroleo": "glp",
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
    def _parse_decimal(val_str: Any) -> float:
        """Converte representacao textual de decimal brasileiro para float."""
        if val_str is None:
            return 0.0
        if isinstance(val_str, (int, float)):
            return round(float(val_str), 4)

        s = str(val_str).strip().replace("R$", "").replace(" ", "")
        if not s:
            return 0.0

        if "." in s and "," in s:
            s = s.replace(".", "").replace(",", ".")
        elif "," in s:
            s = s.replace(",", ".")

        try:
            return round(float(s), 4)
        except ValueError:
            return 0.0

    @classmethod
    def _normalize_product_name(cls, raw_name: str) -> str | None:
        """Normaliza nome de produto para chave canonica com suporte a nomes oficiais DOU/COTEPE."""
        cleaned = raw_name.strip().lstrip("\ufeff").lower()
        cleaned = re.sub(r"\(.*?\)", "", cleaned).strip()
        replacements = (
            ("ã", "a"), ("á", "a"), ("à", "a"), ("â", "a"),
            ("é", "e"), ("ê", "e"),
            ("í", "i"),
            ("ó", "o"), ("ô", "o"), ("õ", "o"),
            ("ú", "u"),
            ("ç", "c"),
            ("-", "_"), (" ", "_"), (".", ""), ("/", "_"),
        )
        for old, new in replacements:
            cleaned = cleaned.replace(old, new)
        while "__" in cleaned:
            cleaned = cleaned.replace("__", "_")
        cleaned = cleaned.strip("_")
        return cls.PRODUCT_ALIASES.get(cleaned)

    def parse_cotepe_text(
        self,
        texto_ou_html: str | bytes,
        filtro_uf: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Parser resiliente para extrair pautas fiscais PMPF por Unidade Federativa.
        Suporta tabelas em CSV, TSV, pipes markdown e HTML com conversao para reais.
        """
        if isinstance(texto_ou_html, bytes):
            try:
                raw_text = texto_ou_html.decode("utf-8-sig")
            except UnicodeDecodeError:
                raw_text = texto_ou_html.decode("latin1", errors="replace")
        else:
            raw_text = str(texto_ou_html).lstrip("\ufeff")

        target_uf = filtro_uf.strip().upper() if filtro_uf else None
        lines_or_rows: list[list[str]] = []

        # Deteccao de formato HTML
        if "<tr" in raw_text.lower():
            row_matches = re.findall(r"<tr[^>]*>(.*?)</tr>", raw_text, re.IGNORECASE | re.DOTALL)
            for row_html in row_matches:
                cells = re.findall(r"<(?:td|th)[^>]*>(.*?)</(?:td|th)>", row_html, re.IGNORECASE | re.DOTALL)
                clean_cells = [re.sub(r"<[^>]+>", "", c).strip().lstrip("\ufeff") for c in cells]
                if any(clean_cells):
                    lines_or_rows.append(clean_cells)
        else:
            # Formato textual / delimitado
            for line in raw_text.splitlines():
                line_str = line.strip().lstrip("\ufeff")
                if not line_str or line_str.startswith("#"):
                    continue
                # Split considerando delimitadores comuns
                if ";" in line_str:
                    parts = [p.strip().lstrip("\ufeff") for p in line_str.split(";")]
                elif "\t" in line_str:
                    parts = [p.strip().lstrip("\ufeff") for p in line_str.split("\t")]
                elif "|" in line_str:
                    parts = [p.strip().lstrip("\ufeff") for p in line_str.split("|")]
                    parts = [p for p in parts if p != ""]
                elif "," in line_str and not re.search(r"\d,\d", line_str):
                    parts = [p.strip().lstrip("\ufeff") for p in line_str.split(",")]
                else:
                    parts = [p.strip().lstrip("\ufeff") for p in re.split(r"\s{2,}", line_str)]

                if any(parts):
                    lines_or_rows.append(parts)

        if not lines_or_rows:
            return []

        # Analise de cabecalho para associacao de produtos
        header_product_map: list[str | None] = []
        data_rows: list[list[str]] = []

        for row in lines_or_rows:
            first_cell = row[0].strip().lstrip("\ufeff").upper()
            if first_cell in ("UF", "ESTADO", "ESTADO_SIGLA", "SIGLA"):
                header_product_map = [self._normalize_product_name(c) for c in row[1:]]
            elif first_cell in self.VALID_UFS:
                data_rows.append(row)
            elif len(row) > 1 and row[1].strip().lstrip("\ufeff").upper() in self.VALID_UFS:
                # Caso a primeira coluna seja indice ordinal ou regiao
                data_rows.append(row[1:])

        # Processamento das linhas por UF
        records: list[dict[str, Any]] = []

        for row in data_rows:
            uf = row[0].strip().upper()
            if uf not in self.VALID_UFS:
                continue

            if target_uf and uf != target_uf:
                continue

            # Valores associados aos produtos canonicos
            row_values = row[1:]
            record: dict[str, Any] = {"uf": uf}

            # Inicializa campos com valor padrao 0.0
            for prod in self.CANONICAL_PRODUCTS:
                record[prod] = 0.0

            if header_product_map:
                for idx, val in enumerate(row_values):
                    if idx < len(header_product_map):
                        canonical_prod = header_product_map[idx]
                        if canonical_prod:
                            record[canonical_prod] = self._parse_decimal(val)
            else:
                for idx, prod in enumerate(self.CANONICAL_PRODUCTS):
                    if idx < len(row_values):
                        record[prod] = self._parse_decimal(row_values[idx])

            records.append(record)

        return records

    def fetch_pmpf_atual(
        self,
        filtro_uf: str | None = None,
        mock_payload: bytes | None = None,
    ) -> ConnectorFetchResult:
        """
        Coleta pauta mais recente de PMPF COTEPE.
        Se mock_payload for fornecido, executa parsing isolado sem rede.
        Se mock_payload for None, consulta endpoint com Circuit Breaker.
        """
        if mock_payload is not None:
            t0 = time.perf_counter()
            data = self.parse_cotepe_text(mock_payload, filtro_uf=filtro_uf)
            latency_ms = (time.perf_counter() - t0) * 1000.0
            return ConnectorFetchResult(
                success=True,
                source_name=self.source_name,
                records_count=len(data),
                data=data,
                raw_bytes_size=len(mock_payload),
                latency_ms=latency_ms,
                cached=False,
                metadata={"filtro_uf": filtro_uf, "modo": "mock_payload"},
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
        try:
            if self.session is not None and hasattr(self.session, "get"):
                response = self.session.get(self.base_url, timeout=self.timeout_sec)
            else:
                with httpx.Client(timeout=self.timeout_sec) as client:
                    response = client.get(self.base_url)

            if response.status_code >= 400:
                raise httpx.HTTPStatusError(
                    f"Erro HTTP {response.status_code}",
                    request=getattr(response, "request", None),
                    response=response,
                )

            raw_bytes = response.content
            latency_ms = (time.perf_counter() - t0) * 1000.0
            self.circuit_breaker.record_success()

            data = self.parse_cotepe_text(raw_bytes, filtro_uf=filtro_uf)

            return ConnectorFetchResult(
                success=True,
                source_name=self.source_name,
                records_count=len(data),
                data=data,
                raw_bytes_size=len(raw_bytes),
                latency_ms=latency_ms,
                cached=False,
                metadata={"filtro_uf": filtro_uf, "status_code": response.status_code},
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

    def fetch_latest_data(self, **kwargs) -> ConnectorFetchResult:
        """Implementacao do contrato abstrato de coleta."""
        return self.fetch_pmpf_atual(
            filtro_uf=kwargs.get("filtro_uf"),
            mock_payload=kwargs.get("mock_payload"),
        )

    def parse_payload(self, payload_bytes: bytes, **kwargs) -> list[dict[str, Any]]:
        """Implementacao do contrato abstrato de parsing."""
        return self.parse_cotepe_text(
            payload_bytes,
            filtro_uf=kwargs.get("filtro_uf"),
        )

    def check_health(self) -> dict[str, Any]:
        """Verifica a saude operacional do conector CONFAZ."""
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
