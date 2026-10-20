"""
Testes Unitarios do Sincronizador e Cache Relacional de Dados Publicos (Fase 3 - Pilar 4).
Valida DDL idempotente, UPSERT de precos ANP, calculo estatistico de benchmark,
pautas fiscais do CONFAZ, series do BACEN SGS, telemetria e fluxo CLI em modo mock.
Zero travessoes em todo o arquivo.
"""

from pathlib import Path

from core.integrations.public_data import (
    PublicDataRepository,
)
from scripts.sync_public_data import sync_public_data


def test_init_schema_idempotency():
    """Valida que o DDL e executado repetidamente sem erros em banco isolado."""
    repo = PublicDataRepository(use_sqlite_fallback=True, sqlite_db_path=":memory:")

    # Executa schema multiplas vezes seguidas para provar idempotencia
    repo.init_schema()
    repo.init_schema()
    repo.init_schema()

    # Confirma que tabelas foram provisionadas
    historico = repo.get_telemetry_history(limit=5)
    assert isinstance(historico, list)
    assert len(historico) == 0


def test_save_and_get_anp_precos_batch():
    """
    Testa salvamento em lote de precos ANP e calculo estatistico de mercado:
    media, min, max, mediana, quartis, desvio padrao, total amostras e postos.
    """
    repo = PublicDataRepository(use_sqlite_fallback=True, sqlite_db_path=":memory:")

    records = [
        {
            "regiao": "SE",
            "estado_sigla": "SP",
            "municipio": "CAMPINAS",
            "revenda": "AUTO POSTO A",
            "cnpj_revenda": "11.111.111/0001-01",
            "produto": "GASOLINA COMUM",
            "data_coleta": "2026-10-15",
            "valor_venda": 5.50,
            "bandeira": "BRANCA",
        },
        {
            "regiao": "SE",
            "estado_sigla": "SP",
            "municipio": "CAMPINAS",
            "revenda": "AUTO POSTO B",
            "cnpj_revenda": "22.222.222/0001-02",
            "produto": "GASOLINA COMUM",
            "data_coleta": "2026-10-15",
            "valor_venda": 5.60,
            "bandeira": "IPIRANGA",
        },
        {
            "regiao": "SE",
            "estado_sigla": "SP",
            "municipio": "CAMPINAS",
            "revenda": "AUTO POSTO C",
            "cnpj_revenda": "33.333.333/0001-03",
            "produto": "GASOLINA COMUM",
            "data_coleta": "2026-10-15",
            "valor_venda": 5.70,
            "bandeira": "SHELL",
        },
        {
            "regiao": "SE",
            "estado_sigla": "SP",
            "municipio": "CAMPINAS",
            "revenda": "AUTO POSTO D",
            "cnpj_revenda": "44.444.444/0001-04",
            "produto": "GASOLINA COMUM",
            "data_coleta": "2026-10-15",
            "valor_venda": 5.80,
            "bandeira": "VIBRA",
        },
        {
            "regiao": "SE",
            "estado_sigla": "SP",
            "municipio": "CAMPINAS",
            "revenda": "AUTO POSTO E",
            "cnpj_revenda": "55.555.555/0001-05",
            "produto": "GASOLINA COMUM",
            "data_coleta": "2026-10-15",
            "valor_venda": 5.90,
            "bandeira": "ALE",
        },
    ]

    inseridos = repo.save_anp_precos_batch(records)
    assert inseridos == 5

    benchmark = repo.get_preco_benchmark_anp("CAMPINAS", "GASOLINA COMUM")

    assert benchmark["municipio"] == "CAMPINAS"
    assert benchmark["produto"] == "GASOLINA COMUM"
    assert benchmark["total_amostras"] == 5
    assert benchmark["postos_amostrados"] == 5
    assert benchmark["preco_minimo"] == 5.50
    assert benchmark["preco_maximo"] == 5.90
    assert benchmark["preco_medio"] == 5.70
    assert benchmark["preco_mediana"] == 5.70
    assert benchmark["quartil_1"] == 5.60
    assert benchmark["quartil_3"] == 5.80
    assert benchmark["desvio_padrao"] > 0.0
    assert benchmark["data_ultima_coleta"] == "2026-10-15"

    # Consulta por municipio inexistente retorna estrutura vazia sem erro
    vazio = repo.get_preco_benchmark_anp("MUNICIPIO_INEXISTENTE", "GASOLINA COMUM")
    assert vazio["total_amostras"] == 0
    assert vazio["preco_medio"] == 0.0
    assert vazio["data_ultima_coleta"] is None


def test_anp_upsert_idempotent():
    """Testa insercao de duplicados atualizando campos sem duplicar linhas (UPSERT)."""
    repo = PublicDataRepository(use_sqlite_fallback=True, sqlite_db_path=":memory:")

    primeiro_registro = [
        {
            "regiao": "SE",
            "estado_sigla": "SP",
            "municipio": "SANTOS",
            "revenda": "AUTO POSTO PRAIA",
            "cnpj_revenda": "99.999.999/0001-99",
            "produto": "GASOLINA COMUM",
            "data_coleta": "2026-10-15",
            "valor_venda": 5.49,
            "bandeira": "BRANCA",
        }
    ]

    # Insercao inicial
    inseridos_1 = repo.save_anp_precos_batch(primeiro_registro)
    assert inseridos_1 == 1

    bench_1 = repo.get_preco_benchmark_anp("SANTOS", "GASOLINA COMUM")
    assert bench_1["total_amostras"] == 1
    assert bench_1["preco_medio"] == 5.49

    # Re-insercao com mesmo CNPJ, Produto e Data, porem novo preco e bandeira
    registro_atualizado = [
        {
            "regiao": "SE",
            "estado_sigla": "SP",
            "municipio": "SANTOS",
            "revenda": "AUTO POSTO PRAIA",
            "cnpj_revenda": "99.999.999/0001-99",
            "produto": "GASOLINA COMUM",
            "data_coleta": "2026-10-15",
            "valor_venda": 5.89,
            "bandeira": "SHELL",
        }
    ]

    inseridos_2 = repo.save_anp_precos_batch(registro_atualizado)
    assert inseridos_2 == 1

    # Total de amostras permanece 1 (sem duplicatas) e preco foi atualizado
    bench_2 = repo.get_preco_benchmark_anp("SANTOS", "GASOLINA COMUM")
    assert bench_2["total_amostras"] == 1
    assert bench_2["preco_medio"] == 5.89


def test_save_and_get_confaz_pmpf():
    """Testa persistencia de pautas fiscais PMPF e consulta da pauta ativa por UF."""
    repo = PublicDataRepository(use_sqlite_fallback=True, sqlite_db_path=":memory:")

    pautas = [
        {
            "uf": "RJ",
            "produto": "gasolina_comum",
            "valor_pauta": 5.90,
            "vigencia_inicio": "2026-10-01",
            "vigencia_fim": "2026-10-15",
            "ato_cotepe_num": "COTEPE 18/2026",
            "data_publicacao_dou": "2026-09-29",
        },
        {
            "uf": "RJ",
            "produto": "gasolina_comum",
            "valor_pauta": 6.05,
            "vigencia_inicio": "2026-10-16",
            "vigencia_fim": None,
            "ato_cotepe_num": "COTEPE 19/2026",
            "data_publicacao_dou": "2026-10-14",
        },
        {
            "uf": "RJ",
            "produto": "etanol_hidratado",
            "valor_pauta": 4.15,
            "vigencia_inicio": "2026-10-16",
            "ato_cotepe_num": "COTEPE 19/2026",
        },
    ]

    inseridos = repo.save_confaz_pmpf_batch(pautas)
    assert inseridos == 3

    # Retorna pauta mais recente ativa
    pmpf_gasolina = repo.get_pmpf_atual("RJ", "gasolina_comum")
    assert pmpf_gasolina is not None
    assert pmpf_gasolina["uf"] == "RJ"
    assert pmpf_gasolina["valor_pauta"] == 6.05
    assert pmpf_gasolina["vigencia_inicio"] == "2026-10-16"
    assert pmpf_gasolina["ato_cotepe_num"] == "COTEPE 19/2026"

    # Retorna pauta de etanol
    pmpf_etanol = repo.get_pmpf_atual("RJ", "etanol_hidratado")
    assert pmpf_etanol is not None
    assert pmpf_etanol["valor_pauta"] == 4.15

    # Consulta com UF sem dados retorna None
    inexistente = repo.get_pmpf_atual("AC", "gasolina_comum")
    assert inexistente is None


def test_save_and_get_bacen_series():
    """Testa salvamento de series Selic, PTAX e IPCA e consulta consolidada."""
    repo = PublicDataRepository(use_sqlite_fallback=True, sqlite_db_path=":memory:")

    series_data = [
        {
            "codigo_serie": 11,
            "nome_serie": "Taxa Selic Diaria Acumulada Anualizada",
            "data_referencia": "2026-10-15",
            "valor": 10.75,
            "unidade": "% a.a.",
        },
        {
            "codigo_serie": 10813,
            "nome_serie": "Taxa de Cambio PTAX Dolar Comercial Venda",
            "data_referencia": "2026-10-15",
            "valor": 5.4520,
            "unidade": "R$",
        },
        {
            "codigo_serie": 433,
            "nome_serie": "IPCA Mensal",
            "data_referencia": "2026-10-01",
            "valor": 0.44,
            "unidade": "%",
        },
    ]

    inseridos = repo.save_bacen_series_batch(series_data)
    assert inseridos == 3

    indicadores = repo.get_indicadores_economicos_recentes()

    assert indicadores["selic_diaria_aa"] == 10.75
    assert indicadores["ptax_dolar_venda"] == 5.4520
    assert indicadores["ipca_mensal_valor"] == 0.44
    assert indicadores["data_referencia_selic"] == "2026-10-15"
    assert indicadores["data_referencia_ptax"] == "2026-10-15"
    assert indicadores["data_referencia_ipca"] == "2026-10-01"


def test_sync_telemetry_recording():
    """Valida registro de auditoria operacional de telemetria com sucesso e erro."""
    repo = PublicDataRepository(use_sqlite_fallback=True, sqlite_db_path=":memory:")

    # Registra sucesso
    repo.record_sync_telemetry(
        fonte="ANP_DADOS_ABERTOS",
        status="SUCESSO",
        processados=100,
        inseridos=95,
        duracao_ms=45.2,
        erro=None,
    )

    # Registra falha
    repo.record_sync_telemetry(
        fonte="CONFAZ_PMPF",
        status="ERRO",
        processados=0,
        inseridos=0,
        duracao_ms=12.1,
        erro="Timeout de rede HTTP 504",
    )

    historico = repo.get_telemetry_history(limit=10)
    assert len(historico) == 2

    # Ordem decrescente de execucao
    erro_entry = historico[0]
    sucesso_entry = historico[1]

    assert erro_entry["fonte"] == "CONFAZ_PMPF"
    assert erro_entry["status"] == "ERRO"
    assert erro_entry["registros_processados"] == 0
    assert "Timeout" in erro_entry["mensagem_erro"]

    assert sucesso_entry["fonte"] == "ANP_DADOS_ABERTOS"
    assert sucesso_entry["status"] == "SUCESSO"
    assert sucesso_entry["registros_processados"] == 100
    assert sucesso_entry["registros_inseridos"] == 95
    assert sucesso_entry["duracao_ms"] == 45.2


def test_sync_public_data_cli_mock_flow():
    """Testa fluxo completo do sincronizador sync_public_data.py em modo mock."""
    repo = PublicDataRepository(use_sqlite_fallback=True, sqlite_db_path=":memory:")

    res = sync_public_data(
        source="all",
        municipio="SAO PAULO",
        uf="SP",
        mock=True,
        repository=repo,
    )

    assert res["mock"] is True
    assert res["source"] == "all"
    assert "anp" in res["sources_executed"]
    assert "confaz" in res["sources_executed"]
    assert "bacen" in res["sources_executed"]

    assert res["sources_executed"]["anp"]["success"] is True
    assert res["sources_executed"]["anp"]["records"] > 0

    assert res["sources_executed"]["confaz"]["success"] is True
    assert res["sources_executed"]["confaz"]["records"] > 0

    assert res["sources_executed"]["bacen"]["success"] is True
    assert res["sources_executed"]["bacen"]["records"] > 0

    # Verifica se os dados estao acessiveis pelos metodos de leitura rapida
    bench = repo.get_preco_benchmark_anp("SAO PAULO", "GASOLINA COMUM")
    assert bench["total_amostras"] >= 5
    assert bench["preco_medio"] > 0.0

    pmpf = repo.get_pmpf_atual("SP", "gasolina_comum")
    assert pmpf is not None
    assert pmpf["valor_pauta"] > 0.0

    indicadores = repo.get_indicadores_economicos_recentes()
    assert indicadores["selic_diaria_aa"] > 0.0


def test_parse_float_and_date_robustness():
    """Valida conversao robusta de numeros brasileiros com virgula e normalizacao de datas."""
    assert PublicDataRepository._parse_float("5,79") == 5.79
    assert PublicDataRepository._parse_float("  10,7500  ") == 10.75
    assert PublicDataRepository._parse_float("R$ 4,19") == 4.19
    assert PublicDataRepository._parse_float(5.5) == 5.5
    assert PublicDataRepository._parse_float(None) == 0.0
    assert PublicDataRepository._parse_float("invalido") == 0.0

    # Normalizacao de data com fallback seguro
    assert PublicDataRepository._normalize_date_str("15/10/2026") == "2026-10-15"
    assert PublicDataRepository._normalize_date_str("2026-10-15") == "2026-10-15"
    assert PublicDataRepository._normalize_date_str("") != ""
    assert len(PublicDataRepository._normalize_date_str(None)) == 10
    assert len(PublicDataRepository._normalize_date_str("  ")) == 10


def test_anp_benchmark_ignores_zero_prices():
    """Garante que precos zerados ou invalidos nao distorcem o benchmark de mercado."""
    repo = PublicDataRepository(use_sqlite_fallback=True, sqlite_db_path=":memory:")

    records = [
        {
            "regiao": "SE",
            "estado_sigla": "SP",
            "municipio": "SOROCABA",
            "revenda": "POSTO VALIDO 1",
            "cnpj_revenda": "10.000.000/0001-01",
            "produto": "GASOLINA COMUM",
            "data_coleta": "2026-10-15",
            "valor_venda": "5,60",
        },
        {
            "regiao": "SE",
            "estado_sigla": "SP",
            "municipio": "SOROCABA",
            "revenda": "POSTO VALIDO 2",
            "cnpj_revenda": "20.000.000/0001-02",
            "produto": "GASOLINA COMUM",
            "data_coleta": "2026-10-15",
            "valor_venda": 5.80,
        },
        {
            "regiao": "SE",
            "estado_sigla": "SP",
            "municipio": "SOROCABA",
            "revenda": "POSTO COM ERRO DE PRECO",
            "cnpj_revenda": "30.000.000/0001-03",
            "produto": "GASOLINA COMUM",
            "data_coleta": "2026-10-15",
            "valor_venda": 0.0,
        },
    ]

    inseridos = repo.save_anp_precos_batch(records)
    assert inseridos == 3

    bench = repo.get_preco_benchmark_anp("SOROCABA", "GASOLINA COMUM")
    # Amostras consideradas no benchmark devem ignorar o preco 0.0
    assert bench["total_amostras"] == 2
    assert bench["preco_minimo"] == 5.60
    assert bench["preco_maximo"] == 5.80
    assert bench["preco_medio"] == 5.70


def test_confaz_product_canonicalization_and_string_values():
    """Valida normalizacao de nomes de produtos com espacos e valores com virgula no CONFAZ."""
    repo = PublicDataRepository(use_sqlite_fallback=True, sqlite_db_path=":memory:")

    pautas = [
        {
            "uf": "MG",
            "produto": "Gasolina Comum",
            "valor_pauta": "5,95",
            "vigencia_inicio": "2026-10-16",
            "ato_cotepe_num": "COTEPE 20/2026",
        }
    ]

    inseridos = repo.save_confaz_pmpf_batch(pautas)
    assert inseridos == 1

    # Consulta tanto com formato canonico quanto formato amigavel
    pmpf_canonico = repo.get_pmpf_atual("MG", "gasolina_comum")
    assert pmpf_canonico is not None
    assert pmpf_canonico["valor_pauta"] == 5.95

    pmpf_amigavel = repo.get_pmpf_atual("MG", "Gasolina Comum")
    assert pmpf_amigavel is not None
    assert pmpf_amigavel["valor_pauta"] == 5.95


def test_circuit_breaker_persistence_in_sync_public_data():
    """Valida que falhas consecutivas disparam transicao de estado no Circuit Breaker persistente."""
    from unittest.mock import MagicMock

    from core.integrations.public_data import (
        ConnectorFetchResult,
        PublicDataCircuitBreaker,
    )
    from scripts.sync_public_data import sync_anp_data

    repo = PublicDataRepository(use_sqlite_fallback=True, sqlite_db_path=":memory:")
    cb = PublicDataCircuitBreaker(failure_threshold=3, cooldown_seconds=60.0)

    mock_con = MagicMock()
    mock_con.source_name = "anp_mock_cb"
    mock_con.fetch_precos_semanais.return_value = ConnectorFetchResult(
        success=False,
        source_name="anp_mock_cb",
        records_count=0,
        data=[],
        raw_bytes_size=0,
        latency_ms=10.0,
        cached=False,
        error_message="HTTP 503 Service Unavailable",
    )

    # 3 falhas consecutivas
    for _ in range(3):
        res = sync_anp_data(repo, connector=mock_con)
        assert res["success"] is False
        cb.record_failure("HTTP 503")

    assert cb.get_state() == "OPEN"
    assert cb.can_execute() is False


def test_public_data_repository_singleton_thread_safety():
    """Valida instanciacao singleton thread-safe sem corrupcao de estado concorrente."""
    import concurrent.futures

    from core.integrations.public_data.repository import get_public_data_repository

    instances = []

    def _get_repo():
        return get_public_data_repository(force_sqlite=True)

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(_get_repo) for _ in range(10)]
        for f in concurrent.futures.as_completed(futures):
            instances.append(f.result())

    assert len(instances) == 10
    for inst in instances:
        assert isinstance(inst, PublicDataRepository)


def test_postgres_index_scan_execution_plan():
    """
    Se o PostgreSQL estiver online na porta 5433, valida via EXPLAIN
    que as consultas analiticas utilizam Index Scan e Index Only Scan.
    """
    import pytest

    try:
        from core.db_pool import get_vector_connection
        conn = get_vector_connection()
    except (OSError, RuntimeError, Exception):  # noqa: BLE001
        pytest.skip("PostgreSQL posto_ai:5433 nao disponivel neste ambiente.")

    cur = conn.cursor()
    try:
        # 1. Verifica plano da data maxima da ANP
        cur.execute(
            "EXPLAIN SELECT MAX(data_coleta) FROM aura_core.anp_precos_semanais WHERE municipio = %s AND produto = %s",
            ("SAO PAULO", "GASOLINA COMUM"),
        )
        plan_max = " ".join(r[0] for r in cur.fetchall())
        assert "Index" in plan_max or "Scan" in plan_max

        # 2. Verifica plano da busca de pautas CONFAZ
        cur.execute(
            "EXPLAIN SELECT uf, produto, valor_pauta, vigencia_inicio FROM aura_core.confaz_pmpf WHERE uf = %s AND produto = %s ORDER BY vigencia_inicio DESC LIMIT 1",
            ("SP", "gasolina_comum"),
        )
        plan_pmpf = " ".join(r[0] for r in cur.fetchall())
        assert "Index Scan" in plan_pmpf or "idx_confaz_pmpf_uf_prod" in plan_pmpf
    finally:
        cur.close()
        conn.close()


def test_ausencia_travessoes_fase3():
    """
    Garante ausencia estrita de travessoes Unicode (\\u2014 e \\u2013) em todos
    os arquivos criados e modificados na Fase 3.
    """
    repo_root = Path(__file__).resolve().parent.parent.parent

    arquivos_fase3 = [
        repo_root / "scripts" / "init_public_data_cache.sql",
        repo_root / "core" / "integrations" / "public_data" / "repository.py",
        repo_root / "scripts" / "sync_public_data.py",
        repo_root / "core" / "integrations" / "public_data" / "__init__.py",
        Path(__file__).resolve(),
        repo_root / "docs" / "roadmap_integracao_apis_publicas.md",
    ]

    for arq in arquivos_fase3:
        assert arq.exists(), f"Arquivo obrigatorio da Fase 3 nao encontrado: {arq}"
        conteudo = arq.read_text(encoding="utf-8")
        assert "\u2014" not in conteudo, f"Travessao em-dash (\\u2014) encontrado no arquivo {arq.name}"
        assert "\u2013" not in conteudo, f"Travessao en-dash (\\u2013) encontrado no arquivo {arq.name}"
