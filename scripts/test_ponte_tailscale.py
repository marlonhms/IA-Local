"""
Script de Diagnóstico e Validação da Ponte Tailscale (Notebook <-> PC de Casa).
Executável tanto no Notebook quanto no Computador de Casa para validar conectividade
de ponta a ponta nas portas 5433 (ERP) e 5434 (Docker pgvector).

Suporta passagem direta de host via CLI:
    python scripts/test_ponte_tailscale.py
    python scripts/test_ponte_tailscale.py 100.77.164.17
    python scripts/test_ponte_tailscale.py marlonh-supwp
    python scripts/test_ponte_tailscale.py --host 100.77.164.17 --erp-port 5433 --vec-port 5434
"""

import os
import sys
import time
import socket
import argparse
import subprocess
from pathlib import Path

# Ajusta path para importar módulos do projeto
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# Configura encoding UTF-8 no Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import psycopg2
from config.settings import DB_ERP_CONFIG, DB_VECTOR_CONFIG


def avaliar_sla_latencia(ms: float) -> str:
    """Classifica a latência observada em relação ao SLA de desenvolvimento."""
    if ms < 100.0:
        return f"{ms:.1f}ms [SLA EXCELENTE - Ideal para desenvolvimento interativo]"
    elif ms <= 250.0:
        return f"{ms:.1f}ms [SLA BOM - Adequado para consultas analíticas e agentes]"
    else:
        return f"{ms:.1f}ms [SLA ALERTA - Latência elevada; verifique sinal Wi-Fi ou rota DERP]"


def testar_porta_socket(host: str, port: int, timeout: float = 4.0) -> tuple[bool, float, str]:
    """
    Testa se a porta TCP está aberta e respondendo via socket puro.
    Utiliza socket.create_connection para suporte nativo dual-stack (IPv4 e IPv6 / MagicDNS).
    """
    t0 = time.perf_counter()
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        sock.close()
        ms = (time.perf_counter() - t0) * 1000
        return True, ms, "OK"
    except socket.timeout:
        return False, 0.0, f"Timeout ({timeout:.1f}s) - Provável bloqueio no Firewall do Windows ou IP inacessível"
    except ConnectionRefusedError:
        return False, 0.0, "Conexão Recusada - Serviço ou container não está escutando nesta porta no host"
    except Exception as e:
        return False, 0.0, str(e)


def testar_conexao_erp(host: str = None, port: int = None, timeout: int = 5) -> tuple[bool, str, float]:
    """Testa autenticação, integridade de tabelas e consulta simples no banco ERP."""
    config = dict(DB_ERP_CONFIG)
    if host:
        config["host"] = host
    if port:
        config["port"] = int(port)
    config["connect_timeout"] = timeout

    target_host = config.get("host", "localhost")
    target_port = int(config.get("port", 5433))

    # 1. Teste de Socket TCP
    ok_sock, lat_sock, err_sock = testar_porta_socket(target_host, target_port, timeout=float(timeout))
    if not ok_sock:
        return False, f"Falha no Socket TCP ({target_host}:{target_port}): {err_sock}", 0.0

    # 2. Teste de Conexão Postgres + Autenticação + Query
    t0 = time.perf_counter()
    try:
        conn = psycopg2.connect(**config)
        cur = conn.cursor()
        cur.execute("SELECT current_database(), current_user, inet_server_port(), version();")
        row = cur.fetchone()
        
        # Verifica tabela produtos
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'produtos'
            );
        """)
        has_produtos = cur.fetchone()[0]
        total_produtos = "N/A"
        if has_produtos:
            cur.execute("SELECT count(*) FROM produtos;")
            total_produtos = cur.fetchone()[0]

        conn.close()
        lat = (time.perf_counter() - t0) * 1000
        sla_desc = avaliar_sla_latencia(lat)
        return True, (
            f"Conectado com sucesso em {sla_desc}\n"
            f"   - Database: {row[0]} | User: {row[1]} | Porta Server: {row[2]}\n"
            f"   - Tabela 'produtos': {total_produtos} registros encontrados no ERP"
        ), lat
    except psycopg2.OperationalError as e:
        return False, f"Falha de autenticação/handshake Postgres: {e}", 0.0
    except UnicodeDecodeError as ude:
        raw_bytes = getattr(ude, "object", b"")
        msg = raw_bytes.decode("latin1", errors="replace").strip() if isinstance(raw_bytes, (bytes, bytearray)) else str(ude)
        return False, f"Falha de autenticação/handshake Postgres: {msg}", 0.0
    except Exception as e:
        return False, f"Erro inesperado no ERP: {e}", 0.0


def testar_conexao_vector(host: str = None, port: int = None, timeout: int = 5) -> tuple[bool, str, float]:
    """Testa autenticação, extensão pgvector e tabela de embeddings no banco vetorial."""
    config = dict(DB_VECTOR_CONFIG)
    if host:
        config["host"] = host
    if port:
        config["port"] = int(port)
    config["connect_timeout"] = timeout

    target_host = config.get("host", "localhost")
    target_port = int(config.get("port", 5433))

    # 1. Teste de Socket TCP
    ok_sock, lat_sock, err_sock = testar_porta_socket(target_host, target_port, timeout=float(timeout))
    if not ok_sock:
        return False, f"Falha no Socket TCP ({target_host}:{target_port}): {err_sock}", 0.0

    # 2. Teste de Conexão Postgres + Extensão Vector + Tabela
    t0 = time.perf_counter()
    try:
        conn = psycopg2.connect(**config)
        cur = conn.cursor()
        cur.execute("SELECT current_database(), current_user, inet_server_port();")
        row = cur.fetchone()

        # Verifica extensão pgvector
        cur.execute("SELECT installed_version FROM pg_available_extensions WHERE name = 'vector';")
        ext = cur.fetchone()
        ext_version = ext[0] if (ext and ext[0]) else "NÃO INSTALADA"

        # Verifica existência da tabela de vetores de forma segura
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'produtos_vetores'
            );
        """)
        has_table = cur.fetchone()[0]
        if has_table:
            cur.execute("SELECT count(*) FROM produtos_vetores;")
            total_vec = cur.fetchone()[0]
            table_info = f"{total_vec} embeddings indexados"
        else:
            table_info = "ainda não criada (popule com 'python scripts/index_produtos.py')"

        conn.close()
        lat = (time.perf_counter() - t0) * 1000
        sla_desc = avaliar_sla_latencia(lat)
        return True, (
            f"Conectado com sucesso em {sla_desc}\n"
            f"   - Database: {row[0]} | User: {row[1]} | Porta Server: {row[2]}\n"
            f"   - Extensão pgvector: v{ext_version}\n"
            f"   - Tabela 'produtos_vetores': {table_info}"
        ), lat
    except psycopg2.OperationalError as e:
        return False, f"Falha de autenticação/handshake pgvector: {e}", 0.0
    except Exception as e:
        return False, f"Erro inesperado no pgvector: {e}", 0.0


def obter_info_tailscale_local() -> dict:
    """Tenta obter informações do nó Tailscale local se o binário estiver disponível."""
    info = {"installed": False, "self_ip": None, "peers": []}
    try:
        res = subprocess.run(["tailscale", "status"], capture_output=True, text=True, timeout=3)
        if res.returncode == 0:
            info["installed"] = True
            lines = res.stdout.strip().splitlines()
            for line in lines:
                parts = line.split()
                if len(parts) >= 2:
                    ip, name = parts[0], parts[1]
                    info["peers"].append((ip, name))
                    if "-" in line:
                        info["self_ip"] = ip
                        info["self_name"] = name
    except Exception:
        pass
    return info


def main():
    parser = argparse.ArgumentParser(
        description="Diagnóstico da Ponte de Rede Tailscale - Ai.la (Notebook <-> PC de Casa)"
    )
    parser.add_argument(
        "target_host",
        nargs="?",
        default=None,
        help="Host alvo opcional (ex: 100.77.164.17 ou marlonh-supwp). Se omitido, usa o definido no .env.",
    )
    parser.add_argument("--host", default=None, help="Host alvo (sinônimo do argumento posicional)")
    parser.add_argument("--erp-port", type=int, default=None, help="Porta do ERP (padrão: 5433)")
    parser.add_argument("--vec-port", type=int, default=None, help="Porta do pgvector (padrão: 5433)")
    parser.add_argument("--timeout", type=int, default=5, help="Timeout de conexão em segundos (padrão: 5)")
    args = parser.parse_args()

    target_host = args.host or args.target_host

    erp_host = target_host or DB_ERP_CONFIG.get("host", "localhost")
    erp_port = args.erp_port or DB_ERP_CONFIG.get("port", 5433)
    vec_host = target_host or DB_VECTOR_CONFIG.get("host", "localhost")
    vec_port = args.vec_port or DB_VECTOR_CONFIG.get("port", 5433)

    print("=" * 76)
    print(" 🔍 DIAGNÓSTICO DA PONTE TAILSCALE - AI.LA (BANCO LOCAL & REMOTO)")
    print("=" * 76)

    # Detecção do Tailscale local
    ts_info = obter_info_tailscale_local()
    if ts_info.get("installed") and ts_info.get("peers"):
        print("\n[Rede Tailscale Ativa]")
        for ip, name in ts_info["peers"][:3]:
            marca = " (ESTA MÁQUINA)" if ip == ts_info.get("self_ip") else ""
            print(f"  • {ip:<16} -> {name}{marca}")

    print(f"\n[Alvos de Teste Carregados]")
    print(f"  • ERP Target    : {erp_host}:{erp_port} (db: {DB_ERP_CONFIG.get('dbname')}, user: {DB_ERP_CONFIG.get('user')})")
    print(f"  • Vector Target : {vec_host}:{vec_port} (db: {DB_VECTOR_CONFIG.get('dbname')}, user: {DB_VECTOR_CONFIG.get('user')})")

    # 1. Teste ERP
    print(f"\n[1/2] Testando Conexão com Banco ERP ({erp_host}:{erp_port})...")
    ok_erp, msg_erp, lat_erp = testar_conexao_erp(host=erp_host, port=erp_port, timeout=args.timeout)
    if ok_erp:
        print(f"  [OK] {msg_erp}")
    else:
        print(f"  [ERRO] {msg_erp}")

    # 2. Teste Vector
    print(f"\n[2/2] Testando Conexão com Banco Vetorial ({vec_host}:{vec_port})...")
    ok_vec, msg_vec, lat_vec = testar_conexao_vector(host=vec_host, port=vec_port, timeout=args.timeout)
    if ok_vec:
        print(f"  [OK] {msg_vec}")
    else:
        print(f"  [ERRO] {msg_vec}")

    print("\n" + "=" * 76)
    if ok_erp and ok_vec:
        print("🎉 SUCESSO TOTAL: A ponte de rede está 100% operacional!")
        print("   Você pode executar e codar o projeto normalmente nesta máquina.")
        print("=" * 76)
        sys.exit(0)
    else:
        print("⚠️  ATENÇÃO: Houve falhas na conexão da ponte. Checklist de Solução:")
        erros_comb = f"{msg_erp} {msg_vec}"
        if "Timeout" in erros_comb:
            print("   -> Firewall: Execute 'liberar_firewall_tailscale.bat' como Administrador no notebook.")
            print("   -> IP/Host: Verifique se o notebook está online no Tailscale ('tailscale status').")
        if "Recusada" in erros_comb:
            print("   -> Serviços: Verifique se o PostgreSQL 16 e o Docker estão em execução no notebook.")
        if "autenticação" in erros_comb.lower() or "password" in erros_comb.lower():
            print("   -> Credenciais: Verifique ERP_DB_PASSWORD e VECTOR_DB_PASSWORD no arquivo .env.")
            print("   -> pg_hba.conf: Verifique autorização da sub-rede Tailscale 100.64.0.0/10 no notebook.")
        print("=" * 76)
        sys.exit(1)


if __name__ == "__main__":
    main()
