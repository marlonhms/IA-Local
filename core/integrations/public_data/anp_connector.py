"""
Conector de Dados Abertos da ANP (Agencia Nacional do Petroleo).
Implementa download e parsing em streaming de series semanais de precos
de combustiveis e cadastro geral de postos revendedores (SICOP).
"""

import csv
import itertools
import time
from collections.abc import Generator
from typing import Any, ClassVar

import httpx

from core.integrations.public_data.base import (
    BasePublicDataConnector,
    ConnectorFetchResult,
    PublicDataCircuitBreaker,
)


class AnpPublicDataConnector(BasePublicDataConnector):
    """
    Conector resiliente para precos de combustiveis e base SICOP da ANP.
    Suporta streaming de dados em blocos de 64 KB com filtragem antecipada.
    """

    source_name: str = "anp_dados_abertos"
    base_url: str = "https://dados.gov.br/api/3/action"

    CANONICAL_FIELD_MAP: ClassVar[dict[str, str]] = {
        "regiao_sigla": "regiao",
        "regiao": "regiao",
        "estado_sigla": "estado_sigla",
        "sigla_uf": "estado_sigla",
        "sigla_da_uf": "estado_sigla",
        "uf": "estado_sigla",
        "estado": "estado_sigla",
        "municipio": "municipio",
        "nome_municipio": "municipio",
        "nome_do_municipio": "municipio",
        "revenda": "revenda",
        "nome_da_revenda": "revenda",
        "nome_revenda": "revenda",
        "razao_social": "revenda",
        "cnpj_da_revenda": "cnpj_revenda",
        "cnpj_revenda": "cnpj_revenda",
        "cnpj": "cnpj_revenda",
        "produto": "produto",
        "nome_produto": "produto",
        "nome_do_produto": "produto",
        "data_da_coleta": "data_coleta",
        "data_coleta": "data_coleta",
        "data": "data_coleta",
        "valor_de_venda": "valor_venda",
        "valor_venda": "valor_venda",
        "preco_de_venda": "valor_venda",
        "preco_venda": "valor_venda",
        "preco": "valor_venda",
        "valor": "valor_venda",
        "bandeira": "bandeira",
        "nome_da_bandeira": "bandeira",
        "unidade_de_medida": "unidade_medida",
        "unidade_medida": "unidade_medida",
        "unidade": "unidade_medida",
    }

    SICOP_FIELD_MAP: ClassVar[dict[str, str]] = {
        "cnpj": "cnpj",
        "cnpj_revenda": "cnpj",
        "razao_social": "razao_social",
        "nome_fantasia": "nome_fantasia",
        "fantasia": "nome_fantasia",
        "uf": "estado_sigla",
        "estado_sigla": "estado_sigla",
        "sigla_uf": "estado_sigla",
        "estado": "estado_sigla",
        "municipio": "municipio",
        "bairro": "bairro",
        "endereco": "endereco",
        "logradouro": "endereco",
        "cep": "cep",
        "bandeira": "bandeira",
        "capacidade_tancagem": "capacidade_tancagem",
        "tancagem_nominal": "capacidade_tancagem",
        "tancagem": "capacidade_tancagem",
        "capacidade": "capacidade_tancagem",
        "status_operacional": "status_operacional",
        "status": "status_operacional",
        "situacao": "status_operacional",
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
    def _normalize_header(header: str) -> str:
        """Remove acentos, tracos e espacos para normalizacao de cabecalho."""
        h = header.strip().lstrip("\ufeff").lower()
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
            h = h.replace(old, new)
        while "__" in h:
            h = h.replace("__", "_")
        return h.strip("_")

    @staticmethod
    def _iter_chunks_or_lines(
        content: str | bytes,
        chunk_size: int = 65536,
    ) -> Generator[str, None, None]:
        """Itera sobre conteudo de forma eficiente em chunks de 64 KB com suporte a UTF-8 BOM."""
        if isinstance(content, bytes):
            try:
                text = content.decode("utf-8-sig")
            except UnicodeDecodeError:
                text = content.decode("latin1", errors="replace")
        else:
            text = str(content).lstrip("\ufeff")

        buffer = ""
        for i in range(0, len(text), chunk_size):
            chunk = text[i:i + chunk_size]
            buffer += chunk
            lines = buffer.split("\n")
            buffer = lines.pop()
            for line in lines:
                line_str = line.strip("\r\n")
                if line_str:
                    yield line_str
        if buffer.strip("\r\n"):
            yield buffer.strip("\r\n")

    def parse_precos_csv(
        self,
        csv_content: str | bytes,
        filtro_municipio: str | None = None,
        filtro_uf: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Parser de streaming para CSV de precos semanais da ANP de alta velocidade.
        Aplica filtro in-flight por indices para descartar registros fora do escopo sem alocacao de dicts.
        """
        line_iter = self._iter_chunks_or_lines(csv_content)
        try:
            first_line = next(line_iter)
        except StopIteration:
            return []

        delimiter = ";" if ";" in first_line else ","

        def _line_stream():
            yield first_line
            yield from line_iter

        reader = csv.reader(_line_stream(), delimiter=delimiter)

        try:
            raw_headers = next(reader)
        except StopIteration:
            return []

        # Mapeia colunas encontradas para campos canonicos
        col_indices: dict[str, int] = {}
        for idx, col in enumerate(raw_headers):
            if not col:
                continue
            norm_col = self._normalize_header(col)
            canonical = self.CANONICAL_FIELD_MAP.get(norm_col, norm_col)
            col_indices[canonical] = idx

        target_mun = filtro_municipio.strip().upper() if filtro_municipio else None
        target_uf = filtro_uf.strip().upper() if filtro_uf else None

        records: list[dict[str, Any]] = []

        # Indices diretos
        idx_mun = col_indices.get("municipio")
        idx_uf = col_indices.get("estado_sigla")
        idx_regiao = col_indices.get("regiao")
        idx_revenda = col_indices.get("revenda")
        idx_cnpj = col_indices.get("cnpj_revenda")
        idx_produto = col_indices.get("produto")
        idx_data = col_indices.get("data_coleta")
        idx_valor = col_indices.get("valor_venda")
        idx_bandeira = col_indices.get("bandeira")
        idx_unidade = col_indices.get("unidade_medida")

        for row in reader:
            if not row:
                continue
            row_len = len(row)

            # Filtragem in-flight antecipada sem instanciar objeto
            if target_mun and idx_mun is not None and idx_mun < row_len and row[idx_mun].strip().upper() != target_mun:
                continue

            if target_uf and idx_uf is not None and idx_uf < row_len and row[idx_uf].strip().upper() != target_uf:
                continue

            # Conversao numerica de valor de venda
            valor_venda = 0.0
            if idx_valor is not None and idx_valor < row_len:
                raw_val = row[idx_valor]
                try:
                    clean_val = str(raw_val).replace("R$", "").replace(" ", "").replace(",", ".")
                    valor_venda = float(clean_val)
                except (ValueError, TypeError):
                    valor_venda = 0.0

            item = {
                "regiao": row[idx_regiao].strip() if idx_regiao is not None and idx_regiao < row_len else "",
                "estado_sigla": row[idx_uf].strip().upper() if idx_uf is not None and idx_uf < row_len else "",
                "municipio": row[idx_mun].strip() if idx_mun is not None and idx_mun < row_len else "",
                "revenda": row[idx_revenda].strip() if idx_revenda is not None and idx_revenda < row_len else "",
                "cnpj_revenda": row[idx_cnpj].strip() if idx_cnpj is not None and idx_cnpj < row_len else "",
                "produto": row[idx_produto].strip() if idx_produto is not None and idx_produto < row_len else "",
                "data_coleta": row[idx_data].strip() if idx_data is not None and idx_data < row_len else "",
                "valor_venda": valor_venda,
                "bandeira": row[idx_bandeira].strip() if idx_bandeira is not None and idx_bandeira < row_len else "",
                "unidade_medida": (row[idx_unidade].strip() if idx_unidade is not None and idx_unidade < row_len else "") or "R$ / litro",
            }
            records.append(item)

        return records

    def parse_postos_sicop(
        self,
        sicop_content: str | bytes,
        filtro_municipio: str | None = None,
        filtro_uf: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Parser de dados cadastrais e tancagem nominal autorizada de postos (SICOP/ANP).
        """
        line_gen = self._iter_chunks_or_lines(sicop_content)
        try:
            first_line = next(line_gen)
        except StopIteration:
            return []

        delimiter = ";" if ";" in first_line else ","
        reader = csv.DictReader(itertools.chain([first_line], line_gen), delimiter=delimiter)

        if not reader.fieldnames:
            return []

        col_map: dict[str, str] = {}
        for col in reader.fieldnames:
            if not col:
                continue
            norm_col = self._normalize_header(col)
            canonical = self.SICOP_FIELD_MAP.get(norm_col, norm_col)
            col_map[col] = canonical

        target_mun = filtro_municipio.strip().upper() if filtro_municipio else None
        target_uf = filtro_uf.strip().upper() if filtro_uf else None

        records: list[dict[str, Any]] = []

        col_cnpj = next((col for col, can in col_map.items() if can == "cnpj"), None)
        col_razao = next((col for col, can in col_map.items() if can == "razao_social"), None)
        col_fantasia = next((col for col, can in col_map.items() if can == "nome_fantasia"), None)
        col_uf = next((col for col, can in col_map.items() if can == "estado_sigla"), None)
        col_mun = next((col for col, can in col_map.items() if can == "municipio"), None)
        col_bairro = next((col for col, can in col_map.items() if can == "bairro"), None)
        col_endereco = next((col for col, can in col_map.items() if can == "endereco"), None)
        col_cep = next((col for col, can in col_map.items() if can == "cep"), None)
        col_bandeira = next((col for col, can in col_map.items() if can == "bandeira"), None)
        col_tancagem = next((col for col, can in col_map.items() if can == "capacidade_tancagem"), None)
        col_status = next((col for col, can in col_map.items() if can == "status_operacional"), None)

        for row in reader:
            if target_mun and col_mun:
                val_m = row.get(col_mun)
                if val_m is None or val_m.strip().upper() != target_mun:
                    continue

            if target_uf and col_uf:
                val_u = row.get(col_uf)
                if val_u is None or val_u.strip().upper() != target_uf:
                    continue

            raw_tanque = row.get(col_tancagem, "0") if col_tancagem else "0"
            try:
                tancagem_litros = float(str(raw_tanque).replace(".", "").replace(",", "."))
            except (ValueError, TypeError):
                tancagem_litros = 0.0

            item = {
                "cnpj": (row.get(col_cnpj) or "").strip(),
                "razao_social": (row.get(col_razao) or "").strip(),
                "nome_fantasia": (row.get(col_fantasia) or "").strip(),
                "estado_sigla": (row.get(col_uf) or "").strip().upper(),
                "municipio": (row.get(col_mun) or "").strip(),
                "bairro": (row.get(col_bairro) or "").strip(),
                "endereco": (row.get(col_endereco) or "").strip(),
                "cep": (row.get(col_cep) or "").strip(),
                "bandeira": (row.get(col_bandeira) or "").strip(),
                "capacidade_tancagem": tancagem_litros,
                "status_operacional": (row.get(col_status) or "ATIVO").strip(),
            }
            records.append(item)

        return records

    def fetch_precos_semanais(
        self,
        filtro_municipio: str | None = None,
        filtro_uf: str | None = None,
        mock_payload: bytes | None = None,
    ) -> ConnectorFetchResult:
        """
        Coleta precos semanais de combustiveis da ANP.
        Se mock_payload for fornecido, executa parsing isolado sem requisicao de rede.
        Se mock_payload for None, consulta endpoint com protecao por Circuit Breaker.
        """
        if mock_payload is not None:
            t0 = time.perf_counter()
            data = self.parse_precos_csv(
                mock_payload,
                filtro_municipio=filtro_municipio,
                filtro_uf=filtro_uf,
            )
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
                    "filtro_municipio": filtro_municipio,
                    "filtro_uf": filtro_uf,
                    "modo": "mock_payload",
                },
            )

        # Requisicao real com Circuit Breaker
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
        target_url = f"{self.base_url}/package_show?id=serie-historica-de-precos-de-combustiveis-por-revenda"

        try:
            if self.session is not None and hasattr(self.session, "get"):
                response = self.session.get(target_url, timeout=self.timeout_sec)
            else:
                with httpx.Client(timeout=self.timeout_sec) as client:
                    response = client.get(target_url)

            if response.status_code >= 400:
                raise httpx.HTTPStatusError(
                    f"Erro HTTP {response.status_code}",
                    request=getattr(response, "request", None),
                    response=response,
                )

            raw_bytes = response.content
            latency_ms = (time.perf_counter() - t0) * 1000.0
            self.circuit_breaker.record_success()

            data_bytes = raw_bytes
            stripped = raw_bytes.strip()
            if stripped.startswith(b"{") and b'"result"' in stripped:
                try:
                    import json
                    meta = json.loads(stripped.decode("utf-8-sig"))
                    resources = meta.get("result", {}).get("resources", [])
                    csv_res = next(
                        (r for r in reversed(resources) if r.get("format", "").upper() == "CSV" or str(r.get("url", "")).endswith(".csv")),
                        None,
                    )
                    if csv_res and csv_res.get("url"):
                        csv_url = csv_res["url"]
                        if self.session is not None and hasattr(self.session, "get"):
                            csv_resp = self.session.get(csv_url, timeout=self.timeout_sec)
                        else:
                            with httpx.Client(timeout=self.timeout_sec) as client:
                                csv_resp = client.get(csv_url)
                        if csv_resp.status_code < 400:
                            data_bytes = csv_resp.content
                except Exception:  # noqa: BLE001
                    data_bytes = raw_bytes

            data = self.parse_precos_csv(
                data_bytes,
                filtro_municipio=filtro_municipio,
                filtro_uf=filtro_uf,
            )

            return ConnectorFetchResult(
                success=True,
                source_name=self.source_name,
                records_count=len(data),
                data=data,
                raw_bytes_size=len(raw_bytes),
                latency_ms=latency_ms,
                cached=False,
                metadata={
                    "filtro_municipio": filtro_municipio,
                    "filtro_uf": filtro_uf,
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

    def fetch_latest_data(self, **kwargs) -> ConnectorFetchResult:
        """Implementacao do contrato abstrato de coleta."""
        return self.fetch_precos_semanais(
            filtro_municipio=kwargs.get("filtro_municipio"),
            filtro_uf=kwargs.get("filtro_uf"),
            mock_payload=kwargs.get("mock_payload"),
        )

    def parse_payload(self, payload_bytes: bytes, **kwargs) -> list[dict[str, Any]]:
        """Implementacao do contrato abstrato de parsing."""
        if kwargs.get("tipo") == "sicop":
            return self.parse_postos_sicop(
                payload_bytes,
                filtro_municipio=kwargs.get("filtro_municipio"),
                filtro_uf=kwargs.get("filtro_uf"),
            )
        return self.parse_precos_csv(
            payload_bytes,
            filtro_municipio=kwargs.get("filtro_municipio"),
            filtro_uf=kwargs.get("filtro_uf"),
        )

    def check_health(self) -> dict[str, Any]:
        """Verifica a saude operacional do conector ANP."""
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
