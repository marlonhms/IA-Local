"""
Testes Unitarios da Convergencia do Armazenamento pgvector Local (Fase 7).
Valida padronizacao do PostgreSQL 16 na porta 5433, banco 'posto_ai',
schemas isolados 'aura_core' e 'n3_sre', indices HNSW e interoperabilidade
entre AURA e Sentinel.
Zero travessoes em todo o arquivo.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from config.settings import (
    AURA_CORE_SCHEMA,
    DB_VECTOR_CONFIG,
    N3_SRE_SCHEMA,
    VECTOR_DB_DRIVER_OPTIONS,
)
from scripts.init_posto_database import (
    apply_schema_migrations,
    ensure_backwards_compatibility_views,
    get_convergence_ddl,
    parse_args,
)


def test_config_settings_pgvector_convergence():
    """Valida configuracoes padronizadas do banco posto_ai na porta 5433."""
    assert DB_VECTOR_CONFIG["port"] == 5433
    assert DB_VECTOR_CONFIG["dbname"] == "posto_ai"
    assert "options" in DB_VECTOR_CONFIG
    assert "search_path=aura_core,public" in DB_VECTOR_CONFIG["options"]
    assert AURA_CORE_SCHEMA == "aura_core"
    assert N3_SRE_SCHEMA == "n3_sre"
    assert "aura_core" in VECTOR_DB_DRIVER_OPTIONS


def test_get_convergence_ddl_declarative():
    """Valida geracao declarativa do DDL com schemas isolados e indices HNSW."""
    ddl_all = get_convergence_ddl("all")
    assert "CREATE EXTENSION IF NOT EXISTS vector;" in ddl_all
    assert "CREATE SCHEMA IF NOT EXISTS aura_core;" in ddl_all
    assert "CREATE TABLE IF NOT EXISTS aura_core.intencoes_vetores" in ddl_all
    assert "CREATE TABLE IF NOT EXISTS aura_core.produtos_vetores" in ddl_all
    assert "CREATE TABLE IF NOT EXISTS aura_core.aura_conhecimento_vetores" in ddl_all
    assert "idx_aura_core_intencoes_vetores_hnsw" in ddl_all
    assert "idx_aura_core_produtos_vetores_hnsw" in ddl_all
    assert "halfvec_cosine_ops" in ddl_all

    assert "CREATE SCHEMA IF NOT EXISTS n3_sre;" in ddl_all
    assert "CREATE TABLE IF NOT EXISTS n3_sre.knowledge_base" in ddl_all
    assert "CREATE TABLE IF NOT EXISTS n3_sre.incident_fingerprints" in ddl_all
    assert "CREATE TABLE IF NOT EXISTS n3_sre.sre_runbooks" in ddl_all
    assert "idx_n3_edge_kb_hnsw" in ddl_all
    assert "idx_n3_sre_runbooks_hnsw" in ddl_all


def test_get_convergence_ddl_filtering():
    """Valida filtragem por schema alvo no gerador DDL."""
    ddl_aura = get_convergence_ddl("aura_core")
    assert "aura_core" in ddl_aura
    assert "n3_sre" not in ddl_aura

    ddl_sre = get_convergence_ddl("n3_sre")
    assert "n3_sre" in ddl_sre
    assert "aura_core" not in ddl_sre


def test_init_posto_database_args():
    """Valida argumentos CLI padronizados para o provisionador do posto_ai."""
    with patch("sys.argv", ["init_posto_database.py"]):
        args = parse_args()
        assert args.port == 5433
        assert args.dbname == "posto_ai"
        assert args.schema == "all"

    with patch("sys.argv", ["init_posto_database.py", "--port", "5433", "--schema", "aura_core"]):
        args = parse_args()
        assert args.port == 5433
        assert args.schema == "aura_core"


def test_apply_schema_migrations_mocked():
    """Valida execucao orquestrada das migracoes com mock de conexao."""
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value = mock_cur
    mock_cur.fetchone.side_effect = [
        None,  # intencoes_vetores view check
        None,  # produtos_vetores view check
        None,  # perguntas_cache view check
        None,  # aura_conhecimento_vetores view check
        (10,),  # count(*) em intencoes_vetores (ja populada)
    ]

    with patch("psycopg2.connect", return_value=mock_conn):
        apply_schema_migrations(
            host="127.0.0.1",
            port=5433,
            user="postgres",
            password="",
            dbname="posto_ai",
            target_schema="all",
        )

    # Verifica que comandos de extensao e DDL foram enviados
    executed_statements = [call_args[0][0] for call_args in mock_cur.execute.call_args_list]
    assert any("CREATE EXTENSION IF NOT EXISTS vector;" in stmt for stmt in executed_statements)
    assert any("CREATE SCHEMA IF NOT EXISTS aura_core;" in stmt for stmt in executed_statements)
    assert any("CREATE SCHEMA IF NOT EXISTS n3_sre;" in stmt for stmt in executed_statements)


def test_ensure_backwards_compatibility_views():
    """Valida criacao de views retrocompativeis quando tabelas em public nao existem."""
    mock_cur = MagicMock()
    # Simula que as tabelas nao existem em public (fetchone retorna None para cada)
    mock_cur.fetchone.return_value = None

    ensure_backwards_compatibility_views(mock_cur)

    executed = [c[0][0] for c in mock_cur.execute.call_args_list]
    assert any("CREATE OR REPLACE VIEW public.intencoes_vetores AS SELECT * FROM aura_core.intencoes_vetores;" in sql for sql in executed)
    assert any("CREATE OR REPLACE VIEW public.produtos_vetores AS SELECT * FROM aura_core.produtos_vetores;" in sql for sql in executed)


def test_sentinel_n3_agent_toml_convergence():
    """Valida que a configuracao do Sentinel n3-agent.toml aponta para a porta 5433 e posto_ai."""
    sentinel_toml_path = Path.home() / "Documents" / "RAG WP" / "src" / "station_agent" / "n3-agent.toml"
    if sentinel_toml_path.exists():
        content = sentinel_toml_path.read_text(encoding="utf-8")
        assert "[vector_db]" in content
        assert "port = 5433" in content
        assert 'dbname = "posto_ai"' in content


def test_sentinel_edge_storage_default_port():
    """Valida que o modulo EdgeVectorStorage do Sentinel tem default na porta 5433."""
    sentinel_storage_path = Path.home() / "Documents" / "RAG WP" / "src" / "station_agent" / "edge_storage.py"
    if sentinel_storage_path.exists():
        content = sentinel_storage_path.read_text(encoding="utf-8")
        assert 'cfg.get("port", 5433)' in content


def test_zero_dashes_enforcement_fase7():
    """Garante ausencia inegociavel de travessoes nos arquivos da Fase 7."""
    files_to_check = [
        Path("config/settings.py"),
        Path("core/db_pool.py"),
        Path("scripts/init_posto_database.py"),
        Path(__file__),
    ]
    for file_path in files_to_check:
        if file_path.exists():
            text = file_path.read_text(encoding="utf-8")
            assert "\u2014" not in text, f"Travessao em dash encontrado em {file_path}"
            assert "\u2013" not in text, f"Travessao en dash encontrado em {file_path}"
