"""AUPS Dominio de Vendas e Loja de Conveniencia.

AURA Universal Posto Schema (AUPS): Dominio Canonico Desacoplado.
Entidades imutaveis para cupons, itens faturados e formas de pagamento.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import AliasChoices, ConfigDict, Field, field_validator, model_validator

from core.domain.base import (
    AUPSBaseModel,
    extract_first_present,
    parse_datetime_safe,
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


class UniversalSaleReceipt(AUPSBaseModel):
    """Cupom fiscal ou pedido de venda fechado no PDV."""

    model_config = ConfigDict(
        frozen=True,
        extra="ignore",
        populate_by_name=True,
    )

    cupom_id: str = Field(
        default="SEM_ID",
        validation_alias=AliasChoices(
            "cupom_id", "venda_id", "id", "id_cupom", "numcupom", "numped", "id_pedido", "sale_id"
        ),
        description="Identificador unico da transacao ou cupom de venda",
    )
    data_hora: datetime = Field(
        default_factory=datetime.now,
        validation_alias=AliasChoices(
            "data_hora", "timestamp", "data", "dataped", "horaped", "datetime", "data_venda"
        ),
        description="Data e hora de emissao da venda",
    )
    pdv: str = Field(
        default="1",
        validation_alias=AliasChoices("pdv", "caixa_pdv", "pos", "caixa", "numpdv"),
        description="Identificador do Ponto de Venda (PDV)",
    )
    total_reais: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias=AliasChoices(
            "total_reais", "total", "total_venda", "valped", "valor_total"
        ),
        description="Valor monetario total da venda em Reais",
    )
    status: str = Field(
        default="CONCLUIDA",
        validation_alias=AliasChoices("status", "situacao", "situ", "status_venda", "estado"),
        description="Status operacional da venda (ex: CONCLUIDA, CANCELADA)",
    )
    operador: str = Field(
        default="SISTEMA",
        validation_alias=AliasChoices(
            "operador", "frentista", "operador_nome", "usuario", "codfren", "nome_operador"
        ),
        description="Identificador ou nome do operador/frentista responsavel",
    )
    itens: list[UniversalSaleItem] = Field(
        default_factory=list,
        validation_alias=AliasChoices("itens", "items", "produtos"),
        description="Lista de itens constituintes da venda",
    )
    pagamentos: list[UniversalPaymentMethod] = Field(
        default_factory=list,
        validation_alias=AliasChoices("pagamentos", "payments", "formas_pagamento"),
        description="Lista de metodos de pagamento vinculados a venda",
    )
    motivo_cancelamento: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "motivo_cancelamento", "motivo", "ven_tx_motivo_cancelamento", "justificativa_cancelamento"
        ),
        description="Justificativa formal do cancelamento da venda",
    )

    @property
    def venda_id(self) -> str:
        """Alias de conveniencia para cupom_id."""
        return self.cupom_id

    @property
    def id(self) -> str:
        """Alias de conveniencia universal para cupom_id."""
        return self.cupom_id

    @property
    def id_cupom(self) -> str:
        """Alias de conveniencia para cupom_id."""
        return self.cupom_id

    @property
    def id_pedido(self) -> str:
        """Alias de conveniencia para cupom_id."""
        return self.cupom_id

    @property
    def pedido_id(self) -> str:
        """Alias de conveniencia para cupom_id."""
        return self.cupom_id

    @field_validator("cupom_id", mode="before")
    @classmethod
    def _validate_cupom_id(cls, v: Any) -> str:
        return parse_str_safe(v, default="SEM_ID")

    @field_validator("pdv", mode="before")
    @classmethod
    def _validate_pdv(cls, v: Any) -> str:
        return parse_str_safe(v, default="1")

    @field_validator("status", mode="before")
    @classmethod
    def _validate_status(cls, v: Any) -> str:
        return parse_str_safe(v, default="CONCLUIDA")

    @field_validator("operador", mode="before")
    @classmethod
    def _validate_operador(cls, v: Any) -> str:
        return parse_str_safe(v, default="SISTEMA")

    @field_validator("data_hora", mode="before")
    @classmethod
    def _validate_data_hora(cls, v: Any) -> datetime:
        return parse_datetime_safe(v)

    @field_validator("total_reais", mode="before")
    @classmethod
    def _validate_total_reais(cls, v: Any) -> float:
        return parse_float_safe(v, default=0.0, allow_negative=False)

    @model_validator(mode="before")
    @classmethod
    def _reconcile_receipt_totals_before(cls, data: Any) -> Any:
        if isinstance(data, dict):
            tot_raw = extract_first_present(
                data,
                ("total_reais", "total", "total_venda", "valped", "valor_total"),
            )
            tot = parse_float_safe(tot_raw, default=0.0, allow_negative=False)
            if tot == 0.0:
                itens = data.get("itens") or data.get("items") or data.get("produtos")
                calc_total = 0.0
                if itens and isinstance(itens, list):
                    for item in itens:
                        if isinstance(item, dict):
                            item_tot = extract_first_present(
                                item,
                                ("total_item_reais", "total_item", "valor_total", "total", "valitem"),
                            )
                            if item_tot is not None:
                                calc_total += parse_float_safe(item_tot, default=0.0, allow_negative=False)
                            else:
                                prc = parse_float_safe(
                                    extract_first_present(
                                        item,
                                        ("preco_unitario_reais", "preco_unitario", "valor_unitario", "unit_price", "prcpec", "preco"),
                                    ),
                                    default=0.0,
                                    allow_negative=False,
                                )
                                qtd = parse_float_safe(
                                    extract_first_present(
                                        item,
                                        ("quantidade", "qtd", "quantity", "qtde", "qtditem"),
                                    ),
                                    default=1.0,
                                    allow_negative=False,
                                )
                                calc_total += round(prc * qtd, 2)
                        elif hasattr(item, "total_item_reais"):
                            calc_total += float(item.total_item_reais)
                if calc_total == 0.0:
                    pagamentos = data.get("pagamentos") or data.get("payments") or data.get("formas_pagamento")
                    if pagamentos and isinstance(pagamentos, list):
                        for pay in pagamentos:
                            if isinstance(pay, dict):
                                pay_val = extract_first_present(
                                    pay,
                                    ("valor_reais", "valor", "total_pago", "amount", "valpra"),
                                )
                                calc_total += parse_float_safe(pay_val, default=0.0, allow_negative=False)
                            elif hasattr(pay, "valor_reais"):
                                calc_total += float(pay.valor_reais)
                if calc_total > 0:
                    data["total_reais"] = round(calc_total, 2)
        return data

    @model_validator(mode="after")
    def _reconcile_receipt_totals_after(self) -> UniversalSaleReceipt:
        if self.total_reais == 0.0:
            if self.itens:
                calc_total = round(sum(item.total_item_reais for item in self.itens), 2)
                if calc_total > 0:
                    object.__setattr__(self, "total_reais", calc_total)
            elif self.pagamentos:
                calc_total = round(sum(pay.valor_reais for pay in self.pagamentos), 2)
                if calc_total > 0:
                    object.__setattr__(self, "total_reais", calc_total)
        return self
