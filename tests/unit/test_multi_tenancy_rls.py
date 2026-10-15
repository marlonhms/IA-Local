"""
Suite de Testes Unitarios para Multi-Tenancy Robusto e Row-Level Security (RLS) (Fase P2-5).
Valida isolamento estrito entre Filial 1 e Filial 2, bloqueio de CrossTenantAccessError
sob tentativas de injecao SQL ou adulteracao de parametros, injecao automatica de
app.current_filial no pool de conexoes pgvector e conformidade com zero travessoes.
"""

from __future__ import annotations

import asyncio
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Self
from unittest.mock import MagicMock, patch

import pytest

from config.settings import BASE_DIR
from core import db_pool
from core.tenancy import (
    CrossTenantAccessError,
    TenantContext,
    filter_records_by_filial,
    inject_rls_filial_context,
    load_rls_migration_sql,
    validate_filial_id,
    validate_sql_filial_isolation,
)


@dataclass
class DummyProductRecord:
    """Objeto estruturado para testar filtragem deterministica em memoria."""

    codpro: int
    descricao: str
    codfilial: int


class FakeRlsPostgresSession:
    """
    Simulador deterministico de sessao PostgreSQL com Row-Level Security (RLS) ativo
    baseado em current_setting('app.current_filial', true)::int.
    """

    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = list(rows)
        self.guc_settings: dict[str, str] = {}
        self.executed_queries: list[tuple[str, Any]] = []
        self.closed = False

    def set_client_encoding(self, encoding: str) -> None:
        self.guc_settings["client_encoding"] = encoding

    def rollback(self) -> None:
        pass

    def cursor(self) -> FakeRlsCursor:
        return FakeRlsCursor(self)

    def select_visible_rows(self) -> list[dict[str, Any]]:
        """Aplica a politica RLS: codfilial = current_setting('app.current_filial', true)::int."""
        raw_filial = self.guc_settings.get("app.current_filial", "")
        if not raw_filial:
            return []
        active_filial = int(raw_filial)
        return [dict(r) for r in self._rows if r.get("codfilial") == active_filial]


class FakeRlsCursor:
    """Cursor simulado que interpreta SET LOCAL / SET SESSION app.current_filial."""

    def __init__(self, session: FakeRlsPostgresSession) -> None:
        self._session = session
        self.closed = False

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        self.close()

    def execute(self, sql: str, params: Any = None) -> None:
        self._session.executed_queries.append((sql, params))
        if "app.current_filial" in sql and params:
            val = params[0] if isinstance(params, (tuple, list)) else params
            self._session.guc_settings["app.current_filial"] = str(val)

    def close(self) -> None:
        self.closed = True


@pytest.mark.unit
class TestMultiTenancyRLS:
    """Testes de isolamento multi-posto, RLS e protecao contra vazamento entre filiais."""

    def setup_method(self) -> None:
        TenantContext.clear()

    def teardown_method(self) -> None:
        TenantContext.clear()

    def test_rls_sql_script_completeness(self) -> None:
        """Verifica que scripts/rls_multi_tenant.sql configura RLS nas 3 tabelas vetoriais."""
        sql_content = load_rls_migration_sql()
        expected_tables = [
            "intencoes_vetores",
            "produtos_vetores",
            "conhecimento_operacional",
        ]
        for table in expected_tables:
            assert table in sql_content, f"Tabela {table} ausente no script RLS"
            assert f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;" in sql_content
            assert f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY;" in sql_content
            assert f"CREATE POLICY filial_isolation_policy ON {table}" in sql_content

        assert "codfilial INT NOT NULL DEFAULT 1" in sql_content
        assert "current_setting('app.current_filial', true)::int" in sql_content

    def test_tenant_context_sync_and_nested_isolation(self) -> None:
        """Garante que TenantContext isola e restaura filial_id e tenant_id corretamente."""
        assert TenantContext.get_filial_id() is None
        assert TenantContext.get_tenant_id() == "default"

        with TenantContext(filial_id=1, tenant_id="rede_posto_sul"):
            assert TenantContext.get_filial_id() == 1
            assert TenantContext.get_tenant_id() == "rede_posto_sul"
            info_1 = TenantContext.get_current()
            assert info_1 is not None and info_1.filial_id == 1

            with TenantContext(filial_id=2, tenant_id="rede_posto_norte"):
                assert TenantContext.get_filial_id() == 2
                assert TenantContext.get_tenant_id() == "rede_posto_norte"

            # Ao sair do bloco interno, restaura Filial 1
            assert TenantContext.get_filial_id() == 1
            assert TenantContext.get_tenant_id() == "rede_posto_sul"

        assert TenantContext.get_filial_id() is None
        assert TenantContext.get_current() is None

    def test_tenant_context_thread_and_async_isolation(self) -> None:
        """Comprova que multiplas threads e corrotinas nao vazam filial_id entre si."""
        results_by_thread: dict[int, int] = {}

        def worker(f_id: int) -> None:
            with TenantContext(filial_id=f_id, tenant_id=f"tenant_{f_id}"):
                results_by_thread[f_id] = TenantContext.require_filial_id()

        t1 = threading.Thread(target=worker, args=(1,))
        t2 = threading.Thread(target=worker, args=(2,))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert results_by_thread[1] == 1
        assert results_by_thread[2] == 2
        assert TenantContext.get_filial_id() is None

        async def async_runner() -> tuple[int, int]:
            async def task_fn(filial: int, delay: float) -> int:
                async with TenantContext(filial_id=filial, tenant_id=f"async_{filial}"):
                    await asyncio.sleep(delay)
                    return TenantContext.require_filial_id()

            res1, res2 = await asyncio.gather(task_fn(1, 0.01), task_fn(2, 0.005))
            return res1, res2

        r1, r2 = asyncio.run(async_runner())
        assert r1 == 1
        assert r2 == 2

    def test_inject_rls_filial_context_and_rls_simulation(self) -> None:
        """Valida injecao de SET LOCAL app.current_filial e isolamento entre Filial 1 e Filial 2."""
        dataset = [
            {"id": 10, "titulo": "Resumo Caixa F1", "codfilial": 1},
            {"id": 11, "titulo": "Estoque Tanque F1", "codfilial": 1},
            {"id": 20, "titulo": "Resumo Caixa F2", "codfilial": 2},
        ]
        session = FakeRlsPostgresSession(dataset)

        # Injeta Filial 1
        injected_1 = inject_rls_filial_context(session, filial_id=1)
        assert injected_1 == 1
        assert ("SET LOCAL app.current_filial = %s", ("1",)) in session.executed_queries
        rows_f1 = session.select_visible_rows()
        assert len(rows_f1) == 2
        assert all(r["codfilial"] == 1 for r in rows_f1)

        # Injeta Filial 2
        injected_2 = inject_rls_filial_context(session, filial_id=2)
        assert injected_2 == 2
        assert ("SET LOCAL app.current_filial = %s", ("2",)) in session.executed_queries
        rows_f2 = session.select_visible_rows()
        assert len(rows_f2) == 1
        assert rows_f2[0]["id"] == 20
        assert rows_f2[0]["codfilial"] == 2

    def test_validate_filial_id_rejects_invalid_values(self) -> None:
        """Garante rejeicao de filial_id <= 0, booleanos, strings ou None."""
        for bad_val in [0, -1, -99, True, False, "1", "1 OR 1=1", None, 1.5]:
            with pytest.raises(CrossTenantAccessError):
                validate_filial_id(bad_val)

    def test_validate_sql_filial_isolation_accepts_valid_queries(self) -> None:
        """Aprova queries parametrizadas que filtram estritamente a filial esperada."""
        sql_pos = (
            "SELECT codpro, descricao FROM produtos_vetores "
            "WHERE ativo = %s AND codfilial = %s ORDER BY codpro"
        )
        assert validate_sql_filial_isolation(sql_pos, (True, 1), expected_filial_id=1) is True

        sql_pyformat = (
            "SELECT id, texto FROM conhecimento_operacional "
            "WHERE cp.codfilial = %(codfilial)s AND categoria = %(cat)s;"
        )
        assert (
            validate_sql_filial_isolation(
                sql_pyformat,
                {"codfilial": 2, "cat": "anp"},
                expected_filial_id=2,
            )
            is True
        )

        sql_named = (
            "SELECT intencao FROM intencoes_vetores "
            "WHERE codfilial = :filial_id"
        )
        assert (
            validate_sql_filial_isolation(
                sql_named,
                {"filial_id": 1},
                expected_filial_id=1,
            )
            is True
        )

    def test_validate_sql_filial_isolation_blocks_cross_tenant_and_injections(self) -> None:
        """
        Garante que uma requisicao da Filial 1 jamais acesse dados da Filial 2,
        mesmo sob injecao de parametros deliberadamente forcados ou tautologias SQL.
        """
        valid_sql = "SELECT * FROM produtos_vetores WHERE codfilial = %s"

        # 1. Tentativa de acessar Filial 2 quando o contexto exige Filial 1
        with pytest.raises(CrossTenantAccessError):
            validate_sql_filial_isolation(valid_sql, (2,), expected_filial_id=1)

        with pytest.raises(CrossTenantAccessError):
            validate_sql_filial_isolation(
                "SELECT * FROM produtos_vetores WHERE codfilial = %(codfilial)s",
                {"codfilial": 2},
                expected_filial_id=1,
            )

        # 2. Query sem WHERE ou sem filtro codfilial
        with pytest.raises(CrossTenantAccessError):
            validate_sql_filial_isolation("SELECT * FROM produtos_vetores", (1,), expected_filial_id=1)

        with pytest.raises(CrossTenantAccessError):
            validate_sql_filial_isolation(
                "SELECT * FROM produtos_vetores WHERE codpro = %s",
                (100,),
                expected_filial_id=1,
            )

        # 3. Filtro literal hardcoded (proibido mesmo que seja o mesmo numero)
        with pytest.raises(CrossTenantAccessError):
            validate_sql_filial_isolation(
                "SELECT * FROM produtos_vetores WHERE codfilial = 1",
                {"codfilial": 1},
                expected_filial_id=1,
            )

        with pytest.raises(CrossTenantAccessError):
            validate_sql_filial_isolation(
                "SELECT * FROM produtos_vetores WHERE codfilial = 2",
                (1,),
                expected_filial_id=1,
            )

        # 4. Tentativas de SQL Injection na string SQL
        malicious_sqls = [
            "SELECT * FROM produtos_vetores WHERE codfilial = %s OR 1=1",
            "SELECT * FROM produtos_vetores WHERE codfilial = %s OR '1'='1'",
            "SELECT * FROM produtos_vetores WHERE codfilial = %s UNION SELECT * FROM produtos_vetores",
            "SELECT * FROM produtos_vetores WHERE codfilial = %s; SET SESSION app.current_filial = '2'",
            "SELECT * FROM produtos_vetores WHERE codfilial = %s -- bypass",
            "SELECT * FROM produtos_vetores WHERE codfilial IN (1, 2) AND codfilial = %s",
            "SELECT * FROM produtos_vetores WHERE codfilial != 99 AND codfilial = %s",
            "SELECT * FROM produtos_vetores WHERE codfilial IS NOT NULL AND codfilial = %s",
        ]
        for bad_sql in malicious_sqls:
            with pytest.raises(CrossTenantAccessError):
                validate_sql_filial_isolation(bad_sql, (1,), expected_filial_id=1)

        # 5. Tentativas de SQL Injection embutidas nos parametros
        sql_with_search = (
            "SELECT * FROM produtos_vetores WHERE codfilial = %s AND descricao LIKE %s"
        )
        with pytest.raises(CrossTenantAccessError):
            validate_sql_filial_isolation(
                sql_with_search,
                (1, "GASOLINA' OR 1=1 --"),
                expected_filial_id=1,
            )

        with pytest.raises(CrossTenantAccessError):
            validate_sql_filial_isolation(
                sql_with_search,
                ("1 OR 1=1", "GASOLINA"),
                expected_filial_id=1,
            )

    def test_filter_records_by_filial_in_memory(self) -> None:
        """Comprova filtragem deterministica em memoria para dicionarios e objetos."""
        mixed_dicts = [
            {"id": 1, "produto": "Gasolina Comum", "codfilial": 1},
            {"id": 2, "produto": "Diesel S10", "codfilial": 2},
            {"id": 3, "produto": "Etanol Hidratado", "filial_id": 1},
            {"id": 4, "produto": "Sem Filial"},
            {"id": 5, "produto": "Filial Booleana Invalida", "codfilial": True},
        ]

        f1_only = filter_records_by_filial(mixed_dicts, filial_id=1)
        assert [r["id"] for r in f1_only] == [1, 3]

        f2_only = filter_records_by_filial(mixed_dicts, filial_id=2)
        assert [r["id"] for r in f2_only] == [2]

        objs = [
            DummyProductRecord(codpro=101, descricao="Lubrificante F1", codfilial=1),
            DummyProductRecord(codpro=202, descricao="Lubrificante F2", codfilial=2),
        ]
        f1_objs = filter_records_by_filial(objs, filial_id=1)
        assert len(f1_objs) == 1
        assert f1_objs[0].codpro == 101

    def test_db_pool_get_vector_connection_injects_session_filial(self) -> None:
        """
        Valida que core/db_pool.py injeta SET SESSION app.current_filial quando
        filial_id e passado explicitamente ou via TenantContext, mantendo 100%
        de retrocompatibilidade quando chamado sem argumentos.
        """
        fake_conn = FakeRlsPostgresSession([])
        mock_pool = MagicMock()
        mock_pool.getconn.return_value = fake_conn

        with patch.object(db_pool, "get_vector_pool", return_value=mock_pool):
            # 1. Chamada sem argumentos e sem TenantContext (100% retrocompativel)
            conn_no_tenant = db_pool.get_vector_connection()
            assert conn_no_tenant.rls_filial_id is None
            assert fake_conn.executed_queries == []
            conn_no_tenant.close()

            # 2. Chamada com parametro explicito filial_id=1
            conn_f1 = db_pool.get_vector_connection(filial_id=1)
            assert conn_f1.rls_filial_id == 1
            assert ("SET SESSION app.current_filial = %s", ("1",)) in fake_conn.executed_queries
            assert fake_conn.guc_settings["app.current_filial"] == "1"
            conn_f1.close()

            # 3. Chamada sem argumentos, mas dentro de um TenantContext(filial_id=2)
            with (
                TenantContext(filial_id=2, tenant_id="posto_filial_2"),
                db_pool.get_vector_db_connection() as conn_f2,
            ):
                assert conn_f2.rls_filial_id == 2
                assert fake_conn.guc_settings["app.current_filial"] == "2"

    def test_zero_travessoes_in_p2_5_files(self) -> None:
        """Valida a regra inegociavel de ZERO travessoes em todos os arquivos do escopo P2-5."""
        em_dash = chr(0x2014)
        en_dash = chr(0x2013)
        files_to_verify = [
            BASE_DIR / "scripts" / "rls_multi_tenant.sql",
            BASE_DIR / "core" / "tenancy.py",
            BASE_DIR / "core" / "db_pool.py",
            Path(__file__),
        ]
        for file_path in files_to_verify:
            assert file_path.exists(), f"Arquivo esperado nao encontrado: {file_path}"
            content = file_path.read_text(encoding="utf-8")
            assert em_dash not in content, f"Travessao (0x2014) detectado em {file_path}"
            assert en_dash not in content, f"Travessao (0x2013) detectado em {file_path}"
