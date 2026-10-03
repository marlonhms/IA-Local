"""
Módulo Central do Motor Cognitivo Headless da AURA
(Autonomous Unified Retail Assistant) - Postos de Combustíveis & PDV.

Arquitetura Desacoplada (Headless Core Engine):
- Roteamento Semântico Vetorial (pgvector HNSW + heurísticas de ultra-baixa latência)
- RAG Híbrido HNSW + GIN FTS + Reciprocal Rank Fusion (RRF) com Cache Semântico
- 11 Ferramentas Analíticas Especializadas de Posto (LMC ANP, Fechamento de Turno, Run-Out, Frentistas, etc.)
- Blindagem de Privacidade e Sanitização LGPD (CentralLogSanitizer)
- Streaming Assíncrono com Fallback Resiliente de Modelos Google Gemini
- Memória de Sessão Multiturn Durável (SQLite / Sessões de Continuidade)
"""

from __future__ import annotations

import os
import sys
import time
import json
import re
import uuid
import sqlite3
import asyncio
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from enum import Enum
from typing import AsyncIterator, Optional, Dict, Any, List, Tuple, Union

from pydantic import BaseModel, Field, ConfigDict
import google.generativeai as genai

# Diretório raiz
BASE_DIR = Path(__file__).resolve().parent.parent

from config.settings import (
    GEMINI_API_KEY,
    DB_ERP_CONFIG,
    DB_VECTOR_CONFIG,
    FALLBACK_MODELS,
    DEFAULT_LLM_MODEL,
    BASE_DIR as SETTINGS_BASE_DIR,
)
from core.rag_engine import HybridRAGEngine
from core.tools import PostoTools, get_erp_connection
from core.sanitizer import central_log_sanitizer
from core.semantic_router import SemanticRouter, classificar_intencao_heuristica


# =============================================================================
# CONTRATOS PYDANTIC & ENUMS DA AURA
# =============================================================================

class AuraChunkType(str, Enum):
    """Tipos de blocos emitidos no streaming assíncrono da AURA."""
    DELTA = "delta"                # Token ou fragmento textual de resposta
    INTENT = "intent"              # Detecção de intenção pelo roteador semântico
    TOOL_START = "tool_start"      # Notificação de início de execução de ferramenta
    TOOL_RESULT = "tool_result"    # Dados estruturados retornados pela ferramenta
    CACHE_HIT = "cache_hit"        # Resposta recuperada instantaneamente do cache semântico
    TELEMETRY = "telemetry"        # Métricas de observabilidade e latência SRE
    ERROR = "error"                # Notificação de erro no processamento
    DONE = "done"                  # Finalização da requisição


class AuraChunk(BaseModel):
    """Envelope de transmissão SSE / Streaming para canais Web, WhatsApp e Parceiros."""
    model_config = ConfigDict(extra="ignore")

    chunk_type: AuraChunkType = Field(..., description="Tipo do bloco de streaming")
    text: Optional[str] = Field(default=None, description="Conteúdo textual do token ou mensagem")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Metadados ou carga útil estruturada")
    session_id: Optional[str] = Field(default=None, description="ID da sessão vinculada")

    def to_sse(self) -> str:
        """Formata o chunk no padrão Server-Sent Events (SSE)."""
        payload = self.model_dump_json(exclude_none=True)
        return f"event: {self.chunk_type.value}\ndata: {payload}\n\n"


class AuraResponse(BaseModel):
    """Resposta consolidada para requisições síncronas/completas (sem streaming)."""
    model_config = ConfigDict(extra="ignore")

    session_id: str = Field(..., description="Identificador único da sessão de conversa")
    query: str = Field(..., description="Pergunta original enviada pelo usuário")
    response_text: str = Field(..., description="Texto final gerado pelo motor da AURA")
    intent: str = Field(..., description="Intenção classificada pelo roteador")
    confidence: float = Field(..., description="Grau de confiança na classificação (0.0 a 1.0)")
    routing_method: str = Field(..., description="Método utilizado no roteamento (pgvector ou heurística)")
    tool_name: Optional[str] = Field(default=None, description="Nome da ferramenta executada")
    tool_result: Optional[Dict[str, Any]] = Field(default=None, description="Resultado bruto da ferramenta")
    telemetry: Dict[str, Any] = Field(default_factory=dict, description="Telemetria SRE da consulta")
    cache_hit: bool = Field(default=False, description="Se a resposta veio do cache semântico")
    lgpd_sanitized_count: int = Field(default=0, description="Quantidade de entidades sensíveis ofuscadas")


class StationStatus(BaseModel):
    """Diagnóstico operacional e telemetria de conectividade de uma filial/posto."""
    model_config = ConfigDict(extra="ignore")

    filial_id: str
    filial_nome: str
    razao_social: Optional[str] = None
    cnpj: Optional[str] = None
    pdv: Optional[str] = None
    erp_online: bool
    erp_host: str
    erp_port: int
    vector_db_online: bool
    vector_db_host: str
    vector_db_port: int
    latency_erp_ms: Optional[float] = None
    total_products_indexed: Optional[int] = None
    cache_hit_ratio_percent: Optional[float] = None
    active_connections: Optional[int] = None


# =============================================================================
# MEMÓRIA DE SESSÃO DURÁVEL (SQLITE)
# =============================================================================

class AuraSessionMemory:
    """
    Armazenamento durável de histórico de conversa por session_id.
    Permite perguntas de continuidade (ex: 'E o fechamento do turno 2?')
    isoladas por usuário/posto no WhatsApp, Web ou API de Parceiros.
    """

    def __init__(self, db_path: Optional[Union[str, Path]] = None):
        if db_path is None:
            data_dir = BASE_DIR / "data"
            data_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = str(data_dir / "aura_sessions.db")
            self._shared_conn = None
        elif str(db_path) == ":memory:":
            self.db_path = ":memory:"
            self._shared_conn = sqlite3.connect(":memory:", check_same_thread=False)
            self._shared_conn.row_factory = sqlite3.Row
        else:
            self.db_path = str(db_path)
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            self._shared_conn = None
        self._init_db()

    @contextmanager
    def _connection(self):
        if self._shared_conn is not None:
            with self._shared_conn:
                yield self._shared_conn
        else:
            conn = sqlite3.connect(self.db_path, timeout=15.0)
            conn.row_factory = sqlite3.Row
            try:
                with conn:
                    yield conn
            finally:
                conn.close()

    def _get_connection(self) -> sqlite3.Connection:
        """Compatibilidade retroativa com chamadas diretas."""
        if self._shared_conn is not None:
            return self._shared_conn
        conn = sqlite3.connect(self.db_path, timeout=15.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._connection() as conn:
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA synchronous = NORMAL;")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS aura_sessions (
                    session_id TEXT PRIMARY KEY,
                    tenant_id TEXT,
                    filial_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS aura_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    intent TEXT,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES aura_sessions(session_id)
                );
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_aura_messages_session 
                ON aura_messages(session_id, created_at);
            """)
            conn.commit()

    def save_message(
        self,
        session_id: str,
        role: str,
        content: str,
        intent: Optional[str] = None,
        tenant_id: Optional[str] = None,
        filial_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Salva uma mensagem de usuário ou assistente na sessão."""
        with self._connection() as conn:
            conn.execute("""
                INSERT INTO aura_sessions (session_id, tenant_id, filial_id, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(session_id) DO UPDATE SET
                    tenant_id = COALESCE(?, tenant_id),
                    filial_id = COALESCE(?, filial_id),
                    updated_at = CURRENT_TIMESTAMP;
            """, (session_id, tenant_id, filial_id, tenant_id, filial_id))

            meta_json = json.dumps(metadata, ensure_ascii=False) if metadata else None
            conn.execute("""
                INSERT INTO aura_messages (session_id, role, content, intent, metadata)
                VALUES (?, ?, ?, ?, ?);
            """, (session_id, role, content, intent, meta_json))
            conn.commit()

    def get_history(self, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Recupera as últimas mensagens ordenadas cronologicamente."""
        with self._connection() as conn:
            cur = conn.execute("""
                SELECT role, content, intent, created_at, metadata
                FROM aura_messages
                WHERE session_id = ?
                ORDER BY id DESC
                LIMIT ?;
            """, (session_id, limit))
            rows = cur.fetchall()

        mensagens = []
        for r in reversed(rows):
            meta = {}
            if r["metadata"]:
                try:
                    meta = json.loads(r["metadata"])
                except Exception:
                    meta = {}
            mensagens.append({
                "role": r["role"],
                "content": r["content"],
                "intent": r["intent"],
                "created_at": r["created_at"],
                "metadata": meta,
            })
        return mensagens

    def format_history_for_prompt(self, session_id: str, limit: int = 6) -> str:
        """Formata o histórico para injeção limpa no prompt de continuidade do LLM."""
        historico = self.get_history(session_id, limit=limit)
        if not historico:
            return "Nenhum histórico anterior nesta sessão."

        linhas = []
        for msg in historico:
            rotulo = "Usuário" if msg["role"] == "user" else "AURA"
            conteudo = msg["content"].replace("\n", " ")
            if len(conteudo) > 300:
                conteudo = conteudo[:300] + "..."
            linhas.append(f"- {rotulo}: {conteudo}")
        return "\n".join(linhas)

    def clear_session(self, session_id: str):
        """Limpa as mensagens de uma sessão específica."""
        with self._connection() as conn:
            conn.execute("DELETE FROM aura_messages WHERE session_id = ?;", (session_id,))
            conn.execute("DELETE FROM aura_sessions WHERE session_id = ?;", (session_id,))
            conn.commit()


# =============================================================================
# EXTRATORES DE PARÂMETROS E CLASSIFICAÇÃO (COMPATIBILIDADE PLENA)
# =============================================================================

def extrair_grupo(pergunta: str) -> Optional[str]:
    """Extrai intenção de grupo (Metadata Filter) via palavras-chave."""
    p = pergunta.lower()
    if "cerveja" in p or "bebida" in p: return "BEBIDAS"
    if "óleo" in p or "oleo" in p or "lubrificante" in p: return "LUBRIFICANTES"
    if "cigarro" in p or "tabaco" in p: return "TABACO"
    if "conveniência" in p or "salgadinho" in p or "doce" in p: return "CONVENIENCIA"
    return None


def extrair_combustivel(pergunta: str) -> Optional[str]:
    """Extrai combustível ou código de tanque da pergunta do usuário."""
    p = pergunta.lower()

    # 1. Menção a tanque específico prioritária
    m_tanque = re.search(r"\b(?:tanque|tq)\s*[-_]?\s*0*([0-9]{1,3})\b", p)
    if m_tanque:
        num = int(m_tanque.group(1))
        return f"{num:03d}"

    # 2. Combustíveis específicos
    if "gasolina aditivada" in p or "aditivada" in p or "grid" in p or "v-power" in p or "octapro" in p or "podium" in p or "premium" in p:
        return "GASOLINA ADITIVADA"
    if "gasolina comum" in p:
        return "GASOLINA COMUM"
    if "gasolinas" in p:
        return "GASOLINA"
    if "diesel s10" in p or "diesel s-10" in p or "s10" in p or "s-10" in p:
        return "DIESEL S10"
    if "diesel s500" in p or "diesel s-500" in p or "s500" in p or "s-500" in p or "diesel comum" in p:
        return "DIESEL S500"
    if "diesel" in p:
        return "DIESEL"
    if "etanol" in p or "álcool" in p or "alcool" in p:
        return "ETANOL"
    if "arla" in p:
        return "ARLA"
    if "gasolina" in p:
        return "GASOLINA COMUM"

    return None


def extrair_data_turno(pergunta: str) -> Tuple[Optional[str], Optional[str]]:
    """Extrai parâmetros de data e turno a partir da pergunta em linguagem natural."""
    p = pergunta.lower()

    # Identificação do Turno
    turno = None
    if re.search(r"\b(1[º°ªo]|primeir[oa]|manh[aã]|turno\s*1|1\s*turno)\b", p):
        turno = "1º TURNO"
    elif re.search(r"\b(2[º°ªo]|segund[oa]|tarde|turno\s*2|2\s*turno)\b", p):
        turno = "2º TURNO"
    elif re.search(r"\b(3[º°ªo]|terceir[oa]|noite|madrugada|turno\s*3|3\s*turno)\b", p):
        turno = "3º TURNO"

    # Identificação da Data
    data = None
    if "hoje" in p:
        data = "hoje"
    elif "anteontem" in p:
        data = "anteontem"
    elif "ontem" in p:
        data = "ontem"
    else:
        m_iso = re.search(r"\b(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})\b", p)
        if m_iso:
            y, m, d = m_iso.groups()
            data = f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
        else:
            m_br = re.search(r"\b(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})\b", p)
            if m_br:
                d, m, y = m_br.groups()
                data = f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
            else:
                m_dia_mes = re.search(r"\b(\d{1,2})[-/](\d{1,2})\b", p)
                if m_dia_mes:
                    d, m = m_dia_mes.groups()
                    data = f"2026-{int(m):02d}-{int(d):02d}"
                else:
                    meses = {
                        "jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
                        "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12
                    }
                    m_ext = re.search(r"\b(\d{1,2})\s+de\s+([a-zçãõ]+)(?:\s+de\s+(\d{4}))?", p)
                    if m_ext:
                        d, mes_str, ano_str = m_ext.groups()
                        mes_prefix = mes_str[:3]
                        if mes_prefix in meses:
                            ano = int(ano_str) if ano_str else 2026
                            data = f"{ano:04d}-{meses[mes_prefix]:02d}-{int(d):02d}"

    return data, turno


def extrair_bico(pergunta: str) -> Optional[str]:
    """Extrai número de bico ou bomba a partir da pergunta."""
    p = pergunta.lower()
    m_b = re.search(r"\b(?:bico|bomba)\s*0*([0-9]{1,3})\b", p)
    if m_b:
        num = int(m_b.group(1))
        return f"{num:03d}"
    return None


def extrair_frentista(pergunta: str) -> Optional[str]:
    """Extrai identificação ou nome de frentista a partir da pergunta."""
    p = pergunta.lower()

    # 1. Padrão numérico
    m_mat = re.search(r"\b(?:matr[ií]cula|frentista|operador|colaborador)\s*0*([0-9]{1,5})\b", p)
    if m_mat:
        num = int(m_mat.group(1))
        return f"{num:05d}"

    # 2. Padrão nominal precedido por cargo
    m_nome = re.search(r"\b(?:frentista|operador|colaborador)\s+([a-zA-ZÀ-ÿ]{3,})\b", p)
    stop_words = {
        "hoje", "ontem", "anteontem", "com", "sem", "que", "mais", "menos", "qual", "quem",
        "tem", "teve", "houve", "de", "do", "da", "no", "na", "em", "um", "uma", "para", "por",
        "geral", "ranking", "pista", "equipe", "time", "vendeu", "faturou", "melhor", "maior",
        "pior", "menor", "bico", "bomba", "turno"
    }
    if m_nome:
        candidato = m_nome.group(1).lower()
        if candidato not in stop_words:
            return candidato.upper()

    # 3. Nomes conhecidos da equipe
    nomes = [
        "italo", "botan", "marcio", "sergio", "erivas", "cristian", "marlon",
        "davi", "ruan", "vinicius", "robson", "gabriel", "ludmila", "samarina"
    ]
    for n in nomes:
        if re.search(rf"\b{n}\b", p):
            return n.upper()

    return None


def limpar_termo_produto(prod: str) -> Optional[str]:
    """Limpa ruído léxico, preposições, artigos e sufixos de um produto extraído."""
    if not prod:
        return None
    p = prod.strip().strip("\"'[](){}<>")
    p = re.sub(r"^(?:o|a|os|as|um|uma|uns|umas|de|do|da|dos|das|no|na|nos|nas|com|para|pra|por)\s+", "", p, flags=re.IGNORECASE).strip()
    p = re.sub(r"^(?:produto|mercadoria|c[oó]digo|cod|item|sku)\s*", "", p, flags=re.IGNORECASE).strip()
    p = re.sub(r"\b(?:na|no|da|do|em)\s+conveni[eê]ncia\b.*", "", p, flags=re.IGNORECASE).strip()
    p = re.sub(r"\b(?:na|no|da|do|em)\s+loja\b.*", "", p, flags=re.IGNORECASE).strip()
    p = re.sub(r"\b(?:hoje|ontem|no\s+caixa|no\s+pdv|no\s+balc[aã]o|no\s+posto)\b.*", "", p, flags=re.IGNORECASE).strip()
    p = re.sub(r"\s+\b(?:gelad[ao]s?|fria?s?|frio?s?|quentes?|trincando)\b", "", p, flags=re.IGNORECASE).strip()
    p = p.rstrip("?.,;! ")

    stop_generic = {
        "conveniencia", "conveniência", "loja", "pdv", "caixa", "produtos", "mercadorias",
        "produto", "mercadoria", "isso", "ele", "ela", "eles", "elas", "combo", "combos",
        "cesta", "vendas", "cross-sell", "cross sell"
    }
    if not p or len(p) < 2 or p.lower() in stop_generic:
        return None
    return p


def extrair_produto_cesta(pergunta: str) -> Optional[str]:
    """Extrai produto alvo para análise de vendas cruzadas (Market Basket)."""
    p = (pergunta or "").strip()

    # 1. Padrões com 'junto com'
    m_junto = re.search(r"\bjunto\s+(?:com|de|a|ao|à)\s+([^?.,;!\n]+)", p, re.IGNORECASE)
    if m_junto:
        res = limpar_termo_produto(m_junto.group(1))
        if res:
            return res

    # 2. Padrões 'combos para/de'
    m_combo = re.search(r"\bcombos?\s+(?:para|pra|de|do|da)\s+([^?.,;!\n]+)", p, re.IGNORECASE)
    if m_combo:
        res = limpar_termo_produto(m_combo.group(1))
        if res:
            return res

    # 3. Padrões 'vende/sai com'
    m_com = re.search(r"\b(?:vende[rm]?|sai[rm]?|compra[rm]?|oferece[rm]?|levar?)\s+com\s+([^?.,;!\n]+)", p, re.IGNORECASE)
    if m_com:
        res = limpar_termo_produto(m_com.group(1))
        if res:
            return res

    # 4. Checagem direta de termos conhecidos
    termos_comuns = [
        "cerveja heineken", "heineken", "cerveja", "coca-cola", "coca cola", "coca",
        "cafe expresso", "café expresso", "café", "cafe", "pao de queijo", "pão de queijo",
        "red bull", "energetico", "energético", "kit kat", "chocolate", "gelo", "carvao", "carvão",
        "halls", "mentos", "salgado"
    ]
    p_lower = p.lower()
    for t in termos_comuns:
        if t in p_lower and any(w in p_lower for w in ["para", "com", "junto", "do", "da", "de"]):
            return t

    return None


def classificar_intencao(pergunta: str, router: Optional[SemanticRouter] = None) -> str:
    """
    Classifica a intenção da pergunta do usuário.
    Se router for fornecido, executa roteamento semântico vetorial com pgvector.
    Caso contrário, executa heurísticas determinísticas com latência ultrarrápida.
    """
    if router is not None:
        intencao, _, _ = router.route(pergunta)
        return intencao
    return classificar_intencao_heuristica(pergunta)


# =============================================================================
# MOTOR CENTRAL DA AURA (AuraEngine)
# =============================================================================

class AuraEngine:
    """
    Motor Headless Puro, Reutilizável e Assíncrono da AURA.
    Encapsula toda a inteligência do posto para consumo via:
    - Sentinel SRE Web
    - WhatsApp (Evolution API)
    - Portais de Parceiros (API Key Gateway)
    - CLI Local (main.py)
    """

    def __init__(
        self,
        tenant_id: Optional[str] = None,
        filial_id: Optional[str] = None,
        rag_engine: Optional[HybridRAGEngine] = None,
        tools: Optional[PostoTools] = None,
        router: Optional[SemanticRouter] = None,
        session_memory: Optional[AuraSessionMemory] = None,
    ):
        self.tenant_id = tenant_id or "default_tenant"
        self.filial_id = filial_id or "posto_01"

        # Lazy / Dependency Injection de componentes essenciais
        self._rag_engine = rag_engine
        self._tools = tools
        self._router = router
        self._session_memory = session_memory or AuraSessionMemory()
        self._dados_filial: Optional[Dict[str, Any]] = None

    @property
    def rag(self) -> HybridRAGEngine:
        if self._rag_engine is None:
            self._rag_engine = HybridRAGEngine()
        return self._rag_engine

    @property
    def tools(self) -> PostoTools:
        if self._tools is None:
            self._tools = PostoTools(self.rag)
        return self._tools

    @property
    def router(self) -> SemanticRouter:
        if self._router is None:
            self._router = SemanticRouter(rag_engine=self.rag)
        return self._router

    @property
    def session_memory(self) -> AuraSessionMemory:
        return self._session_memory

    def get_dados_filial(self, force_reload: bool = False) -> Dict[str, Any]:
        """Obtém dados cadastrais da filial conectada com cache em memória."""
        if self._dados_filial is None or force_reload:
            try:
                self._dados_filial = self.tools.dados_cadastrais_filial()
            except Exception as e:
                self._dados_filial = {
                    "idempresa": self.filial_id,
                    "nome": f"Posto de Combustíveis ({self.filial_id})",
                    "razao_social": "Auto Posto S/A",
                    "cnpj": "00.000.000/0001-00",
                    "endereco": "Unidade Operacional",
                    "pdv": "01",
                    "status_conexao": f"Indisponível: {e}",
                }
        return self._dados_filial

    def get_stations_status(self) -> StationStatus:
        """Verifica a saúde das conexões de banco de dados e telemetria da filial."""
        t0 = time.perf_counter()
        erp_online = False
        lat_erp = None
        db_stats = {}
        t_stats = {}

        # 1. Checagem ERP
        try:
            conn = get_erp_connection()
            conn.close()
            erp_online = True
            lat_erp = (time.perf_counter() - t0) * 1000
        except Exception:
            erp_online = False

        # 2. Checagem Vector DB & Telemetria SRE
        vector_online = False
        try:
            sre_data = self.tools.obter_telemetria_sre()
            vector_online = True
            db_stats = sre_data.get("database_health", {})
            t_stats = sre_data.get("table_stats", {})
        except Exception:
            vector_online = False

        filial = self.get_dados_filial()

        return StationStatus(
            filial_id=str(filial.get("idempresa") or self.filial_id),
            filial_nome=str(filial.get("nome") or "Posto"),
            razao_social=filial.get("razao_social"),
            cnpj=filial.get("cnpj"),
            pdv=str(filial.get("pdv") or "01"),
            erp_online=erp_online,
            erp_host=DB_ERP_CONFIG.get("host", "localhost"),
            erp_port=DB_ERP_CONFIG.get("port", 5433),
            vector_db_online=vector_online,
            vector_db_host=DB_VECTOR_CONFIG.get("host", "localhost"),
            vector_db_port=DB_VECTOR_CONFIG.get("port", 5434),
            latency_erp_ms=round(lat_erp, 2) if lat_erp else None,
            total_products_indexed=t_stats.get("total_rows"),
            cache_hit_ratio_percent=db_stats.get("cache_hit_ratio_percent"),
            active_connections=db_stats.get("active_connections"),
        )

    # -------------------------------------------------------------------------
    # EXECUÇÃO DIRETA DE FERRAMENTAS ANALÍTICAS (HEADLESS INTENT CALL)
    # -------------------------------------------------------------------------

    async def execute_tool(
        self,
        tool_name: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Executa uma das 11 ferramentas analíticas do posto diretamente,
        sem passar pela síntese e consumo de tokens do LLM.
        Alias canônico conforme especificado no roadmap e requisitos da Fase 1.
        """
        return await self.execute_tool_direct(tool_name, params)

    async def execute_tool_direct(
        self,
        tool_name: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Executa uma das 11 ferramentas analíticas do posto diretamente,
        sem passar pela síntese e consumo de tokens do LLM.
        Ideal para endpoints de dashboards, automações e relatórios fixos.
        """
        p = params or {}
        norm_name = tool_name.strip().lower().replace("-", "_").replace(" ", "_")
        t0 = time.perf_counter()

        def _run_sync():
            # Mapeamento universal de nomes de intenções e ferramentas
            if norm_name in (
                "auditoria_turno", "auditar_fechamento_turno", "fechamento_turno",
                "turno", "conciliacao_turno", "auditoria_de_turno", "fechamento_de_turno",
                "conferencia_turno", "conferencia_pista"
            ):
                data_val = p.get("data")
                turno_val = p.get("turno")
                return self.tools.auditar_fechamento_turno(data=data_val, turno=turno_val)

            elif norm_name in (
                "previsao_tanques", "prever_esgotamento_tanques", "runout", "run_out",
                "tanques", "esgotamento_tanques", "autonomia_tanques", "autonomia"
            ):
                comb_val = p.get("filtro_combustivel") or p.get("combustivel")
                return self.tools.prever_esgotamento_tanques(filtro_combustivel=comb_val)

            elif norm_name in (
                "desempenho_pista_frentistas", "auditar_desempenho_pista_frentistas",
                "desempenho_frentistas", "frentistas", "pista", "desempenho_pista",
                "vazao_bicos", "ranking_frentistas"
            ):
                return self.tools.auditar_desempenho_pista_frentistas(
                    data=p.get("data"),
                    turno=p.get("turno"),
                    frentista=p.get("frentista"),
                    bico=p.get("bico"),
                )

            elif norm_name in (
                "lmc_anp", "gerar_relatorio_lmc_anp", "lmc", "relatorio_lmc",
                "lmc_oficial", "livro_lmc"
            ):
                return self.tools.gerar_relatorio_lmc_anp(
                    data=p.get("data"),
                    combustivel=p.get("combustivel"),
                    tanque=p.get("tanque"),
                )

            elif norm_name in (
                "vendas_analitico", "consultar_analise_vendas_erp", "vendas",
                "analise_vendas", "faturamento"
            ):
                tipo_val = p.get("tipo", "mais_vendidos")
                return self.tools.consultar_analise_vendas_erp(tipo=tipo_val)

            elif norm_name in (
                "conveniencia_vendas_cruzadas", "auditar_cesta_conveniencia_vendas_cruzadas",
                "cesta", "market_basket", "vendas_cruzadas", "conveniencia", "combos"
            ):
                return self.tools.auditar_cesta_conveniencia_vendas_cruzadas(
                    filtro_produto=p.get("filtro_produto") or p.get("produto"),
                    min_lift=float(p.get("min_lift", 1.2)),
                    limit=int(p.get("limit", 10)),
                )

            elif norm_name in (
                "sre_metricas", "obter_telemetria_sre", "telemetria",
                "sre", "metricas", "saude_banco"
            ):
                res = self.tools.obter_telemetria_sre()
                res["semantic_router_metrics"] = self.router.get_sre_telemetry()
                return res

            elif norm_name in (
                "dados_filial", "dados_cadastrais_filial", "filial",
                "cadastro_filial", "empresa"
            ):
                return self.get_dados_filial(force_reload=p.get("reload", False))

            elif norm_name in (
                "estoque_posicao", "consultar_estoque_erp", "estoque", "saldo_estoque"
            ):
                return self.tools.consultar_estoque_erp(termo=p.get("termo", ""))

            elif norm_name in (
                "clientes_ranking", "consultar_clientes_erp", "clientes", "ranking_clientes"
            ):
                return self.tools.consultar_clientes_erp(termo=p.get("termo", ""))

            elif norm_name in (
                "catalogo_produtos", "buscar_produtos_catalogo", "catalogo",
                "produtos", "busca_produtos"
            ):
                query_txt = (p.get("termo") or p.get("query") or "").strip() or "combustivel"
                return self.tools.buscar_produtos_catalogo(
                    termo=query_txt,
                    top_k=int(p.get("top_k", 5)),
                    grupo_filter=p.get("grupo"),
                )

            else:
                raise ValueError(f"Ferramenta desconhecida ou não suportada: '{tool_name}'")

        try:
            result_data = await asyncio.to_thread(_run_sync)
            lat_ms = (time.perf_counter() - t0) * 1000
            return {
                "status": "success",
                "tool_name": norm_name,
                "latency_ms": round(lat_ms, 2),
                "data": result_data,
            }
        except Exception as e:
            lat_ms = (time.perf_counter() - t0) * 1000
            return {
                "status": "error",
                "tool_name": norm_name,
                "latency_ms": round(lat_ms, 2),
                "error": str(e),
            }

    # -------------------------------------------------------------------------
    # CONSTRUÇÃO DO PROMPT SISTÊMICO ORIENTADO A POSTO
    # -------------------------------------------------------------------------

    def _build_prompt_sistema(
        self,
        pergunta_sanitizada: str,
        contexto_sanitizado: str,
        historico_formatado: str,
    ) -> str:
        dados_filial = self.get_dados_filial()
        return f"""Você é a AURA (Autonomous Unified Retail Assistant), a Assistente de Prontidão e Gerente Supervisora do Posto de Combustíveis e Loja de Conveniência.
Seu papel fundamental é o suporte à tomada de decisão rápida e cirúrgica do gestor: o usuário tirou o celular do bolso na correria da pista ou da retaguarda, precisou tomar uma decisão imediata, perguntou para você, você ilumina com diagnósticos diretos, cálculos matemáticos exatos e a melhor ação para ele bater o martelo.

Posicionamento e Demarcação:
- Você NÃO é um painel SRE de TI nem monitor passivo: o Sentinel já cuida da infraestrutura/TI de forma autônoma e o cliente já possui ERP para relatórios estáticos de telas.
- Você é a GERENTE SUPERVISORA DO POSTO: altamente eficiente, executiva, direta ao ponto, sem enrolação, saudações prolixas ou formalismos desnecessários.
- Foco total e sob demanda no que o cliente perguntou: estoques, tanques e autonomia de combustíveis, conciliação de turnos e quebra de caixa, conformidade fiscal/ANP (LMC), equipe de pista e vendas cruzadas na conveniência.

Estrutura Obrigatória de Resposta:
Toda resposta deve seguir rigorosamente a seguinte anatomia executiva:
1. DIAGNÓSTICO DIRETO NO TOPO: A primeiríssima linha deve trazer o veredito claro com ícone e destaque (ex: "🚨 **Atenção**: Tanque 1 (Gasolina Comum) crítico com 14h de autonomia", "✅ **Turno Conforme**: Turno 1 conciliado sem furos de caixa ou pista", "⚠️ **Alerta ANP**: Variação volumétrica de +0.82% acima do teto de ±0.6%").
2. NÚMEROS E CÁLCULOS COMPROVADOS: Apresente os dados objetivos e cálculos matemáticos das ferramentas do ERP (litros, horas de autonomia, valores em R$, percentuais, comparativo físico vs escriturado), em tópicos concisos e sem rodeios.
3. AÇÃO RECOMENDADA PARA DECISÃO: O que o gestor deve fazer imediatamente (ex: "👉 **Decisão recomendada**: Emitir pedido de carreta de 15.000 L de Gasolina Comum hoje", "👉 **Decisão recomendada**: Notificar o operador do caixa sobre a quebra de R$ 85,00 antes do fechamento", "👉 **Decisão recomendada**: Ajustar o filtro do bico 004 com vazão de 21 L/min").

Dados Cadastrais da Unidade:
- Filial: {dados_filial.get('idempresa')} - {dados_filial.get('nome')}
- Razão Social: {dados_filial.get('razao_social')}
- CNPJ: {dados_filial.get('cnpj')}
- Endereço: {dados_filial.get('endereco')}
- PDV: {dados_filial.get('pdv')}

Histórico Recente da Sessão (Contexto de Continuidade):
{historico_formatado}

Informações Recuperadas pelas Ferramentas Analíticas do Posto:
{contexto_sanitizado}

Pergunta do Usuário:
"{pergunta_sanitizada}"

Diretrizes Específicas por Assunto:
1. Previsão de Esgotamento de Tanques (Run-Out Forecast) e Autonomia:
   - Diagnóstico no topo: Tanque e combustível mais crítico, percentual atual e menor autonomia.
   - Números: Volume atual, capacidade, consumo médio (L/h), autonomia projetada e espaço livre para descarga (ullage).
   - Ação para o gestor: Sugestão de pedido em múltiplos padrão de compartimento de carreta (5.000 L, 10.000 L, 15.000 L...).
2. Conciliação de Fechamento de Turno e Caixa:
   - Diagnóstico no topo: Status geral (CONCILIADO, FURO DE CAIXA, DIVERGÊNCIA DE PISTA ou TURNO EM ANDAMENTO) e Score (%).
   - Números: Divergência de encerrantes físicos vs CBC04 (litros) e confronto de combustível faturado vs declarado pelo operador por modalidade (Dinheiro, Cartão, PIX).
   - Ação para o gestor: Medida imediata sobre eventuais furos, quebras ou divergências físicas.
3. Livro de Movimentação de Combustíveis (LMC Oficial ANP Portaria 26/1992):
   - Diagnóstico no topo: Status geral ANP (CONFORME_ANP ou ALERTA_FORA_TOLERANCIA_ANP) no período.
   - Números: Estoque de abertura, recebimentos, vendas, escriturado vs físico, e variação (Δ Litros e Δ %) confrontada rigorosamente com o teto regulatório de ±0.6%.
   - Ação para o gestor: Providências regulamentares ou ajuste de medição.
4. Desempenho de Pista, Ranking de Frentistas e Bicos:
   - Diagnóstico no topo: Responda direto quem lidera ou qual bico requer atenção.
   - Números: Faturamento total, volume (L), taxa de conversão de gasolina aditivada (meta: 25-30%) e vazão média dos bicos (alerta se < 25-30 L/min).
   - Ação para o gestor: Ajuste na escala ou manutenção no bico lento.
5. Vendas Cruzadas e Inteligência de Conveniência (Market Basket Analysis):
   - Diagnóstico no topo: Principal oportunidade de combo identificada e Lift atingido.
   - Números: Lift, confiança, cupons conjuntos e ticket médio.
   - Ação para o gestor: Script persuasivo de balcão para os caixas oferecerem no PDV e disposição de balcão.
6. Catálogo de Produtos e Preços:
   - Diagnóstico direto: Nome exato, código SKU, grupo e preço em R$. Se questionado sobre estoque, cite o saldo físico disponível.
7. Vendas Recentes e Faturamento:
   - Cite diretamente dados do ERP: produto, código, data/hora exata, quantidade e valor.
8. Clientes e LGPD:
   - Respeite rigorosamente a proteção de dados (nomes ofuscados quando aplicável) e realidade do PDV.
"""

    # -------------------------------------------------------------------------
    # EXECUÇÃO DA FERRAMENTA PELO ROTEADOR PARA O PIPELINE COGNITIVO
    # -------------------------------------------------------------------------

    def _resolver_contexto_ferramenta(
        self,
        pergunta: str,
        intencao: str,
        query_vector: Optional[list] = None,
    ) -> Tuple[str, Any, Optional[Dict[str, Any]], bool, float]:
        """
        Executa a ferramenta correspondente à intenção identificada e retorna o contexto formatado.
        Retorna: (contexto_extra, resultado_bruto, telemetria_retrieval, cache_hit, tool_latency_ms)
        """
        t0 = time.perf_counter()
        contexto_extra = ""
        resultado_bruto = None
        telemetria_retrieval = None
        cache_hit = False

        try:
            if intencao == "auditoria_turno":
                data_p, turno_p = extrair_data_turno(pergunta)
                resultado_bruto = self.tools.auditar_fechamento_turno(data=data_p, turno=turno_p)
                contexto_extra = f"Auditoria de Fechamento de Turno e Conciliação de Pista no ERP:\n{json.dumps(resultado_bruto, ensure_ascii=False, indent=2, default=str)}\n"

            elif intencao == "previsao_tanques":
                comb_filtro = extrair_combustivel(pergunta)
                resultado_bruto = self.tools.prever_esgotamento_tanques(filtro_combustivel=comb_filtro)
                contexto_extra = f"Previsão de Esgotamento de Combustível (Run-Out Forecast) e Sugestão de Pedidos no ERP:\n{json.dumps(resultado_bruto, ensure_ascii=False, indent=2, default=str)}\n"

            elif intencao == "desempenho_pista_frentistas":
                data_p, turno_p = extrair_data_turno(pergunta)
                frent_p = extrair_frentista(pergunta)
                bico_p = extrair_bico(pergunta)
                resultado_bruto = self.tools.auditar_desempenho_pista_frentistas(data=data_p, turno=turno_p, frentista=frent_p, bico=bico_p)
                contexto_extra = f"Auditoria Operacional de Pista, Vazão de Bicos e Desempenho de Frentistas no ERP:\n{json.dumps(resultado_bruto, ensure_ascii=False, indent=2, default=str)}\n"

            elif intencao == "lmc_anp":
                data_p, _ = extrair_data_turno(pergunta)
                comb_ou_tanque = extrair_combustivel(pergunta)
                tanque_filtro = None
                comb_filtro = None
                if comb_ou_tanque:
                    if comb_ou_tanque.isdigit() or (len(comb_ou_tanque) == 3 and comb_ou_tanque.isnumeric()):
                        tanque_filtro = comb_ou_tanque
                    else:
                        comb_filtro = comb_ou_tanque
                if not tanque_filtro:
                    m_tanque = re.search(r"\b(?:tanque|tq)\s*[-_]?\s*0*([0-9]{1,3})\b", pergunta.lower())
                    if m_tanque:
                        tanque_filtro = f"{int(m_tanque.group(1)):03d}"

                resultado_bruto = self.tools.gerar_relatorio_lmc_anp(
                    data=data_p,
                    combustivel=comb_filtro,
                    tanque=tanque_filtro,
                )
                contexto_extra = f"Livro de Movimentação de Combustíveis (LMC ANP Portaria 26/1992):\n{json.dumps(resultado_bruto, ensure_ascii=False, indent=2, default=str)}\n"

            elif intencao == "vendas_analitico":
                resultado_bruto = self.tools.consultar_analise_vendas_erp(tipo="mais_vendidos")
                contexto_extra = f"Consulta de Histórico de Vendas no ERP:\n{json.dumps(resultado_bruto, ensure_ascii=False, indent=2, default=str)}\n"

            elif intencao == "conveniencia_vendas_cruzadas":
                filtro_prod = extrair_produto_cesta(pergunta)
                resultado_bruto = self.tools.auditar_cesta_conveniencia_vendas_cruzadas(
                    filtro_produto=filtro_prod,
                    min_lift=1.2,
                    limit=10,
                )
                contexto_extra = f"Market Basket Analysis & Vendas Cruzadas da Loja de Conveniência no ERP:\n{json.dumps(resultado_bruto, ensure_ascii=False, indent=2, default=str)}\n"

            elif intencao == "sre_metricas":
                sre_metricas = self.tools.obter_telemetria_sre()
                sre_metricas["semantic_router_metrics"] = self.router.get_sre_telemetry()
                resultado_bruto = sre_metricas
                contexto_extra = f"Métricas de Observabilidade SRE do Banco PostgreSQL 16 e Roteador Semântico:\n{json.dumps(sre_metricas, ensure_ascii=False, indent=2, default=str)}\n"

            elif intencao == "dados_filial":
                resultado_bruto = self.get_dados_filial()
                contexto_extra = f"Dados da Filial:\n{json.dumps(resultado_bruto, ensure_ascii=False, indent=2, default=str)}\n"

            elif intencao == "estoque_posicao":
                resultado_bruto = self.tools.consultar_estoque_erp(termo=pergunta)
                contexto_extra = f"Posição Real de Estoque e Tanques no ERP (porta 5433):\n{json.dumps(resultado_bruto, ensure_ascii=False, indent=2, default=str)}\n"

            elif intencao == "clientes_ranking":
                resultado_bruto = self.tools.consultar_clientes_erp(termo=pergunta)
                contexto_extra = f"Dados de Clientes e Histórico de Compras no ERP (porta 5433):\n{json.dumps(resultado_bruto, ensure_ascii=False, indent=2, default=str)}\n"

            else:
                # Catálogo de produtos (RAG Híbrido HNSW + GIN FTS) com Cache Semântico
                cache_data = self.tools.rag.check_semantic_cache(pergunta, query_vector=query_vector)
                if cache_data.get("resposta_llm"):
                    cache_hit = True
                    resultado_bruto = cache_data
                    contexto_extra = cache_data["resposta_llm"]
                else:
                    grupo_filtro = extrair_grupo(pergunta)
                    busca = self.tools.buscar_produtos_catalogo(
                        pergunta,
                        top_k=5,
                        query_vector=query_vector,
                        grupo_filter=grupo_filtro,
                    )
                    resultado_bruto = busca
                    produtos = busca["results"]
                    telemetria_retrieval = busca.get("telemetry", {})
                    contexto_extra = "Produtos recuperados do catálogo por RAG Híbrido (HNSW + Full-Text Search + RRF):\n"
                    for p in produtos:
                        contexto_extra += (
                            f"- [{p.get('codpro')}] {p.get('nompro')} | Grupo: {p.get('grupo')} | "
                            f"Preço: R$ {p.get('preco', 0.0):.2f} (RRF: {p.get('rrf_score', 0.0):.4f} | "
                            f"Cosine: {p.get('cosine_similarity', 0.0):.2f} | FTS: {p.get('fts_score', 0.0):.2f})\n"
                        )
        except Exception as e:
            resultado_bruto = {"status": "error", "error": str(e)}
            contexto_extra = f"Aviso de execução da ferramenta ({intencao}): Indisponibilidade técnica ao consultar dados ({str(e)}).\n"

        tool_lat_ms = (time.perf_counter() - t0) * 1000
        return contexto_extra, resultado_bruto, telemetria_retrieval, cache_hit, tool_lat_ms

    # -------------------------------------------------------------------------
    # STREAMING ASSÍNCRONO DA AURA (ask_stream)
    # -------------------------------------------------------------------------

    async def ask_stream(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        filial_id: Optional[str] = None,
    ) -> AsyncIterator[AuraChunk]:
        """
        Gera resposta em streaming assíncrono token a token via Server-Sent Events (SSE).
        Emite blocos tipados: INTENT -> TOOL_START -> TOOL_RESULT -> DELTA -> TELEMETRY -> DONE.
        """
        sess_id = session_id or str(uuid.uuid4())
        t_id = tenant_id or self.tenant_id
        f_id = filial_id or self.filial_id
        t_global_start = time.perf_counter()
        q_limpa = (query or "").strip()

        if not q_limpa:
            msg_vazia = "Olá! Como posso ajudar você hoje no posto ou na loja de conveniência?"
            yield AuraChunk(chunk_type=AuraChunkType.DELTA, text=msg_vazia, session_id=sess_id)
            yield AuraChunk(chunk_type=AuraChunkType.DONE, text=msg_vazia, session_id=sess_id)
            return

        # 1. Roteamento Semântico Vetorial / Heurístico
        intencao, confianca, telemetria_rota = self.router.route(q_limpa)
        query_vector = telemetria_rota.get("query_vector")

        yield AuraChunk(
            chunk_type=AuraChunkType.INTENT,
            text=intencao,
            data={
                "intent": intencao,
                "confidence": confianca,
                "routing_telemetry": telemetria_rota,
            },
            session_id=sess_id,
        )

        yield AuraChunk(
            chunk_type=AuraChunkType.TOOL_START,
            text=f"Executando ferramenta para intenção '{intencao}'...",
            data={"intent": intencao},
            session_id=sess_id,
        )

        # 2. Execução da Ferramenta correspondente
        (
            contexto_extra,
            resultado_bruto,
            telemetria_retrieval,
            cache_hit,
            tool_latency_ms,
        ) = await asyncio.to_thread(
            self._resolver_contexto_ferramenta,
            q_limpa,
            intencao,
            query_vector,
        )

        # 3. Tratamento de Cache Hit Semântico
        if cache_hit:
            resposta_cache = contexto_extra
            total_e2e_ms = (time.perf_counter() - t_global_start) * 1000

            yield AuraChunk(
                chunk_type=AuraChunkType.CACHE_HIT,
                text=resposta_cache,
                data={
                    "similarity": resultado_bruto.get("cosine_similarity", 1.0) if isinstance(resultado_bruto, dict) else 1.0,
                    "cache_cost": "zero",
                },
                session_id=sess_id,
            )
            yield AuraChunk(
                chunk_type=AuraChunkType.DELTA,
                text=resposta_cache,
                session_id=sess_id,
            )

            # Persiste mensagem na sessão
            self.session_memory.save_message(
                session_id=sess_id,
                role="user",
                content=q_limpa,
                intent=intencao,
                tenant_id=t_id,
                filial_id=f_id,
            )
            self.session_memory.save_message(
                session_id=sess_id,
                role="assistant",
                content=resposta_cache,
                intent=intencao,
                tenant_id=t_id,
                filial_id=f_id,
                metadata={"cache_hit": True},
            )

            yield AuraChunk(
                chunk_type=AuraChunkType.TELEMETRY,
                data={
                    "intent": intencao,
                    "cache_hit": True,
                    "tool_latency_ms": round(tool_latency_ms, 2),
                    "total_e2e_ms": round(total_e2e_ms, 2),
                },
                session_id=sess_id,
            )
            yield AuraChunk(
                chunk_type=AuraChunkType.DONE,
                text=resposta_cache,
                session_id=sess_id,
            )
            return

        yield AuraChunk(
            chunk_type=AuraChunkType.TOOL_RESULT,
            data={
                "intent": intencao,
                "latency_ms": round(tool_latency_ms, 2),
                "has_structured_data": resultado_bruto is not None,
                "result": resultado_bruto,
            },
            session_id=sess_id,
        )

        # 4. Blindagem LGPD e Sanitização de Contexto e Pergunta
        # Se houver contexto extra injetado pelo chamador (perfil, canal, etc), anexa ao contexto
        if context:
            try:
                ctx_extra_str = json.dumps(context, ensure_ascii=False, indent=2, default=str)
                contexto_extra = f"Contexto Operacional do Chamador:\n{ctx_extra_str}\n\n" + contexto_extra
            except Exception:
                contexto_extra = f"Contexto Operacional do Chamador:\n{str(context)}\n\n" + contexto_extra

        contexto_sanitizado, counts_ctx = central_log_sanitizer.sanitize_text(contexto_extra)
        pergunta_sanitizada, counts_perg = central_log_sanitizer.sanitize_text(q_limpa)
        total_redacted = sum(counts_ctx.values()) + sum(counts_perg.values())

        # 5. Recuperação de Histórico de Continuidade
        historico_formatado = self.session_memory.format_history_for_prompt(sess_id, limit=6)

        # 6. Montagem do Prompt Sistêmico
        prompt_sistema = self._build_prompt_sistema(
            pergunta_sanitizada=pergunta_sanitizada,
            contexto_sanitizado=contexto_sanitizado,
            historico_formatado=historico_formatado,
        )

        # 7. Streaming com Google Gemini e Fallback Resiliente
        t_llm_start = time.perf_counter()
        ttft_ms = None
        texto_completo: List[str] = []
        sucesso_llm = False

        for m_name in FALLBACK_MODELS:
            try:
                model = genai.GenerativeModel(m_name)
                # Invoca streaming assíncrono nativo
                response_stream = await model.generate_content_async(
                    prompt_sistema,
                    stream=True,
                    request_options={"timeout": 12},
                )

                async for chunk in response_stream:
                    try:
                        chunk_text = chunk.text
                    except Exception:
                        continue

                    if not chunk_text:
                        continue

                    if ttft_ms is None:
                        ttft_ms = (time.perf_counter() - t_llm_start) * 1000

                    texto_completo.append(chunk_text)
                    yield AuraChunk(
                        chunk_type=AuraChunkType.DELTA,
                        text=chunk_text,
                        session_id=sess_id,
                    )

                if texto_completo:
                    sucesso_llm = True
                    break

            except Exception:
                # Fallback para o próximo modelo da lista
                continue

        total_llm_ms = (time.perf_counter() - t_llm_start) * 1000
        resposta_final = "".join(texto_completo)

        if not sucesso_llm or not resposta_final:
            resposta_final = "Não foi possível obter resposta dos modelos da AURA no momento. Por favor, tente novamente em instantes."
            yield AuraChunk(
                chunk_type=AuraChunkType.ERROR,
                text=resposta_final,
                session_id=sess_id,
            )

        # 8. Salvamento no Cache Semântico (se catálogo)
        if intencao == "catalogo_produtos" and not cache_hit and query_vector and sucesso_llm:
            frases_bloqueio = ["não há registros", "erro", "indisponível", "não foi possível", "não encontrei"]
            if not any(fb in resposta_final.lower() for fb in frases_bloqueio):
                try:
                    produtos_salvar = resultado_bruto.get("results", []) if isinstance(resultado_bruto, dict) else []
                    await asyncio.to_thread(
                        self.tools.rag.save_semantic_cache,
                        q_limpa,
                        query_vector,
                        resposta_final,
                        produtos_salvar,
                    )
                except Exception:
                    pass

        # 9. Persistência de Histórico de Conversa
        self.session_memory.save_message(
            session_id=sess_id,
            role="user",
            content=q_limpa,
            intent=intencao,
            tenant_id=t_id,
            filial_id=f_id,
        )
        self.session_memory.save_message(
            session_id=sess_id,
            role="assistant",
            content=resposta_final,
            intent=intencao,
            tenant_id=t_id,
            filial_id=f_id,
            metadata={"tool": intencao, "ttft_ms": round(ttft_ms or 0, 2)},
        )

        # 10. Emissão de Telemetria e Conclusão
        total_e2e_ms = (time.perf_counter() - t_global_start) * 1000
        telemetria_final = {
            "intent": intencao,
            "confidence": confianca,
            "routing_method": telemetria_rota.get("method"),
            "tool_latency_ms": round(tool_latency_ms, 2),
            "ttft_ms": round(ttft_ms or 0, 2),
            "llm_total_ms": round(total_llm_ms, 2),
            "total_e2e_ms": round(total_e2e_ms, 2),
            "lgpd_redacted_count": total_redacted,
        }
        if telemetria_retrieval:
            telemetria_final["retrieval"] = telemetria_retrieval

        yield AuraChunk(
            chunk_type=AuraChunkType.TELEMETRY,
            data=telemetria_final,
            session_id=sess_id,
        )

        yield AuraChunk(
            chunk_type=AuraChunkType.DONE,
            text=resposta_final,
            data={"session_id": sess_id, "intent": intencao},
            session_id=sess_id,
        )

    # -------------------------------------------------------------------------
    # RESPOSTA COMPLETA ASSÍNCRONA (ask)
    # -------------------------------------------------------------------------

    async def ask(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        filial_id: Optional[str] = None,
    ) -> AuraResponse:
        """
        Executa o pipeline completo da AURA de forma assíncrona,
        acumulando a resposta e retornando o modelo estruturado AuraResponse.
        """
        sess_id = session_id or str(uuid.uuid4())
        texto_chunks: List[str] = []
        intencao_detectada = "desconhecida"
        confianca = 0.0
        metodo_rota = "heuristica"
        cache_hit = False
        telemetria = {}
        tool_result = None

        async for chunk in self.ask_stream(
            query,
            context=context,
            session_id=sess_id,
            tenant_id=tenant_id,
            filial_id=filial_id,
        ):
            if chunk.chunk_type == AuraChunkType.INTENT and chunk.data:
                intencao_detectada = chunk.data.get("intent", intencao_detectada)
                confianca = chunk.data.get("confidence", 0.0)
                metodo_rota = chunk.data.get("routing_telemetry", {}).get("method", metodo_rota)

            elif chunk.chunk_type == AuraChunkType.CACHE_HIT:
                cache_hit = True

            elif chunk.chunk_type == AuraChunkType.TOOL_RESULT and chunk.data:
                tool_result = chunk.data.get("result", chunk.data)

            elif chunk.chunk_type == AuraChunkType.DELTA and chunk.text:
                texto_chunks.append(chunk.text)

            elif chunk.chunk_type == AuraChunkType.TELEMETRY and chunk.data:
                telemetria = chunk.data

        texto_final = "".join(texto_chunks)

        return AuraResponse(
            session_id=sess_id,
            query=query,
            response_text=texto_final,
            intent=intencao_detectada,
            confidence=confianca,
            routing_method=metodo_rota,
            tool_name=intencao_detectada,
            tool_result=tool_result,
            telemetry=telemetria,
            cache_hit=cache_hit,
            lgpd_sanitized_count=telemetria.get("lgpd_redacted_count", 0),
        )
