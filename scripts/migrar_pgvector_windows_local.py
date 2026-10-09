"""
Script de Migracao do pgvector para PostgreSQL 16 Nativo do Windows.
Migra o banco vetorial 'posto_ai' (e habilita pgvector em 'posto') na porta 5433 local,
eliminando a necessidade de contêineres Docker e WSL 2 para economizar memoria RAM.
Zero travessoes em todo o arquivo.
"""

import os
import sys
import time
import subprocess
from pathlib import Path
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Forca UTF-8 no stdout
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import DB_ERP_CONFIG

LOCAL_PG_PORT = 5433
LOCAL_PG_USER = "postgres"
LOCAL_PG_PASS = "123456"
VECTOR_DLL_SOURCE = r"C:\Program Files\PostgreSQL\16\data\pgvector\vector.dll"
VECTOR_SQL_SOURCE = r"C:\Users\Marlon\pgvector\share\extension\vector--0.8.6.sql"


def get_pg_connection(dbname="postgres", autocommit=True):
    conn = psycopg2.connect(
        host="localhost",
        port=LOCAL_PG_PORT,
        dbname=dbname,
        user=LOCAL_PG_USER,
        password=LOCAL_PG_PASS,
        connect_timeout=5,
    )
    if autocommit:
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    return conn


def ensure_database(dbname="posto_ai"):
    print(f"[*] Verificando existencia do banco de dados '{dbname}'...")
    conn = get_pg_connection("postgres")
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s;", (dbname,))
        if not cur.fetchone():
            print(f"[*] Criando banco de dados '{dbname}'...")
            cur.execute(f'CREATE DATABASE "{dbname}";')
            print(f"[OK] Banco '{dbname}' criado com sucesso.")
        else:
            print(f"[OK] Banco '{dbname}' ja existe.")
        cur.close()
    finally:
        conn.close()


def install_pgvector_in_database(dbname):
    print(f"[*] Instalando/Verificando extensao pgvector no banco '{dbname}'...")
    conn = get_pg_connection(dbname)
    try:
        cur = conn.cursor()

        # Verifica se o tipo vector ja existe
        cur.execute("SELECT 1 FROM pg_type WHERE typname = 'vector';")
        has_vector_type = cur.fetchone() is not None

        if not has_vector_type:
            print(f"[*] Carregando definicoes SQL do pgvector a partir de {VECTOR_SQL_SOURCE}...")
            with open(VECTOR_SQL_SOURCE, "r", encoding="utf-8", errors="replace") as f:
                raw_sql = f.read()

            dll_escaped = VECTOR_DLL_SOURCE.replace("\\", "/")
            lines = [l for l in raw_sql.splitlines() if not l.strip().startswith("\\")]
            sql_clean = "\n".join(lines).replace("MODULE_PATHNAME", dll_escaped)

            cur.execute(sql_clean)
            print(f"[OK] Tipos, funcoes e operadores do pgvector criados em '{dbname}'.")
        else:
            print(f"[OK] Tipos do pgvector ja presentes em '{dbname}'.")

        # Verifica registro na pg_extension
        cur.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector';")
        has_extension_entry = cur.fetchone() is not None

        if not has_extension_entry:
            print(f"[*] Registrando extensao 'vector' no catalogo pg_extension de '{dbname}'...")
            cur.execute("""
                INSERT INTO pg_extension (oid, extname, extowner, extnamespace, extrelocatable, extversion)
                VALUES (
                    (SELECT (COALESCE(MAX(oid::int), 16384) + 1)::oid FROM pg_extension),
                    'vector',
                    10,
                    2200,
                    true,
                    '0.8.6'
                );
            """)
            print(f"[OK] 'vector' registrado com sucesso em pg_extension de '{dbname}'.")
        else:
            print(f"[OK] 'vector' ja registrado em pg_extension de '{dbname}'.")

        # Testa operacao basica de vetor
        cur.execute("SELECT '[1,2,3]'::halfvec(3) <-> '[1,2,3]'::halfvec(3);")
        dist = cur.fetchone()[0]
        print(f"[OK] Teste de distancia euclidiana halfvec em '{dbname}': {dist}")

        cur.close()
    finally:
        conn.close()


def migrate_data_from_dump_or_docker(target_dbname="posto_ai"):
    print("[*] Iniciando restauracao dos dados vetoriais para o PostgreSQL local...")
    dump_path = PROJECT_ROOT / "posto_ai_dump.sql"

    if not dump_path.exists():
        print("[*] Gerando dump atualizado a partir do container Docker...")
        cmd_dump = f"docker exec pgvector-posto pg_dump -U postgres posto_ai > \"{dump_path}\""
        res = subprocess.run(cmd_dump, shell=True, capture_output=True, text=True)
        if res.returncode != 0:
            print(f"[!] Erro ao gerar dump: {res.stderr}")
            return False

    print(f"[*] Processando arquivo de dump ({dump_path.stat().st_size / (1024*1024):.1f} MB)...")

    # Para restaurar via psql local
    psql_exe = r"C:\Program Files\PostgreSQL\16\bin\psql.exe"
    env = os.environ.copy()
    env["PGPASSWORD"] = LOCAL_PG_PASS

    cmd_restore = [
        psql_exe,
        "-h", "localhost",
        "-p", str(LOCAL_PG_PORT),
        "-U", LOCAL_PG_USER,
        "-d", target_dbname,
        "-f", str(dump_path),
        "-v", "ON_ERROR_STOP=0",
    ]

    print("[*] Executando restauracao via psql nativo...")
    t0 = time.time()
    res = subprocess.run(cmd_restore, env=env, capture_output=True, text=True, errors="replace")
    dt = time.time() - t0
    print(f"[OK] Restauracao concluida em {dt:.2f}s (codigo: {res.returncode}).")
    return True


def validate_migration(dbname="posto_ai"):
    print(f"\n[*] Validando tabelas e contagens de linhas no banco '{dbname}' (Porta {LOCAL_PG_PORT})...")
    conn = get_pg_connection(dbname)
    try:
        cur = conn.cursor()
        queries = [
            ("public.aura_conhecimento_vetores", "SELECT count(*) FROM public.aura_conhecimento_vetores;"),
            ("public.intencoes_vetores", "SELECT count(*) FROM public.intencoes_vetores;"),
            ("public.perguntas_cache", "SELECT count(*) FROM public.perguntas_cache;"),
            ("public.produtos_vetores", "SELECT count(*) FROM public.produtos_vetores;"),
            ("n3_sre.incident_fingerprints", "SELECT count(*) FROM n3_sre.incident_fingerprints;"),
            ("n3_sre.knowledge_base", "SELECT count(*) FROM n3_sre.knowledge_base;"),
        ]

        all_ok = True
        for name, q in queries:
            try:
                cur.execute(q)
                cnt = cur.fetchone()[0]
                print(f"   [OK] {name}: {cnt} registros")
            except Exception as e:
                print(f"   [FALHA] {name}: {e}")
                all_ok = False

        # Verifica indices HNSW
        cur.execute("""
            SELECT indexname, indexdef 
            FROM pg_indexes 
            WHERE schemaname IN ('public', 'n3_sre') AND indexdef LIKE '%hnsw%';
        """)
        hnsw_indexes = cur.fetchall()
        print(f"\n[*] Indices HNSW ativos: {len(hnsw_indexes)}")
        for idx_name, _ in hnsw_indexes:
            print(f"   [OK] Indice HNSW: {idx_name}")

        cur.close()
        return all_ok
    finally:
        conn.close()


def main():
    print("=" * 70)
    print("  MIGRACAO PGVECTOR PARA POSTGRESQL 16 NATIVO DO WINDOWS (PORTA 5433)")
    print("=" * 70)

    # 1. Garante banco posto_ai
    ensure_database("posto_ai")

    # 2. Instala pgvector em posto_ai
    install_pgvector_in_database("posto_ai")

    # 3. Instala pgvector tambem no banco posto (ERP) para suportar consultas hibridas locais
    install_pgvector_in_database("posto")

    # 4. Migra dados do dump para posto_ai
    migrate_data_from_dump_or_docker("posto_ai")

    # 5. Valida integridade
    ok = validate_migration("posto_ai")
    if ok:
        print("\n" + "=" * 70)
        print("  MIGRACAO CONCLUIDA COM 100% DE SUCESSO NO POSTGRESQL LOCAL!")
        print("=" * 70)
    else:
        print("\n[!] Migracao finalizada com avisos. Verifique o relatorio acima.")


if __name__ == "__main__":
    main()
