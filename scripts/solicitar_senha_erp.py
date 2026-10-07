"""
Utilitário de Solicitação e Validação da Senha Diária do ERP (webPosto).
Chamado pelos scripts .bat ao iniciar o painel ou o agente.

Solicita a senha do dia para o usuário 'suporte', testa a conexão
em tempo real no PostgreSQL e atualiza tanto o backups/erp_password.txt
quanto o arquivo .env (ERP_DB_PASSWORD).
"""

import sys
import os
import socket
from pathlib import Path

# Protege terminal UTF-8 no Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stdin, "reconfigure"):
    try:
        sys.stdin.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT_DIR / ".env"
BACKUP_PASS_PATH = ROOT_DIR / "backups" / "erp_password.txt"


def obter_config_erp() -> dict:
    """Lê configurações do ERP diretamente do .env ou variáveis de ambiente."""
    cfg = {
        "host": os.getenv("ERP_DB_HOST", "100.77.164.17"),
        "port": int(os.getenv("ERP_DB_PORT", "5433")),
        "dbname": os.getenv("ERP_DB_NAME", "posto"),
        "user": os.getenv("ERP_DB_USER", "suporte"),
    }
    if ENV_PATH.exists():
        try:
            with open(ENV_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        k, v = line.split("=", 1)
                        k, v = k.strip(), v.strip()
                        if k == "ERP_DB_HOST":
                            cfg["host"] = v
                        elif k == "ERP_DB_PORT":
                            cfg["port"] = int(v)
                        elif k == "ERP_DB_NAME":
                            cfg["dbname"] = v
                        elif k == "ERP_DB_USER":
                            cfg["user"] = v
        except Exception:
            pass
    return cfg


def obter_senha_atual() -> str:
    """Retorna a última senha registrada em backups ou .env."""
    if BACKUP_PASS_PATH.exists():
        try:
            with open(BACKUP_PASS_PATH, "r", encoding="utf-8-sig") as f:
                s = f.read().strip("\ufeff \r\n\t")
                if s:
                    return s
        except Exception:
            pass

    if ENV_PATH.exists():
        try:
            with open(ENV_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("ERP_DB_PASSWORD="):
                        val = line.split("=", 1)[1].strip()
                        if val:
                            return val
        except Exception:
            pass

    return "899007"


def salvar_senha(senha: str):
    """Atualiza a senha em backups/erp_password.txt e no .env."""
    BACKUP_PASS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(BACKUP_PASS_PATH, "w", encoding="utf-8") as f:
        f.write(senha.strip() + "\n")

    if ENV_PATH.exists():
        try:
            with open(ENV_PATH, "r", encoding="utf-8") as f:
                lines = f.readlines()
            updated = False
            new_lines = []
            for line in lines:
                if line.startswith("ERP_DB_PASSWORD="):
                    new_lines.append(f"ERP_DB_PASSWORD={senha.strip()}\n")
                    updated = True
                else:
                    new_lines.append(line)
            if not updated:
                new_lines.append(f"\nERP_DB_PASSWORD={senha.strip()}\n")
            with open(ENV_PATH, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
        except Exception as e:
            print(f" [!] Aviso ao atualizar .env: {e}")


def testar_conexao_erp(cfg: dict, senha: str) -> tuple[bool, str]:
    """Testa conexão TCP e autenticação Postgres com a senha informada."""
    host = cfg["host"]
    port = cfg["port"]

    # 1. Teste de Socket rápido
    try:
        s = socket.create_connection((host, port), timeout=2.0)
        s.close()
    except socket.timeout:
        return False, f"Timeout na rede ao alcançar {host}:{port} (Notebook offline ou Firewall bloqueando)"
    except ConnectionRefusedError:
        return False, f"Conexão recusada em {host}:{port} (Serviço PostgreSQL não está em execução)"
    except Exception as e:
        return False, f"Falha de rede em {host}:{port}: {e}"

    # 2. Teste de Autenticação Postgres
    try:
        import psycopg2
        conn = psycopg2.connect(
            host=host,
            port=port,
            dbname=cfg["dbname"],
            user=cfg["user"],
            password=senha,
            connect_timeout=3,
        )
        conn.close()
        return True, "Autenticação bem-sucedida!"
    except UnicodeDecodeError as ude:
        raw = getattr(ude, "object", b"")
        msg = raw.decode("latin1", errors="replace").strip() if isinstance(raw, (bytes, bytearray)) else str(ude)
        return False, msg
    except Exception as e:
        return False, str(e).strip()


def solicitar_senha_interativa():
    cfg = obter_config_erp()
    senha_atual = obter_senha_atual()

    print("=" * 75)
    print(" [AUTENTICACAO ERP] webPosto - Senha do Dia (Usuario 'suporte')")
    print("=" * 75)
    print(f"  * Alvo do Banco : {cfg['host']}:{cfg['port']} (banco: {cfg['dbname']})")
    print(f"  * Usuario ERP   : {cfg['user']}")
    print(f"  * Senha Salva   : [{senha_atual}]")
    print("  * Observacao    : A senha do suporte webPosto expira diariamente.")
    print("-" * 75)

    while True:
        try:
            prompt = f"  -> Digite a SENHA DO DIA para o ERP (ENTER para manter [{senha_atual}]): "
            entrada = input(prompt).strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\n [!] Operacao cancelada pelo usuario.")
            sys.exit(1)

        senha_candidata = entrada if entrada else senha_atual

        print(f"\n  [*] Testando autenticacao no ERP ({cfg['host']}:{cfg['port']})...")
        ok, msg = testar_conexao_erp(cfg, senha_candidata)

        if ok:
            salvar_senha(senha_candidata)
            print(f"  [OK] Conectado e autenticado com sucesso no banco ERP!")
            print(f"  [SALVO] Senha registrada em 'backups/erp_password.txt' e '.env'.")
            print("=" * 75 + "\n")
            sys.exit(0)
        else:
            print(f"  [FALHA]: {msg}")

            # Se for erro de rede/socket, avisa e dá opção de salvar mesmo assim
            if "Timeout" in msg or "recusada" in msg:
                print("\n  [AVISO] O banco ERP parece nao estar acessivel na rede neste momento.")
                print("          (Verifique se o notebook esta ligado e conectado ao Tailscale)")
                try:
                    resp = input("  Deseja salvar esta senha mesmo assim e prosseguir? (S/n): ").strip().lower()
                except (KeyboardInterrupt, EOFError):
                    sys.exit(1)
                if resp in ("", "s", "sim", "y", "yes"):
                    salvar_senha(senha_candidata)
                    print(f"  [SALVO] Senha registrada para quando o servico estiver online.")
                    print("=" * 75 + "\n")
                    sys.exit(0)
                else:
                    senha_atual = senha_candidata
                    continue

            # Se for erro de senha (autenticação falhou)
            print("\n  Opcoes:")
            print("    [1] Digitar outra senha (pressione ENTER)")
            print("    [2] Prosseguir com esta senha mesmo assim")
            print("    [3] Cancelar inicializacao")
            try:
                opc = input("  Escolha [1/2/3] (padrao 1): ").strip()
            except (KeyboardInterrupt, EOFError):
                sys.exit(1)

            if opc == "2":
                salvar_senha(senha_candidata)
                print(f"  [SALVO] Senha registrada. Prosseguindo...")
                print("=" * 75 + "\n")
                sys.exit(0)
            elif opc == "3":
                print("  [!] Inicializacao cancelada.")
                sys.exit(1)
            else:
                senha_atual = senha_candidata
                print()
                continue


if __name__ == "__main__":
    # Suporte a flag não interativa se chamado por script automatizado
    if len(sys.argv) > 1 and sys.argv[1] in ("--non-interactive", "--auto", "-y"):
        senha_atual = obter_senha_atual()
        salvar_senha(senha_atual)
        sys.exit(0)
    solicitar_senha_interativa()
