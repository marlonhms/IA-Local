"""Testes Unitarios da Fase P1 do Backend (AURA Carbon Core).

Valida integralmente as entregas P1.1, P1.2 e P1.3:
- P1.1: DomainToolRegistry, cartucho vertical fuel_convenience, AuraEngine com
  pack_id='pharmacy_health' + MockERPAdapter respondendo conformidade_sngpc_anvisa
  e fechamento_caixa_pbm sem tocar tabelas de posto, e SemanticRouter com
  confidence_threshold=0.72 e frases limpas indexadas por pack_id.
- P1.2: Eliminacao de TRIM() em JOINs de PostgresLocalERPAdapter e validador
  lexical central assert_readonly_safe_sql conectado a PostgresLocalERPAdapter e
  YAMLDataMapperERPAdapter.
- P1.3: Cliente unificado google-genai com Keep-Alive httpx, zero import de
  google.generativeai no core/config e registro dos widgets GenUI Next-Gen
  (WhatIfSimulatorUI, RealizedRoiScorecardUI, McpActionConfirmationUI).
Zero travessoes em todo o modulo.
"""

from __future__ import annotations

import inspect
import re
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import core.aura_engine as ae
import core.rag_engine as re_mod
import core.semantic_router as sr_mod
from core.adapters.erp.mock_adapter import MockERPAdapter
from core.adapters.erp.postgres_local_adapter import PostgresLocalERPAdapter
from core.adapters.erp.yaml_data_mapper import YAMLDataMapperERPAdapter
from core.domain.domain_pack_loader import (
    DomainPackContext,
    load_domain_pack,
    reset_active_domain_pack,
)
from core.llm_client import (
    close_genai_clients,
    embed_content,
    get_genai_client,
    get_http_pool_stats,
)
from core.packs import DomainToolRegistry, create_default_tool_registry
from core.packs.fuel_convenience import FUEL_ONLY_INTENTS, FuelConvenienceTools
from core.tenancy import ReadOnlySQLViolationError, assert_readonly_safe_sql

ROOT_DIR = Path(__file__).resolve().parent.parent.parent


class TestP11DomainToolRegistryAndVerticalCartridge:
    """Valida desacoplamento domain-agnostic (P1.1) e roteamento por DomainPack."""

    def test_default_registry_registers_universal_and_fuel_cartridge(self) -> None:
        registry = create_default_tool_registry()
        univ = registry.list_universal_intents()
        for expected in (
            "auditoria_turno_caixa",
            "previsao_runout_estoque",
            "market_basket_cross_sell",
            "simular_cenario_what_if",
        ):
            assert expected in univ

        fuel_intents = registry.list_pack_intents("fuel_convenience")
        for expected_fuel in ("lmc_anp", "vazao_bicos", "benchmark_anp"):
            assert expected_fuel in fuel_intents

    def test_universal_tools_operate_strictly_over_base_erp_adapter(self, monkeypatch) -> None:
        import core.tools as tools_mod

        def _forbid_raw_erp_conn(*_args, **_kwargs):
            raise AssertionError("Tools universais AUDS nunca podem abrir get_erp_connection() direto!")

        monkeypatch.setattr(tools_mod, "get_erp_connection", _forbid_raw_erp_conn)

        registry = create_default_tool_registry()
        adapter = MockERPAdapter()
        pack = load_domain_pack("pharmacy_health")

        for intent in (
            "auditoria_turno_caixa",
            "previsao_runout_estoque",
            "market_basket_cross_sell",
            "simular_cenario_what_if",
        ):
            res = registry.dispatch(
                intent=intent,
                query=f"executar {intent}",
                erp_adapter=adapter,
                domain_pack=pack,
            )
            assert res is not None
            assert res.pack_id == "pharmacy_health"
            assert res.raw_result["pack_id"] == "pharmacy_health"

    @pytest.mark.asyncio
    async def test_aura_engine_pharmacy_health_answers_without_touching_fuel_tables(
        self,
        monkeypatch,
        tmp_path: Path,
    ) -> None:
        import core.tools as tools_mod

        def _forbid_fuel_db(*_args, **_kwargs):
            raise AssertionError("pharmacy_health nao pode tocar conexao/tabelas de posto!")

        monkeypatch.setattr(tools_mod, "get_erp_connection", _forbid_fuel_db)
        monkeypatch.setattr(ae, "get_erp_connection", _forbid_fuel_db)

        class _Chunk:
            def __init__(self, text: str):
                self.text = text
                self.usage_metadata = None

        class _FastCleanModel:
            def __init__(self, model_name: str):
                self.model_name = model_name

            async def generate_content_async(self, prompt, stream=True, request_options=None):
                async def _gen():
                    yield _Chunk("Auditoria concluida com sucesso para a operacao farmaceutica.")

                return _gen()

        monkeypatch.setattr(ae.genai, "GenerativeModel", _FastCleanModel)

        adapter = MockERPAdapter()
        mem = ae.AuraSessionMemory(db_path=tmp_path / "pharmacy_sessions.db")
        engine = ae.AuraEngine(
            tenant_id="tenant_farma_01",
            filial_id="farma_01",
            erp_adapter=adapter,
            session_memory=mem,
            pack_id="pharmacy_health",
        )

        try:
            # 1. conformidade_sngpc_anvisa via ask_stream completo
            chunks_sngpc = []
            async for ch in engine.ask_stream(
                query="Auditar conformidade sngpc anvisa e medicamentos controlados",
                session_id="sess_farma_1",
                pack_id="pharmacy_health",
            ):
                chunks_sngpc.append(ch)

            intent_chunks = [c for c in chunks_sngpc if c.chunk_type == ae.AuraChunkType.INTENT]
            tool_chunks = [c for c in chunks_sngpc if c.chunk_type == ae.AuraChunkType.TOOL_RESULT]
            done_chunks = [c for c in chunks_sngpc if c.chunk_type == ae.AuraChunkType.DONE]

            assert intent_chunks and intent_chunks[0].text == "conformidade_sngpc_anvisa"
            assert intent_chunks[0].data["pack_id"] == "pharmacy_health"
            assert tool_chunks
            tool_res = tool_chunks[0].data["result"]
            assert tool_res["pack_id"] == "pharmacy_health"
            assert tool_res["intent"] == "conformidade_sngpc_anvisa"
            assert tool_res["tabelas_legadas_posto_acessadas"] is False
            assert done_chunks

            # 2. fechamento_caixa_pbm via ask_stream completo
            chunks_pbm = []
            async for ch in engine.ask_stream(
                query="Mostrar fechamento de caixa pbm de hoje",
                session_id="sess_farma_2",
                pack_id="pharmacy_health",
            ):
                chunks_pbm.append(ch)

            intent_pbm = [c for c in chunks_pbm if c.chunk_type == ae.AuraChunkType.INTENT]
            tool_pbm = [c for c in chunks_pbm if c.chunk_type == ae.AuraChunkType.TOOL_RESULT]
            assert intent_pbm and intent_pbm[0].text == "fechamento_caixa_pbm"
            assert tool_pbm
            pbm_res = tool_pbm[0].data["result"]
            assert pbm_res["pack_id"] == "pharmacy_health"
            assert pbm_res["deterministico"] is True
            assert pbm_res["total_turnos_auditados"] > 0
        finally:
            reset_active_domain_pack()

    def test_semantic_router_threshold_072_and_clean_phrase_seeding(self, monkeypatch) -> None:
        router = sr_mod.SemanticRouter()
        assert router.confidence_threshold == pytest.approx(0.72)

        embedded_batches: list[list[str]] = []
        inserted_rows: list[tuple] = []

        def _fake_embed_content(model, content, output_dimensionality=768, task_type=None, **_kwargs):
            batch = list(content) if isinstance(content, list) else [content]
            embedded_batches.append(batch)
            return [[0.1] * 4 for _ in batch]

        class _FakeCursor:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def execute(self, sql, params=None):
                if "INSERT INTO intencoes_vetores" in sql and params:
                    inserted_rows.append(params)

            def fetchone(self):
                return ("CREATE INDEX idx_intencoes_vetores_hnsw ... WITH (m='32', ef_construction='256')",)

            def fetchall(self):
                return []

        class _FakeConn:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def cursor(self, *args, **kwargs):
                return _FakeCursor()

            def commit(self):
                pass

        monkeypatch.setattr("core.llm_client.embed_content", _fake_embed_content)
        monkeypatch.setattr(router, "_get_connection", lambda: _FakeConn())

        farma_pack = load_domain_pack("pharmacy_health")
        count = router.seed_domain_pack_intents(packs=[farma_pack])

        assert count > 0
        assert embedded_batches
        for phrase in embedded_batches[0]:
            assert not phrase.startswith("Intenção:")
            assert "Pergunta Típica:" not in phrase

        # Todas as insercoes devem conter pack_id='pharmacy_health'
        assert all(row[1] == "pharmacy_health" for row in inserted_rows)
        assert any(row[0] == "conformidade_sngpc_anvisa" for row in inserted_rows)


class TestP12SargableSQLAndReadOnlyGuard:
    """Valida eliminacao de TRIM() em JOINs e validador lexical read-only (P1.2)."""

    def test_postgres_adapter_has_zero_trim_in_joins(self) -> None:
        src = inspect.getsource(PostgresLocalERPAdapter)
        trim_joins = re.findall(r"JOIN\s+\w+\s+\w+\s+ON\s+[^\n]*TRIM\s*\(", src, re.IGNORECASE)
        assert trim_joins == [], f"Encontrados JOINs nao-SARGable com TRIM(): {trim_joins}"

    @pytest.mark.parametrize(
        "safe_sql",
        [
            "SELECT 1;",
            "SELECT p.codi, i.codpec FROM pedido p LEFT JOIN itemped i ON i.pedido = p.codi LIMIT 10;",
            "WITH sub AS (SELECT codi FROM pedido WHERE dtem >= %s) SELECT * FROM sub;",
            "SELECT 'UPDATE permitido apenas como texto literal' AS msg FROM pedido LIMIT 1;",
        ],
    )
    def test_assert_readonly_safe_sql_allows_valid_selects(self, safe_sql: str) -> None:
        assert assert_readonly_safe_sql(safe_sql) == safe_sql

    @pytest.mark.parametrize(
        "malicious_sql",
        [
            "",
            "SELECT 1; DROP TABLE pedido;",
            "SELECT * FROM pedido -- comentario evasivo",
            "SELECT /* comentario */ * FROM pedido",
            "SELECT $$payload$$ FROM pedido",
            "SELECT $tag$DROP TABLE pedido$tag$",
            "SELECT E'\\''; DROP TABLE pedido; SELECT E'\\''",
            "SELECT e'escape_literal' FROM pedido",
            'SELECT "pg_sleep"(10)',
            'SELECT pg_catalog."pg_sleep"(10)',
            'SELECT "set_config"(\'search_path\', \'public\', false)',
            "DELETE FROM pedido WHERE codi = '1'",
            "UPDATE produtos SET valvenda = 0",
            "INSERT INTO pedido VALUES (1)",
            "WITH x AS (DELETE FROM pedido RETURNING *) SELECT * FROM x",
            "COPY pedido TO '/tmp/dump.csv'",
            "SELECT pg_sleep(10)",
            "SELECT dblink('host=evil', 'SELECT 1')",
            "SELECT pg_read_file('/etc/passwd')",
            "SELECT lo_import('/etc/passwd')",
            "SELECT * INTO temp_copy FROM pedido",
            "SELECT * FROM pedido FOR UPDATE",
            "SELECT * FROM pedido FOR KEY SHARE",
            "SELECT * FROM pedido FOR NO KEY UPDATE",
        ],
    )
    def test_assert_readonly_safe_sql_blocks_unsafe_queries(self, malicious_sql: str) -> None:
        with pytest.raises(ReadOnlySQLViolationError):
            assert_readonly_safe_sql(malicious_sql)

    def test_tools_module_routes_all_direct_sql_through_readonly_guard(self) -> None:
        import core.tools as tools_mod

        tools_src = (ROOT_DIR / "core" / "tools.py").read_text(encoding="utf-8")
        # Nenhuma chamada direta cur.execute( fora do wrapper _execute_readonly_sql
        wrapper_matches = re.findall(r"^\s*cur\.execute\(", tools_src, flags=re.MULTILINE)
        assert len(wrapper_matches) == 2, (
            f"Esperadas apenas as 2 chamadas internas de _execute_readonly_sql, encontradas: {len(wrapper_matches)}"
        )

        fake_cur = MagicMock()
        with pytest.raises(ReadOnlySQLViolationError):
            tools_mod._execute_readonly_sql(fake_cur, 'SELECT "pg_sleep"(5);')
        fake_cur.execute.assert_not_called()

        tools_mod._execute_readonly_sql(fake_cur, "SELECT COUNT(*) FROM pedido WHERE dtem = %s;", ["2026-11-24"])
        fake_cur.execute.assert_called_once()


class TestP1HardeningPackIsolationAndNoSideEffects:
    """Valida bloqueio de fallback PostoTools, cache por pack_id e get_active_domain_pack puro."""

    def test_get_active_domain_pack_does_not_mutate_contextvar(self) -> None:
        from core.domain.domain_pack_loader import (
            get_active_domain_pack,
            peek_active_domain_pack,
        )

        reset_active_domain_pack()
        try:
            assert peek_active_domain_pack() is None
            pack = get_active_domain_pack("pharmacy_health")
            assert pack.pack_id == "pharmacy_health"
            # Chamada de leitura nao deve mutar _ACTIVE_PACK_VAR fora de DomainPackContext
            assert peek_active_domain_pack() is None

            default_pack = get_active_domain_pack()
            assert default_pack.pack_id == "fuel_convenience"
            assert peek_active_domain_pack() is None
        finally:
            reset_active_domain_pack()

    def test_semantic_router_help_and_procedural_cache_keyed_by_pack_id(self) -> None:
        router = sr_mod.SemanticRouter()
        with DomainPackContext("pharmacy_health"):
            intent_help, _, _ = router.route("ajuda", use_cache=True)
            intent_proc, _, _ = router.route("como dar entrada em nota fiscal", use_cache=True)

        assert intent_help == "ajuda_sistema"
        assert intent_proc == "procedimento_erp"
        assert "pharmacy_health::ajuda" in router._memory_cache
        assert "ajuda" not in router._memory_cache
        assert "pharmacy_health::como dar entrada em nota fiscal" in router._memory_cache
        assert "como dar entrada em nota fiscal" not in router._memory_cache

    @pytest.mark.asyncio
    async def test_execute_intent_and_resolver_block_postotools_fallback_for_non_fuel_pack(
        self,
        monkeypatch,
        tmp_path: Path,
    ) -> None:
        from fastapi.testclient import TestClient

        import core.tools as tools_mod
        from core.aura_api import create_aura_app

        def _forbid_fuel_db(*_args, **_kwargs):
            raise AssertionError("Pack nao-posto jamais pode abrir get_erp_connection()!")

        monkeypatch.setattr(tools_mod, "get_erp_connection", _forbid_fuel_db)
        monkeypatch.setattr(ae, "get_erp_connection", _forbid_fuel_db)

        adapter = MockERPAdapter()
        mem = ae.AuraSessionMemory(db_path=tmp_path / "pack_iso.db")
        engine = ae.AuraEngine(
            tenant_id="tenant_farma_iso",
            filial_id="farma_02",
            erp_adapter=adapter,
            session_memory=mem,
            pack_id="pharmacy_health",
        )

        # 1. StationStatus e get_dados_filial expoem pack_id e isolam cache por pack
        st_status = engine.get_stations_status()
        assert st_status.pack_id == "pharmacy_health"
        dados_farma = engine.get_dados_filial()
        assert dados_farma["pack_id"] == "pharmacy_health"
        with DomainPackContext("retail_supermarket"):
            dados_retail = engine.get_dados_filial()
            assert dados_retail["pack_id"] == "retail_supermarket"
            assert dados_retail["nome"] != dados_farma["nome"]
        # Cache da farmacia permanece intacto
        assert engine.get_dados_filial()["pack_id"] == "pharmacy_health"

        # 2. execute_tool_direct despacha via DomainToolRegistry para pharmacy_health
        res_sngpc = await engine.execute_tool_direct(
            "conformidade_sngpc_anvisa",
            params={},
            pack_id="pharmacy_health",
        )
        assert res_sngpc["status"] == "success"
        assert res_sngpc["data"]["pack_id"] == "pharmacy_health"
        assert res_sngpc["data"]["tabelas_legadas_posto_acessadas"] is False

        # 3. execute_tool_direct bloqueia fallback legado de posto (ex: lmc_anp / previsao_tanques)
        res_blocked = await engine.execute_tool_direct(
            "lmc_anp",
            params={},
            pack_id="pharmacy_health",
        )
        assert res_blocked["status"] == "error"
        assert "bloqueado" in res_blocked["error"].lower()

        # 4. Endpoint HTTP POST /api/v1/aura/execute-intent propaga pack_id e bloqueia posto
        app = create_aura_app(engine=engine)
        client = TestClient(app)
        r_ok = client.post(
            "/api/v1/aura/execute-intent",
            json={"tool_name": "fechamento_caixa_pbm", "pack_id": "pharmacy_health"},
        )
        assert r_ok.status_code == 200
        assert r_ok.json()["data"]["pack_id"] == "pharmacy_health"

        r_block = client.post(
            "/api/v1/aura/execute-intent",
            json={"tool_name": "previsao_tanques", "pack_id": "pharmacy_health"},
        )
        assert r_block.status_code == 400
        assert "bloqueado" in r_block.json()["detail"]["error"].lower()

        # 5. _resolver_contexto_ferramenta bloqueia queda em elifs legados de PostoTools
        with DomainPackContext("pharmacy_health"):
            _, raw_res, _, _, _ = engine._resolver_contexto_ferramenta(
                "Qual o faturamento dos tanques?",
                "vendas_analitico",
            )
            assert raw_res["status"] == "unsupported_for_pack"
            assert raw_res["pack_id"] == "pharmacy_health"
            assert raw_res["tabelas_legadas_posto_acessadas"] is False
            assert raw_res["fallback_posto_bloqueado"] is True

    def test_adapters_enforce_readonly_guard_before_db_access(self) -> None:
        pg_adapter = PostgresLocalERPAdapter(fallback_on_error=False, force_offline=False)
        with pytest.raises(ReadOnlySQLViolationError):
            pg_adapter._execute_query("SELECT pg_sleep(5);")

        yaml_adapter = YAMLDataMapperERPAdapter(
            mapping={"erp_name": "test_erp", "tables": {"sales": {"table_name": "vendas"}}},
            connection_factory=lambda: (_ for _ in ()).throw(AssertionError("Nao deveria abrir conexao!")),
            fallback_on_error=False,
        )
        with pytest.raises(ReadOnlySQLViolationError):
            yaml_adapter._execute_query("SELECT 1; DELETE FROM vendas;")


class TestP13UnifiedGenAIClientAndGenUIRegistry:
    """Valida migracao para google-genai Keep-Alive e registro dos 3 widgets GenUI (P1.3)."""

    def test_zero_legacy_google_generativeai_imports_in_core_and_config(self) -> None:
        target_files = [
            ROOT_DIR / "config" / "settings.py",
            ROOT_DIR / "core" / "llm_client.py",
            ROOT_DIR / "core" / "aura_engine.py",
            ROOT_DIR / "core" / "rag_engine.py",
            ROOT_DIR / "core" / "semantic_router.py",
        ]
        for path in target_files:
            text = path.read_text(encoding="utf-8")
            assert "import google.generativeai" not in text, f"Import legado encontrado em {path}"

    def test_singleton_genai_client_reuses_keepalive_pool(self) -> None:
        close_genai_clients()
        c1 = get_genai_client(api_key="test_key_keepalive_p13")
        c2 = get_genai_client(api_key="test_key_keepalive_p13")
        assert c1 is c2
        stats = get_http_pool_stats()
        assert stats["active_clients"] >= 1
        assert stats["max_keepalive_connections"] >= 16
        close_genai_clients()

    def test_nextgen_genui_components_registered_in_backend_and_frontend(self) -> None:
        # 1. Backend GENUI_COMPONENT_REGISTRY_MAP
        for intent_key, expected_comp in (
            ("simular_cenario_what_if", "WhatIfSimulatorUI"),
            ("realized_roi_scorecard", "RealizedRoiScorecardUI"),
            ("mcp_external_write_confirmation", "McpActionConfirmationUI"),
        ):
            assert intent_key in ae.GENUI_COMPONENT_REGISTRY_MAP
            assert ae.GENUI_COMPONENT_REGISTRY_MAP[intent_key]["component_name"] == expected_comp
            env = ae.build_canonical_genui_envelope(
                intencao=intent_key,
                tool_call_id=ae.generate_tool_call_id(),
                resultado_bruto={"status": "OK", "title": expected_comp},
                executive_summary=f"Resumo {expected_comp}",
            )
            assert env is not None
            assert env.component_name == expected_comp

        # 2. Frontend web/js/aura-genui-widgets.js
        widgets_js = (ROOT_DIR / "web" / "js" / "aura-genui-widgets.js").read_text(encoding="utf-8")
        for comp in ("WhatIfSimulatorUI", "RealizedRoiScorecardUI", "McpActionConfirmationUI"):
            assert f"class {comp} extends BaseGenUIWidget" in widgets_js
            assert f"name: '{comp}'" in widgets_js

    def test_zero_travessoes_in_new_p1_files(self) -> None:
        p1_files = [
            ROOT_DIR / "core" / "llm_client.py",
            ROOT_DIR / "core" / "packs" / "__init__.py",
            ROOT_DIR / "core" / "packs" / "registry.py",
            ROOT_DIR / "core" / "packs" / "fuel_convenience" / "__init__.py",
            ROOT_DIR / "core" / "packs" / "fuel_convenience" / "tools.py",
            Path(__file__).resolve(),
        ]
        for path in p1_files:
            content = path.read_text(encoding="utf-8")
            assert "\u2014" not in content, f"Em-dash encontrado em {path}"
            assert "\u2013" not in content, f"En-dash encontrado em {path}"
