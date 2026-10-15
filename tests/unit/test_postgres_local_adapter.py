"""Testes Unitarios do Driver PostgreSQL Local - Data Mapper (AUPS Bloco 3).

AURA Universal Posto Schema (AUPS): Bloco 3.
Valida:
1. Instanciacao, propriedades e conformidade com BaseERPAdapter.
2. Leitura real contra PostgreSQL local (quando online) retornando instancias AUPS.
3. Fallback automatico e calibrado para MockERPAdapter (quando offline ou erro).
4. Filtros de data, limites e buscas por termo e categoria no catalogo.
5. Diagnostico de saude (check_health), latencia, contagem de registros e modo operacional.
6. Resiliencia a falhas e excecoes (ERPQueryError e ERPConnectionError).
7. Ausencia estrita de travessoes (zero em-dash e en-dash) e performance sub-segundo.
"""

from __future__ import annotations

import time
from datetime import date, datetime
from pathlib import Path
from unittest.mock import patch

import psycopg2
import pytest

from core.adapters.erp import (
    BaseERPAdapter,
    ERPConnectionError,
    ERPQueryError,
    MockERPAdapter,
    PostgresLocalERPAdapter,
)
from core.domain.cashier import UniversalCashierShift
from core.domain.pumps import UniversalDispenserLog
from core.domain.sales import (
    UniversalPaymentMethod,
    UniversalSaleItem,
    UniversalSaleReceipt,
)
from core.domain.tanks import UniversalTankReading


class TestPostgresLocalAdapterInitialization:
    """Suite de inicializacao, ciclo de vida e propriedades do PostgresLocalERPAdapter."""

    def test_adapter_inheritance_and_properties(self) -> None:
        """Garante que PostgresLocalERPAdapter herda de BaseERPAdapter e possui propriedades corretas."""
        adapter = PostgresLocalERPAdapter()
        assert isinstance(adapter, BaseERPAdapter)
        assert adapter.adapter_name == "Postgres Local ERP Adapter (Data Mapper)"
        assert isinstance(adapter.db_role, str)
        assert len(adapter.db_role) > 0
        assert adapter.force_offline is False
        assert adapter.fallback_on_error is True
        assert isinstance(adapter.fallback_adapter, MockERPAdapter)

    def test_custom_parameters_initialization(self) -> None:
        """Garante suporte a parametros customizados de contingencia e fallback."""
        custom_fallback = MockERPAdapter()
        adapter = PostgresLocalERPAdapter(
            fallback_adapter=custom_fallback,
            fallback_on_error=False,
            force_offline=True,
        )
        assert adapter.fallback_adapter is custom_fallback
        assert adapter.fallback_on_error is False
        assert adapter.force_offline is True
        assert adapter.is_connected is False

    def test_force_offline_setter(self) -> None:
        """Testa alternancia dinamica da flag force_offline."""
        adapter = PostgresLocalERPAdapter()
        original_status = adapter.is_connected
        adapter.force_offline = True
        assert adapter.is_connected is False
        adapter.force_offline = False
        assert adapter.is_connected == original_status

    def test_context_manager_lifecycle(self) -> None:
        """Testa operacao segura dentro de gerenciador de contexto (with)."""
        with PostgresLocalERPAdapter() as adapter:
            assert isinstance(adapter, PostgresLocalERPAdapter)
            assert adapter.adapter_name == "Postgres Local ERP Adapter (Data Mapper)"

    def test_connect_and_disconnect(self) -> None:
        """Testa chamadas explicitas de connect e disconnect."""
        adapter = PostgresLocalERPAdapter()
        res = adapter.connect()
        assert isinstance(res, bool)
        adapter.disconnect()


class TestPostgresLocalAdapterHealthCheck:
    """Suite de verificacao de saude e diagnostico de conexao."""

    def test_check_health_live_or_fallback(self) -> None:
        """Verifica estrutura do relatorio de saude em conexao real ou fallback."""
        adapter = PostgresLocalERPAdapter()
        health = adapter.check_health()
        assert isinstance(health, dict)
        assert health["status"] in {"healthy", "offline_fallback"}
        assert health["adapter"] == "Postgres Local ERP Adapter (Data Mapper)"
        assert isinstance(health["connected"], bool)
        assert isinstance(health["is_connected"], bool)
        assert health["connected"] == health["is_connected"]
        assert health["mode"] in {"live_postgres", "offline_fallback"}
        assert isinstance(health["latency_ms"], float)
        assert health["latency_ms"] >= 0.0
        assert isinstance(health["db_role"], str)
        assert isinstance(health["record_counts"], dict)
        assert "pedidos" in health["record_counts"]
        assert "tanques" in health["record_counts"]
        assert "bombas" in health["record_counts"]
        assert "fechamentos" in health["record_counts"]
        assert "produtos" in health["record_counts"]

    def test_check_health_offline_forced(self) -> None:
        """Garante retorno apropriado de diagnostico quando o modo offline esta forcado."""
        adapter = PostgresLocalERPAdapter(force_offline=True)
        health = adapter.check_health()
        assert health["status"] == "offline_fallback"
        assert health["connected"] is False
        assert health["is_connected"] is False
        assert health["mode"] == "offline_fallback"
        assert "forcado" in str(health["error"]).lower()
        assert isinstance(health["record_counts"], dict)
        assert health["record_counts"]["pedidos"] >= 0
        assert health["record_counts"]["tanques"] >= 0
        assert health["record_counts"]["bombas"] >= 0
        assert health["record_counts"]["fechamentos"] >= 0
        assert health["record_counts"]["produtos"] >= 0

    def test_check_health_handles_connection_failure(self) -> None:
        """Garante que falha de conexao no health check nao lanca excecao e aciona fallback."""
        adapter = PostgresLocalERPAdapter()
        with patch("core.adapters.erp.postgres_local_adapter.get_erp_connection") as mock_conn:
            mock_conn.side_effect = psycopg2.OperationalError("Timeout na conexao com banco")
            health = adapter.check_health()
            assert health["status"] == "offline_fallback"
            assert health["connected"] is False
            assert health["is_connected"] is False
            assert "Timeout" in str(health["error"])
            assert health["record_counts"]["pedidos"] >= 0


class TestPostgresLocalAdapterQueries:
    """Suite de consultas reais e mapeamento para entidades canonicas universais."""

    @pytest.fixture
    def live_adapter(self) -> PostgresLocalERPAdapter:
        return PostgresLocalERPAdapter()

    def test_get_recent_sales_returns_universal_receipts(
        self, live_adapter: PostgresLocalERPAdapter
    ) -> None:
        """Verifica se get_recent_sales retorna lista de UniversalSaleReceipt validos."""
        sales = live_adapter.get_recent_sales(limit=5)
        assert isinstance(sales, list)
        assert len(sales) <= 5
        for s in sales:
            assert isinstance(s, UniversalSaleReceipt)
            assert isinstance(s.cupom_id, str)
            assert len(s.cupom_id) > 0
            assert isinstance(s.data_hora, datetime)
            assert isinstance(s.pdv, str)
            assert isinstance(s.total_reais, float)
            assert s.total_reais >= 0.0
            assert isinstance(s.status, str)
            assert isinstance(s.operador, str)
            assert isinstance(s.itens, list)
            assert isinstance(s.pagamentos, list)
            for item in s.itens:
                assert isinstance(item, UniversalSaleItem)
                assert isinstance(item.sku, str)
                assert isinstance(item.descricao_produto, str)
                assert isinstance(item.preco_unitario_reais, float)
                assert isinstance(item.quantidade, float)
                assert isinstance(item.total_item_reais, float)
            for pag in s.pagamentos:
                assert isinstance(pag, UniversalPaymentMethod)
                assert isinstance(pag.codigo_forma_pagamento, str)
                assert isinstance(pag.tipo, str)
                assert isinstance(pag.valor_reais, float)

    def test_get_recent_sales_date_filters(
        self, live_adapter: PostgresLocalERPAdapter
    ) -> None:
        """Testa filtragem de vendas com limites e datas passadas e futuras."""
        # Limite respeitado
        sales_2 = live_adapter.get_recent_sales(limit=2)
        assert len(sales_2) <= 2

        # Data no futuro remoto nao deve retornar cupons
        sales_future = live_adapter.get_recent_sales(start_date="2099-01-01", limit=10)
        assert sales_future == []

        # Data valida formatada como date
        sales_date_obj = live_adapter.get_recent_sales(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            limit=5,
        )
        assert isinstance(sales_date_obj, list)

    def test_get_recent_sales_with_datetime_objects(
        self, live_adapter: PostgresLocalERPAdapter
    ) -> None:
        """Testa suporte a objetos datetime nos filtros de start_date e end_date."""
        dt_start = datetime(2026, 1, 1, 0, 0, 0)
        dt_end = datetime(2026, 12, 31, 23, 59, 59)
        sales = live_adapter.get_recent_sales(start_date=dt_start, end_date=dt_end, limit=5)
        assert isinstance(sales, list)
        for s in sales:
            assert isinstance(s, UniversalSaleReceipt)

    def test_get_recent_sales_preserves_item_sold_unit_price(
        self, live_adapter: PostgresLocalERPAdapter
    ) -> None:
        """Garante que o preco unitario do item faturado prioriza itemped.valunit sobre o catalogo."""
        sales = live_adapter.get_recent_sales(limit=10)
        assert len(sales) > 0
        for s in sales:
            for item in s.itens:
                assert isinstance(item.preco_unitario_reais, float)
                assert item.preco_unitario_reais >= 0.0
                # Se quantidade for positiva e total positivo, o preco unitario deve ser consistente
                if item.quantidade > 0 and item.total_item_reais > 0:
                    calculated_total = round(item.preco_unitario_reais * item.quantidade, 2)
                    assert abs(calculated_total - item.total_item_reais) <= 0.05

    def test_get_tank_inventory_returns_universal_readings(
        self, live_adapter: PostgresLocalERPAdapter
    ) -> None:
        """Verifica se get_tank_inventory retorna lista de UniversalTankReading validos."""
        tanks = live_adapter.get_tank_inventory()
        assert isinstance(tanks, list)
        for t in tanks:
            assert isinstance(t, UniversalTankReading)
            assert isinstance(t.identificador_tanque, str)
            assert len(t.identificador_tanque) > 0
            assert isinstance(t.timestamp_leitura, datetime)
            assert isinstance(t.volume_atual_litros, float)
            assert t.volume_atual_litros >= 0.0
            assert isinstance(t.volume_agua_mm, float)
            assert t.volume_agua_mm >= 0.0
            if t.temperatura_celsius is not None:
                assert isinstance(t.temperatura_celsius, float)
            assert isinstance(t.percentual_capacidade, float)
            assert 0.0 <= t.percentual_capacidade <= 100.0

    def test_get_pump_dispenses_returns_universal_logs(
        self, live_adapter: PostgresLocalERPAdapter
    ) -> None:
        """Verifica se get_pump_dispenses retorna lista de UniversalDispenserLog com telemetria valida."""
        pumps = live_adapter.get_pump_dispenses(limit=5)
        assert isinstance(pumps, list)
        assert len(pumps) <= 5
        assert len(pumps) > 0
        assert any(p.volume_vendido_litros > 0.0 or p.total_faturado_reais > 0.0 for p in pumps)
        for p in pumps:
            assert isinstance(p, UniversalDispenserLog)
            assert isinstance(p.identificador_bomba, str)
            assert isinstance(p.identificador_bico, str)
            assert isinstance(p.timestamp_registro, datetime)
            assert isinstance(p.encerrante_inicial_litros, float)
            assert isinstance(p.encerrante_final_litros, float)
            assert isinstance(p.volume_aferido_litros, float)
            assert isinstance(p.total_faturado_reais, float)
            assert isinstance(p.volume_vendido_litros, float)
            assert p.volume_vendido_litros >= 0.0

    def test_get_cashier_shifts_returns_universal_shifts(
        self, live_adapter: PostgresLocalERPAdapter
    ) -> None:
        """Verifica se get_cashier_shifts retorna lista de UniversalCashierShift validos."""
        shifts = live_adapter.get_cashier_shifts(limit=5)
        assert isinstance(shifts, list)
        assert len(shifts) <= 5
        for s in shifts:
            assert isinstance(s, UniversalCashierShift)
            assert isinstance(s.operador_id, str)
            assert isinstance(s.operador_nome, str)
            assert isinstance(s.turno_descricao, str)
            assert isinstance(s.data_movimento, date)
            assert isinstance(s.timestamp_abertura, datetime)
            assert isinstance(s.fundo_troco_reais, float)
            assert isinstance(s.total_declarado_reais, float)
            assert isinstance(s.total_sistema_reais, float)
            assert isinstance(s.quebra_sobra_reais, float)

    def test_get_product_catalog_and_filtering(
        self, live_adapter: PostgresLocalERPAdapter
    ) -> None:
        """Verifica se get_product_catalog recupera dados e filtra por termo e categoria."""
        catalog = live_adapter.get_product_catalog(limit=5)
        assert isinstance(catalog, list)
        assert len(catalog) <= 5
        for item in catalog:
            assert isinstance(item, UniversalSaleItem)
            assert isinstance(item.sku, str)
            assert isinstance(item.descricao_produto, str)
            assert isinstance(item.grupo_comercial, str)
            assert isinstance(item.preco_unitario_reais, float)
            assert isinstance(item.quantidade, float)
            assert isinstance(item.total_item_reais, float)

        # Filtro por termo
        filtered = live_adapter.get_product_catalog(filter_term="GASOLINA", limit=5)
        assert isinstance(filtered, list)
        for f in filtered:
            assert "gasolina" in f.descricao_produto.lower() or "gasolina" in f.sku.lower()

        # Filtro por categoria
        cat_filtered = live_adapter.get_product_catalog(category="COMBUSTIVEIS", limit=5)
        assert isinstance(cat_filtered, list)
        for c in cat_filtered:
            assert "combust" in c.grupo_comercial.lower()


class TestPostgresLocalAdapterResilienceAndFallback:
    """Suite de resiliencia: contingencia offline e tratamento de erros do banco."""

    def test_forced_offline_mode_returns_calibrated_mock_data(self) -> None:
        """Garante que forcar modo offline utiliza dados calibrados do MockERPAdapter."""
        adapter = PostgresLocalERPAdapter(force_offline=True)

        sales = adapter.get_recent_sales(limit=5)
        assert len(sales) > 0
        assert isinstance(sales[0], UniversalSaleReceipt)

        tanks = adapter.get_tank_inventory()
        assert len(tanks) > 0
        assert isinstance(tanks[0], UniversalTankReading)

        pumps = adapter.get_pump_dispenses(limit=5)
        assert len(pumps) > 0
        assert isinstance(pumps[0], UniversalDispenserLog)

        shifts = adapter.get_cashier_shifts(limit=5)
        assert len(shifts) > 0
        assert isinstance(shifts[0], UniversalCashierShift)

        catalog = adapter.get_product_catalog(limit=5)
        assert len(catalog) > 0
        assert isinstance(catalog[0], UniversalSaleItem)

    def test_query_failure_triggers_fallback_when_enabled(self) -> None:
        """Garante que falha no _execute_query aciona o MockERPAdapter se fallback_on_error for True."""
        adapter = PostgresLocalERPAdapter(fallback_on_error=True)
        with patch.object(adapter, "_execute_query", side_effect=psycopg2.OperationalError("Conexao perdida")):
            sales = adapter.get_recent_sales(limit=3)
            assert len(sales) > 0
            assert isinstance(sales[0], UniversalSaleReceipt)

            tanks = adapter.get_tank_inventory()
            assert len(tanks) > 0
            assert isinstance(tanks[0], UniversalTankReading)

            pumps = adapter.get_pump_dispenses(limit=3)
            assert len(pumps) > 0
            assert isinstance(pumps[0], UniversalDispenserLog)

            shifts = adapter.get_cashier_shifts(limit=3)
            assert len(shifts) > 0
            assert isinstance(shifts[0], UniversalCashierShift)

            catalog = adapter.get_product_catalog(limit=3)
            assert len(catalog) > 0
            assert isinstance(catalog[0], UniversalSaleItem)

    def test_query_failure_raises_erp_query_error_when_fallback_disabled(self) -> None:
        """Garante que falhas lancam ERPQueryError quando fallback_on_error for False."""
        adapter = PostgresLocalERPAdapter(fallback_on_error=False)
        with patch.object(adapter, "_execute_query", side_effect=psycopg2.OperationalError("Falha critica")):
            with pytest.raises(ERPQueryError) as exc_sales:
                adapter.get_recent_sales(limit=5)
            assert "Erro ao consultar vendas" in str(exc_sales.value)

            with pytest.raises(ERPQueryError) as exc_tanks:
                adapter.get_tank_inventory()
            assert "Erro ao consultar inventario" in str(exc_tanks.value)

            with pytest.raises(ERPQueryError) as exc_pumps:
                adapter.get_pump_dispenses(limit=5)
            assert "Erro ao consultar fechabomba" in str(exc_pumps.value)

            with pytest.raises(ERPQueryError) as exc_shifts:
                adapter.get_cashier_shifts(limit=5)
            assert "Erro ao consultar fechacaixa" in str(exc_shifts.value)

            with pytest.raises(ERPQueryError) as exc_cat:
                adapter.get_product_catalog(limit=5)
            assert "Erro ao consultar catalogo" in str(exc_cat.value)

    def test_connect_failure_raises_erp_connection_error_when_fallback_disabled(self) -> None:
        """Garante que connect lanca ERPConnectionError quando fallback_on_error for False."""
        adapter = PostgresLocalERPAdapter(fallback_on_error=False)
        with patch("core.adapters.erp.postgres_local_adapter.get_erp_connection") as mock_conn:
            mock_conn.side_effect = psycopg2.OperationalError("Falha de rede local")
            with pytest.raises(ERPConnectionError) as exc_conn:
                adapter.connect()
            assert "Falha de conexao com PostgreSQL" in str(exc_conn.value)

    def test_connect_failure_returns_false_when_fallback_enabled(self) -> None:
        """Garante que connect retorna False sem explodir se fallback_on_error for True."""
        adapter = PostgresLocalERPAdapter(fallback_on_error=True)
        with patch("core.adapters.erp.postgres_local_adapter.get_erp_connection") as mock_conn:
            mock_conn.side_effect = psycopg2.OperationalError("Host inacessivel")
            assert adapter.connect() is False

    def test_connection_pool_guaranteed_release_on_query_error(self) -> None:
        """Garante que a conexao emprestada do pool e devolvida mesmo em caso de erro na query."""
        from unittest.mock import MagicMock
        adapter = PostgresLocalERPAdapter(fallback_on_error=False)
        mock_conn_wrapper = MagicMock()
        mock_cur = MagicMock()
        mock_cur.execute.side_effect = psycopg2.DatabaseError("Erro de sintaxe forcado")
        mock_conn_wrapper.cursor.return_value.__enter__.return_value = mock_cur
        mock_conn_wrapper.__enter__.return_value = mock_conn_wrapper

        with patch("core.adapters.erp.postgres_local_adapter.get_erp_connection", return_value=mock_conn_wrapper):
            with pytest.raises(ERPQueryError):
                adapter.get_recent_sales(limit=1)

            # Verifica que o context manager do pool fechou/devolveu a conexao
            mock_conn_wrapper.__exit__.assert_called_once()

    def test_pump_dispenses_falls_back_to_abastecimentos_when_fechabomba_has_only_zero_rows(self) -> None:
        """Garante que se fechabomba contiver apenas registros zerados, abastecimentos e acionado."""
        adapter = PostgresLocalERPAdapter(fallback_on_error=False)

        dummy_fechabomba = [
            {
                "identificador_bomba": "001",
                "identificador_bico": "001",
                "timestamp_registro": datetime(2026, 10, 6, 0, 0),
                "encerrante_inicial_litros": 0.0,
                "encerrante_final_litros": 0.0,
                "volume_aferido_litros": 0.0,
                "total_faturado_reais": 0.0,
            }
        ]
        real_abastecimentos = [
            {
                "identificador_bomba": "1",
                "identificador_bico": "001",
                "timestamp_registro": datetime(2026, 9, 2, 11, 39, 15),
                "encerrante_inicial_litros": 1417.744,
                "encerrante_final_litros": 1427.744,
                "volume_aferido_litros": 0.0,
                "total_faturado_reais": 71.30,
            }
        ]

        def fake_execute(query, params=None):
            if "FROM fechabomba" in query:
                return dummy_fechabomba
            if "FROM abastecimentos" in query:
                return real_abastecimentos
            return []

        with patch.object(adapter, "_execute_query", side_effect=fake_execute):
            logs = adapter.get_pump_dispenses(limit=5)
            assert len(logs) == 1
            assert logs[0].identificador_bico == "001"
            assert logs[0].encerrante_inicial_litros == 1417.744
            assert logs[0].encerrante_final_litros == 1427.744
            assert logs[0].volume_vendido_litros == 10.0
            assert logs[0].total_faturado_reais == 71.30


class TestBlock3QualityAndZeroTravessoes:
    """Suite de qualidade de codigo: ausencia estrita de travessoes e performance."""

    def test_zero_travessoes_in_all_block3_files(self) -> None:
        """Garante ausencia absoluta de travessoes (em-dash e en-dash) nos arquivos do Bloco 3."""
        base_dir = Path(__file__).resolve().parent.parent.parent
        files_to_check = [
            base_dir / "core" / "adapters" / "erp" / "postgres_local_adapter.py",
            base_dir / "core" / "adapters" / "erp" / "__init__.py",
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

    def test_sub_second_performance_offline(self) -> None:
        """Garante que a execucao em contingencia offline e ultra-rapida."""
        adapter = PostgresLocalERPAdapter(force_offline=True)

        start = time.perf_counter()
        for _ in range(50):
            _ = adapter.get_recent_sales(start_date="2026-10-14", limit=10)
            _ = adapter.get_tank_inventory()
            _ = adapter.get_pump_dispenses(limit=5)
            _ = adapter.get_cashier_shifts(target_date="2026-10-14")
            _ = adapter.get_product_catalog(filter_term="gasolina")
            _ = adapter.check_health()
        elapsed = time.perf_counter() - start

        assert elapsed < 0.20, f"Benchmark offline muito lento: {elapsed:.4f}s para 50 iteracoes"
