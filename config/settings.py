"""
Configurações Centralizadas da IA do Posto & Banco Local.
Carrega variáveis de ambiente (.env) e estabelece parâmetros padrão de conexão e LLM.
"""

import os
from pathlib import Path

import google.generativeai as genai
from dotenv import load_dotenv

# Diretório raiz do projeto
BASE_DIR = Path(__file__).resolve().parent.parent

# Carrega o arquivo .env se existir
ENV_PATH = BASE_DIR / ".env"
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
else:
    load_dotenv()

# Google Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


def get_erp_password() -> str:
    """
    Busca a senha do ERP.
    Prioridade:
    1. Variaveis de ambiente explicitas ERP_SERVICE_PASS / ERP_DB_PASSWORD (se diferente de DPAPI_ENCRYPTED)
    2. Cofre Criptografico DPAPI de Maquina (core/identity_vault.py)
    3. Auto-migracao de arquivos legados (backups/erp_password.txt -> cofre DPAPI -> remocao)
    4. Mock automatico em ambiente de testes CI (GitHub Actions)
    Lanca RuntimeError se a credencial nao for encontrada no startup.
    """
    # 1. Variaveis de ambiente explicitas no processo ou .env
    env_service_pass = os.getenv("ERP_SERVICE_PASS")
    if env_service_pass and env_service_pass != "DPAPI_ENCRYPTED":
        return env_service_pass

    env_pass = os.getenv("ERP_DB_PASSWORD")
    if env_pass and env_pass != "DPAPI_ENCRYPTED":
        return env_pass

    # 2. Consulta o cofre criptografico DPAPI de maquina
    try:
        from core.identity_vault import get_vault_secret, store_vault_secret

        vault_pass = get_vault_secret("erp_password")
        if vault_pass:
            return vault_pass
    except Exception:
        vault_pass = None

    # 3. Auto-migracao de arquivos de texto claro legados
    caminhos_senha = [
        BASE_DIR / "backups" / "erp_password.txt",
        BASE_DIR / "erp_password.txt",
        BASE_DIR.parent / "erp_password.txt",
    ]
    for p in caminhos_senha:
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8-sig") as f:
                    s = f.read().strip("\ufeff \r\n\t")
                    if s:
                        try:
                            from core.identity_vault import store_vault_secret

                            store_vault_secret("erp_password", s)
                            p.unlink(missing_ok=True)
                        except Exception:
                            pass
                        return s
            except Exception:
                pass

    # 4. Ambiente de testes e CI
    if os.getenv("CI") or os.getenv("GITHUB_ACTIONS") or os.getenv("PYTEST_CURRENT_TEST"):
        return "ci_test_password"

    raise RuntimeError(
        "Credencial do ERP ausente: defina a senha no cofre DPAPI ou configure ERP_SERVICE_PASS no .env."
    )


# Parametrizacao da Chave Secreta HMAC para Action Vouchers (P0-2)
AURA_VOUCHER_SECRET = os.getenv("AURA_VOUCHER_SECRET", "aura_voucher_hmac_secret_v1")

# Seguranca da API Administrativa e Endpoints Criticos (P1-4)
AURA_API_KEY = os.getenv("AURA_API_KEY", "aura_secret_admin_key_2026")


def get_cors_origins() -> list[str]:
    """Retorna lista de origens CORS autorizadas com fallback seguro."""
    raw = os.getenv("CORS_ORIGINS") or os.getenv("CORS_ALLOWED_ORIGINS", "")
    if not raw:
        return [
            "http://localhost:8000",
            "http://127.0.0.1:8000",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://100.77.164.17:8000",
            "http://marlonh-supwp:8000",
        ]
    origins = [orig.strip() for orig in raw.split(",") if orig.strip()]
    return origins if origins else ["http://localhost:8000", "http://127.0.0.1:8000"]


CORS_ORIGINS = get_cors_origins()

# Integracao Webhooks n8n e Evolution API (P1-7)
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "")
EVOLUTION_API_URL = os.getenv("EVOLUTION_API_URL", "")
EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY", "")
EVOLUTION_INSTANCE = os.getenv("EVOLUTION_INSTANCE", "posto_aura")
WHATSAPP_MANAGER_PHONE = os.getenv("WHATSAPP_MANAGER_PHONE", "")

# Configuracao do Banco ERP (PostgreSQL 16 Windows Service - Porta 5433)
# Prioriza a role tecnica dedicada aura_service_ro (P1-1)
ERP_USER = os.getenv("ERP_SERVICE_USER") or os.getenv("ERP_DB_USER", "aura_service_ro")

# Blindagem em nivel de driver no PostgreSQL (Secao 3.2 e Clausula Quarta da v1.1)
ERP_DB_DRIVER_OPTIONS = os.getenv(
    "ERP_DB_OPTIONS",
    "-c default_transaction_read_only=on -c statement_timeout=4000 -c lock_timeout=1000",
)

DB_ERP_CONFIG = {
    "host": os.getenv("ERP_DB_HOST", "localhost"),
    "port": int(os.getenv("ERP_DB_PORT", "5433")),
    "dbname": os.getenv("ERP_DB_NAME", "posto"),
    "user": ERP_USER,
    "password": get_erp_password(),
    "connect_timeout": int(os.getenv("ERP_DB_CONNECT_TIMEOUT", "5")),
    "options": ERP_DB_DRIVER_OPTIONS,
}

# Configuracao do Banco Vetorial (PostgreSQL 16 Windows pgvector - Porta 5433)
# Schemas isolados: aura_core (inteligencia comercial AURA) e n3_sre (Sentinel SRE)
AURA_CORE_SCHEMA = os.getenv("AURA_CORE_SCHEMA", "aura_core")
N3_SRE_SCHEMA = os.getenv("N3_SRE_SCHEMA", "n3_sre")
VECTOR_DB_DRIVER_OPTIONS = os.getenv(
    "VECTOR_DB_OPTIONS",
    f"-c search_path={AURA_CORE_SCHEMA},public",
)

DB_VECTOR_CONFIG = {
    "host": os.getenv("VECTOR_DB_HOST", "localhost"),
    "port": int(os.getenv("VECTOR_DB_PORT", "5433")),
    "dbname": os.getenv("VECTOR_DB_NAME", "posto_ai"),
    "user": os.getenv("VECTOR_DB_USER", "postgres"),
    "password": os.getenv("VECTOR_DB_PASSWORD", "123456"),
    "connect_timeout": int(os.getenv("VECTOR_DB_CONNECT_TIMEOUT", "5")),
    "options": VECTOR_DB_DRIVER_OPTIONS,
}

# Modelos do Google Gemini
DEFAULT_EMBEDDING_MODEL = os.getenv("DEFAULT_EMBEDDING_MODEL", "models/gemini-embedding-001")
DEFAULT_LLM_MODEL = os.getenv("DEFAULT_LLM_MODEL", "models/gemini-3.5-flash-lite")

FALLBACK_MODELS = [
    DEFAULT_LLM_MODEL,
    "models/gemini-3.5-flash-lite",
    "models/gemini-3.1-flash-lite-preview",
    "models/gemini-3.1-flash-lite",
]
