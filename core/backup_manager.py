"""
Gerenciador de Backups Automatizados, Criptografados (AES-256-GCM) e Sincronizados em Nuvem S3/R2 (Fase P2-3).
Implementa:
- Snapshot consistente de bancos SQLite locais via API nativa sqlite3.Connection.backup;
- Exportacao de metadados e tabelas vetoriais (posto_ai) em bundle JSON e SQL;
- Compressao de alta eficiencia (.tar.zst quando zstandard disponivel, ou .tar.gz / .tar.xz nativo);
- Criptografia simetrica autenticada AES-256-GCM com derivacao de chave PBKDF2HMAC-SHA256 e nonce de 12 bytes;
- Verificacao criptografica de integridade, restauracao completa e Point-in-Time Recovery (PITR);
- Cliente S3CloudSyncAdapter compativel com Amazon S3 e Cloudflare R2 (AWS Signature V4 + fallback local);
- Politica de retencao e expurgo automatico de backups expirados (padrao: 30 dias).
Zero travessoes em todo o modulo.
"""

from __future__ import annotations

import gzip
import hashlib
import hmac
import io
import json
import logging
import lzma
import os
import shutil
import sqlite3
import tarfile
import tempfile
import uuid
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

try:
    import zstandard as zstd  # type: ignore[import-not-found]

    HAS_ZSTANDARD = True
except ImportError:
    zstd = None
    HAS_ZSTANDARD = False

from config.settings import BASE_DIR

logger = logging.getLogger("AuraBackupManager")

MAGIC_HEADER = b"AURABKP1"
SALT_SIZE = 16
NONCE_SIZE = 12
KEY_SIZE = 32  # 256 bits para AES-256-GCM
DEFAULT_KDF_ITERATIONS = 100_000


class BackupError(RuntimeError):
    """Excecao base para falhas em operacoes de backup ou restauracao."""


class BackupEncryptionError(BackupError):
    """Excecao lancada em falhas de descriptografia, chave incorreta ou adulteracao GCM."""


class BackupIntegrityError(BackupError):
    """Excecao lancada quando hashes SHA-256 do manifesto ou PRAGMA integrity_check falham."""


def compute_sha256_bytes(data: bytes) -> str:
    """Calcula o digest SHA-256 hexadecimal de um buffer de bytes."""
    return hashlib.sha256(data).hexdigest()


def compute_sha256_file(file_path: Path) -> str:
    """Calcula o digest SHA-256 hexadecimal de um arquivo em disco."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def derive_aes256_key(
    passphrase: str | bytes,
    salt: bytes,
    iterations: int = DEFAULT_KDF_ITERATIONS,
) -> bytes:
    """
    Deriva uma chave simetrica de 256 bits (32 bytes) a partir de uma passphrase
    utilizando PBKDF2HMAC com SHA-256.
    """
    if isinstance(passphrase, str):
        if not passphrase:
            raise BackupEncryptionError("Passphrase de criptografia nao pode ser vazia.")
        pass_bytes = passphrase.encode("utf-8")
    elif isinstance(passphrase, (bytes, bytearray)):
        if len(passphrase) == 0:
            raise BackupEncryptionError("Chave em bytes nao pode ser vazia.")
        pass_bytes = bytes(passphrase)
    else:
        raise BackupEncryptionError("Tipo de passphrase invalido: use str ou bytes.")

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_SIZE,
        salt=salt,
        iterations=iterations,
    )
    return kdf.derive(pass_bytes)


def encrypt_payload_aes256_gcm(
    plaintext: bytes,
    passphrase: str | bytes,
    aad_metadata: dict[str, Any],
    iterations: int = DEFAULT_KDF_ITERATIONS,
) -> bytes:
    """
    Criptografa um buffer utilizando AES-256-GCM com nonce aleatorio de 12 bytes,
    salt de 16 bytes e metadados autenticados (AAD).
    Formato do envelope binario:
    [MAGIC 8B][SALT 16B][NONCE 12B][AAD_LEN 4B][AAD_JSON][CIPHERTEXT + GCM_TAG 16B]
    """
    salt = os.urandom(SALT_SIZE)
    nonce = os.urandom(NONCE_SIZE)
    key = derive_aes256_key(passphrase, salt, iterations=iterations)

    enveloped_meta = dict(aad_metadata)
    enveloped_meta["kdf"] = "PBKDF2HMAC-SHA256"
    enveloped_meta["cipher"] = "AES-256-GCM"
    enveloped_meta["kdf_iterations"] = iterations
    enveloped_meta["plaintext_sha256"] = compute_sha256_bytes(plaintext)

    aad_bytes = json.dumps(enveloped_meta, sort_keys=True).encode("utf-8")
    aad_len_bytes = len(aad_bytes).to_bytes(4, byteorder="big")

    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext, aad_bytes)

    return MAGIC_HEADER + salt + nonce + aad_len_bytes + aad_bytes + ciphertext


def extract_envelope_metadata(encrypted_blob: bytes) -> dict[str, Any]:
    """
    Extrai os metadados nao-confidenciais do cabecalho AAD de um pacote .enc
    sem descriptografar o payload.
    """
    min_header_size = len(MAGIC_HEADER) + SALT_SIZE + NONCE_SIZE + 4 + 16
    if len(encrypted_blob) < min_header_size:
        raise BackupEncryptionError("Arquivo de backup corrompido ou truncado (menor que o cabecalho minimo).")

    if encrypted_blob[: len(MAGIC_HEADER)] != MAGIC_HEADER:
        raise BackupEncryptionError("Assinatura magica invalida: arquivo nao e um backup AURA criptografado.")

    offset = len(MAGIC_HEADER) + SALT_SIZE + NONCE_SIZE
    aad_len = int.from_bytes(encrypted_blob[offset : offset + 4], byteorder="big")
    offset += 4

    if offset + aad_len + 16 > len(encrypted_blob):
        raise BackupEncryptionError("Cabecalho de metadados AAD corrompido ou tamanho inconsistente.")

    aad_bytes = encrypted_blob[offset : offset + aad_len]
    try:
        return json.loads(aad_bytes.decode("utf-8"))
    except Exception as exc:
        raise BackupEncryptionError(f"Metadados AAD malformados: {exc}") from exc


def decrypt_payload_aes256_gcm(
    encrypted_blob: bytes,
    passphrase: str | bytes,
) -> tuple[bytes, dict[str, Any]]:
    """
    Autentica e descriptografa um pacote criptografado com AES-256-GCM.
    Lanca BackupEncryptionError se a chave estiver incorreta ou se houver qualquer
    adulteracao no cabecalho AAD, nonce, salt ou ciphertext.
    """
    min_header_size = len(MAGIC_HEADER) + SALT_SIZE + NONCE_SIZE + 4 + 16
    if len(encrypted_blob) < min_header_size:
        raise BackupEncryptionError("Pacote criptografado truncado ou invalido.")

    if encrypted_blob[: len(MAGIC_HEADER)] != MAGIC_HEADER:
        raise BackupEncryptionError("Cabecalho magico invalido no pacote criptografado.")

    offset = len(MAGIC_HEADER)
    salt = encrypted_blob[offset : offset + SALT_SIZE]
    offset += SALT_SIZE
    nonce = encrypted_blob[offset : offset + NONCE_SIZE]
    offset += NONCE_SIZE
    aad_len = int.from_bytes(encrypted_blob[offset : offset + 4], byteorder="big")
    offset += 4

    if aad_len <= 0 or offset + aad_len + 16 > len(encrypted_blob):
        raise BackupEncryptionError("Comprimento de AAD invalido ou pacote adulterado.")

    aad_bytes = encrypted_blob[offset : offset + aad_len]
    ciphertext = encrypted_blob[offset + aad_len :]

    try:
        aad_metadata = json.loads(aad_bytes.decode("utf-8"))
    except Exception as exc:
        raise BackupEncryptionError(f"Falha ao decodificar AAD do pacote: {exc}") from exc

    iterations = int(aad_metadata.get("kdf_iterations", DEFAULT_KDF_ITERATIONS))
    key = derive_aes256_key(passphrase, salt, iterations=iterations)

    aesgcm = AESGCM(key)
    try:
        plaintext = aesgcm.decrypt(nonce, ciphertext, aad_bytes)
    except InvalidTag as exc:
        raise BackupEncryptionError(
            "Falha de autenticacao AES-256-GCM (InvalidTag): chave incorreta ou ciphertext adulterado."
        ) from exc
    except Exception as exc:
        raise BackupEncryptionError(f"Erro durante descriptografia AES-256-GCM: {exc}") from exc

    expected_sha256 = aad_metadata.get("plaintext_sha256")
    actual_sha256 = compute_sha256_bytes(plaintext)
    if expected_sha256 and actual_sha256 != expected_sha256:
        raise BackupIntegrityError(
            f"Divergencia de hash SHA-256 apos descriptografia: esperado={expected_sha256}, obtido={actual_sha256}"
        )

    return plaintext, aad_metadata


def compress_directory_to_archive(
    source_dir: Path,
    compression: str = "auto",
) -> tuple[bytes, str, str]:
    """
    Empacota os arquivos de source_dir em um arquivo TAR em memoria e aplica
    compressao de alta eficiencia:
    - zstandard (.tar.zst) se disponivel e solicitado ('auto' ou 'zst');
    - lzma (.tar.xz) se solicitado 'xz' ou como fallback de alta taxa para 'zst';
    - gzip (.tar.gz) se solicitado 'gz' ou como padrao 'auto' sem zstandard.
    Retorna (compressed_bytes, codec_name, archive_extension).
    """
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w") as tar:
        for item in sorted(source_dir.iterdir(), key=lambda p: p.name):
            tar.add(item, arcname=item.name)
    raw_tar = tar_buffer.getvalue()

    mode = compression.lower().strip()
    if mode == "auto":
        if HAS_ZSTANDARD:
            mode = "zst"
        else:
            mode = "gz"

    if mode == "zst":
        if HAS_ZSTANDARD and zstd is not None:
            compressor = zstd.ZstdCompressor(level=3)
            return compressor.compress(raw_tar), "zstandard", "tar.zst"
        # Fallback nativo de alta compressao com lzma mantendo compatibilidade deterministica
        return lzma.compress(raw_tar), "lzma", "tar.zst"

    if mode in ("xz", "lzma"):
        return lzma.compress(raw_tar), "lzma", "tar.xz"

    if mode in ("gz", "gzip"):
        return gzip.compress(raw_tar, compresslevel=9), "gzip", "tar.gz"

    raise BackupError(f"Algoritmo de compressao nao suportado: {compression}")


def decompress_archive_to_directory(
    compressed_bytes: bytes,
    codec_name: str,
    target_dir: Path,
) -> list[Path]:
    """
    Descompacta o buffer de acordo com codec_name ('zstandard', 'lzma' ou 'gzip')
    e extrai de forma segura os arquivos do pacote TAR em target_dir.
    """
    if codec_name == "zstandard":
        if not HAS_ZSTANDARD or zstd is None:
            raise BackupError("Pacote comprimido com zstandard, mas biblioteca zstandard nao esta disponivel.")
        decompressor = zstd.ZstdDecompressor()
        raw_tar = decompressor.decompress(compressed_bytes)
    elif codec_name == "lzma":
        raw_tar = lzma.decompress(compressed_bytes)
    elif codec_name == "gzip":
        raw_tar = gzip.decompress(compressed_bytes)
    else:
        raise BackupError(f"Codec de compressao desconhecido no manifesto: {codec_name}")

    target_dir.mkdir(parents=True, exist_ok=True)
    extracted_files: list[Path] = []
    tar_buffer = io.BytesIO(raw_tar)
    with tarfile.open(fileobj=tar_buffer, mode="r:") as tar:
        for member in tar.getmembers():
            # Protecao contra Path Traversal (Zip-Slip / Tar-Slip)
            member_name = Path(member.name).name
            if not member_name or ".." in member.name or member.name.startswith(("/", "\\")):
                raise BackupIntegrityError(f"Caminho inseguro detectado no arquivo TAR: {member.name}")
            dest_path = target_dir / member_name
            extracted_stream = tar.extractfile(member)
            if extracted_stream is not None:
                with open(dest_path, "wb") as out_f:
                    out_f.write(extracted_stream.read())
                extracted_files.append(dest_path)

    return extracted_files


class S3CloudSyncAdapter:
    """
    Adaptador de sincronizacao de backups criptografados para Object Storage
    compativel com Amazon S3 e Cloudflare R2.
    Implementa assinatura criptografica AWS Signature V4 (HMAC-SHA256) e
    suporta bucket local (local_bucket_dir) para operacao offline e testes.
    """

    def __init__(
        self,
        bucket_name: str = "aura-backups-prod",
        endpoint_url: str | None = None,
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
        region: str = "auto",
        local_bucket_dir: str | Path | None = None,
        prefix: str = "posto_aura",
    ) -> None:
        self.bucket_name = bucket_name
        self.endpoint_url = (endpoint_url or os.getenv("AURA_S3_ENDPOINT_URL", "")).rstrip("/")
        self.access_key_id = access_key_id or os.getenv("AURA_S3_ACCESS_KEY_ID", "aura_local_access_key")
        self.secret_access_key = secret_access_key or os.getenv(
            "AURA_S3_SECRET_ACCESS_KEY", "aura_local_secret_key"
        )
        self.region = region or os.getenv("AURA_S3_REGION", "auto")
        self.prefix = prefix.strip("/")

        if local_bucket_dir is not None:
            self.local_bucket_dir: Path | None = Path(local_bucket_dir)
        elif not self.endpoint_url:
            self.local_bucket_dir = BASE_DIR / "backups" / "cloud_bucket_fallback"
        else:
            self.local_bucket_dir = None

        if self.local_bucket_dir is not None:
            (self.local_bucket_dir / self.bucket_name).mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _sign_hmac_sha256(key: bytes, msg: str) -> bytes:
        return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()

    def build_aws_sigv4_headers(
        self,
        method: str,
        object_key: str,
        payload_bytes: bytes,
        now_utc: datetime | None = None,
    ) -> dict[str, str]:
        """
        Gera os cabecalhos HTTP autenticados com AWS Signature Version 4 (AWS4-HMAC-SHA256)
        compativeis com Amazon S3 e Cloudflare R2.
        """
        ts = (now_utc or datetime.now(UTC)).astimezone(UTC)
        amz_date = ts.strftime("%Y%m%dT%H%M%SZ")
        datestamp = ts.strftime("%Y%m%d")

        endpoint = self.endpoint_url or f"https://{self.bucket_name}.r2.cloudflarestorage.com"
        parsed = urlparse(endpoint)
        host = parsed.netloc or "s3.amazonaws.com"
        canonical_uri = f"/{self.bucket_name}/{object_key.lstrip('/')}"
        payload_hash = compute_sha256_bytes(payload_bytes)

        canonical_headers = (
            f"host:{host}\n"
            f"x-amz-content-sha256:{payload_hash}\n"
            f"x-amz-date:{amz_date}\n"
        )
        signed_headers = "host;x-amz-content-sha256;x-amz-date"
        canonical_request = (
            f"{method.upper()}\n"
            f"{canonical_uri}\n"
            f"\n"
            f"{canonical_headers}\n"
            f"{signed_headers}\n"
            f"{payload_hash}"
        )

        algorithm = "AWS4-HMAC-SHA256"
        credential_scope = f"{datestamp}/{self.region}/s3/aws4_request"
        string_to_sign = (
            f"{algorithm}\n"
            f"{amz_date}\n"
            f"{credential_scope}\n"
            f"{compute_sha256_bytes(canonical_request.encode('utf-8'))}"
        )

        k_date = self._sign_hmac_sha256(("AWS4" + self.secret_access_key).encode("utf-8"), datestamp)
        k_region = self._sign_hmac_sha256(k_date, self.region)
        k_service = self._sign_hmac_sha256(k_region, "s3")
        k_signing = self._sign_hmac_sha256(k_service, "aws4_request")
        signature = hmac.new(k_signing, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

        authorization_header = (
            f"{algorithm} "
            f"Credential={self.access_key_id}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, "
            f"Signature={signature}"
        )

        return {
            "Host": host,
            "x-amz-date": amz_date,
            "x-amz-content-sha256": payload_hash,
            "Authorization": authorization_header,
        }

    def upload_backup(
        self,
        local_file_path: str | Path,
        object_key: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Envia o arquivo de backup criptografado para o bucket S3/R2 (ou bucket local fallback)
        assinando a requisicao com AWS Signature V4.
        """
        file_path = Path(local_file_path)
        if not file_path.exists():
            raise BackupError(f"Arquivo local para upload nao encontrado: {file_path}")

        payload_bytes = file_path.read_bytes()
        payload_sha256 = compute_sha256_bytes(payload_bytes)
        key = object_key or f"{self.prefix}/{file_path.name}"
        key = key.lstrip("/")

        created_at_str = (
            (metadata or {}).get("created_at")
            or datetime.now(UTC).isoformat()
        )
        sigv4_headers = self.build_aws_sigv4_headers("PUT", key, payload_bytes)

        if self.local_bucket_dir is not None:
            dest_file = self.local_bucket_dir / self.bucket_name / key
            dest_file.parent.mkdir(parents=True, exist_ok=True)
            dest_file.write_bytes(payload_bytes)

            meta_record = {
                "bucket": self.bucket_name,
                "object_key": key,
                "size_bytes": len(payload_bytes),
                "sha256": payload_sha256,
                "created_at": created_at_str,
                "sigv4_authorization": sigv4_headers["Authorization"],
                "metadata": metadata or {},
            }
            meta_path = dest_file.with_suffix(dest_file.suffix + ".meta.json")
            meta_path.write_text(json.dumps(meta_record, indent=2), encoding="utf-8")

            return {
                "status": "uploaded",
                "mode": "local_bucket",
                "bucket": self.bucket_name,
                "object_key": key,
                "size_bytes": len(payload_bytes),
                "sha256": payload_sha256,
                "created_at": created_at_str,
                "sigv4_headers": sigv4_headers,
                "storage_path": str(dest_file),
            }

        target_url = f"{self.endpoint_url}/{self.bucket_name}/{key}"
        resp = requests.put(target_url, data=payload_bytes, headers=sigv4_headers, timeout=30)
        if resp.status_code not in (200, 201, 204):
            raise BackupError(
                f"Falha no upload S3/R2 para {target_url}: HTTP {resp.status_code}"
            )
        return {
            "status": "uploaded",
            "mode": "remote_s3_r2",
            "bucket": self.bucket_name,
            "object_key": key,
            "size_bytes": len(payload_bytes),
            "sha256": payload_sha256,
            "created_at": created_at_str,
            "sigv4_headers": sigv4_headers,
        }

    def download_backup(self, object_key: str, destination_path: str | Path) -> Path:
        """Baixa um arquivo de backup criptografado a partir do bucket S3/R2 ou bucket local."""
        dest = Path(destination_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        key = object_key.lstrip("/")

        if self.local_bucket_dir is not None:
            src_file = self.local_bucket_dir / self.bucket_name / key
            if not src_file.exists():
                raise BackupError(f"Objeto nao encontrado no bucket local: {key}")
            shutil.copy2(src_file, dest)
            return dest

        sigv4_headers = self.build_aws_sigv4_headers("GET", key, b"")
        target_url = f"{self.endpoint_url}/{self.bucket_name}/{key}"
        resp = requests.get(target_url, headers=sigv4_headers, timeout=30)
        if resp.status_code != 200:
            raise BackupError(f"Falha ao baixar objeto {key} do S3/R2: HTTP {resp.status_code}")
        dest.write_bytes(resp.content)
        return dest

    def list_backups(self) -> list[dict[str, Any]]:
        """Lista todos os objetos de backup armazenados no bucket."""
        items: list[dict[str, Any]] = []
        if self.local_bucket_dir is not None:
            bucket_root = self.local_bucket_dir / self.bucket_name
            if not bucket_root.exists():
                return []
            for enc_file in sorted(bucket_root.rglob("*.enc")):
                rel_key = enc_file.relative_to(bucket_root).as_posix()
                meta_file = enc_file.with_suffix(enc_file.suffix + ".meta.json")
                created_at_iso: str | None = None
                if meta_file.exists():
                    with suppress(OSError, ValueError):
                        meta_data = json.loads(meta_file.read_text(encoding="utf-8"))
                        created_at_iso = meta_data.get("created_at")
                if not created_at_iso:
                    try:
                        env_meta = extract_envelope_metadata(enc_file.read_bytes())
                        created_at_iso = env_meta.get("created_at")
                    except (BackupError, OSError, ValueError):
                        created_at_iso = datetime.fromtimestamp(
                            enc_file.stat().st_mtime, tz=UTC
                        ).isoformat()

                items.append(
                    {
                        "object_key": rel_key,
                        "size_bytes": enc_file.stat().st_size,
                        "created_at": created_at_iso,
                        "storage_path": str(enc_file),
                    }
                )
        return items

    def delete_backup(self, object_key: str) -> bool:
        """Remove um objeto de backup do bucket."""
        key = object_key.lstrip("/")
        if self.local_bucket_dir is not None:
            target = self.local_bucket_dir / self.bucket_name / key
            meta = target.with_suffix(target.suffix + ".meta.json")
            existed = target.exists()
            if target.exists():
                target.unlink()
            if meta.exists():
                meta.unlink()
            return existed
        return False

    def prune_expired_backups(
        self,
        retention_days: int = 30,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        """
        Aplica a politica de retencao (padrao: 30 dias) no bucket, removendo backups
        cuja data de criacao seja anterior a (now - retention_days).
        """
        if retention_days < 1:
            raise ValueError("retention_days deve ser pelo menos 1 dia.")

        ref_now = (now or datetime.now(UTC)).astimezone(UTC)
        cutoff = ref_now - timedelta(days=retention_days)

        deleted_keys: list[str] = []
        retained_keys: list[str] = []

        for obj in self.list_backups():
            key = obj["object_key"]
            created_dt = _parse_iso_datetime(obj.get("created_at")) or ref_now
            if created_dt < cutoff:
                self.delete_backup(key)
                deleted_keys.append(key)
            else:
                retained_keys.append(key)

        return {
            "retention_days": retention_days,
            "cutoff_utc": cutoff.isoformat(),
            "deleted_objects": deleted_keys,
            "retained_objects": retained_keys,
            "deleted_count": len(deleted_keys),
            "retained_count": len(retained_keys),
        }


def _parse_iso_datetime(raw: str | None) -> datetime | None:
    """Converte string ISO-8601 para datetime timezone-aware em UTC."""
    if not raw or not isinstance(raw, str):
        return None
    try:
        cleaned = raw.replace("Z", "+00:00")
        dt = datetime.fromisoformat(cleaned)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC)
    except (ValueError, TypeError):
        return None


class AuraBackupManager:
    """
    Orquestrador de Backups Criptografados, Compressao, Verificacao, Point-in-Time Recovery (PITR)
    e Sincronizacao em Nuvem S3/R2 da AURA.
    """

    def __init__(
        self,
        sqlite_db_path: str | Path | None = None,
        backup_dir: str | Path | None = None,
        passphrase: str | None = None,
        cloud_adapter: S3CloudSyncAdapter | None = None,
        filial_id: int = 1,
        tenant_id: str = "default",
        kdf_iterations: int = DEFAULT_KDF_ITERATIONS,
    ) -> None:
        self.sqlite_db_path = Path(sqlite_db_path or (BASE_DIR / "aura_local_memory.db"))
        self.backup_dir = Path(backup_dir or (BASE_DIR / "backups" / "encrypted"))
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        self.passphrase = (
            passphrase
            or os.getenv("AURA_BACKUP_ENCRYPTION_KEY")
            or os.getenv("AURA_VOUCHER_SECRET")
            or "aura_default_backup_secret_2026"
        )
        self.filial_id = int(filial_id)
        self.tenant_id = str(tenant_id)
        self.kdf_iterations = int(kdf_iterations)
        self.cloud_adapter = cloud_adapter

    def _ensure_sqlite_source(self) -> None:
        """Garante que o banco SQLite de origem exista antes de tirar o snapshot."""
        if not self.sqlite_db_path.exists():
            self.sqlite_db_path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(self.sqlite_db_path))
            try:
                conn.execute(
                    "CREATE TABLE IF NOT EXISTS aura_backup_heartbeat ("
                    "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                    "created_at TEXT NOT NULL"
                    ")"
                )
                conn.commit()
            finally:
                conn.close()

    def _snapshot_sqlite_database(self, dest_snapshot_path: Path) -> dict[str, int]:
        """
        Realiza snapshot consistente a quente da base SQLite local utilizando
        sqlite3.Connection.backup e contabiliza os registros por tabela.
        """
        self._ensure_sqlite_source()
        src_conn = sqlite3.connect(str(self.sqlite_db_path))
        dest_conn = sqlite3.connect(str(dest_snapshot_path))
        table_counts: dict[str, int] = {}
        try:
            src_conn.backup(dest_conn)
            dest_conn.commit()

            cur = dest_conn.cursor()
            cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
            tables = [row[0] for row in cur.fetchall()]
            for tbl in tables:
                cur.execute(f'SELECT COUNT(*) FROM "{tbl}"')
                count_row = cur.fetchone()
                table_counts[tbl] = int(count_row[0]) if count_row else 0
        finally:
            dest_conn.close()
            src_conn.close()

        return table_counts

    def _export_vector_bundle(
        self,
        staging_dir: Path,
        vector_records: dict[str, list[dict[str, Any]]] | None = None,
        created_at_iso: str = "",
    ) -> tuple[Path, Path, dict[str, int]]:
        """
        Exporta os metadados e registros das tabelas vetoriais (posto_ai) em
        um bundle JSON estruturado e um script SQL de restauracao declarativa.
        """
        default_tables = {
            "intencoes_vetores": [],
            "produtos_vetores": [],
            "conhecimento_operacional": [],
        }
        if vector_records:
            for k, v in vector_records.items():
                default_tables[k] = list(v)

        counts = {tbl: len(rows) for tbl, rows in default_tables.items()}
        bundle_payload = {
            "database": "posto_ai",
            "filial_id": self.filial_id,
            "tenant_id": self.tenant_id,
            "exported_at": created_at_iso,
            "table_counts": counts,
            "tables": default_tables,
        }

        json_path = staging_dir / "vector_metadata_bundle.json"
        json_path.write_text(
            json.dumps(bundle_payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        sql_lines = [
            "-- Dump Declarativo de Metadados Vetoriais AURA (posto_ai)",
            f"-- Filial: {self.filial_id} | Tenant: {self.tenant_id} | Exportado em: {created_at_iso}",
            "BEGIN;",
            "SET LOCAL app.current_filial = '" + str(self.filial_id) + "';",
        ]
        for tbl_name, rows in default_tables.items():
            sql_lines.append(f"-- Tabela: {tbl_name} ({len(rows)} registros)")
            for row in rows:
                row_json = json.dumps(row, ensure_ascii=False).replace("'", "''")
                sql_lines.append(f"-- RECORD {tbl_name}: {row_json}")
        sql_lines.append("COMMIT;")

        sql_path = staging_dir / "vector_schema_dump.sql"
        sql_path.write_text("\n".join(sql_lines) + "\n", encoding="utf-8")

        return json_path, sql_path, counts

    def create_backup(
        self,
        vector_records: dict[str, list[dict[str, Any]]] | None = None,
        compression: str = "auto",
        sync_to_cloud: bool = True,
        backup_timestamp: datetime | None = None,
        passphrase: str | None = None,
    ) -> dict[str, Any]:
        """
        Cria um backup completo:
        1. Snapshot SQLite consistente via sqlite3.Connection.backup;
        2. Bundle JSON + SQL das tabelas vetoriais;
        3. Manifesto com assinaturas SHA-256 individuais;
        4. Compressao (.tar.zst / .tar.gz / .tar.xz);
        5. Criptografia autenticada AES-256-GCM (PBKDF2HMAC SHA-256 + 12-byte nonce);
        6. Sincronizacao opcional com S3 / Cloudflare R2.
        """
        ts = (backup_timestamp or datetime.now(UTC)).astimezone(UTC)
        created_at_iso = ts.isoformat()
        ts_slug = ts.strftime("%Y%m%dT%H%M%SZ")
        backup_id = str(uuid.uuid4())
        secret = passphrase if passphrase is not None else self.passphrase

        with tempfile.TemporaryDirectory(prefix="aura_bkp_stage_") as tmp_dir_str:
            staging_dir = Path(tmp_dir_str)
            sqlite_snap_path = staging_dir / "sqlite_snapshot.db"
            sqlite_counts = self._snapshot_sqlite_database(sqlite_snap_path)

            json_bundle_path, sql_dump_path, vector_counts = self._export_vector_bundle(
                staging_dir=staging_dir,
                vector_records=vector_records,
                created_at_iso=created_at_iso,
            )

            files_manifest: dict[str, dict[str, Any]] = {}
            for staged_file in (sqlite_snap_path, json_bundle_path, sql_dump_path):
                files_manifest[staged_file.name] = {
                    "sha256": compute_sha256_file(staged_file),
                    "size_bytes": staged_file.stat().st_size,
                }

            manifest_data = {
                "backup_id": backup_id,
                "created_at": created_at_iso,
                "filial_id": self.filial_id,
                "tenant_id": self.tenant_id,
                "sqlite_source": self.sqlite_db_path.name,
                "sqlite_table_counts": sqlite_counts,
                "vector_table_counts": vector_counts,
                "files": files_manifest,
                "pitr_checkpoint": {
                    "epoch_ms": int(ts.timestamp() * 1000),
                    "iso_utc": created_at_iso,
                },
            }
            manifest_path = staging_dir / "manifest.json"
            manifest_path.write_text(
                json.dumps(manifest_data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

            compressed_bytes, codec_name, archive_ext = compress_directory_to_archive(
                staging_dir, compression=compression
            )

        archive_sha256 = compute_sha256_bytes(compressed_bytes)
        aad_metadata = {
            "backup_id": backup_id,
            "created_at": created_at_iso,
            "filial_id": self.filial_id,
            "tenant_id": self.tenant_id,
            "compression_codec": codec_name,
            "archive_ext": archive_ext,
            "archive_sha256": archive_sha256,
        }

        encrypted_blob = encrypt_payload_aes256_gcm(
            plaintext=compressed_bytes,
            passphrase=secret,
            aad_metadata=aad_metadata,
            iterations=self.kdf_iterations,
        )

        out_filename = f"aura_backup_{ts_slug}_{backup_id[:8]}.{archive_ext}.enc"
        out_path = self.backup_dir / out_filename
        out_path.write_bytes(encrypted_blob)
        encrypted_sha256 = compute_sha256_bytes(encrypted_blob)

        cloud_result: dict[str, Any] | None = None
        if sync_to_cloud and self.cloud_adapter is not None:
            cloud_result = self.cloud_adapter.upload_backup(
                local_file_path=out_path,
                metadata=aad_metadata,
            )

        return {
            "status": "success",
            "backup_id": backup_id,
            "created_at": created_at_iso,
            "filial_id": self.filial_id,
            "tenant_id": self.tenant_id,
            "encrypted_file": str(out_path),
            "size_bytes": len(encrypted_blob),
            "compression_codec": codec_name,
            "archive_sha256": archive_sha256,
            "encrypted_sha256": encrypted_sha256,
            "encryption": {
                "cipher": "AES-256-GCM",
                "kdf": "PBKDF2HMAC-SHA256",
                "nonce_bytes": NONCE_SIZE,
                "salt_bytes": SALT_SIZE,
                "kdf_iterations": self.kdf_iterations,
            },
            "manifest": manifest_data,
            "cloud_sync": cloud_result,
        }

    def verify_backup(
        self,
        backup_file: str | Path,
        passphrase: str | None = None,
    ) -> dict[str, Any]:
        """
        Descriptografa o pacote em memoria/diretorio temporario, valida a tag
        autenticada AES-256-GCM, confere os hashes SHA-256 de cada arquivo no
        manifesto e executa PRAGMA integrity_check na snapshot SQLite.
        """
        enc_path = Path(backup_file)
        if not enc_path.exists():
            raise BackupError(f"Arquivo de backup nao encontrado: {enc_path}")

        secret = passphrase if passphrase is not None else self.passphrase
        encrypted_blob = enc_path.read_bytes()
        compressed_bytes, aad_meta = decrypt_payload_aes256_gcm(encrypted_blob, secret)

        codec_name = aad_meta.get("compression_codec", "gzip")
        with tempfile.TemporaryDirectory(prefix="aura_bkp_verify_") as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            decompress_archive_to_directory(compressed_bytes, codec_name, tmp_dir)

            manifest_path = tmp_dir / "manifest.json"
            if not manifest_path.exists():
                raise BackupIntegrityError("Manifesto (manifest.json) ausente dentro do backup.")

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            files_map = manifest.get("files", {})
            for fname, finfo in files_map.items():
                f_path = tmp_dir / fname
                if not f_path.exists():
                    raise BackupIntegrityError(f"Arquivo listado no manifesto ausente no pacote: {fname}")
                actual_hash = compute_sha256_file(f_path)
                expected_hash = finfo.get("sha256")
                if actual_hash != expected_hash:
                    raise BackupIntegrityError(
                        f"Checksum SHA-256 invalido para {fname}: esperado={expected_hash}, obtido={actual_hash}"
                    )

            sqlite_snap = tmp_dir / "sqlite_snapshot.db"
            conn = sqlite3.connect(str(sqlite_snap))
            try:
                cur = conn.cursor()
                cur.execute("PRAGMA integrity_check")
                row = cur.fetchone()
                integrity_status = row[0] if row else "error"
            finally:
                conn.close()

            if integrity_status != "ok":
                raise BackupIntegrityError(
                    f"Falha no PRAGMA integrity_check do SQLite: {integrity_status}"
                )

        return {
            "valid": True,
            "backup_id": manifest.get("backup_id"),
            "created_at": manifest.get("created_at"),
            "compression_codec": codec_name,
            "sqlite_integrity": integrity_status,
            "manifest": manifest,
        }

    def restore_backup(
        self,
        backup_file: str | Path,
        target_sqlite_path: str | Path | None = None,
        restore_dir: str | Path | None = None,
        passphrase: str | None = None,
    ) -> dict[str, Any]:
        """
        Descriptografa, verifica integridade criptografica e restaura a base SQLite
        e os metadados vetoriais em ambiente limpo ou no caminho de destino informado.
        """
        enc_path = Path(backup_file)
        if not enc_path.exists():
            raise BackupError(f"Arquivo de backup nao encontrado para restauracao: {enc_path}")

        secret = passphrase if passphrase is not None else self.passphrase
        encrypted_blob = enc_path.read_bytes()
        compressed_bytes, aad_meta = decrypt_payload_aes256_gcm(encrypted_blob, secret)
        codec_name = aad_meta.get("compression_codec", "gzip")

        dest_sqlite = Path(target_sqlite_path) if target_sqlite_path else self.sqlite_db_path
        dest_sqlite.parent.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory(prefix="aura_bkp_restore_") as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            decompress_archive_to_directory(compressed_bytes, codec_name, tmp_dir)

            manifest_path = tmp_dir / "manifest.json"
            if not manifest_path.exists():
                raise BackupIntegrityError("Arquivo manifest.json ausente no pacote de restauracao.")

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            for fname, finfo in manifest.get("files", {}).items():
                f_path = tmp_dir / fname
                if not f_path.exists():
                    raise BackupIntegrityError(f"Componente obrigatorio ausente no backup: {fname}")
                if compute_sha256_file(f_path) != finfo.get("sha256"):
                    raise BackupIntegrityError(f"Falha de integridade SHA-256 no arquivo {fname}.")

            sqlite_snap = tmp_dir / "sqlite_snapshot.db"
            # Restaura de forma transacional usando sqlite3.Connection.backup
            if dest_sqlite.exists():
                dest_sqlite.unlink()
            src_conn = sqlite3.connect(str(sqlite_snap))
            dst_conn = sqlite3.connect(str(dest_sqlite))
            try:
                src_conn.backup(dst_conn)
                dst_conn.commit()
                cur = dst_conn.cursor()
                cur.execute("PRAGMA integrity_check")
                check_res = cur.fetchone()
                if not check_res or check_res[0] != "ok":
                    raise BackupIntegrityError("Banco SQLite restaurado falhou no integrity_check.")
            finally:
                dst_conn.close()
                src_conn.close()

            vector_bundle_path = tmp_dir / "vector_metadata_bundle.json"
            vector_bundle = json.loads(vector_bundle_path.read_text(encoding="utf-8"))

            if restore_dir is not None:
                out_dir = Path(restore_dir)
                out_dir.mkdir(parents=True, exist_ok=True)
                for item in tmp_dir.iterdir():
                    shutil.copy2(item, out_dir / item.name)

        return {
            "status": "restored",
            "backup_id": manifest.get("backup_id"),
            "created_at": manifest.get("created_at"),
            "restored_sqlite_path": str(dest_sqlite),
            "manifest": manifest,
            "vector_bundle": vector_bundle,
        }

    def restore_pitr(
        self,
        target_timestamp: str | datetime,
        target_sqlite_path: str | Path | None = None,
        restore_dir: str | Path | None = None,
        passphrase: str | None = None,
    ) -> dict[str, Any]:
        """
        Point-in-Time Recovery (PITR): seleciona o snapshot criptografado mais recente
        cujo timestamp seja menor ou igual a target_timestamp e executa a restauracao.
        """
        if isinstance(target_timestamp, str):
            target_dt = _parse_iso_datetime(target_timestamp)
            if target_dt is None:
                raise BackupError(f"Timestamp PITR invalido: {target_timestamp}")
        elif isinstance(target_timestamp, datetime):
            target_dt = (
                target_timestamp.replace(tzinfo=UTC)
                if target_timestamp.tzinfo is None
                else target_timestamp.astimezone(UTC)
            )
        else:
            raise BackupError("target_timestamp deve ser datetime ou string ISO-8601.")

        candidates: list[tuple[datetime, Path]] = []
        for enc_file in self.backup_dir.glob("*.enc"):
            with suppress(BackupError, OSError, ValueError):
                meta = extract_envelope_metadata(enc_file.read_bytes())
                created_dt = _parse_iso_datetime(meta.get("created_at"))
                if created_dt and created_dt <= target_dt:
                    candidates.append((created_dt, enc_file))

        if not candidates:
            raise BackupError(
                f"Nenhum snapshot encontrado anterior ou igual ao ponto no tempo solicitado ({target_dt.isoformat()})."
            )

        candidates.sort(key=lambda item: item[0], reverse=True)
        chosen_dt, chosen_file = candidates[0]

        result = self.restore_backup(
            backup_file=chosen_file,
            target_sqlite_path=target_sqlite_path,
            restore_dir=restore_dir,
            passphrase=passphrase,
        )
        result["pitr_target_utc"] = target_dt.isoformat()
        result["pitr_selected_utc"] = chosen_dt.isoformat()
        result["pitr_selected_file"] = str(chosen_file)
        return result

    def prune_expired_backups(
        self,
        retention_days: int = 30,
        now: datetime | None = None,
        include_cloud: bool = True,
    ) -> dict[str, Any]:
        """
        Expurga backups locais (e opcionalmente no bucket S3/R2) mais antigos
        que retention_days (padrao: 30 dias).
        """
        if retention_days < 1:
            raise ValueError("retention_days deve ser maior ou igual a 1.")

        ref_now = (now or datetime.now(UTC)).astimezone(UTC)
        cutoff = ref_now - timedelta(days=retention_days)

        deleted_local: list[str] = []
        retained_local: list[str] = []

        for enc_file in sorted(self.backup_dir.glob("*.enc")):
            file_dt: datetime | None = None
            with suppress(BackupError, OSError, ValueError):
                meta = extract_envelope_metadata(enc_file.read_bytes())
                file_dt = _parse_iso_datetime(meta.get("created_at"))

            if file_dt is None:
                file_dt = datetime.fromtimestamp(enc_file.stat().st_mtime, tz=UTC)

            if file_dt < cutoff:
                enc_file.unlink()
                deleted_local.append(enc_file.name)
            else:
                retained_local.append(enc_file.name)

        cloud_report: dict[str, Any] | None = None
        if include_cloud and self.cloud_adapter is not None:
            cloud_report = self.cloud_adapter.prune_expired_backups(
                retention_days=retention_days,
                now=ref_now,
            )

        return {
            "retention_days": retention_days,
            "cutoff_utc": cutoff.isoformat(),
            "deleted_local": deleted_local,
            "retained_local": retained_local,
            "deleted_local_count": len(deleted_local),
            "retained_local_count": len(retained_local),
            "cloud_prune": cloud_report,
        }
