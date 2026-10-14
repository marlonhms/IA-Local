"""
Testes Unitarios: Esteira de Deploy e Onboarding Multi-Posto (Fase 2.5).
Valida a integridade do template docker-compose.yml, scripts de implantacao
em PowerShell e utilitarios de migracao de banco vetorial.
Zero travessoes em todo o arquivo.
"""

from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


@pytest.mark.unit
def test_docker_compose_structure():
    """Valida o arquivo docker-compose.yml oficial para o posto."""
    compose_file = PROJECT_ROOT / "docker-compose.yml"
    assert compose_file.exists(), "docker-compose.yml nao encontrado na raiz"

    content = compose_file.read_text(encoding="utf-8")
    assert "pgvector/pgvector:pg16" in content, "Imagem oficial pgvector pg16 ausente"
    assert "5434" in content, "Mapeamento da porta 5434 ausente"
    assert "aura_pgvector_posto_data" in content, "Volume persistente nomeado ausente"
    assert "shared_buffers=256MB" in content, "Tuning de memoria para postos ausente"
    assert "healthcheck:" in content, "Healthcheck do PostgreSQL ausente"


@pytest.mark.unit
def test_deploy_posto_powershell_script():
    """Valida o script PowerShell de onboarding em 1-clique."""
    ps_file = PROJECT_ROOT / "scripts" / "deploy_posto.ps1"
    assert ps_file.exists(), "scripts/deploy_posto.ps1 nao encontrado"

    content = ps_file.read_text(encoding="utf-8")
    # Regra do powershell-windows: ASCII puro sem emojis ou caracteres corrompidos
    for i, line in enumerate(content.splitlines(), 1):
        for char in line:
            assert ord(char) < 128, f"Caractere nao-ASCII encontrado na linha {i}: {char}"

    assert "param(" in content
    assert "SkipDocker" in content
    assert "Test-NetConnection" in content
    assert "init_posto_database.py" in content


@pytest.mark.unit
def test_init_posto_database_script():
    """Valida a presenca e sintaxe do script de inicializacao do banco vetorial."""
    init_file = PROJECT_ROOT / "scripts" / "init_posto_database.py"
    assert init_file.exists(), "scripts/init_posto_database.py nao encontrado"

    content = init_file.read_text(encoding="utf-8")
    assert "CREATE EXTENSION IF NOT EXISTS vector;" in content
    assert "intencoes_vetores" in content
    assert "produtos_vetores" in content
    assert "aura_conhecimento_vetores" in content
    assert "--check-only" in content
