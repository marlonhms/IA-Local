"""AUPS Dominio de Tanques e Monitoramento de Estoque.

AURA Universal Posto Schema (AUPS) e AUDS: Dominio Canonico Desacoplado.
Entidades imutaveis para tanques fisicos e medicoes de volume/agua/temperatura.
Zero travessoes em todo o modulo.
"""

from __future__ import annotations

from typing import Any

from pydantic import AliasChoices, ConfigDict, Field, field_validator

from core.domain.base import (
    AUPSBaseModel,
    parse_bool_safe,
    parse_float_safe,
    parse_str_safe,
)
from core.domain.universal_entities import (
    UniversalInventoryNode,
    UniversalTankReading,
)


class UniversalTank(AUPSBaseModel):
    """Cadastro mestre de tanque fisico subterraneo ou aereo."""

    model_config = ConfigDict(
        frozen=True,
        extra="ignore",
        populate_by_name=True,
    )

    identificador_tanque: str = Field(
        default="0",
        validation_alias=AliasChoices(
            "identificador_tanque", "tanque_id", "numero_tanque", "tanque", "id", "codtan"
        ),
        description="Identificador unico ou numero do tanque",
    )
    codigo_combustivel: str = Field(
        default="SEM_CODIGO",
        validation_alias=AliasChoices(
            "codigo_combustivel", "cod_combustivel", "codcomb", "fuel_code", "codprd"
        ),
        description="Codigo de cadastro do combustivel armazenado",
    )
    descricao_combustivel: str = Field(
        default="COMBUSTIVEL DIVERSO",
        validation_alias=AliasChoices(
            "descricao_combustivel", "combustivel", "descricao", "fuel_name", "desccomb", "nome_combustivel"
        ),
        description="Descricao amigavel do combustivel (ex: Gasolina Comum)",
    )
    capacidade_nominal_litros: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias=AliasChoices(
            "capacidade_nominal_litros",
            "capacidade_nominal",
            "capacidade_litros",
            "capacidade",
            "captan",
            "capacidade_maxima",
        ),
        description="Capacidade volumetrica total do tanque em Litros",
    )
    ativo: bool = Field(
        default=True,
        validation_alias=AliasChoices("ativo", "status_ativo", "is_active"),
        description="Indica se o tanque esta operacional",
    )

    @property
    def tanque_id(self) -> str:
        """Alias de conveniencia para identificador_tanque."""
        return self.identificador_tanque

    @property
    def id(self) -> str:
        """Alias universal para identificador_tanque."""
        return self.identificador_tanque

    @field_validator("identificador_tanque", mode="before")
    @classmethod
    def _validate_id(cls, v: Any) -> str:
        return parse_str_safe(v, default="0")

    @field_validator("codigo_combustivel", mode="before")
    @classmethod
    def _validate_codigo(cls, v: Any) -> str:
        return parse_str_safe(v, default="SEM_CODIGO")

    @field_validator("descricao_combustivel", mode="before")
    @classmethod
    def _validate_descricao(cls, v: Any) -> str:
        return parse_str_safe(v, default="COMBUSTIVEL DIVERSO")

    @field_validator("capacidade_nominal_litros", mode="before")
    @classmethod
    def _validate_capacidade(cls, v: Any) -> float:
        return parse_float_safe(v, default=0.0, allow_negative=False)

    @field_validator("ativo", mode="before")
    @classmethod
    def _validate_ativo(cls, v: Any) -> bool:
        return parse_bool_safe(v, default=True)


__all__ = [
    "UniversalInventoryNode",
    "UniversalTank",
    "UniversalTankReading",
]
