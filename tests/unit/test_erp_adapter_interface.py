"""Testes Unitarios da Interface do Adaptador ERP e Mock (Bloco 2).

AURA Universal Posto Schema (AUPS): ERP Port e Open Posto Architecture.
Valida:
1. Impossibilidade de instanciacao direta de BaseERPAdapter (TypeError).
2. Conformidade total do MockERPAdapter com a interface abstrata.
3. Retorno de objetos canônicos universais validos de core/domain/.
4. Filtros temporais, limites numericos e busca textual/categorial no catalogo.
5. Diagnostico de saude (check_health), latencia, conectividade e simulacao de desconexao.
6. Geracao de dados realistas (cesta com multiplos itens, quebra/sobra de caixa, encerrantes).
7. Ausencia estrita de travessoes e performance sub-segundo (< 0.3s).
"""

from __future__ import annotations

import time
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pytest

from core.adapters.erp.base import (
    BaseERPAdapter,
    ERPAdapterError,
    ERPConnectionError,
    ERPQueryError,
    normalize_date_filter,
)
from core.adapters.erp.mock_adapter import MockERPAdapter
from core.domain.cashier import UniversalCashierShift
from core.domain.pumps import UniversalDispenserLog
from core.domain.sales import (
    UniversalPaymentMethod,
    UniversalSaleItem,
    UniversalSaleReceipt,
)
from core.domain.tanks import UniversalTankReading


class TestBaseERPAdapterInterface:
    """Suite de testes do contrato formal BaseERPAdapter."""

    def test_base_erp_adapter_cannot_be_instantiated(self) -> None:
        """Garante que a classe abstrata BaseERPAdapter nao pode ser instanciada."""
        with pytest.raises(TypeError) as exc_info:
            BaseERPAdapter()  # type: ignore[abstract]
        error_msg = str(exc_info.value)
        assert "Can't instantiate abstract class BaseERPAdapter" in error_msg
        assert "abstract method" in error_msg

    def test_incomplete_subclass_cannot_be_instantiated(self) -> None:
        """Garante que subclasses incompletas falham ao serem instanciadas."""

        class IncompleteAdapter(BaseERPAdapter):
            @property
            def adapter_name(self) -> str:
                return "Incomplete"

            # Faltam todos os outros metodos abstratos e propriedades

        with pytest.raises(TypeError) as exc_info:
            IncompleteAdapter()  # type: ignore[abstract]
        assert "abstract method" in str(exc_info.value)

    def test_complete_minimal_subclass_can_be_instantiated(self) -> None:
        """Garante que uma subclasse concreta que implementa todos os metodos funciona."""

        class ConcreteMinimalAdapter(BaseERPAdapter):
            @property
            def adapter_name(self) -> str:
                return "Minimal"

            @property
            def is_connected(self) -> bool:
                return True

            def get_recent_sales(
                self,
                start_date: str | date | None = None,
                end_date: str | date | None = None,
                limit: int = 100,
            ) -> list[UniversalSaleReceipt]:
                return []

            def get_tank_inventory(self) -> list[UniversalTankReading]:
                return []

            def get_pump_dispenses(
                self,
                start_date: str | date | None = None,
                end_date: str | date | None = None,
                limit: int = 100,
            ) -> list[UniversalDispenserLog]:
                return []

            def get_cashier_shifts(
                self,
                target_date: str | date | None = None,
                limit: int = 50,
            ) -> list[UniversalCashierShift]:
                return []

            def get_product_catalog(
                self,
                filter_term: str | None = None,
                category: str | None = None,
                limit: int = 100,
            ) -> list[UniversalSaleItem]:
                return []

            def check_health(self) -> dict[str, Any]:
                return {"status": "healthy"}

        adapter = ConcreteMinimalAdapter()
        assert adapter.adapter_name == "Minimal"
        assert adapter.is_connected is True
        assert adapter.get_recent_sales() == []
        assert adapter.check_health() == {"status": "healthy"}

    def test_erp_exceptions_hierarchy(self) -> None:
        """Garante que as excecoes herdam corretamente de ERPAdapterError."""
        assert issubclass(ERPAdapterError, Exception)
        assert issubclass(ERPConnectionError, ERPAdapterError)
        assert issubclass(ERPQueryError, ERPAdapterError)
        err = ERPQueryError("Erro de consulta no ERP")
        assert isinstance(err, ERPAdapterError)
        assert isinstance(err, Exception)

    def test_context_manager_lifecycle(self) -> None:
        """Testa o ciclo de vida do adaptador com gerenciador de contexto (with)."""
        adapter = MockERPAdapter()
        with adapter as ctx:
            assert ctx is adapter
            assert ctx.is_connected is True
        assert adapter.is_connected is False

    def test_connect_and_disconnect_explicit(self) -> None:
        """Testa abertura e fechamento explicitos de conexao."""
        mock = MockERPAdapter()
        assert mock.is_connected is True
        mock.disconnect()
        assert mock.is_connected is False
        mock.connect()
        assert mock.is_connected is True


class TestNormalizeDateFilter:
    """Suite de validacao do utilitario de normalizacao de datas."""

    def test_normalize_date_filter_variants(self) -> None:
        """Testa conversao de date, datetime, string ISO e brasileira."""
        assert normalize_date_filter(None) is None
        assert normalize_date_filter("") is None
        assert normalize_date_filter("   ") is None

        d = date(2026, 10, 15)
        assert normalize_date_filter(d) == d

        dt = datetime(2026, 10, 15, 14, 30, 0)
        assert normalize_date_filter(dt) == d

        assert normalize_date_filter("2026-10-15") == d
        assert normalize_date_filter("15/10/2026") == d
        assert normalize_date_filter("15/10/2026 14:30:00") == d

    def test_normalize_date_filter_invalid_format_raises(self) -> None:
        """Garante que formatos invalidos lancam ValueError em vez de fallback silencioso."""
        with pytest.raises(ValueError):
            normalize_date_filter("data_invalida")
        with pytest.raises(ValueError):
            normalize_date_filter("2026-99-99")
        with pytest.raises(ValueError):
            normalize_date_filter("32/13/2026")


class TestMockERPAdapterConformity:
    """Suite de conformidade do MockERPAdapter com o protocolo AUPS."""

    def test_mock_adapter_implements_base_erp_adapter(self) -> None:
        """Garante que MockERPAdapter herda e cumpre a interface BaseERPAdapter."""
        mock = MockERPAdapter()
        assert isinstance(mock, BaseERPAdapter)
        assert isinstance(mock.adapter_name, str)
        assert len(mock.adapter_name) > 0
        assert mock.is_connected is True

    def test_check_health_structure(self) -> None:
        """Valida a estrutura do dicionario retornado por check_health()."""
        mock = MockERPAdapter()
        health = mock.check_health()

        assert isinstance(health, dict)
        assert "status" in health
        assert health["status"] == "healthy"
        assert "latency_ms" in health or "latencia" in health
        assert "is_connected" in health or "conectividade" in health
        assert "mode" in health or "modo" in health
        assert health["is_connected"] is True
        assert health["mode"] == "mock_in_memory"

    def test_disconnection_and_error_simulation(self) -> None:
        """Valida comportamento em estado desconectado."""
        mock = MockERPAdapter()
        mock.set_connected(False)
        assert mock.is_connected is False

        health = mock.check_health()
        assert health["status"] == "unhealthy"
        assert health["is_connected"] is False

        with pytest.raises(ERPConnectionError):
            mock.get_recent_sales()

        with pytest.raises(ERPConnectionError):
            mock.get_tank_inventory()

        with pytest.raises(ERPConnectionError):
            mock.get_pump_dispenses()

        with pytest.raises(ERPConnectionError):
            mock.get_cashier_shifts()

        with pytest.raises(ERPConnectionError):
            mock.get_product_catalog()

        # Reconexao
        mock.is_connected = True
        assert mock.is_connected is True
        assert len(mock.get_recent_sales()) > 0


class TestMockERPAdapterSales:
    """Suite de validacao das consultas de vendas e itens faturados."""

    def test_get_recent_sales_default_data(self) -> None:
        """Valida que o retorno padrao contem cupons validos com itens e pagamentos."""
        mock = MockERPAdapter()
        sales = mock.get_recent_sales()

        assert len(sales) >= 5
        for sale in sales:
            assert isinstance(sale, UniversalSaleReceipt)
            assert isinstance(sale.cupom_id, str)
            assert len(sale.cupom_id) > 0
            assert sale.total_reais > 0.0
            assert len(sale.itens) > 0
            for item in sale.itens:
                assert isinstance(item, UniversalSaleItem)
                assert item.total_item_reais > 0.0
            assert len(sale.pagamentos) > 0
            for pag in sale.pagamentos:
                assert isinstance(pag, UniversalPaymentMethod)
                assert pag.valor_reais > 0.0

    def test_basket_multi_item_receipt(self) -> None:
        """Garante a presenca de cupons com cesta de multiplos itens para analises de cross-sell."""
        mock = MockERPAdapter()
        sales = mock.get_recent_sales()
        multi_item_sales = [s for s in sales if len(s.itens) >= 2]
        assert len(multi_item_sales) >= 2

        # Verifica cupom tipico de conveniencia com 3 itens
        convenience_basket = [s for s in sales if len(s.itens) >= 3]
        assert len(convenience_basket) >= 1
        basket = convenience_basket[0]
        skus = [it.sku for it in basket.itens]
        assert "CONV_03" in skus  # Cafe expresso
        assert "CONV_04" in skus  # Pao de queijo
        assert "CONV_01" in skus  # Agua mineral

    def test_sales_filtering_by_date_range(self) -> None:
        """Testa filtros por data inicial, data final e intervalos combinados."""
        mock = MockERPAdapter()

        # Filtrar apenas vendas de 2026-10-14
        sales_14 = mock.get_recent_sales(start_date="2026-10-14", end_date="2026-10-14")
        assert len(sales_14) == 3
        for s in sales_14:
            assert s.data_hora.date() == date(2026, 10, 14)

        # Filtrar apenas vendas de 2026-10-15
        sales_15 = mock.get_recent_sales(start_date=date(2026, 10, 15), end_date=date(2026, 10, 15))
        assert len(sales_15) == 3
        for s in sales_15:
            assert s.data_hora.date() == date(2026, 10, 15)

        # Intervalo amplo cobrindo ambos os dias
        sales_both = mock.get_recent_sales(start_date="2026-10-14", end_date="2026-10-15")
        assert len(sales_both) == 6

        # Intervalo futuro sem registros
        sales_future = mock.get_recent_sales(start_date="2026-11-01")
        assert len(sales_future) == 0

        # Intervalo invertido (start > end) retorna lista vazia
        sales_inverted = mock.get_recent_sales(start_date="2026-10-16", end_date="2026-10-14")
        assert sales_inverted == []

    def test_sales_limiting(self) -> None:
        """Testa aplicacao de limit na consulta de vendas."""
        mock = MockERPAdapter()

        assert len(mock.get_recent_sales(limit=1)) == 1
        assert len(mock.get_recent_sales(limit=2)) == 2
        assert len(mock.get_recent_sales(limit=0)) == 0
        assert len(mock.get_recent_sales(limit=-5)) == 0

    def test_sales_reverse_chronological_ordering(self) -> None:
        """Garante que as vendas sao retornadas da mais recente para a mais antiga."""
        mock = MockERPAdapter()
        recent = mock.get_recent_sales(limit=2)
        assert len(recent) == 2
        assert recent[0].cupom_id == "CUPOM_20261015_003"
        assert recent[1].cupom_id == "CUPOM_20261015_002"
        assert recent[0].data_hora > recent[1].data_hora

    def test_sales_invalid_date_raises_erp_query_error(self) -> None:
        """Garante que datas invalidas na consulta disparam ERPQueryError."""
        mock = MockERPAdapter()
        with pytest.raises(ERPQueryError):
            mock.get_recent_sales(start_date="data_falsa")
        with pytest.raises(ERPQueryError):
            mock.get_recent_sales(end_date="2026-99-99")


class TestMockERPAdapterTanks:
    """Suite de validacao do inventario e telemetria de tanques."""

    def test_get_tank_inventory(self) -> None:
        """Garante que o retorno contem leituras validas de tanques com estoque e percentual."""
        mock = MockERPAdapter()
        tanks = mock.get_tank_inventory()

        assert len(tanks) == 4
        for tank in tanks:
            assert isinstance(tank, UniversalTankReading)
            assert tank.volume_atual_litros > 0.0
            assert 0.0 <= tank.percentual_capacidade <= 100.0
            assert tank.volume_agua_mm >= 0.0
            assert tank.temperatura_celsius is not None
            assert 15.0 <= tank.temperatura_celsius <= 45.0

        tanque_ids = [t.identificador_tanque for t in tanks]
        assert "1" in tanque_ids
        assert "2" in tanque_ids
        assert "3" in tanque_ids
        assert "4" in tanque_ids


class TestMockERPAdapterPumps:
    """Suite de validacao das saidas de bicos e diferencas de encerrante."""

    def test_get_pump_dispenses_default(self) -> None:
        """Valida integridade dos registros de encerrantes e calculo de volume."""
        mock = MockERPAdapter()
        dispenses = mock.get_pump_dispenses()

        assert len(dispenses) == 4
        for disp in dispenses:
            assert isinstance(disp, UniversalDispenserLog)
            assert disp.encerrante_final_litros > disp.encerrante_inicial_litros
            assert disp.volume_vendido_litros > 0.0
            assert disp.total_faturado_reais > 0.0

    def test_pump_dispenses_date_filter_and_limits(self) -> None:
        """Testa filtros de data e limit em leituras de bombas."""
        mock = MockERPAdapter()

        disp_14 = mock.get_pump_dispenses(start_date="2026-10-14", end_date="2026-10-14")
        assert len(disp_14) == 2
        for d in disp_14:
            assert d.timestamp_registro.date() == date(2026, 10, 14)

        disp_15 = mock.get_pump_dispenses(start_date="2026-10-15", end_date="2026-10-15")
        assert len(disp_15) == 2

        assert len(mock.get_pump_dispenses(limit=1)) == 1
        assert len(mock.get_pump_dispenses(limit=0)) == 0

    def test_pumps_reverse_chronological_ordering(self) -> None:
        """Garante que as medicoes de bicos sao retornadas das mais recentes para as mais antigas."""
        mock = MockERPAdapter()
        recent = mock.get_pump_dispenses(limit=2)
        assert len(recent) == 2
        assert recent[0].timestamp_registro >= recent[1].timestamp_registro
        assert recent[0].timestamp_registro.date() == date(2026, 10, 15)

    def test_pump_dispenses_invalid_date_raises_erp_query_error(self) -> None:
        """Garante que filtro de data invalido para bicos dispara ERPQueryError."""
        mock = MockERPAdapter()
        with pytest.raises(ERPQueryError):
            mock.get_pump_dispenses(start_date="data_falsa")


class TestMockERPAdapterCashier:
    """Suite de validacao dos turnos e conciliacao de caixa."""

    def test_get_cashier_shifts_coverage(self) -> None:
        """Garante a cobertura de turnos com fechamento exato, quebra e sobra."""
        mock = MockERPAdapter()
        shifts = mock.get_cashier_shifts()

        assert len(shifts) == 4
        for shift in shifts:
            assert isinstance(shift, UniversalCashierShift)
            assert shift.fundo_troco_reais == 200.00
            assert shift.total_declarado_reais > 0.0
            assert shift.total_sistema_reais > 0.0

        # Verifica cenarios financeiros auditados
        quebras = [s for s in shifts if s.quebra_sobra_reais < 0.0]
        sobras = [s for s in shifts if s.quebra_sobra_reais > 0.0]
        exatos = [s for s in shifts if s.quebra_sobra_reais == 0.0]

        assert len(quebras) == 1
        assert quebras[0].quebra_sobra_reais == -15.00  # Quebra de 15 reais

        assert len(sobras) == 1
        assert sobras[0].quebra_sobra_reais == 15.00  # Sobra de 15 reais

        assert len(exatos) == 2

    def test_cashier_shifts_filtering_by_target_date(self) -> None:
        """Valida filtro por data contabilidade do movimento."""
        mock = MockERPAdapter()

        shifts_14 = mock.get_cashier_shifts(target_date="2026-10-14")
        assert len(shifts_14) == 2
        for s in shifts_14:
            assert s.data_movimento == date(2026, 10, 14)

        shifts_15 = mock.get_cashier_shifts(target_date=date(2026, 10, 15))
        assert len(shifts_15) == 2

        shifts_inexistente = mock.get_cashier_shifts(target_date="2026-12-31")
        assert len(shifts_inexistente) == 0

        assert len(mock.get_cashier_shifts(limit=1)) == 1
        assert len(mock.get_cashier_shifts(limit=0)) == 0

    def test_cashier_shifts_reverse_chronological_ordering(self) -> None:
        """Garante que os turnos de caixa sao ordenados do movimento mais recente para o mais antigo."""
        mock = MockERPAdapter()
        recent = mock.get_cashier_shifts(limit=2)
        assert len(recent) == 2
        assert recent[0].data_movimento == date(2026, 10, 15)
        assert recent[1].data_movimento == date(2026, 10, 15)

    def test_cashier_shifts_invalid_date_raises_erp_query_error(self) -> None:
        """Garante que filtro de data invalido para turnos dispara ERPQueryError."""
        mock = MockERPAdapter()
        with pytest.raises(ERPQueryError):
            mock.get_cashier_shifts(target_date="data_falsa")


class TestMockERPAdapterCatalog:
    """Suite de validacao do catalogo de produtos e combustiveis."""

    def test_get_product_catalog_all(self) -> None:
        """Valida que o catalogo padrao contem todos os itens cadastrados."""
        mock = MockERPAdapter()
        catalog = mock.get_product_catalog()

        assert len(catalog) >= 10
        for item in catalog:
            assert isinstance(item, UniversalSaleItem)
            assert len(item.sku) > 0
            assert len(item.descricao_produto) > 0
            assert item.preco_unitario_reais > 0.0

    def test_catalog_filter_by_term(self) -> None:
        """Testa busca por termo no nome e no SKU com insensibilidade a acentos e caixa."""
        mock = MockERPAdapter()

        # Busca por gasolina (deve retornar Comum e Aditivada)
        gasolinas = mock.get_product_catalog(filter_term="gasolina")
        assert len(gasolinas) == 2
        for g in gasolinas:
            assert "gasolina" in g.descricao_produto.lower()

        # Busca com acento vs sem acento (Cafe vs Café)
        cafe_accent = mock.get_product_catalog(filter_term="Café")
        cafe_no_accent = mock.get_product_catalog(filter_term="cafe")
        assert len(cafe_accent) == 1
        assert len(cafe_no_accent) == 1
        assert cafe_accent[0].sku == "CONV_03"
        assert cafe_no_accent[0].sku == "CONV_03"

        # Busca por SKU
        sku_comb = mock.get_product_catalog(filter_term="COMB_04")
        assert len(sku_comb) == 1
        assert sku_comb[0].descricao_produto == "Diesel S10"

        # Termo inexistente
        assert mock.get_product_catalog(filter_term="PRODUTO_INEXISTENTE_XYZ") == []

    def test_catalog_filter_by_category(self) -> None:
        """Testa filtragem por categoria ou departamento comercial."""
        mock = MockERPAdapter()

        fuels = mock.get_product_catalog(category="COMBUSTIVEIS")
        assert len(fuels) == 4
        for f in fuels:
            assert f.grupo_comercial == "COMBUSTIVEIS"

        convenience = mock.get_product_catalog(category="conveniencia")
        assert len(convenience) == 6
        for c in convenience:
            assert c.grupo_comercial == "CONVENIENCIA"

        lubes = mock.get_product_catalog(category="LUBRIFICANTES")
        assert len(lubes) == 3

    def test_catalog_combined_filter_and_limits(self) -> None:
        """Testa combinacao de termo, categoria e limite."""
        mock = MockERPAdapter()

        # Termo que existe em lubrificantes
        res = mock.get_product_catalog(filter_term="aditivo", category="LUBRIFICANTES")
        assert len(res) == 1
        assert res[0].sku == "LUB_02"

        # Termo que nao bate com a categoria
        res_empty = mock.get_product_catalog(filter_term="gasolina", category="CONVENIENCIA")
        assert res_empty == []

        # Limite
        assert len(mock.get_product_catalog(category="CONVENIENCIA", limit=2)) == 2
        assert len(mock.get_product_catalog(limit=0)) == 0


class TestMockERPAdapterCustomization:
    """Suite de testes para injeção de dados customizados e mutabilidade controlada."""

    def test_instantiation_with_empty_custom_data(self) -> None:
        """Garante que o adaptador mock aceita dados vazios customizados."""
        mock = MockERPAdapter(
            sales=[],
            tanks=[],
            pumps=[],
            shifts=[],
            catalog=[],
            is_connected=True,
            latency_ms=1.2,
        )
        assert mock.get_recent_sales() == []
        assert mock.get_tank_inventory() == []
        assert mock.get_pump_dispenses() == []
        assert mock.get_cashier_shifts() == []
        assert mock.get_product_catalog() == []

        health = mock.check_health()
        assert health["latency_ms"] == 1.2
        assert health["sales_count"] == 0

    def test_add_entities_and_reset(self) -> None:
        """Testa adicao incremental de entidades e operacao de reset."""
        mock = MockERPAdapter(sales=[])
        assert len(mock.get_recent_sales()) == 0

        new_sale = UniversalSaleReceipt(
            cupom_id="CUPOM_TESTE_999",
            data_hora=datetime(2026, 10, 15, 12, 0, 0),
            pdv="1",
            total_reais=50.00,
        )
        mock.add_sale(new_sale)
        assert len(mock.get_recent_sales()) == 1
        assert mock.get_recent_sales()[0].cupom_id == "CUPOM_TESTE_999"

        # Operacao de reset restaura o padrao
        mock.reset()
        assert len(mock.get_recent_sales()) >= 5
        assert mock.is_connected is True


class TestMockERPAdapterConcurrencyAndTimezone:
    """Suite de validacao para fusos horarios e concorrencia multithread."""

    def test_timezone_aware_and_naive_sales_sorting(self) -> None:
        """Garante ordenacao estavel entre datetimes aware (UTC) e naive sem TypeError."""
        mock = MockERPAdapter(sales=[])
        sale_naive = UniversalSaleReceipt(
            cupom_id="CUPOM_NAIVE",
            data_hora=datetime(2026, 10, 15, 10, 0, 0),
            pdv="1",
            total_reais=50.0,
        )
        sale_utc = UniversalSaleReceipt(
            cupom_id="CUPOM_UTC",
            data_hora=datetime(2026, 10, 15, 14, 0, 0, tzinfo=UTC),
            pdv="1",
            total_reais=60.0,
        )
        mock.add_sale(sale_naive)
        mock.add_sale(sale_utc)

        sales = mock.get_recent_sales(limit=10)
        assert len(sales) == 2
        cupom_ids = [s.cupom_id for s in sales]
        assert "CUPOM_NAIVE" in cupom_ids
        assert "CUPOM_UTC" in cupom_ids

    def test_timezone_aware_date_filter(self) -> None:
        """Testa consulta passando start_date e end_date com timezone explicito."""
        mock = MockERPAdapter()
        dt_filter = datetime(2026, 10, 15, 12, 0, 0, tzinfo=UTC)
        sales = mock.get_recent_sales(start_date=dt_filter, end_date=dt_filter)
        assert isinstance(sales, list)
        for s in sales:
            assert s.data_hora.date() == dt_filter.astimezone().date()

    def test_multithreading_concurrent_readers_and_writers(self) -> None:
        """Garante thread-safety sob operacoes concorrentes de leitura e mutacao."""
        import threading

        mock = MockERPAdapter()
        errors: list[Exception] = []

        def reader_task() -> None:
            try:
                for _ in range(30):
                    _ = mock.get_recent_sales(limit=5)
                    _ = mock.get_tank_inventory()
                    _ = mock.get_pump_dispenses(limit=2)
                    _ = mock.get_cashier_shifts(limit=2)
                    _ = mock.check_health()
            except Exception as e:  # noqa: BLE001
                errors.append(e)

        def writer_task() -> None:
            try:
                for i in range(20):
                    new_sale = UniversalSaleReceipt(
                        cupom_id=f"THREAD_SALE_{i}",
                        data_hora=datetime.now(),
                        pdv="9",
                        total_reais=10.0 + i,
                    )
                    mock.add_sale(new_sale)
                    if i % 10 == 0:
                        mock.reset()
            except Exception as e:  # noqa: BLE001
                errors.append(e)

        threads: list[threading.Thread] = []
        for _ in range(5):
            threads.append(threading.Thread(target=reader_task))
        for _ in range(3):
            threads.append(threading.Thread(target=writer_task))

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Erros de concorrencia detectados: {errors}"


class TestBlock2QualityAndPerformance:
    """Suite de qualidade de codigo: ausencia estrita de travessoes e benchmark sub-segundo."""

    def test_zero_travessoes_in_all_block2_files(self) -> None:
        """Garante ausencia absoluta de travessoes (em-dash e en-dash) nos arquivos do Bloco 2."""
        base_dir = Path(__file__).resolve().parent.parent.parent
        files_to_check = [
            base_dir / "core" / "adapters" / "__init__.py",
            base_dir / "core" / "adapters" / "erp" / "__init__.py",
            base_dir / "core" / "adapters" / "erp" / "base.py",
            base_dir / "core" / "adapters" / "erp" / "mock_adapter.py",
            base_dir / "docs" / "roadmap_blindagem_juridica_clean_room.md",
            Path(__file__).resolve(),
        ]

        em_dash = chr(8212)
        en_dash = chr(8211)

        violations: list[str] = []
        for file_path in files_to_check:
            assert file_path.exists(), f"Arquivo nao encontrado: {file_path}"
            content = file_path.read_text(encoding="utf-8")
            for line_no, line in enumerate(content.splitlines(), start=1):
                if em_dash in line:
                    violations.append(f"{file_path.name}:{line_no} contem caractere proibido em-dash: {line}")
                if en_dash in line:
                    violations.append(f"{file_path.name}:{line_no} contem caractere proibido en-dash: {line}")

        assert not violations, "Violacoes da regra de ZERO TRAVESSOES encontradas:\n" + "\n".join(
            violations
        )

    def test_sub_second_performance_benchmark(self) -> None:
        """Garante que a execucao de multiplas consultas do MockERPAdapter ocorre em sub-milisegundo."""
        mock = MockERPAdapter()

        start = time.perf_counter()
        for _ in range(50):
            _ = mock.get_recent_sales(start_date="2026-10-14", limit=10)
            _ = mock.get_tank_inventory()
            _ = mock.get_pump_dispenses(limit=5)
            _ = mock.get_cashier_shifts(target_date="2026-10-14")
            _ = mock.get_product_catalog(filter_term="gasolina")
            _ = mock.check_health()
        elapsed = time.perf_counter() - start

        # 50 iteracoes completas de todos os metodos devem rodar em menos de 0.15 segundos
        assert elapsed < 0.15, f"Benchmark muito lento: {elapsed:.4f}s para 50 ciclos completos"
