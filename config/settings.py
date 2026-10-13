"""
Configurações Centralizadas da IA do Posto & Banco Local.
Carrega variáveis de ambiente (.env) e estabelece parâmetros padrão de conexão e LLM.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai

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
    1. Variavel de ambiente ERP_DB_PASSWORD (se definida no .env)
    2. Arquivo de senha diario/local (backups/erp_password.txt)
    Lanca RuntimeError se a credencial nao for encontrada no startup.
    """
    env_pass = os.getenv("ERP_DB_PASSWORD")
    if env_pass:
        return env_pass

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
                        return s
            except Exception:
                pass
    raise RuntimeError(
        "Credencial do ERP ausente: defina ERP_DB_PASSWORD no .env ou forneca backups/erp_password.txt."
    )


# Parametrizacao da Chave Secreta HMAC para Action Vouchers (P0-2)
AURA_VOUCHER_SECRET = os.getenv("AURA_VOUCHER_SECRET", "aura_voucher_hmac_secret_v1")

# Configuracao do Banco ERP (PostgreSQL 16 Windows Service - Porta 5433)
DB_ERP_CONFIG = {
    "host": os.getenv("ERP_DB_HOST", "localhost"),
    "port": int(os.getenv("ERP_DB_PORT", "5433")),
    "dbname": os.getenv("ERP_DB_NAME", "posto"),
    "user": os.getenv("ERP_DB_USER", "suporte"),
    "password": get_erp_password(),
    "connect_timeout": int(os.getenv("ERP_DB_CONNECT_TIMEOUT", "5")),
}

# Configuracao do Banco Vetorial (PostgreSQL 16 Windows pgvector - Porta 5433)
DB_VECTOR_CONFIG = {
    "host": os.getenv("VECTOR_DB_HOST", "localhost"),
    "port": int(os.getenv("VECTOR_DB_PORT", "5433")),
    "dbname": os.getenv("VECTOR_DB_NAME", "posto_ai"),
    "user": os.getenv("VECTOR_DB_USER", "postgres"),
    "password": os.getenv("VECTOR_DB_PASSWORD", ""),
    "connect_timeout": int(os.getenv("VECTOR_DB_CONNECT_TIMEOUT", "5")),
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
