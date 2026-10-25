"""AUPS Dominio de Vendas e Loja de Conveniencia.

AURA Universal Posto Schema (AUPS) e AUDS: Dominio Canonico Desacoplado.
Entidades imutaveis para cupons, itens faturados e formas de pagamento.
Zero travessoes em todo o modulo.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from pydantic import AliasChoices, ConfigDict, Field, field_validator, model_validator

from core.domain.base import (
    AUPSBaseModel,
    extract_first_present,
    parse_float_safe,
    parse_str_safe,
    strip_accents,
)

PaymentType = Literal["dinheiro", "credito", "debito", "pix", "prazo", "outro"]


class UniversalPaymentMethod(AUPSBaseModel):
    """Metodo e forma de liquidacao financeira de uma venda no posto."""

    model_config = ConfigDict(
        frozen=True,
        extra="ignore",
        populate_by_name=True,
    )

    codigo_forma_pagamento: str = Field(
        default="0",
        validation_alias=AliasChoices(
            "codigo_forma_pagamento", "codigo", "cod_forma", "id", "codpra"
        ),
        description="Codigo identificador da forma de pagamento",
    )
    descricao_forma: str = Field(
        default="OUTROS",
        validation_alias=AliasChoices(
            "descricao_forma", "descricao", "nome_forma", "forma", "descpra"
        ),
        description="Descricao textual da modalidade de pagamento",
    )
    tipo: PaymentType = Field(
        default="outro",
        validation_alias=AliasChoices("tipo", "tipo_pagamento", "payment_type"),
        description="Tipo normalizado (dinheiro, credito, debito, pix, prazo, outro)",
    )
    valor_reais: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias=AliasChoices(
            "valor_reais", "valor", "total_pago", "amount", "valpra"
        ),
        description="Valor liquidado nesta forma de pagamento em Reais",
    )

    @field_validator("codigo_forma_pagamento", mode="before")
    @classmethod
    def _validate_codigo(cls, v: Any) -> str:
        return parse_str_safe(v, default="0")

    @field_validator("descricao_forma", mode="before")
    @classmethod
    def _validate_descricao(cls, v: Any) -> str:
        return parse_str_safe(v, default="OUTROS")

    @field_validator("tipo", mode="before")
    @classmethod
    def _normalize_tipo(cls, v: Any) -> str:
        if not v:
            return "outro"
        clean = strip_accents(str(v)).strip().lower()
        if "cred" in clean:
            return "credito"
        if "deb" in clean:
            return "debito"
        if "pix" in clean:
            return "pix"
        if "dinh" in clean or "especie" in clean or "money" in clean or "cash" in clean:
            return "dinheiro"
        if "praz" in clean or "fat" in clean or "conv" in clean or "bol" in clean:
            return "prazo"
        if clean in {"dinheiro", "credito", "debito", "pix", "prazo", "outro"}:
            return clean
        return "outro"

    @field_validator("valor_reais", mode="before")
    @classmethod
    def _validate_valor_reais(cls, v: Any) -> float:
        return parse_float_safe(v, default=0.0, allow_negative=False)


class UniversalSaleItem(AUPSBaseModel):
    """Item mercantil faturado (combustivel ou produto de conveniencia)."""

    model_config = ConfigDict(
        frozen=True,
        extra="ignore",
        populate_by_name=True,
    )

    sku: str = Field(
        default="SEM_CODIGO",
        validation_alias=AliasChoices(
            "sku", "codigo_produto", "cod_produto", "codpec", "cod_item", "id"
        ),
        description="Codigo SKU ou identificador do produto",
    )
    descricao_produto: str = Field(
        default="PRODUTO DIVERSO",
        validation_alias=AliasChoices(
            "descricao_produto", "descricao", "nome_produto", "produto", "descpec", "product_name"
        ),
        description="Descricao comercial do produto ou servico",
    )
    grupo_comercial: str = Field(
        default="GERAL",
        validation_alias=AliasChoices(
            "grupo_comercial", "grupo", "categoria", "departamento", "descgrp", "codgrp"
        ),
        description="Grupo, categoria ou departamento comercial do item",
    )
    preco_unitario_reais: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias=AliasChoices(
            "preco_unitario_reais", "preco_unitario", "valor_unitario", "unit_price", "prcpec", "preco"
        ),
        description="Preco unitario de venda em Reais",
    )
    quantidade: float = Field(
        default=1.0,
        ge=0.0,
        validation_alias=AliasChoices(
            "quantidade", "qtd", "quantity", "qtde", "qtditem"
        ),
        description="Quantidade faturada",
    )
    total_item_reais: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias=AliasChoices(
            "total_item_reais", "total_item", "valor_total", "total", "valitem"
        ),
        description="Valor monetario total do item em Reais",
    )

    @field_validator("sku", mode="before")
    @classmethod
    def _validate_sku(cls, v: Any) -> str:
        return parse_str_safe(v, default="SEM_CODIGO")

    @field_validator("descricao_produto", mode="before")
    @classmethod
    def _validate_descricao(cls, v: Any) -> str:
        return parse_str_safe(v, default="PRODUTO DIVERSO")

    @field_validator("grupo_comercial", mode="before")
    @classmethod
    def _validate_grupo(cls, v: Any) -> str:
        return parse_str_safe(v, default="GERAL")

    @field_validator("preco_unitario_reais", "total_item_reais", mode="before")
    @classmethod
    def _validate_money_numerics(cls, v: Any) -> float:
        return parse_float_safe(v, default=0.0, allow_negative=False)

    @field_validator("quantidade", mode="before")
    @classmethod
    def _validate_quantidade(cls, v: Any) -> float:
        return parse_float_safe(v, default=1.0, allow_negative=False)

    @model_validator(mode="before")
    @classmethod
    def _calculate_missing_totals(cls, data: Any) -> Any:
        if isinstance(data, dict):
            prc_raw = extract_first_present(
                data,
                (
                    "preco_unitario_reais",
                    "preco_unitario",
                    "valor_unitario",
                    "unit_price",
                    "prcpec",
                    "preco",
                ),
            )
            qtd_raw = extract_first_present(
                data,
                ("quantidade", "qtd", "quantity", "qtde", "qtditem"),
                default=1.0,
            )
            tot_raw = extract_first_present(
                data,
                ("total_item_reais", "total_item", "valor_total", "total", "valitem"),
            )

            prc = parse_float_safe(prc_raw, default=0.0, allow_negative=False)
            qtd = parse_float_safe(qtd_raw, default=1.0, allow_negative=False)
            tot = parse_float_safe(tot_raw, default=0.0, allow_negative=False)

            if tot == 0.0 and prc > 0.0:
                tot = round(prc * qtd, 2)
                data["total_item_reais"] = tot
            elif prc == 0.0 and tot > 0.0 and qtd > 0.0:
                prc = round(tot / qtd, 2)
                data["preco_unitario_reais"] = prc
        return data


if TYPE_CHECKING:
    from core.domain.universal_entities import (
        UniversalSaleReceipt,
        UniversalSaleTransaction,
    )


def __getattr__(name: str) -> Any:
    if name in ("UniversalSaleReceipt", "UniversalSaleTransaction"):
        from core.domain.universal_entities import UniversalSaleTransaction
        return UniversalSaleTransaction
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return list(__all__)


__all__ = [
    "PaymentType",
    "UniversalPaymentMethod",
    "UniversalSaleItem",
    "UniversalSaleReceipt",
    "UniversalSaleTransaction",
]
