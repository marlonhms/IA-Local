"""Testes Unitarios do Dominio Canonico Universal AUPS (Bloco 1).

AURA Universal Posto Schema (AUPS): Dominio Puro Desacoplado.
Valida: instanciacao, imutabilidade, aliases legados, serializacao,
resiliencia a nulos, formatos internacionais e brasileiros,
pureza de drivers de banco, ausencia de travessoes e performance sub-milisegundo.
"""

from __future__ import annotations

import inspect
import math
import time
from datetime import date, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

import core.domain.base
import core.domain.cashier
import core.domain.pumps
import core.domain.sales
import core.domain.tanks
from core.domain import (
    UniversalCashierShift,
    UniversalCashMovement,
    UniversalDispenserLog,
    UniversalPaymentMethod,
    UniversalPump,
    UniversalSaleItem,
    UniversalSaleReceipt,
    UniversalTank,
    UniversalTankReading,
    parse_bool_safe,
    parse_date_safe,
    parse_datetime_safe,
    parse_float_safe,
    parse_str_safe,
)


class TestAUPSDomainSales:
    """Suite de validacao do dominio de vendas e conveniencia."""

    def test_universal_sale_item_instantiation_and_computation(self) -> None:
        """Testa instanciacao de item, aliases legados e calculo de total."""
        # Instanciacao canonica
        item1 = UniversalSaleItem(
            sku="GAS_COMUM",
            descricao_produto="Gasolina Comum",
            grupo_comercial="COMBUSTIVEIS",
            preco_unitario_reais=5.89,
            quantidade=20.0,
            total_item_reais=117.80,
        )
        assert item1.sku == "GAS_COMUM"
        assert item1.quantidade == 20.0
        assert item1.total_item_reais == 117.80

        # Instanciacao via aliases legados de ERP
        item_legacy = UniversalSaleItem.model_validate({
            "codpec": "PROD_001",
            "descpec": "Agua Mineral 500ml",
            "descgrp": "CONVENIENCIA",
            "prcpec": "3,50",
            "qtditem": "3",
        })
        assert item_legacy.sku == "PROD_001"
        assert item_legacy.descricao_produto == "Agua Mineral 500ml"
        assert item_legacy.grupo_comercial == "CONVENIENCIA"
        assert item_legacy.preco_unitario_reais == 3.50
        assert item_legacy.quantidade == 3.0
        # Calculo automatico do total
        assert item_legacy.total_item_reais == 10.50

    def test_universal_sale_item_null_and_type_resilience(self) -> None:
        """Garante que UniversalSaleItem tolera nulos e tipos anomalos sem crash."""
        item = UniversalSaleItem.model_validate({
            "sku": None,
            "descricao_produto": None,
            "grupo_comercial": None,
            "preco_unitario_reais": None,
            "quantidade": None,
            "total_item_reais": None,
        })
        assert item.sku == "SEM_CODIGO"
        assert item.descricao_produto == "PRODUTO DIVERSO"
        assert item.grupo_comercial == "GERAL"
        assert item.preco_unitario_reais == 0.0
        assert item.quantidade == 1.0
        assert item.total_item_reais == 0.0

    def test_universal_payment_method_normalization(self) -> None:
        """Testa normalizacao resiliente de tipos de pagamento."""
        p_cred = UniversalPaymentMethod(
            codigo_forma_pagamento="02",
            descricao_forma="Cartao Visa Credito",
            tipo="Cartão de Crédito",
            valor_reais=100.0,
        )
        assert p_cred.tipo == "credito"

        p_deb = UniversalPaymentMethod.model_validate({
            "codpra": "03",
            "descpra": "Mastercard Debito",
            "tipo": "DEBITO",
            "valpra": "45,50",
        })
        assert p_deb.codigo_forma_pagamento == "03"
        assert p_deb.tipo == "debito"
        assert p_deb.valor_reais == 45.50

        p_pix = UniversalPaymentMethod(
            codigo_forma_pagamento="99",
            descricao_forma="PIX Banco Central",
            tipo="PIX QR Code",
            valor_reais=25.0,
        )
        assert p_pix.tipo == "pix"

        p_dinh = UniversalPaymentMethod(
            codigo_forma_pagamento="01",
            descricao_forma="Dinheiro em Especie",
            tipo="dinheiro",
            valor_reais=50.0,
        )
        assert p_dinh.tipo == "dinheiro"

        p_prazo = UniversalPaymentMethod(
            codigo_forma_pagamento="05",
            descricao_forma="Convenio Frota a Prazo",
            tipo="faturado",
            valor_reais=300.0,
        )
        assert p_prazo.tipo == "prazo"

        p_outro = UniversalPaymentMethod(
            codigo_forma_pagamento="98",
            descricao_forma="Voucher Refeicao",
            tipo="voucher",
            valor_reais=30.0,
        )
        assert p_outro.tipo == "outro"

    def test_universal_payment_method_null_resilience(self) -> None:
        """Garante que UniversalPaymentMethod tolera campos nulos."""
        pay = UniversalPaymentMethod.model_validate({
            "codigo_forma_pagamento": None,
            "descricao_forma": None,
            "tipo": None,
            "valor_reais": None,
        })
        assert pay.codigo_forma_pagamento == "0"
        assert pay.descricao_forma == "OUTROS"
        assert pay.tipo == "outro"
        assert pay.valor_reais == 0.0

    def test_universal_sale_receipt_properties_and_reconciliation(self) -> None:
        """Testa recibo de venda, reconciliacao de totais e properties de id."""
        item = UniversalSaleItem(
            sku="ETANOL",
            descricao_produto="Etanol Hidratado",
            preco_unitario_reais=3.99,
            quantidade=10.0,
        )
        pay = UniversalPaymentMethod(
            codigo_forma_pagamento="01",
            descricao_forma="Dinheiro",
            tipo="dinheiro",
            valor_reais=39.90,
        )

        receipt = UniversalSaleReceipt(
            cupom_id="CUPOM_9876",
            data_hora=datetime(2026, 10, 15, 14, 30),
            pdv="2",
            status="CONCLUIDA",
            operador="CARLOS_SILVA",
            itens=[item],
            pagamentos=[pay],
        )

        assert receipt.cupom_id == "CUPOM_9876"
        assert receipt.venda_id == "CUPOM_9876"
        assert receipt.id == "CUPOM_9876"
        assert receipt.id_cupom == "CUPOM_9876"
        assert receipt.id_pedido == "CUPOM_9876"
        assert receipt.pedido_id == "CUPOM_9876"
        assert receipt.total_reais == 39.90
        assert len(receipt.itens) == 1
        assert len(receipt.pagamentos) == 1

        # Teste de alias legado para cupom
        receipt_legacy = UniversalSaleReceipt.model_validate({
            "numped": "PED_555",
            "dataped": "15/10/2026 15:45:00",
            "numpdv": "3",
            "valped": "150.00",
            "situ": "A",
            "codfren": "MARCOS",
        })
        assert receipt_legacy.cupom_id == "PED_555"
        assert receipt_legacy.venda_id == "PED_555"
        assert receipt_legacy.pdv == "3"
        assert receipt_legacy.total_reais == 150.00
        assert receipt_legacy.operador == "MARCOS"

    def test_universal_sale_receipt_reconciliation_from_raw_dict_items(self) -> None:
        """Garante reconciliacao automatica de totais com itens em dict bruto sem total_item_reais."""
        receipt = UniversalSaleReceipt.model_validate({
            "cupom_id": "C_RAW_01",
            "data_hora": datetime(2026, 10, 15, 10, 0),
            "itens": [
                {
                    "sku": "PROD_A",
                    "descricao_produto": "Produto A",
                    "preco_unitario_reais": 12.50,
                    "quantidade": 2.0,
                },
                {
                    "sku": "PROD_B",
                    "descricao_produto": "Produto B",
                    "preco_unitario_reais": 5.00,
                    "quantidade": 3.0,
                },
            ],
        })
        # 12.50 * 2 + 5.00 * 3 = 25.00 + 15.00 = 40.00
        assert receipt.total_reais == 40.00
        assert receipt.itens[0].total_item_reais == 25.00
        assert receipt.itens[1].total_item_reais == 15.00

    def test_universal_sale_receipt_reconciliation_from_payments_when_no_items(self) -> None:
        """Garante reconciliacao a partir de pagamentos quando itens nao forem detalhados."""
        receipt = UniversalSaleReceipt.model_validate({
            "cupom_id": "C_PAY_01",
            "data_hora": datetime(2026, 10, 15, 11, 0),
            "pagamentos": [
                {"codigo_forma_pagamento": "01", "descricao_forma": "Dinheiro", "valor_reais": 50.0},
                {"codigo_forma_pagamento": "02", "descricao_forma": "PIX", "valor_reais": 35.50},
            ],
        })
        assert receipt.total_reais == 85.50

    def test_universal_sale_receipt_null_tolerance(self) -> None:
        """Garante que UniversalSaleReceipt nao quebra quando banco retorna NULL para colunas."""
        receipt = UniversalSaleReceipt.model_validate({
            "cupom_id": "C_NULL_01",
            "data_hora": None,
            "pdv": None,
            "status": None,
            "operador": None,
            "total_reais": None,
        })
        assert receipt.cupom_id == "C_NULL_01"
        assert isinstance(receipt.data_hora, datetime)
        assert receipt.pdv == "1"
        assert receipt.status == "CONCLUIDA"
        assert receipt.operador == "SISTEMA"
        assert receipt.total_reais == 0.0


class TestAUPSDomainTanks:
    """Suite de validacao do dominio de tanques e estoque."""

    def test_universal_tank_instantiation_and_aliases(self) -> None:
        """Testa criacao de tanque mestre e aliases de banco."""
        tank = UniversalTank(
            identificador_tanque="T01",
            codigo_combustivel="GAS_COM",
            descricao_combustivel="Gasolina Comum",
            capacidade_nominal_litros=30000.0,
        )
        assert tank.identificador_tanque == "T01"
        assert tank.tanque_id == "T01"
        assert tank.id == "T01"
        assert tank.capacidade_nominal_litros == 30000.0
        assert tank.ativo is True

        tank_legacy = UniversalTank.model_validate({
            "codtan": "02",
            "codcomb": "ETAN",
            "desccomb": "Etanol Comum",
            "captan": "15000",
            "ativo": "S",
        })
        assert tank_legacy.identificador_tanque == "02"
        assert tank_legacy.codigo_combustivel == "ETAN"
        assert tank_legacy.capacidade_nominal_litros == 15000.0
        assert tank_legacy.ativo is True

    def test_universal_tank_null_resilience(self) -> None:
        """Garante resiliencia a nulos em UniversalTank."""
        tank = UniversalTank.model_validate({
            "identificador_tanque": None,
            "codigo_combustivel": None,
            "descricao_combustivel": None,
            "capacidade_nominal_litros": None,
            "ativo": None,
        })
        assert tank.identificador_tanque == "0"
        assert tank.codigo_combustivel == "SEM_CODIGO"
        assert tank.descricao_combustivel == "COMBUSTIVEL DIVERSO"
        assert tank.capacidade_nominal_litros == 0.0
        assert tank.ativo is True

    def test_universal_tank_reading_instantiation(self) -> None:
        """Testa leitura pontual de medicao e percentual de capacidade."""
        reading = UniversalTankReading(
            identificador_tanque="T01",
            timestamp_leitura="15/10/2026 06:00:00",
            volume_atual_litros=15000.0,
            volume_agua_mm=0.0,
            temperatura_celsius=24.5,
            percentual_capacidade=50.0,
        )
        assert reading.identificador_tanque == "T01"
        assert reading.tanque_id == "T01"
        assert reading.volume_atual_litros == 15000.0
        assert reading.percentual_capacidade == 50.0
        assert reading.temperatura_celsius == 24.5
        assert reading.volume_agua_mm == 0.0

        # Inferir percentual quando fornecida capacidade nominal nos dados
        reading_inferred = UniversalTankReading.model_validate({
            "tanque": "T02",
            "data_hora": "2026-10-15T07:00:00",
            "volume_atual": 12000.0,
            "capacidade": 24000.0,
        })
        assert reading_inferred.percentual_capacidade == 50.0

    def test_universal_tank_reading_null_and_negative_temp(self) -> None:
        """Testa nulos e temperatura negativa legitima em regiao fria."""
        reading = UniversalTankReading.model_validate({
            "identificador_tanque": "T03",
            "timestamp_leitura": datetime(2026, 7, 10, 4, 0),
            "volume_atual_litros": 8000.0,
            "temperatura_celsius": -1.5,
            "volume_agua_mm": None,
            "percentual_capacidade": None,
        })
        assert reading.temperatura_celsius == -1.5
        assert reading.volume_agua_mm == 0.0
        assert reading.percentual_capacidade == 0.0


class TestAUPSDomainPumps:
    """Suite de validacao do dominio de bombas e bicos."""

    def test_universal_pump_instantiation_and_aliases(self) -> None:
        """Testa configuracao de bomba, bico e tanque."""
        pump = UniversalPump(
            identificador_bomba="B01",
            identificador_bico="BC01",
            codigo_combustivel="GAS_ADIT",
            identificador_tanque="T01",
            descricao_combustivel="Gasolina Aditivada",
        )
        assert pump.identificador_bomba == "B01"
        assert pump.bomba_id == "B01"
        assert pump.identificador_bico == "BC01"
        assert pump.bico_id == "BC01"
        assert pump.tanque_id == "T01"
        assert pump.ativo is True

        pump_legacy = UniversalPump.model_validate({
            "codbom": "02",
            "codbic": "03",
            "codcomb": "DIESEL_S10",
            "codtan": "04",
            "ativo": "1",
        })
        assert pump_legacy.identificador_bomba == "02"
        assert pump_legacy.identificador_bico == "03"
        assert pump_legacy.ativo is True

    def test_universal_pump_null_resilience(self) -> None:
        """Garante resiliencia a nulos em UniversalPump."""
        pump = UniversalPump.model_validate({
            "identificador_bomba": None,
            "identificador_bico": None,
            "codigo_combustivel": None,
            "identificador_tanque": None,
            "descricao_combustivel": None,
            "ativo": None,
        })
        assert pump.identificador_bomba == "0"
        assert pump.identificador_bico == "0"
        assert pump.codigo_combustivel == "SEM_CODIGO"
        assert pump.identificador_tanque == "0"
        assert pump.descricao_combustivel is None
        assert pump.ativo is True

    def test_universal_dispenser_log_computation(self) -> None:
        """Testa log de encerrante e property de volume vendido."""
        log = UniversalDispenserLog(
            identificador_bomba="B01",
            identificador_bico="BC01",
            timestamp_registro=datetime(2026, 10, 15, 22, 0),
            encerrante_inicial_litros=10000.0,
            encerrante_final_litros=10550.0,
            volume_aferido_litros=10.0,
            total_faturado_reais=3186.0,
        )
        # Volume vendido liquido = 10550 - 10000 - 10 = 540.0 L
        assert log.volume_vendido_litros == 540.0
        assert log.total_faturado_reais == 3186.0
        assert log.bomba_id == "B01"
        assert log.bico_id == "BC01"

        # Tratamento de afericao zero e aliases legados
        log_legacy = UniversalDispenserLog.model_validate({
            "codbom": "01",
            "codbic": "02",
            "datareg": "15/10/2026 22:30:00",
            "encini": "5000,00",
            "encfim": "5200,00",
            "volafe": "0,00",
        })
        assert log_legacy.volume_vendido_litros == 200.0


class TestAUPSDomainCashier:
    """Suite de validacao do dominio de operadores e caixa."""

    def test_universal_cashier_shift_calculations(self) -> None:
        """Testa calculo de quebra/sobra e manipulacao de datas de turno."""
        shift = UniversalCashierShift(
            operador_id="OP_101",
            operador_nome="Joao Pereira",
            turno_descricao="MANHA",
            data_movimento="15/10/2026",
            timestamp_abertura="15/10/2026 06:00:00",
            timestamp_fechamento="15/10/2026 14:00:00",
            fundo_troco_reais=200.0,
            total_declarado_reais=4500.0,
            total_sistema_reais=4550.0,
        )
        assert shift.data_movimento == date(2026, 10, 15)
        # Quebra calculada automaticamente: 4500 - 4550 = -50.00
        assert shift.quebra_sobra_reais == -50.0
        assert shift.usuario_id == "OP_101"
        assert shift.funcionario_id == "OP_101"
        assert shift.nome_operador == "Joao Pereira"

        # Quebra passada explicitamente deve ser respeitada
        shift_explicit = UniversalCashierShift(
            operador_id="OP_102",
            operador_nome="Maria Silva",
            turno_descricao="TARDE",
            data_movimento=date(2026, 10, 15),
            timestamp_abertura=datetime(2026, 10, 15, 14, 0),
            total_declarado_reais=1000.0,
            total_sistema_reais=1000.0,
            quebra_sobra_reais=0.0,
        )
        assert shift_explicit.quebra_sobra_reais == 0.0

    def test_universal_cashier_shift_null_quebra_sobra_inference(self) -> None:
        """Garante que quebra_sobra_reais e calculada mesmo se o payload contiver quebra_sobra_reais: None."""
        shift = UniversalCashierShift.model_validate({
            "operador_id": "OP_200",
            "operador_nome": "Marcos",
            "turno_descricao": "NOITE",
            "data_movimento": "20/12/2025 14:30:00",
            "timestamp_abertura": "20/12/2025 18:00:00",
            "total_declarado_reais": "1.000,00",
            "total_sistema_reais": "1.250,00",
            "quebra_sobra_reais": None,
        })
        # Data extraida corretamente de string com hora preservando ano 2025
        assert shift.data_movimento == date(2025, 12, 20)
        # 1000 - 1250 = -250.00
        assert shift.quebra_sobra_reais == -250.0

    def test_universal_cash_movement_normalization(self) -> None:
        """Testa normalizacao de sangrias e suprimentos."""
        mov_sang = UniversalCashMovement(
            tipo_movimento="SANGRIA_COFRE",
            valor_reais=1500.0,
            justificativa="Recolhimento para cofre boca de lobo",
            timestamp_movimento=datetime(2026, 10, 15, 11, 30),
            operador_id="OP_101",
            pdv="1",
        )
        assert mov_sang.tipo_movimento == "sangria"
        assert mov_sang.usuario_id == "OP_101"
        assert mov_sang.funcionario_id == "OP_101"

        mov_sup = UniversalCashMovement(
            tipo_movimento="Reforco de Troco",
            valor_reais="200,00",
            timestamp_movimento="15/10/2026 09:00:00",
            operador_id="OP_101",
            justificativa=None,
            pdv=None,
        )
        assert mov_sup.tipo_movimento == "suprimento"
        assert mov_sup.valor_reais == 200.0
        assert mov_sup.justificativa == ""
        assert mov_sup.pdv == "1"


class TestAUPSConvertersAndRobustness:
    """Suite de validacao dos conversores seguros contra corrupcao e formatos internacionais."""

    def test_parse_float_safe_international_and_brazilian(self) -> None:
        """Garante que converte tanto formato brasileiro quanto formato americano/internacional."""
        assert parse_float_safe("1.234,56") == 1234.56
        assert parse_float_safe("1,234.56") == 1234.56
        assert parse_float_safe("1,234,567.89") == 1234567.89
        assert parse_float_safe("1.234.567,89") == 1234567.89
        assert parse_float_safe("R$ 50,00") == 50.0
        assert parse_float_safe("R$ 50.00") == 50.0
        assert parse_float_safe(None, default=10.0) == 10.0
        assert parse_float_safe("invalido", default=0.0) == 0.0

    def test_parse_float_safe_nan_and_inf_protection(self) -> None:
        """Garante protecao contra NaN e Inf."""
        assert parse_float_safe(float("nan"), default=0.0) == 0.0
        assert parse_float_safe(float("inf"), default=0.0) == 0.0
        assert parse_float_safe(float("-inf"), default=0.0) == 0.0
        assert not math.isnan(parse_float_safe(float("nan")))

    def test_parse_datetime_safe_and_millisecond_timestamp(self) -> None:
        """Garante parsing de datas ISO, brasileiras e timestamps em milissegundos."""
        dt_ms = parse_datetime_safe(1760527800000)
        assert isinstance(dt_ms, datetime)
        assert dt_ms.year >= 2025

        dt_iso = parse_datetime_safe("2026-10-15T14:30:00")
        assert dt_iso == datetime(2026, 10, 15, 14, 30, 0)

        dt_br = parse_datetime_safe("15/10/2026 14:30:00")
        assert dt_br == datetime(2026, 10, 15, 14, 30, 0)

    def test_parse_date_safe_with_timestamp_and_time_component(self) -> None:
        """Garante que strings com hora nao corrompem a data de referencia."""
        d1 = parse_date_safe("20/12/2025 14:30:00")
        assert d1 == date(2025, 12, 20)

        d2 = parse_date_safe("2025-12-20T14:30:00")
        assert d2 == date(2025, 12, 20)

        d3 = parse_date_safe("2025-12-20")
        assert d3 == date(2025, 12, 20)

    def test_parse_bool_safe(self) -> None:
        """Garante conversoes flexiveis de booleanos de ERPs."""
        assert parse_bool_safe("S") is True
        assert parse_bool_safe("sim") is True
        assert parse_bool_safe("1") is True
        assert parse_bool_safe(1) is True
        assert parse_bool_safe("N") is False
        assert parse_bool_safe("nao") is False
        assert parse_bool_safe("0") is False
        assert parse_bool_safe(0) is False
        assert parse_bool_safe(None, default=True) is True
        assert parse_bool_safe(None, default=False) is False

    def test_parse_str_safe(self) -> None:
        """Garante limpeza de strings e aplicacao de default seguro."""
        assert parse_str_safe(None, default="DEFAULT") == "DEFAULT"
        assert parse_str_safe("   ", default="DEFAULT") == "DEFAULT"
        assert parse_str_safe(101, default="DEFAULT") == "101"
        assert parse_str_safe("  Texto Valido  ") == "Texto Valido"


class TestAUPSImmutabilityAndSerialization:
    """Suite de imutabilidade e serializacao Pydantic v2."""

    def test_immutability_enforcement(self) -> None:
        """Garante que todas as entidades AUPS rejeitam mutacoes de estado."""
        receipt = UniversalSaleReceipt(
            cupom_id="C01",
            data_hora=datetime.now(),
            total_reais=100.0,
        )
        with pytest.raises(ValidationError):
            receipt.total_reais = 200.0

        tank = UniversalTank(
            identificador_tanque="T01",
            codigo_combustivel="GAS",
            descricao_combustivel="Gasolina",
            capacidade_nominal_litros=10000.0,
        )
        with pytest.raises(ValidationError):
            tank.capacidade_nominal_litros = 20000.0

        pump = UniversalPump(
            identificador_bomba="B1",
            identificador_bico="BC1",
            codigo_combustivel="GAS",
            identificador_tanque="T1",
        )
        with pytest.raises(ValidationError):
            pump.ativo = False

        shift = UniversalCashierShift(
            operador_id="OP1",
            operador_nome="Operador",
            turno_descricao="MANHA",
            data_movimento=date.today(),
            timestamp_abertura=datetime.now(),
        )
        with pytest.raises(ValidationError):
            shift.total_declarado_reais = 50.0

    def test_serialization_and_deserialization_fidelity(self) -> None:
        """Garante fidelidade bidirecional na serializacao dict e JSON."""
        item = UniversalSaleItem(
            sku="LUB_01",
            descricao_produto="Oleo Motor 5W30",
            grupo_comercial="LUBRIFICANTES",
            preco_unitario_reais=45.0,
            quantidade=2.0,
            total_item_reais=90.0,
        )
        data_dict = item.model_dump()
        assert data_dict["sku"] == "LUB_01"
        assert data_dict["total_item_reais"] == 90.0

        json_str = item.model_dump_json()
        assert "LUB_01" in json_str

        # Reconstrucao identica a partir de JSON
        rebuilt = UniversalSaleItem.model_validate_json(json_str)
        assert rebuilt == item


class TestAUPSArchitectureAndPerformance:
    """Suite de arquitetura clean room, pureza e desempenho sub-milisegundo."""

    def test_pure_domain_no_database_driver_imports(self) -> None:
        """Garante isolamento arquitetural Clean Room: zero drivers de banco no dominio."""
        domain_modules = [
            core.domain.base,
            core.domain.sales,
            core.domain.tanks,
            core.domain.pumps,
            core.domain.cashier,
        ]
        forbidden_drivers = ["psycopg2", "sqlite3", "sqlalchemy", "asyncpg", "mysql"]

        for mod in domain_modules:
            source = inspect.getsource(mod)
            for driver in forbidden_drivers:
                assert f"import {driver}" not in source, (
                    f"Violacao de Clean Room: {mod.__name__} importa driver {driver}"
                )
                assert f"from {driver}" not in source, (
                    f"Violacao de Clean Room: {mod.__name__} importa de {driver}"
                )

    def test_zero_travessoes_compliance(self) -> None:
        """Garante a regra inegociavel de zero travessoes (em-dash e en-dash)."""
        domain_dir = Path(__file__).resolve().parent.parent.parent / "core" / "domain"
        test_file = Path(__file__).resolve()

        files_to_check = list(domain_dir.glob("*.py")) + [test_file]
        assert len(files_to_check) >= 6

        forbidden_chars = ["\u2014", "\u2013"]
        for file_path in files_to_check:
            content = file_path.read_text(encoding="utf-8")
            for char in forbidden_chars:
                assert char not in content, (
                    f"Violacao da regra ZERO TRAVESSOES: caractere {char!r} encontrado em {file_path.name}"
                )

    def test_performance_sub_millisecond(self) -> None:
        """Garante que a instanciacao das entidades AUPS execute em tempo sub-milisegundo."""
        iterations = 1000
        start = time.perf_counter()

        for i in range(iterations):
            _ = UniversalSaleItem(
                sku=f"SKU_{i}",
                descricao_produto="Item Benchmark",
                preco_unitario_reais=10.0,
                quantidade=2.0,
            )

        elapsed = time.perf_counter() - start
        avg_ms_per_op = (elapsed / iterations) * 1000.0

        # Sub-milisegundo significa avg < 1.0 ms por operacao
        assert avg_ms_per_op < 1.0, (
            f"Performance de instanciacao lenta: {avg_ms_per_op:.4f} ms por entidade (esperado < 1.0 ms)"
        )
