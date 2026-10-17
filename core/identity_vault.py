"""
Cofre Criptografico de Maquina via Windows DPAPI (core/identity_vault.py).
Implementa a Fase 2 do Roadmap Sentinel-AURA:
- Criptografia atrelada a chave de hardware do SO / chip TPM (CRYPTPROTECT_LOCAL_MACHINE)
- Eliminacao definitiva de senhas do ERP e segredos em texto claro no .env e arquivos .txt
- Persistencia binaria atomica com assinatura de integridade (AURAVAULT1)
- Suporte a multiplos segredos (erp_password, vector_password, voucher_secret, etc.)
- Fallback defensivo e portabilidade para testes multiplataforma (Linux / CI)
Regra inegociavel: ZERO travessoes em todo o arquivo.
"""

from __future__ import annotations

import base64
import ctypes
import hashlib
import json
import logging
import os
import shutil
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("aura.identity_vault")

MAGIC_HEADER = b"AURAVAULT1\0"
CRYPTPROTECT_LOCAL_MACHINE = 0x4
PROJECT_ROOT = Path(__file__).resolve().parent.parent


class _DataBlob(ctypes.Structure):
    _fields_ = [("cbData", ctypes.c_ulong), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]


def _build_data_blob(data: bytes) -> Tuple[_DataBlob, Any]:
    """Cria a estrutura DATA_BLOB para interoperabilidade com crypt32.dll."""
    buffer = (ctypes.c_ubyte * len(data)).from_buffer_copy(data)
    blob = _DataBlob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    return blob, buffer


def _protect_windows(data: bytes, entropy: bytes) -> bytes:
    """Criptografa bytes usando CryptProtectData com escopo de maquina local."""
    if os.name != "nt":
        raise OSError("DPAPI esta disponivel apenas no ambiente Windows.")
    source_blob, src_buf = _build_data_blob(data)
    extra_blob, ext_buf = _build_data_blob(entropy)
    output_blob = _DataBlob()

    if not ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(source_blob),
        "AURA Machine Vault Secret",
        ctypes.byref(extra_blob),
        None,
        None,
        CRYPTPROTECT_LOCAL_MACHINE,
        ctypes.byref(output_blob),
    ):
        raise ctypes.WinError()

    try:
        return ctypes.string_at(output_blob.pbData, output_blob.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(output_blob.pbData)
        del src_buf, ext_buf


def _unprotect_windows(data: bytes, entropy: bytes) -> bytes:
    """Descriptografa bytes usando CryptUnprotectData."""
    if os.name != "nt":
        raise OSError("DPAPI esta disponivel apenas no ambiente Windows.")
    source_blob, src_buf = _build_data_blob(data)
    extra_blob, ext_buf = _build_data_blob(entropy)
    output_blob = _DataBlob()

    if not ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(source_blob),
        None,
        ctypes.byref(extra_blob),
        None,
        None,
        0,
        ctypes.byref(output_blob),
    ):
        raise ctypes.WinError()

    try:
        return ctypes.string_at(output_blob.pbData, output_blob.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(output_blob.pbData)
        del src_buf, ext_buf


def _software_fallback_protect(data: bytes, entropy: bytes) -> bytes:
    """
    Fallback criptografico autenticado para hosts de teste nao-Windows (Linux / CI).
    Deriva uma chave pseudo-aleatoria estavel via PBKDF2 HMAC-SHA256 e cifra via XOR + HMAC.
    """
    salt = b"aura_software_fallback_salt_2026"
    key = hashlib.pbkdf2_hmac("sha256", entropy, salt, 10000, 32)
    # Keystream deterministico estendido
    keystream = bytearray()
    counter = 0
    while len(keystream) < len(data):
        keystream.extend(hashlib.sha256(key + counter.to_bytes(4, "big")).digest())
        counter += 1
    cipher = bytes(b ^ k for b, k in zip(data, keystream[: len(data)]))
    tag = hashlib.sha256(key + cipher).digest()
    return tag + cipher


def _software_fallback_unprotect(data: bytes, entropy: bytes) -> bytes:
    """Descriptografa payload produzido pelo fallback de software."""
    salt = b"aura_software_fallback_salt_2026"
    key = hashlib.pbkdf2_hmac("sha256", entropy, salt, 10000, 32)
    if len(data) < 32:
        raise ValueError("Payload de fallback corrompido ou truncado.")
    tag = data[:32]
    cipher = data[32:]
    expected_tag = hashlib.sha256(key + cipher).digest()
    if not (tag == expected_tag):
        raise ValueError("Integridade violada no fallback criptografico.")
    keystream = bytearray()
    counter = 0
    while len(keystream) < len(cipher):
        keystream.extend(hashlib.sha256(key + counter.to_bytes(4, "big")).digest())
        counter += 1
    return bytes(b ^ k for b, k in zip(cipher, keystream[: len(cipher)]))


class AuraIdentityVault:
    """
    Cofre de segredos e credenciais locais da AURA.
    Armazena senhas de banco e chaves de API cifradas com chave do chip TPM/SO da maquina.
    """

    def __init__(
        self,
        station_id: str = "default_station",
        vault_path: Optional[Path] = None,
        protect_fn: Optional[Callable[[bytes, bytes], bytes]] = None,
        unprotect_fn: Optional[Callable[[bytes, bytes], bytes]] = None,
    ) -> None:
        self.station_id = station_id
        safe_id = hashlib.sha256(station_id.encode("utf-8")).hexdigest()[:16]
        self.entropy = b"aura-station-vault-v1\0" + safe_id.encode("utf-8")

        if vault_path is not None:
            self.vault_path = Path(vault_path)
        else:
            self.vault_path = self._resolve_default_vault_path()

        if protect_fn is not None:
            self._protect = protect_fn
            self._unprotect = unprotect_fn or _unprotect_windows
        elif os.name == "nt":
            self._protect = _protect_windows
            self._unprotect = _unprotect_windows
        else:
            self._protect = _software_fallback_protect
            self._unprotect = _software_fallback_unprotect

    @staticmethod
    def _resolve_default_vault_path() -> Path:
        """
        Define o caminho padrao do cofre compartilhado da maquina.
        No Windows corporativo, %ProgramData%\\Aura\\vault\\vault.bin e compartilhado
        entre servicos da Sessao 0 (AuraBackendService) e console interativo da Sessao 1.
        """
        env_override = os.getenv("AURA_VAULT_PATH")
        if env_override:
            p = Path(env_override)
            p.parent.mkdir(parents=True, exist_ok=True)
            return p

        data_dir_override = os.getenv("AURA_DATA_DIR")
        if data_dir_override:
            p = Path(data_dir_override) / "vault" / "vault.bin"
            p.parent.mkdir(parents=True, exist_ok=True)
            return p

        if os.name == "nt":
            prog_data = os.getenv("PROGRAMDATA") or r"C:\ProgramData"
            p = Path(prog_data) / "Aura" / "vault" / "vault.bin"
            try:
                p.parent.mkdir(parents=True, exist_ok=True)
                return p
            except Exception:
                pass

        p = PROJECT_ROOT / "data" / "vault" / "vault.bin"
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def _load_vault_dict(self) -> Dict[str, str]:
        """Carrega e descriptografa o dicionario de segredos armazenado em disco."""
        if not self.vault_path.is_file():
            return {}

        try:
            raw_bytes = self.vault_path.read_bytes()
            if not raw_bytes.startswith(MAGIC_HEADER):
                logger.warning(
                    "Cofre em %s possui assinatura invalida ou incompativel.",
                    self.vault_path,
                )
                return {}

            ciphertext = raw_bytes[len(MAGIC_HEADER) :]
            decrypted_json_bytes = self._unprotect(ciphertext, self.entropy)
            data = json.loads(decrypted_json_bytes.decode("utf-8"))
            if isinstance(data, dict):
                return data
            return {}
        except Exception as exc:
            logger.warning(
                "Falha ao descriptografar cofre DPAPI em %s: %s",
                self.vault_path,
                exc,
            )
            return {}

    def _save_vault_dict(self, secrets_dict: Dict[str, str]) -> bool:
        """Criptografa e grava atomicamente o dicionario de segredos."""
        try:
            self.vault_path.parent.mkdir(parents=True, exist_ok=True)
            plain_bytes = json.dumps(
                secrets_dict, ensure_ascii=False, sort_keys=True
            ).encode("utf-8")
            ciphertext = self._protect(plain_bytes, self.entropy)

            temp_path = self.vault_path.with_suffix(f".{os.getpid()}.tmp")
            temp_path.write_bytes(MAGIC_HEADER + ciphertext)
            temp_path.replace(self.vault_path)
            return True
        except Exception as exc:
            logger.error(
                "Nao foi possivel proteger o cofre DPAPI em %s: %s",
                self.vault_path,
                exc,
            )
            return False

    def store_secret(self, key: str, value: str) -> bool:
        """Salva uma credencial de forma segura no cofre criptografado."""
        if not key or not isinstance(key, str):
            return False
        clean_key = key.strip().lower()
        clean_value = str(value).strip() if value is not None else ""

        current = self._load_vault_dict()
        current[clean_key] = clean_value
        return self._save_vault_dict(current)

    def get_secret(self, key: str) -> Optional[str]:
        """Recupera e descriptografa uma credencial pelo nome de chave."""
        if not key or not isinstance(key, str):
            return None
        clean_key = key.strip().lower()
        secrets = self._load_vault_dict()
        return secrets.get(clean_key)

    def has_secret(self, key: str) -> bool:
        """Verifica se uma determinada credencial esta presente no cofre."""
        val = self.get_secret(key)
        return bool(val)

    def delete_secret(self, key: str) -> bool:
        """Remove um segredo especifico do cofre."""
        if not key or not isinstance(key, str):
            return False
        clean_key = key.strip().lower()
        current = self._load_vault_dict()
        if clean_key in current:
            del current[clean_key]
            return self._save_vault_dict(current)
        return True

    def list_keys(self) -> List[str]:
        """Lista os nomes de chaves armazenadas no cofre sem expor os valores."""
        return sorted(list(self._load_vault_dict().keys()))

    def clear(self) -> bool:
        """Remove o arquivo fisico do cofre."""
        try:
            if self.vault_path.is_file():
                self.vault_path.unlink()
            return True
        except Exception as exc:
            logger.warning("Falha ao limpar cofre em %s: %s", self.vault_path, exc)
            return False


# Singleton Padrao do Cofre
_GLOBAL_VAULT: Optional[AuraIdentityVault] = None


def get_identity_vault() -> AuraIdentityVault:
    """Retorna a instancia compartilhada do cofre de identidade e credenciais."""
    global _GLOBAL_VAULT
    if _GLOBAL_VAULT is None:
        station_id = os.getenv("AURA_STATION_ID", "aura_station_host")
        _GLOBAL_VAULT = AuraIdentityVault(station_id=station_id)
    return _GLOBAL_VAULT


def store_vault_secret(key: str, value: str) -> bool:
    """Funcao utilitaria para armazenar um segredo no cofre padrao."""
    return get_identity_vault().store_secret(key, value)


def get_vault_secret(key: str) -> Optional[str]:
    """Funcao utilitaria para recuperar um segredo do cofre padrao."""
    return get_identity_vault().get_secret(key)


def has_vault_secret(key: str) -> bool:
    """Funcao utilitaria para checar se um segredo existe no cofre padrao."""
    return get_identity_vault().has_secret(key)


def list_vault_keys() -> List[str]:
    """Lista as chaves presentes no cofre padrao."""
    return get_identity_vault().list_keys()


def migrate_plain_text_passwords_to_vault() -> Dict[str, Any]:
    """
    Localiza senhas em texto claro em backups/erp_password.txt ou erp_password.txt,
    grava no cofre DPAPI e remove os arquivos legados com seguranca.
    """
    vault = get_identity_vault()
    migrated: List[str] = []

    candidatos = [
        PROJECT_ROOT / "backups" / "erp_password.txt",
        PROJECT_ROOT / "erp_password.txt",
        PROJECT_ROOT.parent / "erp_password.txt",
    ]

    for p in candidatos:
        if p.is_file():
            try:
                content = p.read_text(encoding="utf-8-sig").strip("\ufeff \r\n\t")
                if content:
                    vault.store_secret("erp_password", content)
                    migrated.append(str(p))
                p.unlink(missing_ok=True)
                logger.info(
                    "Credencial em texto claro em %s migrada para o cofre DPAPI e arquivo expurgado.",
                    p,
                )
            except Exception as exc:
                logger.warning(
                    "Falha ao migrar ou remover arquivo de senha %s: %s", p, exc
                )

    return {
        "migrated_count": len(migrated),
        "files_removed": migrated,
        "vault_ready": vault.has_secret("erp_password"),
    }
