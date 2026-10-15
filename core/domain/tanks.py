"""AUPS Dominio de Tanques e Monitoramento de Estoque.

AURA Universal Posto Schema (AUPS): Dominio Canonico Desacoplado.
Entidades imutaveis para tanques fisicos e medicoes de volume/agua/temperatura.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import AliasChoices, ConfigDict, Field, field_validator, model_validator

from core.domain.base import (
    AUPSBaseModel,
    extract_first_present,
    parse_bool_safe,
    parse_datetime_safe,
    parse_float_safe,
    parse_str_safe,
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


class UniversalTankReading(AUPSBaseModel):
    """Leitura pontual de telemetria ou medicao em regua de um tanque."""

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
        description="Identificador do tanque medido",
    )
    timestamp_leitura: datetime = Field(
        default_factory=datetime.now,
        validation_alias=AliasChoices(
            "timestamp_leitura", "data_hora", "timestamp", "data", "datamed", "horamed", "datetime"
        ),
        description="Momento temporal da medicao de estoque",
    )
    volume_atual_litros: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias=AliasChoices(
            "volume_atual_litros", "volume_atual", "volume", "estoque_fisico", "volmed", "litros"
        ),
        description="Volume apurado de combustivel em Litros",
    )
    volume_agua_mm: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias=AliasChoices(
            "volume_agua_mm", "agua_mm", "nivel_agua_mm", "agua", "aguamed"
        ),
        description="Nivel de agua medido no fundo do tanque em milimetros",
    )
    temperatura_celsius: float | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "temperatura_celsius", "temperatura", "temp_c", "tempmed"
        ),
        description="Temperatura medida no combustivel em graus Celsius",
    )
    percentual_capacidade: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias=AliasChoices(
            "percentual_capacidade", "percentual", "ocupacao_pct", "pct_capacidade"
        ),
        description="Taxa percentual de ocupacao do tanque (0 a 100%)",
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

    @field_validator("timestamp_leitura", mode="before")
    @classmethod
    def _validate_timestamp(cls, v: Any) -> datetime:
        return parse_datetime_safe(v)

    @field_validator("volume_atual_litros", "volume_agua_mm", mode="before")
    @classmethod
    def _validate_floats(cls, v: Any) -> float:
        return parse_float_safe(v, default=0.0, allow_negative=False)

    @field_validator("temperatura_celsius", mode="before")
    @classmethod
    def _validate_temperatura(cls, v: Any) -> float | None:
        if v is None:
            return None
        return parse_float_safe(v, default=0.0, allow_negative=True)

    @field_validator("percentual_capacidade", mode="before")
    @classmethod
    def _validate_percentual(cls, v: Any) -> float:
        return parse_float_safe(v, default=0.0, allow_negative=False)

    @model_validator(mode="before")
    @classmethod
    def _infer_percentual_capacidade(cls, data: Any) -> Any:
        if isinstance(data, dict):
            pct_raw = extract_first_present(
                data,
                (
                    "percentual_capacidade",
                    "percentual",
                    "ocupacao_pct",
                    "pct_capacidade",
                ),
            )
            pct = parse_float_safe(pct_raw, default=0.0, allow_negative=False)
            if pct == 0.0:
                vol = parse_float_safe(
                    extract_first_present(
                        data,
                        (
                            "volume_atual_litros",
                            "volume_atual",
                            "volume",
                            "estoque_fisico",
                            "volmed",
                            "litros",
                        ),
                    ),
                    default=0.0,
                    allow_negative=False,
                )
                cap = parse_float_safe(
                    extract_first_present(
                        data,
                        (
                            "capacidade_nominal_litros",
                            "capacidade_nominal",
                            "capacidade_litros",
                            "capacidade",
                            "captan",
                            "capacidade_maxima",
                        ),
                    ),
                    default=0.0,
                    allow_negative=False,
                )
                if cap > 0.0:
                    data["percentual_capacidade"] = round((vol / cap) * 100.0, 2)
        return data
