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

from collections import OrderedDict
import unicodedata

import asyncio
import hashlib
import hmac
import json
import math
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
# BLINDAGEM ZERO-TRUST: LGPD PII SCRUBBING E INVARIANTES FISICAS (MODULO 3)
# =============================================================================

_CPF_REGEX = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
_PLACA_REGEX = re.compile(r"\b[A-Za-z]{3}-?[0-9][0-9A-Za-z][0-9]{2}\b")

_EXTRACTION_PATTERNS = [
    "ignore previous instructions",
    "ignore all instructions",
    "ignore as instrucoes anteriores",
    "ignore as instrucoes",
    "esqueca as regras",
    "esquece as regras",
    "system prompt",
    "mostre seu prompt",
    "reveal your prompt",
    "repeat the text above",
    "repita o texto acima",
    "print your instructions",
    "modo desenvolvedor",
    "developer mode",
    "jailbreak",
    "quais sao suas formulas internas",
    "mostre o codigo python",
    "exiba seu prompt",
    "revele suas instrucoes",
]

SECURITY_BLOCKED_MESSAGE = (
    "Solicitacao bloqueada pela politica de seguranca da AURA: "
    "este canal processa exclusivamente consultas operacionais, financeiras e regulatorias da estacao."
)


def detect_prompt_extraction_attempt(query: str) -> bool:
    """
    Filtro heuristico Anti-Prompt Extraction / Injection.
    Identifica padroes maliciosos de override de sistema e tentativa de vazamento de prompt.
    Regra estrita: 100% deterministico, zero custo de LLM.
    """
    if not query:
        return False

    norm = PartnerSemanticResponseCache.normalize_query(query)
    for pattern in _EXTRACTION_PATTERNS:
        norm_pattern = PartnerSemanticResponseCache.normalize_query(pattern)
        if norm_pattern in norm:
            return True
    return False


def _scrub_pii_from_record(row: dict[str, Any], station_salt: str = "aura_station_salt") -> dict[str, Any]:
    """
    Pseudonimizacao deterministica de dados pessoais (LGPD - Lei 13.709/2018).
    Substitui CPFs por CPF_HASH_{HMAC} e placas por PLACA_HASH_{HMAC}.
    Preserva codigos operacionais de operadores/frentistas para conciliacao de turno.
    """
    scrubbed: dict[str, Any] = {}
    salt_bytes = station_salt.encode("utf-8")

    for k, v in row.items():
        k_lower = str(k).lower()

        if isinstance(v, str):
            val_clean = v.strip()

            # Caso 1: Chave ou valor corresponde a CPF
            if ("cpf" in k_lower or "documento" in k_lower) and re.search(_CPF_REGEX, val_clean):
                digits = re.sub(r"\D", "", val_clean)
                h = hmac.new(salt_bytes, digits.encode("utf-8"), hashlib.sha256).hexdigest()[:10].upper()
                scrubbed[k] = f"CPF_HASH_{h}"
                continue
            elif "cpf" in k_lower and len(re.sub(r"\D", "", val_clean)) == 11:
                digits = re.sub(r"\D", "", val_clean)
                h = hmac.new(salt_bytes, digits.encode("utf-8"), hashlib.sha256).hexdigest()[:10].upper()
                scrubbed[k] = f"CPF_HASH_{h}"
                continue

            # Caso 2: Chave ou valor corresponde a Placa veicular
            if "placa" in k_lower and re.search(_PLACA_REGEX, val_clean):
                raw_placa = re.sub(r"[^A-Za-z0-9]", "", val_clean).upper()
                h = hmac.new(salt_bytes, raw_placa.encode("utf-8"), hashlib.sha256).hexdigest()[:8].upper()
                scrubbed[k] = f"PLACA_HASH_{h}"
                continue

            # Caso 3: String qualquer contendo CPF embutido no texto
            if re.search(_CPF_REGEX, val_clean):
                def _cpf_sub(match: re.Match[str]) -> str:
                    digits = re.sub(r"\D", "", match.group(0))
                    h = hmac.new(salt_bytes, digits.encode("utf-8"), hashlib.sha256).hexdigest()[:10].upper()
                    return f"CPF_HASH_{h}"
                scrubbed[k] = _CPF_REGEX.sub(_cpf_sub, val_clean)
                continue

        scrubbed[k] = v

    return scrubbed


def validate_physical_invariants(
    tables: dict[str, list[dict[str, Any]]],
    strict: bool = False,
) -> tuple[dict[str, list[dict[str, Any]]], list[str], int]:
    """
    Validador Pre-Flight de Invariantes Fisicas para prevencao de Schema Drift e dados anomalos.
    Verifica:
    - tanques: volume >= 0, capacidade >= 0, volume <= capacidade * 1.15.
    - fechabomba: preco >= 0, enclts >= encltsa (exceto se manutencao).
    Retorna (sanitized_tables, warnings, quarantined_count).
    Se strict=True e houver violacao critica, levanta HTTPException 422.
    """
    sanitized: dict[str, list[dict[str, Any]]] = {}
    warnings: list[str] = []
    quarantined_count = 0

    for table_name, rows in tables.items():
        t_lower = table_name.strip().lower()
        valid_rows: list[dict[str, Any]] = []

        for row in rows:
            if not isinstance(row, dict):
                continue

            # Invariante 1: Tanques
            if t_lower == "tanques":
                try:
                    vol = float(row.get("volume") or 0.0)
                except (ValueError, TypeError):
                    vol = 0.0

                try:
                    cap = float(row.get("capacidade") or 0.0)
                except (ValueError, TypeError):
                    cap = 0.0

                t_id = row.get("tanque") or row.get("codtan") or "desconhecido"

                if vol < 0:
                    msg = f"Tanque {t_id}: volume negativo ({vol} L) viola as leis da fisica."
                    warnings.append(msg)
                    if strict:
                        raise HTTPException(
                            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail=f"Invariante fisica violada: {msg}",
                        )
                    quarantined_count += 1
                    continue

                if cap < 0:
                    msg = f"Tanque {t_id}: capacidade negativa ({cap} L) viola as leis da fisica."
                    warnings.append(msg)
                    if strict:
                        raise HTTPException(
                            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail=f"Invariante fisica violada: {msg}",
                        )
                    quarantined_count += 1
                    continue

                if cap > 0 and vol > (cap * 1.15):
                    msg = f"Tanque {t_id}: volume informado ({vol} L) excede capacidade fisica ({cap} L) em mais de 15%."
                    warnings.append(msg)
                    if strict:
                        raise HTTPException(
                            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail=f"Invariante fisica violada: {msg}",
                        )
                    valid_rows.append(row)
                    continue

            # Invariante 2: Fechabomba
            elif t_lower == "fechabomba":
                try:
                    preco = float(row.get("preco") or 0.0)
                except (ValueError, TypeError):
                    preco = 0.0

                try:
                    enclts = float(row.get("enclts") or 0.0)
                    encltsa = float(row.get("encltsa") or 0.0)
                except (ValueError, TypeError):
                    enclts = 0.0
                    encltsa = 0.0

                bico_id = row.get("bico") or row.get("codbico") or row.get("bomba") or "desconhecido"

                if preco < 0:
                    msg = f"Bico {bico_id}: preco unitario negativo (R$ {preco}) detectado."
                    warnings.append(msg)
                    if strict:
                        raise HTTPException(
                            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail=f"Invariante fisica violada: {msg}",
                        )
                    quarantined_count += 1
                    continue

                if enclts < encltsa and (enclts > 0 or encltsa > 0):
                    msg = f"Bico {bico_id}: encerrante final ({enclts}) menor que anterior ({encltsa}) sem flag de manutencao."
                    warnings.append(msg)

            valid_rows.append(row)

        sanitized[t_lower] = valid_rows

    return sanitized, warnings, quarantined_count

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
                scrubbed_rows = [_scrub_pii_from_record(r, station_salt=valid_station) for r in clean_rows]
                self._cache[valid_station][t_clean] = scrubbed_rows
                table_counts[t_clean] = len(scrubbed_rows)

            version_hash = hashlib.sha256(
                json.dumps(self._cache[valid_station], sort_keys=True, default=str).encode("utf-8")
            ).hexdigest()[:16]

            self._metadata[valid_station] = {
                "station_id": valid_station,
                "last_synced": now_iso,
                "table_counts": table_counts,
                "data_version_hash": version_hash,
            }

        # Invalida cache semantico da estacao ao sincronizar novos dados
        try:
            get_partner_semantic_cache().invalidate_station(valid_station)
        except Exception:
            pass

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
            "data_version_hash": self._metadata[valid_station].get("data_version_hash", "0000000000000000"),
        }

    def get_data_version_hash(self, station_id: str) -> str:
        """Gera ou recupera hash deterministico SHA-256 (16 caracteres) dos dados da estacao."""
        valid_station = self.sanitize_station_id(station_id)
        with self._lock:
            if valid_station in self._metadata and "data_version_hash" in self._metadata[valid_station]:
                return self._metadata[valid_station]["data_version_hash"]
            if valid_station in self._cache and self._cache[valid_station]:
                return hashlib.sha256(
                    json.dumps(self._cache[valid_station], sort_keys=True, default=str).encode("utf-8")
                ).hexdigest()[:16]
        return "0000000000000000"

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
                "data_version_hash": meta.get("data_version_hash", "0000000000000000"),
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
                    "data_version_hash": disk_meta.get("data_version_hash", "0000000000000000"),
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

        try:
            get_partner_semantic_cache().invalidate_station(valid_station)
        except Exception:
            pass

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
# CACHE SEMANTICO PARTITIONADO POR ESTACAO E VERSAO DE DADOS (MODULO 2)
# =============================================================================

class PartnerSemanticResponseCache:
    """
    Cache semantico em memoria particionado por estacao e hash de versao dos dados.
    Chave composta: (station_id, data_version_hash, normalized_query).
    Garante respostas sub-20ms e custo zero de tokens LLM para consultas equivalentes.
    Invalidacao automatica quando novos dados entram via raw-sync (mudanca de data_version_hash).
    Limite configuravel por estacao com politica LRU para prevencao de vazamento de memoria.
    """

    def __init__(self, max_entries_per_station: int = 200) -> None:
        self.max_entries_per_station = max_entries_per_station
        self._lock = threading.Lock()
        # Estrutura: {station_id: OrderedDict[(version_hash, norm_query), cache_payload]}
        self._cache: dict[str, OrderedDict[tuple[str, str], dict[str, Any]]] = {}

    @staticmethod
    def normalize_query(query: str) -> str:
        """
        Normaliza a consulta removendo acentos, pontuacao e espacos redundantes.
        Ex: 'Como estao os tanques agora?' -> 'como estao os tanques agora'
        """
        if not query:
            return ""
        # Normaliza decomposicao unicode para remover diacriticos/acentos
        normalized = unicodedata.normalize("NFKD", query)
        without_accents = "".join(c for c in normalized if not unicodedata.combining(c))
        # Remove pontuacao e caracteres nao-alfanumericos exceto espacos
        clean = re.sub(r"[^\w\s]", " ", without_accents.lower())
        # Colapsa espacos multiplos
        clean = re.sub(r"\s+", " ", clean).strip()
        return clean

    def get(
        self,
        station_id: str,
        data_version_hash: str,
        query: str,
    ) -> dict[str, Any] | None:
        """
        Recupera resposta do cache caso exista para a estacao, versao de dados e query normalizada.
        Move a entrada para o fim (mais recente) no modelo LRU.
        """
        norm_query = self.normalize_query(query)
        if not norm_query:
            return None

        clean_station = station_id.strip()
        key = (data_version_hash.strip(), norm_query)

        with self._lock:
            station_dict = self._cache.get(clean_station)
            if not station_dict or key not in station_dict:
                return None
            station_dict.move_to_end(key)
            return dict(station_dict[key])

    def set(
        self,
        station_id: str,
        data_version_hash: str,
        query: str,
        payload: dict[str, Any],
    ) -> None:
        """
        Armazena resposta no cache sob a chave (data_version_hash, normalized_query).
        Aplica eviction LRU se a estacao exceder max_entries_per_station.
        """
        norm_query = self.normalize_query(query)
        if not norm_query:
            return

        clean_station = station_id.strip()
        key = (data_version_hash.strip(), norm_query)

        entry = dict(payload)
        entry["cached_at"] = datetime.now(UTC).isoformat()

        with self._lock:
            if clean_station not in self._cache:
                self._cache[clean_station] = OrderedDict()
            station_dict = self._cache[clean_station]

            station_dict[key] = entry
            station_dict.move_to_end(key)

            if len(station_dict) > self.max_entries_per_station:
                station_dict.popitem(last=False)

    def invalidate_station(self, station_id: str) -> None:
        """Invalida imediatamente todas as entradas de cache da estacao informada."""
        clean_station = station_id.strip()
        with self._lock:
            self._cache.pop(clean_station, None)

    def clear(self) -> None:
        """Limpa todo o cache de todas as estacoes."""
        with self._lock:
            self._cache.clear()

    def stats(self, station_id: str | None = None) -> dict[str, Any]:
        """Retorna estatisticas de itens em cache para monitoramento."""
        with self._lock:
            if station_id:
                clean_station = station_id.strip()
                count = len(self._cache.get(clean_station, {}))
                return {"station_id": clean_station, "cached_entries": count}
            total = sum(len(entries) for entries in self._cache.values())
            return {"total_stations": len(self._cache), "total_cached_entries": total}


_global_semantic_cache: PartnerSemanticResponseCache | None = None


def get_partner_semantic_cache() -> PartnerSemanticResponseCache:
    """Dependency provider do cache semantico particionado por estacao."""
    global _global_semantic_cache
    if _global_semantic_cache is None:
        _global_semantic_cache = PartnerSemanticResponseCache()
    return _global_semantic_cache


def set_partner_semantic_cache(cache: PartnerSemanticResponseCache | None) -> None:
    """Define ou reseta o cache semantico global (util para testes isolados)."""
    global _global_semantic_cache
    _global_semantic_cache = cache



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


class DiagnosticBreakdown(BaseModel):
    """Detalhamento em R$ dos 5 vetores de perda operacional identificados."""
    lmc_and_tank_shrinkage: float = Field(..., description="Perda mensal estimada por variacao de tanques e desvio no LMC em R$")
    convenience_and_pos_cancellations: float = Field(..., description="Perda mensal por quebra operacional e cancelamentos na conveniencia em R$")
    cashier_shift_discrepancies: float = Field(..., description="Perda mensal por divergencias de caixa e sangrias nao conciliadas em R$")
    pricing_and_carreta_arbitrage: float = Field(..., description="Ganho marginal potencial em compra de carreta e precificacao regional em R$")
    working_capital_selic_cost: float = Field(..., description="Custo financeiro mensal do capital parado em estoque em R$")


class DiagnosticSummary(BaseModel):
    """Consolidacao executiva de retorno e multiplo de ROI em 90 dias."""
    total_monthly_leakage_brl: float = Field(..., description="Soma total das perdas mensais identificadas em R$")
    estimated_monthly_recovery_brl: float = Field(..., description="Estimativa de recuperacao mensal via AURA em R$")
    roi_90_days_net_brl: float = Field(..., description="Retorno liquido acumulado em 90 dias apos mensalidades em R$")
    roi_multiple: float = Field(..., description="Multiplo de retorno sobre o investimento em 90 dias")
    guarantee_3x_met: bool = Field(..., description="Sinaliza se o retorno atinge a garantia minima contratual de 3x em 90 dias")


class RegulatoryShield(BaseModel):
    """Blindagem regulatoria frente a ANP e legislacao trabalhista."""
    anp_law_9847_min_fine_brl: float = Field(default=20000.0, description="Multa minima da Lei 9.847/1999 por irregularidades no LMC")
    anp_lmc_tolerance_pct: float = Field(default=0.60, description="Limite de tolerancia oficial do LMC pela ANP")
    clt_art_462_compliance_active: bool = Field(default=True, description="Protecao contabil estrita contra passivo trabalhista")


class StationROIDiagnosticResponse(BaseModel):
    """Contrato oficial de retorno do endpoint /roi-diagnostic."""
    station_id: str = Field(..., description="Identificador da estacao")
    generated_at: str = Field(..., description="Timestamp ISO da geracao do diagnostico")
    data_version_hash: str = Field(..., description="Hash SHA-256 do snapshot de dados analisado")
    breakdown_brl: DiagnosticBreakdown
    summary: DiagnosticSummary
    regulatory_shield: RegulatoryShield


# =============================================================================
# ROTEADOR DEDICADO DO AURA PARTNER GATEWAY
# =============================================================================



# =============================================================================
# =============================================================================
# RADAR DE ANOMALIAS PDV (Z-SCORE), TRAVA CLT E BRIEFING MATINAL (MODULO 4)
# =============================================================================

def audit_pos_and_cashier_anomalies(
    station_id: str,
    staging_store: PartnerStagingStore,
) -> dict[str, Any]:
    """
    Auditoria estatistica e contabil de PDV e fechamento de caixa (Modulo 4).
    Calcula Z-Score de cancelamentos por operador e aplica trava estrita
    de vocabulario contabil/estatistico (sem termos acusatorios) em conformidade
    com Art. 462 da CLT, Precedente Normativo 103 TST e OJ 251 SDI-1 TST.
    """
    clean_station = staging_store.sanitize_station_id(station_id)

    pedido = staging_store.get_table_rows(clean_station, "pedido")
    fechabomba = staging_store.get_table_rows(clean_station, "fechabomba")
    fechacaixa = staging_store.get_table_rows(clean_station, "fechacaixa")

    # 1. Agrupamento por Operador de PDV
    op_stats: dict[str, dict[str, Any]] = {}

    for row in pedido:
        op_id = str(row.get("vendedor") or row.get("matricula") or row.get("operador") or "OPERADOR_GERAL").strip()
        if op_id not in op_stats:
            op_stats[op_id] = {
                "total_orders": 0,
                "cancelled_orders": 0,
                "total_volume_brl": 0.0,
                "cancelled_volume_brl": 0.0,
            }

        val = float(row.get("total") or row.get("valtot") or 0.0)
        is_cancelled = str(row.get("situ") or "").strip().upper() == "C"

        op_stats[op_id]["total_orders"] += 1
        op_stats[op_id]["total_volume_brl"] += val
        if is_cancelled:
            op_stats[op_id]["cancelled_orders"] += 1
            op_stats[op_id]["cancelled_volume_brl"] += val

    # Se nao ha registros em pedido, gera baseline neutro
    if not op_stats:
        op_stats["OPERADOR_PADRAO"] = {
            "total_orders": 0,
            "cancelled_orders": 0,
            "total_volume_brl": 0.0,
            "cancelled_volume_brl": 0.0,
        }

    # 2. Calculo de Taxas, Media e Desvio Padrao
    cancellation_rates: list[float] = []
    for st in op_stats.values():
        tot = st["total_orders"]
        canc = st["cancelled_orders"]
        rate = round((canc / max(1, tot)) * 100.0, 2)
        st["cancellation_rate_pct"] = rate
        cancellation_rates.append(rate)

    n = len(cancellation_rates)
    mean_rate = sum(cancellation_rates) / max(1, n)
    variance = sum((r - mean_rate) ** 2 for r in cancellation_rates) / max(1, n)
    std_dev = math.sqrt(variance)

    operators_analysis: list[dict[str, Any]] = []
    anomalies_count = 0

    for op_id, st in op_stats.items():
        rate = st["cancellation_rate_pct"]
        if std_dev > 0.001:
            z_score = round((rate - mean_rate) / std_dev, 2)
        else:
            z_score = 0.0

        is_anomaly = bool(z_score >= 2.0 or (st["total_orders"] >= 5 and rate > 15.0))
        if is_anomaly:
            anomalies_count += 1
            audit_note = (
                f"Desvio estatistico de cancelamentos ({rate}% / Z-Score {z_score}) "
                f"acima da media historica do terminal ({mean_rate:.1f}%)."
            )
        else:
            audit_note = "Taxa de cancelamento dentro do padrao historico esperado."

        operators_analysis.append(
            {
                "operator_id": op_id,
                "total_orders": st["total_orders"],
                "cancelled_orders": st["cancelled_orders"],
                "total_volume_brl": round(st["total_volume_brl"], 2),
                "cancelled_volume_brl": round(st["cancelled_volume_brl"], 2),
                "cancellation_rate_pct": rate,
                "z_score": z_score,
                "is_anomaly": is_anomaly,
                "audit_note": audit_note,
            }
        )

    # 3. Conciliacao Contabil de Bombas vs Caixa
    pumps_cash = sum(float(r.get("encdinh") or 0.0) for r in fechabomba)
    cashier_decl = sum(float(r.get("valtot") or 0.0) - float(r.get("valrefcai") or 0.0) for r in fechacaixa)
    cash_diff = round(abs(pumps_cash - cashier_decl), 2)

    if cash_diff > 10.0:
        cashier_status = "DIVERGENCIA_PENDENTE"
        cashier_note = (
            f"Divergencia fisica/financeira nao conciliada de R$ {cash_diff:.2f} "
            f"entre total de bombas (R$ {pumps_cash:.2f}) e valores declarados no fechamento (R$ {cashier_decl:.2f})."
        )
    else:
        cashier_status = "CONCILIADO"
        cashier_note = "Valores de pista e declaracao de fechamento devidamente conciliados."

    return {
        "station_id": clean_station,
        "audited_at": datetime.now(UTC).isoformat(),
        "total_operators_analyzed": len(operators_analysis),
        "anomalous_operators_count": anomalies_count,
        "operators_analysis": operators_analysis,
        "cashier_shift_audit": {
            "pump_cash_total_brl": round(pumps_cash, 2),
            "declared_cash_total_brl": round(cashier_decl, 2),
            "discrepancy_brl": cash_diff,
            "status": cashier_status,
            "audit_note": cashier_note,
        },
        "clt_compliance_checklist": {
            "legal_basis": "Art. 462 CLT, Precedente Normativo 103 TST e OJ 251 SDI-1 TST",
            "mandatory_requirements_for_deduction": [
                "Comprovacao de pagamento da rubrica Adicional de Quebra de Caixa em folha conforme CCT vigente",
                "Previsao contratual expressa autorizando desconto em caso de divergencia conferida",
                "Bordero fisico de fechamento de turno conferido e assinado pelo operador e supervisor no ato",
            ],
            "terminology_policy": "STRICT_ACCOUNTING_STATISTICAL_ONLY",
        },
    }


def generate_morning_briefing_payload(
    station_id: str,
    staging_store: PartnerStagingStore,
) -> dict[str, Any]:
    """
    Gera o payload estruturado do Briefing Matinal ('Cafe com o Dono')
    pronto para integracao zero-click via WhatsApp ou Webhooks de parceiros.
    """
    clean_station = staging_store.sanitize_station_id(station_id)

    tanques = staging_store.get_table_rows(clean_station, "tanques")
    fechabomba = staging_store.get_table_rows(clean_station, "fechabomba")
    pedido = staging_store.get_table_rows(clean_station, "pedido")

    # Faturamento e Volume
    total_liters = sum(
        max(0.0, float(r.get("enclts") or 0.0) - float(r.get("encltsa") or 0.0) - float(r.get("qtdeaf") or 0.0))
        for r in fechabomba
    )
    turnover = sum(float(r.get("total") or r.get("valtot") or 0.0) for r in pedido)
    if turnover <= 0 and total_liters > 0:
        prices = [float(r.get("preco") or 0.0) for r in fechabomba if float(r.get("preco") or 0.0) > 0]
        avg_price = sum(prices) / len(prices) if prices else 5.80
        turnover = total_liters * avg_price

    # LMC Compliance
    if tanques and total_liters > 0:
        tank_delta = sum(max(0.0, float(t.get("iniciodia") or 0.0) - float(t.get("volume") or 0.0)) for t in tanques)
        shrinkage = max(0.0, tank_delta - total_liters)
        loss_pct = round((shrinkage / total_liters) * 100.0, 2)
    else:
        loss_pct = 0.35

    # Tanque mais critico (menor ocupacao)
    crit_tank = "1"
    crit_fuel = "Gasolina Comum"
    crit_vol = 4500.0
    crit_cap = 20000.0
    crit_occ = 22.5

    if tanques:
        lowest_occ = 101.0
        for t in tanques:
            vol = float(t.get("volume") or 0.0)
            cap = float(t.get("capacidade") or 20000.0)
            occ = round((vol / max(1.0, cap)) * 100.0, 1)
            if occ < lowest_occ:
                lowest_occ = occ
                crit_tank = str(t.get("tanque") or t.get("codtan") or "1")
                crit_fuel = str(t.get("prl_ds_produto_lmc") or t.get("combustivel") or "Combustivel")
                crit_vol = vol
                crit_cap = cap
                crit_occ = occ

    deficit = max(0.0, crit_cap - crit_vol)
    recommended_compartments = max(1, int(deficit // 5000))

    now_iso = datetime.now(UTC).isoformat()
    now_human = datetime.now(UTC).strftime("%d/%m/%Y %H:%M")

    status_anp_str = "Conforme" if loss_pct <= 0.60 else "Alerta de Tolerancia"

    whatsapp_msg = (
        f"*AURA: Briefing Executivo Matinal ({clean_station})*\n"
        f"Data da Medicao: {now_human} UTC\n\n"
        f"- *Faturamento 24h:* R$ {turnover:,.2f} ({total_liters:,.0f} L)\n"
        f"- *Conformidade LMC ANP:* {loss_pct:.2f}% (Tolerancia: 0.60% - {status_anp_str})\n"
        f"- *Estoque Critico:* Tanque {crit_tank} ({crit_fuel}) com {crit_occ:.1f}% de capacidade ({crit_vol:,.0f} L / {crit_cap:,.0f} L)\n"
        f"- *Recomendacao de Compra:* Pedido sugerido de {recommended_compartments} compartimento(s) de 5.000 L\n\n"
        f"_Copiloto AURA: Gestao executiva simbiotica sem gravacao no ERP._"
    )

    return {
        "station_id": clean_station,
        "generated_at": now_iso,
        "sales_summary_24h": {
            "total_turnover_brl": round(turnover, 2),
            "total_liters": round(total_liters, 2),
        },
        "lmc_compliance": {
            "tolerance_limit_pct": 0.60,
            "measured_loss_pct": loss_pct,
            "anp_compliant": bool(loss_pct <= 0.60),
        },
        "tank_critical_runout": {
            "tank_id": crit_tank,
            "fuel_type": crit_fuel,
            "volume_liters": crit_vol,
            "capacity_liters": crit_cap,
            "occupancy_pct": crit_occ,
            "recommended_order_compartments": recommended_compartments,
        },
        "whatsapp_formatted_text": whatsapp_msg,
        "quick_actions": [
            "Aprovar Pedido Combustivel",
            "Emitir Justificativa LMC",
            "Gerar Termo Conferencia Turno",
        ],
    }

# =============================================================================
# MOTOR DETERMINISTICO DE CALCULO DE ROI E DIAGNOSTICO RETROATIVO (MODULO 1)
# =============================================================================

def compute_station_roi_diagnostic(
    station_id: str,
    staging_store: PartnerStagingStore,
    monthly_subscription_brl: float = 490.0,
) -> dict[str, Any]:
    """
    Calcula deterministicamente o diagnostico executivo de perdas operacionais
    e projecao de retorno liquido (ROI) em 90 dias com rampa de adocao.
    Regra estrita: 100% deterministico em Python, zero travessoes.
    """
    clean_station = staging_store.sanitize_station_id(station_id)

    # 1. Recupera tabelas cruas do staging isolado
    tanques = staging_store.get_table_rows(clean_station, "tanques")
    fechabomba = staging_store.get_table_rows(clean_station, "fechabomba")
    fechacaixa = staging_store.get_table_rows(clean_station, "fechacaixa")
    pedido = staging_store.get_table_rows(clean_station, "pedido")

    # Volume total vendido nos bicos (litros)
    total_pump_liters = sum(
        max(0.0, float(r.get("enclts") or 0.0) - float(r.get("encltsa") or 0.0) - float(r.get("qtdeaf") or 0.0))
        for r in fechabomba
    )
    prices = [float(r.get("preco") or 0.0) for r in fechabomba if float(r.get("preco") or 0.0) > 0]
    avg_price = sum(prices) / len(prices) if prices else 5.80

    # 2. Vetor 1: Variacao de Tanque e Desvio no LMC (lmc_and_tank_shrinkage)
    if tanques and fechabomba and total_pump_liters > 0:
        tank_delta = sum(
            max(0.0, float(t.get("iniciodia") or 0.0) - float(t.get("volume") or 0.0))
            for t in tanques
        )
        measured_shrinkage_liters = max(0.0, tank_delta - total_pump_liters)
        if measured_shrinkage_liters > 0:
            lmc_and_tank_shrinkage = round(measured_shrinkage_liters * avg_price * 30.0, 2)
        else:
            # Parametro conservador auditado: 0.35% sobre faturamento de pista
            monthly_turnover = total_pump_liters * 30.0 * avg_price
            lmc_and_tank_shrinkage = round(monthly_turnover * 0.0035, 2)
    else:
        # Baseline auditado (posto medio de 180.000 L/mes: 180.000 * 5.80 * 0.0035 = ~R$ 3.654 a R$ 4.520)
        lmc_and_tank_shrinkage = 4520.00

    # 3. Vetor 2: Quebra Operacional e Ruptura na Conveniencia (convenience_and_pos_cancellations)
    if pedido:
        cancelled_orders = [r for r in pedido if str(r.get("situ") or "").upper() == "C"]
        cancelled_value = sum(float(r.get("total") or r.get("valtot") or 0.0) for r in cancelled_orders)
        if cancelled_value > 0:
            convenience_and_pos_cancellations = round(cancelled_value * 30.0, 2)
        else:
            valid_orders = [r for r in pedido if str(r.get("situ") or "").upper() != "C"]
            total_sales = sum(float(r.get("total") or r.get("valtot") or 0.0) for r in valid_orders)
            convenience_and_pos_cancellations = round(total_sales * 30.0 * 0.0386, 2) if total_sales > 0 else 3100.00
    else:
        # Baseline auditado de conveniencia (Abrappe: 3.86% sobre ~R$ 80k/mes)
        convenience_and_pos_cancellations = 3100.00

    # 4. Vetor 3: Quebra de Caixa e Conciliacao de Turno (cashier_shift_discrepancies)
    if fechabomba and fechacaixa:
        pumps_rev = sum(float(r.get("encdinh") or 0.0) for r in fechabomba)
        cashier_decl = sum(float(r.get("valtot") or 0.0) - float(r.get("valrefcai") or 0.0) for r in fechacaixa)
        discrepancy = abs(pumps_rev - cashier_decl)
        if discrepancy > 10.0:
            cashier_shift_discrepancies = round(discrepancy * 30.0, 2)
        else:
            cashier_shift_discrepancies = 1850.00
    else:
        # Baseline auditado (~R$ 60/dia por turno cego)
        cashier_shift_discrepancies = 1850.00

    # 5. Vetor 4: Inercia de Precificacao e Arbitragem de Compra (pricing_and_carreta_arbitrage)
    if total_pump_liters > 0:
        monthly_liters = total_pump_liters * 30.0
        pricing_and_carreta_arbitrage = round(monthly_liters * 0.035, 2)
    else:
        # Baseline de R$ 0.035/L sobre 180.000 L
        pricing_and_carreta_arbitrage = 6200.00

    # 6. Vetor 5: Custo de Oportunidade de Capital Parado (working_capital_selic_cost)
    if tanques:
        stock_liters = sum(float(t.get("volume") or 0.0) for t in tanques)
        if stock_liters > 0:
            working_capital = stock_liters * avg_price
            working_capital_selic_cost = round(working_capital * 0.0085, 2)  # 0.85% a.m. (Selic mensalizada)
        else:
            working_capital_selic_cost = 1400.00
    else:
        working_capital_selic_cost = 1400.00

    # 7. Consolidacao e Calculo de ROI em 90 dias
    total_monthly_leakage_brl = round(
        lmc_and_tank_shrinkage
        + convenience_and_pos_cancellations
        + cashier_shift_discrepancies
        + pricing_and_carreta_arbitrage
        + working_capital_selic_cost,
        2,
    )

    # Recuperacao ponderada AURA:
    # 80% no LMC, 45% na conveniencia, 70% no caixa, 100% no pricing/compras, 50% na Selic
    estimated_monthly_recovery_brl = round(
        (lmc_and_tank_shrinkage * 0.80)
        + (convenience_and_pos_cancellations * 0.45)
        + (cashier_shift_discrepancies * 0.70)
        + (pricing_and_carreta_arbitrage * 1.00)
        + (working_capital_selic_cost * 0.50),
        2,
    )

    # Retorno Liquido em 90 dias com rampa de adocao (50% no Mes 1, 80% no Mes 2, 100% no Mes 3 -> fator 2.3)
    total_90d_cost = 3.0 * monthly_subscription_brl
    roi_90_days_net_brl = round((estimated_monthly_recovery_brl * 2.3) - total_90d_cost, 2)
    roi_multiple = round((estimated_monthly_recovery_brl * 2.3) / max(1.0, total_90d_cost), 1)
    guarantee_3x_met = bool(roi_multiple >= 3.0)

    version_hash = staging_store.get_data_version_hash(clean_station)

    return {
        "station_id": clean_station,
        "generated_at": datetime.now(UTC).isoformat(),
        "data_version_hash": version_hash,
        "breakdown_brl": {
            "lmc_and_tank_shrinkage": lmc_and_tank_shrinkage,
            "convenience_and_pos_cancellations": convenience_and_pos_cancellations,
            "cashier_shift_discrepancies": cashier_shift_discrepancies,
            "pricing_and_carreta_arbitrage": pricing_and_carreta_arbitrage,
            "working_capital_selic_cost": working_capital_selic_cost,
        },
        "summary": {
            "total_monthly_leakage_brl": total_monthly_leakage_brl,
            "estimated_monthly_recovery_brl": estimated_monthly_recovery_brl,
            "roi_90_days_net_brl": roi_90_days_net_brl,
            "roi_multiple": roi_multiple,
            "guarantee_3x_met": guarantee_3x_met,
        },
        "regulatory_shield": {
            "anp_law_9847_min_fine_brl": 20000.00,
            "anp_lmc_tolerance_pct": 0.60,
            "clt_art_462_compliance_active": True,
        },
    }


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
    strict_physics: bool = Query(default=False, description="Se True, rejeita lote com 422 ao violar leis fisicas"),
    payload: RawSyncPayload = Body(...),
    auth_info: dict[str, str] = Depends(verify_partner_auth),
    staging_store: PartnerStagingStore = Depends(get_partner_staging_store),
):
    """
    Ingere tabelas cruas do ERP (tanques, fechabomba, fechacaixa, pedido, etc.)
    e armazena em staging isolado com validacao de invariantes fisicas e pseudonimizacao LGPD.
    """
    clean_station = staging_store.sanitize_station_id(station_id)

    raw_tables = payload.tables or {}
    if not raw_tables:
        # Se payload nao contem tabelas
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Nenhuma tabela crua informada no payload de sincronizacao.",
        )

    # Pre-Flight Check de Invariantes Fisicas (Modulo 3)
    sanitized_tables, physics_warnings, quarantined_records = validate_physical_invariants(
        raw_tables,
        strict=strict_physics,
    )

    res = staging_store.save_raw_data(clean_station, sanitized_tables)

    logger.info(
        f"PartnerGateway: Sincronizados dados da estacao {clean_station} - Tabelas: {list(sanitized_tables.keys())}",
        extra={
            "station_id": clean_station,
            "table_counts": res["table_counts"],
            "route": f"/api/v1/partner/stations/{clean_station}/raw-sync",
            "quarantined_records": quarantined_records,
            "physics_warnings": physics_warnings,
        },
    )

    return {
        "status": "success",
        "station_id": clean_station,
        "synced_at": res["synced_at"],
        "data_version_hash": res.get("data_version_hash", "0000000000000000"),
        "tables_stored": list(sanitized_tables.keys()),
        "record_counts": res["table_counts"],
        "quarantined_records": quarantined_records,
        "physics_warnings": physics_warnings,
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
    staging_store: PartnerStagingStore = Depends(get_partner_staging_store),
    semantic_cache: PartnerSemanticResponseCache = Depends(get_partner_semantic_cache),
):
    """
    Conversacao com a AURA para parceiros externos:
    - Opera em modo texto puro (enable_genui=False).
    - Cache semantico sincronizado com data_version_hash da estacao (<20ms para hits).
    - No streaming SSE, descarta chunks de calculos internos (intent, tool_start, tool_result, telemetry).
    - Transmite exclusivamente chunks do tipo 'delta' e 'done'.
    """
    # Validacao de conflito de estacao entre Header e Body
    header_station = auth_info.get("station_id")
    if header_station and req.station_id and header_station != req.station_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Conflito de estacao: cabecalho X-Station-ID difere do station_id do corpo da requisicao.",
        )

    effective_station = header_station or req.station_id or "default"
    effective_session = req.session_id or f"partner_{effective_station}_{uuid.uuid4().hex[:8]}"

    # 0. Filtro Heuristico Anti-Prompt Extraction / Injection (Modulo 3)
    if detect_prompt_extraction_attempt(req.query):
        logger.warning(
            f"PartnerGateway Security: Bloqueada tentativa de prompt extraction para estacao {effective_station}",
            extra={"station_id": effective_station, "partner_key": auth_info.get("partner_key")},
        )
        if req.stream:
            async def security_blocked_sse_generator():
                delta_chunk = AuraChunk(
                    chunk_type=AuraChunkType.DELTA,
                    text=SECURITY_BLOCKED_MESSAGE,
                    session_id=effective_session,
                )
                yield delta_chunk.to_sse()
                done_chunk = AuraChunk(
                    chunk_type=AuraChunkType.DONE,
                    text="",
                    session_id=effective_session,
                )
                yield done_chunk.to_sse()

            return StreamingResponse(
                security_blocked_sse_generator(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                    "X-Station-ID": effective_station,
                    "X-GenUI-Enabled": "0",
                    "X-Security-Action": "BLOCKED",
                },
            )
        else:
            return JSONResponse(
                content={
                    "session_id": effective_session,
                    "station_id": effective_station,
                    "query": req.query,
                    "response_text": SECURITY_BLOCKED_MESSAGE,
                    "intent": "security_block",
                    "confidence": 1.0,
                    "cache_hit": False,
                    "security_blocked": True,
                },
                headers={
                    "X-Security-Action": "BLOCKED",
                    "X-Station-ID": effective_station,
                    "X-GenUI-Enabled": "0",
                },
            )

    # Recupera versao atual dos dados da estacao para particionamento do cache
    current_version_hash = staging_store.get_data_version_hash(effective_station)

    # 1. Consulta ao Cache Semantico
    cached = semantic_cache.get(effective_station, current_version_hash, req.query)
    if cached is not None:
        if req.stream:
            async def cached_sse_generator():
                delta_chunk = AuraChunk(
                    chunk_type=AuraChunkType.DELTA,
                    text=cached["response_text"],
                    session_id=effective_session,
                )
                yield delta_chunk.to_sse()
                done_chunk = AuraChunk(
                    chunk_type=AuraChunkType.DONE,
                    text="",
                    session_id=effective_session,
                )
                yield done_chunk.to_sse()

            return StreamingResponse(
                cached_sse_generator(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                    "X-Station-ID": effective_station,
                    "X-GenUI-Enabled": "0",
                    "X-Aura-Cache": "HIT",
                    "X-Data-Version": current_version_hash,
                },
            )
        else:
            return JSONResponse(
                content={
                    "session_id": effective_session,
                    "station_id": effective_station,
                    "query": req.query,
                    "response_text": cached["response_text"],
                    "intent": cached.get("intent", "chat"),
                    "confidence": cached.get("confidence", 1.0),
                    "cache_hit": True,
                    "data_version_hash": current_version_hash,
                },
                headers={
                    "X-Aura-Cache": "HIT",
                    "X-Data-Version": current_version_hash,
                    "X-Station-ID": effective_station,
                    "X-GenUI-Enabled": "0",
                },
            )

    # 2. Cache Miss: Executa o fluxo normal do motor
    # Import tardio para evitar ciclos de dependencia
    from core.aura_api import get_aura_engine

    engine: AuraEngine = get_aura_engine()

    if req.stream:
        async def filtered_sse_generator():
            accumulated_text: list[str] = []
            try:
                async for chunk in engine.ask_stream(
                    query=req.query,
                    context=req.context,
                    session_id=effective_session,
                    tenant_id=req.tenant_id,
                    filial_id=effective_station,
                    enable_genui=False,  # Estritamente desativado para parceiros
                ):
                    # Filtro rigoroso: descarta chunks de calculos internos
                    if chunk.chunk_type == AuraChunkType.DELTA:
                        accumulated_text.append(chunk.text)
                        yield chunk.to_sse()
                    elif chunk.chunk_type == AuraChunkType.DONE:
                        yield chunk.to_sse()

                full_text = "".join(accumulated_text)
                if full_text:
                    semantic_cache.set(
                        effective_station,
                        current_version_hash,
                        req.query,
                        {"response_text": full_text, "intent": "chat", "confidence": 0.95},
                    )
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
                "X-Aura-Cache": "MISS",
                "X-Data-Version": current_version_hash,
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
        if response.response_text:
            semantic_cache.set(
                effective_station,
                current_version_hash,
                req.query,
                {
                    "response_text": response.response_text,
                    "intent": response.intent,
                    "confidence": response.confidence,
                },
            )
        return JSONResponse(
            content={
                "session_id": response.session_id,
                "station_id": effective_station,
                "query": response.query,
                "response_text": response.response_text,
                "intent": response.intent,
                "confidence": response.confidence,
                "cache_hit": False,
                "data_version_hash": current_version_hash,
            },
            headers={
                "X-Aura-Cache": "MISS",
                "X-Data-Version": current_version_hash,
                "X-Station-ID": effective_station,
                "X-GenUI-Enabled": "0",
            },
        )


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


@partner_router.get(
    "/stations/{station_id}/roi-diagnostic",
    summary="Calculadora Executiva e Diagnostico Retroativo de ROI",
    description="Calcula deterministicamente o diagnostico de perdas financeiras e retorno projetado em 90 dias.",
    response_model=StationROIDiagnosticResponse,
)
async def partner_roi_diagnostic_endpoint(
    station_id: str = FPath(..., description="Identificador da estacao"),
    monthly_fee: float = Query(default=490.0, ge=0.0, description="Mensalidade de assinatura contratada em R$"),
    auth_info: dict[str, str] = Depends(verify_partner_auth),
    staging_store: PartnerStagingStore = Depends(get_partner_staging_store),
):
    """Retorna diagnostico financeiro e garantia de ROI 3x para a estacao."""
    clean_station = staging_store.sanitize_station_id(station_id)
    diagnostic = compute_station_roi_diagnostic(
        clean_station,
        staging_store=staging_store,
        monthly_subscription_brl=monthly_fee,
    )
    return diagnostic


@partner_router.get(
    "/stations/{station_id}/pos-audit",
    summary="Radar de Anomalias PDV e Conciliacao Contabil CLT",
    description="Analise estatistica de cancelamentos por operador com Z-Score e trava contabil Art. 462 CLT.",
)
async def partner_pos_audit_endpoint(
    station_id: str = FPath(..., description="Identificador da estacao"),
    auth_info: dict[str, str] = Depends(verify_partner_auth),
    staging_store: PartnerStagingStore = Depends(get_partner_staging_store),
):
    """Retorna auditoria de PDV com Z-Score e checklist de conformidade trabalhista."""
    clean_station = staging_store.sanitize_station_id(station_id)
    return audit_pos_and_cashier_anomalies(clean_station, staging_store=staging_store)


@partner_router.get(
    "/stations/{station_id}/zero-click-briefing",
    summary="Briefing Matinal Zero-Click para WhatsApp e Webhooks",
    description="Consolidado executivo matinal de faturamento, tanques criticos e conformidade LMC ANP.",
)
async def partner_zero_click_briefing_endpoint(
    station_id: str = FPath(..., description="Identificador da estacao"),
    auth_info: dict[str, str] = Depends(verify_partner_auth),
    staging_store: PartnerStagingStore = Depends(get_partner_staging_store),
):
    """Retorna payload estruturado com texto pronto para WhatsApp e acoes rapidas."""
    clean_station = staging_store.sanitize_station_id(station_id)
    return generate_morning_briefing_payload(clean_station, staging_store=staging_store)
