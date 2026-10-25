"""AUPS Dominio de Bombas e Bicos de Combustivel.

AURA Universal Posto Schema (AUPS) e AUDS: Dominio Canonico Desacoplado.
Entidades imutaveis para bombas, bicos e encerrantes de pista.
Zero travessoes em todo o modulo.
"""

from __future__ import annotations

from typing import Any

from pydantic import AliasChoices, ConfigDict, Field, field_validator

from core.domain.base import (
    AUPSBaseModel,
    parse_bool_safe,
    parse_str_safe,
)
from core.domain.universal_entities import (
    UniversalDispenserLog,
    UniversalEquipmentTelemetry,
)


class UniversalPump(AUPSBaseModel):
    """Associacao fisica de bomba, bico, produto e tanque supridor."""

    model_config = ConfigDict(
        frozen=True,
        extra="ignore",
        populate_by_name=True,
    )

    identificador_bomba: str = Field(
        default="0",
        validation_alias=AliasChoices(
            "identificador_bomba", "bomba_id", "numero_bomba", "bomba", "codbom"
        ),
        description="Identificador fisico ou numero da bomba",
    )
    identificador_bico: str = Field(
        default="0",
        validation_alias=AliasChoices(
            "identificador_bico", "bico_id", "numero_bico", "bico", "codbic"
        ),
        description="Identificador fisico do bico dispensador",
    )
    codigo_combustivel: str = Field(
        default="SEM_CODIGO",
        validation_alias=AliasChoices(
            "codigo_combustivel", "cod_combustivel", "codcomb", "fuel_code"
        ),
        description="Codigo do combustivel dispensado neste bico",
    )
    identificador_tanque: str = Field(
        default="0",
        validation_alias=AliasChoices(
            "identificador_tanque", "tanque_id", "numero_tanque", "tanque", "codtan"
        ),
        description="Identificador do tanque de origem conectado ao bico",
    )
    descricao_combustivel: str | None = Field(
        default=None,
        validation_alias=AliasChoices("descricao_combustivel", "combustivel", "descricao"),
        description="Descricao amigavel do combustivel dispensado",
    )
    ativo: bool = Field(
        default=True,
        validation_alias=AliasChoices("ativo", "status_ativo", "is_active"),
        description="Indica se o bico/bomba esta em operacao",
    )

    bomba_fisica: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "bomba_fisica", "referencia", "bom_ds_referencia", "ilha"
        ),
        description="Descricao fisica ou referencia da bomba no posto",
    )
    manual_permitido: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "manual_permitido", "abastecimento_manual", "bic_fl_abastecimento_manual"
        ),
        description="Indica se o bico permite abastecimento manual no PDV",
    )

    @property
    def bomba_id(self) -> str:
        """Alias de conveniencia para identificador_bomba."""
        return self.identificador_bomba

    @property
    def bico_id(self) -> str:
        """Alias de conveniencia para identificador_bico."""
        return self.identificador_bico

    @property
    def tanque_id(self) -> str:
        """Alias de conveniencia para identificador_tanque."""
        return self.identificador_tanque

    @field_validator(
        "identificador_bomba", "identificador_bico", "identificador_tanque", mode="before"
    )
    @classmethod
    def _validate_ids(cls, v: Any) -> str:
        return parse_str_safe(v, default="0")

    @field_validator("codigo_combustivel", mode="before")
    @classmethod
    def _validate_codigo_combustivel(cls, v: Any) -> str:
        return parse_str_safe(v, default="SEM_CODIGO")

    @field_validator("descricao_combustivel", "bomba_fisica", mode="before")
    @classmethod
    def _validate_descricao(cls, v: Any) -> str | None:
        if v is None:
            return None
        return parse_str_safe(v, default="")

    @field_validator("ativo", mode="before")
    @classmethod
    def _validate_ativo(cls, v: Any) -> bool:
        if v is None:
            return True
        return parse_bool_safe(v, default=True)

    @field_validator("manual_permitido", mode="before")
    @classmethod
    def _validate_manual_permitido(cls, v: Any) -> bool:
        if v is None:
            return False
        return parse_bool_safe(v, default=False)


__all__ = [
    "UniversalDispenserLog",
    "UniversalEquipmentTelemetry",
    "UniversalPump",
]
