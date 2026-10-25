"""AUPS Dominio de Fechamento de Caixa e Movimentacoes Financeiras.

AURA Universal Posto Schema (AUPS) e AUDS: Dominio Canonico Desacoplado.
Entidades imutaveis para turnos de operadores, sangrias e suprimentos.
Zero travessoes em todo o modulo.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal

from pydantic import AliasChoices, ConfigDict, Field, field_validator

from core.domain.base import (
    AUPSBaseModel,
    parse_datetime_safe,
    parse_float_safe,
    parse_str_safe,
    strip_accents,
)

CashMovementType = Literal["sangria", "suprimento", "estorno", "outro"]


class UniversalCashMovement(AUPSBaseModel):
    """Movimentacao avulsa de numerario no caixa (sangria, suprimento ou estorno)."""

    model_config = ConfigDict(
        frozen=True,
        extra="ignore",
        populate_by_name=True,
    )

    tipo_movimento: CashMovementType = Field(
        default="outro",
        validation_alias=AliasChoices("tipo_movimento", "tipo", "movement_type", "tipomov"),
        description="Modalidade do movimento financeiro (sangria, suprimento, estorno, outro)",
    )
    valor_reais: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias=AliasChoices("valor_reais", "valor", "amount", "valmov"),
        description="Valor monetario movimentado em Reais",
    )
    justificativa: str = Field(
        default="",
        validation_alias=AliasChoices("justificativa", "motivo", "observacao", "descricao", "obs"),
        description="Justificativa ou motivo registrado pelo operador",
    )
    timestamp_movimento: datetime = Field(
        default_factory=datetime.now,
        validation_alias=AliasChoices(
            "timestamp_movimento", "data_hora", "timestamp", "data", "datamov", "horamov"
        ),
        description="Data e hora da realizacao da movimentacao",
    )
    operador_id: str = Field(
        default="SISTEMA",
        validation_alias=AliasChoices(
            "operador_id", "usuario_id", "funcionario_id", "id_operador", "id", "codfun"
        ),
        description="Identificador do operador que executou o movimento",
    )
    pdv: str | None = Field(
        default="1",
        validation_alias=AliasChoices("pdv", "caixa_pdv", "pos", "caixa", "numpdv"),
        description="Identificador do PDV associado",
    )

    @property
    def usuario_id(self) -> str:
        """Alias de conveniencia para operador_id."""
        return self.operador_id

    @property
    def funcionario_id(self) -> str:
        """Alias de conveniencia para operador_id."""
        return self.operador_id

    @field_validator("tipo_movimento", mode="before")
    @classmethod
    def _normalize_movement_type(cls, v: Any) -> str:
        if not v:
            return "outro"
        clean = strip_accents(str(v)).strip().lower()
        if "sang" in clean or "retir" in clean or "recolh" in clean:
            return "sangria"
        if "sup" in clean or "refor" in clean or "entrad" in clean:
            return "suprimento"
        if "estorn" in clean or "canc" in clean:
            return "estorno"
        if clean in {"sangria", "suprimento", "estorno", "outro"}:
            return clean
        return "outro"

    @field_validator("valor_reais", mode="before")
    @classmethod
    def _validate_valor(cls, v: Any) -> float:
        return parse_float_safe(v, default=0.0, allow_negative=False)

    @field_validator("justificativa", mode="before")
    @classmethod
    def _validate_justificativa(cls, v: Any) -> str:
        return parse_str_safe(v, default="")

    @field_validator("timestamp_movimento", mode="before")
    @classmethod
    def _validate_timestamp(cls, v: Any) -> datetime:
        return parse_datetime_safe(v)

    @field_validator("operador_id", mode="before")
    @classmethod
    def _validate_operador_id(cls, v: Any) -> str:
        return parse_str_safe(v, default="SISTEMA")

    @field_validator("pdv", mode="before")
    @classmethod
    def _validate_pdv(cls, v: Any) -> str | None:
        if v is None:
            return "1"
        return parse_str_safe(v, default="1")


if TYPE_CHECKING:
    from core.domain.universal_entities import (
        UniversalCashierSession,
        UniversalCashierShift,
    )


def __getattr__(name: str) -> Any:
    if name in ("UniversalCashierSession", "UniversalCashierShift"):
        from core.domain.universal_entities import UniversalCashierSession
        return UniversalCashierSession
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return list(__all__)


__all__ = [
    "CashMovementType",
    "UniversalCashMovement",
    "UniversalCashierSession",
    "UniversalCashierShift",
]
