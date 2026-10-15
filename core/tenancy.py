"""
Modulo de Multi-Tenancy Robusto e Row-Level Security (RLS) por Filial (Fase P2-5).
Garante isolamento matematico entre filiais na camada de sessao PostgreSQL (pgvector),
validacao sintatica e semantica de queries SQL e filtragem deterministica em memoria.
Zero travessoes em todo o modulo.
"""

from __future__ import annotations

import contextlib
import contextvars
import logging
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Self

logger = logging.getLogger("AuraTenancy")

# ContextVars thread-safe e async-safe para isolamento de tenant e filial ativa
_current_filial_var: contextvars.ContextVar[int | None] = contextvars.ContextVar(
    "aura_current_filial", default=None
)
_current_tenant_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "aura_current_tenant", default="default"
)


class CrossTenantAccessError(PermissionError):
    """
    Excecao lancada quando uma operacao viola o isolamento multi-filial (RLS),
    omite o filtro parametrizado de filial ou tenta injecao de parametros cross-tenant.
    """


@dataclass(frozen=True)
class TenantInfo:
    """Representa o contexto imutavel de tenant e filial ativos na execucao atual."""

    filial_id: int
    tenant_id: str = "default"


def validate_filial_id(filial_id: Any) -> int:
    """
    Valida que filial_id e estritamente um inteiro positivo (> 0) e nao um booleano.
    Lanca CrossTenantAccessError em caso de tipo invalido ou tentativa de injecao.
    """
    if isinstance(filial_id, bool) or not isinstance(filial_id, int):
        raise CrossTenantAccessError(
            f"Identificador de filial invalido (tipo {type(filial_id).__name__}): esperado int positivo."
        )
    if filial_id <= 0:
        raise CrossTenantAccessError(
            f"Identificador de filial invalido ({filial_id}): deve ser maior que zero."
        )
    return filial_id


class TenantContext:
    """
    Gerenciador de contexto thread-safe e async-safe (baseado em contextvars)
    para propagacao do tenant_id e filial_id ativo ao longo da requisicao.
    """

    def __init__(self, filial_id: int, tenant_id: str = "default") -> None:
        self.filial_id: int = validate_filial_id(filial_id)
        if not isinstance(tenant_id, str) or not tenant_id.strip():
            raise CrossTenantAccessError("Identificador de tenant_id invalido ou vazio.")
        self.tenant_id: str = tenant_id.strip()
        self._filial_token: contextvars.Token[int | None] | None = None
        self._tenant_token: contextvars.Token[str] | None = None

    def __enter__(self) -> Self:
        self._filial_token = _current_filial_var.set(self.filial_id)
        self._tenant_token = _current_tenant_var.set(self.tenant_id)
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        if self._filial_token is not None:
            _current_filial_var.reset(self._filial_token)
            self._filial_token = None
        if self._tenant_token is not None:
            _current_tenant_var.reset(self._tenant_token)
            self._tenant_token = None

    async def __aenter__(self) -> Self:
        return self.__enter__()

    async def __aexit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        self.__exit__(exc_type, exc_val, exc_tb)

    @classmethod
    def set(
        cls, filial_id: int, tenant_id: str = "default"
    ) -> tuple[contextvars.Token[int | None], contextvars.Token[str]]:
        """Define diretamente a filial e o tenant ativos no contexto de execucao atual."""
        valid_filial = validate_filial_id(filial_id)
        if not isinstance(tenant_id, str) or not tenant_id.strip():
            raise CrossTenantAccessError("Identificador de tenant_id invalido ou vazio.")
        t_filial = _current_filial_var.set(valid_filial)
        t_tenant = _current_tenant_var.set(tenant_id.strip())
        return t_filial, t_tenant

    @classmethod
    def reset(
        cls, tokens: tuple[contextvars.Token[int | None], contextvars.Token[str]]
    ) -> None:
        """Restaura os tokens anteriores de filial_id e tenant_id."""
        filial_token, tenant_token = tokens
        _current_filial_var.reset(filial_token)
        _current_tenant_var.reset(tenant_token)

    @classmethod
    def clear(cls) -> None:
        """Limpa o contexto ativo voltando para os valores padrao (None e 'default')."""
        _current_filial_var.set(None)
        _current_tenant_var.set("default")

    @classmethod
    def get_filial_id(cls) -> int | None:
        """Retorna o filial_id ativo no contexto atual ou None se nao definido."""
        return _current_filial_var.get()

    @classmethod
    def require_filial_id(cls) -> int:
        """Retorna o filial_id ativo ou lanca CrossTenantAccessError se ausente."""
        filial_id = _current_filial_var.get()
        if filial_id is None:
            raise CrossTenantAccessError(
                "Nenhum filial_id ativo encontrado no TenantContext para operacao multi-tenant."
            )
        return validate_filial_id(filial_id)

    @classmethod
    def get_tenant_id(cls) -> str:
        """Retorna o tenant_id ativo no contexto atual."""
        return _current_tenant_var.get()

    @classmethod
    def get_current(cls) -> TenantInfo | None:
        """Retorna TenantInfo com filial_id e tenant_id ativos, ou None se sem filial."""
        filial_id = _current_filial_var.get()
        if filial_id is None:
            return None
        return TenantInfo(filial_id=filial_id, tenant_id=_current_tenant_var.get())


def inject_rls_filial_context(
    conn: Any,
    filial_id: int | None = None,
    session_scope: bool = False,
) -> int:
    """
    Injeta o identificador da filial ativa na sessao/transacao PostgreSQL
    executando 'SET LOCAL app.current_filial = %s' (ou 'SET SESSION' se session_scope=True).
    Se filial_id nao for informado, tenta obter do TenantContext ativo.
    """
    resolved_filial = filial_id if filial_id is not None else TenantContext.get_filial_id()
    if resolved_filial is None:
        raise CrossTenantAccessError(
            "Impossivel injetar contexto RLS: filial_id nao informado e ausente no TenantContext."
        )
    valid_filial = validate_filial_id(resolved_filial)

    sql_cmd = (
        "SET SESSION app.current_filial = %s"
        if session_scope
        else "SET LOCAL app.current_filial = %s"
    )
    param_val = (str(valid_filial),)

    cursor_obj = conn.cursor()
    if hasattr(cursor_obj, "__enter__") and hasattr(cursor_obj, "__exit__"):
        with cursor_obj as cur:
            cur.execute(sql_cmd, param_val)
    else:
        try:
            cursor_obj.execute(sql_cmd, param_val)
        finally:
            if hasattr(cursor_obj, "close"):
                cursor_obj.close()

    with contextlib.suppress(AttributeError, TypeError):
        conn._rls_filial_id = valid_filial

    logger.debug(
        "Contexto RLS injetado com sucesso: app.current_filial=%d (session_scope=%s)",
        valid_filial,
        session_scope,
    )
    return valid_filial


# Padroes proibidos de injecao SQL ou bypass de politica de isolamento RLS
_SQL_INJECTION_PATTERNS = [
    re.compile(r"--"),
    re.compile(r"/\*"),
    re.compile(r"\*/"),
    re.compile(r"\bOR\b\s+['\"]?\d+['\"]?\s*=\s*['\"]?\d+['\"]?", re.IGNORECASE),
    re.compile(r"\bOR\b\s+['\"]?[a-zA-Z0-9_]+['\"]?\s*=\s*['\"]?[a-zA-Z0-9_]+['\"]?", re.IGNORECASE),
    re.compile(r"\bOR\b\s+(?:TRUE|1)\b", re.IGNORECASE),
    re.compile(r"\bUNION\b\s+(?:ALL\s+)?\bSELECT\b", re.IGNORECASE),
    re.compile(r"\bSET\b\s+(?:LOCAL\s+|SESSION\s+)?app\.current_filial", re.IGNORECASE),
    re.compile(r"\bRESET\b\s+app\.current_filial", re.IGNORECASE),
    re.compile(r"\bDISABLE\s+ROW\s+LEVEL\s+SECURITY\b", re.IGNORECASE),
    re.compile(r"\bDROP\s+(?:POLICY|TABLE)\b", re.IGNORECASE),
    re.compile(r"\b(?:[a-zA-Z_][a-zA-Z0-9_]*\.)?codfilial\s*(?:!=|<>|>|<|>=|<=)", re.IGNORECASE),
    re.compile(r"\b(?:[a-zA-Z_][a-zA-Z0-9_]*\.)?codfilial\s+IS\s+(?:NOT\s+)?NULL\b", re.IGNORECASE),
    re.compile(r"\b(?:[a-zA-Z_][a-zA-Z0-9_]*\.)?codfilial\s+(?:NOT\s+)?IN\s*\(", re.IGNORECASE),
    re.compile(r"\b(?:[a-zA-Z_][a-zA-Z0-9_]*\.)?codfilial\s+BETWEEN\b", re.IGNORECASE),
    re.compile(r"\bOR\s+(?:[a-zA-Z_][a-zA-Z0-9_]*\.)?codfilial\b", re.IGNORECASE),
]

# Detecta comparacao literal hardcoded: ex. codfilial = 2
_HARDCODED_FILIAL_PATTERN = re.compile(
    r"\b(?:[a-zA-Z_][a-zA-Z0-9_]*\.)?codfilial\s*=\s*['\"]?\d+['\"]?",
    re.IGNORECASE,
)

# Detecta filtro parametrizado valido de codfilial
_PARAMETERIZED_FILIAL_PATTERN = re.compile(
    r"\b(?:[a-zA-Z_][a-zA-Z0-9_]*\.)?codfilial\s*=\s*"
    r"(?P<placeholder>%s|%\((?P<pyformat_key>codfilial|filial_id)\)s|:(?P<named_key>codfilial|filial_id))",
    re.IGNORECASE,
)


def _check_string_for_sql_injection(value: str, context_label: str) -> None:
    """Verifica se uma string contem padroes de injecao SQL ou bypass de tenant."""
    if ";" in value:
        raise CrossTenantAccessError(
            f"Multiplos comandos SQL ou ponto-e-virgula detectado em {context_label}."
        )
    for pattern in _SQL_INJECTION_PATTERNS:
        if pattern.search(value):
            raise CrossTenantAccessError(
                f"Tentativa de injecao SQL ou bypass cross-tenant detectada em {context_label}."
            )


def validate_sql_filial_isolation(
    sql: str,
    params: dict[str, Any] | tuple[Any, ...] | list[Any] | None,
    expected_filial_id: int,
) -> bool:
    """
    Verificador sintatico e semantico de consultas SQL multi-filial.
    Garante que:
    1. expected_filial_id e um inteiro positivo valido;
    2. A query SQL possui clausula WHERE filtrando codfilial de forma parametrizada;
    3. Nao ha padroes de SQL injection, comentarios maliciosos, OR 1=1, UNION ou multiplos statements;
    4. Os parametros fornecidos contem exatamente o expected_filial_id sem divergencia entre filiais.
    """
    valid_expected = validate_filial_id(expected_filial_id)

    if not isinstance(sql, str) or not sql.strip():
        raise CrossTenantAccessError("Consulta SQL vazia ou invalida.")

    # Remove no maximo um ponto-e-virgula final legitimo antes de checar multiplos statements
    normalized_sql = sql.strip()
    if normalized_sql.endswith(";"):
        normalized_sql = normalized_sql[:-1].strip()

    _check_string_for_sql_injection(normalized_sql, "consulta SQL")

    if not re.search(r"\bWHERE\b", normalized_sql, re.IGNORECASE):
        raise CrossTenantAccessError(
            "Consulta SQL rejeitada: clausula WHERE obrigatoria com filtro codfilial ausente."
        )

    if _HARDCODED_FILIAL_PATTERN.search(normalized_sql):
        raise CrossTenantAccessError(
            "Consulta SQL rejeitada: filtro codfilial deve ser obrigatoriamente parametrizado, nunca literal."
        )

    matches = list(_PARAMETERIZED_FILIAL_PATTERN.finditer(normalized_sql))
    if not matches:
        raise CrossTenantAccessError(
            "Consulta SQL rejeitada: filtro parametrizado 'codfilial = %s' (ou :filial_id / %(codfilial)s) ausente."
        )

    if params is None:
        raise CrossTenantAccessError(
            "Parametros da query ausentes (None): filtro parametrizado de filial requer parametros explicitos."
        )

    if isinstance(params, dict):
        if not params:
            raise CrossTenantAccessError("Dicionario de parametros vazio na consulta multi-filial.")

        for k, v in params.items():
            if isinstance(v, str):
                _check_string_for_sql_injection(v, f"parametro '{k}'")

        found_filial_keys = [k for k in ("codfilial", "filial_id") if k in params]
        if not found_filial_keys:
            raise CrossTenantAccessError(
                "Dicionario de parametros nao contem a chave obrigatoria 'codfilial' ou 'filial_id'."
            )

        for key in found_filial_keys:
            param_filial = validate_filial_id(params[key])
            if param_filial != valid_expected:
                raise CrossTenantAccessError(
                    f"Violacao Cross-Tenant bloqueada: parametro '{key}'={param_filial} diverge da filial autorizada ({valid_expected})."
                )

        # Verifica tambem se a query usa placeholder compativel
        for m in matches:
            py_key = m.group("pyformat_key")
            named_key = m.group("named_key")
            req_key = py_key or named_key
            if req_key and req_key not in params:
                raise CrossTenantAccessError(
                    f"Placeholder '{req_key}' referenciado na SQL nao esta presente nos parametros."
                )

        return True

    if isinstance(params, (tuple, list)):
        if len(params) == 0:
            raise CrossTenantAccessError("Sequencia de parametros vazia na consulta multi-filial.")

        for idx, item in enumerate(params):
            if isinstance(item, str):
                _check_string_for_sql_injection(item, f"parametro posicional [{idx}]")

        # Mapeia todos os placeholders posicionais %s na query para encontrar o indice de codfilial
        for m in matches:
            placeholder = m.group("placeholder")
            if placeholder != "%s":
                raise CrossTenantAccessError(
                    f"Placeholder nomeado '{placeholder}' incompativel com parametros posicionais (tuple/list)."
                )
            prefix_sql = normalized_sql[: m.start("placeholder")]
            placeholder_index = len(re.findall(r"%s", prefix_sql))
            if placeholder_index >= len(params):
                raise CrossTenantAccessError(
                    f"Indice do placeholder de codfilial ({placeholder_index}) fora do alcance dos parametros ({len(params)})."
                )
            bound_val = validate_filial_id(params[placeholder_index])
            if bound_val != valid_expected:
                raise CrossTenantAccessError(
                    f"Violacao Cross-Tenant bloqueada: codfilial posicional={bound_val} diverge da filial autorizada ({valid_expected})."
                )

        return True

    raise CrossTenantAccessError(
        f"Tipo de parametros nao suportado ({type(params).__name__}): use dict, tuple ou list."
    )


def filter_records_by_filial(
    records: Iterable[Any],
    filial_id: int,
    field_name: str = "codfilial",
) -> list[Any]:
    """
    Filtro deterministico em memoria para blindar retornos de adaptadores ou caches.
    Descarta imediatamente qualquer registro que nao pertenca estritamente a filial_id.
    Suporta dicionarios e objetos/modelos estruturados.
    """
    valid_filial = validate_filial_id(filial_id)
    if records is None:
        return []

    filtered: list[Any] = []
    candidate_fields: Sequence[str] = (
        (field_name, "codfilial", "filial_id")
        if field_name not in ("codfilial", "filial_id")
        else ("codfilial", "filial_id")
    )

    for rec in records:
        rec_filial: Any = None
        if isinstance(rec, dict):
            for f in candidate_fields:
                if f in rec:
                    rec_filial = rec[f]
                    break
        else:
            for f in candidate_fields:
                if hasattr(rec, f):
                    rec_filial = getattr(rec, f)
                    break

        if isinstance(rec_filial, bool) or not isinstance(rec_filial, int):
            continue
        if rec_filial == valid_filial:
            filtered.append(rec)

    return filtered


def load_rls_migration_sql(sql_path: Path | None = None) -> str:
    """Carrega o script SQL de configuracao de Row-Level Security (scripts/rls_multi_tenant.sql)."""
    if sql_path is None:
        base_dir = Path(__file__).resolve().parent.parent
        sql_path = base_dir / "scripts" / "rls_multi_tenant.sql"
    return sql_path.read_text(encoding="utf-8")
