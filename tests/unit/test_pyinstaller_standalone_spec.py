"""
Testes Unitarios da Distribuicao Binaria Standalone via PyInstaller (Fase 8).
Valida manifesto AuraBackend.spec, scripts de compilacao automatizada e instalador
de um clique para estacoes de postos sem dependencia de Python.
Zero travessoes em todo o arquivo.
"""

import ast
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def test_aurabackend_spec_syntax_and_structure():
    """Valida sintaxe Python e presenca dos blocos principais no AuraBackend.spec."""
    spec_path = PROJECT_ROOT / "AuraBackend.spec"
    assert spec_path.is_file(), "AuraBackend.spec nao encontrado na raiz do projeto"

    spec_text = spec_path.read_text(encoding="utf-8")
    parsed_ast = ast.parse(spec_text)
    assert parsed_ast is not None, "Falha ao analisar AST de AuraBackend.spec"

    assert "Analysis" in spec_text
    assert "PYZ" in spec_text
    assert "EXE" in spec_text
    assert "COLLECT" in spec_text
    assert "name='AuraBackend'" in spec_text or 'name="AuraBackend"' in spec_text


def test_aurabackend_spec_hidden_imports():
    """Valida presenca dos modulos vitais em hiddenimports do AuraBackend.spec."""
    spec_path = PROJECT_ROOT / "AuraBackend.spec"
    spec_text = spec_path.read_text(encoding="utf-8")

    essential_modules = [
        "win32service",
        "win32serviceutil",
        "servicemanager",
        "uvicorn",
        "fastapi",
        "pydantic",
        "psycopg2",
        "sqlite3",
        "core.service",
        "core.identity_vault",
        "core.resource_watchdog",
        "core.desktop_notifier",
        "core.outbox",
        "core.command_journal",
        "core.aura_api",
        "core.db_pool",
    ]

    for mod in essential_modules:
        assert f"'{mod}'" in spec_text or f'"{mod}"' in spec_text, f"Modulo oculto obrigatorio ausente: {mod}"


def test_aurabackend_spec_datas():
    """Valida inclusao de diretorios de assets e configuracoes no pacote standalone."""
    spec_path = PROJECT_ROOT / "AuraBackend.spec"
    spec_text = spec_path.read_text(encoding="utf-8")

    assert "('web', 'web')" in spec_text or '("web", "web")' in spec_text
    assert "('config/erp_mappings', 'config/erp_mappings')" in spec_text or '("config/erp_mappings", "config/erp_mappings")' in spec_text


def test_build_aura_standalone_script_structure():
    """Valida presenca e integridade do script de compilacao PowerShell."""
    build_script = PROJECT_ROOT / "scripts" / "build_aura_standalone.ps1"
    assert build_script.is_file(), "scripts/build_aura_standalone.ps1 nao encontrado"

    content = build_script.read_text(encoding="utf-8")
    assert "PyInstaller" in content
    assert "AuraBackend.spec" in content
    assert "dist\\AuraBackend\\AuraBackend.exe" in content
    assert "$Clean" in content


def test_installer_bat_structure():
    """Valida presenca e comandos do instalador autonomo Instalar-Aura.bat."""
    installer_path = PROJECT_ROOT / "scripts" / "installer" / "Instalar-Aura.bat"
    assert installer_path.is_file(), "scripts/installer/Instalar-Aura.bat nao encontrado"

    bat_text = installer_path.read_text(encoding="utf-8", errors="ignore")
    assert "net session" in bat_text, "Verificacao de UAC ausente no instalador"
    assert "Start-Process" in bat_text, "Auto-elevacao de Administrador ausente"
    assert "AuraBackendService" in bat_text, "Nome do servico SCM ausente"
    assert "--install-service" in bat_text, "Flag de instalacao de servico ausente"
    assert "--start-service" in bat_text or "sc.exe start" in bat_text, "Comando de inicio de servico ausente"
    assert "netsh advfirewall firewall" in bat_text, "Regra de Firewall ausente"
    assert "http://localhost:8000" in bat_text, "URL inicial do navegador ausente"


def test_zero_dashes_enforcement_fase8():
    """Garante ausencia inegociavel de travessoes nos arquivos da Fase 8."""
    files_to_check = [
        PROJECT_ROOT / "AuraBackend.spec",
        PROJECT_ROOT / "scripts" / "build_aura_standalone.ps1",
        PROJECT_ROOT / "scripts" / "installer" / "Instalar-Aura.bat",
        Path(__file__),
    ]

    for file_path in files_to_check:
        if file_path.exists():
            text = file_path.read_text(encoding="utf-8", errors="ignore")
            assert "\u2014" not in text, f"Travessao em dash encontrado em {file_path}"
            assert "\u2013" not in text, f"Travessao en dash encontrado em {file_path}"
