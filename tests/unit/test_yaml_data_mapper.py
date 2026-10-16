"""Testes Unitarios do Mapeador Declarativo Multi-ERP via YAML (P3-3).

AURA Universal Posto Schema (AUPS): Bloco 4.
Valida:
1. Carregamento e validacao de YAMLs de mapeamento de referencia (Linx, Petros, Generic).
2. Tratamento defensivo contra injecao SQL e rejeicao estrita de identificadores invalidos.
3. Geracao dinamica de queries parametrizadas (%s) com filtros e ordenacao.
4. Mapeamento fiel para entidades canonicas universais do AUPS.
5. Execucao simulada com MockDBConnection e conversao de vendas, tanques, bombas e caixas.
6. Fallback gracioso para MockERPAdapter em desconexoes e excecoes.
7. Ausencia estrita de travessoes (zero em-dash e en-dash) e execucao sub-segundo.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import date, datetime
from pathlib import Path
from types import TracebackType
from typing import Any, Self

import pytest
from pydantic import ValidationError

from core.adapters.erp import (
    BaseERPAdapter,
    ColumnMappingConfig,
    ERPMappingConfig,
    ERPQueryError,
    FilterConfig,
    JoinConfig,
    TableMappingConfig,
    YAMLDataMapperERPAdapter,
    create_yaml_erp_adapter,
)
from core.adapters.erp.yaml_data_mapper import validate_identifier
from core.domain.cashier import UniversalCashierShift
from core.domain.pumps import UniversalDispenserLog, UniversalPump
from core.domain.sales import (
    UniversalPaymentMethod,
    UniversalSaleItem,
    UniversalSaleReceipt,
)
from core.domain.tanks import UniversalTankReading


class MockDBCursor:
    """Cursor simulado para execucao deterministica em testes unitarios."""

    def __init__(self, query_handler: Callable[[str, list[Any]], list[dict[str, Any]]]) -> None:
        self._query_handler = query_handler
        self._rows: list[dict[str, Any]] = []
        self.description: list[tuple[str, ...]] | None = None

    def execute(self, query: str, params: list[Any] | tuple[Any, ...] | None = None) -> None:
        self._rows = self._query_handler(query, list(params or []))
        if self._rows and isinstance(self._rows[0], dict):
            self.description = [(k, None, None, None, None, None, None) for k in self._rows[0]]
        else:
            self.description = None

    def fetchall(self) -> list[dict[str, Any]]:
        return self._rows

    def fetchone(self) -> dict[str, Any] | None:
        return self._rows[0] if self._rows else None

    def close(self) -> None:
        pass


class MockDBConnection:
    """Conexao de banco simulada com context manager para testes unitarios."""

    def __init__(self, query_handler: Callable[[str, list[Any]], list[dict[str, Any]]]) -> None:
        self._query_handler = query_handler
        self.closed = False

    def cursor(self, **kwargs: Any) -> MockDBCursor:
        return MockDBCursor(self._query_handler)

    def close(self) -> None:
        self.closed = True

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.close()


class TestERPMappingConfigLoading:
    """Suite de validacao do carregamento de arquivos YAML declarativos."""

    def test_load_reference_generic_postgres_yaml(self) -> None:
        """Garante leitura e integridade estrutural do generic_postgres.yaml."""
        cfg = ERPMappingConfig.from_yaml_file("config/erp_mappings/generic_postgres.yaml")
        assert cfg.erp_name == "Generic PostgreSQL"
        assert cfg.dialect == "postgres"
        assert "sales" in cfg.tables
        assert "tanks" in cfg.tables
        assert "pumps" in cfg.tables
        assert "cashier" in cfg.tables
        assert "products" in cfg.tables

        sales_tbl = cfg.get_table("sales")
        assert sales_tbl is not None
        assert sales_tbl.table_name == "pedido"
        assert sales_tbl.primary_key == "codi"
        assert sales_tbl.date_column == "dtem"
        assert sales_tbl.status_column == "situ"
        assert sales_tbl.cancelled_value == "C"

        cols = sales_tbl.get_column_mappings()
        assert "cupom_id" in cols
        assert cols["cupom_id"].source_column == "codi"
        assert cols["total_reais"].source_column == "valortotal"

    def test_load_reference_linx_postos_yaml(self) -> None:
        """Garante leitura e integridade estrutural do linx_postos.yaml."""
        cfg = ERPMappingConfig.from_yaml_file("config/erp_mappings/linx_postos.yaml")
        assert cfg.erp_name == "Linx Postos"
        assert "sales" in cfg.tables
        assert "sales_items" in cfg.tables
        assert "sales_payments" in cfg.tables

        sales_tbl = cfg.get_table("sales")
        assert sales_tbl is not None
        assert sales_tbl.table_name == "vendas_pdv"
        assert sales_tbl.cancelled_value == "CANCELADA"

        items_tbl = cfg.get_table("sales_items")
        assert items_tbl is not None
        assert items_tbl.table_name == "vendas_itens"
        assert items_tbl.foreign_key == "id_venda"

    def test_load_reference_petros_yaml(self) -> None:
        """Garante leitura e integridade estrutural do petros.yaml."""
        cfg = ERPMappingConfig.from_yaml_file("config/erp_mappings/petros.yaml")
        assert cfg.erp_name == "Adaptive Petros"
        assert "sales" in cfg.tables
        assert "tanks" in cfg.tables
        assert "pumps" in cfg.tables
        assert "cashier" in cfg.tables

        tanks_tbl = cfg.get_table("tanks")
        assert tanks_tbl is not None
        assert tanks_tbl.table_name == "tb_tanque_leitura"
        assert tanks_tbl.primary_key == "cd_tanque"

    def test_load_yaml_from_string(self) -> None:
        """Testa carregamento dinamico a partir de string de YAML."""
        yaml_content = """
        erp_name: "CustomERP"
        tables:
          products:
            table_name: "produtos"
            columns:
              sku: "codigo"
              descricao_produto: "nome"
        """
        cfg = ERPMappingConfig.from_yaml_string(yaml_content)
        assert cfg.erp_name == "CustomERP"
        assert "products" in cfg.tables
        assert cfg.tables["products"].table_name == "produtos"

    def test_missing_file_raises_not_found(self) -> None:
        """Garante excecao FileNotFoundError quando arquivo nao existe."""
        with pytest.raises(FileNotFoundError):
            ERPMappingConfig.from_yaml_file("config/erp_mappings/arquivo_inexistente.yaml")

    def test_invalid_yaml_type_raises_type_error(self) -> None:
        """Garante TypeError caso o conteudo YAML nao seja dicionario raiz."""
        with pytest.raises(TypeError):
            ERPMappingConfig.from_yaml_string("- item1\n- item2")

    def test_table_shorthand_normalization(self) -> None:
        """Garante normalizacao de tabela definida em formato abreviado (string)."""
        yaml_content = """
        erp_name: "MiniERP"
        tables:
          sales: "pedido"
        """
        cfg = ERPMappingConfig.from_yaml_string(yaml_content)
        assert cfg.tables["sales"].table_name == "pedido"

    def test_table_mapping_columns_as_list(self) -> None:
        """Garante suporte a definicao de colunas como lista de mapeamentos."""
        tbl = TableMappingConfig(
            table_name="pedido",
            columns=[
                {"source_column": "codi", "target_field": "cupom_id"},
                {"source": "valortotal", "target": "total_reais"},
            ],
        )
        cols = tbl.get_column_mappings()
        assert "cupom_id" in cols
        assert cols["cupom_id"].source_column == "codi"
        assert "total_reais" in cols
        assert cols["total_reais"].source_column == "valortotal"

    def test_generic_postgres_yaml_includes_medicaotanques(self) -> None:
        """Garante que generic_postgres.yaml mapeia a tabela medicaotanques."""
        cfg = ERPMappingConfig.from_yaml_file("config/erp_mappings/generic_postgres.yaml")
        assert "tank_readings" in cfg.tables
        tank_tbl = cfg.get_table("tank_readings")
        assert tank_tbl is not None
        assert tank_tbl.table_name == "medicaotanques"
        assert tank_tbl.primary_key == "codtan"
        assert tank_tbl.foreign_key == "codtan"
        cols = tank_tbl.get_column_mappings()
        assert "identificador_tanque" in cols
        assert "volume_atual_litros" in cols

    def test_entity_aliases_resolution(self) -> None:
        """Garante resolucao automatica de sinonimos em portugues para entidades."""
        cfg = ERPMappingConfig.from_yaml_file("config/erp_mappings/generic_postgres.yaml")
        assert cfg.get_table("vendas") is not None
        assert cfg.get_table("vendas").table_name == "pedido"
        assert cfg.get_table("itens") is not None
        assert cfg.get_table("itens").table_name == "itemped"
        assert cfg.get_table("tanques") is not None
        assert cfg.get_table("tanques").table_name == "tanques"
        assert cfg.get_table("bombas") is not None
        assert cfg.get_table("bombas").table_name == "fechabomba"
        assert cfg.get_table("caixa") is not None
        assert cfg.get_table("caixa").table_name == "fechacaixa"
        assert cfg.get_table("produtos") is not None
        assert cfg.get_table("produtos").table_name == "produtos"


class TestSQLIdentifierValidation:
    """Suite de protecao rigorosa contra SQL Injection em identificadores."""

    @pytest.mark.parametrize(
        "valid_name",
        [
            "pedido",
            "itemped",
            "vendas_pdv",
            "p.nompro",
            "public.tanques",
            "col_123",
            "_codigo",
            "tab1.col2",
        ],
    )
    def test_valid_identifiers_allowed(self, valid_name: str) -> None:
        """Valida que identificadores bem formados sao aceitos."""
        assert validate_identifier(valid_name) == valid_name

    @pytest.mark.parametrize(
        "malicious_name",
        [
            "pedido; DROP TABLE pedido;",
            "vendas -- comentario",
            "col/*comment*/",
            "table' OR '1'='1",
            "(SELECT 1)",
            "users UNION SELECT * FROM passwords",
            "schema.table.column",
            "col name with spaces",
            "col-dash",
            "col$dollar",
            "",
            "   ",
        ],
    )
    def test_malicious_identifiers_rejected(self, malicious_name: str) -> None:
        """Valida rejeicao imediata de qualquer identificador malicioso ou com caracteres proibidos."""
        with pytest.raises(ValueError):
            validate_identifier(malicious_name)

    def test_table_mapping_rejects_malicious_table_name(self) -> None:
        """Garante que TableMappingConfig rejeita nomes de tabela com injecao SQL."""
        with pytest.raises(ValidationError):
            TableMappingConfig(table_name="pedido; DROP TABLE pedido;")

    def test_column_mapping_rejects_malicious_source_column(self) -> None:
        """Garante que ColumnMappingConfig rejeita nomes de coluna com injecao SQL."""
        with pytest.raises(ValidationError):
            ColumnMappingConfig(source_column="codi; DROP TABLE users;")

    def test_filter_config_rejects_malicious_operator(self) -> None:
        """Garante que FilterConfig rejeita operadores fora da lista permitida."""
        with pytest.raises(ValidationError):
            FilterConfig(column="status", operator="UNION SELECT")

    def test_join_config_rejects_malicious_join_type(self) -> None:
        """Garante que JoinConfig rejeita tipos de join invalidos."""
        with pytest.raises(ValidationError):
            JoinConfig(
                table="produtos",
                type="MALICIOUS_JOIN",
                left_column="codpro",
                right_column="codpro",
            )

    def test_target_field_rejects_qualified_dot_notation(self) -> None:
        """Garante que target_field rejeita nomes qualificados com ponto (ex: p.sku)."""
        with pytest.raises(ValidationError):
            ColumnMappingConfig(source_column="codi", target_field="p.cupom_id")


class TestSQLQueryBuilder:
    """Suite de construcao segura e parametrizacao de consultas SQL."""

    def test_build_select_sql_with_all_components(self) -> None:
        """Valida geracao de SELECT parametrizado com colunas, where, order e limit."""
        adapter = create_yaml_erp_adapter("generic_postgres", force_offline=True)
        table_cfg = adapter.config.get_table("sales")
        assert table_cfg is not None

        sql, params = adapter._build_select_sql(
            table_cfg,
            extra_where=["dtem >= %s", "dtem <= %s"],
            extra_params=["2026-10-01", "2026-10-15"],
            limit=25,
        )

        assert "SELECT" in sql
        assert "codi AS cupom_id" in sql
        assert "FROM pedido" in sql
        assert "WHERE dtem >= %s AND dtem <= %s" in sql
        assert "ORDER BY dtem DESC" in sql
        assert "LIMIT %s" in sql
        assert params == ["2026-10-01", "2026-10-15", 25]

    def test_build_select_sql_with_joins(self) -> None:
        """Valida construcao de query contendo declaracao de JOIN."""
        table_cfg = TableMappingConfig(
            table_name="vendas",
            columns={"cupom_id": "vendas.id", "item_nome": "produtos.nome"},
            joins=[
                JoinConfig(
                    table="produtos",
                    type="LEFT",
                    left_table="vendas",
                    left_column="prod_id",
                    right_table="produtos",
                    right_column="id",
                )
            ],
        )
        adapter = YAMLDataMapperERPAdapter(
            ERPMappingConfig(erp_name="TestERP", tables={"vendas": table_cfg}),
            force_offline=True,
        )
        sql, _ = adapter._build_select_sql(table_cfg)
        assert "LEFT JOIN produtos ON vendas.prod_id = produtos.id" in sql

    def test_unary_operators_is_null_and_is_not_null(self) -> None:
        """Garante que operadores unarios IS NULL e IS NOT NULL nao incluem placeholder %s."""
        table_cfg = TableMappingConfig(
            table_name="pedido",
            filters=[
                FilterConfig(column="dtcanc", operator="IS NULL"),
                FilterConfig(column="dtem", operator="IS NOT NULL"),
            ],
        )
        adapter = YAMLDataMapperERPAdapter(
            ERPMappingConfig(erp_name="TestERP", tables={"pedido": table_cfg}),
            force_offline=True,
        )
        sql, params = adapter._build_select_sql(table_cfg)
        assert "dtcanc IS NULL" in sql
        assert "dtem IS NOT NULL" in sql
        assert "IS NULL %s" not in sql
        assert "IS NOT NULL %s" not in sql
        assert params == []

    def test_in_and_not_in_operators(self) -> None:
        """Garante que operadores IN e NOT IN geram placeholders parametrizados para colecoes."""
        table_cfg = TableMappingConfig(
            table_name="pedido",
            filters=[
                FilterConfig(column="situ", operator="IN", value=["A", "F"]),
                FilterConfig(column="pdv", operator="NOT IN", value=["99"]),
            ],
        )
        adapter = YAMLDataMapperERPAdapter(
            ERPMappingConfig(erp_name="TestERP", tables={"pedido": table_cfg}),
            force_offline=True,
        )
        sql, params = adapter._build_select_sql(table_cfg)
        assert "situ IN (%s, %s)" in sql
        assert "pdv NOT IN (%s)" in sql
        assert params == ["A", "F", "99"]

    def test_in_operator_with_empty_list(self) -> None:
        """Garante que operador IN com colecao vazia gera clausula segura 1=0."""
        table_cfg = TableMappingConfig(
            table_name="pedido",
            filters=[
                FilterConfig(column="situ", operator="IN", value=[]),
            ],
        )
        adapter = YAMLDataMapperERPAdapter(
            ERPMappingConfig(erp_name="TestERP", tables={"pedido": table_cfg}),
            force_offline=True,
        )
        sql, params = adapter._build_select_sql(table_cfg)
        assert "1=0" in sql
        assert params == []


class TestYAMLDataMapperMockExecution:
    """Suite de execucao deterministica com conexao simulada e conversao AUPS."""

    def test_get_recent_sales_with_items_and_payments(self) -> None:
        """Garante conversao de vendas com itens e pagamentos para UniversalSaleReceipt."""
        def mock_handler(query: str, params: list[Any]) -> list[dict[str, Any]]:
            if "FROM pedido" in query:
                return [
                    {
                        "cupom_id": "PED1001",
                        "pdv": "PDV1",
                        "data_hora": datetime(2026, 10, 16, 10, 30, 0),
                        "total_reais": 150.00,
                        "status": "CONCLUIDA",
                        "operador": "CARLOS_SILVA",
                        "motivo_cancelamento": None,
                    }
                ]
            if "FROM itemped" in query:
                return [
                    {
                        "pedido": "PED1001",
                        "sku": "GAS_COMUM",
                        "descricao_produto": "Gasolina Comum Aditivada",
                        "grupo_comercial": "COMBUSTIVEIS",
                        "preco_unitario_reais": 5.00,
                        "quantidade": 30.0,
                        "total_item_reais": 150.00,
                    }
                ]
            return []

        mock_conn = MockDBConnection(mock_handler)
        adapter = create_yaml_erp_adapter(
            "generic_postgres",
            connection_factory=lambda: mock_conn,
        )

        receipts = adapter.get_recent_sales(start_date="2026-10-16", limit=10)
        assert len(receipts) == 1
        rec = receipts[0]
        assert isinstance(rec, UniversalSaleReceipt)
        assert rec.cupom_id == "PED1001"
        assert rec.total_reais == 150.00
        assert rec.operador == "CARLOS_SILVA"
        assert len(rec.itens) == 1

        item = rec.itens[0]
        assert isinstance(item, UniversalSaleItem)
        assert item.sku == "GAS_COMUM"
        assert item.quantidade == 30.0
        assert item.preco_unitario_reais == 5.00
        assert item.total_item_reais == 150.00

        assert len(rec.pagamentos) == 1
        assert isinstance(rec.pagamentos[0], UniversalPaymentMethod)

    def test_get_tank_inventory_mapping(self) -> None:
        """Garante recuperacao e conversao para UniversalTankReading."""
        def mock_handler(query: str, params: list[Any]) -> list[dict[str, Any]]:
            if "FROM tanques" in query:
                return [
                    {
                        "identificador_tanque": "TQ01",
                        "combustivel": "Gasolina Comum",
                        "codigo_lmc": "1001",
                        "timestamp_leitura": datetime(2026, 10, 16, 8, 0, 0),
                        "volume_atual_litros": 12500.0,
                        "volume_agua_mm": 5.0,
                        "temperatura_celsius": 24.5,
                        "capacidade_nominal_litros": 15000.0,
                        "saldo_inicial_litros": 13000.0,
                        "saldo_final_litros": 12500.0,
                    }
                ]
            return []

        adapter = create_yaml_erp_adapter(
            "generic_postgres",
            connection_factory=lambda: MockDBConnection(mock_handler),
        )

        readings = adapter.get_tank_inventory()
        assert len(readings) == 1
        rd = readings[0]
        assert isinstance(rd, UniversalTankReading)
        assert rd.identificador_tanque == "TQ01"
        assert rd.combustivel == "Gasolina Comum"
        assert rd.volume_atual_litros == 12500.0
        assert rd.capacidade_nominal_litros == 15000.0
        assert rd.percentual_capacidade > 80.0

    def test_get_pump_dispenses_mapping(self) -> None:
        """Garante recuperacao e conversao para UniversalDispenserLog."""
        def mock_handler(query: str, params: list[Any]) -> list[dict[str, Any]]:
            if "FROM fechabomba" in query:
                return [
                    {
                        "identificador_bomba": "BOMBA_01",
                        "identificador_bico": "BICO_01",
                        "identificador_tanque": "TQ01",
                        "codigo_combustivel": "GAS",
                        "descricao_combustivel": "Gasolina",
                        "turno_descricao": "MANHA",
                        "pdv": "1",
                        "timestamp_registro": datetime(2026, 10, 16, 14, 0, 0),
                        "encerrante_inicial_litros": 1000.0,
                        "encerrante_final_litros": 1500.0,
                        "volume_aferido_litros": 20.0,
                        "preco_unitario_reais": 5.50,
                        "total_faturado_reais": 2640.0,
                    }
                ]
            return []

        adapter = create_yaml_erp_adapter(
            "generic_postgres",
            connection_factory=lambda: MockDBConnection(mock_handler),
        )

        logs = adapter.get_pump_dispenses(limit=5)
        assert len(logs) == 1
        log = logs[0]
        assert isinstance(log, UniversalDispenserLog)
        assert log.identificador_bomba == "BOMBA_01"
        assert log.identificador_bico == "BICO_01"
        assert log.encerrante_final_litros == 1500.0
        assert log.volume_vendido_litros == 480.0

    def test_get_pumps_catalog_mapping(self) -> None:
        """Garante recuperacao de catalogo de bombas quando tabela presente."""
        def mock_handler(query: str, params: list[Any]) -> list[dict[str, Any]]:
            return [
                {
                    "identificador_bomba": "ILHA_1",
                    "identificador_bico": "BICO_01",
                    "identificador_tanque": "TQ01",
                    "codigo_combustivel": "GAS_01",
                    "descricao_combustivel": "Gasolina Comum",
                    "ativo": True,
                }
            ]

        adapter = create_yaml_erp_adapter(
            "generic_postgres",
            connection_factory=lambda: MockDBConnection(mock_handler),
        )

        pumps = adapter.get_pumps_catalog()
        assert len(pumps) == 1
        p = pumps[0]
        assert isinstance(p, UniversalPump)
        assert p.identificador_bico == "BICO_01"
        assert p.identificador_bomba == "ILHA_1"

    def test_get_cashier_shifts_mapping(self) -> None:
        """Garante recuperacao e conversao para UniversalCashierShift."""
        def mock_handler(query: str, params: list[Any]) -> list[dict[str, Any]]:
            if "FROM fechacaixa" in query:
                return [
                    {
                        "caixa_id": "CX_101",
                        "pdv": "PDV_1",
                        "fechado": True,
                        "operador_id": "OP_007",
                        "operador_nome": "MARIA_OLIVEIRA",
                        "turno_descricao": "TARDE",
                        "data_movimento": date(2026, 10, 16),
                        "timestamp_abertura": datetime(2026, 10, 16, 14, 0, 0),
                        "timestamp_fechamento": datetime(2026, 10, 16, 22, 0, 0),
                        "fundo_troco_reais": 200.0,
                        "dinheiro_declarado_reais": 1500.0,
                        "cartao_declarado_reais": 3500.0,
                        "prazo_declarado_reais": 0.0,
                        "venda_combustivel_reais": 4800.0,
                        "venda_produtos_reais": 200.0,
                        "litros_declarados": 900.0,
                        "total_declarado_reais": 5000.0,
                    }
                ]
            return []

        adapter = create_yaml_erp_adapter(
            "generic_postgres",
            connection_factory=lambda: MockDBConnection(mock_handler),
        )

        shifts = adapter.get_cashier_shifts(target_date="2026-10-16")
        assert len(shifts) == 1
        sh = shifts[0]
        assert isinstance(sh, UniversalCashierShift)
        assert sh.caixa_id == "CX_101"
        assert sh.operador_id == "OP_007"
        assert sh.total_declarado_reais == 5000.0
        assert sh.total_sistema_reais == 5000.0
        assert sh.quebra_sobra_reais == 0.0

    def test_get_product_catalog_mapping(self) -> None:
        """Garante busca no catalogo de produtos com filtros de termo e categoria."""
        def mock_handler(query: str, params: list[Any]) -> list[dict[str, Any]]:
            if "FROM produtos" in query:
                return [
                    {
                        "sku": "PROD_OLEO",
                        "descricao_produto": "Oleo Lubrificante 5W30",
                        "grupo_comercial": "LUBRIFICANTES",
                        "preco_unitario_reais": 45.0,
                    }
                ]
            return []

        adapter = create_yaml_erp_adapter(
            "generic_postgres",
            connection_factory=lambda: MockDBConnection(mock_handler),
        )

        items = adapter.get_product_catalog(filter_term="oleo", category="LUBRIFICANTES")
        assert len(items) == 1
        it = items[0]
        assert isinstance(it, UniversalSaleItem)
        assert it.sku == "PROD_OLEO"
        assert it.descricao_produto == "Oleo Lubrificante 5W30"
        assert it.preco_unitario_reais == 45.0

    def test_child_tables_project_foreign_key_in_sql(self) -> None:
        """Garante que a query de itens projeta a foreign key e vincula os itens aos cupons."""
        captured_queries: list[str] = []

        def mock_handler(query: str, params: list[Any]) -> list[dict[str, Any]]:
            captured_queries.append(query)
            if "FROM pedido" in query:
                return [
                    {
                        "cupom_id": "PED_555",
                        "pdv": "PDV1",
                        "data_hora": datetime(2026, 10, 16, 10, 0, 0),
                        "total_reais": 200.0,
                        "status": "CONCLUIDA",
                        "operador": "JOAO",
                        "motivo_cancelamento": None,
                    }
                ]
            if "FROM itemped" in query:
                assert "__parent_sale_id__" in query
                assert "pedido AS __parent_sale_id__" in query
                return [
                    {
                        "__parent_sale_id__": "PED_555",
                        "sku": "ETANOL",
                        "descricao_produto": "Etanol Hidratado",
                        "preco_unitario_reais": 4.0,
                        "quantidade": 50.0,
                        "total_item_reais": 200.0,
                    }
                ]
            return []

        adapter = create_yaml_erp_adapter(
            "generic_postgres",
            connection_factory=lambda: MockDBConnection(mock_handler),
        )

        receipts = adapter.get_recent_sales(limit=10)
        assert len(receipts) == 1
        assert receipts[0].cupom_id == "PED_555"
        assert len(receipts[0].itens) == 1
        assert receipts[0].itens[0].sku == "ETANOL"
        assert receipts[0].itens[0].total_item_reais == 200.0

    def test_column_transform_and_default_value(self) -> None:
        """Garante aplicacao de transforms (strip, upper) e default_value em colunas nulas."""
        tbl = TableMappingConfig(
            table_name="produtos",
            columns={
                "sku": ColumnMappingConfig(
                    source_column="codpro",
                    transform="upper",
                    default_value="SEM_CODIGO",
                ),
                "descricao_produto": ColumnMappingConfig(
                    source_column="nompro",
                    transform="strip",
                    default_value="PRODUTO INDEFINIDO",
                ),
                "preco_unitario_reais": "valvenda",
            },
        )
        adapter = YAMLDataMapperERPAdapter(
            ERPMappingConfig(erp_name="TestERP", tables={"products": tbl}),
            connection_factory=lambda: MockDBConnection(
                lambda q, p: [
                    {
                        "sku": "  gas_premium  ",
                        "descricao_produto": None,
                        "preco_unitario_reais": 6.89,
                    }
                ]
            ),
        )

        prods = adapter.get_product_catalog()
        assert len(prods) == 1
        assert prods[0].sku == "GAS_PREMIUM"
        assert prods[0].descricao_produto == "PRODUTO INDEFINIDO"

    def test_get_pump_dispenses_incluir_cancelados_false(self) -> None:
        """Garante filtragem de abastecimentos cancelados quando incluir_cancelados=False."""
        captured_queries: list[str] = []

        def mock_handler(query: str, params: list[Any]) -> list[dict[str, Any]]:
            captured_queries.append(query)
            return []

        tbl = TableMappingConfig(
            table_name="fechabomba",
            status_column="situacao",
            cancelled_value="CANCELADO",
            columns={"identificador_bico": "codbom"},
        )
        adapter = YAMLDataMapperERPAdapter(
            ERPMappingConfig(erp_name="TestERP", tables={"pumps": tbl}),
            connection_factory=lambda: MockDBConnection(mock_handler),
        )

        adapter.get_pump_dispenses(incluir_cancelados=False)
        assert len(captured_queries) == 1
        assert "COALESCE(situacao::text, '') != %s" in captured_queries[0]

    def test_check_health_live(self) -> None:
        """Garante retorno de diagnostico com contagem de tabelas."""
        def mock_handler(query: str, params: list[Any]) -> list[dict[str, Any]]:
            return [{"cnt": 42}]

        adapter = create_yaml_erp_adapter(
            "generic_postgres",
            connection_factory=lambda: MockDBConnection(mock_handler),
        )

        h = adapter.check_health()
        assert h["status"] == "healthy"
        assert h["connected"] is True
        assert h["erp_name"] == "Generic PostgreSQL"
        assert isinstance(h["latency_ms"], float)
        assert h["record_counts"]["sales"] == 42


class TestYAMLDataMapperFallbackAndResilience:
    """Suite de contingencia e resiliencia operacional."""

    def test_force_offline_mode_returns_fallback_data(self) -> None:
        """Garante que force_offline=True utiliza MockERPAdapter com total isolamento."""
        adapter = create_yaml_erp_adapter("generic_postgres", force_offline=True)
        assert adapter.is_connected is False
        assert adapter.adapter_name == "YAML Data Mapper [Generic PostgreSQL]"

        sales = adapter.get_recent_sales(limit=5)
        assert len(sales) > 0
        assert isinstance(sales[0], UniversalSaleReceipt)

        tanks = adapter.get_tank_inventory()
        assert len(tanks) > 0
        assert isinstance(tanks[0], UniversalTankReading)

        dispenses = adapter.get_pump_dispenses(limit=5)
        assert len(dispenses) > 0
        assert isinstance(dispenses[0], UniversalDispenserLog)

        shifts = adapter.get_cashier_shifts(limit=5)
        assert len(shifts) > 0
        assert isinstance(shifts[0], UniversalCashierShift)

        prods = adapter.get_product_catalog(limit=5)
        assert len(prods) > 0
        assert isinstance(prods[0], UniversalSaleItem)

    def test_fallback_on_db_exception(self) -> None:
        """Garante acionamento automatico do fallback quando o banco falha."""
        def failing_handler(query: str, params: list[Any]) -> list[dict[str, Any]]:
            raise RuntimeError("Conexao com banco interrompida")

        adapter = create_yaml_erp_adapter(
            "generic_postgres",
            connection_factory=lambda: MockDBConnection(failing_handler),
            fallback_on_error=True,
        )

        # Deve acionar fallback e retornar dados sem lancar excecao fatal
        sales = adapter.get_recent_sales(limit=5)
        assert len(sales) > 0

    def test_raise_error_when_fallback_disabled(self) -> None:
        """Garante lancamento de ERPQueryError quando fallback_on_error=False."""
        def failing_handler(query: str, params: list[Any]) -> list[dict[str, Any]]:
            raise RuntimeError("Erro fatal de conexao")

        adapter = create_yaml_erp_adapter(
            "generic_postgres",
            connection_factory=lambda: MockDBConnection(failing_handler),
            fallback_on_error=False,
        )

        with pytest.raises(ERPQueryError):
            adapter.get_recent_sales(limit=5)

    def test_check_health_offline_status(self) -> None:
        """Garante formato correto de relatorio de saude quando em offline."""
        adapter = create_yaml_erp_adapter("generic_postgres", force_offline=True)
        health = adapter.check_health()
        assert health["status"] == "offline_fallback"
        assert health["connected"] is False
        assert health["mode"] == "offline_fallback"

    def test_context_manager_lifecycle(self) -> None:
        """Garante operacao segura via context manager."""
        with create_yaml_erp_adapter("generic_postgres", force_offline=True) as adapter:
            assert isinstance(adapter, BaseERPAdapter)
            assert adapter.connect() is False
            adapter.disconnect()


class TestBlock4QualityAndZeroTravessoes:
    """Suite de qualidade de codigo: zero travessoes e benchmark sub-segundo."""

    def test_zero_travessoes_in_all_yaml_and_adapter_files(self) -> None:
        """Garante ausencia absoluta de travessoes (em-dash e en-dash) nos arquivos do P3-3."""
        base_dir = Path(__file__).resolve().parent.parent.parent
        files_to_check = [
            base_dir / "core" / "adapters" / "erp" / "yaml_data_mapper.py",
            base_dir / "core" / "adapters" / "erp" / "__init__.py",
            base_dir / "config" / "erp_mappings" / "generic_postgres.yaml",
            base_dir / "config" / "erp_mappings" / "linx_postos.yaml",
            base_dir / "config" / "erp_mappings" / "petros.yaml",
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
                    violations.append(f"{file_path.name}:{line_no} contem em-dash: {line}")
                if en_dash in line:
                    violations.append(f"{file_path.name}:{line_no} contem en-dash: {line}")

        assert not violations, "Violacoes da regra de ZERO TRAVESSOES encontradas:\n" + "\n".join(violations)

    def test_sub_second_performance_offline(self) -> None:
        """Garante que o adaptador declarativo opera em nivel sub-segundo."""
        adapter = create_yaml_erp_adapter("generic_postgres", force_offline=True)

        start = time.perf_counter()
        for _ in range(50):
            _ = adapter.get_recent_sales(start_date="2026-10-14", limit=10)
            _ = adapter.get_tank_inventory()
            _ = adapter.get_pump_dispenses(limit=5)
            _ = adapter.get_cashier_shifts(target_date="2026-10-14")
            _ = adapter.get_product_catalog(filter_term="gasolina")
            _ = adapter.check_health()
        elapsed = time.perf_counter() - start

        assert elapsed < 0.25, f"Benchmark muito lento: {elapsed:.4f}s para 50 iteracoes"
