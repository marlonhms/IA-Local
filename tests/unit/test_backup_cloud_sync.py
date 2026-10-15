"""
Suite de Testes Unitarios da Politica de Backups Automatizados, Criptografados (AES-256-GCM)
e Sincronizados em Nuvem S3 / Cloudflare R2 (Fase P2-3).
Valida snapshot SQLite, bundle vetorial, compressao (.tar.zst / .tar.gz / .tar.xz),
criptografia AES-256-GCM (PBKDF2HMAC SHA-256 + nonce 12B), deteccao de adulteracao de
ciphertext ou chave incorreta, restauracao identica em ambiente limpo, Point-in-Time
Recovery (PITR), retencao de 30 dias, upload S3/R2 com AWS Signature V4 e zero travessoes.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from config.settings import BASE_DIR
from core.backup_manager import (
    MAGIC_HEADER,
    AuraBackupManager,
    BackupEncryptionError,
    S3CloudSyncAdapter,
    extract_envelope_metadata,
)
from scripts.backup_cloud_sync import execute_backup_cli


def _create_sample_sqlite_db(db_path: Path, vouchers_count: int = 2) -> None:
    """Cria um banco SQLite populado com sessoes e Action Vouchers para teste de backup."""
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS aura_sessions ("
            "session_id TEXT PRIMARY KEY, "
            "tenant_id TEXT NOT NULL, "
            "filial_id INTEGER NOT NULL, "
            "messages_json TEXT NOT NULL"
            ")"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS aura_action_vouchers ("
            "voucher_id TEXT PRIMARY KEY, "
            "action_type TEXT NOT NULL, "
            "hmac_signature TEXT NOT NULL, "
            "created_at TEXT NOT NULL"
            ")"
        )
        conn.execute("DELETE FROM aura_sessions")
        conn.execute("DELETE FROM aura_action_vouchers")

        conn.execute(
            "INSERT INTO aura_sessions (session_id, tenant_id, filial_id, messages_json) "
            "VALUES (?, ?, ?, ?)",
            ("sess_001", "rede_aura", 1, '[{"role": "user", "content": "Fechamento turno 1"}]'),
        )
        for i in range(1, vouchers_count + 1):
            conn.execute(
                "INSERT INTO aura_action_vouchers (voucher_id, action_type, hmac_signature, created_at) "
                "VALUES (?, ?, ?, ?)",
                (
                    f"vch_{i:03d}",
                    "COMPRA_COMBUSTIVEL",
                    f"hmac_sha256_sig_{i:03d}",
                    f"2026-10-15T10:0{i}:00+00:00",
                ),
            )
        conn.commit()
    finally:
        conn.close()


@pytest.mark.unit
class TestBackupCloudSyncP23:
    """Testes unitarios para AuraBackupManager, S3CloudSyncAdapter e CLI backup_cloud_sync."""

    def test_create_backup_compression_and_encryption_aes256_gcm(
        self, tmp_path: Path
    ) -> None:
        """Valida criacao de backup, compressao (.tar.zst / .tar.gz) e criptografia AES-256-GCM."""
        sqlite_src = tmp_path / "source_memory.db"
        _create_sample_sqlite_db(sqlite_src, vouchers_count=3)

        backup_dir = tmp_path / "backups"
        local_bucket = tmp_path / "s3_local"
        cloud = S3CloudSyncAdapter(
            bucket_name="aura-test-bucket",
            local_bucket_dir=local_bucket,
        )
        manager = AuraBackupManager(
            sqlite_db_path=sqlite_src,
            backup_dir=backup_dir,
            passphrase="StrongSecretKey#2026!AES256",
            cloud_adapter=cloud,
            filial_id=1,
            tenant_id="posto_matriz",
            kdf_iterations=10_000,
        )

        vector_records: dict[str, list[dict[str, object]]] = {
            "intencoes_vetores": [
                {"id": 1, "intencao": "lmc_anp", "codfilial": 1},
                {"id": 2, "intencao": "auditoria_turno", "codfilial": 1},
            ],
            "produtos_vetores": [
                {"codpro": 101, "descricao": "GASOLINA COMUM", "codfilial": 1},
            ],
            "conhecimento_operacional": [
                {"id": 50, "titulo": "Portaria ANP 26/1992", "codfilial": 1},
            ],
        }

        for comp_mode in ("zst", "gz", "xz"):
            report = manager.create_backup(
                vector_records=vector_records,
                compression=comp_mode,
                sync_to_cloud=True,
            )
            assert report["status"] == "success"
            assert report["encryption"]["cipher"] == "AES-256-GCM"
            assert report["encryption"]["kdf"] == "PBKDF2HMAC-SHA256"
            assert report["encryption"]["nonce_bytes"] == 12
            assert report["encryption"]["salt_bytes"] == 16

            enc_file = Path(report["encrypted_file"])
            assert enc_file.exists()
            raw_bytes = enc_file.read_bytes()
            assert raw_bytes.startswith(MAGIC_HEADER)

            envelope_meta = extract_envelope_metadata(raw_bytes)
            assert envelope_meta["backup_id"] == report["backup_id"]
            assert envelope_meta["cipher"] == "AES-256-GCM"

            verification = manager.verify_backup(enc_file)
            assert verification["valid"] is True
            assert verification["sqlite_integrity"] == "ok"
            assert verification["manifest"]["sqlite_table_counts"]["aura_action_vouchers"] == 3
            assert verification["manifest"]["vector_table_counts"]["intencoes_vetores"] == 2

    def test_decryption_fails_on_wrong_key_or_tampered_ciphertext(
        self, tmp_path: Path
    ) -> None:
        """
        Comprova que chave incorreta, adulteracao de 1 bit no ciphertext ou
        adulteracao dos metadados AAD disparam BackupEncryptionError imediatamente.
        """
        sqlite_src = tmp_path / "source.db"
        _create_sample_sqlite_db(sqlite_src, vouchers_count=1)

        manager = AuraBackupManager(
            sqlite_db_path=sqlite_src,
            backup_dir=tmp_path / "backups",
            passphrase="CorrectMasterPassword_2026",
            kdf_iterations=10_000,
        )
        report = manager.create_backup(sync_to_cloud=False)
        enc_path = Path(report["encrypted_file"])

        # 1. Tentativa de verificacao ou restauracao com chave incorreta
        with pytest.raises(BackupEncryptionError):
            manager.verify_backup(enc_path, passphrase="WrongPassword_123")

        with pytest.raises(BackupEncryptionError):
            manager.restore_backup(
                enc_path,
                target_sqlite_path=tmp_path / "should_not_exist.db",
                passphrase="WrongPassword_123",
            )

        # 2. Adulteracao de 1 byte no final do ciphertext / GCM tag
        original_bytes = bytearray(enc_path.read_bytes())
        tampered_cipher = bytearray(original_bytes)
        tampered_cipher[-5] ^= 0xFF
        tampered_cipher_path = tmp_path / "tampered_ciphertext.enc"
        tampered_cipher_path.write_bytes(bytes(tampered_cipher))

        with pytest.raises(BackupEncryptionError):
            manager.verify_backup(tampered_cipher_path)

        # 3. Adulteracao de 1 byte dentro dos metadados AAD no cabecalho
        tampered_aad = bytearray(original_bytes)
        aad_start = len(MAGIC_HEADER) + 16 + 12 + 4
        tampered_aad[aad_start + 5] ^= 0x01
        tampered_aad_path = tmp_path / "tampered_aad.enc"
        tampered_aad_path.write_bytes(bytes(tampered_aad))

        with pytest.raises(BackupEncryptionError):
            manager.verify_backup(tampered_aad_path)

    def test_identical_restoration_in_clean_environment_and_pitr(
        self, tmp_path: Path
    ) -> None:
        """
        Valida restauracao identica em ambiente limpo e recuperacao Point-in-Time (PITR)
        entre multiplos snapshots em instantes distintos.
        """
        sqlite_src = tmp_path / "live_aura.db"
        backup_dir = tmp_path / "backups_pitr"
        manager = AuraBackupManager(
            sqlite_db_path=sqlite_src,
            backup_dir=backup_dir,
            passphrase="PITR_Secret_Key_2026",
            kdf_iterations=10_000,
        )

        # Snapshot T1 (10:00 UTC): 2 vouchers no banco
        t1 = datetime(2026, 10, 15, 10, 0, 0, tzinfo=UTC)
        _create_sample_sqlite_db(sqlite_src, vouchers_count=2)
        bkp_t1 = manager.create_backup(
            vector_records={"produtos_vetores": [{"codpro": 1, "codfilial": 1}]},
            sync_to_cloud=False,
            backup_timestamp=t1,
        )

        # Snapshot T2 (18:00 UTC): 5 vouchers no banco
        t2 = datetime(2026, 10, 15, 18, 0, 0, tzinfo=UTC)
        _create_sample_sqlite_db(sqlite_src, vouchers_count=5)
        bkp_t2 = manager.create_backup(
            vector_records={"produtos_vetores": [{"codpro": 1, "codfilial": 1}, {"codpro": 2, "codfilial": 1}]},
            sync_to_cloud=False,
            backup_timestamp=t2,
        )

        # Restauracao em ambiente limpo do backup T2
        clean_sqlite_t2 = tmp_path / "clean_env_t2" / "restored.db"
        clean_extract_t2 = tmp_path / "clean_env_t2" / "extracted"
        res_t2 = manager.restore_backup(
            backup_file=bkp_t2["encrypted_file"],
            target_sqlite_path=clean_sqlite_t2,
            restore_dir=clean_extract_t2,
        )
        assert res_t2["status"] == "restored"
        assert clean_sqlite_t2.exists()
        assert (clean_extract_t2 / "manifest.json").exists()
        assert len(res_t2["vector_bundle"]["tables"]["produtos_vetores"]) == 2

        conn_t2 = sqlite3.connect(str(clean_sqlite_t2))
        try:
            cnt_t2 = conn_t2.execute("SELECT COUNT(*) FROM aura_action_vouchers").fetchone()[0]
            assert cnt_t2 == 5
        finally:
            conn_t2.close()

        # Point-in-Time Recovery (PITR) para 12:30 UTC (deve selecionar automaticamente T1!)
        pitr_sqlite = tmp_path / "clean_env_pitr" / "restored_pitr.db"
        pitr_target = datetime(2026, 10, 15, 12, 30, 0, tzinfo=UTC)
        res_pitr = manager.restore_pitr(
            target_timestamp=pitr_target,
            target_sqlite_path=pitr_sqlite,
        )
        assert res_pitr["backup_id"] == bkp_t1["backup_id"]
        assert len(res_pitr["vector_bundle"]["tables"]["produtos_vetores"]) == 1

        conn_pitr = sqlite3.connect(str(pitr_sqlite))
        try:
            cnt_pitr = conn_pitr.execute("SELECT COUNT(*) FROM aura_action_vouchers").fetchone()[0]
            assert cnt_pitr == 2
        finally:
            conn_pitr.close()

    def test_retention_policy_30_days_prunes_expired_backups(
        self, tmp_path: Path
    ) -> None:
        """
        Valida que a politica de retencao de 30 dias remove backups com 45 e 31 dias
        e preserva backups com 29 dias e de hoje, tanto localmente quanto no bucket S3/R2.
        """
        sqlite_src = tmp_path / "retention_source.db"
        _create_sample_sqlite_db(sqlite_src, vouchers_count=1)

        cloud = S3CloudSyncAdapter(
            bucket_name="aura-retention-bucket",
            local_bucket_dir=tmp_path / "cloud_bucket",
        )
        manager = AuraBackupManager(
            sqlite_db_path=sqlite_src,
            backup_dir=tmp_path / "local_backups",
            passphrase="RetentionKey_2026",
            cloud_adapter=cloud,
            kdf_iterations=10_000,
        )

        ref_now = datetime(2026, 10, 15, 12, 0, 0, tzinfo=UTC)
        ages_days = [45, 31, 29, 0]
        for days_ago in ages_days:
            ts = ref_now - timedelta(days=days_ago)
            manager.create_backup(
                sync_to_cloud=True,
                backup_timestamp=ts,
            )

        assert len(list(manager.backup_dir.glob("*.enc"))) == 4
        assert len(cloud.list_backups()) == 4

        prune_report = manager.prune_expired_backups(retention_days=30, now=ref_now)
        assert prune_report["deleted_local_count"] == 2
        assert prune_report["retained_local_count"] == 2
        assert prune_report["cloud_prune"]["deleted_count"] == 2
        assert prune_report["cloud_prune"]["retained_count"] == 2

        assert len(list(manager.backup_dir.glob("*.enc"))) == 2
        assert len(cloud.list_backups()) == 2

    def test_s3_r2_sigv4_headers_and_cli_orchestration(
        self, tmp_path: Path
    ) -> None:
        """
        Valida a geracao da assinatura AWS Signature V4 para Cloudflare R2 / S3
        e testa o CLI scripts/backup_cloud_sync.py nas 4 operacoes (backup, verify, restore, prune).
        """
        remote_adapter = S3CloudSyncAdapter(
            bucket_name="aura-r2-prod",
            endpoint_url="https://acc999.r2.cloudflarestorage.com",
            access_key_id="AKIAIOSFODNN7EXAMPLE",
            secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            region="auto",
        )
        sample_file = tmp_path / "dummy.enc"
        sample_file.write_bytes(b"encrypted_payload_test")

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch("requests.put", return_value=mock_resp) as mocked_put:
            up_res = remote_adapter.upload_backup(sample_file, object_key="posto_1/dummy.enc")
            assert up_res["status"] == "uploaded"
            assert up_res["mode"] == "remote_s3_r2"
            auth_header = up_res["sigv4_headers"]["Authorization"]
            assert auth_header.startswith("AWS4-HMAC-SHA256 Credential=AKIAIOSFODNN7EXAMPLE/")
            assert "SignedHeaders=host;x-amz-content-sha256;x-amz-date" in auth_header
            assert "Signature=" in auth_header
            mocked_put.assert_called_once()

        # Testa o CLI completo (backup -> verify -> restore -> prune)
        sqlite_cli_db = tmp_path / "cli_source.db"
        _create_sample_sqlite_db(sqlite_cli_db, vouchers_count=4)
        cli_bkp_dir = tmp_path / "cli_backups"
        cli_bucket_dir = tmp_path / "cli_cloud"
        cli_restored_db = tmp_path / "cli_restored.db"

        common_args = [
            "--sqlite-path", str(sqlite_cli_db),
            "--backup-dir", str(cli_bkp_dir),
            "--local-bucket-dir", str(cli_bucket_dir),
            "--passphrase", "CLI_Secret_2026",
            "--filial-id", "1",
        ]

        res_backup = execute_backup_cli(["--action", "backup", *common_args])
        assert res_backup["status"] == "ok"
        created_enc = res_backup["result"]["encrypted_file"]

        res_verify = execute_backup_cli(
            ["--action", "verify", "--backup-file", created_enc, *common_args]
        )
        assert res_verify["result"]["valid"] is True

        res_restore = execute_backup_cli(
            [
                "--action", "restore",
                "--backup-file", created_enc,
                "--target-sqlite-path", str(cli_restored_db),
                *common_args,
            ]
        )
        assert res_restore["result"]["status"] == "restored"
        assert cli_restored_db.exists()

        res_prune = execute_backup_cli(
            ["--action", "prune", "--retention-days", "30", *common_args]
        )
        assert res_prune["result"]["retained_local_count"] == 1

    def test_zero_travessoes_in_p2_3_files(self) -> None:
        """Garante a regra inegociavel de ZERO travessoes nos arquivos do escopo P2-3."""
        em_dash = chr(0x2014)
        en_dash = chr(0x2013)
        files_to_check = [
            BASE_DIR / "core" / "backup_manager.py",
            BASE_DIR / "scripts" / "backup_cloud_sync.py",
            Path(__file__),
        ]
        for file_path in files_to_check:
            assert file_path.exists(), f"Arquivo esperado nao encontrado: {file_path}"
            content = file_path.read_text(encoding="utf-8")
            assert em_dash not in content, f"Travessao (0x2014) detectado em {file_path}"
            assert en_dash not in content, f"Travessao (0x2013) detectado em {file_path}"
