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
    codigo_combustivel: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "codigo_combustivel", "cod_combustivel", "codcomb", "fuel_code", "codpro"
        ),
        description="Codigo do combustivel dispensado",
    )
    descricao_combustivel: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "descricao_combustivel", "combustivel", "descricao", "nompro"
        ),
        description="Descricao amigavel do combustivel dispensado",
    )
    identificador_tanque: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "identificador_tanque", "tanque_id", "numero_tanque", "tanque", "codtan"
        ),
        description="Identificador do tanque alimentador do bico",
    )
    preco_unitario_reais: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias=AliasChoices(
            "preco_unitario_reais", "preco_unitario", "preco_fechamento", "preco", "pu", "valunit"
        ),
        description="Preco unitario por litro faturado no fechamento",
    )
    turno_descricao: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "turno_descricao", "turno", "descricao_turno", "periodo"
        ),
        description="Descricao do turno em que ocorreu a medicao",
    )
    pdv: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "pdv", "caixa_pdv", "pos", "caixa", "codpdv"
        ),
        description="Identificador do PDV associado a bomba",
    )
    qtd_abastecimentos: int = Field(
        default=0,
        ge=0,
        validation_alias=AliasChoices(
            "qtd_abastecimentos", "quantidade_abastecimentos", "abastecimentos_count"
        ),
        description="Quantidade de abastecimentos computados na automacao",
    )
    volume_automacao_litros: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias=AliasChoices(
            "volume_automacao_litros", "volume_automacao", "litros_automacao"
        ),
        description="Volume total registrado pela automacao de pista em Litros",
    )
    total_automacao_reais: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias=AliasChoices(
            "total_automacao_reais", "total_automacao", "faturamento_automacao"
        ),
        description="Total financeiro registrado pela automacao de pista em Reais",
    )
    controle: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "controle", "nro_abastecimento", "id_abastecimento", "transacao_id"
        ),
        description="Identificador unico da transacao ou controle de abastecimento",
    )
    volume_litros: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias=AliasChoices(
            "volume_litros", "litros", "volume", "lts", "qtd_litros"
        ),
        description="Volume individual do abastecimento em Litros",
    )
    operador_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "operador_id", "idfrentista", "matricula", "frentista_id", "codfun"
        ),
        description="Matricula ou ID do frentista que operou o bico",
    )
    operador_nome: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "operador_nome", "frentista_nome", "nome_frentista", "nome", "nomfun"
        ),
        description="Nome do frentista responsavel pelo abastecimento",
    )
    duracao_segundos: float | None = Field(
        default=None,
        ge=0.0,
        validation_alias=AliasChoices(
            "duracao_segundos", "tempo", "duracao", "tempo_segundos"
        ),
        description="Tempo de duracao do abastecimento medido em segundos",
    )
    tempo_descricao: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "tempo_descricao", "abt_ds_tempo", "tempo_str"
        ),
        description="Descricao textual do tempo de abastecimento no concentrador",
    )
    venda_cancelada: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "venda_cancelada", "abt_bl_venda_cancelada", "cancelado", "is_cancelled"
        ),
        description="Indica se o abastecimento teve sua venda cancelada",
    )
    string_full: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "string_full", "raw_payload", "observacao", "log_bruto"
        ),
        description="Payload bruto da automacao de pista ou observacao de manual",
    )

    @property
    def volume_vendido_litros(self) -> float:
        """Calcula o volume liquido faturado (encerrante final - inicial - afericoes ou volume direto)."""
        diff = self.encerrante_final_litros - self.encerrante_inicial_litros - self.volume_aferido_litros
        if diff > 0.0:
            return round(diff, 3)
        if self.volume_litros > 0.0:
            return round(self.volume_litros, 3)
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
        "preco_unitario_reais",
        "volume_automacao_litros",
        "total_automacao_reais",
        "volume_litros",
        mode="before",
    )
    @classmethod
    def _validate_numeric_fields(cls, v: Any) -> float:
        return parse_float_safe(v, default=0.0, allow_negative=False)

    @field_validator("duracao_segundos", mode="before")
    @classmethod
    def _validate_duracao_segundos(cls, v: Any) -> float | None:
        if v is None:
            return None
        return parse_float_safe(v, default=0.0, allow_negative=False)

    @field_validator(
        "codigo_combustivel",
        "descricao_combustivel",
        "identificador_tanque",
        "turno_descricao",
        "pdv",
        "controle",
        "operador_id",
        "operador_nome",
        "tempo_descricao",
        "string_full",
        mode="before",
    )
    @classmethod
    def _validate_combustivel_info(cls, v: Any) -> str | None:
        if v is None:
            return None
        parsed = parse_str_safe(v, default="")
        return parsed if parsed else None

    @field_validator("venda_cancelada", mode="before")
    @classmethod
    def _validate_venda_cancelada(cls, v: Any) -> bool:
        if v is None:
            return False
        return parse_bool_safe(v, default=False)

    @field_validator("qtd_abastecimentos", mode="before")
    @classmethod
    def _validate_qtd_abastecimentos(cls, v: Any) -> int:
        if v is None:
            return 0
        try:
            return max(0, int(v))
        except (ValueError, TypeError):
            return 0


