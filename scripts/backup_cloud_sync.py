"""
CLI Executavel de Orquestracao de Backups Criptografados (AES-256-GCM) e Sincronizacao S3/R2 (Fase P2-3).
Suporta as acoes:
  --action backup  : Cria snapshot SQLite + bundle vetorial, comprime, criptografa e sincroniza com S3/R2.
  --action verify  : Verifica autenticidade AES-256-GCM, hashes SHA-256 do manifesto e integridade SQLite.
  --action restore : Descriptografa e restaura backup (direto ou via Point-in-Time Recovery PITR).
  --action prune   : Aplica politica de retencao (padrao 30 dias) removendo backups expirados.
Zero travessoes em todo o script.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.backup_manager import (
    AuraBackupManager,
    BackupError,
    S3CloudSyncAdapter,
)


def build_arg_parser() -> argparse.ArgumentParser:
    """Constroi o parser de argumentos de linha de comando para backup_cloud_sync."""
    parser = argparse.ArgumentParser(
        prog="backup_cloud_sync",
        description="Orquestrador CLI de Backups Criptografados AES-256-GCM e Cloud Sync S3/R2 da AURA.",
    )
    parser.add_argument(
        "--action",
        choices=("backup", "restore", "verify", "prune"),
        default="backup",
        help="Operacao a ser executada: backup, restore, verify ou prune.",
    )
    parser.add_argument(
        "--sqlite-path",
        type=str,
        default=None,
        help="Caminho para o banco SQLite local de origem.",
    )
    parser.add_argument(
        "--backup-dir",
        type=str,
        default=None,
        help="Diretorio local de armazenamento dos pacotes criptografados (.enc).",
    )
    parser.add_argument(
        "--backup-file",
        type=str,
        default=None,
        help="Arquivo .enc especifico para as acoes verify ou restore.",
    )
    parser.add_argument(
        "--target-sqlite-path",
        type=str,
        default=None,
        help="Caminho SQLite de destino para a acao restore.",
    )
    parser.add_argument(
        "--restore-dir",
        type=str,
        default=None,
        help="Diretorio de destino para extrair manifesto e bundle vetorial no restore.",
    )
    parser.add_argument(
        "--pitr-timestamp",
        type=str,
        default=None,
        help="Timestamp ISO-8601 UTC alvo para Point-in-Time Recovery (PITR) na acao restore.",
    )
    parser.add_argument(
        "--passphrase",
        type=str,
        default=None,
        help="Passphrase secreta para derivacao PBKDF2HMAC-SHA256 da chave AES-256-GCM.",
    )
    parser.add_argument(
        "--compression",
        choices=("auto", "zst", "gz", "xz"),
        default="auto",
        help="Algoritmo de compressao do pacote TAR (padrao: auto).",
    )
    parser.add_argument(
        "--retention-days",
        type=int,
        default=30,
        help="Dias de retencao para expurgo de backups antigos na acao prune (padrao: 30).",
    )
    parser.add_argument(
        "--bucket",
        type=str,
        default="aura-backups-prod",
        help="Nome do bucket Amazon S3 / Cloudflare R2.",
    )
    parser.add_argument(
        "--endpoint-url",
        type=str,
        default=None,
        help="Endpoint HTTPS compativel com S3 / Cloudflare R2.",
    )
    parser.add_argument(
        "--local-bucket-dir",
        type=str,
        default=None,
        help="Diretorio de bucket local fallback para ambientes offline ou testes.",
    )
    parser.add_argument(
        "--no-cloud-sync",
        action="store_true",
        help="Desativa o upload para o bucket na nuvem durante a criacao do backup.",
    )
    parser.add_argument(
        "--filial-id",
        type=int,
        default=1,
        help="Identificador da filial (codfilial) associado ao backup (padrao: 1).",
    )
    parser.add_argument(
        "--tenant-id",
        type=str,
        default="default",
        help="Identificador do tenant associado ao backup.",
    )
    return parser


def _resolve_latest_backup_file(backup_dir: Path) -> Path:
    """Localiza o arquivo .enc mais recente no diretorio de backups."""
    candidates = sorted(backup_dir.glob("*.enc"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        raise BackupError(f"Nenhum arquivo de backup (.enc) encontrado em: {backup_dir}")
    return candidates[0]


def execute_backup_cli(argv: Sequence[str] | None = None) -> dict[str, Any]:
    """
    Executa a operacao solicitada via argumentos CLI e retorna um relatorio estruturado.
    """
    parser = build_arg_parser()
    parsed = parser.parse_args(argv)

    cloud_adapter = S3CloudSyncAdapter(
        bucket_name=parsed.bucket,
        endpoint_url=parsed.endpoint_url,
        local_bucket_dir=parsed.local_bucket_dir,
        prefix=f"{parsed.tenant_id}/filial_{parsed.filial_id}",
    )

    manager = AuraBackupManager(
        sqlite_db_path=parsed.sqlite_path,
        backup_dir=parsed.backup_dir,
        passphrase=parsed.passphrase,
        cloud_adapter=cloud_adapter,
        filial_id=parsed.filial_id,
        tenant_id=parsed.tenant_id,
    )

    action = parsed.action
    if action == "backup":
        op_result = manager.create_backup(
            compression=parsed.compression,
            sync_to_cloud=not parsed.no_cloud_sync,
        )
    elif action == "verify":
        target_enc = (
            Path(parsed.backup_file)
            if parsed.backup_file
            else _resolve_latest_backup_file(manager.backup_dir)
        )
        op_result = manager.verify_backup(backup_file=target_enc)
    elif action == "restore":
        if parsed.pitr_timestamp:
            op_result = manager.restore_pitr(
                target_timestamp=parsed.pitr_timestamp,
                target_sqlite_path=parsed.target_sqlite_path,
                restore_dir=parsed.restore_dir,
            )
        else:
            target_enc = (
                Path(parsed.backup_file)
                if parsed.backup_file
                else _resolve_latest_backup_file(manager.backup_dir)
            )
            op_result = manager.restore_backup(
                backup_file=target_enc,
                target_sqlite_path=parsed.target_sqlite_path,
                restore_dir=parsed.restore_dir,
            )
    elif action == "prune":
        op_result = manager.prune_expired_backups(
            retention_days=parsed.retention_days,
            include_cloud=not parsed.no_cloud_sync,
        )
    else:
        raise BackupError(f"Acao desconhecida: {action}")

    return {
        "action": action,
        "status": "ok",
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "filial_id": parsed.filial_id,
        "tenant_id": parsed.tenant_id,
        "result": op_result,
    }


def main(argv: Sequence[str] | None = None) -> int:
    """Ponto de entrada CLI com emissao de relatorio JSON estruturado."""
    try:
        report = execute_backup_cli(argv)
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0
    except (BackupError, OSError, ValueError) as exc:
        err_report = {
            "status": "error",
            "timestamp_utc": datetime.now(UTC).isoformat(),
            "error_type": type(exc).__name__,
            "message": str(exc),
        }
        print(json.dumps(err_report, indent=2, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
