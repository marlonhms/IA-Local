"""Mapeador Declarativo Multi-ERP via YAML (Zero-Code YAML Data Mapper).

AURA Universal Posto Schema (AUPS) & AUDS: Bloco 4 (Declarative Multi-ERP Gateway).
Permite a homologacao rapida de novos sistemas de gestao (ERPs relacionais e PDVs de mercado)
atraves de arquivos declarativos YAML, traduzindo automaticamente para entidades canonicas AUPS / AUDS.
Inclui tratamento estrito contra injecao SQL, queries parametrizadas (%s) e fallback gracioso.
Zero travessoes em todo o modulo.
"""

from __future__ import annotations

import logging
import re
import time
from collections.abc import Callable
from contextlib import suppress
from datetime import date, datetime
from pathlib import Path
from typing import Any

import psycopg2
import yaml
from psycopg2.extras import RealDictCursor
from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from core.adapters.erp.base import (
    BaseERPAdapter,
    ERPAdapterError,
    ERPQueryError,
    normalize_date_filter,
)
from core.adapters.erp.mock_adapter import MockERPAdapter
from core.domain.cashier import UniversalCashierShift
from core.domain.pumps import UniversalDispenserLog, UniversalPump
from core.domain.sales import (
    UniversalPaymentMethod,
    UniversalSaleItem,
    UniversalSaleReceipt,
)
from core.domain.tanks import UniversalTankReading

logger = logging.getLogger("YAMLDataMapperERPAdapter")

# Expressao regular estrita para identificadores SQL seguros (tabelas, colunas, schemas)
IDENTIFIER_REGEX = re.compile(r"^[a-zA-Z0-9_]+$")
ALLOWED_OPERATORS = {
    "=",
    "!=",
    "<>",
    ">",
    "<",
    ">=",
    "<=",
    "LIKE",
    "ILIKE",
    "IS NULL",
    "IS NOT NULL",
    "IN",
    "NOT IN",
}

DATABASE_EXCEPTIONS = (
    psycopg2.Error,
    RuntimeError,
    OSError,
    ValueError,
    KeyError,
    TypeError,
    AttributeError,
)


def validate_identifier(name: str) -> str:
    """Valida identificador SQL permitindo apenas letras, numeros e underscores.

    Suporta notacao schema.tabela ou tabela.coluna (maximo 2 partes).
    Lanca ValueError caso o identificador contenha caracteres invalidos.
    """
    if not name or not isinstance(name, str):
        raise ValueError(f"Identificador SQL invalido ou vazio: {name!r}")
    clean = name.strip()
    if not clean:
        raise ValueError("Identificador SQL nao pode ser vazio")

    parts = clean.split(".")
    if len(parts) > 2:
        raise ValueError(f"Identificador SQL contem mais de um separador de qualificacao: {clean}")

    for p in parts:
        if not p or len(p) > 63:
            raise ValueError(f"Parte do identificador SQL com tamanho invalido (1 a 63 chars): {p!r}")
        if not IDENTIFIER_REGEX.match(p):
            raise ValueError(
                f"Identificador SQL contem caracteres proibidos (apenas letras, numeros e underscores): {clean!r}"
            )

    return clean


class ColumnMappingConfig(BaseModel):
    """Configuracao declarativa de mapeamento de coluna fisica para campo AUPS."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    source_column: str = Field(
        ...,
        validation_alias=AliasChoices("source_column", "source", "column", "col", "name"),
        description="Nome da coluna fisica na tabela do ERP",
    )
    target_field: str | None = Field(
        default=None,
        validation_alias=AliasChoices("target_field", "target", "field", "aups_field"),
        description="Nome do campo correspondente na entidade canonica AUPS",
    )
    data_type: str = Field(
        default="string",
        description="Tipo de dado para conversao (string, float, int, bool, datetime, date)",
    )
    default_value: Any = Field(
        default=None,
        validation_alias=AliasChoices("default_value", "default"),
        description="Valor padrao se a coluna do banco for nula",
    )
    transform: str | None = Field(
        default=None,
        description="Transformacao opcional a aplicar no valor (strip, upper, lower)",
    )

    @field_validator("source_column")
    @classmethod
    def _validate_source(cls, v: str) -> str:
        return validate_identifier(v)

    @field_validator("target_field")
    @classmethod
    def _validate_target(cls, v: str | None) -> str | None:
        if v is not None:
            clean = v.strip()
            if not clean or "." in clean or not IDENTIFIER_REGEX.match(clean):
                raise ValueError(
                    f"target_field deve ser um identificador simples sem separador de ponto: {v!r}"
                )
            return clean
        return None


class JoinConfig(BaseModel):
    """Declaracao de juncao relacional (JOIN) entre tabelas no ERP."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    table: str = Field(..., description="Nome da tabela de juncao")
    type: str = Field(default="LEFT", description="Tipo de juncao: LEFT, INNER, RIGHT")
    left_column: str = Field(..., description="Coluna da tabela principal")
    right_column: str = Field(..., description="Coluna da tabela de juncao")
    left_table: str | None = Field(default=None, description="Tabela de origem (opcional)")
    right_table: str | None = Field(default=None, description="Tabela de destino (opcional)")

    @field_validator("table", "left_column", "right_column")
    @classmethod
    def _validate_table_and_columns(cls, v: str) -> str:
        return validate_identifier(v)

    @field_validator("type")
    @classmethod
    def _validate_join_type(cls, v: str) -> str:
        clean = v.strip().upper()
        if clean not in {"LEFT", "INNER", "RIGHT", "FULL", "CROSS"}:
            raise ValueError(f"Tipo de juncao SQL invalido: {v!r}")
        return clean


class FilterConfig(BaseModel):
    """Filtro estatico seguro parametrizado."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    column: str = Field(..., description="Coluna a filtrar")
    operator: str = Field(default="=", description="Operador SQL permitido")
    value: Any = Field(default=None, description="Valor do filtro parametrizado")

    @field_validator("column")
    @classmethod
    def _validate_col(cls, v: str) -> str:
        return validate_identifier(v)

    @field_validator("operator")
    @classmethod
    def _validate_op(cls, v: str) -> str:
        clean = v.strip().upper()
        if clean not in ALLOWED_OPERATORS:
            raise ValueError(f"Operador SQL proibido: {v!r}")
        return clean


class TableMappingConfig(BaseModel):
    """Mapeamento declarativo de uma tabela ou entidade do ERP."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    table_name: str = Field(
        ...,
        validation_alias=AliasChoices("table_name", "table", "name"),
        description="Nome da tabela fisica no banco do ERP",
    )
    primary_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("primary_key", "pk", "id_column"),
        description="Coluna identificadora primaria da tabela",
    )
    foreign_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("foreign_key", "fk"),
        description="Coluna de ligacao com entidade pai",
    )
    date_column: str | None = Field(
        default=None,
        validation_alias=AliasChoices("date_column", "timestamp_column", "dt_column"),
        description="Coluna temporal para filtragem por data",
    )
    status_column: str | None = Field(
        default=None,
        validation_alias=AliasChoices("status_column", "situacao_column"),
        description="Coluna de status da transacao ou registro",
    )
    cancelled_value: Any = Field(
        default="C",
        validation_alias=AliasChoices("cancelled_value", "valor_cancelado"),
        description="Valor da coluna status indicando cancelamento",
    )
    order_by: str | None = Field(
        default=None,
        description="Coluna padrao de ordenacao dos resultados",
    )
    order_desc: bool = Field(
        default=True,
        description="Se True, ordena decrescente (DESC)",
    )
    columns: dict[str, str | ColumnMappingConfig] = Field(
        default_factory=dict,
        description="Dicionario de mapeamento de colunas AUPS -> ERP",
    )
    joins: list[JoinConfig] = Field(
        default_factory=list,
        description="Lista de juncoes relacionais complementares",
    )
    filters: list[FilterConfig] = Field(
        default_factory=list,
        description="Filtros estaticos complementares parametrizados",
    )

    @model_validator(mode="before")
    @classmethod
    def _normalize_columns_input(cls, data: Any) -> Any:
        if isinstance(data, dict):
            cols = data.get("columns")
            if isinstance(cols, list):
                norm_cols: dict[str, Any] = {}
                for item in cols:
                    if isinstance(item, dict):
                        tgt = (
                            item.get("target_field")
                            or item.get("target")
                            or item.get("field")
                            or item.get("aups_field")
                        )
                        src = (
                            item.get("source_column")
                            or item.get("source")
                            or item.get("column")
                            or item.get("col")
                            or item.get("name")
                        )
                        key = str(tgt or src)
                        norm_cols[key] = item
                    elif isinstance(item, str):
                        norm_cols[item] = item
                data["columns"] = norm_cols
        return data

    @field_validator("table_name")
    @classmethod
    def _validate_table_name(cls, v: str) -> str:
        return validate_identifier(v)

    @field_validator("primary_key", "foreign_key", "date_column", "status_column")
    @classmethod
    def _validate_optional_identifiers(cls, v: str | None) -> str | None:
        if v is not None:
            return validate_identifier(v)
        return None

    @field_validator("order_by")
    @classmethod
    def _validate_order_by(cls, v: str | None) -> str | None:
        if v is not None:
            return validate_identifier(v)
        return None

    def get_column_mappings(self) -> dict[str, ColumnMappingConfig]:
        """Normaliza e retorna mapeamentos com target_field garantido."""
        normalized: dict[str, ColumnMappingConfig] = {}
        for target_key, val in self.columns.items():
            valid_target = validate_identifier(target_key)
            if isinstance(val, str):
                col_cfg = ColumnMappingConfig(
                    source_column=val,
                    target_field=valid_target,
                )
            elif isinstance(val, ColumnMappingConfig):
                col_cfg = ColumnMappingConfig(
                    source_column=val.source_column,
                    target_field=val.target_field or valid_target,
                    data_type=val.data_type,
                    default_value=val.default_value,
                    transform=val.transform,
                )
            elif isinstance(val, dict):
                src = val.get("source_column") or val.get("source") or val.get("col") or val.get("column")
                if not src:
                    raise ValueError(f"source_column obrigatorio para coluna '{valid_target}'")
                col_cfg = ColumnMappingConfig(
                    source_column=src,
                    target_field=val.get("target_field") or valid_target,
                    data_type=val.get("data_type", "string"),
                    default_value=val.get("default_value") or val.get("default"),
                    transform=val.get("transform"),
                )
            else:
                raise TypeError(f"Tipo invalido para definicao de coluna '{valid_target}': {type(val)}")
            normalized[valid_target] = col_cfg
        return normalized


class ERPMappingConfig(BaseModel):
    """Configuracao declarativa completa de mapeamento de um ERP."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    erp_name: str = Field(
        ...,
        validation_alias=AliasChoices("erp_name", "name", "erp"),
        description="Nome de identificacao do software ERP",
    )
    erp_version: str = Field(
        default="1.0",
        validation_alias=AliasChoices("erp_version", "version"),
        description="Versao do arquivo de mapeamento",
    )
    description: str = Field(
        default="",
        description="Descricao amigavel do ERP e peculiaridades de pista",
    )
    dialect: str = Field(
        default="postgres",
        description="Dialeto SQL do banco de dados (ex: postgres)",
    )
    tables: dict[str, TableMappingConfig] = Field(
        default_factory=dict,
        description="Mapeamento de tabelas para entidades AUPS",
    )

    @model_validator(mode="before")
    @classmethod
    def _normalize_tables_dict(cls, data: Any) -> Any:
        if isinstance(data, dict):
            tables_raw = data.get("tables", {})
            if isinstance(tables_raw, list):
                norm_tables = {}
                for tbl in tables_raw:
                    if isinstance(tbl, dict):
                        tbl_name = (
                            tbl.get("entity")
                            or tbl.get("entity_name")
                            or tbl.get("table_name")
                            or tbl.get("name")
                        )
                        if tbl_name:
                            norm_tables[str(tbl_name)] = tbl
                data["tables"] = norm_tables
            elif isinstance(tables_raw, dict):
                normalized_tables = {}
                for k, v in tables_raw.items():
                    if isinstance(v, str):
                        normalized_tables[k] = {"table_name": v}
                    else:
                        normalized_tables[k] = v
                data["tables"] = normalized_tables
        return data

    def get_table(self, entity_name: str) -> TableMappingConfig | None:
        """Recupera configuracao de tabela pelo nome canonico da entidade ou alias."""
        if entity_name in self.tables:
            return self.tables[entity_name]

        # Mapeamento de sinonimos e aliases em portugues e ingles
        aliases_map = {
            "sales": ["vendas", "pedido", "pedidos", "sale", "venda"],
            "sales_items": ["itens", "itemped", "items", "vendas_itens", "sale_items"],
            "sales_payments": ["pagamentos", "formas_pagamento", "payments", "vendas_pagamentos", "sale_payments"],
            "tanks": ["tanques", "tank", "tanque", "tank_readings", "medicaotanques"],
            "pumps": ["bombas", "bicos", "fechabomba", "encerrantes", "pump", "dispenser"],
            "cashier": ["caixa", "fechacaixa", "turnos", "fechamento_caixa", "shifts"],
            "products": ["produtos", "produto", "catalog", "catalogo", "cad_produtos"],
            "pumps_catalog": ["catalogo_bombas", "bombas_cadastro", "cad_bombas"],
        }

        for cand in aliases_map.get(entity_name, []):
            if cand in self.tables:
                return self.tables[cand]

        for main_key, cand_list in aliases_map.items():
            if entity_name in cand_list and main_key in self.tables:
                return self.tables[main_key]

        return None

    @classmethod
    def from_yaml_file(cls, file_path: str | Path) -> ERPMappingConfig:
        """Carrega e valida configuracao a partir de um arquivo YAML."""
        path = Path(file_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Arquivo de mapeamento YAML nao encontrado: {path}")
        raw_text = path.read_text(encoding="utf-8")
        parsed = yaml.safe_load(raw_text)
        if not isinstance(parsed, dict):
            raise TypeError(f"Estrutura YAML invalida em {path}: esperado dicionario raiz")
        return cls(**parsed)

    @classmethod
    def from_yaml_string(cls, content: str) -> ERPMappingConfig:
        """Carrega e valida configuracao a partir de string de conteudo YAML."""
        parsed = yaml.safe_load(content)
        if not isinstance(parsed, dict):
            raise TypeError("Conteudo YAML invalido: esperado dicionario raiz")
        return cls(**parsed)


def _resolve_mapping_config(
    mapping_path_or_name: str | Path | ERPMappingConfig | dict[str, Any],
) -> ERPMappingConfig:
    """Resolve parametro de mapeamento para ERPMappingConfig."""
    if isinstance(mapping_path_or_name, ERPMappingConfig):
        return mapping_path_or_name
    if isinstance(mapping_path_or_name, dict):
        return ERPMappingConfig(**mapping_path_or_name)

    p = Path(mapping_path_or_name)
    if p.exists() and p.is_file():
        return ERPMappingConfig.from_yaml_file(p)

    # Tenta buscar no diretorio padrao config/erp_mappings
    base_dir = Path(__file__).resolve().parent.parent.parent.parent
    mappings_dir = base_dir / "config" / "erp_mappings"

    candidates = [
        mappings_dir / str(mapping_path_or_name),
        mappings_dir / f"{mapping_path_or_name}.yaml",
        mappings_dir / f"{mapping_path_or_name}.yml",
    ]
    for cand in candidates:
        if cand.exists() and cand.is_file():
            return ERPMappingConfig.from_yaml_file(cand)

    # Tenta como conteudo YAML direto se contiver quebras de linha ou campos esperados
    if isinstance(mapping_path_or_name, str) and ("\n" in mapping_path_or_name or "erp_name:" in mapping_path_or_name):
        return ERPMappingConfig.from_yaml_string(mapping_path_or_name)

    raise FileNotFoundError(
        f"Nao foi possivel localizar o arquivo de mapeamento ERP: '{mapping_path_or_name}'"
    )


class YAMLDataMapperERPAdapter(BaseERPAdapter):
    """Adaptador de ERP universal orientado a schemas declarativos YAML.

    Traduz consultas relacionais proprietarias de qualquer ERP de posto para
    entidades universais AUPS sem necessidade de programar adaptadores em Python.
    """

    def __init__(
        self,
        mapping: ERPMappingConfig | Path | str | dict[str, Any],
        connection_factory: Callable[[], Any] | None = None,
        fallback_adapter: BaseERPAdapter | None = None,
        fallback_on_error: bool = True,
        force_offline: bool = False,
    ) -> None:
        """Inicializa o adaptador declarativo YAML.

        Args:
            mapping: Instancia de ERPMappingConfig, Path para arquivo YAML,
                     nome do arquivo (ex: 'linx_postos'), dict ou string de conteudo YAML.
            connection_factory: Funcao que retorna conexao psycopg2 ou wrapper gerenciado.
            fallback_adapter: Adaptador substituto para contingencia offline.
            fallback_on_error: Se True, redireciona para o fallback ao ocorrer erro SQL.
            force_offline: Se True, opera estritamente via fallback sem acessar banco.
        """
        self._config = _resolve_mapping_config(mapping)
        self._connection_factory = connection_factory
        self._fallback_adapter = fallback_adapter or MockERPAdapter()
        self._fallback_on_error = fallback_on_error
        self._force_offline = force_offline

    @property
    def config(self) -> ERPMappingConfig:
        """Retorna a configuracao declarativa do ERP ativo."""
        return self._config

    @property
    def adapter_name(self) -> str:
        """Nome identificador do adaptador ERP."""
        return f"YAML Data Mapper [{self._config.erp_name}]"

    @property
    def fallback_adapter(self) -> BaseERPAdapter:
        """Instancia do adaptador de contingencia offline."""
        return self._fallback_adapter

    @property
    def fallback_on_error(self) -> bool:
        """Indica se fallback automatico em excecoes esta habilitado."""
        return self._fallback_on_error

    @property
    def force_offline(self) -> bool:
        """Indica se o modo offline forcado esta ativado."""
        return self._force_offline

    @force_offline.setter
    def force_offline(self, val: bool) -> None:
        self._force_offline = bool(val)

    def _get_connection(self) -> Any:
        """Obtem conexao de banco de dados via factory ou db_pool."""
        if self._connection_factory is not None:
            return self._connection_factory()
        # Fallback para o pool centralizado do ecossistema AURA
        from core.db_pool import get_erp_connection
        return get_erp_connection(timeout=3)

    @property
    def is_connected(self) -> bool:
        """Verifica se a conexao fisica com a fonte de dados esta ativa."""
        if self._force_offline:
            return False
        conn_obj = None
        try:
            conn_obj = self._get_connection()
            if hasattr(conn_obj, "__enter__") and hasattr(conn_obj, "__exit__"):
                with conn_obj as conn, conn.cursor() as cur:
                    cur.execute("SELECT 1;")
                    cur.fetchone()
            else:
                cur = conn_obj.cursor()
                try:
                    cur.execute("SELECT 1;")
                    cur.fetchone()
                finally:
                    if hasattr(cur, "close"):
                        cur.close()
            return True
        except DATABASE_EXCEPTIONS:
            return False
        finally:
            if conn_obj is not None and hasattr(conn_obj, "close"):
                with suppress(Exception):
                    conn_obj.close()

    def connect(self) -> bool:
        """Verifica prontidao da conexao com a fonte declarada."""
        return self.is_connected

    def disconnect(self) -> None:
        """Finaliza recursos de conexao."""

    def _execute_query(
        self,
        query: str,
        params: list[Any] | tuple[Any, ...] | None = None,
    ) -> list[dict[str, Any]]:
        """Executa consulta SQL com RealDictCursor ou conversao de tuplas."""
        conn_obj = self._get_connection()
        try:
            if hasattr(conn_obj, "__enter__") and hasattr(conn_obj, "__exit__"):
                with conn_obj as conn:
                    return self._fetch_rows(conn, query, params)
            else:
                return self._fetch_rows(conn_obj, query, params)
        finally:
            if hasattr(conn_obj, "close"):
                with suppress(Exception):
                    conn_obj.close()

    def _fetch_rows(
        self,
        conn: Any,
        query: str,
        params: list[Any] | tuple[Any, ...] | None = None,
    ) -> list[dict[str, Any]]:
        """Executa consulta na conexao e retorna lista de dicionarios."""
        cursor_kwargs: dict[str, Any] = {}
        if hasattr(psycopg2, "extras") and hasattr(psycopg2.extras, "RealDictCursor"):
            cursor_kwargs["cursor_factory"] = RealDictCursor

        try:
            cur = conn.cursor(**cursor_kwargs)
        except TypeError:
            cur = conn.cursor()

        try:
            cur.execute(query, params or ())
            if cur.description is None:
                return []
            rows = cur.fetchall()
            results: list[dict[str, Any]] = []
            for r in rows:
                if isinstance(r, dict):
                    results.append(dict(r))
                elif hasattr(r, "_asdict"):
                    results.append(dict(r._asdict()))
                elif hasattr(cur, "description"):
                    col_names = [d[0] for d in cur.description]
                    results.append(dict(zip(col_names, r)))
                else:
                    results.append(dict(r))
            return results
        finally:
            if hasattr(cur, "close"):
                cur.close()

    def _build_select_sql(
        self,
        table_cfg: TableMappingConfig,
        extra_where: list[str] | None = None,
        extra_params: list[Any] | None = None,
        order_by: str | None = None,
        limit: int | None = None,
        extra_select_cols: list[str] | None = None,
    ) -> tuple[str, list[Any]]:
        """Gera instrucao SELECT parametrizada com protecao contra injecao SQL."""
        t_name = validate_identifier(table_cfg.table_name)
        col_mappings = table_cfg.get_column_mappings()

        cols_parts: list[str] = []
        if not col_mappings:
            cols_parts.append("*")
        else:
            cols_parts.extend(
                f"{col.source_column} AS {col.target_field}"
                for col in col_mappings.values()
            )
        if extra_select_cols:
            for extra_col in extra_select_cols:
                if extra_col not in cols_parts:
                    cols_parts.append(extra_col)
        select_cols_sql = ", ".join(cols_parts)

        joins_sql_parts = []
        for j in table_cfg.joins:
            j_type = j.type
            j_table = validate_identifier(j.table)
            l_table = validate_identifier(j.left_table) if j.left_table else t_name
            r_table = validate_identifier(j.right_table) if j.right_table else j_table
            l_col = validate_identifier(j.left_column)
            r_col = validate_identifier(j.right_column)
            joins_sql_parts.append(
                f"{j_type} JOIN {j_table} ON {l_table}.{l_col} = {r_table}.{r_col}"
            )
        joins_sql = " " + " ".join(joins_sql_parts) if joins_sql_parts else ""

        where_parts: list[str] = []
        params: list[Any] = []

        # Filtros estaticos configurados na tabela
        for flt in table_cfg.filters:
            op_upper = flt.operator.upper()
            if op_upper in ("IS NULL", "IS NOT NULL"):
                where_parts.append(f"{flt.column} {op_upper}")
            elif op_upper in ("IN", "NOT IN"):
                if isinstance(flt.value, (list, tuple, set)):
                    if not flt.value:
                        where_parts.append("1=0" if op_upper == "IN" else "1=1")
                    else:
                        val_list = list(flt.value)
                        placeholders = ", ".join(["%s"] * len(val_list))
                        where_parts.append(f"{flt.column} {op_upper} ({placeholders})")
                        params.extend(val_list)
                else:
                    where_parts.append(f"{flt.column} {op_upper} (%s)")
                    params.append(flt.value)
            else:
                where_parts.append(f"{flt.column} {flt.operator} %s")
                params.append(flt.value)

        # Filtros adicionais dinamicos
        if extra_where:
            where_parts.extend(extra_where)
        if extra_params:
            params.extend(extra_params)

        where_sql = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""

        order_col = order_by or table_cfg.order_by
        order_sql = ""
        if order_col:
            v_order = validate_identifier(order_col)
            direction = "DESC" if table_cfg.order_desc else "ASC"
            order_sql = f"ORDER BY {v_order} {direction}"

        limit_sql = ""
        if limit is not None:
            limit_sql = "LIMIT %s"
            params.append(max(1, int(limit)))

        query = f"SELECT {select_cols_sql} FROM {t_name}{joins_sql} {where_sql} {order_sql} {limit_sql};".strip()
        return query, params

    @staticmethod
    def _apply_column_mappings_to_row(
        row: dict[str, Any],
        col_mappings: dict[str, ColumnMappingConfig],
    ) -> dict[str, Any]:
        """Aplica valores padrao, casts e transformacoes declaradas no mapeamento."""
        transformed = dict(row)
        for target_field, col_cfg in col_mappings.items():
            val = transformed.get(target_field)
            if val is None and col_cfg.default_value is not None:
                val = col_cfg.default_value
            if val is not None and col_cfg.transform:
                tr = col_cfg.transform.strip().lower()
                if tr == "strip" and isinstance(val, str):
                    val = val.strip()
                elif tr == "upper" and isinstance(val, str):
                    val = val.upper()
                elif tr == "lower" and isinstance(val, str):
                    val = val.lower()
            if val is not None and col_cfg.data_type:
                dt = col_cfg.data_type.strip().lower()
                if dt == "float" and not isinstance(val, float):
                    try:
                        val = float(val)
                    except (ValueError, TypeError):
                        pass
                elif dt == "int" and not isinstance(val, int):
                    try:
                        val = int(val)
                    except (ValueError, TypeError):
                        pass
                elif dt == "bool" and not isinstance(val, bool):
                    val = bool(val)
                elif dt == "string" and not isinstance(val, str):
                    val = str(val)
            if target_field in transformed or col_cfg.default_value is not None:
                transformed[target_field] = val
        return transformed

    def get_recent_sales(
        self,
        start_date: str | date | datetime | None = None,
        end_date: str | date | datetime | None = None,
        limit: int = 100,
        include_cancelled: bool = False,
    ) -> list[UniversalSaleReceipt]:
        """Recupera lista de cupons de venda e itens faturados no periodo."""
        if self._force_offline:
            return self._fallback_adapter.get_recent_sales(
                start_date, end_date, limit, include_cancelled=include_cancelled
            )

        table_cfg = self._config.get_table("sales")
        if not table_cfg:
            if self._fallback_on_error:
                return self._fallback_adapter.get_recent_sales(
                    start_date, end_date, limit, include_cancelled=include_cancelled
                )
            raise ERPAdapterError("Mapeamento da entidade 'sales' nao declarado no YAML")

        dt_ini = normalize_date_filter(start_date)
        dt_fim = normalize_date_filter(end_date)
        lim = max(1, int(limit))

        extra_where: list[str] = []
        extra_params: list[Any] = []

        if not include_cancelled and table_cfg.status_column:
            extra_where.append(f"COALESCE({table_cfg.status_column}::text, '') != %s")
            extra_params.append(str(table_cfg.cancelled_value))

        if dt_ini and table_cfg.date_column:
            extra_where.append(f"{table_cfg.date_column} >= %s")
            extra_params.append(dt_ini)

        if dt_fim and table_cfg.date_column:
            extra_where.append(f"{table_cfg.date_column} <= %s")
            extra_params.append(dt_fim)

        try:
            sql, params = self._build_select_sql(
                table_cfg,
                extra_where=extra_where,
                extra_params=extra_params,
                limit=lim,
            )
            rows = self._execute_query(sql, params)
        except Exception as exc:
            if self._fallback_on_error:
                logger.warning("Falha em get_recent_sales no YAMLDataMapper (%s): usando fallback.", exc)
                return self._fallback_adapter.get_recent_sales(
                    start_date, end_date, limit, include_cancelled=include_cancelled
                )
            raise ERPQueryError(f"Erro ao consultar vendas declaradas no ERP: {exc}") from exc

        if not rows:
            return []

        # Carrega itens vinculados se tabela sales_items estiver declarada
        items_by_sale: dict[str, list[UniversalSaleItem]] = {}
        items_cfg = self._config.get_table("sales_items")
        if items_cfg and items_cfg.foreign_key:
            sale_ids = [str(r.get("cupom_id") or "") for r in rows if r.get("cupom_id")]
            if sale_ids:
                try:
                    fk_col = validate_identifier(items_cfg.foreign_key)
                    items_col_map = items_cfg.get_column_mappings()
                    batch_size = 500
                    for i in range(0, len(sale_ids), batch_size):
                        chunk_ids = sale_ids[i : i + batch_size]
                        placeholders = ", ".join(["%s"] * len(chunk_ids))
                        items_where = [f"{fk_col}::text IN ({placeholders})"]
                        items_sql, items_params = self._build_select_sql(
                            items_cfg,
                            extra_where=items_where,
                            extra_params=chunk_ids,
                            extra_select_cols=[f"{fk_col} AS __parent_sale_id__"],
                        )
                        item_rows = self._execute_query(items_sql, items_params)
                        for ir in item_rows:
                            parent_id = str(
                                ir.pop("__parent_sale_id__", None)
                                or ir.get(fk_col)
                                or ir.get("cupom_id")
                                or ""
                            )
                            norm_ir = self._apply_column_mappings_to_row(ir, items_col_map)
                            item_obj = UniversalSaleItem(**norm_ir)
                            items_by_sale.setdefault(parent_id, []).append(item_obj)
                except DATABASE_EXCEPTIONS as exc:
                    logger.debug("Nao foi possivel carregar sales_items vinculados (%s)", exc)

        # Carrega pagamentos vinculados se tabela sales_payments estiver declarada
        payments_by_sale: dict[str, list[UniversalPaymentMethod]] = {}
        pay_cfg = self._config.get_table("sales_payments")
        if pay_cfg and pay_cfg.foreign_key:
            sale_ids = [str(r.get("cupom_id") or "") for r in rows if r.get("cupom_id")]
            if sale_ids:
                try:
                    fk_col = validate_identifier(pay_cfg.foreign_key)
                    pay_col_map = pay_cfg.get_column_mappings()
                    batch_size = 500
                    for i in range(0, len(sale_ids), batch_size):
                        chunk_ids = sale_ids[i : i + batch_size]
                        placeholders = ", ".join(["%s"] * len(chunk_ids))
                        pay_where = [f"{fk_col}::text IN ({placeholders})"]
                        pay_sql, pay_params = self._build_select_sql(
                            pay_cfg,
                            extra_where=pay_where,
                            extra_params=chunk_ids,
                            extra_select_cols=[f"{fk_col} AS __parent_sale_id__"],
                        )
                        pay_rows = self._execute_query(pay_sql, pay_params)
                        for pr in pay_rows:
                            parent_id = str(
                                pr.pop("__parent_sale_id__", None)
                                or pr.get(fk_col)
                                or pr.get("cupom_id")
                                or ""
                            )
                            norm_pr = self._apply_column_mappings_to_row(pr, pay_col_map)
                            pay_obj = UniversalPaymentMethod(**norm_pr)
                            payments_by_sale.setdefault(parent_id, []).append(pay_obj)
                except DATABASE_EXCEPTIONS as exc:
                    logger.debug("Nao foi possivel carregar sales_payments vinculados (%s)", exc)

        receipts: list[UniversalSaleReceipt] = []
        sales_col_map = table_cfg.get_column_mappings()
        for r in rows:
            norm_r = self._apply_column_mappings_to_row(r, sales_col_map)
            cupom_id = str(norm_r.get("cupom_id") or "SEM_ID")
            sale_items = items_by_sale.get(cupom_id, [])
            sale_payments = payments_by_sale.get(cupom_id, [])

            # Se nao ha pagamentos separados, tenta construir pagamento unico a partir do cupom
            if not sale_payments and norm_r.get("total_reais") is not None:
                tot_val = float(norm_r.get("total_reais") or 0.0)
                if tot_val > 0.0:
                    sale_payments = [
                        UniversalPaymentMethod(
                            codigo_forma_pagamento=str(norm_r.get("cod_forma") or "0"),
                            descricao_forma=str(norm_r.get("desc_forma") or "OUTROS"),
                            tipo="outro",
                            valor_reais=tot_val,
                        )
                    ]

            receipt_data = dict(norm_r)
            receipt_data["itens"] = sale_items
            receipt_data["pagamentos"] = sale_payments

            receipt = UniversalSaleReceipt(**receipt_data)
            receipts.append(receipt)

        return receipts[:lim]

    def get_tank_inventory(self) -> list[UniversalTankReading]:
        """Recupera telemetria atual de estoque dos tanques de combustivel."""
        if self._force_offline:
            return self._fallback_adapter.get_tank_inventory()

        table_cfg = self._config.get_table("tanks")
        if not table_cfg:
            if self._fallback_on_error:
                return self._fallback_adapter.get_tank_inventory()
            raise ERPAdapterError("Mapeamento da entidade 'tanks' nao declarado no YAML")

        try:
            sql, params = self._build_select_sql(table_cfg)
            rows = self._execute_query(sql, params)
        except Exception as exc:
            if self._fallback_on_error:
                logger.warning("Falha em get_tank_inventory no YAMLDataMapper (%s): usando fallback.", exc)
                return self._fallback_adapter.get_tank_inventory()
            raise ERPQueryError(f"Erro ao consultar tanques no ERP: {exc}") from exc

        readings: list[UniversalTankReading] = []
        col_mappings = table_cfg.get_column_mappings()
        for r in rows:
            norm_r = self._apply_column_mappings_to_row(r, col_mappings)
            readings.append(UniversalTankReading(**norm_r))
        return readings

    def get_pump_dispenses(
        self,
        start_date: str | date | None = None,
        end_date: str | date | None = None,
        limit: int = 100,
        bico: str | None = None,
        turno: str | None = None,
        frentista: str | None = None,
        granular: bool = False,
        incluir_cancelados: bool = True,
    ) -> list[UniversalDispenserLog]:
        """Recupera medicoes e diferencas de encerrantes dos bicos dispensadores."""
        if self._force_offline:
            return self._fallback_adapter.get_pump_dispenses(
                start_date=start_date,
                end_date=end_date,
                limit=limit,
                bico=bico,
                turno=turno,
                frentista=frentista,
                granular=granular,
                incluir_cancelados=incluir_cancelados,
            )

        table_cfg = self._config.get_table("pumps")
        if not table_cfg:
            if self._fallback_on_error:
                return self._fallback_adapter.get_pump_dispenses(
                    start_date=start_date,
                    end_date=end_date,
                    limit=limit,
                    bico=bico,
                    turno=turno,
                    frentista=frentista,
                    granular=granular,
                    incluir_cancelados=incluir_cancelados,
                )
            raise ERPAdapterError("Mapeamento da entidade 'pumps' nao declarado no YAML")

        dt_ini = normalize_date_filter(start_date)
        dt_fim = normalize_date_filter(end_date)
        lim = max(1, int(limit))

        extra_where: list[str] = []
        extra_params: list[Any] = []

        if not incluir_cancelados and table_cfg.status_column:
            extra_where.append(f"COALESCE({table_cfg.status_column}::text, '') != %s")
            extra_params.append(str(table_cfg.cancelled_value))

        if dt_ini and table_cfg.date_column:
            extra_where.append(f"{table_cfg.date_column} >= %s")
            extra_params.append(dt_ini)

        if dt_fim and table_cfg.date_column:
            extra_where.append(f"{table_cfg.date_column} <= %s")
            extra_params.append(dt_fim)

        # Mapeamento reverso para identificar colunas de filtro
        col_mappings = table_cfg.get_column_mappings()
        bico_col = (
            col_mappings.get("identificador_bico")
            or col_mappings.get("bico")
            or col_mappings.get("codbom")
        )
        turno_col = (
            col_mappings.get("turno_descricao")
            or col_mappings.get("turno")
        )
        operador_col = (
            col_mappings.get("operador_id")
            or col_mappings.get("operador_nome")
            or col_mappings.get("operador")
            or col_mappings.get("frentista")
        )

        if bico and bico_col:
            extra_where.append(f"{bico_col.source_column}::text = %s")
            extra_params.append(str(bico).strip())

        if turno and turno_col:
            extra_where.append(f"{turno_col.source_column}::text ILIKE %s")
            extra_params.append(f"%{turno.strip()}%")

        if frentista and operador_col:
            extra_where.append(f"{operador_col.source_column}::text ILIKE %s")
            extra_params.append(f"%{frentista.strip()}%")

        try:
            sql, params = self._build_select_sql(
                table_cfg,
                extra_where=extra_where,
                extra_params=extra_params,
                limit=lim,
            )
            rows = self._execute_query(sql, params)
        except Exception as exc:
            if self._fallback_on_error:
                logger.warning("Falha em get_pump_dispenses no YAMLDataMapper (%s): usando fallback.", exc)
                return self._fallback_adapter.get_pump_dispenses(
                    start_date=start_date,
                    end_date=end_date,
                    limit=limit,
                    bico=bico,
                    turno=turno,
                    frentista=frentista,
                    granular=granular,
                    incluir_cancelados=incluir_cancelados,
                )
            raise ERPQueryError(f"Erro ao consultar bombas no ERP: {exc}") from exc

        logs: list[UniversalDispenserLog] = []
        for r in rows:
            norm_r = self._apply_column_mappings_to_row(r, col_mappings)
            logs.append(UniversalDispenserLog(**norm_r))
        return logs

    def get_pumps_catalog(self) -> list[UniversalPump]:
        """Recupera catalogo de bombas e bicos cadastrados fisicamente no ERP."""
        if self._force_offline:
            return self._fallback_adapter.get_pumps_catalog()

        table_cfg = self._config.get_table("pumps_catalog") or self._config.get_table("pumps")
        if not table_cfg:
            return self._fallback_adapter.get_pumps_catalog()

        try:
            sql, params = self._build_select_sql(table_cfg)
            rows = self._execute_query(sql, params)
        except Exception as exc:
            if self._fallback_on_error:
                return self._fallback_adapter.get_pumps_catalog()
            raise ERPQueryError(f"Erro ao consultar catalogo de bombas: {exc}") from exc

        pumps: list[UniversalPump] = []
        col_mappings = table_cfg.get_column_mappings()
        for r in rows:
            norm_r = self._apply_column_mappings_to_row(r, col_mappings)
            pumps.append(UniversalPump(**norm_r))
        return pumps

    def get_cashier_shifts(
        self,
        target_date: str | date | None = None,
        limit: int = 50,
    ) -> list[UniversalCashierShift]:
        """Recupera fechamentos consolidados de turno de caixa e frentistas."""
        if self._force_offline:
            return self._fallback_adapter.get_cashier_shifts(target_date, limit)

        table_cfg = self._config.get_table("cashier")
        if not table_cfg:
            if self._fallback_on_error:
                return self._fallback_adapter.get_cashier_shifts(target_date, limit)
            raise ERPAdapterError("Mapeamento da entidade 'cashier' nao declarado no YAML")

        dt_alvo = normalize_date_filter(target_date)
        lim = max(1, int(limit))

        extra_where: list[str] = []
        extra_params: list[Any] = []

        if dt_alvo and table_cfg.date_column:
            extra_where.append(f"{table_cfg.date_column} = %s")
            extra_params.append(dt_alvo)

        try:
            sql, params = self._build_select_sql(
                table_cfg,
                extra_where=extra_where,
                extra_params=extra_params,
                limit=lim,
            )
            rows = self._execute_query(sql, params)
        except Exception as exc:
            if self._fallback_on_error:
                logger.warning("Falha em get_cashier_shifts no YAMLDataMapper (%s): usando fallback.", exc)
                return self._fallback_adapter.get_cashier_shifts(target_date, limit)
            raise ERPQueryError(f"Erro ao consultar fechamentos de caixa no ERP: {exc}") from exc

        shifts: list[UniversalCashierShift] = []
        cashier_col_map = table_cfg.get_column_mappings()
        for r in rows:
            shift_data = self._apply_column_mappings_to_row(r, cashier_col_map)
            if float(shift_data.get("total_sistema_reais") or 0.0) == 0.0:
                tot_comb = float(shift_data.get("venda_combustivel_reais") or 0.0)
                tot_prod = float(shift_data.get("venda_produtos_reais") or 0.0)
                if tot_comb > 0 or tot_prod > 0:
                    shift_data["total_sistema_reais"] = round(tot_comb + tot_prod, 2)
            if float(shift_data.get("total_declarado_reais") or 0.0) == 0.0:
                tot_din = float(shift_data.get("dinheiro_declarado_reais") or 0.0)
                tot_cart = float(shift_data.get("cartao_declarado_reais") or 0.0)
                tot_prz = float(shift_data.get("prazo_declarado_reais") or 0.0)
                tot_conv = float(shift_data.get("convenio_cheque_reais") or 0.0)
                sum_decl = tot_din + tot_cart + tot_prz + tot_conv
                if sum_decl > 0:
                    shift_data["total_declarado_reais"] = round(sum_decl, 2)
            if "quebra_sobra_reais" not in shift_data or shift_data["quebra_sobra_reais"] is None:
                tot_decl = float(shift_data.get("total_declarado_reais") or 0.0)
                tot_sist = float(shift_data.get("total_sistema_reais") or 0.0)
                shift_data["quebra_sobra_reais"] = round(tot_decl - tot_sist, 2)
            shifts.append(UniversalCashierShift(**shift_data))
        return shifts

    def get_product_catalog(
        self,
        filter_term: str | None = None,
        category: str | None = None,
        limit: int = 100,
    ) -> list[UniversalSaleItem]:
        """Recupera catalogo de produtos e combustiveis cadastrados no ERP."""
        if self._force_offline:
            return self._fallback_adapter.get_product_catalog(filter_term, category, limit)

        table_cfg = self._config.get_table("products")
        if not table_cfg:
            if self._fallback_on_error:
                return self._fallback_adapter.get_product_catalog(filter_term, category, limit)
            raise ERPAdapterError("Mapeamento da entidade 'products' nao declarado no YAML")

        lim = max(1, int(limit))
        extra_where: list[str] = []
        extra_params: list[Any] = []

        col_mappings = table_cfg.get_column_mappings()
        sku_col = col_mappings.get("sku")
        desc_col = col_mappings.get("descricao_produto")
        grp_col = col_mappings.get("grupo_comercial")

        if filter_term and filter_term.strip():
            term = f"%{filter_term.strip()}%"
            terms_clauses = []
            if sku_col:
                terms_clauses.append(f"{sku_col.source_column}::text ILIKE %s")
                extra_params.append(term)
            if desc_col:
                terms_clauses.append(f"{desc_col.source_column}::text ILIKE %s")
                extra_params.append(term)
            if terms_clauses:
                extra_where.append("(" + " OR ".join(terms_clauses) + ")")

        if category and category.strip() and grp_col:
            extra_where.append(f"{grp_col.source_column}::text ILIKE %s")
            extra_params.append(f"%{category.strip()}%")

        try:
            sql, params = self._build_select_sql(
                table_cfg,
                extra_where=extra_where,
                extra_params=extra_params,
                limit=lim,
            )
            rows = self._execute_query(sql, params)
        except Exception as exc:
            if self._fallback_on_error:
                logger.warning("Falha em get_product_catalog no YAMLDataMapper (%s): usando fallback.", exc)
                return self._fallback_adapter.get_product_catalog(filter_term, category, limit)
            raise ERPQueryError(f"Erro ao consultar catalogo de produtos no ERP: {exc}") from exc

        items: list[UniversalSaleItem] = []
        prod_col_map = table_cfg.get_column_mappings()
        for r in rows:
            norm_r = self._apply_column_mappings_to_row(r, prod_col_map)
            items.append(UniversalSaleItem(**norm_r))
        return items

    def check_health(self) -> dict[str, Any]:
        """Verifica conectividade, latencia em ms e saude das tabelas mapeadas."""
        def _get_fallback_counts(fh: dict[str, Any]) -> dict[str, int]:
            return {
                "pedidos": int(fh.get("sales_count") or len(getattr(self._fallback_adapter, "_sales", []))),
                "tanques": int(fh.get("tank_readings_count") or len(getattr(self._fallback_adapter, "_tanks", []))),
                "bombas": int(fh.get("pump_dispenses_count") or len(getattr(self._fallback_adapter, "_pumps", []))),
                "fechamentos": int(fh.get("cashier_shifts_count") or len(getattr(self._fallback_adapter, "_shifts", []))),
                "produtos": int(fh.get("catalog_items_count") or len(getattr(self._fallback_adapter, "_catalog", []))),
            }

        if self._force_offline:
            fallback_h = self._fallback_adapter.check_health()
            return {
                "status": "offline_fallback",
                "adapter": self.adapter_name,
                "connected": False,
                "is_connected": False,
                "mode": "offline_fallback",
                "erp_name": self._config.erp_name,
                "latency_ms": fallback_h.get("latency_ms", 0.5),
                "record_counts": _get_fallback_counts(fallback_h),
                "error": "Modo offline forcado ativado",
            }

        t0 = time.perf_counter()
        try:
            record_counts: dict[str, int] = {}
            for entity_key, table_cfg in self._config.tables.items():
                v_table = validate_identifier(table_cfg.table_name)
                rows = self._execute_query(f"SELECT COUNT(*) AS cnt FROM {v_table};")
                if rows:
                    record_counts[entity_key] = int(rows[0].get("cnt") or 0)
                else:
                    record_counts[entity_key] = 0

            latency_ms = (time.perf_counter() - t0) * 1000.0

            return {
                "status": "healthy",
                "adapter": self.adapter_name,
                "connected": True,
                "is_connected": True,
                "mode": f"live_yaml_{self._config.dialect}",
                "erp_name": self._config.erp_name,
                "latency_ms": round(latency_ms, 2),
                "record_counts": record_counts,
                "error": None,
            }
        except DATABASE_EXCEPTIONS as exc:
            latency_ms = (time.perf_counter() - t0) * 1000.0
            fallback_h = self._fallback_adapter.check_health()
            return {
                "status": "offline_fallback",
                "adapter": self.adapter_name,
                "connected": False,
                "is_connected": False,
                "mode": "offline_fallback",
                "erp_name": self._config.erp_name,
                "latency_ms": round(latency_ms, 2),
                "record_counts": _get_fallback_counts(fallback_h),
                "error": str(exc),
            }


def create_yaml_erp_adapter(
    mapping_path_or_name: str | Path | ERPMappingConfig | dict[str, Any],
    connection_factory: Callable[[], Any] | None = None,
    fallback_adapter: BaseERPAdapter | None = None,
    fallback_on_error: bool = True,
    force_offline: bool = False,
) -> YAMLDataMapperERPAdapter:
    """Factory universal para criacao de instâncias do YAMLDataMapperERPAdapter."""
    return YAMLDataMapperERPAdapter(
        mapping=mapping_path_or_name,
        connection_factory=connection_factory,
        fallback_adapter=fallback_adapter,
        fallback_on_error=fallback_on_error,
        force_offline=force_offline,
    )
