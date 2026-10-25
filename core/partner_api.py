"""
Modulo Isolado: AURA Partner API Gateway (Opcao A).

Permite a ingestao de dados brutos provenientes do backend de parceiros
(como WebPosto) sem qualquer necessidade de instalacao local no cliente,
armazenando em staging isolado para mapeamento via YAMLDataMapperERPAdapter
com generic_postgres.yaml para entidades AUPS.
Oferece tambem chat conversacional corporativo em modo texto puro
(sem GenUI, sem vouchers ou cartoes) com streaming SSE filtrado.

Regra estrita de conformidade: Zero travessoes em todo o modulo.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import threading
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from fastapi import (
    APIRouter,
    Body,
    Depends,
    HTTPException,
    Header,
    Path as FPath,
    Query,
    Request,
    status,
)
from fastapi.responses import JSONResponse, Response, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, model_validator

from core.aura_engine import (
    AuraChunk,
    AuraChunkType,
    AuraEngine,
)
from core.logger import logger


# =============================================================================
# CONSTANTES E CONFIGURACOES DE AMBIENTE
# =============================================================================

DEFAULT_PARTNER_API_KEY = "aura-partner-default-key"
DEFAULT_STAGING_DIR = Path("data") / "staging" / "partner"

# Tabelas padrao esperadas do WebPosto / generic_postgres
RECOGNIZED_RAW_TABLES = {
    "tanques",
    "fechabomba",
    "fechacaixa",
    "pedido",
    "itemped",
    "medicaotanques",
    "produtos",
}


# =============================================================================
# FUNCOES AUXILIARES DE PARSING E CONVERSAO
# =============================================================================

def _get_field_val(r: dict[str, Any], key: str) -> Any:
    """Recupera valor de campo de um registro de forma case-insensitive."""
    if key in r:
        return r[key]
    key_lower = key.lower()
    for k, v in r.items():
        if k.lower() == key_lower:
            return v
    return None


def _compare_values(v_a: Any, v_b: Any) -> int:
    """Compara dois valores (numericos, ISO-datetime ou string) retornando -1, 0 ou 1."""
    if v_a is None and v_b is None:
        return 0
    if v_a is None:
        return -1
    if v_b is None:
        return 1

    # Comparacao numerica se ambos puderem ser convertidos para float
    try:
        fa = float(v_a)
        fb = float(v_b)
        return (fa > fb) - (fa < fb)
    except (ValueError, TypeError):
        pass

    # Comparacao textual/temporal (normaliza T para espaco para datas ISO)
    sa = str(v_a).replace("T", " ")
    sb = str(v_b).replace("T", " ")
    return (sa > sb) - (sa < sb)


def _sanitize_record_numbers(row: dict[str, Any]) -> dict[str, Any]:
    """Sanitiza strings numericas no padrao brasileiro (ex: '1.250,50' ou '5,89')."""
    cleaned: dict[str, Any] = {}
    for k, v in row.items():
        if isinstance(v, str):
            s = v.strip()
            # Formato brasileiro com milhar e virgula: '1.250,50'
            if re.match(r"^-?\d{1,3}(\.\d{3})*,\d+$", s):
                try:
                    cleaned[k] = float(s.replace(".", "").replace(",", "."))
                    continue
                except ValueError:
                    pass
            # Formato brasileiro com virgula simples: '5,89'
            if re.match(r"^-?\d+,\d+$", s):
                try:
                    cleaned[k] = float(s.replace(",", "."))
                    continue
                except ValueError:
                    pass
            cleaned[k] = s
        elif isinstance(v, dict):
            cleaned[k] = _sanitize_record_numbers(v)
        else:
            cleaned[k] = v
    return cleaned


# =============================================================================
# CONEXAO E CURSOR SIMULADOS PARA STAGING (DB-API COMPLIANT)
# =============================================================================

class PartnerStagingCursor:
    """Cursor simulado compativel com DB-API que le diretamente do staging isolado."""

    def __init__(self, store: PartnerStagingStore, station_id: str) -> None:
        self._store = store
        self._station_id = station_id
        self._rows: list[dict[str, Any]] = []
        self.description: list[tuple[str, Any, Any, Any, Any, Any, Any]] | None = None
        self.rowcount: int = 0

    def execute(self, query: str, params: list[Any] | tuple[Any, ...] | None = None) -> None:
        """Executa consultas parametrizadas do YAMLDataMapperERPAdapter sobre dados em staging."""
        clean_q = query.strip()
        params_list = list(params or [])

        # 1. Healthcheck e consultas SELECT 1
        if clean_q.upper().startswith("SELECT 1"):
            self._rows = [{"?column?": 1}]
            self.description = [("?column?", None, None, None, None, None, None)]
            self.rowcount = 1
            return

        # 2. Identifica tabela alvo no FROM
        m_from = re.search(r"\bFROM\s+([a-zA-Z0-9_]+)", clean_q, re.IGNORECASE)
        if not m_from:
            self._rows = []
            self.description = None
            self.rowcount = 0
            return

        table_name = m_from.group(1).lower()
        raw_rows = self._store.get_table_rows(self._station_id, table_name)

        # 3. Filtragem por WHERE parametrizada
        filtered_rows = list(raw_rows)
        m_where = re.search(r"\bWHERE\s+(.*?)(?:\s+ORDER\s+BY|\s+LIMIT|\s*;|$)", clean_q, re.IGNORECASE | re.DOTALL)
        if m_where:
            where_body = m_where.group(1).strip()
            conditions = re.split(r"(?i)\s+AND\s+", where_body)
            param_idx = 0
            for cond in conditions:
                c_clean = cond.strip()
                if not c_clean:
                    continue
                num_placeholders = c_clean.count("%s")
                c_params = params_list[param_idx : param_idx + num_placeholders]
                param_idx += num_placeholders

                # 3.1. Condicao != ou <> (ex: COALESCE(situ::text, '') != %s)
                if "!=" in c_clean or "<>" in c_clean:
                    m_col = re.search(r"(?:COALESCE\s*\(\s*)?([a-zA-Z0-9_]+)", c_clean, re.IGNORECASE)
                    if m_col and c_params:
                        col_k = m_col.group(1).lower()
                        exclude_val = str(c_params[0])
                        filtered_rows = [
                            r for r in filtered_rows
                            if str(_get_field_val(r, col_k) or "") != exclude_val
                        ]

                # 3.2. Condicao >= %s
                elif ">=" in c_clean and c_params:
                    m_col = re.search(r"([a-zA-Z0-9_]+)\s*>=", c_clean, re.IGNORECASE)
                    if m_col:
                        col_k = m_col.group(1).lower()
                        bound_val = c_params[0]
                        filtered_rows = [
                            r for r in filtered_rows
                            if _compare_values(_get_field_val(r, col_k), bound_val) >= 0
                        ]

                # 3.3. Condicao <= %s
                elif "<=" in c_clean and c_params:
                    m_col = re.search(r"([a-zA-Z0-9_]+)\s*<=", c_clean, re.IGNORECASE)
                    if m_col:
                        col_k = m_col.group(1).lower()
                        bound_val = c_params[0]
                        filtered_rows = [
                            r for r in filtered_rows
                            if _compare_values(_get_field_val(r, col_k), bound_val) <= 0
                        ]

                # 3.4. Condicao = %s
                elif "=" in c_clean and "IN" not in c_clean.upper() and c_params:
                    m_col = re.search(r"([a-zA-Z0-9_]+)\s*=", c_clean, re.IGNORECASE)
                    if m_col:
                        col_k = m_col.group(1).lower()
                        target_val = c_params[0]
                        filtered_rows = [
                            r for r in filtered_rows
                            if str(_get_field_val(r, col_k) or "") == str(target_val)
                        ]

                # 3.5. Condicao IN (%s, ...)
                elif "IN (" in c_clean.upper() and c_params:
                    m_col = re.search(r"([a-zA-Z0-9_]+)(?:::text)?\s+IN\s*\(", c_clean, re.IGNORECASE)
                    col_k = m_col.group(1).lower() if m_col else None
                    fk_set = {str(p) for p in c_params}
                    filtered_rows = [
                        r for r in filtered_rows
                        if (col_k and str(_get_field_val(r, col_k) or "") in fk_set)
                        or any(str(r.get(k, "")) in fk_set for k in ("pedido", "cupom_id", "codtan", "codi"))
                    ]

                # 3.6. Condicao IS NULL
                elif "IS NULL" in c_clean.upper():
                    m_col = re.search(r"([a-zA-Z0-9_]+)\s+IS\s+NULL", c_clean, re.IGNORECASE)
                    if m_col:
                        col_k = m_col.group(1).lower()
                        filtered_rows = [
                            r for r in filtered_rows
                            if _get_field_val(r, col_k) is None or _get_field_val(r, col_k) == ""
                        ]

                # 3.7. Condicao IS NOT NULL
                elif "IS NOT NULL" in c_clean.upper():
                    m_col = re.search(r"([a-zA-Z0-9_]+)\s+IS\s+NOT\s+NULL", c_clean, re.IGNORECASE)
                    if m_col:
                        col_k = m_col.group(1).lower()
                        filtered_rows = [
                            r for r in filtered_rows
                            if _get_field_val(r, col_k) is not None and _get_field_val(r, col_k) != ""
                        ]

                # 3.8. Falsidade absoluta: 1=0
                elif "1=0" in c_clean:
                    filtered_rows = []

        # 4. Tratamento de agregacao: SELECT COUNT(*) AS alias / SELECT COUNT(1) AS alias
        m_count = re.search(r"SELECT\s+COUNT\s*\([^\)]*\)\s+AS\s+([a-zA-Z0-9_]+)", clean_q, re.IGNORECASE)
        if m_count:
            cnt_alias = m_count.group(1)
            self._rows = [{cnt_alias: len(filtered_rows)}]
            self.description = [(cnt_alias, None, None, None, None, None, None)]
            self.rowcount = 1
            return

        # 5. Ordenacao por ORDER BY
        m_order = re.search(r"\bORDER\s+BY\s+([a-zA-Z0-9_\.]+)(?:\s+(ASC|DESC))?", clean_q, re.IGNORECASE)
        if m_order:
            order_col = m_order.group(1).split(".")[-1].lower()
            direction = (m_order.group(2) or "ASC").upper()
            reverse = (direction == "DESC")

            def sort_key(row: dict[str, Any]):
                v = _get_field_val(row, order_col)
                if v is None:
                    return (1, "")
                try:
                    return (0, float(v))
                except (ValueError, TypeError):
                    return (0, str(v).replace("T", " "))

            filtered_rows.sort(key=sort_key, reverse=reverse)

        # 6. Parseia colunas selecionadas e seus aliases (SELECT col AS alias, ...)
        col_defs: list[tuple[str, str]] = []
        m_sel = re.search(r"SELECT\s+(.*?)\s+FROM", clean_q, re.IGNORECASE | re.DOTALL)
        if m_sel:
            raw_cols = m_sel.group(1).split(",")
            for part in raw_cols:
                part_clean = part.strip()
                if not part_clean or part_clean == "*":
                    continue
                if re.search(r"\s+AS\s+", part_clean, re.IGNORECASE):
                    src_expr, alias = re.split(r"\s+AS\s+", part_clean, flags=re.IGNORECASE, maxsplit=1)
                    src_clean = src_expr.strip()
                    alias_clean = alias.strip()
                else:
                    src_clean = part_clean
                    alias_clean = part_clean

                # Remove funcoes e cast (ex: COALESCE(col::text, '') -> col)
                if "::" in src_clean:
                    src_clean = src_clean.split("::")[0].strip()
                if "(" in src_clean:
                    m_inner = re.search(r"\(([a-zA-Z0-9_\.]+)", src_clean)
                    if m_inner:
                        src_clean = m_inner.group(1).strip()
                if "." in src_clean:
                    src_clean = src_clean.split(".")[-1].strip()

                col_defs.append((src_clean, alias_clean))

        # 7. Mapeamento de colunas para dicionario de saida com aliases
        output_rows: list[dict[str, Any]] = []
        for r in filtered_rows:
            if not col_defs:
                output_rows.append(dict(r))
                continue
            mapped: dict[str, Any] = {}
            for src_col, alias in col_defs:
                val = _get_field_val(r, src_col)
                if val is None:
                    val = _get_field_val(r, alias)
                mapped[alias] = val
            output_rows.append(mapped)

        # 8. LIMIT
        m_limit = re.search(r"LIMIT\s+(\d+|%s)", clean_q, re.IGNORECASE)
        if m_limit:
            lim_str = m_limit.group(1)
            if lim_str == "%s" and params_list:
                try:
                    lim = int(params_list[-1])
                    output_rows = output_rows[:lim]
                except (ValueError, TypeError):
                    pass
            elif lim_str.isdigit():
                output_rows = output_rows[:int(lim_str)]

        self._rows = output_rows
        self.rowcount = len(output_rows)
        if col_defs:
            self.description = [(alias, None, None, None, None, None, None) for _, alias in col_defs]
        elif output_rows:
            self.description = [(k, None, None, None, None, None, None) for k in output_rows[0]]
        else:
            self.description = None

    def fetchall(self) -> list[dict[str, Any]]:
        return list(self._rows)

    def fetchone(self) -> dict[str, Any] | None:
        return self._rows[0] if self._rows else None

    def close(self) -> None:
        pass


class PartnerStagingConnection:
    """Conexao de banco de dados simulada para staging de parceiros."""

    def __init__(self, store: PartnerStagingStore, station_id: str) -> None:
        self._store = store
        self._station_id = station_id
        self.closed = False

    def cursor(self, **kwargs: Any) -> PartnerStagingCursor:
        return PartnerStagingCursor(self._store, self._station_id)

    def close(self) -> None:
        self.closed = True

    def __enter__(self) -> PartnerStagingConnection:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()


# =============================================================================
# REPOSITORIO DE STAGING ISOLADO (PARTNER STAGING STORE)
# =============================================================================

class PartnerStagingStore:
    """
    Gerenciador thread-safe de staging isolado por estacao.
    Persiste dados brutos em disco no volume dedicado e mantem cache em memoria
    para consultas sub-milissegundo via YAMLDataMapperERPAdapter.
    """

    def __init__(self, staging_dir: Path | str | None = None) -> None:
        configured_dir = os.getenv("PARTNER_STAGING_DIR")
        if configured_dir:
            self.staging_dir = Path(configured_dir)
        elif staging_dir is not None:
            self.staging_dir = Path(staging_dir)
        else:
            self.staging_dir = DEFAULT_STAGING_DIR

        self._lock = threading.Lock()
        # Estrutura em memoria: {station_id: {table_name: [list of row dicts]}}
        self._cache: dict[str, dict[str, list[dict[str, Any]]]] = {}
        # Metadados de sincronizacao: {station_id: {"last_synced": iso_str, "table_counts": {...}}}
        self._metadata: dict[str, dict[str, Any]] = {}

        self._ensure_storage_dir()

    def _ensure_storage_dir(self) -> None:
        """Garante a existencia do diretorio base de staging."""
        try:
            self.staging_dir.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            logger.warning(f"PartnerStagingStore: Nao foi possivel criar diretorio {self.staging_dir}: {exc}")

    @staticmethod
    def sanitize_station_id(station_id: str) -> str:
        """Valida e sanitiza o station_id prevenindo ataques de path traversal."""
        clean = station_id.strip()
        if not clean or not re.match(r"^[a-zA-Z0-9_\-]+$", clean):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Identificador de estacao invalido: use apenas letras, numeros, hifens e sublinhados.",
            )
        if len(clean) > 64:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Identificador de estacao excessivamente longo (limite de 64 caracteres).",
            )
        return clean

    def save_raw_data(
        self,
        station_id: str,
        tables: dict[str, list[dict[str, Any]]],
    ) -> dict[str, Any]:
        """Armazena tabelas cruas no staging isolado da estacao informada."""
        valid_station = self.sanitize_station_id(station_id)
        now_iso = datetime.now(UTC).isoformat()

        table_counts: dict[str, int] = {}
        with self._lock:
            if valid_station not in self._cache:
                self._cache[valid_station] = {}

            for table_name, rows in tables.items():
                t_clean = table_name.strip().lower()
                clean_rows = [_sanitize_record_numbers(r) for r in rows if isinstance(r, dict)]
                self._cache[valid_station][t_clean] = clean_rows
                table_counts[t_clean] = len(clean_rows)

            self._metadata[valid_station] = {
                "station_id": valid_station,
                "last_synced": now_iso,
                "table_counts": table_counts,
            }

        # Persistencia em disco no volume isolado
        try:
            station_dir = self.staging_dir / valid_station
            station_dir.mkdir(parents=True, exist_ok=True)
            staging_file = station_dir / "raw_data.json"
            meta_file = station_dir / "meta.json"

            payload = {
                "station_id": valid_station,
                "synced_at": now_iso,
                "tables": self._cache[valid_station],
            }
            tmp_staging = station_dir / "raw_data.tmp"
            tmp_staging.write_text(json.dumps(payload, ensure_ascii=False, default=str), encoding="utf-8")
            tmp_staging.replace(staging_file)

            tmp_meta = station_dir / "meta.tmp"
            tmp_meta.write_text(json.dumps(self._metadata[valid_station], ensure_ascii=False), encoding="utf-8")
            tmp_meta.replace(meta_file)
        except Exception as exc:
            logger.warning(f"PartnerStagingStore: Falha ao persistir staging em disco para {valid_station}: {exc}")

        return {
            "station_id": valid_station,
            "synced_at": now_iso,
            "table_counts": table_counts,
        }

    def get_table_rows(self, station_id: str, table_name: str) -> list[dict[str, Any]]:
        """Recupera linhas de uma tabela para a estacao informada."""
        valid_station = self.sanitize_station_id(station_id)
        t_clean = table_name.strip().lower()

        with self._lock:
            if valid_station in self._cache and t_clean in self._cache[valid_station]:
                return self._cache[valid_station][t_clean]

        # Fallback de leitura do disco se nao estiver em memoria
        station_dir = self.staging_dir / valid_station
        staging_file = station_dir / "raw_data.json"
        if staging_file.exists():
            try:
                data = json.loads(staging_file.read_text(encoding="utf-8"))
                tables = data.get("tables", {})
                with self._lock:
                    if valid_station not in self._cache:
                        self._cache[valid_station] = {}
                    for tbl, rws in tables.items():
                        self._cache[valid_station][tbl.lower()] = rws
                return self._cache.get(valid_station, {}).get(t_clean, [])
            except Exception as exc:
                logger.error(f"PartnerStagingStore: Erro ao carregar staging do disco ({valid_station}): {exc}")

        return []

    def get_station_status(self, station_id: str) -> dict[str, Any]:
        """Retorna diagnostico de prontidao e contagem de registros da estacao."""
        valid_station = self.sanitize_station_id(station_id)
        with self._lock:
            meta = self._metadata.get(valid_station)
            cached_tables = self._cache.get(valid_station, {})

        if meta:
            return {
                "station_id": valid_station,
                "status": "ready",
                "last_synced": meta.get("last_synced"),
                "table_counts": meta.get("table_counts", {}),
                "is_cached": True,
            }

        # Tenta carregar metadados em disco
        meta_file = self.staging_dir / valid_station / "meta.json"
        if meta_file.exists():
            try:
                disk_meta = json.loads(meta_file.read_text(encoding="utf-8"))
                return {
                    "station_id": valid_station,
                    "status": "ready",
                    "last_synced": disk_meta.get("last_synced"),
                    "table_counts": disk_meta.get("table_counts", {}),
                    "is_cached": False,
                }
            except Exception:
                pass

        return {
            "station_id": valid_station,
            "status": "empty",
            "last_synced": None,
            "table_counts": {},
            "is_cached": False,
        }

    def clear_station(self, station_id: str) -> None:
        """Limpa staging em memoria e disco para testes ou desprovisionamento."""
        valid_station = self.sanitize_station_id(station_id)
        with self._lock:
            self._cache.pop(valid_station, None)
            self._metadata.pop(valid_station, None)

        station_dir = self.staging_dir / valid_station
        if station_dir.exists():
            for f in station_dir.glob("*"):
                try:
                    f.unlink()
                except Exception:
                    pass
            try:
                station_dir.rmdir()
            except Exception:
                pass

    def get_connection(self, station_id: str) -> PartnerStagingConnection:
        """Retorna uma conexao DB-API vinculada ao staging isolado da estacao."""
        return PartnerStagingConnection(self, station_id)


# Instancia singleton de staging
_global_staging_store: PartnerStagingStore | None = None


def get_partner_staging_store() -> PartnerStagingStore:
    """Dependency provider do armazenamento em staging isolado."""
    global _global_staging_store
    if _global_staging_store is None:
        _global_staging_store = PartnerStagingStore()
    return _global_staging_store


def set_partner_staging_store(store: PartnerStagingStore | None) -> None:
    """Permite sobrescrever ou injetar a instancia de staging para testes."""
    global _global_staging_store
    _global_staging_store = store


# =============================================================================
# FACTORY PARA ADAPTADOR ERP YAML VINCULADO AO STAGING
# =============================================================================

def get_partner_erp_adapter(
    station_id: str,
    staging_store: PartnerStagingStore | None = None,
) -> Any:
    """
    Cria uma instancia de YAMLDataMapperERPAdapter configurada com generic_postgres.yaml
    e conectada diretamente ao staging isolado da estacao informada.
    """
    from core.adapters.erp import create_yaml_erp_adapter

    store = staging_store or get_partner_staging_store()
    return create_yaml_erp_adapter(
        "generic_postgres",
        connection_factory=lambda: store.get_connection(station_id),
    )


# =============================================================================
# AUTENTICACAO DE PARCEIROS E ISOLAMENTO MULTI-TENANT
# =============================================================================

def verify_partner_auth(
    request: Request,
    x_partner_key: str | None = Header(None, alias="X-Partner-Key"),
    authorization: str | None = Header(None, alias="Authorization"),
    x_station_id: str | None = Header(None, alias="X-Station-ID"),
) -> dict[str, str]:
    """
    Valida autenticacao do parceiro via Header X-Partner-Key ou Authorization: Bearer,
    e valida a correspondencia da estacao via Header X-Station-ID.
    """
    # 1. Extracao da chave de parceiro
    provided_key: str | None = None
    if x_partner_key:
        provided_key = x_partner_key.strip()
    elif authorization and authorization.lower().startswith("bearer "):
        provided_key = authorization[7:].strip()

    if not provided_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticacao de parceiro necessaria: informe o cabecalho X-Partner-Key ou Authorization: Bearer.",
        )

    # 2. Validacao da chave de parceiro
    expected_key = (
        os.getenv("AURA_PARTNER_API_KEY")
        or os.getenv("PARTNER_API_KEY")
        or os.getenv("AURA_API_KEY")
        or DEFAULT_PARTNER_API_KEY
    )
    if provided_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticacao de parceiro invalida: chave incorreta.",
        )

    # 3. Validacao do station_id
    station_id = x_station_id.strip() if x_station_id else None
    path_station_id = request.path_params.get("station_id")

    if path_station_id and station_id and path_station_id != station_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Conflito de estacao: cabecalho X-Station-ID difere do station_id da URL.",
        )

    effective_station = station_id or path_station_id or ""
    return {
        "partner_key": provided_key,
        "station_id": effective_station,
    }


# =============================================================================
# ESQUEMAS DE DADOS (PYDANTIC SCHEMAS)
# =============================================================================

class RawSyncPayload(BaseModel):
    """Payload de ingestao de tabelas brutas para staging isolado."""
    model_config = ConfigDict(extra="allow")

    station_id: str | None = Field(default=None, description="Identificador da filial/estacao")
    sync_timestamp: datetime | None = Field(default=None, description="Timestamp da sincronizacao no parceiro")
    tables: dict[str, list[dict[str, Any]]] | None = Field(
        default=None,
        description="Dicionario de tabelas cruas (ex: tanques, fechabomba, fechacaixa, pedido)",
    )

    @model_validator(mode="before")
    @classmethod
    def extract_top_level_tables(cls, data: Any) -> Any:
        """Permite envio com chave 'tables' aninhada ou com tabelas diretamente na raiz."""
        if not isinstance(data, dict):
            return data

        raw_tables = data.get("tables")
        if raw_tables is None:
            extracted: dict[str, list[dict[str, Any]]] = {}
            for k, v in data.items():
                if k in ("station_id", "sync_timestamp"):
                    continue
                if isinstance(v, list):
                    extracted[k] = v
            if extracted:
                data["tables"] = extracted
        return data


class PartnerChatRequest(BaseModel):
    """Contrato de entrada para chat de parceiro em modo texto puro."""
    query: str = Field(..., min_length=1, description="Pergunta ou instrucao em linguagem natural")
    session_id: str | None = Field(default=None, description="Identificador da sessao conversacional")
    stream: bool = Field(default=True, description="Se True, transmite via Server-Sent Events (SSE)")
    station_id: str | None = Field(default=None, description="Identificador da estacao do posto")
    tenant_id: str | None = Field(default=None, description="Identificador da rede ou tenant")
    context: dict[str, Any] | None = Field(default=None, description="Contexto adicional opcional")


# =============================================================================
# ROTEADOR DEDICADO DO AURA PARTNER GATEWAY
# =============================================================================

partner_router = APIRouter(prefix="/api/v1/partner", tags=["AURA Partner Gateway"])


@partner_router.get(
    "/health",
    summary="Healthcheck do Partner Gateway",
    description="Informa a prontidao do gateway de parceiros e versao de protocolo.",
)
async def partner_health_endpoint():
    """Endpoint de status operacional do AURA Partner Gateway."""
    return {
        "status": "online",
        "service": "AURA Partner Gateway (Opcao A)",
        "protocol_version": "1.0.0",
        "timestamp": datetime.now(UTC).isoformat(),
    }


@partner_router.post(
    "/stations/{station_id}/raw-sync",
    summary="Ingestao de Dados Brutos em Staging Isolado",
    description="Recebe tabelas cruas do backend do parceiro (ex: WebPosto) e armazena em staging isolado.",
)
async def partner_raw_sync_endpoint(
    station_id: str = FPath(..., description="Identificador da estacao/posto fisico"),
    payload: RawSyncPayload = Body(...),
    auth_info: dict[str, str] = Depends(verify_partner_auth),
    staging_store: PartnerStagingStore = Depends(get_partner_staging_store),
):
    """
    Ingere tabelas cruas do ERP (tanques, fechabomba, fechacaixa, pedido, etc.)
    e armazena em staging isolado para mapeamento universal via YAMLDataMapperERPAdapter.
    """
    clean_station = staging_store.sanitize_station_id(station_id)

    raw_tables = payload.tables or {}
    if not raw_tables:
        # Se payload nao contem tabelas
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Nenhuma tabela crua informada no payload de sincronizacao.",
        )

    res = staging_store.save_raw_data(clean_station, raw_tables)

    logger.info(
        f"PartnerGateway: Sincronizados dados da estacao {clean_station} - Tabelas: {list(raw_tables.keys())}",
        extra={
            "station_id": clean_station,
            "table_counts": res["table_counts"],
            "route": f"/api/v1/partner/stations/{clean_station}/raw-sync",
        },
    )

    return {
        "status": "success",
        "station_id": clean_station,
        "synced_at": res["synced_at"],
        "tables_stored": list(raw_tables.keys()),
        "record_counts": res["table_counts"],
        "message": "Dados brutos sincronizados com sucesso em staging isolado.",
    }


@partner_router.get(
    "/stations/{station_id}/status",
    summary="Status do Staging da Estacao",
    description="Consulta o status de sincronizacao e contagem de registros em staging para uma estacao.",
)
async def partner_station_status_endpoint(
    station_id: str = FPath(..., description="Identificador da estacao"),
    auth_info: dict[str, str] = Depends(verify_partner_auth),
    staging_store: PartnerStagingStore = Depends(get_partner_staging_store),
):
    """Consulta prontidao de staging da estacao."""
    clean_station = staging_store.sanitize_station_id(station_id)
    return staging_store.get_station_status(clean_station)


@partner_router.post(
    "/chat",
    summary="Chat Conversacional Corporativo para Parceiros (Texto Puro)",
    description="Canal de chat sem GenUI (sem cartoes ou vouchers) com streaming SSE filtrado transmitindo apenas delta e done.",
)
async def partner_chat_endpoint(
    req: PartnerChatRequest,
    request: Request,
    auth_info: dict[str, str] = Depends(verify_partner_auth),
):
    """
    Conversacao com a AURA para parceiros externos:
    - Opera em modo texto puro (enable_genui=False).
    - No streaming SSE, descarta chunks de calculos internos (intent, tool_start, tool_result, telemetry).
    - Transmite exclusivamente chunks do tipo 'delta' e 'done'.
    """
    # Import tardio para evitar ciclos de dependencia
    from core.aura_api import get_aura_engine

    engine: AuraEngine = get_aura_engine()

    # Validacao de conflito de estacao entre Header e Body
    header_station = auth_info.get("station_id")
    if header_station and req.station_id and header_station != req.station_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Conflito de estacao: cabecalho X-Station-ID difere do station_id do corpo da requisicao.",
        )

    effective_station = header_station or req.station_id or "default"
    effective_session = req.session_id or f"partner_{effective_station}_{uuid.uuid4().hex[:8]}"

    if req.stream:
        async def filtered_sse_generator():
            try:
                async for chunk in engine.ask_stream(
                    query=req.query,
                    context=req.context,
                    session_id=effective_session,
                    tenant_id=req.tenant_id,
                    filial_id=effective_station,
                    enable_genui=False, # Estritamente desativado para parceiros
                ):
                    # Filtro rigoroso: descarta chunks de calculos internos
                    if chunk.chunk_type in (AuraChunkType.DELTA, AuraChunkType.DONE):
                        yield chunk.to_sse()
            except Exception as exc:
                logger.error(f"PartnerGateway: Erro no streaming SSE: {exc}", exc_info=True)
                err_chunk = AuraChunk(
                    chunk_type=AuraChunkType.DELTA,
                    text=f"Erro interno no processamento: {exc}",
                    session_id=effective_session,
                )
                yield err_chunk.to_sse()
                done_chunk = AuraChunk(
                    chunk_type=AuraChunkType.DONE,
                    text="",
                    session_id=effective_session,
                )
                yield done_chunk.to_sse()

        return StreamingResponse(
            filtered_sse_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
                "X-Station-ID": effective_station,
                "X-GenUI-Enabled": "0",
            },
        )
    else:
        # Resposta sincronizada texto puro (sem GenUI, sem vouchers)
        response = await engine.ask(
            query=req.query,
            context=req.context,
            session_id=effective_session,
            tenant_id=req.tenant_id,
            filial_id=effective_station,
            enable_genui=False,
        )
        return {
            "session_id": response.session_id,
            "station_id": effective_station,
            "query": response.query,
            "response_text": response.response_text,
            "intent": response.intent,
            "confidence": response.confidence,
        }


# =============================================================================
# ENDPOINTS DE CONSULTA DE ENTIDADES AUPS MAPEADAS PELO YAMLDataMapper
# =============================================================================

@partner_router.get(
    "/stations/{station_id}/tanks",
    summary="Consulta Tanques em Formato AUPS",
    description="Executa o YAMLDataMapper com generic_postgres.yaml sobre o staging e retorna UniversalTankReading.",
)
async def partner_get_tanks_endpoint(
    station_id: str = FPath(..., description="Identificador da estacao"),
    auth_info: dict[str, str] = Depends(verify_partner_auth),
    staging_store: PartnerStagingStore = Depends(get_partner_staging_store),
):
    """Retorna medicoes de tanques da estacao mapeadas para o padrao canonico AUPS."""
    clean_station = staging_store.sanitize_station_id(station_id)
    adapter = get_partner_erp_adapter(clean_station, staging_store=staging_store)
    tanks = adapter.get_tank_inventory()
    tanks_payload = []
    for t in tanks:
        d = t.model_dump(mode="json")
        d["identificador_tanque"] = t.identificador_tanque
        d["combustivel"] = t.combustivel
        d["volume_atual_litros"] = t.volume_atual_litros
        d["capacidade_nominal_litros"] = t.capacidade_nominal_litros
        tanks_payload.append(d)
    return {
        "station_id": clean_station,
        "count": len(tanks),
        "tanks": tanks_payload,
    }


@partner_router.get(
    "/stations/{station_id}/pumps",
    summary="Consulta Bombas/Bicos em Formato AUPS",
    description="Executa o YAMLDataMapper com generic_postgres.yaml sobre o staging e retorna UniversalDispenserLog.",
)
async def partner_get_pumps_endpoint(
    station_id: str = FPath(..., description="Identificador da estacao"),
    auth_info: dict[str, str] = Depends(verify_partner_auth),
    staging_store: PartnerStagingStore = Depends(get_partner_staging_store),
):
    """Retorna encerrantes de bicos/bombas mapeados para AUPS."""
    clean_station = staging_store.sanitize_station_id(station_id)
    adapter = get_partner_erp_adapter(clean_station, staging_store=staging_store)
    pumps = adapter.get_pump_dispenses()
    pumps_payload = []
    for p in pumps:
        d = p.model_dump(mode="json")
        d["identificador_bomba"] = p.identificador_equipamento
        d["identificador_bico"] = p.identificador_componente
        d["volume_vendido_litros"] = p.volume_vendido_litros
        d["delta_leitura"] = p.delta_leitura
        pumps_payload.append(d)
    return {
        "station_id": clean_station,
        "count": len(pumps),
        "pumps": pumps_payload,
    }


@partner_router.get(
    "/stations/{station_id}/shifts",
    summary="Consulta Fechamentos de Caixa em Formato AUPS",
    description="Executa o YAMLDataMapper com generic_postgres.yaml sobre o staging e retorna UniversalCashierShift.",
)
async def partner_get_shifts_endpoint(
    station_id: str = FPath(..., description="Identificador da estacao"),
    auth_info: dict[str, str] = Depends(verify_partner_auth),
    staging_store: PartnerStagingStore = Depends(get_partner_staging_store),
):
    """Retorna fechamentos de caixa mapeados para AUPS."""
    clean_station = staging_store.sanitize_station_id(station_id)
    adapter = get_partner_erp_adapter(clean_station, staging_store=staging_store)
    shifts = adapter.get_cashier_shifts()
    return {
        "station_id": clean_station,
        "count": len(shifts),
        "shifts": [s.model_dump(mode="json") for s in shifts],
    }


@partner_router.get(
    "/stations/{station_id}/sales",
    summary="Consulta Vendas em Formato AUPS",
    description="Executa o YAMLDataMapper com generic_postgres.yaml sobre o staging e retorna UniversalSaleReceipt.",
)
async def partner_get_sales_endpoint(
    station_id: str = FPath(..., description="Identificador da estacao"),
    limit: int = Query(default=50, ge=1, le=500, description="Limite de registros"),
    auth_info: dict[str, str] = Depends(verify_partner_auth),
    staging_store: PartnerStagingStore = Depends(get_partner_staging_store),
):
    """Retorna cupons fiscais e itens mapeados para AUPS."""
    clean_station = staging_store.sanitize_station_id(station_id)
    adapter = get_partner_erp_adapter(clean_station, staging_store=staging_store)
    sales = adapter.get_recent_sales(limit=limit)
    return {
        "station_id": clean_station,
        "count": len(sales),
        "sales": [s.model_dump(mode="json") for s in sales],
    }
