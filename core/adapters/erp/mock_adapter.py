"""Adaptador ERP Mock em Memoria (AUPS).

AURA Universal Posto Schema (AUPS): Bloco 2 (Open Posto Architecture).
Fornece geracao deterministica e ultra-rapida de dados de posto para testes unitarios.
Opera 100% em memoria sem conexao de rede ou banco fisico.
"""

from __future__ import annotations

import threading
from datetime import date, datetime
from typing import Any

from core.adapters.erp.base import (
    BaseERPAdapter,
    ERPConnectionError,
    ERPQueryError,
    normalize_date_filter,
)
from core.domain.base import strip_accents
from core.domain.cashier import UniversalCashierShift
from core.domain.pumps import UniversalDispenserLog
from core.domain.sales import (
    UniversalPaymentMethod,
    UniversalSaleItem,
    UniversalSaleReceipt,
)
from core.domain.tanks import UniversalTankReading


def _to_comparable_timestamp(dt: datetime) -> float:
    """Converte datetime naive ou aware para timestamp float comparavel."""
    if dt.tzinfo is not None:
        return dt.timestamp()
    return dt.astimezone().timestamp()


def _to_local_date(dt: date | datetime) -> date:
    """Extrai date do calendario com ajuste de timezone local se necessario."""
    if isinstance(dt, datetime):
        if dt.tzinfo is not None:
            return dt.astimezone().date()
        return dt.date()
    return dt


class MockERPAdapter(BaseERPAdapter):
    """Adaptador de ERP Mock em memoria com dados canonicos realistas.

    Gera massa deterministica de vendas (cestas de conveniencia e combustiveis),
    tanques com telemetria, bicos com encerrantes e turnos de caixa com quebra/sobra.
    Thread-safe com locks reentrantes e tempo de execucao em sub-milisegundo (< 0.1s).
    """

    def __init__(
        self,
        sales: list[UniversalSaleReceipt] | None = None,
        tanks: list[UniversalTankReading] | None = None,
        pumps: list[UniversalDispenserLog] | None = None,
        shifts: list[UniversalCashierShift] | None = None,
        catalog: list[UniversalSaleItem] | None = None,
        is_connected: bool = True,
        latency_ms: float = 0.5,
    ) -> None:
        """Inicializa o adaptador mock com dados customizados ou deterministicos padrao."""
        self._lock = threading.RLock()
        self._is_connected = is_connected
        self._latency_ms = latency_ms

        if sales is not None:
            self._sales = list(sales)
        else:
            self._sales = self._generate_default_sales()

        if tanks is not None:
            self._tanks = list(tanks)
        else:
            self._tanks = self._generate_default_tanks()

        if pumps is not None:
            self._pumps = list(pumps)
        else:
            self._pumps = self._generate_default_pumps()

        if shifts is not None:
            self._shifts = list(shifts)
        else:
            self._shifts = self._generate_default_shifts()

        if catalog is not None:
            self._catalog = list(catalog)
        else:
            self._catalog = self._generate_default_catalog()

    @property
    def adapter_name(self) -> str:
        """Nome identificador do adaptador mock."""
        return "Mock ERP Adapter (In-Memory AUPS)"

    @property
    def is_connected(self) -> bool:
        """Indica se o adaptador mock esta operando em modo conectado."""
        with self._lock:
            return self._is_connected

    @is_connected.setter
    def is_connected(self, value: bool) -> None:
        """Permite alternar o estado de conectividade para simulacao de falhas."""
        with self._lock:
            self._is_connected = bool(value)

    def set_connected(self, status: bool) -> None:
        """Helper explicito para alternar conexao em suites de teste."""
        with self._lock:
            self._is_connected = bool(status)

    def connect(self) -> bool:
        """Estabelece conexao com a fonte de dados em memoria."""
        with self._lock:
            self._is_connected = True
            return True

    def disconnect(self) -> None:
        """Finaliza conexao com a fonte de dados em memoria."""
        with self._lock:
            self._is_connected = False

    def reset(self) -> None:
        """Restaura os dados mock para a massa deterministica padrao."""
        with self._lock:
            self._is_connected = True
            self._latency_ms = 0.5
            self._sales = self._generate_default_sales()
            self._tanks = self._generate_default_tanks()
            self._pumps = self._generate_default_pumps()
            self._shifts = self._generate_default_shifts()
            self._catalog = self._generate_default_catalog()

    def add_sale(self, sale: UniversalSaleReceipt) -> None:
        """Adiciona um cupom de venda a base em memoria."""
        with self._lock:
            self._sales.append(sale)

    def add_tank_reading(self, reading: UniversalTankReading) -> None:
        """Adiciona uma leitura de tanque a base em memoria."""
        with self._lock:
            self._tanks.append(reading)

    def add_pump_dispense(self, dispense: UniversalDispenserLog) -> None:
        """Adiciona um fechamento de bico a base em memoria."""
        with self._lock:
            self._pumps.append(dispense)

    def add_cashier_shift(self, shift: UniversalCashierShift) -> None:
        """Adiciona um fechamento de turno de caixa a base em memoria."""
        with self._lock:
            self._shifts.append(shift)

    def add_catalog_item(self, item: UniversalSaleItem) -> None:
        """Adiciona um item ao catalogo em memoria."""
        with self._lock:
            self._catalog.append(item)

    def get_recent_sales(
        self,
        start_date: str | date | datetime | None = None,
        end_date: str | date | datetime | None = None,
        limit: int = 100,
        include_cancelled: bool = False,
    ) -> list[UniversalSaleReceipt]:
        """Consulta cupons de venda em memoria com suporte a filtro de datas e limites.

        Retorna registros ordenados do mais recente para o mais antigo (data_hora desc).
        """
        with self._lock:
            if not self._is_connected:
                raise ERPConnectionError(
                    f"Adaptador '{self.adapter_name}' desconectado. Falha na consulta de vendas."
                )

            if limit <= 0:
                return []

            try:
                s_date = normalize_date_filter(start_date)
                e_date = normalize_date_filter(end_date)
            except ValueError as err:
                raise ERPQueryError(
                    f"Parametro de data invalido para consulta de vendas: {err}"
                ) from err

            if s_date and e_date and s_date > e_date:
                return []

            filtered: list[UniversalSaleReceipt] = []
            for receipt in self._sales:
                is_canc = str(receipt.status).upper() in ("CANCELADA", "C", "CANCELADO")
                if not include_cancelled and is_canc:
                    continue
                rec_date = _to_local_date(receipt.data_hora)
                if s_date and rec_date < s_date:
                    continue
                if e_date and rec_date > e_date:
                    continue
                filtered.append(receipt)

            filtered.sort(
                key=lambda r: _to_comparable_timestamp(r.data_hora),
                reverse=True,
            )

            return filtered[:limit]

    def get_tank_inventory(self) -> list[UniversalTankReading]:
        """Retorna telemetria atual dos tanques de combustivel em memoria."""
        with self._lock:
            if not self._is_connected:
                raise ERPConnectionError(
                    f"Adaptador '{self.adapter_name}' desconectado. Falha na leitura de estoques."
                )
            return list(self._tanks)

    def get_pump_dispenses(
        self,
        start_date: str | date | datetime | None = None,
        end_date: str | date | datetime | None = None,
        limit: int = 100,
    ) -> list[UniversalDispenserLog]:
        """Consulta medicoes de encerrantes dos bicos dispensadores com filtros.

        Retorna registros ordenados do mais recente para o mais antigo (timestamp_registro desc).
        """
        with self._lock:
            if not self._is_connected:
                raise ERPConnectionError(
                    f"Adaptador '{self.adapter_name}' desconectado. Falha na consulta de bicos."
                )

            if limit <= 0:
                return []

            try:
                s_date = normalize_date_filter(start_date)
                e_date = normalize_date_filter(end_date)
            except ValueError as err:
                raise ERPQueryError(
                    f"Parametro de data invalido para consulta de bicos: {err}"
                ) from err

            if s_date and e_date and s_date > e_date:
                return []

            filtered: list[UniversalDispenserLog] = []
            for dispense in self._pumps:
                disp_date = _to_local_date(dispense.timestamp_registro)
                if s_date and disp_date < s_date:
                    continue
                if e_date and disp_date > e_date:
                    continue
                filtered.append(dispense)

            filtered.sort(
                key=lambda d: _to_comparable_timestamp(d.timestamp_registro),
                reverse=True,
            )

            return filtered[:limit]

    def get_cashier_shifts(
        self,
        target_date: str | date | datetime | None = None,
        limit: int = 50,
    ) -> list[UniversalCashierShift]:
        """Consulta fechamentos de turno de caixa com filtro opcional por data de movimento.

        Retorna turnos ordenados por data e fechamento mais recente (data_movimento desc).
        """
        with self._lock:
            if not self._is_connected:
                raise ERPConnectionError(
                    f"Adaptador '{self.adapter_name}' desconectado. Falha na consulta de turnos."
                )

            if limit <= 0:
                return []

            try:
                t_date = normalize_date_filter(target_date)
            except ValueError as err:
                raise ERPQueryError(
                    f"Parametro de data invalido para consulta de turnos: {err}"
                ) from err

            filtered: list[UniversalCashierShift] = []
            for shift in self._shifts:
                if t_date and shift.data_movimento != t_date:
                    continue
                filtered.append(shift)

            filtered.sort(
                key=lambda s: (
                    s.data_movimento,
                    _to_comparable_timestamp(
                        s.timestamp_fechamento or s.timestamp_abertura
                    ),
                ),
                reverse=True,
            )

            return filtered[:limit]

    def get_product_catalog(
        self,
        filter_term: str | None = None,
        category: str | None = None,
        limit: int = 100,
    ) -> list[UniversalSaleItem]:
        """Busca itens no catalogo de produtos com filtros textuais e categorizacao."""
        with self._lock:
            if not self._is_connected:
                raise ERPConnectionError(
                    f"Adaptador '{self.adapter_name}' desconectado. Falha na consulta de catalogo."
                )

            if limit <= 0:
                return []

            term_clean = strip_accents(filter_term).strip().lower() if filter_term else None
            cat_clean = strip_accents(category).strip().lower() if category else None

            filtered: list[UniversalSaleItem] = []
            for item in self._catalog:
                if term_clean:
                    name_clean = strip_accents(item.descricao_produto).lower()
                    sku_clean = strip_accents(item.sku).lower()
                    if term_clean not in name_clean and term_clean not in sku_clean:
                        continue
                if cat_clean:
                    item_cat_clean = strip_accents(item.grupo_comercial).lower()
                    if cat_clean not in item_cat_clean:
                        continue
                filtered.append(item)

            return filtered[:limit]

    def check_health(self) -> dict[str, Any]:
        """Retorna diagnostico de saude operacional do adaptador mock."""
        with self._lock:
            return {
                "status": "healthy" if self._is_connected else "unhealthy",
                "latency_ms": self._latency_ms,
                "latencia": self._latency_ms,
                "is_connected": self._is_connected,
                "conectividade": self._is_connected,
                "mode": "mock_in_memory",
                "modo": "mock_in_memory",
                "adapter_name": self.adapter_name,
                "sales_count": len(self._sales),
                "tank_readings_count": len(self._tanks),
                "pump_dispenses_count": len(self._pumps),
                "cashier_shifts_count": len(self._shifts),
                "catalog_items_count": len(self._catalog),
            }

    # Geradores deterministicos de dados realistas AUPS

    def _generate_default_sales(self) -> list[UniversalSaleReceipt]:
        """Gera massa deterministica de vendas para testes analiticos e de cesta."""
        return [
            UniversalSaleReceipt(
                cupom_id="CUPOM_20261014_001",
                data_hora=datetime(2026, 10, 14, 8, 30, 0),
                pdv="1",
                status="CONCLUIDA",
                operador="CARLOS_PDV",
                itens=[
                    UniversalSaleItem(
                        sku="CONV_03",
                        descricao_produto="Cafe Expresso 50ml",
                        grupo_comercial="CONVENIENCIA",
                        preco_unitario_reais=5.00,
                        quantidade=1.0,
                        total_item_reais=5.00,
                    ),
                    UniversalSaleItem(
                        sku="CONV_04",
                        descricao_produto="Pao de Queijo Tradicional",
                        grupo_comercial="CONVENIENCIA",
                        preco_unitario_reais=6.50,
                        quantidade=1.0,
                        total_item_reais=6.50,
                    ),
                    UniversalSaleItem(
                        sku="CONV_01",
                        descricao_produto="Agua Mineral Sem Gas 500ml",
                        grupo_comercial="CONVENIENCIA",
                        preco_unitario_reais=3.50,
                        quantidade=2.0,
                        total_item_reais=7.00,
                    ),
                ],
                pagamentos=[
                    UniversalPaymentMethod(
                        codigo_forma_pagamento="03",
                        descricao_forma="Cartao Debito Elo",
                        tipo="debito",
                        valor_reais=18.50,
                    )
                ],
                total_reais=18.50,
            ),
            UniversalSaleReceipt(
                cupom_id="CUPOM_20261014_002",
                data_hora=datetime(2026, 10, 14, 9, 15, 0),
                pdv="1",
                status="CONCLUIDA",
                operador="JOAO_PISTA",
                itens=[
                    UniversalSaleItem(
                        sku="COMB_01",
                        descricao_produto="Gasolina Comum",
                        grupo_comercial="COMBUSTIVEIS",
                        preco_unitario_reais=5.89,
                        quantidade=35.0,
                        total_item_reais=206.15,
                    ),
                    UniversalSaleItem(
                        sku="LUB_02",
                        descricao_produto="Aditivo de Combustivel Flex 200ml",
                        grupo_comercial="LUBRIFICANTES",
                        preco_unitario_reais=32.00,
                        quantidade=1.0,
                        total_item_reais=32.00,
                    ),
                ],
                pagamentos=[
                    UniversalPaymentMethod(
                        codigo_forma_pagamento="02",
                        descricao_forma="Cartao Credito Visa",
                        tipo="credito",
                        valor_reais=238.15,
                    )
                ],
                total_reais=238.15,
            ),
            UniversalSaleReceipt(
                cupom_id="CUPOM_20261014_003",
                data_hora=datetime(2026, 10, 14, 11, 45, 0),
                pdv="2",
                status="CONCLUIDA",
                operador="MARCOS_PISTA",
                itens=[
                    UniversalSaleItem(
                        sku="COMB_04",
                        descricao_produto="Diesel S10",
                        grupo_comercial="COMBUSTIVEIS",
                        preco_unitario_reais=6.15,
                        quantidade=120.0,
                        total_item_reais=738.00,
                    ),
                ],
                pagamentos=[
                    UniversalPaymentMethod(
                        codigo_forma_pagamento="05",
                        descricao_forma="Faturado a Prazo Frota",
                        tipo="prazo",
                        valor_reais=738.00,
                    )
                ],
                total_reais=738.00,
            ),
            UniversalSaleReceipt(
                cupom_id="CUPOM_20261015_001",
                data_hora=datetime(2026, 10, 15, 14, 10, 0),
                pdv="1",
                status="CONCLUIDA",
                operador="MARIA_CAIXA",
                itens=[
                    UniversalSaleItem(
                        sku="CONV_02",
                        descricao_produto="Refrigerante Cola Lata 350ml",
                        grupo_comercial="CONVENIENCIA",
                        preco_unitario_reais=6.00,
                        quantidade=1.0,
                        total_item_reais=6.00,
                    ),
                    UniversalSaleItem(
                        sku="CONV_06",
                        descricao_produto="Salgado Assado Frango",
                        grupo_comercial="CONVENIENCIA",
                        preco_unitario_reais=9.00,
                        quantidade=1.0,
                        total_item_reais=9.00,
                    ),
                ],
                pagamentos=[
                    UniversalPaymentMethod(
                        codigo_forma_pagamento="04",
                        descricao_forma="PIX Banco Central",
                        tipo="pix",
                        valor_reais=15.00,
                    )
                ],
                total_reais=15.00,
            ),
            UniversalSaleReceipt(
                cupom_id="CUPOM_20261015_002",
                data_hora=datetime(2026, 10, 15, 16, 30, 0),
                pdv="1",
                status="CONCLUIDA",
                operador="JOAO_PISTA",
                itens=[
                    UniversalSaleItem(
                        sku="COMB_03",
                        descricao_produto="Etanol Hidratado",
                        grupo_comercial="COMBUSTIVEIS",
                        preco_unitario_reais=3.99,
                        quantidade=40.0,
                        total_item_reais=159.60,
                    ),
                ],
                pagamentos=[
                    UniversalPaymentMethod(
                        codigo_forma_pagamento="01",
                        descricao_forma="Dinheiro em Especie",
                        tipo="dinheiro",
                        valor_reais=159.60,
                    )
                ],
                total_reais=159.60,
            ),
            UniversalSaleReceipt(
                cupom_id="CUPOM_20261015_003",
                data_hora=datetime(2026, 10, 15, 18, 0, 0),
                pdv="1",
                status="CONCLUIDA",
                operador="CARLOS_PDV",
                itens=[
                    UniversalSaleItem(
                        sku="LUB_01",
                        descricao_produto="Oleo Sintetico 5W30 1L",
                        grupo_comercial="LUBRIFICANTES",
                        preco_unitario_reais=45.00,
                        quantidade=1.0,
                        total_item_reais=45.00,
                    ),
                    UniversalSaleItem(
                        sku="CONV_05",
                        descricao_produto="Energetico Lata 473ml",
                        grupo_comercial="CONVENIENCIA",
                        preco_unitario_reais=12.00,
                        quantidade=2.0,
                        total_item_reais=24.00,
                    ),
                ],
                pagamentos=[
                    UniversalPaymentMethod(
                        codigo_forma_pagamento="02",
                        descricao_forma="Cartao Credito Master",
                        tipo="credito",
                        valor_reais=69.00,
                    )
                ],
                total_reais=69.00,
            ),
            UniversalSaleReceipt(
                cupom_id="CUPOM_20261015_CANC01",
                data_hora=datetime(2026, 10, 15, 18, 30, 0),
                pdv="1",
                status="CANCELADA",
                operador="CARLOS_PDV",
                motivo_cancelamento="Cupom fiscal de combustivel cancelado apos conclusao do abastecimento",
                itens=[
                    UniversalSaleItem(
                        sku="COMB_01",
                        descricao_produto="Gasolina Comum",
                        grupo_comercial="COMBUSTIVEIS",
                        preco_unitario_reais=5.89,
                        quantidade=20.0,
                        total_item_reais=117.80,
                    ),
                ],
                pagamentos=[
                    UniversalPaymentMethod(
                        codigo_forma_pagamento="01",
                        descricao_forma="Dinheiro em Especie",
                        tipo="dinheiro",
                        valor_reais=117.80,
                    )
                ],
                total_reais=117.80,
            ),
        ]

    def _generate_default_tanks(self) -> list[UniversalTankReading]:
        """Gera medicoes deterministicas de tanques com estoque e percentual."""
        return [
            UniversalTankReading(
                identificador_tanque="1",
                combustivel="Gasolina Comum",
                codigo_lmc="420101001",
                bicos_conectados=["1"],
                timestamp_leitura=datetime(2026, 10, 15, 18, 0, 0),
                volume_atual_litros=15420.0,
                volume_agua_mm=0.0,
                temperatura_celsius=24.5,
                percentual_capacidade=77.10,
                capacidade_nominal_litros=20000.0,
                saldo_inicial_litros=17000.0,
                saldo_final_litros=15420.0,
                tem_medicao_fisica=True,
            ),
            UniversalTankReading(
                identificador_tanque="2",
                combustivel="Gasolina Aditivada",
                codigo_lmc="420101002",
                bicos_conectados=["2"],
                timestamp_leitura=datetime(2026, 10, 15, 18, 0, 0),
                volume_atual_litros=8200.0,
                volume_agua_mm=0.0,
                temperatura_celsius=24.8,
                percentual_capacidade=54.67,
                capacidade_nominal_litros=15000.0,
                saldo_inicial_litros=9000.0,
                saldo_final_litros=8200.0,
                tem_medicao_fisica=True,
            ),
            UniversalTankReading(
                identificador_tanque="3",
                combustivel="Etanol Hidratado",
                codigo_lmc="420102001",
                bicos_conectados=["4"],
                timestamp_leitura=datetime(2026, 10, 15, 18, 0, 0),
                volume_atual_litros=9850.0,
                volume_agua_mm=2.0,
                temperatura_celsius=23.9,
                percentual_capacidade=65.67,
                capacidade_nominal_litros=15000.0,
                saldo_inicial_litros=10500.0,
                saldo_final_litros=9850.0,
                tem_medicao_fisica=True,
            ),
            UniversalTankReading(
                identificador_tanque="4",
                combustivel="Diesel S10",
                codigo_lmc="420103001",
                bicos_conectados=["3"],
                timestamp_leitura=datetime(2026, 10, 15, 18, 0, 0),
                volume_atual_litros=21500.0,
                volume_agua_mm=0.0,
                temperatura_celsius=25.1,
                percentual_capacidade=71.67,
                capacidade_nominal_litros=30000.0,
                saldo_inicial_litros=24000.0,
                saldo_final_litros=21500.0,
                tem_medicao_fisica=True,
            ),
        ]

    def _generate_default_pumps(self) -> list[UniversalDispenserLog]:
        """Gera medicoes deterministicas de encerrantes de pista."""
        return [
            UniversalDispenserLog(
                identificador_bomba="1",
                identificador_bico="1",
                identificador_tanque="1",
                codigo_combustivel="COMB_01",
                descricao_combustivel="Gasolina Comum",
                turno_descricao="MANHA",
                pdv="1",
                timestamp_registro=datetime(2026, 10, 14, 22, 0, 0),
                encerrante_inicial_litros=124500.0,
                encerrante_final_litros=126100.0,
                volume_aferido_litros=20.0,
                preco_unitario_reais=5.89,
                total_faturado_reais=9306.20,
                qtd_abastecimentos=42,
                volume_automacao_litros=1580.0,
                total_automacao_reais=9306.20,
            ),
            UniversalDispenserLog(
                identificador_bomba="1",
                identificador_bico="2",
                identificador_tanque="2",
                codigo_combustivel="COMB_02",
                descricao_combustivel="Gasolina Aditivada",
                turno_descricao="MANHA",
                pdv="1",
                timestamp_registro=datetime(2026, 10, 14, 22, 0, 0),
                encerrante_inicial_litros=89200.0,
                encerrante_final_litros=90350.0,
                volume_aferido_litros=10.0,
                preco_unitario_reais=6.19,
                total_faturado_reais=4548.60,
                qtd_abastecimentos=25,
                volume_automacao_litros=1140.0,
                total_automacao_reais=4548.60,
            ),
            UniversalDispenserLog(
                identificador_bomba="2",
                identificador_bico="3",
                identificador_tanque="4",
                codigo_combustivel="COMB_04",
                descricao_combustivel="Diesel S10",
                turno_descricao="MANHA",
                pdv="2",
                timestamp_registro=datetime(2026, 10, 15, 22, 0, 0),
                encerrante_inicial_litros=241000.0,
                encerrante_final_litros=244200.0,
                volume_aferido_litros=20.0,
                preco_unitario_reais=6.15,
                total_faturado_reais=19557.00,
                qtd_abastecimentos=38,
                volume_automacao_litros=3180.0,
                total_automacao_reais=19557.00,
            ),
            UniversalDispenserLog(
                identificador_bomba="2",
                identificador_bico="4",
                identificador_tanque="3",
                codigo_combustivel="COMB_03",
                descricao_combustivel="Etanol Hidratado",
                turno_descricao="MANHA",
                pdv="2",
                timestamp_registro=datetime(2026, 10, 15, 22, 0, 0),
                encerrante_inicial_litros=63400.0,
                encerrante_final_litros=64150.0,
                volume_aferido_litros=0.0,
                preco_unitario_reais=3.99,
                total_faturado_reais=4612.50,
                qtd_abastecimentos=20,
                volume_automacao_litros=750.0,
                total_automacao_reais=4612.50,
            ),
        ]

    def _generate_default_shifts(self) -> list[UniversalCashierShift]:
        """Gera fechamentos deterministicos de turno com cenarios de quebra e sobra."""
        return [
            UniversalCashierShift(
                caixa_id="1",
                pdv="1",
                fechado=True,
                operador_id="101",
                operador_nome="JOAO_SILVA",
                turno_descricao="MANHA",
                data_movimento=date(2026, 10, 14),
                timestamp_abertura=datetime(2026, 10, 14, 6, 0, 0),
                timestamp_fechamento=datetime(2026, 10, 14, 14, 0, 0),
                fundo_troco_reais=200.00,
                dinheiro_declarado_reais=1580.00,
                cartao_declarado_reais=2500.00,
                prazo_declarado_reais=300.00,
                convenio_cheque_reais=200.00,
                venda_combustivel_reais=4200.00,
                venda_produtos_reais=395.00,
                litros_declarados=800.0,
                total_declarado_reais=4580.00,
                total_sistema_reais=4595.00,
                quebra_sobra_reais=-15.00,
            ),
            UniversalCashierShift(
                caixa_id="2",
                pdv="1",
                fechado=True,
                operador_id="102",
                operador_nome="MARIA_SOUZA",
                turno_descricao="TARDE",
                data_movimento=date(2026, 10, 14),
                timestamp_abertura=datetime(2026, 10, 14, 14, 0, 0),
                timestamp_fechamento=datetime(2026, 10, 14, 22, 0, 0),
                fundo_troco_reais=200.00,
                dinheiro_declarado_reais=1820.00,
                cartao_declarado_reais=3000.00,
                prazo_declarado_reais=300.00,
                convenio_cheque_reais=200.00,
                venda_combustivel_reais=4800.00,
                venda_produtos_reais=520.00,
                litros_declarados=950.0,
                total_declarado_reais=5320.00,
                total_sistema_reais=5320.00,
                quebra_sobra_reais=0.00,
            ),
            UniversalCashierShift(
                caixa_id="3",
                pdv="1",
                fechado=True,
                operador_id="103",
                operador_nome="CARLOS_OLIVEIRA",
                turno_descricao="MANHA",
                data_movimento=date(2026, 10, 15),
                timestamp_abertura=datetime(2026, 10, 15, 6, 0, 0),
                timestamp_fechamento=datetime(2026, 10, 15, 14, 0, 0),
                fundo_troco_reais=200.00,
                dinheiro_declarado_reais=1690.00,
                cartao_declarado_reais=2700.00,
                prazo_declarado_reais=300.00,
                convenio_cheque_reais=200.00,
                venda_combustivel_reais=4400.00,
                venda_produtos_reais=475.00,
                litros_declarados=860.0,
                total_declarado_reais=4890.00,
                total_sistema_reais=4875.00,
                quebra_sobra_reais=15.00,
            ),
            UniversalCashierShift(
                caixa_id="4",
                pdv="1",
                fechado=True,
                operador_id="104",
                operador_nome="ANA_PEREIRA",
                turno_descricao="TARDE",
                data_movimento=date(2026, 10, 15),
                timestamp_abertura=datetime(2026, 10, 15, 14, 0, 0),
                timestamp_fechamento=datetime(2026, 10, 15, 22, 0, 0),
                fundo_troco_reais=200.00,
                dinheiro_declarado_reais=2100.00,
                cartao_declarado_reais=3400.00,
                prazo_declarado_reais=350.00,
                convenio_cheque_reais=250.00,
                venda_combustivel_reais=5500.00,
                venda_produtos_reais=600.00,
                litros_declarados=1100.0,
                total_declarado_reais=6100.00,
                total_sistema_reais=6100.00,
                quebra_sobra_reais=0.00,
            ),
        ]

    def _generate_default_catalog(self) -> list[UniversalSaleItem]:
        """Gera catalogo deterministico de combustiveis, lubrificantes e conveniencia."""
        return [
            UniversalSaleItem(
                sku="COMB_01",
                descricao_produto="Gasolina Comum",
                grupo_comercial="COMBUSTIVEIS",
                preco_unitario_reais=5.89,
                quantidade=1.0,
                total_item_reais=5.89,
            ),
            UniversalSaleItem(
                sku="COMB_02",
                descricao_produto="Gasolina Aditivada",
                grupo_comercial="COMBUSTIVEIS",
                preco_unitario_reais=6.15,
                quantidade=1.0,
                total_item_reais=6.15,
            ),
            UniversalSaleItem(
                sku="COMB_03",
                descricao_produto="Etanol Hidratado",
                grupo_comercial="COMBUSTIVEIS",
                preco_unitario_reais=3.99,
                quantidade=1.0,
                total_item_reais=3.99,
            ),
            UniversalSaleItem(
                sku="COMB_04",
                descricao_produto="Diesel S10",
                grupo_comercial="COMBUSTIVEIS",
                preco_unitario_reais=6.15,
                quantidade=1.0,
                total_item_reais=6.15,
            ),
            UniversalSaleItem(
                sku="LUB_01",
                descricao_produto="Oleo Sintetico 5W30 1L",
                grupo_comercial="LUBRIFICANTES",
                preco_unitario_reais=45.00,
                quantidade=1.0,
                total_item_reais=45.00,
            ),
            UniversalSaleItem(
                sku="LUB_02",
                descricao_produto="Aditivo de Combustivel Flex 200ml",
                grupo_comercial="LUBRIFICANTES",
                preco_unitario_reais=32.00,
                quantidade=1.0,
                total_item_reais=32.00,
            ),
            UniversalSaleItem(
                sku="LUB_03",
                descricao_produto="Fluido de Freio DOT4 500ml",
                grupo_comercial="LUBRIFICANTES",
                preco_unitario_reais=28.00,
                quantidade=1.0,
                total_item_reais=28.00,
            ),
            UniversalSaleItem(
                sku="CONV_01",
                descricao_produto="Agua Mineral Sem Gas 500ml",
                grupo_comercial="CONVENIENCIA",
                preco_unitario_reais=3.50,
                quantidade=1.0,
                total_item_reais=3.50,
            ),
            UniversalSaleItem(
                sku="CONV_02",
                descricao_produto="Refrigerante Cola Lata 350ml",
                grupo_comercial="CONVENIENCIA",
                preco_unitario_reais=6.00,
                quantidade=1.0,
                total_item_reais=6.00,
            ),
            UniversalSaleItem(
                sku="CONV_03",
                descricao_produto="Cafe Expresso 50ml",
                grupo_comercial="CONVENIENCIA",
                preco_unitario_reais=5.00,
                quantidade=1.0,
                total_item_reais=5.00,
            ),
            UniversalSaleItem(
                sku="CONV_04",
                descricao_produto="Pao de Queijo Tradicional",
                grupo_comercial="CONVENIENCIA",
                preco_unitario_reais=6.50,
                quantidade=1.0,
                total_item_reais=6.50,
            ),
            UniversalSaleItem(
                sku="CONV_05",
                descricao_produto="Energetico Lata 473ml",
                grupo_comercial="CONVENIENCIA",
                preco_unitario_reais=12.00,
                quantidade=1.0,
                total_item_reais=12.00,
            ),
            UniversalSaleItem(
                sku="CONV_06",
                descricao_produto="Salgado Assado Frango",
                grupo_comercial="CONVENIENCIA",
                preco_unitario_reais=9.00,
                quantidade=1.0,
                total_item_reais=9.00,
            ),
        ]
