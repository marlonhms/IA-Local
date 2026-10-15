"""
Daemon de Sincronizacao Continua (ERP -> pgvector) com Change Data Capture (CDC).
Suporta dois modos operacionais (P2-2):
1. Modo Orientado a Eventos (LISTEN/NOTIFY no canal 'aura_cdc_channel'): desperta
   em sub-segundo (< 500ms) quando mutacoes reais ocorrem no ERP.
2. Fallback Gracioso de Polling (intervalo longo de 4 horas / 14400s ou customizado):
   acionado automaticamente quando o ERP opera em modo Clean Room Read-Only sem triggers.
Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

import argparse
import sys
import time
from contextlib import suppress
from pathlib import Path

import google.generativeai as genai
import psycopg2
from psycopg2.extras import RealDictCursor

# Garante saida em UTF-8 no terminal Windows
if sys.stdout.encoding != "utf-8":
    with suppress(AttributeError, OSError, ValueError):
        sys.stdout.reconfigure(encoding="utf-8")

# Adiciona o diretorio raiz ao path para importacoes absolutas
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import (
    DB_ERP_CONFIG,
    DB_VECTOR_CONFIG,
    DEFAULT_EMBEDDING_MODEL,
    GEMINI_API_KEY,
    get_erp_password,
)
from core.cdc_listener import (
    DEFAULT_CDC_CHANNEL,
    FALLBACK_POLLING_INTERVAL_SECONDS,
    AuraCDCListener,
)
from scripts.index_produtos import (
    calcular_hash_produto,
    gerar_texto_busca_produto,
)


def sync_cycle(conn_erp, conn_vec) -> int:
    """Executa um ciclo unico de verificacao e sincronizacao CDC via Delta Hash."""
    with conn_erp.cursor(cursor_factory=RealDictCursor) as cur_erp:
        cur_erp.execute(
            """
            SELECT TRIM(p.codpro) as codpro, TRIM(p.nompro) as nompro,
                   COALESCE(TRIM(g.grupo), 'GERAL') as grupo, COALESCE(TRIM(p.codbar), '') as codbar,
                   COALESCE(TRIM(p.uni), 'UN') as unidade, COALESCE(p.valvenda, 0) as preco
            FROM public.produtos p
            LEFT JOIN public.grupos g ON g.codi = p.codgru
            WHERE p.nompro IS NOT NULL AND TRIM(p.nompro) <> '';
            """
        )
        produtos_erp = cur_erp.fetchall()

    with conn_vec.cursor(cursor_factory=RealDictCursor) as cur_vec:
        cur_vec.execute(
            "SELECT codpro, hash_md5 FROM produtos_vetores WHERE embedding IS NOT NULL;"
        )
        produtos_vec = {r["codpro"]: r["hash_md5"] for r in cur_vec.fetchall()}

    a_atualizar = []
    for p_erp in produtos_erp:
        cod = p_erp["codpro"]
        h = calcular_hash_produto(
            p_erp["nompro"],
            p_erp["grupo"],
            p_erp["codbar"],
            p_erp["preco"],
            p_erp["unidade"],
        )
        if cod not in produtos_vec or produtos_vec[cod] != h:
            a_atualizar.append((p_erp, h))

    if a_atualizar:
        print(
            f"[{time.strftime('%H:%M:%S')}] CDC: Detectados {len(a_atualizar)} produtos "
            f"alterados/novos de {len(produtos_erp)} totais. Sincronizando..."
        )

        batch_size = 20
        sucessos = 0
        with conn_vec.cursor() as cur_vec:
            for i in range(0, len(a_atualizar), batch_size):
                lote = a_atualizar[i : i + batch_size]
                textos_lote = []
                for p, _h in lote:
                    texto_busca = gerar_texto_busca_produto(
                        p["nompro"],
                        p["grupo"],
                        p["unidade"],
                        p["preco"],
                        p["codbar"],
                    )
                    textos_lote.append(texto_busca)

                try:
                    res = genai.embed_content(
                        model=DEFAULT_EMBEDDING_MODEL,
                        content=textos_lote,
                        output_dimensionality=768,
                        task_type="retrieval_document",
                    )
                    vetores = res["embedding"]

                    for (p, h), vetor, texto_busca in zip(
                        lote, vetores, textos_lote, strict=False
                    ):
                        cur_vec.execute(
                            """
                            INSERT INTO produtos_vetores (
                                codpro, nompro, grupo, codbar, unidade, preco,
                                texto_busca, embedding, hash_md5, atualizado_em
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s::halfvec, %s, NOW())
                            ON CONFLICT (codpro) DO UPDATE SET
                                nompro = EXCLUDED.nompro,
                                grupo = EXCLUDED.grupo,
                                codbar = EXCLUDED.codbar,
                                unidade = EXCLUDED.unidade,
                                preco = EXCLUDED.preco,
                                texto_busca = EXCLUDED.texto_busca,
                                embedding = EXCLUDED.embedding,
                                hash_md5 = EXCLUDED.hash_md5,
                                atualizado_em = NOW();
                            """,
                            (
                                p["codpro"],
                                p["nompro"],
                                p["grupo"],
                                p["codbar"],
                                p["unidade"],
                                p["preco"],
                                texto_busca,
                                str(vetor),
                                h,
                            ),
                        )

                    conn_vec.commit()
                    sucessos += len(lote)
                except ( psycopg2.Error, RuntimeError, ValueError, KeyError, OSError) as e:
                    print(f"[{time.strftime('%H:%M:%S')}] Erro ao sincronizar lote CDC: {e}")

        print(
            f"[{time.strftime('%H:%M:%S')}] Sincronizacao CDC concluida "
            f"({sucessos}/{len(a_atualizar)} atualizados)."
        )
    else:
        economia_pct = 100.0 if produtos_erp else 0.0
        print(
            f"[{time.strftime('%H:%M:%S')}] CDC Hit: Todos os {len(produtos_erp)} "
            f"produtos identicos ({economia_pct:.1f}% economia API)."
        )

    return len(a_atualizar)


def sync_loop(
    interval_seconds: int = FALLBACK_POLLING_INTERVAL_SECONDS,
    run_once: bool = False,
    mode: str = "event",
    channel: str = DEFAULT_CDC_CHANNEL,
) -> None:
    """
    Executa o loop principal do daemon de sincronizacao.
    No modo 'event' (padrao), registra LISTEN no PostgreSQL para despertar instantaneamente
    em mutacoes e faz fallback automatico para polling de intervalo longo se indisponivel.
    """
    print("=" * 65)
    print("  DAEMON DE SINCRONIZACAO CONTINUA COM CDC (ERP -> PGVECTOR)")
    print("=" * 65)

    if not GEMINI_API_KEY:
        print("[ERRO] Chave GEMINI_API_KEY nao configurada no .env!")
        return

    listener = AuraCDCListener(
        channel=channel,
        fallback_interval_seconds=interval_seconds,
    )
    if mode == "poll":
        listener.activate_polling_fallback("Modo polling solicitado explicitamente via CLI")

    while True:
        conn_erp = None
        conn_vec = None
        try:
            DB_ERP_CONFIG["password"] = get_erp_password()
            conn_erp = psycopg2.connect(**DB_ERP_CONFIG)
            conn_vec = psycopg2.connect(**DB_VECTOR_CONFIG)

            # Executa sincronizacao inicial de alinhamento
            sync_cycle(conn_erp, conn_vec)

            if run_once:
                break

            if listener.mode == "event" and listener.setup_listen(conn_erp):
                print(
                    f"[{time.strftime('%H:%M:%S')}] Escutando canal de eventos "
                    f"PostgreSQL LISTEN '{listener.channel}' (timeout={interval_seconds}s)..."
                )
                should_sync, events = listener.wait_for_change_or_timeout(
                    conn_erp, timeout_seconds=float(interval_seconds)
                )
                if should_sync and events:
                    codigos = [e.codpro or "*" for e in events]
                    print(
                        f"[{time.strftime('%H:%M:%S')}] Evento CDC recebido "
                        f"({len(events)} mutacoes deduplicadas: {codigos}). Sincronizando..."
                    )
                    sync_cycle(conn_erp, conn_vec)
            else:
                print(
                    f"[{time.strftime('%H:%M:%S')}] Modo Polling Fallback ativo. "
                    f"Aguardando proximo ciclo ({interval_seconds}s)..."
                )
                time.sleep(interval_seconds)

        except (psycopg2.Error, RuntimeError, ValueError, OSError) as e:
            msg = str(e)
            if (
                "utf-8" in msg.lower()
                or "password" in msg.lower()
                or "autenticacao" in msg.lower()
                or "autenticação" in msg.lower()
            ):
                print(
                    f"[{time.strftime('%H:%M:%S')}] [AVISO ERP] Senha do ERP invalida ou "
                    "expirada para a data atual. Atualize 'backups/erp_password.txt'."
                )
            else:
                print(f"[{time.strftime('%H:%M:%S')}] Erro no sync daemon: {e}")

            if run_once:
                break
            time.sleep(min(interval_seconds, 60))
        finally:
            if conn_erp is not None:
                with suppress(psycopg2.Error, OSError):
                    conn_erp.close()
            if conn_vec is not None:
                with suppress(psycopg2.Error, OSError):
                    conn_vec.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Daemon de Sincronizacao Continua com CDC Orientado a Eventos e Delta Hash"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Executa apenas um ciclo de sincronizacao e finaliza",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=FALLBACK_POLLING_INTERVAL_SECONDS,
        help="Intervalo em segundos para timeout ou fallback de polling (padrao: 14400s / 4h)",
    )
    parser.add_argument(
        "--mode",
        choices=["event", "poll"],
        default="event",
        help="Modo de operacao: 'event' (LISTEN/NOTIFY com fallback) ou 'poll' (polling puro)",
    )
    args = parser.parse_args()

    sync_loop(
        interval_seconds=args.interval,
        run_once=args.once,
        mode=args.mode,
    )
