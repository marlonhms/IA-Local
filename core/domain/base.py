"""AUPS Base Model e conversores utilitarios universais.

AURA Universal Posto Schema (AUPS): Dominio Canonico Desacoplado.
Fornece infraestrutura base de validacao resiliente e imutabilidade para postos.
"""

from __future__ import annotations

import math
import unicodedata
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict


def strip_accents(text: str) -> str:
    """Remove acentos e diacriticos de strings para comparacao resiliente."""
    if not text:
        return ""
    return "".join(
        c
        for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )


def extract_first_present(
    data: dict[str, Any], keys: tuple[str, ...], default: Any = None
) -> Any:
    """Retorna o primeiro valor presente em data para a tupla de chaves fornecida."""
    for k in keys:
        if k in data and data[k] is not None:
            return data[k]
    return default


def parse_str_safe(v: Any, default: str = "") -> str:
    """Converte qualquer valor em string limpa, aplicando default seguro se nulo ou vazio."""
    if v is None:
        return default
    s = str(v).strip()
    return s if s else default


def parse_bool_safe(v: Any, default: bool = True) -> bool:
    """Converte strings e tipos variados em boolean seguro tolerando formatos comuns em ERPs."""
    if v is None:
        return default
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    if isinstance(v, str):
        clean = v.strip().lower()
        if clean in ("true", "1", "s", "sim", "t", "y", "yes", "ativo"):
            return True
        if clean in ("false", "0", "n", "nao", "não", "f", "no", "inativo"):
            return False
    return default


def parse_float_safe(
    v: Any, default: float = 0.0, allow_negative: bool = True
) -> float:
    """Converte valores numericos em float de forma resiliente."""
    if v is None:
        return default
    if isinstance(v, (int, float, Decimal)):
        try:
            val = float(v)
            if math.isnan(val) or math.isinf(val):
                return default
            if not allow_negative and val < 0:
                return default
            return val
        except (TypeError, ValueError, OverflowError):
            return default
    if isinstance(v, str):
        clean = v.strip().replace("R$", "").replace(" ", "")
        if not clean:
            return default
        last_dot = clean.rfind(".")
        last_comma = clean.rfind(",")
        if last_dot != -1 and last_comma != -1:
            if last_comma > last_dot:
                # Formato brasileiro: 1.234,56 -> remove pontos, troca virgula por ponto
                clean = clean.replace(".", "").replace(",", ".")
            else:
                # Formato internacional: 1,234.56 -> remove virgulas de milhar
                clean = clean.replace(",", "")
        elif last_comma != -1:
            clean = clean.replace(",", ".")
        try:
            val = float(clean)
            if math.isnan(val) or math.isinf(val):
                return default
            if not allow_negative and val < 0:
                return default
            return val
        except ValueError:
            return default
    try:
        val = float(v)
        if math.isnan(val) or math.isinf(val):
            return default
        if not allow_negative and val < 0:
            return default
        return val
    except (TypeError, ValueError, OverflowError):
        return default


def parse_datetime_safe(v: Any) -> datetime:
    """Converte strings e tipos variados em datetime seguro."""
    if isinstance(v, datetime):
        return v
    if isinstance(v, date):
        return datetime.combine(v, time.min)
    if isinstance(v, (int, float)):
        try:
            ts = float(v)
            if ts > 1e11:
                ts = ts / 1000.0
            return datetime.fromtimestamp(ts)
        except (ValueError, OSError, OverflowError):
            return datetime.now()
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return datetime.now()
        try:
            return datetime.fromisoformat(s)
        except ValueError:
            pass
        formats = (
            "%d/%m/%Y %H:%M:%S",
            "%d/%m/%Y %H:%M",
            "%d/%m/%Y",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
            "%Y/%m/%d %H:%M:%S",
            "%Y/%m/%d",
        )
        for fmt in formats:
            try:
                return datetime.strptime(s, fmt)
            except ValueError:
                pass
    return datetime.now()


def parse_date_safe(v: Any) -> date:
    """Converte strings e tipos variados em date seguro."""
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    if isinstance(v, (int, float)):
        return parse_datetime_safe(v).date()
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return date.today()
        try:
            return date.fromisoformat(s)
        except ValueError:
            pass
        dt = parse_datetime_safe(s)
        formats = ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d")
        for fmt in formats:
            try:
                return datetime.strptime(s, fmt).date()
            except ValueError:
                pass
        return dt.date()
    return date.today()


class AUPSBaseModel(BaseModel):
    """Modelo base imutavel e desacoplado do AURA Universal Posto Schema."""

    model_config = ConfigDict(
        frozen=True,
        extra="ignore",
        populate_by_name=True,
    )


# Alias de generalizacao universal para AUDS
AUDSBaseModel = AUPSBaseModel
