"""
Testes Unitarios da Fase 2 (Roadmap Sentinel-AURA):
Cofre Criptografico de Maquina via Windows DPAPI & Eliminacao de Senhas em Texto Claro.

Valida:
1. Operacoes CRUD basicas do cofre (store_secret, get_secret, has_secret, list_keys, delete_secret).
2. Protecao criptografica autenticada: assinatura de integridade AURAVAULT1 e nao exposicao de texto claro no arquivo em disco.
3. Tratamento resiliente de cofres com cabecalho corrompido, adulterado ou truncado.
4. Funcoes globais utilitarias e singleton (get_identity_vault, store_vault_secret, get_vault_secret).
5. Auto-migracao e expurgo fisico de arquivos legados de senha (.txt).
6. Integracao de config/settings.py (get_erp_password) com o cofre DPAPI e marcador DPAPI_ENCRYPTED.
7. Integracao de scripts/solicitar_senha_erp.py (salvar_senha) com persistencia segura no cofre.
8. Ausencia total de travessoes (\\u2014, \\u2013) em todo o codigo da Fase 2.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict

import pytest

import config.settings as aura_settings
from core.identity_vault import (
    MAGIC_HEADER,
    AuraIdentityVault,
    _software_fallback_protect,
    _software_fallback_unprotect,
    get_identity_vault,
    get_vault_secret,
    has_vault_secret,
    list_vault_keys,
    migrate_plain_text_passwords_to_vault,
    store_vault_secret,
)


@pytest.fixture(autouse=True)
def _reset_global_identity_vault() -> Any:
    """Garante isolamento estrito entre testes resetando o singleton global do cofre."""
    import core.identity_vault as idv_mod

    idv_mod._GLOBAL_VAULT = None
    yield
    idv_mod._GLOBAL_VAULT = None


@pytest.fixture
def temp_vault(tmp_path: Path) -> AuraIdentityVault:
    """Instancia um cofre isolado em diretorio temporario para testes unitarios."""
    vault_file = tmp_path / "vault_test.bin"
    return AuraIdentityVault(station_id="test_posto_unit", vault_path=vault_file)


class TestAuraIdentityVaultBasics:
    """Testa operacoes fundamentais de armazenamento e recuperacao de credenciais."""

    def test_store_and_retrieve_secret(self, temp_vault: AuraIdentityVault) -> None:
        assert temp_vault.store_secret("erp_password", "senha_super_secreta_123") is True
        assert temp_vault.has_secret("erp_password") is True
        assert temp_vault.get_secret("erp_password") == "senha_super_secreta_123"

    def test_case_insensitivity_and_whitespace_trimming(
        self, temp_vault: AuraIdentityVault
    ) -> None:
        temp_vault.store_secret("  ERP_PASSWORD  ", "  minha_senha_456  ")
        assert temp_vault.has_secret("erp_password") is True
        assert temp_vault.get_secret("ERP_PASSWORD") == "minha_senha_456"

    def test_multiple_independent_secrets(self, temp_vault: AuraIdentityVault) -> None:
        temp_vault.store_secret("erp_password", "pass_erp")
        temp_vault.store_secret("vector_password", "pass_vector")
        temp_vault.store_secret("voucher_secret", "pass_voucher")

        keys = temp_vault.list_keys()
        assert keys == ["erp_password", "vector_password", "voucher_secret"]
        assert temp_vault.get_secret("erp_password") == "pass_erp"
        assert temp_vault.get_secret("vector_password") == "pass_vector"
        assert temp_vault.get_secret("voucher_secret") == "pass_voucher"

    def test_delete_secret(self, temp_vault: AuraIdentityVault) -> None:
        temp_vault.store_secret("temp_token", "abc123xyz")
        assert temp_vault.has_secret("temp_token") is True

        assert temp_vault.delete_secret("temp_token") is True
        assert temp_vault.has_secret("temp_token") is False
        assert temp_vault.get_secret("temp_token") is None

    def test_clear_vault_file(self, temp_vault: AuraIdentityVault) -> None:
        temp_vault.store_secret("key1", "val1")
        assert temp_vault.vault_path.is_file()

        assert temp_vault.clear() is True
        assert not temp_vault.vault_path.is_file()
        assert temp_vault.get_secret("key1") is None


class TestAuraIdentityVaultSecurityAndResilience:
    """Testa a protecao criptografica e resiliencia contra dados adulterados."""

    def test_raw_bytes_on_disk_do_not_contain_plaintext(
        self, temp_vault: AuraIdentityVault
    ) -> None:
        plain_secret = "palavra_secreta_comprovada_998877"
        temp_vault.store_secret("teste_chave", plain_secret)

        raw_bytes = temp_vault.vault_path.read_bytes()
        # Valida presenca da assinatura magica
        assert raw_bytes.startswith(MAGIC_HEADER)
        # Garante que a senha em texto claro NAO esta exposta no arquivo fisico
        assert plain_secret.encode("utf-8") not in raw_bytes

    def test_corrupted_magic_header_handling(
        self, temp_vault: AuraIdentityVault
    ) -> None:
        temp_vault.store_secret("chave_valida", "valor123")
        # Sobrescreve com cabecalho invalido
        temp_vault.vault_path.write_bytes(b"INVALID_HEADER_GARBAGE_12345")

        # Nao deve lancar excecao fatal, deve retornar dicionario vazio
        assert temp_vault.get_secret("chave_valida") is None
        assert temp_vault.list_keys() == []

    def test_tampered_ciphertext_handling(self, temp_vault: AuraIdentityVault) -> None:
        temp_vault.store_secret("chave_valida", "valor123")
        raw = temp_vault.vault_path.read_bytes()
        # Adulterar bytes finais do payload criptografado
        tampered = bytearray(raw)
        tampered[-4:] = b"\xff\x00\xaa\xbb"
        temp_vault.vault_path.write_bytes(bytes(tampered))

        assert temp_vault.get_secret("chave_valida") is None

    def test_software_fallback_roundtrip(self) -> None:
        data = b'{"erp_password": "fallback_segredo_2026"}'
        entropy = b"aura_test_entropy_123"

        cipher = _software_fallback_protect(data, entropy)
        assert data not in cipher

        decrypted = _software_fallback_unprotect(cipher, entropy)
        assert decrypted == data

    def test_software_fallback_tamper_detection(self) -> None:
        data = b"dados_confidenciais"
        entropy = b"entropy_salt"
        cipher = bytearray(_software_fallback_protect(data, entropy))

        # Altera um byte do ciphertext
        cipher[-1] ^= 0x01
        with pytest.raises(ValueError):
            _software_fallback_unprotect(bytes(cipher), entropy)


class TestAuraIdentityVaultHelpersAndMigration:
    """Testa utilitarios globais e processo de auto-migracao de arquivos legados."""

    def test_global_vault_helpers(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        test_vault_path = tmp_path / "global_vault.bin"
        monkeypatch.setenv("AURA_VAULT_PATH", str(test_vault_path))

        # Reset singleton global
        import core.identity_vault as idv_mod

        idv_mod._GLOBAL_VAULT = None

        assert store_vault_secret("token_global", "global_secret_xyz") is True
        assert has_vault_secret("token_global") is True
        assert get_vault_secret("token_global") == "global_secret_xyz"
        assert "token_global" in list_vault_keys()

    def test_migrate_plain_text_passwords_to_vault(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        test_vault_path = tmp_path / "migration_vault.bin"
        monkeypatch.setenv("AURA_VAULT_PATH", str(test_vault_path))

        import core.identity_vault as idv_mod

        idv_mod._GLOBAL_VAULT = None

        # Cria arquivo legado simulado
        fake_root = tmp_path / "project_root"
        fake_backups = fake_root / "backups"
        fake_backups.mkdir(parents=True, exist_ok=True)
        legacy_file = fake_backups / "erp_password.txt"
        legacy_file.write_text("senha_legada_12345", encoding="utf-8")

        monkeypatch.setattr(idv_mod, "PROJECT_ROOT", fake_root)

        res = migrate_plain_text_passwords_to_vault()

        assert res["migrated_count"] >= 1
        assert str(legacy_file) in res["files_removed"]
        # O arquivo legado DEVE ter sido expurgado do disco
        assert not legacy_file.exists()
        # A senha DEVE estar acessivel no cofre DPAPI
        assert get_vault_secret("erp_password") == "senha_legada_12345"


class TestSettingsAndScriptIntegration:
    """Testa integracao de get_erp_password() e salvar_senha()."""

    def test_get_erp_password_prioritizes_vault(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        test_vault_path = tmp_path / "settings_vault.bin"
        monkeypatch.setenv("AURA_VAULT_PATH", str(test_vault_path))
        monkeypatch.delenv("CI", raising=False)
        monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

        import core.identity_vault as idv_mod

        idv_mod._GLOBAL_VAULT = None
        store_vault_secret("erp_password", "senha_dpapi_prioritaria")

        monkeypatch.setenv("ERP_DB_PASSWORD", "DPAPI_ENCRYPTED")
        monkeypatch.setenv("ERP_SERVICE_PASS", "DPAPI_ENCRYPTED")

        pwd = aura_settings.get_erp_password()
        assert pwd == "senha_dpapi_prioritaria"

    def test_salvar_senha_in_scripts(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        test_vault_path = tmp_path / "script_vault.bin"
        monkeypatch.setenv("AURA_VAULT_PATH", str(test_vault_path))

        import core.identity_vault as idv_mod

        idv_mod._GLOBAL_VAULT = None

        fake_root = tmp_path / "fake_script_root"
        fake_root.mkdir(parents=True, exist_ok=True)
        env_file = fake_root / ".env"
        env_file.write_text("ERP_DB_PASSWORD=senha_antiga_clara\nERP_SERVICE_PASS=senha_antiga_clara\n", encoding="utf-8")

        fake_backups = fake_root / "backups"
        fake_backups.mkdir(parents=True, exist_ok=True)
        legacy_txt = fake_backups / "erp_password.txt"
        legacy_txt.write_text("senha_antiga_clara", encoding="utf-8")

        import scripts.solicitar_senha_erp as script_mod

        monkeypatch.setattr(script_mod, "ROOT_DIR", fake_root)
        monkeypatch.setattr(script_mod, "ENV_PATH", env_file)
        monkeypatch.setattr(script_mod, "BACKUP_PASS_PATH", legacy_txt)

        script_mod.salvar_senha("nova_senha_homologada_8899")

        # Verifica gravacao no cofre
        assert get_vault_secret("erp_password") == "nova_senha_homologada_8899"

        # Verifica atualizacao do .env com o marcador DPAPI_ENCRYPTED
        env_content = env_file.read_text(encoding="utf-8")
        assert "ERP_DB_PASSWORD=DPAPI_ENCRYPTED" in env_content
        assert "ERP_SERVICE_PASS=DPAPI_ENCRYPTED" in env_content
        assert "nova_senha_homologada_8899" not in env_content

        # Verifica expurgo fisico do arquivo .txt
        assert not legacy_txt.exists()


class TestZeroForbiddenDashesPhase2:
    """Garante ausencia total de travessoes (\\u2014, \\u2013) em todos os arquivos da Fase 2."""

    def test_no_forbidden_dashes_in_phase2_artifacts(self) -> None:
        target_files = [
            Path("core/identity_vault.py"),
            Path("config/settings.py"),
            Path("scripts/solicitar_senha_erp.py"),
            Path("tests/unit/test_identity_vault_dpapi.py"),
        ]

        violations = []
        for p in target_files:
            assert p.exists(), f"Arquivo obrigatorio nao encontrado: {p}"
            text = p.read_text(encoding="utf-8", errors="ignore")
            if "\u2014" in text or "\u2013" in text:
                violations.append(str(p))

        assert not violations, f"Arquivos com travessoes proibidos: {violations}"
