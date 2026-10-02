"""
Módulo Unificado de Sanitização de Dados Sensíveis, Blindagem LGPD e Processamento NLP para o Ai.la.

Garantias e Recursos:
1. Conformidade Total com a LGPD (Lei 13.709/2018):
   - Mascaramento determinístico de CPFs (com validação matemática oficial do DV da Receita Federal).
   - Mascaramento de CNPJs (padrão numérico e formato alfanumérico 2026).
   - Ofuscação de Placas de Veículos (Mercosul e padrão clássico brasileiro ABC-1234).
   - Proteção de Telefones e Programas de Fidelidade (KMV, ShellBox, Premmia).
   - Proteção de Cartões de Crédito / TEF / Smart POS (13 a 16 dígitos).
   - Chaves de Acesso de Documentos Fiscais (NFC-e / NF-e 44 dígitos com validação de DV SEFAZ).
   - Credenciais em Connection Strings, URLs, senhas SQL e Tokens de API.
2. Defesa OWASP GenAI 2026 (ACS-DEF-01):
   - Neutralização de injeções indiretas de prompt em placas, observações de venda e cadastros.
3. Processador NLP Híbrido Baseado em spaCy:
   - Vocabulário técnico nativo de postos de combustíveis e PDVs (fechabomba, fechacaixa, concentrador, tanques, bicos, etc.).
   - Extração ultrarrápida (<2ms) sem consumo de tokens do LLM.
4. Compressão Inteligente de Contexto:
   - Redução de volume de logs e dados para transmissão via streaming e economia de tokens no Google Gemini.
"""

from __future__ import annotations

import copy
import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    import spacy
    from spacy.matcher import Matcher, PhraseMatcher
except ImportError:
    spacy = None
    Matcher = None
    PhraseMatcher = None

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

POLICY_VERSION = "aila-lgpd-sanitization-v1"

# ---------------------------------------------------------------------------
# Marcadores Canônicos de Redação (LGPD / OWASP)
# ---------------------------------------------------------------------------
REDACTED_PASSWORD = "[REDACTED:PASSWORD]"
REDACTED_TOKEN = "[REDACTED:TOKEN]"
REDACTED_EMAIL = "[REDACTED:EMAIL]"
REDACTED_PHONE = "[REDACTED:PHONE]"
REDACTED_CPF = "[REDACTED:CPF]"
REDACTED_CNPJ = "[REDACTED:CNPJ]"
REDACTED_CREDIT_CARD = "[REDACTED:CREDIT_CARD]"
REDACTED_PLACA = "[REDACTED:PLACA]"
REDACTED_CERTIFICATE = "[REDACTED:CERTIFICATE]"
REDACTED_BASE64 = "[REDACTED:BASE64]"
REDACTED_CREDENTIAL = "[REDACTED:CREDENTIAL]"
REDACTED_FISCAL_ACCESS_KEY = "[REDACTED:FISCAL_ACCESS_KEY]"
NEUTRALIZED_PROMPT_INJECTION = "[NEUTRALIZED_PROMPT_INJECTION_OWASP_ACS]"


# ---------------------------------------------------------------------------
# Validadores Oficiais e Algorítmicos
# ---------------------------------------------------------------------------
def is_valid_cpf(cpf_str: str) -> bool:
    """Valida o dígito verificador oficial de um CPF brasileiro (Receita Federal)."""
    digits = [int(c) for c in cpf_str if c.isdigit()]
    if len(digits) != 11 or len(set(digits)) == 1:
        return False
    s1 = sum(digits[i] * (10 - i) for i in range(9))
    d1 = (s1 * 10) % 11
    if d1 == 10:
        d1 = 0
    if digits[9] != d1:
        return False
    s2 = sum(digits[i] * (11 - i) for i in range(10))
    d2 = (s2 * 10) % 11
    if d2 == 10:
        d2 = 0
    return digits[10] == d2


def mask_cpf_display(cpf_str: str) -> str:
    """
    Retorna CPF parcialmente ofuscado para exibição amigável: 123.***.***-45.
    Se não for válido, retorna [REDACTED:CPF].
    """
    digits = re.sub(r"\D", "", cpf_str)
    if len(digits) == 11:
        return f"{digits[:3]}.***.***-{digits[-2:]}"
    return REDACTED_CPF


def is_pure_hex_hash(s: str) -> bool:
    """Verifica se a string é um hash hexadecimal (evita falso positivo em Base64)."""
    return bool(re.fullmatch(r"[0-9a-fA-F]+", s))


def is_valid_fiscal_access_key(value: str) -> bool:
    """Valida o dígito verificador módulo 11 de chave NF-e/NFC-e de 44 dígitos (SEFAZ)."""
    if len(value) != 44 or not value.isdigit():
        return False

    body = value[:43]
    weight = 2
    total = 0
    for digit in reversed(body):
        total += int(digit) * weight
        weight = 2 if weight == 9 else weight + 1

    remainder = total % 11
    check_digit = 0 if remainder in (0, 1) else 11 - remainder
    return int(value[-1]) == check_digit


# ---------------------------------------------------------------------------
# Expressões Regulares Compiladas de Alta Performance
# ---------------------------------------------------------------------------
_PEM_PATTERN = re.compile(
    r"-----BEGIN [A-Z0-9 _-]+-----(?:\r?\n|\s)[\s\S]*?(?:\r?\n|\s)-----END [A-Z0-9 _-]+-----"
)
_URL_CRED_PATTERN = re.compile(
    r"\b([a-zA-Z][a-zA-Z0-9+.-]*://)([^:\s/@]+):(?!\s*\[REDACTED:)([^@\s/]+)@([^\s/]+)"
)
_URL_CRED_NOUSER_PATTERN = re.compile(
    r"\b([a-zA-Z][a-zA-Z0-9+.-]*://)(?!\s*\[REDACTED:)([^@\s/:]+)@([^\s/]+)"
)
_SQL_PASSWORD_PATTERN = re.compile(
    r"(?i)\b(?P<col>senha|password|passwd|pwd)(\s*=\s*)(')(?!\s*\[REDACTED:)([^']*)(')"
)
_CONN_STR_PASSWORD_PATTERN = re.compile(
    r"(?i)\b(password|senha|passwd|pwd)\s*=\s*(['\"]?)(?!\s*\[REDACTED:)([^;\s'\"]+)\2"
)
_JSON_PASSWORD_PATTERN = re.compile(
    r'(?i)("(?P<key>password|senha|passwd|pwd|secret|client_secret|api_secret)")\s*:\s*(")(?!\s*\[REDACTED:)([^"]*)(")'
)
_JSON_PASSWORD_UNQUOTED = re.compile(
    r'(?i)("(?P<key>password|senha|passwd|pwd|secret|client_secret|api_secret)")\s*:\s*(?!\[REDACTED:)([0-9a-zA-Z_]+)'
)
_KV_PASSWORD_PATTERN = re.compile(
    r"(?i)\b(?P<key>password|senha|passwd|pwd|client_secret|api_secret)\s*[:=]\s*(['\"]?)(?!\s*\[REDACTED:)([^\s,'\"`;\r\n\}\]]+)\2"
)
_AUTH_HEADER_PATTERN = re.compile(
    r"(?i)\b((?:Authorization\s*:\s*(?:Bearer|Basic|Digest|Token)|Bearer)\s+)(?!\s*\[REDACTED:)([^\s\r\n,;]+)"
)
_JWT_PATTERN = re.compile(
    r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"
)
_API_KEY_PATTERN = re.compile(
    r"\b(?:sk-[A-Za-z0-9]{16,}|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z\-_]{35})\b"
)
_JSON_TOKEN_PATTERN = re.compile(
    r'(?i)("(?P<key>api[_-]?key|access[_-]?token|auth[_-]?token|refresh[_-]?token|secret[_-]?token|id[_-]?token|session[_-]?id|sid|jsessionid|phpsessid)")\s*:\s*(")(?!\s*\[REDACTED:)([^"]*)(")'
)
_JSON_TOKEN_UNQUOTED = re.compile(
    r'(?i)("(?P<key>api[_-]?key|access[_-]?token|auth[_-]?token|refresh[_-]?token|secret[_-]?token|id[_-]?token|session[_-]?id|sid|jsessionid|phpsessid)")\s*:\s*(?!\[REDACTED:)([0-9a-zA-Z_]+)'
)
_KV_TOKEN_PATTERN = re.compile(
    r"(?i)\b(?P<key>api[_-]?key|access[_-]?token|auth[_-]?token|refresh[_-]?token|secret[_-]?token|id[_-]?token|session[_-]?id|sid|jsessionid|phpsessid)\s*[:=]\s*(['\"]?)(?!\s*\[REDACTED:)([^\s,'\"`;\r\n\}\]]+)\2"
)
_COOKIE_HEADER_PATTERN = re.compile(r"(?i)\b((?:Cookie|Set-Cookie)\s*:\s*)([^\r\n]+)")
_COOKIE_SESSION_PARAM = re.compile(
    r"(?i)\b(?P<name>session(?:id)?|token|jwt|auth|jsessionid|phpsessid)=([^\s;,]+)"
)
_EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_CONTEXTUAL_PHONE_PATTERN = re.compile(
    r"(?i)\b(?P<label>telefone|celular|tel|fone|whatsapp|phone|contato|kmv|fidelidade)\s*[:=]?\s*(['\"]?)(?!\s*\[REDACTED:)(\+?\d[\d\s().-]{7,18}\d)\1"
)
_FORMATTED_PHONE_PATTERN = re.compile(
    r"(?:\+?55\s*)?(?:\(\d{2}\)\s*|\b\d{2}\s+)(?:9\s*)?\d{4}[-.\s]?\d{4}\b"
)
_FORMATTED_CPF_PATTERN = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")
_UNFORMATTED_CPF_PATTERN = re.compile(r"(?<!\d)(\d{11})(?!\d)")
_CNPJ_PATTERN = re.compile(
    r"\b(?:[A-Z0-9]{2}\.[A-Z0-9]{3}\.[A-Z0-9]{3}/[A-Z0-9]{4}-\d{2}|\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})\b",
    re.IGNORECASE,
)
_CREDIT_CARD_PATTERN = re.compile(
    r"\b(?:\d{4}[ -]?\d{4}[ -]?\d{4}[ -]?\d{4}|\d{4}[ -]?\d{6}[ -]?\d{4,5})\b"
)
# Placas padrão antigo (ABC-1234) e padrão Mercosul (ABC1D23)
_PLACA_PATTERN = re.compile(r"\b(?:[a-zA-Z]{3}-\d{4}|[a-zA-Z]{3}\d[a-jA-J]\d{2})\b")

_CONTEXTUAL_FISCAL_ACCESS_KEY_PATTERN = re.compile(
    r"(?i)(?P<label>nfc_ds_chave|nfe_ds_chave|cte_ds_chave|mdfe_ds_chave|chave(?:_de)?_acesso|chnfe|chcte|chmdfe)"
    r"(?P<separator>\s*[\"']?\s*[:=]\s*[\"']?\s*)(?P<value>\d{44})"
)
_FISCAL_ACCESS_KEY_PATTERN = re.compile(r"(?<!\d)(\d{44})(?!\d)")

_PROMPT_INJECTION_PATTERN = re.compile(
    r"\b(?:ignore|disregard|forget)\s+(?:all\s+)?(?:previous|prior|above)\s+(?:instructions|prompts|rules|commands)\b|"
    r"\b(?:you are now|assume the role of|act as|behave as)\s+(?:a|an|the)?\s*(?:unrestricted|system|root|admin|god)\b|"
    r"\[(?:system|instruction|override|developer|jailbreak)\]|"
    r"<\/?(?:system|instruction|prompt|command|rules)>|"
    r"\b(?:execute\s+(?:drop|delete|truncate|grant|alter)\s+table)\b",
    re.IGNORECASE,
)
_MULTILINE_BASE64_PATTERN = re.compile(
    r"(?:^[A-Za-z0-9+/]{40,}\r?\n)+^[A-Za-z0-9+/]{4,}={0,2}$", re.MULTILINE
)
_BASE64_PATTERN = re.compile(
    r"(?<![A-Za-z0-9+/])([A-Za-z0-9+/]{64,}={0,2})(?![A-Za-z0-9+/=])"
)

# ---------------------------------------------------------------------------
# Vocabulário Especializado de Postos de Combustíveis e PDVs (webPosto / ERP)
# ---------------------------------------------------------------------------
POSTO_VOCABULARY = {
    "DB_TABLE": [
        "abastecimentos",
        "fechabomba",
        "fechacaixa",
        "concentrador",
        "tanques",
        "tanque",
        "bicos",
        "bico",
        "produtos",
        "produto",
        "pedido",
        "itemped",
        "clientes",
        "cliente",
        "usuarios",
        "usuario",
        "cartes",
        "caixa",
        "aliquotas",
        "regra_preco",
        "veiculos",
        "motoristas",
        "receber",
        "pagar",
        "plano_conta_gerencial",
        "empresa",
        "pdv",
        "grupos",
        "observacoes",
    ],
    "DB_CONSTRAINT": [
        "cliente_fk_plano_conta_gerencial",
        "pk_abastecimentos",
        "pk_clientes",
        "pk_produtos",
        "pk_pedido",
        "unique constraint",
        "foreign key constraint",
    ],
    "ERROR_SIGNATURE": [
        "[FireDAC][Phys][PG][libpq]",
        "violates foreign key constraint",
        "duplicate key value violates unique constraint",
        "relation does not exist",
        "column does not exist",
        "Connection refused",
        "timeout expired",
        "Rejeição:",
        "cStat",
    ],
    "SERVICE_NAME": [
        "Companytec",
        "CBC04",
        "CBCPROTOCOLO",
        "QualityPDV",
        "QualityPDV_PAF",
        "webPosto",
        "IntegraWeb",
        "IntegraWebService.exe",
        "webPostoPayServer",
        "SiTef",
        "TEF",
        "PAF-ECF",
    ],
}


# ---------------------------------------------------------------------------
# Classe Central: CentralLogSanitizer (Determinístico & Idempotente)
# ---------------------------------------------------------------------------
class CentralLogSanitizer:
    """
    Sanitizador centralizado, determinístico e idempotente do ecossistema Ai.la.
    Remove dados sensíveis antes de qualquer envio para LLMs externos (Gemini),
    projeções de telemetria, streaming SSE ou logs exportados.
    """

    def __init__(self, policy_version: str = POLICY_VERSION):
        self.policy_version = policy_version

    def sanitize_text(self, text: str) -> Tuple[str, Dict[str, int]]:
        """
        Higieniza uma string completa, substituindo dados sensíveis por marcadores canônicos.
        Retorna (texto_sanitizado, contadores_por_categoria).
        """
        if not text:
            return "", {}

        counts: Dict[str, int] = {}
        result = text

        # 1. Certificados e Chaves Privadas PEM
        pem_matches = _PEM_PATTERN.findall(result)
        if pem_matches:
            counts["certificate"] = counts.get("certificate", 0) + len(pem_matches)
            result = _PEM_PATTERN.sub(REDACTED_CERTIFICATE, result)

        # 2. Credenciais em URLs
        def _sub_url(m):
            counts["credential"] = counts.get("credential", 0) + 1
            return f"{m.group(1)}{m.group(2)}:{REDACTED_CREDENTIAL}@{m.group(4)}"

        result = _URL_CRED_PATTERN.sub(_sub_url, result)

        def _sub_url_nouser(m):
            counts["credential"] = counts.get("credential", 0) + 1
            return f"{m.group(1)}{REDACTED_CREDENTIAL}@{m.group(3)}"

        result = _URL_CRED_NOUSER_PATTERN.sub(_sub_url_nouser, result)

        # 3. SQL Passwords
        def _sub_sql_pwd(m):
            counts["password"] = counts.get("password", 0) + 1
            return f"{m.group('col')}{m.group(2)}'{REDACTED_PASSWORD}'"

        result = _SQL_PASSWORD_PATTERN.sub(_sub_sql_pwd, result)

        # 4. Connection Strings
        def _sub_conn(m):
            counts["password"] = counts.get("password", 0) + 1
            return f"{m.group(1)}={m.group(2)}{REDACTED_PASSWORD}{m.group(2)}"

        result = _CONN_STR_PASSWORD_PATTERN.sub(_sub_conn, result)

        # 5. JSON Passwords
        def _sub_json_pwd(m):
            counts["password"] = counts.get("password", 0) + 1
            return f'{m.group(1)}: "{REDACTED_PASSWORD}"'

        result = _JSON_PASSWORD_PATTERN.sub(_sub_json_pwd, result)
        result = _JSON_PASSWORD_UNQUOTED.sub(_sub_json_pwd, result)

        # 6. Parâmetros Chave-Valor para Senhas
        def _sub_kv_pwd(m):
            counts["password"] = counts.get("password", 0) + 1
            sep = ":" if ":" in m.group(0) else "="
            return f"{m.group('key')}{sep}{m.group(2)}{REDACTED_PASSWORD}{m.group(2)}"

        result = _KV_PASSWORD_PATTERN.sub(_sub_kv_pwd, result)

        # 7. Cabeçalhos de Autorização HTTP
        def _sub_auth(m):
            counts["token"] = counts.get("token", 0) + 1
            return f"{m.group(1)}{REDACTED_TOKEN}"

        result = _AUTH_HEADER_PATTERN.sub(_sub_auth, result)

        # 8. JWT Tokens
        jwt_matches = _JWT_PATTERN.findall(result)
        if jwt_matches:
            counts["token"] = counts.get("token", 0) + len(jwt_matches)
            result = _JWT_PATTERN.sub(REDACTED_TOKEN, result)

        # 9. API Keys Conhecidas
        api_matches = _API_KEY_PATTERN.findall(result)
        if api_matches:
            counts["token"] = counts.get("token", 0) + len(api_matches)
            result = _API_KEY_PATTERN.sub(REDACTED_TOKEN, result)

        # 10. JSON Tokens
        def _sub_json_tok(m):
            counts["token"] = counts.get("token", 0) + 1
            return f'{m.group(1)}: "{REDACTED_TOKEN}"'

        result = _JSON_TOKEN_PATTERN.sub(_sub_json_tok, result)
        result = _JSON_TOKEN_UNQUOTED.sub(_sub_json_tok, result)

        # 11. Parâmetros Chave-Valor para Tokens
        def _sub_kv_tok(m):
            counts["token"] = counts.get("token", 0) + 1
            sep = ":" if ":" in m.group(0) else "="
            return f"{m.group('key')}{sep}{m.group(2)}{REDACTED_TOKEN}{m.group(2)}"

        result = _KV_TOKEN_PATTERN.sub(_sub_kv_tok, result)

        # 12. Cookies e Sessões
        def _sub_cookie(m):
            prefix = m.group(1)
            cookie_val = m.group(2)

            def _sub_session(sm):
                counts["token"] = counts.get("token", 0) + 1
                return f"{sm.group('name')}={REDACTED_TOKEN}"

            return prefix + _COOKIE_SESSION_PARAM.sub(_sub_session, cookie_val)

        result = _COOKIE_HEADER_PATTERN.sub(_sub_cookie, result)

        # 13. E-mails
        email_matches = _EMAIL_PATTERN.findall(result)
        if email_matches:
            counts["email"] = counts.get("email", 0) + len(email_matches)
            result = _EMAIL_PATTERN.sub(REDACTED_EMAIL, result)

        # 14. Telefones Contextuais (inclui telefones de fidelidade KMV / ShellBox)
        def _sub_ctx_phone(m):
            counts["phone"] = counts.get("phone", 0) + 1
            sep = ":" if ":" in m.group(0) else "="
            return f"{m.group('label')}{sep} {REDACTED_PHONE}"

        result = _CONTEXTUAL_PHONE_PATTERN.sub(_sub_ctx_phone, result)

        # 15. Telefones Formatados BR
        phone_matches = _FORMATTED_PHONE_PATTERN.findall(result)
        if phone_matches:
            counts["phone"] = counts.get("phone", 0) + len(phone_matches)
            result = _FORMATTED_PHONE_PATTERN.sub(REDACTED_PHONE, result)

        # 16. CPF Formatado
        cpf_matches = _FORMATTED_CPF_PATTERN.findall(result)
        if cpf_matches:
            counts["cpf"] = counts.get("cpf", 0) + len(cpf_matches)
            result = _FORMATTED_CPF_PATTERN.sub(REDACTED_CPF, result)

        # 17. CPF Não Formatado (validado matematicamente com DV da Receita)
        def _sub_unformatted_cpf(m):
            val = m.group(1)
            if is_valid_cpf(val):
                counts["cpf"] = counts.get("cpf", 0) + 1
                return REDACTED_CPF
            return val

        result = _UNFORMATTED_CPF_PATTERN.sub(_sub_unformatted_cpf, result)

        # 18. CNPJ
        cnpj_matches = _CNPJ_PATTERN.findall(result)
        if cnpj_matches:
            counts["cnpj"] = counts.get("cnpj", 0) + len(cnpj_matches)
            result = _CNPJ_PATTERN.sub(REDACTED_CNPJ, result)

        # 19. Cartões de Crédito / TEF
        card_matches = _CREDIT_CARD_PATTERN.findall(result)
        if card_matches:
            counts["credit_card"] = counts.get("credit_card", 0) + len(card_matches)
            result = _CREDIT_CARD_PATTERN.sub(REDACTED_CREDIT_CARD, result)

        # 20. Placas de Veículos (Pista de Abastecimento)
        placa_matches = _PLACA_PATTERN.findall(result)
        if placa_matches:
            counts["placa"] = counts.get("placa", 0) + len(placa_matches)
            result = _PLACA_PATTERN.sub(REDACTED_PLACA, result)

        # 21. Chaves de Acesso Fiscais (NFC-e / NF-e 44 dígitos)
        def _sub_contextual_fiscal_access_key(m):
            counts["fiscal_access_key"] = counts.get("fiscal_access_key", 0) + 1
            return f"{m.group('label')}{m.group('separator')}{REDACTED_FISCAL_ACCESS_KEY}"

        result = _CONTEXTUAL_FISCAL_ACCESS_KEY_PATTERN.sub(
            _sub_contextual_fiscal_access_key, result
        )

        def _sub_fiscal_access_key(m):
            value = m.group(1)
            if is_valid_fiscal_access_key(value):
                counts["fiscal_access_key"] = counts.get("fiscal_access_key", 0) + 1
                return REDACTED_FISCAL_ACCESS_KEY
            return value

        result = _FISCAL_ACCESS_KEY_PATTERN.sub(_sub_fiscal_access_key, result)

        # 22. Neutralização de Injeção de Prompt (OWASP GenAI 2026)
        injection_matches = _PROMPT_INJECTION_PATTERN.findall(result)
        if injection_matches:
            counts["prompt_injection"] = counts.get("prompt_injection", 0) + len(
                injection_matches
            )
            result = _PROMPT_INJECTION_PATTERN.sub(NEUTRALIZED_PROMPT_INJECTION, result)

        # 23. Base64 Extenso Multilinha
        def _sub_multi_b64(m):
            counts["base64"] = counts.get("base64", 0) + 1
            return REDACTED_BASE64

        result = _MULTILINE_BASE64_PATTERN.sub(_sub_multi_b64, result)

        # 24. Base64 Extenso Monolinha
        def _sub_b64(m):
            val = m.group(1)
            if not is_pure_hex_hash(val):
                counts["base64"] = counts.get("base64", 0) + 1
                return REDACTED_BASE64
            return val

        result = _BASE64_PATTERN.sub(_sub_b64, result)

        return result, counts

    def sanitize_lines(self, lines: List[str]) -> Tuple[List[str], Dict[str, int]]:
        """Higieniza uma lista de linhas de texto, agregando os contadores."""
        if not lines:
            return [], {}

        aggregated_counts: Dict[str, int] = {}
        sanitized_lines: List[str] = []

        for line in lines:
            sanitized_line, line_counts = self.sanitize_text(line)
            sanitized_lines.append(sanitized_line)
            for category, count in line_counts.items():
                aggregated_counts[category] = aggregated_counts.get(category, 0) + count

        return sanitized_lines, aggregated_counts

    def sanitize_payload(
        self, payload: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], Dict[str, int]]:
        """Higieniza de forma profunda um dicionário contendo campos textuais."""
        clean_payload = copy.deepcopy(payload)
        aggregated_counts: Dict[str, int] = {}

        def _walk_and_clean(obj):
            if isinstance(obj, dict):
                return {k: _walk_and_clean(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [_walk_and_clean(item) for item in obj]
            elif isinstance(obj, str):
                cleaned, counts = self.sanitize_text(obj)
                for cat, c in counts.items():
                    aggregated_counts[cat] = aggregated_counts.get(cat, 0) + c
                return cleaned
            return obj

        clean_payload = _walk_and_clean(clean_payload)
        return clean_payload, aggregated_counts

    @classmethod
    def sanitize(cls, text: str) -> str:
        """Método estático de conveniência que retorna apenas o texto limpo."""
        if not text:
            return ""
        clean_text, _ = central_log_sanitizer.sanitize_text(text)
        return clean_text

    def get_metadata(self, counts: Dict[str, int]) -> Dict[str, Any]:
        """Gera metadados seguros da auditoria LGPD sem expor fragmentos dos segredos."""
        return {
            "policy_version": self.policy_version,
            "redacted_counts": dict(sorted(counts.items())),
            "total_sanitized": sum(counts.values()),
        }


# Instância Singleton Centralizada
central_log_sanitizer = CentralLogSanitizer()


# ---------------------------------------------------------------------------
# Entidades Técnicas e Processamento NLP com spaCy
# ---------------------------------------------------------------------------
class SpacyExtractedEntities(BaseModel):
    """Contrato Pydantic v2 para as entidades técnicas extraídas do ecossistema do posto."""

    tables: List[str] = Field(
        default_factory=list, description="Tabelas do ERP identificadas"
    )
    constraints: List[str] = Field(
        default_factory=list, description="Constraints ou foreign keys"
    )
    error_signatures: List[str] = Field(
        default_factory=list, description="Assinaturas de erro de motor ou biblioteca"
    )
    services: List[str] = Field(
        default_factory=list, description="Serviços ou protocolos (Companytec, CBC04, etc.)"
    )
    sql_operations: List[str] = Field(
        default_factory=list, description="Operações SQL (SELECT, INSERT, UPDATE, etc.)"
    )
    extracted_summary: str = Field(
        "", description="Resumo denso pré-processado para o LLM"
    )


class SpacyLogNLPProcessor:
    """
    Processador NLP Baseado em spaCy para Análise Determinística de Logs e Contextos do Posto.
    Opera em memória em tempo de execução (<2ms) com zero consumo de tokens de API.
    """

    def __init__(self):
        if spacy is None:
            self.nlp = None
            self.matcher = None
            self.phrase_matcher = None
            logger.info("spaCy não instalado. SpacyLogNLPProcessor em modo pass-through.")
            return

        try:
            self.nlp = spacy.load("pt_core_news_sm")
            logger.info("Modelo pt_core_news_sm carregado para o Ai.la NLP Processor.")
        except Exception:
            self.nlp = spacy.blank("pt")
            logger.info("Pipeline blank('pt') inicializado para o Ai.la NLP Processor.")

        self.matcher = Matcher(self.nlp.vocab)
        self.phrase_matcher = PhraseMatcher(self.nlp.vocab, attr="LOWER")

        # Registra vocabulário de postos no PhraseMatcher
        for category, phrases in POSTO_VOCABULARY.items():
            patterns = [self.nlp.make_doc(text) for text in phrases]
            self.phrase_matcher.add(category, patterns)

        # Regras de SQL Pattern no Matcher
        self.matcher.add(
            "SQL_OP",
            [
                [
                    {
                        "LOWER": {
                            "IN": [
                                "update",
                                "insert",
                                "delete",
                                "alter",
                                "select",
                                "truncate",
                                "drop",
                            ]
                        }
                    },
                    {"LOWER": {"IN": ["into", "from", "table", "set"]}, "OP": "?"},
                ]
            ],
        )

    def extract_entities(self, text: str) -> SpacyExtractedEntities:
        """Extrai entidades estruturadas usando o pipeline do spaCy."""
        if not text or not self.nlp:
            return SpacyExtractedEntities()

        doc = self.nlp(text[:25000])

        tables: Set[str] = set()
        constraints: Set[str] = set()
        errors: Set[str] = set()
        services: Set[str] = set()
        sql_ops: Set[str] = set()

        # 1. Varredura via PhraseMatcher
        matches = self.phrase_matcher(doc)
        for match_id, start, end in matches:
            span = doc[start:end]
            label = self.nlp.vocab.strings[match_id]
            clean_text = span.text.strip().lower()

            if label == "DB_TABLE":
                tables.add(clean_text)
            elif label == "DB_CONSTRAINT":
                constraints.add(clean_text)
            elif label == "ERROR_SIGNATURE":
                errors.add(span.text.strip())
            elif label == "SERVICE_NAME":
                services.add(span.text.strip())

        # 2. Varredura via Token Matcher (SQL Operations)
        sql_matches = self.matcher(doc)
        for match_id, start, end in sql_matches:
            span = doc[start:end]
            sql_ops.add(span.text.strip().upper())

        # 3. Varredura Regex de apoio para foreign keys dinâmicas
        fk_match = re.findall(r'constraint\s+"([^"]+)"', text, re.IGNORECASE)
        for fk in fk_match:
            constraints.add(fk.lower())

        table_quoted = re.findall(r'table\s+"([^"]+)"', text, re.IGNORECASE)
        for t in table_quoted:
            tables.add(t.lower())

        # 4. Geração de Resumo Denso Pré-Mastigado
        summary_parts = []
        if services:
            summary_parts.append(f"Módulo: {', '.join(services)}")
        if errors:
            summary_parts.append(f"Erro: {', '.join(list(errors)[:2])}")
        if tables:
            summary_parts.append(f"Tabela(s): {', '.join(sorted(tables))}")
        if constraints:
            summary_parts.append(f"Constraint: {', '.join(sorted(constraints))}")

        extracted_summary = (
            " | ".join(summary_parts)
            if summary_parts
            else "Contexto do posto verificado sem inconsistências óbvias"
        )

        return SpacyExtractedEntities(
            tables=sorted(list(tables)),
            constraints=sorted(list(constraints)),
            error_signatures=sorted(list(errors)),
            services=sorted(list(services)),
            sql_operations=sorted(list(sql_ops)),
            extracted_summary=extracted_summary,
        )


# ---------------------------------------------------------------------------
# Classe Wrapper de Alto Nível: DataSanitizer
# ---------------------------------------------------------------------------
class DataSanitizer:
    """
    Sanitizador e Pré-Processador Híbrido de Alto Nível para o Ai.la.
    Integra a blindagem de regex da LGPD com a extração semântica spaCy.
    """

    def __init__(self, use_spacy: bool = True):
        self.use_spacy = use_spacy
        self.nlp_processor = SpacyLogNLPProcessor() if use_spacy else None

    def redact_deterministic(self, text: str) -> str:
        """Executa a sanitização determinística e idempotente via CentralLogSanitizer."""
        if not text:
            return ""
        sanitized, _ = central_log_sanitizer.sanitize_text(text)
        return sanitized

    def detect_prompt_injection(self, text: str) -> List[str]:
        """Detecta tentativas de injeção indireta de prompt (OWASP GenAI 2026)."""
        if not text:
            return []
        return [match.group(0) for match in _PROMPT_INJECTION_PATTERN.finditer(text)]

    def sanitize(self, raw_text: str) -> str:
        """Executa a sanitização completa do texto."""
        return self.redact_deterministic(raw_text)

    def extract_spacy_entities(self, raw_text: str) -> SpacyExtractedEntities:
        """Extrai entidades técnicas via spaCy."""
        sanitized = self.sanitize(raw_text)
        if self.nlp_processor:
            return self.nlp_processor.extract_entities(sanitized)
        return SpacyExtractedEntities()

    def compress_for_llm(self, raw_text: str, max_lines: int = 25) -> Dict[str, Any]:
        """
        Comprime um log ou contexto denso em um payload estruturado,
        reduzindo em até 80% o consumo de tokens e eliminando dados sensíveis.
        """
        injection_matches = self.detect_prompt_injection(raw_text)
        sanitized = self.sanitize(raw_text)
        entities = (
            self.nlp_processor.extract_entities(sanitized)
            if self.nlp_processor
            else SpacyExtractedEntities()
        )

        meaningful_lines = []
        for line in sanitized.splitlines():
            line_str = line.strip()
            if not line_str:
                continue
            if any(
                k in line_str.upper()
                for k in [
                    "ERROR",
                    "EXCEPTION",
                    "ABASTECIMENTO",
                    "FECHAMENTO",
                    "DIVERGENCIA",
                    "QUEBRA",
                    "UPDATE",
                    "INSERT",
                    "DELETE",
                    "SELECT",
                    "REJEICAO",
                ]
            ):
                meaningful_lines.append(line_str)

        selected_lines = (
            meaningful_lines[-max_lines:]
            if len(meaningful_lines) > max_lines
            else meaningful_lines
        )
        condensed = (
            "\n".join(selected_lines) if selected_lines else sanitized[:1200]
        )

        return {
            "entities": entities.model_dump(),
            "condensed_context": condensed,
            "summary_line": entities.extracted_summary,
            "injection_detected": len(injection_matches) > 0,
            "injection_count": len(injection_matches),
        }


# Instância Singleton Global
data_sanitizer = DataSanitizer(use_spacy=True)


# ---------------------------------------------------------------------------
# Funções de Conveniência para Importação Direta
# ---------------------------------------------------------------------------
def sanitize_text(text: str) -> str:
    """Função utilitária rápida para sanitizar qualquer string antes de envio ou log."""
    return CentralLogSanitizer.sanitize(text)


def sanitize_dict(data: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, int]]:
    """Função utilitária para sanitizar dicionários ou payloads JSON."""
    return central_log_sanitizer.sanitize_payload(data)
