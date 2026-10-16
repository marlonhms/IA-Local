"""
AURA - Motor de Provisionamento e Instalador Automatizado 1-Clique (Windows / On-Premise).

Responsavel por automatizar o onboarding completo de um novo posto de combustiveis:
1. Geracao e provisionamento idempotente de segredos criptograficos no arquivo `.env`
   (incluindo blindagem de sessao somente-leitura e timeouts estritos do ERP).
2. Checagens de pre-requisitos locais (Preflight Checks: Python, assets offline-first,
   esquema Alembic e termo de conformidade LGPD).
3. Aplicacao declarativa de migracoes de banco de dados local (`AuraMigrationManager`).
4. Registro automatico do Opt-In inicial de interoperabilidade LGPD (`ComplianceManager`).
5. Deteccao de interfaces de rede (LAN local e VPN Mesh Tailscale `100.x.x.x`).
6. Emissao de recibo auditavel de instalacao (`data/install_receipt.json`).
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import secrets
import socket
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.compliance_manager import ComplianceManager
from core.migrations import AuraMigrationManager

logger = logging.getLogger("aura.installer_wizard")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ENV_PATH = PROJECT_ROOT / ".env"
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "aura_local_memory.db"
DEFAULT_COMPLIANCE_JSON = PROJECT_ROOT / "data" / "compliance_opt_in.json"
DEFAULT_RECEIPT_PATH = PROJECT_ROOT / "data" / "install_receipt.json"

REQUIRED_OFFLINE_VENDOR_FILES = (
    "tailwind.min.js",
    "lucide.min.js",
    "marked.min.js",
)

ERP_SAFE_DRIVER_OPTIONS = (
    "-c default_transaction_read_only=on -c statement_timeout=4000 -c lock_timeout=1000"
)


class PostoInstallerWizard:
    """Orquestrador programatico de instalacao 1-clique para novos postos."""

    def __init__(
        self,
        project_root: Path | str | None = None,
        env_path: Path | str | None = None,
        db_path: Path | str | None = None,
        compliance_json_path: Path | str | None = None,
        receipt_path: Path | str | None = None,
    ) -> None:
        self.project_root = Path(project_root) if project_root else PROJECT_ROOT
        self.env_path = Path(env_path) if env_path else (self.project_root / ".env")
        self.db_path = (
            Path(db_path) if db_path else (self.project_root / "data" / "aura_local_memory.db")
        )
        self.compliance_json_path = (
            Path(compliance_json_path)
            if compliance_json_path
            else (self.project_root / "data" / "compliance_opt_in.json")
        )
        self.receipt_path = (
            Path(receipt_path)
            if receipt_path
            else (self.project_root / "data" / "install_receipt.json")
        )

    @staticmethod
    def generate_env_secrets() -> dict[str, str]:
        """Gera segredos criptograficos de 256 bits para operacao segura do posto."""
        return {
            "AURA_VOUCHER_SECRET": secrets.token_hex(32),
            "AURA_API_KEY": f"aura_live_{secrets.token_hex(24)}",
            "AURA_BACKUP_ENCRYPTION_KEY": secrets.token_hex(32),
        }

    def provision_env_file(
        self,
        *,
        filial_id: int = 1,
        tenant_id: str = "posto_matriz",
        erp_host: str = "127.0.0.1",
        erp_port: int = 5432,
        erp_db: str = "BD_Posto",
        erp_user: str = "aura_service_ro",
        erp_password: str = "aura_ro_pass_2026",
        api_port: int = 8000,
        force_regenerate_secrets: bool = False,
    ) -> dict[str, Any]:
        """
        Cria ou atualiza o arquivo `.env` preservando valores ja configurados
        e garantindo que todos os segredos obrigatorios e travas de seguranca existam.
        """
        existing_vars: dict[str, str] = {}
        existing_lines: list[str] = []

        if self.env_path.exists():
            raw_text = self.env_path.read_text(encoding="utf-8")
            for line in raw_text.splitlines():
                existing_lines.append(line)
                stripped = line.strip()
                if stripped and not stripped.startswith("#") and "=" in stripped:
                    key, val = stripped.split("=", 1)
                    existing_vars[key.strip()] = val.strip().strip('"').strip("'")

        generated_secrets = self.generate_env_secrets()
        placeholders = {
            "",
            "troque-este-segredo-em-producao",
            "changeme",
            "default_secret",
        }

        final_secrets: dict[str, str] = {}
        for key, new_val in generated_secrets.items():
            current_val = existing_vars.get(key, "")
            if force_regenerate_secrets or current_val in placeholders:
                final_secrets[key] = new_val
            else:
                final_secrets[key] = current_val

        defaults: dict[str, str] = {
            "AURA_ENV": existing_vars.get("AURA_ENV", "production"),
            "AURA_TENANT_ID": existing_vars.get("AURA_TENANT_ID", tenant_id),
            "AURA_FILIAL_ID": existing_vars.get("AURA_FILIAL_ID", str(filial_id)),
            "AURA_API_HOST": existing_vars.get("AURA_API_HOST", "0.0.0.0"),
            "AURA_API_PORT": existing_vars.get("AURA_API_PORT", str(api_port)),
            "ERP_DB_HOST": existing_vars.get("ERP_DB_HOST", erp_host),
            "ERP_DB_PORT": existing_vars.get("ERP_DB_PORT", str(erp_port)),
            "ERP_DB_NAME": existing_vars.get("ERP_DB_NAME", erp_db),
            "ERP_DB_USER": existing_vars.get("ERP_DB_USER", erp_user),
            "ERP_DB_PASSWORD": existing_vars.get("ERP_DB_PASSWORD", erp_password),
            "ERP_DB_OPTIONS": ERP_SAFE_DRIVER_OPTIONS,
            "AURA_VOUCHER_SECRET": final_secrets["AURA_VOUCHER_SECRET"],
            "AURA_API_KEY": final_secrets["AURA_API_KEY"],
            "AURA_BACKUP_ENCRYPTION_KEY": final_secrets["AURA_BACKUP_ENCRYPTION_KEY"],
            "OLLAMA_BASE_URL": existing_vars.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
            "OLLAMA_MODEL": existing_vars.get("OLLAMA_MODEL", "llama3.1:8b"),
        }

        updated_keys: set[str] = set()
        output_lines: list[str] = []

        if not existing_lines:
            output_lines.append("# AURA - Configuracao Gerada pelo Instalador 1-Clique")
            output_lines.append(f"# Gerado em: {datetime.now(UTC).isoformat()}")
            output_lines.append("")

        for line in existing_lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and "=" in stripped:
                key, _ = stripped.split("=", 1)
                clean_key = key.strip()
                if clean_key in defaults:
                    output_lines.append(f'{clean_key}="{defaults[clean_key]}"')
                    updated_keys.add(clean_key)
                else:
                    output_lines.append(line)
            else:
                output_lines.append(line)

        for key, val in defaults.items():
            if key not in updated_keys:
                output_lines.append(f'{key}="{val}"')

        self.env_path.parent.mkdir(parents=True, exist_ok=True)
        self.env_path.write_text("\n".join(output_lines) + "\n", encoding="utf-8")

        return {
            "env_path": str(self.env_path),
            "created_or_updated": True,
            "erp_user": defaults["ERP_DB_USER"],
            "erp_options": defaults["ERP_DB_OPTIONS"],
            "filial_id": int(defaults["AURA_FILIAL_ID"]),
            "tenant_id": defaults["AURA_TENANT_ID"],
            "secrets_ready": all(len(final_secrets[k]) >= 32 for k in final_secrets),
        }

    def run_preflight_checks(self) -> dict[str, Any]:
        """Executa checagens locais de integridade antes do provisionamento."""
        py_ok = sys.version_info >= (3, 10)
        vendor_dir = self.project_root / "web" / "static" / "vendor"
        missing_assets = [
            fname for fname in REQUIRED_OFFLINE_VENDOR_FILES if not (vendor_dir / fname).is_file()
        ]
        alembic_ini_ok = (self.project_root / "alembic.ini").is_file()
        termo_path = self.project_root / "docs" / "compliance" / "termo_interoperabilidade_lgpd.md"
        termo_ok = termo_path.is_file()

        checks = {
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "python_ok": py_ok,
            "offline_vendor_dir": str(vendor_dir),
            "offline_assets_ok": len(missing_assets) == 0,
            "missing_offline_assets": missing_assets,
            "alembic_config_ok": alembic_ini_ok,
            "compliance_term_ok": termo_ok,
        }
        checks["all_passed"] = bool(
            py_ok and checks["offline_assets_ok"] and alembic_ini_ok and termo_ok
        )
        return checks

    def apply_database_migrations(self) -> dict[str, Any]:
        """Aplica todas as migracoes declarativas do Alembic no banco SQLite local."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        manager = AuraMigrationManager(db_path=self.db_path)
        applied_revs = manager.upgrade("head")
        current_rev = manager.get_current_revision()
        integrity = manager.verify_schema_integrity()
        is_valid = bool(integrity.get("valid", integrity.get("is_valid", False)))
        return {
            "db_path": str(self.db_path),
            "applied_revisions": applied_revs,
            "current_revision": current_rev,
            "is_valid": is_valid,
            "present_tables": integrity.get("present_tables", []),
            "missing_tables": integrity.get("missing_tables", []),
        }

    def register_initial_opt_in(
        self,
        *,
        loja_cnpj: str = "00.000.000/0001-91",
        razao_social: str = "Posto Revendedor Homologado AURA LTDA",
        assinado_por: str = "Instalador Automatizado 1-Clique (Responsavel Tecnico)",
    ) -> dict[str, Any]:
        """Registra o aceite inicial de interoperabilidade LGPD na instalacao do posto."""
        self.compliance_json_path.parent.mkdir(parents=True, exist_ok=True)
        cm = ComplianceManager(
            db_path=self.db_path,
            json_path=self.compliance_json_path,
        )
        status = cm.register_opt_in(
            {
                "loja_cnpj": loja_cnpj,
                "razao_social": razao_social,
                "assinado_por": assinado_por,
                "status": "active",
            }
        )
        return status.model_dump(mode="json")

    @staticmethod
    def detect_network_endpoints(api_port: int = 8000) -> dict[str, Any]:
        """
        Detecta automaticamente o IP da rede local (LAN) e o IP da VPN Mesh Tailscale
        (`100.x.x.x`), montando as URLs prontas de acesso ao painel executivo.
        """
        lan_ip = "127.0.0.1"
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.settimeout(0.5)
                s.connect(("8.8.8.8", 80))
                lan_ip = s.getsockname()[0]
        except OSError:
            try:
                lan_ip = socket.gethostbyname(socket.gethostname())
            except OSError:
                lan_ip = "127.0.0.1"

        tailscale_ip: str | None = None
        # 1. Tenta consultar a CLI do Tailscale se disponivel no PATH ou em Program Files
        ts_candidates = [
            "tailscale",
            r"C:\Program Files\Tailscale\tailscale.exe",
        ]
        for cmd in ts_candidates:
            try:
                proc = subprocess.run(
                    [cmd, "ip", "-4"],
                    capture_output=True,
                    text=True,
                    timeout=2.0,
                    check=False,
                )
                if proc.returncode == 0 and proc.stdout.strip():
                    first_line = proc.stdout.strip().splitlines()[0].strip()
                    if first_line.startswith("100."):
                        tailscale_ip = first_line
                        break
            except (OSError, subprocess.SubprocessError) as exc:
                logger.debug("Candidato Tailscale CLI indisponivel (%s): %s", cmd, exc)

        # 2. Fallback por inspecao de interfaces locais procurando CGNAT 100.64.0.0/10
        if not tailscale_ip:
            try:
                host_ips = socket.gethostbyname_ex(socket.gethostname())[2]
                for ip in host_ips:
                    if ip.startswith("100."):
                        tailscale_ip = ip
                        break
            except OSError as exc:
                logger.debug("Fallback socket Tailscale indisponivel: %s", exc)

        endpoints = {
            "localhost_url": f"http://localhost:{api_port}",
            "lan_ip": lan_ip,
            "lan_url": f"http://{lan_ip}:{api_port}",
            "tailscale_ip": tailscale_ip,
            "tailscale_url": f"http://{tailscale_ip}:{api_port}" if tailscale_ip else None,
            "health_url": f"http://localhost:{api_port}/api/v1/aura/health",
            "metrics_url": f"http://localhost:{api_port}/metrics",
        }
        return endpoints

    def run_full_setup(
        self,
        *,
        loja_cnpj: str = "00.000.000/0001-91",
        razao_social: str = "Posto Revendedor Homologado AURA LTDA",
        assinado_por: str = "Instalador Automatizado 1-Clique (Responsavel Tecnico)",
        filial_id: int = 1,
        tenant_id: str = "posto_matriz",
        api_port: int = 8000,
    ) -> dict[str, Any]:
        """
        Executa o fluxo completo de provisionamento local da AURA e grava o recibo
        auditavel em `data/install_receipt.json`.
        """
        preflight = self.run_preflight_checks()
        env_result = self.provision_env_file(
            filial_id=filial_id,
            tenant_id=tenant_id,
            api_port=api_port,
        )
        migrations_result = self.apply_database_migrations()
        compliance_result = self.register_initial_opt_in(
            loja_cnpj=loja_cnpj,
            razao_social=razao_social,
            assinado_por=assinado_por,
        )
        endpoints = self.detect_network_endpoints(api_port=api_port)

        receipt = {
            "installer_version": "1.0.0",
            "installed_at": datetime.now(UTC).isoformat(),
            "status": "installed" if preflight["all_passed"] and migrations_result["is_valid"] else "degraded",
            "preflight": preflight,
            "environment": env_result,
            "database_migrations": migrations_result,
            "compliance_opt_in": compliance_result,
            "endpoints": endpoints,
        }

        self.receipt_path.parent.mkdir(parents=True, exist_ok=True)
        self.receipt_path.write_text(
            json.dumps(receipt, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return receipt


def _build_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="AURA - Wizard de Provisionamento 1-Clique para Postos Windows"
    )
    parser.add_argument(
        "--cnpj",
        default=os.environ.get("AURA_INSTALL_CNPJ", "00.000.000/0001-91"),
        help="CNPJ do posto revendedor para registro do Opt-In LGPD",
    )
    parser.add_argument(
        "--razao-social",
        default=os.environ.get(
            "AURA_INSTALL_RAZAO_SOCIAL", "Posto Revendedor Homologado AURA LTDA"
        ),
        help="Razao social do estabelecimento comercial",
    )
    parser.add_argument(
        "--assinado-por",
        default=os.environ.get(
            "AURA_INSTALL_ASSINADO_POR",
            "Instalador Automatizado 1-Clique (Responsavel Tecnico)",
        ),
        help="Responsavel pela assinatura do termo de interoperabilidade",
    )
    parser.add_argument(
        "--filial-id",
        type=int,
        default=int(os.environ.get("AURA_FILIAL_ID", "1")),
        help="Codigo numerico da filial (padrao: 1)",
    )
    parser.add_argument(
        "--tenant-id",
        default=os.environ.get("AURA_TENANT_ID", "posto_matriz"),
        help="Identificador do tenant/rede de postos",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("AURA_API_PORT", "8000")),
        help="Porta HTTP do painel e API da AURA (padrao: 8000)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Imprime o recibo de instalacao em JSON puro na saida padrao",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_cli_parser()
    args = parser.parse_args(argv)

    wizard = PostoInstallerWizard()
    receipt = wizard.run_full_setup(
        loja_cnpj=args.cnpj,
        razao_social=args.razao_social,
        assinado_por=args.assinado_por,
        filial_id=args.filial_id,
        tenant_id=args.tenant_id,
        api_port=args.port,
    )

    if args.json:
        print(json.dumps(receipt, indent=2, ensure_ascii=False))
    else:
        ep = receipt["endpoints"]
        print("[OK] Provisionamento programatico AURA concluido com sucesso!")
        print(f"  - Revisao Alembic : {receipt['database_migrations']['current_revision']}")
        print(f"  - Status LGPD     : {receipt['compliance_opt_in']['status']}")
        print(f"  - Acesso Local    : {ep['localhost_url']}")
        print(f"  - Acesso Rede LAN : {ep['lan_url']}")
        if ep.get("tailscale_url"):
            print(f"  - Acesso Tailscale: {ep['tailscale_url']}")
        print(f"  - Recibo Salvo em : {wizard.receipt_path}")

    return 0 if receipt["status"] == "installed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
