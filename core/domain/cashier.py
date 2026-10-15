"""AUPS Dominio de Fechamento de Caixa e Movimentacoes Financeiras.

AURA Universal Posto Schema (AUPS): Dominio Canonico Desacoplado.
Entidades imutaveis para turnos de operadores, sangrias e suprimentos.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import AliasChoices, ConfigDict, Field, field_validator, model_validator

from core.domain.base import (
    AUPSBaseModel,
    extract_first_present,
    parse_date_safe,
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


class UniversalCashierShift(AUPSBaseModel):
    """Fechamento consolidado de turno de caixa e frentista."""

    model_config = ConfigDict(
        frozen=True,
        extra="ignore",
        populate_by_name=True,
    )

    operador_id: str = Field(
        default="0",
        validation_alias=AliasChoices(
            "operador_id", "usuario_id", "funcionario_id", "id_operador", "id", "codfun"
        ),
        description="Identificador do operador ou frentista responsavel",
    )
    operador_nome: str = Field(
        default="OPERADOR",
        validation_alias=AliasChoices(
            "operador_nome", "nome_operador", "nome", "usuario_nome", "nomefun"
        ),
        description="Nome civil ou de guerra do operador",
    )
    turno_descricao: str = Field(
        default="GERAL",
        validation_alias=AliasChoices(
            "turno_descricao", "turno", "descricao_turno", "periodo", "descturn"
        ),
        description="Identificacao do turno operacional (ex: MANHA, TARDE, NOITE)",
    )
    data_movimento: date = Field(
        default_factory=date.today,
        validation_alias=AliasChoices("data_movimento", "data", "data_turno", "datamov"),
        description="Data de referencia contabil do movimento",
    )
    timestamp_abertura: datetime = Field(
        default_factory=datetime.now,
        validation_alias=AliasChoices(
            "timestamp_abertura", "data_abertura", "hora_abertura", "abertura", "dtabt", "hrabt"
        ),
        description="Data e hora exata da abertura do turno",
    )
    timestamp_fechamento: datetime | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "timestamp_fechamento", "data_fechamento", "hora_fechamento", "fechamento", "dtfch", "hrfch"
        ),
        description="Data e hora do encerramento do turno",
    )
    fundo_troco_reais: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias=AliasChoices(
            "fundo_troco_reais", "fundo_troco", "troco_inicial", "fundotroco"
        ),
        description="Valor inicial disponibilizado como fundo de troco em Reais",
    )
    total_declarado_reais: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias=AliasChoices(
            "total_declarado_reais", "total_declarado", "valor_declarado", "valdec"
        ),
        description="Valor total em dinheiro e comprovantes declarado pelo operador",
    )
    total_sistema_reais: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias=AliasChoices(
            "total_sistema_reais", "total_sistema", "valor_apurado", "total_apurado", "valsist"
        ),
        description="Valor total calculado pelo sistema ERP para as vendas do turno",
    )
    quebra_sobra_reais: float = Field(
        default=0.0,
        validation_alias=AliasChoices(
            "quebra_sobra_reais", "quebra_sobra", "diferenca_reais", "diferenca", "quebra"
        ),
        description="Diferenca apurada (declarado menos sistema; negativo indica quebra)",
    )

    @property
    def usuario_id(self) -> str:
        """Alias de conveniencia para operador_id."""
        return self.operador_id

    @property
    def funcionario_id(self) -> str:
        """Alias de conveniencia para operador_id."""
        return self.operador_id

    @property
    def nome_operador(self) -> str:
        """Alias de conveniencia para operador_nome."""
        return self.operador_nome

    @field_validator("operador_id", mode="before")
    @classmethod
    def _validate_operador_id(cls, v: Any) -> str:
        return parse_str_safe(v, default="0")

    @field_validator("operador_nome", mode="before")
    @classmethod
    def _validate_operador_nome(cls, v: Any) -> str:
        return parse_str_safe(v, default="OPERADOR")

    @field_validator("turno_descricao", mode="before")
    @classmethod
    def _validate_turno(cls, v: Any) -> str:
        return parse_str_safe(v, default="GERAL")

    @field_validator("data_movimento", mode="before")
    @classmethod
    def _validate_data(cls, v: Any) -> date:
        return parse_date_safe(v)

    @field_validator("timestamp_abertura", mode="before")
    @classmethod
    def _validate_abertura(cls, v: Any) -> datetime:
        return parse_datetime_safe(v)

    @field_validator("timestamp_fechamento", mode="before")
    @classmethod
    def _validate_fechamento(cls, v: Any) -> datetime | None:
        if v is None:
            return None
        return parse_datetime_safe(v)

    @field_validator(
        "fundo_troco_reais",
        "total_declarado_reais",
        "total_sistema_reais",
        mode="before",
    )
    @classmethod
    def _validate_positive_floats(cls, v: Any) -> float:
        return parse_float_safe(v, default=0.0, allow_negative=False)

    @field_validator("quebra_sobra_reais", mode="before")
    @classmethod
    def _validate_quebra_sobra(cls, v: Any) -> float:
        return parse_float_safe(v, default=0.0, allow_negative=True)

    @model_validator(mode="before")
    @classmethod
    def _infer_quebra_sobra(cls, data: Any) -> Any:
        if isinstance(data, dict):
            diff_raw = extract_first_present(
                data,
                (
                    "quebra_sobra_reais",
                    "quebra_sobra",
                    "diferenca_reais",
                    "diferenca",
                    "quebra",
                ),
            )
            if diff_raw is None:
                dec = parse_float_safe(
                    extract_first_present(
                        data,
                        (
                            "total_declarado_reais",
                            "total_declarado",
                            "valor_declarado",
                            "valdec",
                        ),
                    ),
                    default=0.0,
                    allow_negative=False,
                )
                sis = parse_float_safe(
                    extract_first_present(
                        data,
                        (
                            "total_sistema_reais",
                            "total_sistema",
                            "valor_apurado",
                            "total_apurado",
                            "valsist",
                        ),
                    ),
                    default=0.0,
                    allow_negative=False,
                )
                data["quebra_sobra_reais"] = round(dec - sis, 2)
        return data
