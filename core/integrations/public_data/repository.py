"""
Repositorio de Cache Relacional Local para Dados Publicos Governamentais (Fase 3 - Pilar 4).
Persiste series da ANP, pautas do CONFAZ e indicadores do BACEN no schema aura_core (posto_ai:5433).
Suporta pool de conexao do PostgreSQL e fallback isolado em SQLite para operacao hermetica offline.
Zero travessoes em todo o modulo.
"""

from __future__ import annotations

import datetime
import logging
import sqlite3
import statistics
import threading
from collections.abc import Callable
from contextlib import contextmanager
from pathlib import Path
from typing import Any

logger = logging.getLogger("AuraPublicDataRepository")

# Mapa de nomes canonicos para series do BACEN
BACEN_SERIES_METADATA: dict[int, dict[str, str]] = {
    11: {"nome_serie": "Taxa Selic Diaria Acumulada Anualizada", "unidade": "% a.a."},
    432: {"nome_serie": "Meta Taxa Selic Definida pelo COPOM", "unidade": "% a.a."},
    10813: {"nome_serie": "Taxa de Cambio PTAX Dolar Comercial Venda", "unidade": "R$"},
    1: {"nome_serie": "Taxa de Cambio PTAX Dolar Comercial Venda", "unidade": "R$"},
    433: {"nome_serie": "Indice Nacional de Precos ao Consumidor Amplo (IPCA)", "unidade": "%"},
    189: {"nome_serie": "Indice Geral de Precos do Mercado (IGP-M)", "unidade": "%"},
}


class PublicDataRepository:
    """
    Repositorio relacional para dados publicos sincronizados.
    Garante consultas sub-50ms locais e persistencia idempotente via UPSERT.
    """

    def __init__(
        self,
        connection_provider: Callable[[], Any] | None = None,
        use_sqlite_fallback: bool = False,
        sqlite_db_path: str = ":memory:",
        auto_init: bool = True,
    ) -> None:
        self._lock = threading.RLock()
        self.use_sqlite = use_sqlite_fallback
        self.sqlite_db_path = sqlite_db_path
        self._sqlite_conn: sqlite3.Connection | None = None
        self._connection_provider = connection_provider

        if self.use_sqlite:
            self._init_sqlite()
        else:
            if self._connection_provider is None:
                try:
                    from core.db_pool import get_vector_connection
                    # Teste rapido de conectividade com PostgreSQL
                    test_conn = get_vector_connection()
                    test_conn.close()
                    self._connection_provider = get_vector_connection
                except (OSError, RuntimeError, Exception) as exc:  # noqa: BLE001
                    logger.warning(
                        "PostgreSQL posto_ai indisponivel (%s). Ativando fallback SQLite em memoria.",
                        exc,
                    )
                    self.use_sqlite = True
                    self._init_sqlite()

        if auto_init:
            self.init_schema()

    def _init_sqlite(self) -> None:
        """Inicializa conexao SQLite com schema aura_core acoplado."""
        self._sqlite_conn = sqlite3.connect(
            self.sqlite_db_path,
            check_same_thread=False,
            isolation_level=None,
        )
        self._sqlite_conn.row_factory = sqlite3.Row
        with self._lock:
            # Acopla aura_core em memoria para permitir sintaxe aura_core.tabela
            self._sqlite_conn.execute("ATTACH DATABASE ':memory:' AS aura_core;")

    @contextmanager
    def _get_connection(self):
        """Context manager que fornece conexao ativa com PostgreSQL ou SQLite."""
        if self.use_sqlite:
            with self._lock:
                yield self._sqlite_conn
        else:
            conn = self._connection_provider()
            try:
                yield conn
            finally:
                conn.close()

    def init_schema(self) -> None:
        """
        Executa DDL declarativo e idempotente para criacao das tabelas e indices.
        No PostgreSQL, executa scripts/init_public_data_cache.sql.
        No SQLite, executa schema compativel com o schema aura_core.
        """
        if self.use_sqlite:
            with self._get_connection() as conn:
                conn.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS aura_core.anp_precos_semanais (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        regiao TEXT,
                        estado_sigla TEXT NOT NULL,
                        municipio TEXT NOT NULL,
                        revenda TEXT,
                        cnpj_revenda TEXT,
                        produto TEXT NOT NULL,
                        data_coleta TEXT NOT NULL,
                        valor_venda REAL NOT NULL,
                        unidade_medida TEXT DEFAULT 'R$ / litro',
                        bandeira TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(cnpj_revenda, produto, data_coleta)
                    );
                    CREATE INDEX IF NOT EXISTS aura_core.idx_anp_precos_mun_prod
                    ON anp_precos_semanais (municipio, produto, data_coleta);
                    CREATE INDEX IF NOT EXISTS aura_core.idx_anp_precos_uf
                    ON anp_precos_semanais (estado_sigla);

                    CREATE TABLE IF NOT EXISTS aura_core.confaz_pmpf (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        uf TEXT NOT NULL,
                        produto TEXT NOT NULL,
                        valor_pauta REAL NOT NULL,
                        vigencia_inicio TEXT NOT NULL,
                        vigencia_fim TEXT,
                        ato_cotepe_num TEXT,
                        data_publicacao_dou TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(uf, produto, vigencia_inicio)
                    );
                    CREATE INDEX IF NOT EXISTS aura_core.idx_confaz_pmpf_uf_prod
                    ON confaz_pmpf (uf, produto, vigencia_inicio);

                    CREATE TABLE IF NOT EXISTS aura_core.bacen_series_historicas (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        codigo_serie INTEGER NOT NULL,
                        nome_serie TEXT NOT NULL,
                        data_referencia TEXT NOT NULL,
                        valor REAL NOT NULL,
                        unidade TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(codigo_serie, data_referencia)
                    );
                    CREATE INDEX IF NOT EXISTS aura_core.idx_bacen_serie_data
                    ON bacen_series_historicas (codigo_serie, data_referencia);

                    CREATE TABLE IF NOT EXISTS aura_core.public_sync_telemetry (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        fonte TEXT NOT NULL,
                        status TEXT NOT NULL,
                        registros_processados INTEGER NOT NULL DEFAULT 0,
                        registros_inseridos INTEGER NOT NULL DEFAULT 0,
                        duracao_ms REAL NOT NULL,
                        mensagem_erro TEXT,
                        executado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                    """
                )
        else:
            sql_path = Path(__file__).resolve().parent.parent.parent.parent / "scripts" / "init_public_data_cache.sql"
            if not sql_path.exists():
                sql_path = Path("scripts/init_public_data_cache.sql")
            ddl_sql = sql_path.read_text(encoding="utf-8")
            with self._get_connection() as conn:
                cur = conn.cursor()
                try:
                    cur.execute(ddl_sql)
                    conn.commit()
                finally:
                    cur.close()

    def _execute_write(self, query: str, params: tuple | list = ()) -> int:
        """Executa operacao de escrita transacional adaptando placeholders."""
        if self.use_sqlite:
            sqlite_sql = query.replace("%s", "?")
            with self._get_connection() as conn:
                cur = conn.execute(sqlite_sql, params)
                return cur.rowcount
        else:
            with self._get_connection() as conn:
                cur = conn.cursor()
                try:
                    cur.execute(query, params)
                    conn.commit()
                    return cur.rowcount
                finally:
                    cur.close()

    def _execute_query(self, query: str, params: tuple | list = ()) -> list[dict[str, Any]]:
        """Executa consulta de leitura retornando lista de dicionarios."""
        if self.use_sqlite:
            sqlite_sql = query.replace("%s", "?")
            with self._get_connection() as conn:
                cur = conn.execute(sqlite_sql, params)
                rows = cur.fetchall()
                return [dict(r) for r in rows]
        else:
            with self._get_connection() as conn:
                cur = conn.cursor()
                try:
                    cur.execute(query, params)
                    rows = cur.fetchall()
                    if not cur.description:
                        return []
                    col_names = [desc[0] for desc in cur.description]
                    return [dict(zip(col_names, r)) for r in rows]
                finally:
                    cur.close()

    @staticmethod
    def _parse_float(val: Any) -> float:
        """Converte de forma robusta strings com virgula, espacos ou simbolos para float."""
        if val is None:
            return 0.0
        if isinstance(val, (int, float)):
            return float(val)
        try:
            s = str(val).strip().replace("R$", "").replace(" ", "").replace(",", ".")
            return float(s)
        except (ValueError, TypeError):
            return 0.0

    @staticmethod
    def _normalize_date_str(val: Any) -> str:
        """Converte formatos DD/MM/AAAA ou ISO para AAAA-MM-DD com fallback seguro."""
        if val is None:
            return datetime.date.today().isoformat()
        if isinstance(val, (datetime.date, datetime.datetime)):
            return val.strftime("%Y-%m-%d")
        s = str(val).strip()
        if not s:
            return datetime.date.today().isoformat()
        if "/" in s:
            parts = s.split("/")
            if len(parts) == 3:
                d, m, y = parts
                try:
                    return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
                except ValueError:
                    return datetime.date.today().isoformat()
        try:
            dt = datetime.date.fromisoformat(s[:10])
            return dt.isoformat()
        except ValueError:
            return datetime.date.today().isoformat()

    def save_anp_precos_batch(self, records: list[dict[str, Any]]) -> int:
        """
        Salva lote de precos semanais da ANP de forma idempotente via UPSERT:
        ON CONFLICT (cnpj_revenda, produto, data_coleta)
        DO UPDATE SET valor_venda = EXCLUDED.valor_venda, bandeira = EXCLUDED.bandeira.
        """
        if not records:
            return 0

        upsert_sql = """
        INSERT INTO aura_core.anp_precos_semanais (
            regiao, estado_sigla, municipio, revenda, cnpj_revenda,
            produto, data_coleta, valor_venda, unidade_medida, bandeira
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (cnpj_revenda, produto, data_coleta)
        DO UPDATE SET
            valor_venda = EXCLUDED.valor_venda,
            bandeira = EXCLUDED.bandeira;
        """

        salvos = 0
        if self.use_sqlite:
            sqlite_sql = upsert_sql.replace("%s", "?")
            with self._get_connection() as conn:
                conn.execute("BEGIN TRANSACTION")
                try:
                    for r in records:
                        cnpj = str(r.get("cnpj_revenda", "")).strip()
                        produto = str(r.get("produto", "")).strip()
                        data_col = self._normalize_date_str(r.get("data_coleta"))
                        if not cnpj or not produto:
                            continue

                        valor_venda = self._parse_float(r.get("valor_venda", 0.0))
                        params = (
                            str(r.get("regiao", "")).strip(),
                            str(r.get("estado_sigla", r.get("uf", ""))).strip().upper(),
                            str(r.get("municipio", "")).strip().upper(),
                            str(r.get("revenda", "")).strip(),
                            cnpj,
                            produto.upper(),
                            data_col,
                            valor_venda,
                            str(r.get("unidade_medida", "R$ / litro")).strip() or "R$ / litro",
                            str(r.get("bandeira", "")).strip(),
                        )
                        conn.execute(sqlite_sql, params)
                        salvos += 1
                    conn.execute("COMMIT")
                except Exception:
                    conn.execute("ROLLBACK")
                    raise
        else:
            with self._get_connection() as conn:
                cur = conn.cursor()
                try:
                    for r in records:
                        cnpj = str(r.get("cnpj_revenda", "")).strip()
                        produto = str(r.get("produto", "")).strip()
                        data_col = self._normalize_date_str(r.get("data_coleta"))
                        if not cnpj or not produto:
                            continue

                        valor_venda = self._parse_float(r.get("valor_venda", 0.0))
                        params = (
                            str(r.get("regiao", "")).strip(),
                            str(r.get("estado_sigla", r.get("uf", ""))).strip().upper(),
                            str(r.get("municipio", "")).strip().upper(),
                            str(r.get("revenda", "")).strip(),
                            cnpj,
                            produto.upper(),
                            data_col,
                            valor_venda,
                            str(r.get("unidade_medida", "R$ / litro")).strip() or "R$ / litro",
                            str(r.get("bandeira", "")).strip(),
                        )
                        cur.execute(upsert_sql, params)
                        salvos += 1
                    conn.commit()
                finally:
                    cur.close()

        return salvos

    def save_confaz_pmpf_batch(self, records: list[dict[str, Any]]) -> int:
        """
        Salva lote de pautas COTEPE PMPF de forma idempotente via UPSERT:
        ON CONFLICT (uf, produto, vigencia_inicio)
        DO UPDATE SET valor_pauta = EXCLUDED.valor_pauta.
        Suporta tanto registros canonicos (com produto e valor_pauta) quanto matrizes de UF.
        """
        if not records:
            return 0

        upsert_sql = """
        INSERT INTO aura_core.confaz_pmpf (
            uf, produto, valor_pauta, vigencia_inicio, vigencia_fim,
            ato_cotepe_num, data_publicacao_dou
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (uf, produto, vigencia_inicio)
        DO UPDATE SET
            valor_pauta = EXCLUDED.valor_pauta,
            ato_cotepe_num = COALESCE(EXCLUDED.ato_cotepe_num, aura_core.confaz_pmpf.ato_cotepe_num);
        """

        # Normaliza registros para linhas individuais
        flat_records: list[tuple] = []
        canonical_products = (
            "gasolina_comum",
            "gasolina_aditivada",
            "etanol_hidratado",
            "diesel_s10",
            "diesel_s500",
            "glp",
        )

        for r in records:
            uf = str(r.get("uf", "")).strip().upper()
            if not uf:
                continue

            vig_inicio = self._normalize_date_str(r.get("vigencia_inicio"))
            vig_fim = self._normalize_date_str(r.get("vigencia_fim")) if r.get("vigencia_fim") else None
            ato_num = str(r.get("ato_cotepe_num", "")).strip() or None
            dt_dou = self._normalize_date_str(r.get("data_publicacao_dou")) if r.get("data_publicacao_dou") else None

            if "produto" in r and "valor_pauta" in r:
                prod = str(r["produto"]).strip().lower().replace(" ", "_")
                val = self._parse_float(r["valor_pauta"])
                flat_records.append((uf, prod, val, vig_inicio, vig_fim, ato_num, dt_dou))
            else:
                for prod_key in canonical_products:
                    if prod_key in r:
                        val = self._parse_float(r[prod_key])
                        flat_records.append((uf, prod_key, val, vig_inicio, vig_fim, ato_num, dt_dou))

        salvos = 0
        if self.use_sqlite:
            sqlite_sql = upsert_sql.replace("%s", "?")
            with self._get_connection() as conn:
                conn.execute("BEGIN TRANSACTION")
                try:
                    for params in flat_records:
                        conn.execute(sqlite_sql, params)
                        salvos += 1
                    conn.execute("COMMIT")
                except Exception:
                    conn.execute("ROLLBACK")
                    raise
        else:
            with self._get_connection() as conn:
                cur = conn.cursor()
                try:
                    for params in flat_records:
                        cur.execute(upsert_sql, params)
                        salvos += 1
                    conn.commit()
                finally:
                    cur.close()

        return salvos

    def save_bacen_series_batch(self, records: list[dict[str, Any]]) -> int:
        """
        Salva lote de series macroeconomicas do BACEN SGS via UPSERT:
        ON CONFLICT (codigo_serie, data_referencia)
        DO UPDATE SET valor = EXCLUDED.valor.
        """
        if not records:
            return 0

        upsert_sql = """
        INSERT INTO aura_core.bacen_series_historicas (
            codigo_serie, nome_serie, data_referencia, valor, unidade
        ) VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (codigo_serie, data_referencia)
        DO UPDATE SET valor = EXCLUDED.valor;
        """

        salvos = 0
        if self.use_sqlite:
            sqlite_sql = upsert_sql.replace("%s", "?")
            with self._get_connection() as conn:
                conn.execute("BEGIN TRANSACTION")
                try:
                    for r in records:
                        try:
                            cod = int(r.get("codigo_serie", 0) or 0)
                        except (ValueError, TypeError):
                            continue
                        if cod <= 0:
                            continue

                        dt_ref = self._normalize_date_str(
                            r.get("data_referencia") or r.get("data_iso") or r.get("data")
                        )
                        valor = self._parse_float(r.get("valor", 0.0))

                        meta = BACEN_SERIES_METADATA.get(cod, {})
                        nome = str(r.get("nome_serie") or meta.get("nome_serie") or f"Serie {cod}").strip()
                        unidade = str(r.get("unidade") or meta.get("unidade") or "").strip()

                        conn.execute(sqlite_sql, (cod, nome, dt_ref, valor, unidade))
                        salvos += 1
                    conn.execute("COMMIT")
                except Exception:
                    conn.execute("ROLLBACK")
                    raise
        else:
            with self._get_connection() as conn:
                cur = conn.cursor()
                try:
                    for r in records:
                        try:
                            cod = int(r.get("codigo_serie", 0) or 0)
                        except (ValueError, TypeError):
                            continue
                        if cod <= 0:
                            continue

                        dt_ref = self._normalize_date_str(
                            r.get("data_referencia") or r.get("data_iso") or r.get("data")
                        )
                        valor = self._parse_float(r.get("valor", 0.0))

                        meta = BACEN_SERIES_METADATA.get(cod, {})
                        nome = str(r.get("nome_serie") or meta.get("nome_serie") or f"Serie {cod}").strip()
                        unidade = str(r.get("unidade") or meta.get("unidade") or "").strip()

                        cur.execute(upsert_sql, (cod, nome, dt_ref, valor, unidade))
                        salvos += 1
                    conn.commit()
                finally:
                    cur.close()

        return salvos

    def record_sync_telemetry(
        self,
        fonte: str,
        status: str,
        processados: int,
        inseridos: int,
        duracao_ms: float,
        erro: str | None = None,
    ) -> None:
        """Registra auditoria de execucao de sincronizacao em public_sync_telemetry."""
        sql = """
        INSERT INTO aura_core.public_sync_telemetry (
            fonte, status, registros_processados, registros_inseridos, duracao_ms, mensagem_erro
        ) VALUES (%s, %s, %s, %s, %s, %s);
        """
        params = (
            str(fonte).strip(),
            str(status).strip().upper(),
            int(processados),
            int(inseridos),
            round(float(duracao_ms), 2),
            str(erro) if erro else None,
        )
        self._execute_write(sql, params)

    def get_preco_benchmark_anp(
        self,
        municipio: str,
        produto: str,
        dias_historico: int = 30,
    ) -> dict[str, Any]:
        """
        Consulta estatisticas descritivas de mercado da ANP para um municipio e produto.
        Retorna: preco_medio, preco_minimo, preco_maximo, preco_mediana, quartil_1,
        quartil_3, desvio_padrao, total_amostras, data_ultima_coleta e postos_amostrados.
        Tempo de resposta garantido: sub-50ms.
        """
        mun_clean = municipio.strip().upper()
        prod_clean = produto.strip().upper()

        # 1. Identifica data da coleta mais recente disponivel com uso direto do indice composto
        sql_max = """
        SELECT MAX(data_coleta) AS max_data
        FROM aura_core.anp_precos_semanais
        WHERE municipio = %s AND produto = %s;
        """
        res_max = self._execute_query(sql_max, (mun_clean, prod_clean))
        max_dt_str = res_max[0].get("max_data") if res_max else None

        if not max_dt_str:
            return {
                "municipio": mun_clean,
                "produto": prod_clean,
                "preco_medio": 0.0,
                "preco_minimo": 0.0,
                "preco_maximo": 0.0,
                "preco_mediana": 0.0,
                "quartil_1": 0.0,
                "quartil_3": 0.0,
                "desvio_padrao": 0.0,
                "total_amostras": 0,
                "data_ultima_coleta": None,
                "postos_amostrados": 0,
            }

        max_dt = datetime.date.fromisoformat(str(max_dt_str)[:10])
        dt_limite = (max_dt - datetime.timedelta(days=dias_historico)).isoformat()

        # 2. Coleta registros do intervalo historico aproveitando ordenacao pelo indice
        sql_rows = """
        SELECT revenda, cnpj_revenda, valor_venda, bandeira, data_coleta
        FROM aura_core.anp_precos_semanais
        WHERE municipio = %s
          AND produto = %s
          AND data_coleta >= %s
        ORDER BY data_coleta DESC;
        """
        rows = self._execute_query(sql_rows, (mun_clean, prod_clean, dt_limite))

        # Filtra estritamente amostras validas e estritamente positivas (> 0)
        valores = [
            float(r["valor_venda"])
            for r in rows
            if r.get("valor_venda") is not None and float(r.get("valor_venda")) > 0
        ]
        if not valores:
            return {
                "municipio": mun_clean,
                "produto": prod_clean,
                "preco_medio": 0.0,
                "preco_minimo": 0.0,
                "preco_maximo": 0.0,
                "preco_mediana": 0.0,
                "quartil_1": 0.0,
                "quartil_3": 0.0,
                "desvio_padrao": 0.0,
                "total_amostras": 0,
                "data_ultima_coleta": str(max_dt_str)[:10],
                "postos_amostrados": 0,
            }

        # Calculo estatistico robusto
        total = len(valores)
        preco_min = round(min(valores), 3)
        preco_max = round(max(valores), 3)
        preco_medio = round(statistics.mean(valores), 3)
        preco_mediana = round(statistics.median(valores), 3)

        if total >= 2:
            stdev_val = round(statistics.stdev(valores), 3)
            quantiles = statistics.quantiles(valores, n=4, method="inclusive")
            q1 = round(quantiles[0], 3)
            q3 = round(quantiles[2], 3)
        else:
            stdev_val = 0.0
            q1 = valores[0]
            q3 = valores[0]

        stations = {r.get("cnpj_revenda") or r.get("revenda") for r in rows if (r.get("cnpj_revenda") or r.get("revenda"))}
        postos_count = len(stations) if stations else len(rows)

        return {
            "municipio": mun_clean,
            "produto": prod_clean,
            "preco_medio": preco_medio,
            "preco_minimo": preco_min,
            "preco_maximo": preco_max,
            "preco_mediana": preco_mediana,
            "quartil_1": q1,
            "quartil_3": q3,
            "desvio_padrao": stdev_val,
            "total_amostras": total,
            "data_ultima_coleta": str(max_dt_str)[:10],
            "postos_amostrados": postos_count,
        }

    def get_ranking_postos_anp(
        self,
        municipio: str,
        produto: str,
        limit: int = 5,
        ordem: str = "asc",
        dias_historico: int = 30,
    ) -> list[dict[str, Any]]:
        """
        Retorna o ranking de postos pesquisados pela ANP ordenados por preco.
        Ordem 'asc' para os menores precos (mais baratos) ou 'desc' para maiores precos.
        """
        mun_clean = municipio.strip().upper()
        prod_clean = produto.strip().upper()

        sql_max = """
        SELECT MAX(data_coleta) AS max_data
        FROM aura_core.anp_precos_semanais
        WHERE municipio = %s AND produto = %s;
        """
        res_max = self._execute_query(sql_max, (mun_clean, prod_clean))
        max_dt_str = res_max[0].get("max_data") if res_max else None
        if not max_dt_str:
            return []

        max_dt = datetime.date.fromisoformat(str(max_dt_str)[:10])
        dt_limite = (max_dt - datetime.timedelta(days=dias_historico)).isoformat()

        sql_rows = """
        SELECT revenda, cnpj_revenda, valor_venda, bandeira, data_coleta
        FROM aura_core.anp_precos_semanais
        WHERE municipio = %s
          AND produto = %s
          AND data_coleta >= %s
        ORDER BY data_coleta DESC;
        """
        rows = self._execute_query(sql_rows, (mun_clean, prod_clean, dt_limite))
        if not rows:
            return []

        postos_vistos: dict[str, dict[str, Any]] = {}
        for r in rows:
            val = r.get("valor_venda")
            if val is None or float(val) <= 0:
                continue
            chave = (r.get("cnpj_revenda") or r.get("revenda") or "").strip().upper()
            if not chave:
                continue
            if chave not in postos_vistos:
                postos_vistos[chave] = {
                    "posto": (r.get("revenda") or "Posto Sem Nome").strip(),
                    "cnpj": (r.get("cnpj_revenda") or "").strip(),
                    "bandeira": (r.get("bandeira") or "Branca").strip(),
                    "preco": round(float(val), 3),
                    "data_coleta": str(r.get("data_coleta") or "")[:10],
                }

        lista_postos = list(postos_vistos.values())
        is_desc = str(ordem).lower().strip() == "desc"
        lista_postos.sort(key=lambda x: x["preco"], reverse=is_desc)
        return lista_postos[:max(1, limit)]

    def get_pmpf_atual(self, uf: str, produto: str) -> dict[str, Any] | None:
        """
        Retorna a pauta fiscal ativa de PMPF para a UF e combustivel especificados.
        """
        uf_clean = uf.strip().upper()
        prod_clean = produto.strip().lower().replace(" ", "_")
        raw_prod = produto.strip().lower()

        sql = """
        SELECT uf, produto, valor_pauta, vigencia_inicio, vigencia_fim,
               ato_cotepe_num, data_publicacao_dou
        FROM aura_core.confaz_pmpf
        WHERE uf = %s
          AND (produto = %s OR produto = %s)
        ORDER BY vigencia_inicio DESC
        LIMIT 1;
        """
        rows = self._execute_query(sql, (uf_clean, prod_clean, raw_prod))
        if not rows:
            return None

        r = rows[0]
        return {
            "uf": r.get("uf"),
            "produto": r.get("produto"),
            "valor_pauta": float(r.get("valor_pauta", 0.0) or 0.0),
            "vigencia_inicio": str(r.get("vigencia_inicio"))[:10],
            "vigencia_fim": str(r.get("vigencia_fim"))[:10] if r.get("vigencia_fim") else None,
            "ato_cotepe_num": r.get("ato_cotepe_num"),
            "data_publicacao_dou": str(r.get("data_publicacao_dou"))[:10] if r.get("data_publicacao_dou") else None,
        }

    def get_indicadores_economicos_recentes(self) -> dict[str, Any]:
        """
        Retorna as ultimas taxas oficiais cadastradas da Selic diaria, PTAX dolar, IPCA mensal, Meta Selic e IGP-M.
        """
        codigos = [11, 432, 10813, 1, 433, 189]
        sql = """
        SELECT codigo_serie, nome_serie, data_referencia, valor, unidade
        FROM aura_core.bacen_series_historicas
        WHERE codigo_serie = %s
        ORDER BY data_referencia DESC
        LIMIT 1;
        """

        series_map: dict[int, dict[str, Any]] = {}
        for cod in codigos:
            rows = self._execute_query(sql, (cod,))
            if rows:
                r = rows[0]
                series_map[cod] = {
                    "codigo_serie": cod,
                    "nome_serie": r.get("nome_serie"),
                    "data_referencia": str(r.get("data_referencia"))[:10],
                    "valor": float(r.get("valor", 0.0) or 0.0),
                    "unidade": r.get("unidade"),
                }

        selic_info = series_map.get(11)
        selic_meta_info = series_map.get(432)
        ptax_info = series_map.get(10813) or series_map.get(1)
        ipca_info = series_map.get(433)
        igpm_info = series_map.get(189)

        return {
            "selic_diaria": selic_info,
            "selic_meta_copom": selic_meta_info,
            "ptax_dolar": ptax_info,
            "ipca_mensal": ipca_info,
            "igpm_mensal": igpm_info,
            "selic_diaria_aa": selic_info["valor"] if selic_info else 0.0,
            "selic_meta_copom_valor": selic_meta_info["valor"] if selic_meta_info else 0.0,
            "ptax_dolar_venda": ptax_info["valor"] if ptax_info else 0.0,
            "ipca_mensal_valor": ipca_info["valor"] if ipca_info else 0.0,
            "igpm_mensal_valor": igpm_info["valor"] if igpm_info else 0.0,
            "data_referencia_selic": selic_info["data_referencia"] if selic_info else None,
            "data_referencia_ptax": ptax_info["data_referencia"] if ptax_info else None,
            "data_referencia_ipca": ipca_info["data_referencia"] if ipca_info else None,
        }

    def get_telemetry_history(self, fonte: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
        """Retorna historico recente de sincronizacoes para auditoria operacional."""
        if fonte:
            sql = """
            SELECT id, fonte, status, registros_processados, registros_inseridos,
                   duracao_ms, mensagem_erro, executado_em
            FROM aura_core.public_sync_telemetry
            WHERE UPPER(fonte) = UPPER(%s)
            ORDER BY executado_em DESC, id DESC
            LIMIT %s;
            """
            return self._execute_query(sql, (fonte.strip(), limit))
        else:
            sql = """
            SELECT id, fonte, status, registros_processados, registros_inseridos,
                   duracao_ms, mensagem_erro, executado_em
            FROM aura_core.public_sync_telemetry
            ORDER BY executado_em DESC, id DESC
            LIMIT %s;
            """
            return self._execute_query(sql, (limit,))

    def get_latest_collection_date(self, fonte: str = "anp") -> str | None:
        """
        Retorna a data da ultima coleta registrada para a fonte governamental especificada.
        Suporta 'anp' (data_coleta), 'confaz' (vigencia_inicio) e 'bacen' (data_referencia).
        """
        src = str(fonte).strip().lower()
        try:
            if src == "anp":
                sql = "SELECT MAX(data_coleta) AS dt FROM aura_core.anp_precos_semanais;"
                rows = self._execute_query(sql)
            elif src == "confaz":
                sql = "SELECT MAX(vigencia_inicio) AS dt FROM aura_core.confaz_pmpf;"
                rows = self._execute_query(sql)
            elif src == "bacen":
                sql = "SELECT MAX(data_referencia) AS dt FROM aura_core.bacen_series_historicas;"
                rows = self._execute_query(sql)
            else:
                sql = "SELECT MAX(executado_em) AS dt FROM aura_core.public_sync_telemetry WHERE UPPER(fonte) = UPPER(%s);"
                rows = self._execute_query(sql, (src,))

            if rows and rows[0].get("dt"):
                return str(rows[0]["dt"])[:10]
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao consultar ultima data de coleta da fonte %s: %s", fonte, exc)
        return None

    def check_data_staleness(self, fonte: str = "anp", max_age_days: int = 7) -> dict[str, Any]:
        """
        Verifica se a base de dados publica esta defasada alem do limite maximo de dias.
        Retorna dicionario com flags 'is_stale', 'age_days' e 'last_date'.
        """
        dt_str = self.get_latest_collection_date(fonte)
        if not dt_str:
            return {
                "fonte": fonte,
                "is_stale": True,
                "last_date": None,
                "age_days": 999,
                "max_age_days": max_age_days,
            }

        try:
            dt = datetime.date.fromisoformat(dt_str[:10])
            today = datetime.date.today()
            age = (today - dt).days
            return {
                "fonte": fonte,
                "is_stale": age > max_age_days,
                "last_date": dt_str,
                "age_days": max(0, age),
                "max_age_days": max_age_days,
            }
        except (ValueError, TypeError):
            return {
                "fonte": fonte,
                "is_stale": True,
                "last_date": dt_str,
                "age_days": 999,
                "max_age_days": max_age_days,
            }


_repo_lock = threading.Lock()
_repository_instance: PublicDataRepository | None = None


def get_public_data_repository(
    force_sqlite: bool = False,
    sqlite_db_path: str = ":memory:",
) -> PublicDataRepository:
    """Retorna instancia singleton thread-safe do PublicDataRepository."""
    global _repository_instance
    if force_sqlite:
        return PublicDataRepository(use_sqlite_fallback=True, sqlite_db_path=sqlite_db_path)
    if _repository_instance is None:
        with _repo_lock:
            if _repository_instance is None:
                _repository_instance = PublicDataRepository()
    return _repository_instance
