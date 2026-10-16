"""
Testes unitarios para o Ecossistema do Instalador Automatizado de 1-Clique (Windows).

Valida:
1. `PostoInstallerWizard` (`core/installer_wizard.py`):
   - Geracao de segredos criptograficos de 256 bits e provisionamento idempotente do `.env`
   - Checagens de pre-requisitos (Preflight Checks: Python, assets offline, Alembic e LGPD)
   - Aplicacao de migracoes declarativas Alembic em SQLite isolado
   - Registro automatico do Opt-In de conformidade LGPD
   - Deteccao de interfaces de rede (LAN e Tailscale)
   - Execucao completa `run_full_setup` e emissao do recibo `install_receipt.json`
2. `scripts/instalar_posto.ps1`:
   - Conformidade estrita com ASCII puro (`ord(c) < 128`, regra `powershell-windows`)
   - Presenca dos 8 estagios de provisionamento e execucao real em modo `-DryRun`
3. `INSTALAR_POSTO_1_CLIQUE.bat`:
   - Existencia, conformidade ASCII e chamada ao script PowerShell
4. Regra inegociavel de ZERO travessoes (`\\u2014`, `\\u2013`).
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from core.installer_wizard import (
    ERP_SAFE_DRIVER_OPTIONS,
    PROJECT_ROOT,
    PostoInstallerWizard,
    main,
)


def test_generate_env_secrets_entropy() -> None:
    """Garante que os segredos gerados possuem entropia criptografica de 256 bits."""
    secrets_map = PostoInstallerWizard.generate_env_secrets()
    assert len(secrets_map["AURA_VOUCHER_SECRET"]) == 64
    assert secrets_map["AURA_API_KEY"].startswith("aura_live_")
    assert len(secrets_map["AURA_API_KEY"]) >= 58
    assert len(secrets_map["AURA_BACKUP_ENCRYPTION_KEY"]) == 64


def test_provision_env_file_idempotent(tmp_path: Path) -> None:
    """Garante criacao e atualizacao idempotente do .env preservando segredos validos."""
    env_file = tmp_path / ".env"
    wizard = PostoInstallerWizard(env_path=env_file)

    # 1. Criacao inicial do .env
    res1 = wizard.provision_env_file(filial_id=3, tenant_id="rede_sul", api_port=8000)
    assert res1["created_or_updated"] is True
    assert res1["secrets_ready"] is True
    assert res1["filial_id"] == 3
    assert res1["tenant_id"] == "rede_sul"
    assert env_file.is_file()

    content1 = env_file.read_text(encoding="utf-8")
    assert 'ERP_DB_USER="aura_service_ro"' in content1
    assert f'ERP_DB_OPTIONS="{ERP_SAFE_DRIVER_OPTIONS}"' in content1

    # Extrai o AURA_VOUCHER_SECRET gerado na primeira execucao
    voucher_lines = [
        line for line in content1.splitlines() if line.startswith("AURA_VOUCHER_SECRET=")
    ]
    assert len(voucher_lines) == 1
    first_secret = voucher_lines[0]

    # 2. Segunda execucao deve preservar o segredo ja existente
    wizard.provision_env_file(filial_id=3, tenant_id="rede_sul", api_port=8000)
    content2 = env_file.read_text(encoding="utf-8")
    assert first_secret in content2


def test_preflight_checks_on_project_root() -> None:
    """Verifica que o preflight no repositorio real aprova Python, assets offline, Alembic e LGPD."""
    wizard = PostoInstallerWizard(project_root=PROJECT_ROOT)
    checks = wizard.run_preflight_checks()
    assert checks["python_ok"] is True
    assert checks["offline_assets_ok"] is True
    assert checks["missing_offline_assets"] == []
    assert checks["alembic_config_ok"] is True
    assert checks["compliance_term_ok"] is True
    assert checks["all_passed"] is True


def test_full_setup_and_receipt_generation(tmp_path: Path) -> None:
    """Testa o fluxo ponta-a-ponta do Wizard em banco e arquivos isolados em tmp_path."""
    env_file = tmp_path / ".env"
    db_file = tmp_path / "data" / "aura_local_memory.db"
    comp_file = tmp_path / "data" / "compliance_opt_in.json"
    receipt_file = tmp_path / "data" / "install_receipt.json"

    wizard = PostoInstallerWizard(
        project_root=PROJECT_ROOT,
        env_path=env_file,
        db_path=db_file,
        compliance_json_path=comp_file,
        receipt_path=receipt_file,
    )

    receipt = wizard.run_full_setup(
        loja_cnpj="12.345.678/0001-99",
        razao_social="Auto Posto Estrela do Sul LTDA",
        assinado_por="Engenheiro Responsavel",
        filial_id=2,
        tenant_id="estrela_sul",
        api_port=8000,
    )

    assert receipt["status"] == "installed"
    assert receipt["database_migrations"]["current_revision"] == "0002_compliance"
    assert receipt["database_migrations"]["is_valid"] is True
    assert receipt["compliance_opt_in"]["status"] == "active"
    assert receipt["compliance_opt_in"]["loja_cnpj"] == "12.345.678/0001-99"
    assert receipt["endpoints"]["localhost_url"] == "http://localhost:8000"
    assert receipt_file.is_file()

    saved_receipt = json.loads(receipt_file.read_text(encoding="utf-8"))
    assert saved_receipt["status"] == "installed"


def test_cli_main_json_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Valida a execucao via CLI (`--json`) redirecionando artefatos para `tmp_path`."""
    orig_init = PostoInstallerWizard.__init__

    def _patched_init(self: PostoInstallerWizard, *args: object, **kwargs: object) -> None:
        orig_init(
            self,
            project_root=PROJECT_ROOT,
            env_path=tmp_path / ".env",
            db_path=tmp_path / "aura_cli.db",
            compliance_json_path=tmp_path / "compliance_cli.json",
            receipt_path=tmp_path / "receipt_cli.json",
        )

    monkeypatch.setattr(PostoInstallerWizard, "__init__", _patched_init)

    exit_code = main(
        [
            "--cnpj",
            "98.765.432/0001-10",
            "--razao-social",
            "Posto CLI Teste LTDA",
            "--filial-id",
            "5",
            "--json",
        ]
    )
    assert exit_code == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["status"] == "installed"
    assert payload["environment"]["filial_id"] == 5


def test_powershell_script_pure_ascii_and_stages() -> None:
    """Garante que `scripts/instalar_posto.ps1` e 100% ASCII puro e contem os 8 estagios."""
    ps1_path = PROJECT_ROOT / "scripts" / "instalar_posto.ps1"
    assert ps1_path.is_file(), "Script scripts/instalar_posto.ps1 nao encontrado"

    content = ps1_path.read_text(encoding="utf-8")
    non_ascii = [
        (idx, ch, ord(ch))
        for idx, ch in enumerate(content)
        if ord(ch) >= 128
    ]
    assert non_ascii == [], f"Caracteres nao-ASCII encontrados no PowerShell: {non_ascii[:5]}"

    for step in range(1, 9):
        assert f'Write-Stage "{step}/8"' in content, f"Estagio {step}/8 ausente no script PS1"

    assert "core.installer_wizard" in content
    assert "New-NetFirewallRule" in content
    assert "aura_service_ro" in content


def test_powershell_script_dry_run_execution() -> None:
    """Executa `scripts/instalar_posto.ps1 -DryRun` no PowerShell real e valida saida limpa."""
    ps_bin = shutil.which("powershell.exe")
    if sys.platform != "win32" or not ps_bin:
        pytest.skip("powershell.exe nao disponivel neste ambiente de execucao (requer Windows)")

    ps1_path = PROJECT_ROOT / "scripts" / "instalar_posto.ps1"
    proc = subprocess.run(
        [
            ps_bin,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(ps1_path),
            "-DryRun",
        ],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert proc.returncode == 0, f"Falha no DryRun: {proc.stderr}\n{proc.stdout}"
    assert "INSTALACAO 1-CLIQUE CONCLUIDA COM SUCESSO!" in proc.stdout
    assert "[1/8]" in proc.stdout
    assert "[8/8]" in proc.stdout


def test_batch_launcher_structure_and_ascii() -> None:
    """Valida o atalho `INSTALAR_POSTO_1_CLIQUE.bat` na raiz do projeto."""
    bat_path = PROJECT_ROOT / "INSTALAR_POSTO_1_CLIQUE.bat"
    assert bat_path.is_file(), "Atalho INSTALAR_POSTO_1_CLIQUE.bat nao encontrado"

    content = bat_path.read_text(encoding="utf-8")
    assert all(ord(c) < 128 for c in content), "INSTALAR_POSTO_1_CLIQUE.bat deve ser ASCII puro"
    assert "scripts\\instalar_posto.ps1" in content


def test_zero_em_dashes_in_installer_files() -> None:
    """Garante ausencia absoluta de travessoes nos arquivos do instalador 1-clique."""
    target_files = [
        PROJECT_ROOT / "core" / "installer_wizard.py",
        PROJECT_ROOT / "scripts" / "instalar_posto.ps1",
        PROJECT_ROOT / "INSTALAR_POSTO_1_CLIQUE.bat",
        Path(__file__),
    ]
    for path in target_files:
        text = path.read_text(encoding="utf-8")
        assert "\u2014" not in text, f"Travessao longo detectado em {path.name}"
        assert "\u2013" not in text, f"Travessao medio detectado em {path.name}"
