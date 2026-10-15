"""AUPS Dominio de Bombas e Bicos de Combustivel.

AURA Universal Posto Schema (AUPS): Dominio Canonico Desacoplado.
Entidades imutaveis para bombas, bicos e encerrantes de pista.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import AliasChoices, ConfigDict, Field, field_validator

from core.domain.base import (
    AUPSBaseModel,
    parse_bool_safe,
    parse_datetime_safe,
    parse_float_safe,
    parse_str_safe,
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

    @field_validator("descricao_combustivel", mode="before")
    @classmethod
    def _validate_descricao(cls, v: Any) -> str | None:
        if v is None:
            return None
        return parse_str_safe(v, default="")

    @field_validator("ativo", mode="before")
    @classmethod
    def _validate_ativo(cls, v: Any) -> bool:
        return parse_bool_safe(v, default=True)


class UniversalDispenserLog(AUPSBaseModel):
    """Registro de fechamento ou leitura de encerrante do medidor do bico."""

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
        description="Identificador da bomba de combustivel",
    )
    identificador_bico: str = Field(
        default="0",
        validation_alias=AliasChoices(
            "identificador_bico", "bico_id", "numero_bico", "bico", "codbic"
        ),
        description="Identificador do bico de abastecimento",
    )
    timestamp_registro: datetime = Field(
        default_factory=datetime.now,
        validation_alias=AliasChoices(
            "timestamp_registro", "data_hora", "timestamp", "data", "datareg", "horareg", "datetime"
        ),
        description="Data e hora do registro do encerrante",
    )
    encerrante_inicial_litros: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias=AliasChoices(
            "encerrante_inicial_litros",
            "encerrante_inicial",
            "encerrante_anterior",
            "encini",
            "leitura_inicial",
        ),
        description="Leitura do encerrante no inicio do periodo em Litros",
    )
    encerrante_final_litros: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias=AliasChoices(
            "encerrante_final_litros",
            "encerrante_final",
            "encerrante_atual",
            "encfim",
            "leitura_final",
        ),
        description="Leitura do encerrante no fechamento do periodo em Litros",
    )
    volume_aferido_litros: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias=AliasChoices(
            "volume_aferido_litros", "volume_aferido", "afericao_litros", "afericao", "volafe"
        ),
        description="Volume retirado para calibracao/afericao tecnica em Litros",
    )
    total_faturado_reais: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias=AliasChoices(
            "total_faturado_reais", "total_faturado", "faturamento_reais", "valor_total", "total", "valtot"
        ),
        description="Total financeiro liquidado correspondente as saidas do bico",
    )

    @property
    def volume_vendido_litros(self) -> float:
        """Calcula o volume liquido faturado (encerrante final - inicial - afericoes)."""
        diff = self.encerrante_final_litros - self.encerrante_inicial_litros - self.volume_aferido_litros
        return max(0.0, round(diff, 3))

    @property
    def bomba_id(self) -> str:
        """Alias de conveniencia para identificador_bomba."""
        return self.identificador_bomba

    @property
    def bico_id(self) -> str:
        """Alias de conveniencia para identificador_bico."""
        return self.identificador_bico

    @field_validator("identificador_bomba", "identificador_bico", mode="before")
    @classmethod
    def _validate_ids(cls, v: Any) -> str:
        return parse_str_safe(v, default="0")

    @field_validator("timestamp_registro", mode="before")
    @classmethod
    def _validate_timestamp(cls, v: Any) -> datetime:
        return parse_datetime_safe(v)

    @field_validator(
        "encerrante_inicial_litros",
        "encerrante_final_litros",
        "volume_aferido_litros",
        "total_faturado_reais",
        mode="before",
    )
    @classmethod
    def _validate_numeric_fields(cls, v: Any) -> float:
        return parse_float_safe(v, default=0.0, allow_negative=False)
