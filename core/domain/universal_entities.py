"""AUDS Dominio Canonico Universal: AURA Universal Domain Schema (AUDS).

Entidades imutaveis e contratos canonicos universais para operacoes de varejo,
distribuicao e postos de combustiveis.
Totalmente desacoplado de bancos de dados ou ERPs proprietarios.
Compatibilidade estrita com AUPS legado via TypeAliases e heranca reversa.
Zero travessoes em todo o modulo.
"""

from __future__ import annotations

import math
from datetime import date, datetime
from typing import Any

from pydantic import AliasChoices, ConfigDict, Field, field_validator, model_validator

from core.domain.base import (
    AUPSBaseModel,
    extract_first_present,
    parse_bool_safe,
    parse_date_safe,
    parse_datetime_safe,
    parse_float_safe,
    parse_str_safe,
)
from core.domain.cashier import (
    CashMovementType,
    UniversalCashMovement,
)
from core.domain.sales import (
    PaymentType,
    UniversalPaymentMethod,
    UniversalSaleItem,
)

# Alias para Base Model do AUDS
AUDSBaseModel = AUPSBaseModel


class UniversalSaleTransaction(AUDSBaseModel):
    """Contrato canonico universal para qualquer venda faturada ou cupom de PDV.
    
    Generaliza o UniversalSaleReceipt para suportar varejo amplo, supermercados,
    atacado e operacoes de pista.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="ignore",
        populate_by_name=True,
    )

    cupom_id: str = Field(
        default="SEM_ID",
        validation_alias=AliasChoices(
            "cupom_id",
            "venda_id",
            "transaction_id",
            "id",
            "id_cupom",
            "numcupom",
            "numped",
            "id_pedido",
            "sale_id",
            "codigo_transacao",
        ),
        description="Identificador unico universal da transacao comercial",
    )
    data_hora: datetime = Field(
        default_factory=datetime.now,
        validation_alias=AliasChoices(
            "data_hora",
            "timestamp",
            "data",
            "dataped",
            "horaped",
            "datetime",
            "data_venda",
            "data_emissao",
        ),
        description="Data e hora de emissao da venda",
    )
    pdv: str = Field(
        default="1",
        validation_alias=AliasChoices(
            "pdv", "caixa_pdv", "pos", "caixa", "numpdv", "terminal", "terminal_id"
        ),
        description="Identificador do Ponto de Venda ou terminal emissor",
    )
    total_reais: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias=AliasChoices(
            "total_reais", "total", "total_venda", "valped", "valor_total", "amount"
        ),
        description="Valor monetario total liquido da transacao em Reais",
    )
    status: str = Field(
        default="CONCLUIDA",
        validation_alias=AliasChoices(
            "status", "situacao", "situ", "status_venda", "estado"
        ),
        description="Status operacional da venda (ex: CONCLUIDA, CANCELADA)",
    )
    operador: str = Field(
        default="SISTEMA",
        validation_alias=AliasChoices(
            "operador",
            "frentista",
            "operador_nome",
            "usuario",
            "codfren",
            "nome_operador",
            "vendedor",
            "atendente",
        ),
        description="Identificador ou nome do operador ou vendedor",
    )
    itens: list[UniversalSaleItem] = Field(
        default_factory=list,
        validation_alias=AliasChoices("itens", "items", "produtos", "linhas"),
        description="Lista de itens ou produtos faturados",
    )
    pagamentos: list[UniversalPaymentMethod] = Field(
        default_factory=list,
        validation_alias=AliasChoices(
            "pagamentos", "payments", "formas_pagamento", "liquidacoes"
        ),
        description="Lista de metodos e modalidades de pagamento vinculados",
    )
    motivo_cancelamento: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "motivo_cancelamento",
            "motivo",
            "ven_tx_motivo_cancelamento",
            "justificativa_cancelamento",
        ),
        description="Justificativa formal de cancelamento, se aplicavel",
    )
    cliente_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "cliente_id", "cliente", "customer_id", "codcli", "cpf_cnpj_cliente"
        ),
        description="Identificador anonimizado do cliente ou parceiro comercial",
    )
    canal_venda: str = Field(
        default="PDV",
        validation_alias=AliasChoices(
            "canal_venda", "canal", "channel", "origem_venda"
        ),
        description="Canal de venda (PDV, E_COMMERCE, B2B, TELEVENDAS, PISTA)",
    )
    desconto_reais: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias=AliasChoices("desconto_reais", "desconto", "valdesc"),
        description="Valor total concedido em descontos na transacao",
    )

    @property
    def venda_id(self) -> str:
        """Alias de conveniencia para cupom_id."""
        return self.cupom_id

    @property
    def id(self) -> str:
        """Alias universal para cupom_id."""
        return self.cupom_id

    @property
    def id_cupom(self) -> str:
        """Alias de compatibilidade para cupom_id."""
        return self.cupom_id

    @property
    def id_pedido(self) -> str:
        """Alias de compatibilidade para cupom_id."""
        return self.cupom_id

    @property
    def pedido_id(self) -> str:
        """Alias de compatibilidade para cupom_id."""
        return self.cupom_id

    @property
    def transaction_id(self) -> str:
        """Alias universal para cupom_id."""
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

    @field_validator("total_reais", "desconto_reais", mode="before")
    @classmethod
    def _validate_floats(cls, v: Any) -> float:
        return parse_float_safe(v, default=0.0, allow_negative=False)

    @model_validator(mode="before")
    @classmethod
    def _reconcile_receipt_totals_before(cls, data: Any) -> Any:
        if isinstance(data, dict):
            tot_raw = extract_first_present(
                data,
                ("total_reais", "total", "total_venda", "valped", "valor_total", "amount"),
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
    def _reconcile_receipt_totals_after(self) -> UniversalSaleTransaction:
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


# Alias de retrocompatibilidade estrita
UniversalSaleReceipt = UniversalSaleTransaction


class UniversalInventoryNode(AUDSBaseModel):
    """Contrato canonico universal para qualquer no de inventario e estoque fisico.
    
    Generaliza o UniversalTankReading para comportar gôndolas de supermercado,
    camaras frias, prateleiras de farmacia, depositos de atacado e tanques volumetricos.
    Suporta parametro flexivel lot_multiple em vez de multiplos fixos de 5.000L.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="ignore",
        populate_by_name=True,
    )

    identificador_node: str = Field(
        default="0",
        validation_alias=AliasChoices(
            "identificador_node",
            "identificador_tanque",
            "tanque_id",
            "numero_tanque",
            "tanque",
            "id",
            "codtan",
            "node_id",
            "deposito_id",
            "gondola_id",
            "local_estoque",
        ),
        description="Identificador unico do no de inventario, tanque ou deposito",
    )
    nome_node: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "nome_node", "descricao_tanque", "nome_deposito", "nome_gondola", "deposito", "gondola"
        ),
        description="Descricao amigavel do local fisico de estocagem",
    )
    tipo_node: str = Field(
        default="tanque",
        validation_alias=AliasChoices("tipo_node", "tipo_estoque", "node_type"),
        description="Tipo de estrutura fisica (tanque, gondola, deposito, camara_fria, palete)",
    )
    timestamp_leitura: datetime = Field(
        default_factory=datetime.now,
        validation_alias=AliasChoices(
            "timestamp_leitura",
            "data_hora",
            "timestamp",
            "data",
            "datamed",
            "horamed",
            "datetime",
        ),
        description="Momento temporal da medicao de inventario ou estoque",
    )
    quantidade_atual: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias=AliasChoices(
            "quantidade_atual",
            "volume_atual_litros",
            "volume_atual",
            "volume",
            "estoque_fisico",
            "volmed",
            "litros",
            "saldo_atual",
            "quantidade",
        ),
        description="Quantidade ou volume fisico apurado na leitura",
    )
    capacidade_maxima: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias=AliasChoices(
            "capacidade_maxima",
            "capacidade_nominal_litros",
            "capacidade_litros",
            "capacidade",
            "captan",
            "capacidade_nominal",
        ),
        description="Capacidade maxima nominal do no de inventario",
    )
    quantidade_minima_seguranca: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias=AliasChoices(
            "quantidade_minima_seguranca",
            "ponto_pedido",
            "estoque_minimo",
            "safety_stock",
            "lastro_minimo",
        ),
        description="Estoque de seguranca ou ponto de ressuprimento",
    )
    unidade_medida: str = Field(
        default="L",
        validation_alias=AliasChoices("unidade_medida", "unidade", "uom", "unid"),
        description="Unidade de medida (L, UN, CX, KG, PAL)",
    )
    lot_multiple: float = Field(
        default=5000.0,
        gt=0.0,
        validation_alias=AliasChoices(
            "lot_multiple", "lote_multiplo", "tamanho_lote", "pack_size", "multiplo_compra"
        ),
        description="Multiplo de pedido ou lote padrao de compra (ex: 5.000L para combustivel, 12 para caixas)",
    )
    saldo_inicial: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias=AliasChoices(
            "saldo_inicial", "saldo_inicial_litros", "qtdeinicioturno", "qtdean"
        ),
        description="Saldo fisico no inicio do periodo",
    )
    saldo_final: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias=AliasChoices(
            "saldo_final", "saldo_final_litros", "tan_vl_quantidade_fim", "qtdeat"
        ),
        description="Saldo fisico no encerramento do periodo",
    )
    percentual_ocupacao: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias=AliasChoices(
            "percentual_ocupacao", "percentual_capacidade", "percentual", "ocupacao_pct", "pct_capacidade"
        ),
        description="Taxa percentual de ocupacao da capacidade (0 a 100%)",
    )
    volume_agua_mm: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias=AliasChoices(
            "volume_agua_mm", "agua_mm", "nivel_agua_mm", "agua", "aguamed"
        ),
        description="Nivel de contaminacao de agua em milimetros (especifico de combustiveis)",
    )
    temperatura_celsius: float | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "temperatura_celsius", "temperatura", "temp_c", "tempmed"
        ),
        description="Temperatura medida no combustivel ou ambiente controlado",
    )
    tem_medicao_fisica: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "tem_medicao_fisica", "medicao_fisica", "has_physical_measurement"
        ),
        description="Indica se houve afericao fisica com regua, telemetria ou inventario rotativo",
    )
    codigo_item: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "codigo_item",
            "combustivel",
            "codigo_combustivel",
            "sku",
            "cod_produto",
            "codigo_produto",
            "prl_ds_produto_lmc",
            "nompro",
            "codigo_lmc",
            "codlmc",
        ),
        description="Codigo ou identificador do produto principal alocado neste no",
    )
    descricao_item: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "descricao_item",
            "descricao_combustivel",
            "combustivel",
            "descricao_produto",
            "produto",
            "nompro",
        ),
        description="Descricao comercial do produto alocado",
    )
    codigo_lmc: str | None = Field(
        default=None,
        validation_alias=AliasChoices("codigo_lmc", "codlmc", "codlmc_anp"),
        description="Codigo regulatorio LMC ANP, se aplicavel",
    )
    bicos_conectados: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("bicos_conectados", "bicos", "bicos_vinculados"),
        description="Lista de bicos abastecedores conectados a este tanque",
    )

    # Aliases de conveniencia para 100% de retrocompatibilidade com AUPS UniversalTankReading
    @property
    def identificador_tanque(self) -> str:
        return self.identificador_node

    @property
    def tanque_id(self) -> str:
        return self.identificador_node

    @property
    def id(self) -> str:
        return self.identificador_node

    @property
    def node_id(self) -> str:
        return self.identificador_node

    @property
    def volume_atual_litros(self) -> float:
        return self.quantidade_atual

    @property
    def capacidade_nominal_litros(self) -> float:
        return self.capacidade_maxima

    @property
    def saldo_inicial_litros(self) -> float:
        return self.saldo_inicial

    @property
    def saldo_final_litros(self) -> float:
        return self.saldo_final

    @property
    def percentual_capacidade(self) -> float:
        return self.percentual_ocupacao

    @property
    def combustivel(self) -> str | None:
        return self.descricao_item or self.codigo_item

    @property
    def codigo_combustivel(self) -> str | None:
        """Alias de conveniencia para codigo_item."""
        return self.codigo_item

    @property
    def descricao_combustivel(self) -> str | None:
        """Alias de conveniencia para descricao_item."""
        return self.descricao_item

    @property
    def capacidade_livre(self) -> float:
        """Espaco fisico disponivel para recebimento de carga (Ullage)."""
        return max(0.0, self.capacidade_maxima - self.quantidade_atual)

    @property
    def ullage(self) -> float:
        """Alias para capacidade_livre."""
        return self.capacidade_livre

    def calcular_lotes_reposicao(self, quantidade_necessaria: float) -> int:
        """Calcula o numero de lotes fechados necessarios para suprir a demanda."""
        if self.lot_multiple <= 0:
            return int(quantidade_necessaria)
        return math.ceil(quantidade_necessaria / self.lot_multiple)

    def calcular_espaco_para_lotes(self) -> int:
        """Calcula quantos lotes fechados cabem no espaco livre (capacidade_livre)."""
        if self.lot_multiple <= 0:
            return 0
        return math.floor(self.capacidade_livre / self.lot_multiple)

    @field_validator("identificador_node", mode="before")
    @classmethod
    def _validate_id(cls, v: Any) -> str:
        return parse_str_safe(v, default="0")

    @field_validator("timestamp_leitura", mode="before")
    @classmethod
    def _validate_timestamp(cls, v: Any) -> datetime:
        return parse_datetime_safe(v)

    @field_validator(
        "quantidade_atual",
        "capacidade_maxima",
        "quantidade_minima_seguranca",
        "saldo_inicial",
        "saldo_final",
        "percentual_ocupacao",
        "volume_agua_mm",
        mode="before",
    )
    @classmethod
    def _validate_positive_floats(cls, v: Any) -> float:
        return parse_float_safe(v, default=0.0, allow_negative=False)

    @field_validator("lot_multiple", mode="before")
    @classmethod
    def _validate_lot_multiple(cls, v: Any) -> float:
        val = parse_float_safe(v, default=5000.0, allow_negative=False)
        return val if val > 0 else 5000.0

    @field_validator("temperatura_celsius", mode="before")
    @classmethod
    def _validate_temperatura(cls, v: Any) -> float | None:
        if v is None:
            return None
        return parse_float_safe(v, default=0.0, allow_negative=True)

    @field_validator("tem_medicao_fisica", mode="before")
    @classmethod
    def _validate_tem_medicao_fisica(cls, v: Any) -> bool:
        return bool(v) if v is not None else False

    @field_validator("bicos_conectados", mode="before")
    @classmethod
    def _validate_bicos_conectados(cls, v: Any) -> list[str]:
        if not v:
            return []
        if isinstance(v, (list, tuple, set)):
            return [str(x).strip() for x in v if str(x).strip()]
        return [str(v).strip()]

    @model_validator(mode="before")
    @classmethod
    def _infer_percentual_capacidade(cls, data: Any) -> Any:
        if isinstance(data, dict):
            pct_raw = extract_first_present(
                data,
                (
                    "percentual_ocupacao",
                    "percentual_capacidade",
                    "percentual",
                    "ocupacao_pct",
                    "pct_capacidade",
                ),
            )
            pct = parse_float_safe(pct_raw, default=0.0, allow_negative=False)
            if pct == 0.0:
                qtd = parse_float_safe(
                    extract_first_present(
                        data,
                        (
                            "quantidade_atual",
                            "volume_atual_litros",
                            "volume_atual",
                            "volume",
                            "estoque_fisico",
                            "volmed",
                            "litros",
                            "saldo_atual",
                            "quantidade",
                        ),
                    ),
                    default=0.0,
                    allow_negative=False,
                )
                cap = parse_float_safe(
                    extract_first_present(
                        data,
                        (
                            "capacidade_maxima",
                            "capacidade_nominal_litros",
                            "capacidade_litros",
                            "capacidade",
                            "captan",
                            "capacidade_nominal",
                        ),
                    ),
                    default=0.0,
                    allow_negative=False,
                )
                if cap > 0.0:
                    data["percentual_ocupacao"] = round((qtd / cap) * 100.0, 2)
        return data


# Alias de retrocompatibilidade estrita
UniversalTankReading = UniversalInventoryNode


class UniversalEquipmentTelemetry(AUDSBaseModel):
    """Contrato canonico universal para qualquer equipamento ou medidor de saida.
    
    Generaliza o UniversalDispenserLog para suportar balancas de checkout,
    sensores de vazao, terminais POS e bicos de bombas de combustivel.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="ignore",
        populate_by_name=True,
    )

    identificador_equipamento: str = Field(
        default="0",
        validation_alias=AliasChoices(
            "identificador_equipamento",
            "identificador_bomba",
            "bomba_id",
            "numero_bomba",
            "bomba",
            "codbom",
            "equipamento_id",
            "device_id",
            "terminal_id",
        ),
        description="Identificador unico do equipamento ou bomba",
    )
    identificador_componente: str = Field(
        default="0",
        validation_alias=AliasChoices(
            "identificador_componente",
            "identificador_bico",
            "bico_id",
            "numero_bico",
            "bico",
            "codbic",
            "subdevice_id",
            "canal_id",
            "sensor_id",
        ),
        description="Identificador do componente, bico ou sensor medidor",
    )
    tipo_equipamento: str = Field(
        default="bomba_combustivel",
        validation_alias=AliasChoices("tipo_equipamento", "equipment_type"),
        description="Tipo do equipamento (bomba_combustivel, sensor_vazao, balanca, terminal_pdv)",
    )
    timestamp_registro: datetime = Field(
        default_factory=datetime.now,
        validation_alias=AliasChoices(
            "timestamp_registro",
            "data_hora",
            "timestamp",
            "data",
            "datareg",
            "horareg",
            "datetime",
        ),
        description="Data e hora do registro do medidor",
    )
    leitura_inicial: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias=AliasChoices(
            "leitura_inicial",
            "encerrante_inicial_litros",
            "encerrante_inicial",
            "encerrante_anterior",
            "encini",
        ),
        description="Leitura inicial do medidor no inicio do periodo",
    )
    leitura_final: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias=AliasChoices(
            "leitura_final",
            "encerrante_final_litros",
            "encerrante_final",
            "encerrante_atual",
            "encfim",
        ),
        description="Leitura final do medidor no fechamento do periodo",
    )
    volume_aferido: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias=AliasChoices(
            "volume_aferido",
            "volume_aferido_litros",
            "afericao_litros",
            "afericao",
            "volafe",
            "calibracao",
        ),
        description="Volume retirado para calibracao ou afericao tecnica",
    )
    total_faturado_reais: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias=AliasChoices(
            "total_faturado_reais",
            "total_faturado",
            "faturamento_reais",
            "valor_total",
            "total",
            "valtot",
        ),
        description="Total financeiro liquidado correspondente as saidas",
    )
    codigo_item: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "codigo_item",
            "codigo_combustivel",
            "cod_combustivel",
            "codcomb",
            "fuel_code",
            "codpro",
            "sku",
        ),
        description="Codigo do produto dispensado",
    )
    descricao_item: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "descricao_item",
            "descricao_combustivel",
            "combustivel",
            "descricao",
            "nompro",
        ),
        description="Descricao amigavel do produto dispensado",
    )
    identificador_origem: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "identificador_origem",
            "identificador_tanque",
            "tanque_id",
            "numero_tanque",
            "tanque",
            "codtan",
            "local_estoque_id",
        ),
        description="Identificador da origem de estocagem (tanque ou deposito supridor)",
    )
    preco_unitario_reais: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias=AliasChoices(
            "preco_unitario_reais",
            "preco_unitario",
            "preco_fechamento",
            "preco",
            "pu",
            "valunit",
        ),
        description="Preco unitario apurado no fechamento",
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
        validation_alias=AliasChoices("pdv", "caixa_pdv", "pos", "caixa", "codpdv"),
        description="Identificador do PDV associado",
    )
    qtd_acionamentos: int = Field(
        default=0,
        ge=0,
        validation_alias=AliasChoices(
            "qtd_acionamentos",
            "qtd_abastecimentos",
            "abastecimentos",
            "total_operacoes",
        ),
        description="Quantidade total de operacoes ou abastecimentos",
    )
    volume_automacao_litros: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias=AliasChoices(
            "volume_automacao_litros",
            "volume_automacao",
            "litros_automacao",
        ),
        description="Volume total registrado pela automacao de pista em Litros",
    )
    total_automacao_reais: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias=AliasChoices(
            "total_automacao_reais",
            "total_automacao",
            "faturamento_automacao",
        ),
        description="Total financeiro registrado pela automacao de pista em Reais",
    )
    controle: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "controle",
            "nro_abastecimento",
            "id_abastecimento",
            "transacao_id",
        ),
        description="Identificador unico da transacao ou controle de abastecimento",
    )
    volume_litros: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias=AliasChoices(
            "volume_litros",
            "litros",
            "volume",
            "lts",
            "qtd_litros",
        ),
        description="Volume individual do abastecimento em Litros",
    )
    operador_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "operador_id",
            "idfrentista",
            "matricula",
            "frentista_id",
            "codfun",
        ),
        description="Matricula ou ID do frentista ou operador",
    )
    operador_nome: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "operador_nome",
            "frentista_nome",
            "nome_frentista",
            "nome",
            "nomfun",
        ),
        description="Nome do frentista ou operador responsavel",
    )
    duracao_segundos: float | None = Field(
        default=None,
        ge=0.0,
        validation_alias=AliasChoices(
            "duracao_segundos",
            "tempo",
            "duracao",
            "tempo_segundos",
        ),
        description="Tempo de duracao da operacao medido em segundos",
    )
    tempo_descricao: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "tempo_descricao",
            "abt_ds_tempo",
            "tempo_str",
        ),
        description="Descricao textual do tempo da operacao ou concentrador",
    )
    venda_cancelada: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "venda_cancelada",
            "abt_bl_venda_cancelada",
            "cancelado",
            "is_cancelled",
        ),
        description="Indica se a operacao ou venda foi cancelada",
    )
    string_full: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "string_full",
            "raw_payload",
            "observacao",
            "log_bruto",
        ),
        description="Payload bruto da automacao ou observacao textual",
    )

    # Aliases de conveniencia para compatibilidade total com UniversalDispenserLog
    @property
    def identificador_bomba(self) -> str:
        return self.identificador_equipamento

    @property
    def bomba_id(self) -> str:
        return self.identificador_equipamento

    @property
    def identificador_bico(self) -> str:
        return self.identificador_componente

    @property
    def bico_id(self) -> str:
        return self.identificador_componente

    @property
    def encerrante_inicial_litros(self) -> float:
        return self.leitura_inicial

    @property
    def encerrante_final_litros(self) -> float:
        return self.leitura_final

    @property
    def volume_aferido_litros(self) -> float:
        return self.volume_aferido

    @property
    def qtd_abastecimentos(self) -> int:
        return self.qtd_acionamentos

    @property
    def codigo_combustivel(self) -> str | None:
        return self.codigo_item

    @property
    def descricao_combustivel(self) -> str | None:
        return self.descricao_item

    @property
    def identificador_tanque(self) -> str | None:
        return self.identificador_origem

    @property
    def tanque_id(self) -> str | None:
        return self.identificador_origem

    @property
    def delta_leitura(self) -> float:
        """Diferenca bruta entre a leitura final e a inicial."""
        return max(0.0, round(self.leitura_final - self.leitura_inicial, 3))

    @property
    def volume_vendido_litros(self) -> float:
        """Calcula o volume liquido faturado (encerrante final - inicial - afericoes ou volume direto)."""
        diff = self.leitura_final - self.leitura_inicial - self.volume_aferido
        if diff > 0.0:
            return round(diff, 3)
        if self.volume_litros > 0.0:
            return round(self.volume_litros, 3)
        return max(0.0, round(diff, 3))

    @property
    def volume_vendido(self) -> float:
        """Alias para volume_vendido_litros."""
        return self.volume_vendido_litros

    @field_validator(
        "identificador_equipamento", "identificador_componente", mode="before"
    )
    @classmethod
    def _validate_ids(cls, v: Any) -> str:
        return parse_str_safe(v, default="0")

    @field_validator("timestamp_registro", mode="before")
    @classmethod
    def _validate_timestamp(cls, v: Any) -> datetime:
        return parse_datetime_safe(v)

    @field_validator(
        "leitura_inicial",
        "leitura_final",
        "volume_aferido",
        "total_faturado_reais",
        "preco_unitario_reais",
        "volume_automacao_litros",
        "total_automacao_reais",
        "volume_litros",
        mode="before",
    )
    @classmethod
    def _validate_positive_floats(cls, v: Any) -> float:
        return parse_float_safe(v, default=0.0, allow_negative=False)

    @field_validator("duracao_segundos", mode="before")
    @classmethod
    def _validate_duracao_segundos(cls, v: Any) -> float | None:
        if v is None:
            return None
        return parse_float_safe(v, default=0.0, allow_negative=False)

    @field_validator(
        "codigo_item",
        "descricao_item",
        "identificador_origem",
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
    def _validate_str_fields(cls, v: Any) -> str | None:
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

    @field_validator("qtd_acionamentos", mode="before")
    @classmethod
    def _validate_qtd_acionamentos(cls, v: Any) -> int:
        if v is None:
            return 0
        try:
            return max(0, int(v))
        except (ValueError, TypeError):
            return 0


# Alias de retrocompatibilidade estrita
UniversalDispenserLog = UniversalEquipmentTelemetry


class UniversalCashierSession(AUDSBaseModel):
    """Contrato canonico universal para fechamento de caixa e turno de operador.
    
    Generaliza o UniversalCashierShift para suportar qualquer PDV de loja,
    supermercado, frente de pista ou canal de recebimento.
    """

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
        description="Identificador do operador ou vendedor responsavel",
    )
    operador_nome: str = Field(
        default="OPERADOR",
        validation_alias=AliasChoices(
            "operador_nome", "nome_operador", "nome", "usuario_nome", "nomefun"
        ),
        description="Nome do operador de caixa",
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
        description="Data contabil de referencia do movimento",
    )
    timestamp_abertura: datetime = Field(
        default_factory=datetime.now,
        validation_alias=AliasChoices(
            "timestamp_abertura", "data_abertura", "hora_abertura", "abertura", "dtabt", "hrabt"
        ),
        description="Data e hora exata da abertura da sessao",
    )
    timestamp_fechamento: datetime | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "timestamp_fechamento", "data_fechamento", "hora_fechamento", "fechamento", "dtfch", "hrfch"
        ),
        description="Data e hora do encerramento da sessao",
    )
    fundo_troco_reais: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias=AliasChoices(
            "fundo_troco_reais", "fundo_troco", "troco_inicial", "fundotroco"
        ),
        description="Valor inicial disponibilizado como fundo de troco",
    )
    total_declarado_reais: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias=AliasChoices(
            "total_declarado_reais", "total_declarado", "valor_declarado", "valdec"
        ),
        description="Valor total declarado pelo operador no fechamento",
    )
    total_sistema_reais: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias=AliasChoices(
            "total_sistema_reais", "total_sistema", "valor_apurado", "total_apurado", "valsist"
        ),
        description="Valor total calculado pelo sistema para as vendas do turno",
    )
    quebra_sobra_reais: float = Field(
        default=0.0,
        validation_alias=AliasChoices(
            "quebra_sobra_reais", "quebra_sobra", "diferenca_reais", "diferenca", "quebra"
        ),
        description="Diferenca apurada (declarado menos sistema; negativo indica quebra)",
    )
    pdv: str = Field(
        default="1",
        validation_alias=AliasChoices("pdv", "caixa_pdv", "pos", "caixa", "codpdv"),
        description="Identificador do PDV associado",
    )
    caixa_id: str = Field(
        default="1",
        validation_alias=AliasChoices(
            "caixa_id", "cai_cd_caixa", "terminal_id", "terminal", "sessao_id", "shift_id"
        ),
        description="Identificador unico da sessao ou terminal de caixa",
    )
    fechado: bool = Field(
        default=True,
        validation_alias=AliasChoices("fechado", "is_closed", "status_fechado"),
        description="Indica se o caixa esta formalmente encerrado",
    )
    dinheiro_declarado_reais: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias=AliasChoices("dinheiro_declarado_reais", "dinheiro", "valdinh", "cash"),
        description="Total declarado em dinheiro em especie",
    )
    cartao_declarado_reais: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias=AliasChoices("cartao_declarado_reais", "cartao", "valcart", "card"),
        description="Total declarado em cartoes de credito e debito / TEF",
    )
    pix_declarado_reais: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias=AliasChoices("pix_declarado_reais", "pix", "valpix"),
        description="Total declarado em recebimentos instantaneos PIX",
    )
    prazo_declarado_reais: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias=AliasChoices("prazo_declarado_reais", "prazo", "valnotpra", "faturado"),
        description="Total declarado em faturamento a prazo ou convenios",
    )
    convenio_cheque_reais: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias=AliasChoices("convenio_cheque_reais", "convenio_cheque", "convenio", "cheque"),
        description="Total declarado em convenios corporativos e cheques",
    )
    venda_combustivel_reais: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias=AliasChoices("venda_combustivel_reais", "venda_combustivel", "combustivel_reais"),
        description="Total de faturamento apurado em combustiveis",
    )
    venda_produtos_reais: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias=AliasChoices("venda_produtos_reais", "venda_produtos", "produtos_reais"),
        description="Total de faturamento apurado em produtos e conveniencia",
    )
    litros_declarados: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias=AliasChoices("litros_declarados", "litros"),
        description="Total de litros declarados",
    )
    movimentos: list[UniversalCashMovement] = Field(
        default_factory=list,
        validation_alias=AliasChoices("movimentos", "sangrias_suprimentos", "cash_movements"),
        description="Lista de movimentacoes avulsas de sangrias e suprimentos",
    )

    @property
    def usuario_id(self) -> str:
        return self.operador_id

    @property
    def funcionario_id(self) -> str:
        return self.operador_id

    @property
    def nome_operador(self) -> str:
        return self.operador_nome

    @property
    def sessao_id(self) -> str:
        return self.caixa_id

    @property
    def terminal_id(self) -> str:
        return self.caixa_id

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
        "dinheiro_declarado_reais",
        "cartao_declarado_reais",
        "pix_declarado_reais",
        "prazo_declarado_reais",
        "convenio_cheque_reais",
        "venda_combustivel_reais",
        "venda_produtos_reais",
        "litros_declarados",
        mode="before",
    )
    @classmethod
    def _validate_positive_floats(cls, v: Any) -> float:
        return parse_float_safe(v, default=0.0, allow_negative=False)

    @field_validator("quebra_sobra_reais", mode="before")
    @classmethod
    def _validate_quebra_sobra(cls, v: Any) -> float:
        return parse_float_safe(v, default=0.0, allow_negative=True)

    @field_validator("pdv", "caixa_id", mode="before")
    @classmethod
    def _validate_shift_ids(cls, v: Any) -> str:
        return parse_str_safe(v, default="1")

    @field_validator("fechado", mode="before")
    @classmethod
    def _validate_fechado(cls, v: Any) -> bool:
        if isinstance(v, str):
            clean = v.strip().upper()
            return clean in ("S", "SIM", "TRUE", "1", "FECHADO")
        return bool(v) if v is not None else True

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


# Alias de retrocompatibilidade estrita
UniversalCashierShift = UniversalCashierSession


class UniversalFinancialSettlement(AUDSBaseModel):
    """Contrato canonico universal para recebiveis de cartoes/TEF, PIX e taxas MDR.
    
    Permite auditar a erosao de margem frente a taxas contratadas vs descontadas,
    prazos de compensacao D+N e custo de antecipacao via taxa Selic.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="ignore",
        populate_by_name=True,
    )

    liquidacao_id: str = Field(
        default="0",
        validation_alias=AliasChoices(
            "liquidacao_id", "id", "settlement_id", "nsu", "codigo_autorizacao", "doc_id", "numdoc"
        ),
        description="Identificador unico da transacao ou lote de recebiveis",
    )
    timestamp_transacao: datetime = Field(
        default_factory=datetime.now,
        validation_alias=AliasChoices(
            "timestamp_transacao", "data_hora", "timestamp", "data_venda", "data_transacao"
        ),
        description="Data e hora em que a venda foi realizada no terminal",
    )
    timestamp_liquidacao_prevista: datetime | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "timestamp_liquidacao_prevista", "data_liquidacao", "data_prevista", "data_credito", "vencimento"
        ),
        description="Data prevista para o credito na conta bancaria do lojista",
    )
    timestamp_liquidacao_real: datetime | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "timestamp_liquidacao_real", "data_pagamento", "data_baixa", "data_efetiva"
        ),
        description="Data real em que o valor foi creditado",
    )
    adquirente_ou_banco: str = Field(
        default="OUTROS",
        validation_alias=AliasChoices(
            "adquirente_ou_banco", "adquirente", "banco", "credenciadora", "operadora", "acquirer"
        ),
        description="Nome da adquirente ou instituicao financeira (Stone, Cielo, Rede, PagBank, Banco do Brasil)",
    )
    bandeira: str | None = Field(
        default=None,
        validation_alias=AliasChoices("bandeira", "brand", "card_brand"),
        description="Bandeira do cartao ou modalidade (Visa, Mastercard, Elo, Hipercard, PIX)",
    )
    modalidade: str = Field(
        default="debito",
        validation_alias=AliasChoices(
            "modalidade", "tipo_liquidacao", "payment_method", "modalidade_pagamento"
        ),
        description="Modalidade de liquidacao (debito, credito_vista, credito_parcelado, pix, boleto)",
    )
    parcela_atual: int = Field(
        default=1,
        ge=1,
        validation_alias=AliasChoices("parcela_atual", "parcela", "num_parcela"),
        description="Numero da parcela atual",
    )
    total_parcelas: int = Field(
        default=1,
        ge=1,
        validation_alias=AliasChoices("total_parcelas", "qtd_parcelas", "parcelas"),
        description="Numero total de parcelas da transacao",
    )
    valor_bruto_reais: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias=AliasChoices(
            "valor_bruto_reais", "valor_bruto", "amount_gross", "valor_venda", "valor"
        ),
        description="Valor nominal bruto faturado na transacao",
    )
    taxa_mdr_contratada_pct: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias=AliasChoices(
            "taxa_mdr_contratada_pct", "taxa_contratada_pct", "mdr_contratada", "fee_rate_contracted"
        ),
        description="Taxa percentual de intermediacao contratada formalmente",
    )
    taxa_mdr_real_pct: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias=AliasChoices(
            "taxa_mdr_real_pct", "taxa_real_pct", "mdr_real", "fee_rate_actual"
        ),
        description="Taxa percentual efetivamente descontada pela credenciadora",
    )
    desconto_taxa_reais: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias=AliasChoices(
            "desconto_taxa_reais", "valor_taxa_reais", "fee_amount", "desconto_adquirente"
        ),
        description="Valor monetario da taxa retida pela credenciadora",
    )
    valor_liquido_reais: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias=AliasChoices(
            "valor_liquido_reais", "valor_liquido", "net_amount", "valor_creditado"
        ),
        description="Valor monetario liquido que entra na conta do lojista",
    )
    prazo_dias_compensacao: int = Field(
        default=1,
        ge=0,
        validation_alias=AliasChoices(
            "prazo_dias_compensacao", "prazo_dn", "d_plus_n", "dias_compensacao"
        ),
        description="Prazo contratual de liquidacao em dias (D+0, D+1, D+30)",
    )
    status_liquidacao: str = Field(
        default="PENDENTE",
        validation_alias=AliasChoices("status_liquidacao", "status", "estado"),
        description="Status do recebivel (PENDENTE, LIQUIDADO, CANCELADO, ESTORNADO, CONTESTADO)",
    )
    codigo_venda_origem: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "codigo_venda_origem", "venda_id", "cupom_id", "id_cupom", "sale_id"
        ),
        description="Identificador da venda ou cupom fiscal gerador do recebivel",
    )
    custo_antecipacao_reais: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias=AliasChoices("custo_antecipacao_reais", "custo_antecipacao", "tarifa_antecipacao"),
        description="Custo financeiro cobrado para antecipacao de recebiveis",
    )
    divergencia_taxa_reais: float = Field(
        default=0.0,
        validation_alias=AliasChoices("divergencia_taxa_reais", "divergencia_taxa", "perda_taxa"),
        description="Diferenca monetaria cobrada a maior em relacao ao contrato",
    )

    @property
    def taxa_divergente(self) -> bool:
        """Indica se a taxa cobrada diverge da contratada alem da margem de arredondamento."""
        diff_pct = abs(self.taxa_mdr_real_pct - self.taxa_mdr_contratada_pct)
        return diff_pct > 0.005 or self.divergencia_taxa_reais > 0.05

    @property
    def perda_divergencia_reais(self) -> float:
        """Retorna o valor monetario da perda financeira por divergencia de taxa."""
        if self.divergencia_taxa_reais > 0:
            return round(self.divergencia_taxa_reais, 2)
        desconto_esperado = self.valor_bruto_reais * (self.taxa_mdr_contratada_pct / 100.0)
        perda = self.desconto_taxa_reais - desconto_esperado
        return round(max(0.0, perda), 2)

    @field_validator("liquidacao_id", mode="before")
    @classmethod
    def _validate_liquidacao_id(cls, v: Any) -> str:
        return parse_str_safe(v, default="0")

    @field_validator("adquirente_ou_banco", mode="before")
    @classmethod
    def _validate_adquirente(cls, v: Any) -> str:
        return parse_str_safe(v, default="OUTROS")

    @field_validator("timestamp_transacao", mode="before")
    @classmethod
    def _validate_ts_transacao(cls, v: Any) -> datetime:
        return parse_datetime_safe(v)

    @field_validator("timestamp_liquidacao_prevista", "timestamp_liquidacao_real", mode="before")
    @classmethod
    def _validate_optional_ts(cls, v: Any) -> datetime | None:
        if v is None:
            return None
        return parse_datetime_safe(v)

    @field_validator(
        "valor_bruto_reais",
        "taxa_mdr_contratada_pct",
        "taxa_mdr_real_pct",
        "desconto_taxa_reais",
        "valor_liquido_reais",
        "custo_antecipacao_reais",
        mode="before",
    )
    @classmethod
    def _validate_positive_floats(cls, v: Any) -> float:
        return parse_float_safe(v, default=0.0, allow_negative=False)

    @field_validator("divergencia_taxa_reais", mode="before")
    @classmethod
    def _validate_divergencia(cls, v: Any) -> float:
        return parse_float_safe(v, default=0.0, allow_negative=True)

    @field_validator("parcela_atual", "total_parcelas", "prazo_dias_compensacao", mode="before")
    @classmethod
    def _validate_ints(cls, v: Any) -> int:
        try:
            if v is None:
                return 1
            return int(v)
        except (ValueError, TypeError):
            return 1

    @model_validator(mode="before")
    @classmethod
    def _compute_financial_reconciliation(cls, data: Any) -> Any:
        if isinstance(data, dict):
            bruto = parse_float_safe(
                extract_first_present(data, ("valor_bruto_reais", "valor_bruto", "amount_gross", "valor_venda", "valor")),
                default=0.0,
                allow_negative=False,
            )
            taxa_real = parse_float_safe(
                extract_first_present(data, ("taxa_mdr_real_pct", "taxa_real_pct", "mdr_real", "fee_rate_actual")),
                default=0.0,
                allow_negative=False,
            )
            taxa_cont = parse_float_safe(
                extract_first_present(data, ("taxa_mdr_contratada_pct", "taxa_contratada_pct", "mdr_contratada", "fee_rate_contracted")),
                default=0.0,
                allow_negative=False,
            )
            desc = parse_float_safe(
                extract_first_present(data, ("desconto_taxa_reais", "valor_taxa_reais", "fee_amount", "desconto_adquirente")),
                default=0.0,
                allow_negative=False,
            )
            liq = parse_float_safe(
                extract_first_present(data, ("valor_liquido_reais", "valor_liquido", "net_amount", "valor_creditado")),
                default=0.0,
                allow_negative=False,
            )

            # Se desconto monetario nao foi informado mas temos taxa percentual real
            if desc == 0.0 and taxa_real > 0.0 and bruto > 0.0:
                desc = round(bruto * (taxa_real / 100.0), 2)
                data["desconto_taxa_reais"] = desc

            # Se valor liquido nao foi informado
            if liq == 0.0 and bruto > 0.0:
                data["valor_liquido_reais"] = round(bruto - desc, 2)

            # Se taxa real nao foi informada mas temos desconto monetario
            if taxa_real == 0.0 and desc > 0.0 and bruto > 0.0:
                data["taxa_mdr_real_pct"] = round((desc / bruto) * 100.0, 3)

            # Calculo automatico da divergencia monetaria
            if taxa_cont > 0.0 and bruto > 0.0:
                desc_esperado = round(bruto * (taxa_cont / 100.0), 2)
                diff = round(desc - desc_esperado, 2)
                if "divergencia_taxa_reais" not in data or data["divergencia_taxa_reais"] == 0.0:
                    data["divergencia_taxa_reais"] = diff

        return data


__all__ = [
    "AUDSBaseModel",
    "CashMovementType",
    "PaymentType",
    "UniversalCashMovement",
    "UniversalCashierSession",
    "UniversalCashierShift",
    "UniversalDispenserLog",
    "UniversalEquipmentTelemetry",
    "UniversalFinancialSettlement",
    "UniversalInventoryNode",
    "UniversalPaymentMethod",
    "UniversalSaleItem",
    "UniversalSaleReceipt",
    "UniversalSaleTransaction",
    "UniversalTankReading",
]
