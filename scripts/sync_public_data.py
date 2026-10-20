"""
Sincronizador em Segundo Plano de Dados Abertos Governamentais (Fase 3 - Pilar 4).
Orquestra conectores da ANP, CONFAZ e BACEN SGS com persistencia em cache relacional local.
Executa em lote, daemon ou cron com footprint de memoria inferior a 80 MB e protecao por Circuit Breaker.
Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

# Garante inclusao do diretorio raiz no PYTHONPATH
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.integrations.public_data import (
    AnpPublicDataConnector,
    BacenSgsConnector,
    ConfazPmpfConnector,
    PublicDataRepository,
    get_public_data_repository,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
)
logger = logging.getLogger("AuraPublicDataSync")

# Payloads deterministicos em memoria para modo mock
MOCK_CSV_ANP = (
    "Região - Sigla;Estado - Sigla;Município;Revenda;CNPJ da Revenda;Produto;Data da Coleta;Valor de Venda;Bandeira;Unidade de Medida\n"
    "SE;SP;SAO PAULO;AUTO POSTO PINHEIROS LTDA;01.234.567/0001-89;GASOLINA COMUM;15/10/2026;5.79;BRANCA;R$ / litro\n"
    "SE;SP;SAO PAULO;POSTO BANDEIRANTES EXPRESS;02.345.678/0001-90;GASOLINA COMUM;15/10/2026;5.89;IPIRANGA;R$ / litro\n"
    "SE;SP;SAO PAULO;POSTO AVENIDA PAULISTA;03.456.789/0001-01;GASOLINA COMUM;15/10/2026;5.69;VIBRA;R$ / litro\n"
    "SE;SP;SAO PAULO;AUTO POSTO CIDADE JARDIM;04.567.890/0001-12;GASOLINA COMUM;15/10/2026;5.99;SHELL;R$ / litro\n"
    "SE;SP;SAO PAULO;POSTO MARGINAL TIETE;05.678.901/0001-23;GASOLINA COMUM;15/10/2026;5.59;BRANCA;R$ / litro\n"
    "SE;SP;SAO PAULO;AUTO POSTO PINHEIROS LTDA;01.234.567/0001-89;ETANOL HIDRATADO;15/10/2026;3.89;BRANCA;R$ / litro\n"
    "SE;SP;SAO PAULO;POSTO BANDEIRANTES EXPRESS;02.345.678/0001-90;ETANOL HIDRATADO;15/10/2026;3.99;IPIRANGA;R$ / litro\n"
    "SE;SP;SAO PAULO;POSTO BANDEIRANTES EXPRESS;02.345.678/0001-90;DIESEL S10;15/10/2026;5.95;IPIRANGA;R$ / litro\n"
).encode()

MOCK_TEXT_CONFAZ = (
    b"ESTADO;GASOLINA COMUM;GASOLINA ADITIVADA;ETANOL;DIESEL S10;DIESEL S500;GLP\n"
    b"SP;5.89;6.09;3.99;5.95;5.80;8.50\n"
    b"RJ;5.99;6.19;4.19;6.05;5.90;8.60\n"
    b"MG;5.92;6.12;4.05;5.98;5.85;8.55\n"
    b"PR;5.85;6.05;3.95;5.90;5.75;8.45\n"
)

MOCK_JSON_BACEN_SELIC = b'[{"data": "15/10/2026", "valor": "10.75"}]'
MOCK_JSON_BACEN_PTAX = b'[{"data": "15/10/2026", "valor": "5.4520"}]'
MOCK_JSON_BACEN_IPCA = b'[{"data": "01/10/2026", "valor": "0.44"}]'

_default_anp_connector: AnpPublicDataConnector | None = None
_default_confaz_connector: ConfazPmpfConnector | None = None
_default_bacen_connector: BacenSgsConnector | None = None


def get_default_connectors() -> tuple[AnpPublicDataConnector, ConfazPmpfConnector, BacenSgsConnector]:
    """Retorna conectores reutilizaveis para preservar estado do Circuit Breaker."""
    global _default_anp_connector, _default_confaz_connector, _default_bacen_connector
    if _default_anp_connector is None:
        _default_anp_connector = AnpPublicDataConnector()
    if _default_confaz_connector is None:
        _default_confaz_connector = ConfazPmpfConnector()
    if _default_bacen_connector is None:
        _default_bacen_connector = BacenSgsConnector()
    return _default_anp_connector, _default_confaz_connector, _default_bacen_connector


def sync_anp_data(
    repo: PublicDataRepository,
    municipio: str | None = None,
    uf: str | None = None,
    mock: bool = False,
    connector: AnpPublicDataConnector | None = None,
) -> dict[str, Any]:
    """Sincroniza precos semanais de combustiveis da ANP."""
    t0 = time.perf_counter()
    con = connector or get_default_connectors()[0]
    fonte = con.source_name
    mock_payload = MOCK_CSV_ANP if mock else None

    try:
        res = con.fetch_precos_semanais(
            filtro_municipio=municipio,
            filtro_uf=uf,
            mock_payload=mock_payload,
        )

        if not res.success:
            duracao = (time.perf_counter() - t0) * 1000.0
            repo.record_sync_telemetry(
                fonte=fonte,
                status="ERRO",
                processados=0,
                inseridos=0,
                duracao_ms=duracao,
                erro=res.error_message or "Falha desconhecida na coleta ANP",
            )
            return {"source": "anp", "success": False, "records": 0, "error": res.error_message}

        inseridos = repo.save_anp_precos_batch(res.data)
        duracao = (time.perf_counter() - t0) * 1000.0

        repo.record_sync_telemetry(
            fonte=fonte,
            status="SUCESSO",
            processados=res.records_count,
            inseridos=inseridos,
            duracao_ms=duracao,
        )
        logger.info("ANP: %d registros processados, %d inseridos em %.2f ms.", res.records_count, inseridos, duracao)
        return {"source": "anp", "success": True, "records": inseridos, "duracao_ms": duracao}

    except Exception as exc:
        duracao = (time.perf_counter() - t0) * 1000.0
        logger.exception("Erro durante sincronizacao ANP")
        repo.record_sync_telemetry(
            fonte=fonte,
            status="ERRO",
            processados=0,
            inseridos=0,
            duracao_ms=duracao,
            erro=str(exc),
        )
        return {"source": "anp", "success": False, "records": 0, "error": str(exc)}


def sync_confaz_data(
    repo: PublicDataRepository,
    uf: str | None = None,
    mock: bool = False,
    connector: ConfazPmpfConnector | None = None,
) -> dict[str, Any]:
    """Sincroniza pautas fiscais de PMPF do CONFAZ / Atos COTEPE."""
    t0 = time.perf_counter()
    con = connector or get_default_connectors()[1]
    fonte = con.source_name
    mock_payload = MOCK_TEXT_CONFAZ if mock else None

    try:
        res = con.fetch_pmpf_atual(
            filtro_uf=uf,
            mock_payload=mock_payload,
        )

        if not res.success:
            duracao = (time.perf_counter() - t0) * 1000.0
            repo.record_sync_telemetry(
                fonte=fonte,
                status="ERRO",
                processados=0,
                inseridos=0,
                duracao_ms=duracao,
                erro=res.error_message or "Falha desconhecida na coleta CONFAZ",
            )
            return {"source": "confaz", "success": False, "records": 0, "error": res.error_message}

        inseridos = repo.save_confaz_pmpf_batch(res.data)
        duracao = (time.perf_counter() - t0) * 1000.0

        repo.record_sync_telemetry(
            fonte=fonte,
            status="SUCESSO",
            processados=res.records_count,
            inseridos=inseridos,
            duracao_ms=duracao,
        )
        logger.info("CONFAZ: %d UFs processadas, %d pautas inseridas em %.2f ms.", res.records_count, inseridos, duracao)
        return {"source": "confaz", "success": True, "records": inseridos, "duracao_ms": duracao}

    except Exception as exc:
        duracao = (time.perf_counter() - t0) * 1000.0
        logger.exception("Erro durante sincronizacao CONFAZ")
        repo.record_sync_telemetry(
            fonte=fonte,
            status="ERRO",
            processados=0,
            inseridos=0,
            duracao_ms=duracao,
            erro=str(exc),
        )
        return {"source": "confaz", "success": False, "records": 0, "error": str(exc)}


def sync_bacen_data(
    repo: PublicDataRepository,
    mock: bool = False,
    connector: BacenSgsConnector | None = None,
) -> dict[str, Any]:
    """Sincroniza series temporais macroeconomicas do BACEN SGS."""
    t0 = time.perf_counter()
    con = connector or get_default_connectors()[2]
    fonte = con.source_name

    mock_dict = (
        {
            11: MOCK_JSON_BACEN_SELIC,
            10813: MOCK_JSON_BACEN_PTAX,
            433: MOCK_JSON_BACEN_IPCA,
        }
        if mock
        else None
    )

    try:
        # Coleta das tres series canonicas
        records: list[dict[str, Any]] = []
        series_codigos = [con.SERIE_SELIC_DIARIA, con.SERIE_PTAX_DOLAR_VENDA, con.SERIE_IPCA_MENSAL]

        for cod in series_codigos:
            p = mock_dict.get(cod) if mock_dict else None
            res = con.fetch_serie(codigo_serie=cod, mock_payload=p)
            if res.success and res.data:
                records.extend(res.data)

        if not records:
            duracao = (time.perf_counter() - t0) * 1000.0
            repo.record_sync_telemetry(
                fonte=fonte,
                status="ERRO",
                processados=0,
                inseridos=0,
                duracao_ms=duracao,
                erro="Nenhuma serie BACEN retornou dados validos",
            )
            return {"source": "bacen", "success": False, "records": 0, "error": "Sem dados"}

        inseridos = repo.save_bacen_series_batch(records)
        duracao = (time.perf_counter() - t0) * 1000.0

        repo.record_sync_telemetry(
            fonte=fonte,
            status="SUCESSO",
            processados=len(records),
            inseridos=inseridos,
            duracao_ms=duracao,
        )
        logger.info("BACEN: %d pontos processados, %d inseridos em %.2f ms.", len(records), inseridos, duracao)
        return {"source": "bacen", "success": True, "records": inseridos, "duracao_ms": duracao}

    except Exception as exc:
        duracao = (time.perf_counter() - t0) * 1000.0
        logger.exception("Erro durante sincronizacao BACEN")
        repo.record_sync_telemetry(
            fonte=fonte,
            status="ERRO",
            processados=0,
            inseridos=0,
            duracao_ms=duracao,
            erro=str(exc),
        )
        return {"source": "bacen", "success": False, "records": 0, "error": str(exc)}


def sync_public_data(
    source: str = "all",
    municipio: str | None = None,
    uf: str | None = None,
    mock: bool = False,
    repository: PublicDataRepository | None = None,
    anp_connector: AnpPublicDataConnector | None = None,
    confaz_connector: ConfazPmpfConnector | None = None,
    bacen_connector: BacenSgsConnector | None = None,
) -> dict[str, Any]:
    """
    Funcao principal de sincronizacao de dados publicos da AURA.
    Pode ser invocada via CLI ou importada por modulos e daemons de retaguarda.
    """
    repo = repository or get_public_data_repository()
    src = source.strip().lower()

    effective_mun = municipio or os.getenv("POSTO_MUNICIPIO", "SAO PAULO")
    effective_uf = uf or os.getenv("POSTO_UF", "SP")

    results: dict[str, Any] = {
        "timestamp": time.time(),
        "source": src,
        "mock": mock,
        "sources_executed": {},
    }

    if src in ("anp", "all"):
        results["sources_executed"]["anp"] = sync_anp_data(
            repo, municipio=effective_mun, uf=effective_uf, mock=mock, connector=anp_connector
        )

    if src in ("confaz", "all"):
        results["sources_executed"]["confaz"] = sync_confaz_data(
            repo, uf=effective_uf, mock=mock, connector=confaz_connector
        )

    if src in ("bacen", "all"):
        results["sources_executed"]["bacen"] = sync_bacen_data(
            repo, mock=mock, connector=bacen_connector
        )

    return results


def run_sync_loop(
    source: str = "all",
    municipio: str | None = None,
    uf: str | None = None,
    mock: bool = False,
    interval_hours: float = 24.0,
    once: bool = False,
    force_sqlite: bool = False,
) -> None:
    """Loop de execucao para worker continuo de segundo plano."""
    repo = get_public_data_repository(force_sqlite=force_sqlite)
    anp_con, confaz_con, bacen_con = get_default_connectors()
    logger.info(
        "Iniciando Aura Public Data Sync Worker (source=%s, interval=%.1fh, once=%s, mock=%s).",
        source,
        interval_hours,
        once,
        mock,
    )

    interval_sec = max(60.0, float(interval_hours) * 3600.0)

    while True:
        try:
            logger.info("Disparando rodada de sincronizacao de dados governamentais...")
            sync_public_data(
                source=source,
                municipio=municipio,
                uf=uf,
                mock=mock,
                repository=repo,
                anp_connector=anp_con,
                confaz_connector=confaz_con,
                bacen_connector=bacen_con,
            )
        except Exception:
            logger.exception("Erro fatal no ciclo de sincronizacao")

        if once:
            logger.info("Execucao unica concluida (--once). Encerrando processo.")
            break

        logger.info("Aguardando proximo ciclo em %.1f horas...", interval_hours)
        time.sleep(interval_sec)


def main() -> None:
    """Ponto de entrada da linha de comando (CLI)."""
    parser = argparse.ArgumentParser(
        description="AURA Public Data Sync Worker - Sincronizacao de dados publicos da ANP, CONFAZ e BACEN."
    )
    parser.add_argument(
        "--source",
        choices=["anp", "confaz", "bacen", "all"],
        default="all",
        help="Fonte de dados a sincronizar (padrao: all)",
    )
    parser.add_argument(
        "--municipio",
        default=None,
        help="Municipio alvo para filtragem de precos ANP",
    )
    parser.add_argument(
        "--uf",
        default=None,
        help="Sigla da UF alvo (ex: SP, RJ, MG)",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Executa em modo de simulacao hermetica com payloads locais sem requisicoes de rede",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Executa uma unica vez e encerra (ideal para cron e pipelines CI)",
    )
    parser.add_argument(
        "--interval-hours",
        type=float,
        default=24.0,
        help="Intervalo de horas entre sincronizacoes quando rodando como daemon",
    )
    parser.add_argument(
        "--sqlite",
        action="store_true",
        help="Forca uso de fallback SQLite em memoria em vez do PostgreSQL local",
    )

    args = parser.parse_args()

    run_sync_loop(
        source=args.source,
        municipio=args.municipio,
        uf=args.uf,
        mock=args.mock,
        interval_hours=args.interval_hours,
        once=args.once,
        force_sqlite=args.sqlite,
    )


if __name__ == "__main__":
    main()
