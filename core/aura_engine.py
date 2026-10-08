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
import logging
from contextlib import contextmanager

logger = logging.getLogger("aura.engine")
from datetime import datetime, timezone
from pathlib import Path
from enum import Enum
from typing import AsyncIterator, Optional, Dict, Any, List, Tuple, Union

from pydantic import BaseModel, Field, ConfigDict, model_validator
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
from core.semantic_router import SemanticRouter, classificar_intencao_heuristica, RETRY_REGEX
from core.schemas.idempotency import generate_tool_call_id, generate_action_id
from core.schemas.genui import (
    GenUIEnvelope,
    GenUIActionOption,
    GenUIActionResult,
    ExecutiveMetric,
    ExecutiveImpactProjection,
    ExecutiveEvidenceItem,
    ExecutiveDecisionProps,
    ActionExecuteRequest,
    ActionVoucher,
    generate_action_voucher_signature,
    verify_action_voucher_signature,
    FuelMarginItem,
    PaymentFeeImpactItem,
    MarginAnalysisProps,
    ScenarioPoint,
    PredictiveScenarioProps,
    BenchmarkComparisonItem,
    BenchmarkComparisonProps,
    FinancialLeakItem,
    FinancialLeakAuditProps,
    UpsellComboItem,
    BasketUpsellStrategyProps,
)
from core.config import is_genui_enabled
from core.telemetry import AuraSRETelemetry

# =============================================================================
# CONTRATOS PYDANTIC & ENUMS DA AURA
# =============================================================================

class AuraChunkType(str, Enum):
    """Tipos de blocos emitidos no streaming assíncrono da AURA."""
    DELTA = "delta"                      # Token ou fragmento textual de resposta (Resumo Executivo)
    INTENT = "intent"                    # Detecção de intenção pelo roteador semântico
    TOOL_START = "tool_start"            # Notificação de início de execução de ferramenta
    TOOL_RESULT = "tool_result"          # Dados estruturados retornados pela ferramenta
    UI_SKELETON = "ui_skeleton"          # Sinal para exibir esqueleto do widget (< 100ms)
    UI_DELTA = "ui_delta"                # Fragmentos fracionados de JSON de props
    UI_COMPLETE = "ui_complete"          # Payload completo e validado da ferramenta (GenUIEnvelope)
    UI_ACTION_RESULT = "ui_action_result"# Confirmação de ação transacional executada (F1-01)
    UI_ACTION_FEEDBACK = "ui_action_feedback"# Feedback assíncrono com Action Voucher (Protocolo SSE v1.0)
    CACHE_HIT = "cache_hit"              # Resposta recuperada instantaneamente do cache semântico
    TELEMETRY = "telemetry"              # Métricas de observabilidade e latência SRE
    ERROR = "error"                      # Notificação de erro no processamento
    DONE = "done"                        # Finalização da requisição


class AuraChunk(BaseModel):
    """Envelope de transmissão SSE / Streaming para canais Web, WhatsApp e Parceiros."""
    model_config = ConfigDict(extra="ignore")

    chunk_type: AuraChunkType = Field(..., description="Tipo do bloco de streaming")
    text: Optional[str] = Field(default=None, description="Conteúdo textual do token ou mensagem")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Metadados ou carga útil estruturada")
    session_id: Optional[str] = Field(default=None, description="ID da sessão vinculada")
    tool_call_id: Optional[str] = Field(default=None, description="UUID da invocação da ferramenta (RFC 4122 v4)")
    component_name: Optional[str] = Field(default=None, description="Nome do componente no SecureComponentRegistry")
    title: Optional[str] = Field(default=None, description="Título contextual ou mensagem de status do skeleton")
    envelope: Optional[Dict[str, Any]] = Field(default=None, description="Envelope canônico GenUI estruturado")

    @model_validator(mode="after")
    def sync_envelope_and_data(self) -> "AuraChunk":
        """Garante que envelope e data estejam sincronizados em chunks UI_COMPLETE."""
        if self.chunk_type == AuraChunkType.UI_COMPLETE:
            if self.envelope is not None and self.data is None:
                self.data = self.envelope
            elif self.data is not None and self.envelope is None:
                self.envelope = self.data
        return self

    def to_dict(self) -> Dict[str, Any]:
        """Serializa o chunk em dicionário seguro para consumo SSE ou JSON."""
        return self.model_dump(mode="json", exclude_none=True)

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
    tool_call_id: Optional[str] = Field(default=None, description="Identificador único da chamada de ferramenta")
    envelope: Optional[Dict[str, Any]] = Field(default=None, description="Envelope canônico GenUI serializado")
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
                    tool_call_id TEXT,
                    name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES aura_sessions(session_id)
                );
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_aura_messages_session 
                ON aura_messages(session_id, created_at);
            """)

            # Migracao dinamica de colunas para bancos SQLite preexistentes
            try:
                cur = conn.execute("PRAGMA table_info(aura_messages);")
                colunas = {row["name"] for row in cur.fetchall()}
                if "tool_call_id" not in colunas:
                    conn.execute("ALTER TABLE aura_messages ADD COLUMN tool_call_id TEXT;")
                if "name" not in colunas:
                    conn.execute("ALTER TABLE aura_messages ADD COLUMN name TEXT;")
            except Exception:
                pass

            # Tabela de Action Vouchers auditaveis para idempotencia estrita (F5-01)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS aura_action_vouchers (
                    voucher_id TEXT PRIMARY KEY,
                    action_id TEXT UNIQUE NOT NULL,
                    tool_call_id TEXT NOT NULL,
                    session_id TEXT,
                    action_name TEXT NOT NULL,
                    action_type TEXT DEFAULT 'mutation',
                    operator_id TEXT,
                    status TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    payload TEXT,
                    details TEXT,
                    signature TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            try:
                cur_v = conn.execute("PRAGMA table_info(aura_action_vouchers);")
                colunas_v = {row["name"] for row in cur_v.fetchall()}
                if "timestamp" not in colunas_v:
                    conn.execute("ALTER TABLE aura_action_vouchers ADD COLUMN timestamp TEXT;")
            except Exception:
                pass

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_aura_vouchers_action 
                ON aura_action_vouchers(action_id);
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_aura_vouchers_session 
                ON aura_action_vouchers(session_id);
            """)

            # Tabela duravel da trilha de auditoria transacional (F7-04)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS aura_action_audit_log (
                    audit_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    session_id TEXT,
                    tool_call_id TEXT NOT NULL,
                    action_id TEXT NOT NULL,
                    action_name TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    operator_id TEXT,
                    operator_role TEXT,
                    authorized INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    details TEXT,
                    client_ip TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_aura_audit_action 
                ON aura_action_audit_log(action_id);
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_aura_audit_session 
                ON aura_action_audit_log(session_id);
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_aura_audit_status 
                ON aura_action_audit_log(status);
            """)

            # Tabela duravel de telemetria e observabilidade SRE (F9-02)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS aura_sre_telemetry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    metric_type TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    session_id TEXT,
                    tool_call_id TEXT,
                    details TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_aura_sre_metric_type 
                ON aura_sre_telemetry(metric_type);
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
        tool_call_id: Optional[str] = None,
        name: Optional[str] = None,
    ):
        """Salva uma mensagem de usuario, assistente ou ferramenta (role: tool) na sessao."""
        eff_tool_call_id = tool_call_id or (metadata.get("tool_call_id") if isinstance(metadata, dict) else None)
        eff_name = name or (metadata.get("name") if isinstance(metadata, dict) else None)

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
                INSERT INTO aura_messages (session_id, role, content, intent, metadata, tool_call_id, name)
                VALUES (?, ?, ?, ?, ?, ?, ?);
            """, (session_id, role, content, intent, meta_json, eff_tool_call_id, eff_name))
            conn.commit()

    def get_history(self, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Recupera as ultimas mensagens ordenadas cronologicamente."""
        with self._connection() as conn:
            cur = conn.execute("""
                SELECT role, content, intent, created_at, metadata, tool_call_id, name
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

            row_keys = r.keys() if hasattr(r, "keys") else []
            t_id = r["tool_call_id"] if "tool_call_id" in row_keys else None
            n_val = r["name"] if "name" in row_keys else None

            msg_item = {
                "role": r["role"],
                "content": r["content"],
                "intent": r["intent"],
                "created_at": r["created_at"],
                "metadata": meta,
            }
            if t_id:
                msg_item["tool_call_id"] = t_id
            elif "tool_call_id" in meta:
                msg_item["tool_call_id"] = meta["tool_call_id"]

            if n_val:
                msg_item["name"] = n_val
            elif "name" in meta:
                msg_item["name"] = meta["name"]

            mensagens.append(msg_item)
        return mensagens

    def format_history_for_prompt(self, session_id: str, limit: int = 6) -> str:
        """Formata o historico para injecao limpa no prompt de continuidade do LLM."""
        historico = self.get_history(session_id, limit=limit)
        if not historico:
            return "Nenhum histórico anterior nesta sessão."

        linhas = []
        for msg in historico:
            role = msg.get("role", "")
            if role == "user":
                rotulo = "Usuário"
            elif role == "tool":
                act_name = msg.get("name") or "Ação de Sistema"
                rotulo = f"Ação Confirmada [{act_name}]"
            elif role == "assistant":
                rotulo = "AURA"
            else:
                rotulo = role.capitalize()

            conteudo = (msg.get("content") or "").replace("\n", " ")
            if len(conteudo) > 400:
                conteudo = conteudo[:400] + "..."
            linhas.append(f"- {rotulo}: {conteudo}")
        return "\n".join(linhas)

    def get_history_as_messages(self, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Recupera historico formatado em lista canonica de dicionarios para IA de nuvem."""
        historico = self.get_history(session_id, limit=limit)
        resultado = []
        for msg in historico:
            item = {
                "role": msg.get("role", "user"),
                "content": msg.get("content", ""),
            }
            if msg.get("role") == "tool":
                if msg.get("tool_call_id"):
                    item["tool_call_id"] = msg["tool_call_id"]
                if msg.get("name"):
                    item["name"] = msg["name"]
            resultado.append(item)
        return resultado

    def save_action_voucher(
        self,
        voucher: ActionVoucher,
        session_id: str = "",
        operator_id: str = "",
        action_type: str = "mutation",
        payload: Optional[Dict[str, Any]] = None,
    ):
        """Salva um Action Voucher homologado garantindo idempotencia duravel no SQLite."""
        details_json = json.dumps(voucher.details, ensure_ascii=False) if voucher.details else "{}"
        payload_json = json.dumps(payload, ensure_ascii=False) if payload else "{}"
        with self._connection() as conn:
            conn.execute("""
                INSERT INTO aura_action_vouchers (
                    voucher_id, action_id, tool_call_id, session_id, action_name,
                    action_type, operator_id, status, timestamp, payload, details, signature
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(action_id) DO UPDATE SET
                    status = excluded.status,
                    signature = excluded.signature;
            """, (
                voucher.voucher_id,
                voucher.action_id,
                voucher.tool_call_id,
                session_id,
                voucher.action_name,
                action_type,
                operator_id,
                voucher.status,
                voucher.timestamp,
                payload_json,
                details_json,
                voucher.signature,
            ))
            conn.commit()

    def get_action_voucher(self, action_id: str) -> Optional[ActionVoucher]:
        """Recupera um Action Voucher pelo action_id para validacao de idempotencia estrita."""
        with self._connection() as conn:
            cur = conn.execute("""
                SELECT voucher_id, action_id, tool_call_id, status, timestamp, action_name, details, signature
                FROM aura_action_vouchers
                WHERE action_id = ?;
            """, (action_id,))
            row = cur.fetchone()

        if not row:
            return None

        details_dict = {}
        if row["details"]:
            try:
                details_dict = json.loads(row["details"])
            except Exception:
                details_dict = {}

        return ActionVoucher(
            voucher_id=row["voucher_id"],
            action_id=row["action_id"],
            tool_call_id=row["tool_call_id"],
            status=row["status"],
            timestamp=str(row["timestamp"]),
            action_name=row["action_name"],
            details=details_dict,
            signature=row["signature"],
        )

    def get_action_vouchers_for_session(self, session_id: str) -> List[ActionVoucher]:
        """Recupera todos os vouchers homologados em uma determinada sessao."""
        with self._connection() as conn:
            cur = conn.execute("""
                SELECT voucher_id, action_id, tool_call_id, status, timestamp, action_name, details, signature
                FROM aura_action_vouchers
                WHERE session_id = ?
                ORDER BY created_at ASC;
            """, (session_id,))
            rows = cur.fetchall()

        vouchers = []
        for row in rows:
            details_dict = {}
            if row["details"]:
                try:
                    details_dict = json.loads(row["details"])
                except Exception:
                    details_dict = {}
            vouchers.append(ActionVoucher(
                voucher_id=row["voucher_id"],
                action_id=row["action_id"],
                tool_call_id=row["tool_call_id"],
                status=row["status"],
                timestamp=str(row["timestamp"]),
                action_name=row["action_name"],
                details=details_dict,
                signature=row["signature"],
            ))
        return vouchers

    def save_audit_log(
        self,
        audit_id: Optional[str] = None,
        session_id: str = "",
        tool_call_id: str = "",
        action_id: str = "",
        action_name: str = "",
        action_type: str = "mutation",
        operator_id: str = "",
        operator_role: str = "gerente",
        authorized: bool = True,
        status: str = "APPROVED",
        details: Optional[Dict[str, Any]] = None,
        client_ip: Optional[str] = None,
        timestamp: Optional[str] = None,
    ) -> str:
        """Registra uma tentativa de execucao de acao na trilha de auditoria duravel (F7-04)."""
        eff_audit_id = audit_id or str(uuid.uuid4())
        ts = timestamp or datetime.now(timezone.utc).isoformat()
        details_json = json.dumps(details, ensure_ascii=False, default=str) if details else "{}"
        norm_status = str(status).strip().upper() if status else "APPROVED"
        auth_int = 1 if authorized else 0

        with self._connection() as conn:
            conn.execute("""
                INSERT INTO aura_action_audit_log (
                    audit_id, timestamp, session_id, tool_call_id, action_id,
                    action_name, action_type, operator_id, operator_role,
                    authorized, status, details, client_ip
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(audit_id) DO UPDATE SET
                    status = excluded.status,
                    details = excluded.details;
            """, (
                eff_audit_id,
                ts,
                session_id,
                tool_call_id,
                action_id,
                action_name,
                action_type,
                operator_id,
                operator_role,
                auth_int,
                norm_status,
                details_json,
                client_ip,
            ))
            conn.commit()
        return eff_audit_id

    def get_audit_logs(
        self,
        session_id: Optional[str] = None,
        action_id: Optional[str] = None,
        operator_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Recupera registros da trilha de auditoria duravel com filtros opcionais (F7-04)."""
        query = """
            SELECT audit_id, timestamp, session_id, tool_call_id, action_id,
                   action_name, action_type, operator_id, operator_role,
                   authorized, status, details, client_ip, created_at
            FROM aura_action_audit_log
            WHERE 1=1
        """
        params: List[Any] = []
        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)
        if action_id:
            query += " AND action_id = ?"
            params.append(action_id)
        if operator_id:
            query += " AND operator_id = ?"
            params.append(operator_id)
        if status:
            query += " AND status = ?"
            params.append(str(status).strip().upper())

        query += " ORDER BY rowid DESC LIMIT ?"
        params.append(max(1, min(500, int(limit))))

        with self._connection() as conn:
            cur = conn.execute(query, tuple(params))
            rows = cur.fetchall()

        logs = []
        for r in rows:
            det = {}
            if r["details"]:
                try:
                    det = json.loads(r["details"])
                except Exception:
                    det = {}
            logs.append({
                "audit_id": r["audit_id"],
                "timestamp": str(r["timestamp"]),
                "session_id": r["session_id"],
                "tool_call_id": r["tool_call_id"],
                "action_id": r["action_id"],
                "action_name": r["action_name"],
                "action_type": r["action_type"],
                "operator_id": r["operator_id"],
                "operator_role": r["operator_role"],
                "authorized": bool(r["authorized"]),
                "status": r["status"],
                "details": det,
                "client_ip": r["client_ip"],
            })
        return logs

    def save_telemetry_metric(
        self,
        metric_type: str,
        metric_value: float,
        session_id: Optional[str] = None,
        tool_call_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        timestamp: Optional[str] = None,
    ):
        """Salva um evento de telemetria SRE no SQLite de forma duravel e nao-bloqueante (F9-02)."""
        ts = timestamp or datetime.now(timezone.utc).isoformat()
        details_json = json.dumps(details, ensure_ascii=False, default=str) if details else "{}"
        try:
            with self._connection() as conn:
                conn.execute("""
                    INSERT INTO aura_sre_telemetry (
                        timestamp, metric_type, metric_value, session_id, tool_call_id, details
                    )
                    VALUES (?, ?, ?, ?, ?, ?);
                """, (ts, str(metric_type), float(metric_value), session_id, tool_call_id, details_json))
                conn.commit()
        except Exception:
            pass

    def get_telemetry_metrics_records(
        self,
        metric_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Recupera registros duraveis de telemetria para auditoria e analise SRE."""
        query = "SELECT id, timestamp, metric_type, metric_value, session_id, tool_call_id, details FROM aura_sre_telemetry"
        params: List[Any] = []
        if metric_type:
            query += " WHERE metric_type = ?"
            params.append(str(metric_type))
        query += " ORDER BY id DESC LIMIT ?"
        params.append(max(1, min(1000, int(limit))))

        try:
            with self._connection() as conn:
                cur = conn.execute(query, tuple(params))
                rows = cur.fetchall()
        except Exception:
            return []

        records = []
        for r in rows:
            det = {}
            if r["details"]:
                try:
                    det = json.loads(r["details"])
                except Exception:
                    det = {}
            records.append({
                "id": r["id"],
                "timestamp": str(r["timestamp"]),
                "metric_type": r["metric_type"],
                "metric_value": float(r["metric_value"]),
                "session_id": r["session_id"],
                "tool_call_id": r["tool_call_id"],
                "details": det,
            })
        return records

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
# MAPEAMENTO DO CATÁLOGO DE COMPONENTES GENUI & BUILDER CANÔNICO
# =============================================================================

GENUI_COMPONENT_REGISTRY_MAP: Dict[str, Dict[str, str]] = {
    "mentoria_decisao": {
        "component_name": "render_ExecutiveDecisionMentorUI",
        "client_component": "ExecutiveDecisionMentorUI",
        "title": "Processando diagnóstico executivo e mentoria de decisões...",
    },
    "executive_briefing": {
        "component_name": "render_ExecutiveDecisionMentorUI",
        "client_component": "ExecutiveDecisionMentorUI",
        "title": "Gerando briefing executivo do negócio...",
    },
    "comparativo_turnos": {
        "component_name": "render_BenchmarkComparisonUI",
        "client_component": "BenchmarkComparisonUI",
        "title": "Comparando desempenho entre turnos e operadores...",
    },
    "analise_margem": {
        "component_name": "render_MarginAnalysisUI",
        "client_component": "MarginAnalysisUI",
        "title": "Analisando margem de rentabilidade e taxas de cartões...",
    },
    "cenario_preditivo": {
        "component_name": "render_PredictiveScenarioUI",
        "client_component": "PredictiveScenarioUI",
        "title": "Simulando cenários preditivos e elasticidade de demanda...",
    },
    "simulacao_preditiva": {
        "component_name": "render_PredictiveScenarioUI",
        "client_component": "PredictiveScenarioUI",
        "title": "Simulando cenários preditivos e elasticidade de demanda...",
    },
    "benchmark_comparativo": {
        "component_name": "render_BenchmarkComparisonUI",
        "client_component": "BenchmarkComparisonUI",
        "title": "Comparando performance contra benchmarks e concorrência...",
    },
    "auditoria_fuga_financeira": {
        "component_name": "render_FinancialLeakAuditUI",
        "client_component": "FinancialLeakAuditUI",
        "title": "Auditando quebras de caixa, sangrias e conciliação TEF...",
    },
    "auditoria_quebras": {
        "component_name": "render_FinancialLeakAuditUI",
        "client_component": "FinancialLeakAuditUI",
        "title": "Auditando quebras de caixa, sangrias e conciliação TEF...",
    },
    "previsao_tanques": {
        "component_name": "render_TankRunOutForecastUI",
        "client_component": "TankForecastWidget",
        "title": "Analisando autonomia e volumetria dos tanques...",
    },
    "auditoria_turno": {
        "component_name": "render_ShiftReconciliationUI",
        "client_component": "ShiftReconciliationWidget",
        "title": "Auditando fechamento de turno e conciliação de caixa...",
    },
    "lmc_anp": {
        "component_name": "render_LMCReportUI",
        "client_component": "LMCReportWidget",
        "title": "Verificando conformidade do LMC (Portaria ANP nº 26)...",
    },
    "desempenho_pista_frentistas": {
        "component_name": "render_PumpPerformanceUI",
        "client_component": "PumpPerformanceWidget",
        "title": "Analisando desempenho de pista, frentistas e vazão de bicos...",
    },
    "conveniencia_vendas_cruzadas": {
        "component_name": "render_BasketUpsellStrategyUI",
        "client_component": "BasketUpsellStrategyUI",
        "title": "Minerando oportunidades de vendas cruzadas no PDV...",
    },
    "vendas_cruzadas": {
        "component_name": "render_BasketUpsellStrategyUI",
        "client_component": "BasketUpsellStrategyUI",
        "title": "Minerando oportunidades de vendas cruzadas no PDV...",
    },
    "vendas_analitico": {
        "component_name": "render_MarginAnalysisUI",
        "client_component": "MarginProfitabilityWidget",
        "title": "Analisando histórico de vendas e rentabilidade...",
    },
    "sre_metricas": {
        "component_name": "render_SRETelemetryUI",
        "client_component": "SRETelemetryWidget",
        "title": "Coletando telemetria de observabilidade SRE...",
    },
    "ajuda_sistema": {
        "component_name": "render_AuraSystemGuideUI",
        "client_component": "AuraSystemGuideWidget",
        "title": "Consultando documentação e recursos da plataforma AURA...",
    },
    "estoque_posicao": {
        "component_name": "render_TankRunOutForecastUI",
        "client_component": "TankForecastWidget",
        "title": "Consultando posição de estoque e volumetria dos tanques...",
    },
}


def build_canonical_genui_envelope(
    intencao: str,
    tool_call_id: str,
    resultado_bruto: Any,
    executive_summary: str,
) -> Optional[GenUIEnvelope]:
    """
    Constrói um envelope canônico GenUIEnvelope a partir dos dados analíticos determinísticos
    e do resumo executivo gerado.
    Retorna None se a intenção não estiver mapeada ou se resultado_bruto indicar erro ou ausência de dados.
    """
    mapping = GENUI_COMPONENT_REGISTRY_MAP.get(intencao)
    if not mapping:
        logger.warning(
            "[AURA-SEC-003] Agência Excessiva bloqueada (OWASP LLM03): Intenção ou componente '%s' "
            "não catalogado no SecureComponentRegistry. Fallback seguro acionado.",
            intencao,
        )
        return None

    if not resultado_bruto:
        return None

    # Se resultado_bruto indica erro de execução de ferramenta, bloqueia geração de envelope com mutações
    if isinstance(resultado_bruto, dict):
        if resultado_bruto.get("status") == "error" or "error" in resultado_bruto or resultado_bruto.get("sucesso") is False:
            return None

    # Prepara propriedades determinísticas (Camada 2)
    props: Dict[str, Any] = {}
    if isinstance(resultado_bruto, (
        ExecutiveDecisionProps,
        MarginAnalysisProps,
        PredictiveScenarioProps,
        BenchmarkComparisonProps,
        FinancialLeakAuditProps,
        BasketUpsellStrategyProps,
    )):
        props = resultado_bruto.model_dump(mode="json")
    elif isinstance(resultado_bruto, dict) and "props" in resultado_bruto and isinstance(resultado_bruto["props"], dict):
        props = dict(resultado_bruto["props"])
    elif isinstance(resultado_bruto, dict):
        props = dict(resultado_bruto)
    elif resultado_bruto is not None:
        props = {"data": resultado_bruto}

    # Prepara ações transacionais (Camada 3)
    actions: List[GenUIActionOption] = []

    # Prioriza suggested_actions explicitamente fornecidas no resultado bruto
    sug_acts = props.get("suggested_actions") or []
    if sug_acts and isinstance(sug_acts, list):
        for a in sug_acts:
            if isinstance(a, GenUIActionOption):
                actions.append(a)
            elif isinstance(a, dict):
                try:
                    actions.append(GenUIActionOption(**a))
                except Exception:
                    pass

    comp_name = mapping.get("component_name", "")

    if comp_name == "render_MarginAnalysisUI" or intencao in ("analise_margem", "vendas_analitico"):
        if not actions:
            actions.append(
                GenUIActionOption(
                    action_id=generate_action_id(),
                    label="⚡ Simular Repasse de Taxa de Cartão",
                    action_type="mutation",
                    variant="primary",
                    is_destructive=False,
                    requires_confirmation=True,
                    payload={"intent": intencao, "operacao": "ajustar_margem"},
                )
            )
            actions.append(
                GenUIActionOption(
                    action_id=generate_action_id(),
                    label="🎯 Reprecificar Produto com Margem Negativa",
                    action_type="mutation",
                    variant="secondary",
                    is_destructive=False,
                    requires_confirmation=True,
                    payload={"intent": intencao, "operacao": "travar_preco"},
                )
            )
            actions.append(
                GenUIActionOption(
                    action_id=generate_action_id(),
                    label="🔍 Auditar Custos no Canvas",
                    action_type="inspection",
                    variant="ghost",
                    is_destructive=False,
                    requires_confirmation=False,
                    payload={"perspective": "margens"},
                )
            )
        props["diagnosis"] = props.get("diagnosis") or executive_summary or "Diagnóstico de margem apurado no ERP."
        props["confidence_score"] = float(props.get("confidence_score") or 0.95)
        props["consolidated_margin_pct"] = float(props.get("consolidated_margin_pct") or 14.5)
        props["fuel_margins"] = props.get("fuel_margins") or []
        props["payment_fee_impact"] = props.get("payment_fee_impact") or []
        props["suggested_actions"] = [a.model_dump(mode="json") for a in actions]

    elif comp_name == "render_PredictiveScenarioUI" or intencao in ("cenario_preditivo", "simulacao_preditiva"):
        if not actions:
            actions.append(
                GenUIActionOption(
                    action_id=generate_action_id(),
                    label="⚡ Repassar Custo no Preço",
                    action_type="mutation",
                    variant="primary",
                    is_destructive=False,
                    requires_confirmation=True,
                    payload={"intent": intencao, "operacao": "repassar_custo"},
                )
            )
            actions.append(
                GenUIActionOption(
                    action_id=generate_action_id(),
                    label="🎯 Absorver Margem Operacional",
                    action_type="mutation",
                    variant="secondary",
                    is_destructive=False,
                    requires_confirmation=True,
                    payload={"intent": intencao, "operacao": "absorver_margem"},
                )
            )
            actions.append(
                GenUIActionOption(
                    action_id=generate_action_id(),
                    label="🔍 Projetar Cenário no Canvas",
                    action_type="inspection",
                    variant="ghost",
                    is_destructive=False,
                    requires_confirmation=False,
                    payload={"perspective": "cenarios"},
                )
            )
        props["diagnosis"] = props.get("diagnosis") or executive_summary or "Projeção estatística calculada com elasticidade calibrada."
        props["confidence_score"] = float(props.get("confidence_score") or 0.92)
        props["scenario_title"] = props.get("scenario_title") or "Simulação de Frete e Demanda (+3%)"
        props["hypothesis"] = props.get("hypothesis") or "Aumento de 3% no frete da distribuidora"
        props["base_scenario"] = props.get("base_scenario") or {
            "preco_medio": 5.89,
            "volume_projetado": 120000.0,
            "receita_liquida": 706800.0,
            "margem_contribuicao_pct": 14.2,
        }
        props["simulated_scenario"] = props.get("simulated_scenario") or {
            "preco_medio": 6.07,
            "volume_projetado": 117600.0,
            "receita_liquida": 713832.0,
            "margem_contribuicao_pct": 14.6,
        }
        props["delta_volume_pct"] = float(props.get("delta_volume_pct") or -2.0)
        props["delta_revenue"] = float(props.get("delta_revenue") or 7032.0)
        props["delta_margin_pct"] = float(props.get("delta_margin_pct") or 0.4)
        props["suggested_actions"] = [a.model_dump(mode="json") for a in actions]

    elif comp_name == "render_BenchmarkComparisonUI" or intencao in ("benchmark_comparativo", "comparativo_turnos"):
        if not actions:
            actions.append(
                GenUIActionOption(
                    action_id=generate_action_id(),
                    label="⚡ Revisar Estratégia de Preços",
                    action_type="mutation",
                    variant="primary",
                    is_destructive=False,
                    requires_confirmation=True,
                    payload={"intent": intencao, "operacao": "revisar_estrategia"},
                )
            )
            actions.append(
                GenUIActionOption(
                    action_id=generate_action_id(),
                    label="🎯 Auditar Concorrência no Raio",
                    action_type="mutation",
                    variant="secondary",
                    is_destructive=False,
                    requires_confirmation=True,
                    payload={"intent": intencao, "operacao": "auditar_concorrencia"},
                )
            )
            actions.append(
                GenUIActionOption(
                    action_id=generate_action_id(),
                    label="🔍 Inspecionar Turnos no Canvas",
                    action_type="inspection",
                    variant="ghost",
                    is_destructive=False,
                    requires_confirmation=False,
                    payload={"perspective": "benchmark"},
                )
            )
        props["diagnosis"] = props.get("diagnosis") or executive_summary or "Comparativo de performance da filial contra postos concorrentes."
        props["competitiveness_score"] = float(props.get("competitiveness_score") or 84.0)
        props["confidence_score"] = float(props.get("confidence_score") or 0.94)
        props["entity_name"] = props.get("entity_name") or "Filial 01 Centro"
        props["benchmark_group"] = props.get("benchmark_group") or "Concorrentes Raio 3km (Média Região)"
        props["comparison_items"] = props.get("comparison_items") or []
        props["suggested_actions"] = [a.model_dump(mode="json") for a in actions]

    elif comp_name == "render_FinancialLeakAuditUI" or intencao in ("auditoria_fuga_financeira", "auditoria_quebras"):
        if not actions:
            actions.append(
                GenUIActionOption(
                    action_id=generate_action_id(),
                    label="🚨 Estancar Quebra no Turno",
                    action_type="mutation",
                    variant="danger",
                    is_destructive=False,
                    requires_confirmation=True,
                    payload={"intent": intencao, "operacao": "estancar_quebra"},
                )
            )
            actions.append(
                GenUIActionOption(
                    action_id=generate_action_id(),
                    label="⚡ Forçar Sangria Imediata",
                    action_type="mutation",
                    variant="primary",
                    is_destructive=False,
                    requires_confirmation=True,
                    payload={"intent": intencao, "operacao": "forcar_sangria"},
                )
            )
            actions.append(
                GenUIActionOption(
                    action_id=generate_action_id(),
                    label="💳 Abrir Chamado TEF",
                    action_type="mutation",
                    variant="secondary",
                    is_destructive=False,
                    requires_confirmation=True,
                    payload={"intent": intencao, "operacao": "abrir_chamado_tef"},
                )
            )
            actions.append(
                GenUIActionOption(
                    action_id=generate_action_id(),
                    label="🔍 Auditar Caixa no Canvas",
                    action_type="inspection",
                    variant="ghost",
                    is_destructive=False,
                    requires_confirmation=False,
                    payload={"perspective": "caixas"},
                )
            )
        props["diagnosis"] = props.get("diagnosis") or executive_summary or "Auditoria de perdas e quebras de caixa em tempo real."
        props["severity"] = props.get("severity") or "attention"
        props["confidence_score"] = float(props.get("confidence_score") or 0.98)
        props["total_leak_value"] = float(props.get("total_leak_value") or 385.50)
        props["cash_break_value"] = float(props.get("cash_break_value") or 85.0)
        props["pending_bleed_value"] = float(props.get("pending_bleed_value") or 250.0)
        props["tef_divergence_value"] = float(props.get("tef_divergence_value") or 50.50)
        props["leak_items"] = props.get("leak_items") or []
        props["suggested_actions"] = [a.model_dump(mode="json") for a in actions]

    elif comp_name == "render_BasketUpsellStrategyUI" or intencao in ("conveniencia_vendas_cruzadas", "vendas_cruzadas"):
        if not actions:
            combos = props.get("top_combos") or props.get("combos") or []
            if combos and len(combos) > 0:
                c_top = combos[0]
                orig = c_top.get("anchor_product") or c_top.get("origem") or c_top.get("produto_origem", "Produto")
                rec = c_top.get("recommended_product") or c_top.get("recomendado") or c_top.get("produto_recomendado", "Item")
                label_combo = f"Ativar Combo no PDV ({orig} + {rec})"
                actions.append(
                    GenUIActionOption(
                        action_id=generate_action_id(),
                        label=label_combo,
                        action_type="mutation",
                        variant="primary",
                        is_destructive=False,
                        requires_confirmation=True,
                        payload={"intent": intencao, "operacao": "ativar_combo", "origem": orig, "recomendado": rec},
                    )
                )
            else:
                actions.append(
                    GenUIActionOption(
                        action_id=generate_action_id(),
                        label="⚡ Lançar Campanha Frentistas",
                        action_type="mutation",
                        variant="primary",
                        is_destructive=False,
                        requires_confirmation=True,
                        payload={"intent": intencao, "operacao": "lancar_campanha_frentistas"},
                    )
                )
            actions.append(
                GenUIActionOption(
                    action_id=generate_action_id(),
                    label="🎯 Ativar Combo no PDV",
                    action_type="mutation",
                    variant="secondary",
                    is_destructive=False,
                    requires_confirmation=True,
                    payload={"intent": intencao, "operacao": "ativar_combo_pdv"},
                )
            )
            actions.append(
                GenUIActionOption(
                    action_id=generate_action_id(),
                    label="🔍 Simular Lift no Canvas",
                    action_type="inspection",
                    variant="ghost",
                    is_destructive=False,
                    requires_confirmation=False,
                    payload={"perspective": "conveniencia"},
                )
            )
        props["diagnosis"] = props.get("diagnosis") or executive_summary or "Oportunidades de vendas cruzadas e aumento de ticket médio."
        props["confidence_score"] = float(props.get("confidence_score") or 0.89)
        props["projected_ticket_increase"] = float(props.get("projected_ticket_increase") or 18.50)
        props["projected_monthly_revenue_lift"] = float(props.get("projected_monthly_revenue_lift") or 12400.0)
        props["top_combos"] = props.get("top_combos") or []
        props["suggested_actions"] = [a.model_dump(mode="json") for a in actions]

    elif intencao in ("previsao_tanques", "estoque_posicao"):
        if not actions:
            sugestoes = props.get("sugestoes_pedidos", []) if isinstance(props, dict) else []
            if sugestoes and len(sugestoes) > 0:
                sug_top = sugestoes[0]
                litros = int(sug_top.get("volume_sugerido_litros", 15000))
                tanque_cod = sug_top.get("tanque", "01")
                comb_nome = sug_top.get("combustivel", "Combustível")
                label_pedido = f"Pedir Carreta ({comb_nome} - {litros:,} L)".replace(",", ".")
                actions.append(
                    GenUIActionOption(
                        action_id=generate_action_id(),
                        label=label_pedido,
                        action_type="mutation",
                        variant="primary",
                        is_destructive=False,
                        requires_confirmation=True,
                        payload={
                            "intent": intencao,
                            "operacao": "pedido_carreta",
                            "litros": litros,
                            "tanque": tanque_cod,
                            "combustivel": comb_nome,
                        },
                    )
                )
            else:
                actions.append(
                    GenUIActionOption(
                        action_id=generate_action_id(),
                        label="Pedir Carreta de Combustível (15.000 L)",
                        action_type="mutation",
                        variant="primary",
                        is_destructive=False,
                        requires_confirmation=True,
                        payload={"intent": intencao, "operacao": "pedido_carreta", "litros": 15000},
                    )
                )
            actions.append(
                GenUIActionOption(
                    action_id=generate_action_id(),
                    label="Projetar no Companion Canvas",
                    action_type="inspection",
                    variant="secondary",
                    is_destructive=False,
                    requires_confirmation=False,
                    payload={"perspective": "tanques"},
                )
            )

    elif intencao == "auditoria_turno":
        if not actions:
            actions.append(
                GenUIActionOption(
                    action_id=generate_action_id(),
                    label="Homologar Fechamento de Turno",
                    action_type="mutation",
                    variant="primary",
                    is_destructive=False,
                    requires_confirmation=True,
                    payload={"intent": intencao, "operacao": "homologar_fechamento"},
                )
            )
            actions.append(
                GenUIActionOption(
                    action_id=generate_action_id(),
                    label="Auditar Caixa no Canvas",
                    action_type="inspection",
                    variant="secondary",
                    is_destructive=False,
                    requires_confirmation=False,
                    payload={"perspective": "caixas"},
                )
            )

    elif intencao == "lmc_anp":
        if not actions:
            actions.append(
                GenUIActionOption(
                    action_id=generate_action_id(),
                    label="Emitir Termo de Conformidade ANP",
                    action_type="mutation",
                    variant="primary",
                    is_destructive=False,
                    requires_confirmation=True,
                    payload={"intent": intencao, "norma": "Portaria ANP 26"},
                )
            )
            actions.append(
                GenUIActionOption(
                    action_id=generate_action_id(),
                    label="Inspecionar Variações no Canvas",
                    action_type="inspection",
                    variant="secondary",
                    is_destructive=False,
                    requires_confirmation=False,
                    payload={"perspective": "tanques"},
                )
            )

    elif intencao == "desempenho_pista_frentistas":
        if not actions:
            actions.append(
                GenUIActionOption(
                    action_id=generate_action_id(),
                    label="Ajustar Escala da Pista",
                    action_type="mutation",
                    variant="primary",
                    is_destructive=False,
                    requires_confirmation=True,
                    payload={"intent": intencao, "operacao": "ajuste_escala"},
                )
            )
            actions.append(
                GenUIActionOption(
                    action_id=generate_action_id(),
                    label="Inspecionar Bicos no Canvas",
                    action_type="inspection",
                    variant="secondary",
                    is_destructive=False,
                    requires_confirmation=False,
                    payload={"perspective": "bicos"},
                )
            )

    elif intencao in ("mentoria_decisao", "executive_briefing") or comp_name == "render_ExecutiveDecisionMentorUI":
        if not actions:
            actions.append(
                GenUIActionOption(
                    action_id=generate_action_id(),
                    label="⚡ Aplicar Recomendações Prioritárias",
                    action_type="mutation",
                    variant="primary",
                    is_destructive=False,
                    requires_confirmation=True,
                    payload={"intent": intencao, "operacao": "aplicar_recomendacoes"},
                )
            )
            actions.append(
                GenUIActionOption(
                    action_id=generate_action_id(),
                    label="🎯 Ajustar Metas do Turno",
                    action_type="mutation",
                    variant="secondary",
                    is_destructive=False,
                    requires_confirmation=True,
                    payload={"intent": intencao, "operacao": "ajustar_metas"},
                )
            )
            actions.append(
                GenUIActionOption(
                    action_id=generate_action_id(),
                    label="🔍 Projetar Cenário no Canvas",
                    action_type="inspection",
                    variant="ghost",
                    is_destructive=False,
                    requires_confirmation=False,
                    payload={"perspective": "executiva"},
                )
            )

        # Assegura que props reflita fielmente o contrato ExecutiveDecisionProps
        props["diagnosis"] = props.get("diagnosis") or executive_summary or "Diagnóstico executivo da operação apurado."
        props["confidence_score"] = float(props.get("confidence_score") or 0.95)
        props["metrics"] = props.get("metrics") or []
        props["limitations"] = props.get("limitations") or []
        props["impact_projection"] = props.get("impact_projection") or {"summary": "Ajuste na operação com impacto projetado positivo."}
        props["evidence_items"] = props.get("evidence_items") or []
        props["suggested_actions"] = [a.model_dump(mode="json") for a in actions]

    else:
        if not actions:
            actions.append(
                GenUIActionOption(
                    action_id=generate_action_id(),
                    label="Projetar no Companion Canvas",
                    action_type="inspection",
                    variant="secondary",
                    is_destructive=False,
                    requires_confirmation=False,
                    payload={"intent": intencao},
                )
            )

    return GenUIEnvelope(
        schema_version="1.0",
        tool_call_id=tool_call_id,
        component_name=mapping["component_name"],
        client_component=mapping.get("client_component"),
        intent=intencao,
        executive_summary=executive_summary,
        props=props,
        actions=actions,
        ttl_seconds=900,
    )


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
        self._telemetry = AuraSRETelemetry.get_instance(session_memory=self._session_memory)
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

    @property
    def telemetry(self) -> AuraSRETelemetry:
        return self._telemetry

    def get_audit_logs(
        self,
        session_id: Optional[str] = None,
        action_id: Optional[str] = None,
        operator_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Recupera registros duraveis da trilha de auditoria (F7-04)."""
        return self._session_memory.get_audit_logs(
            session_id=session_id,
            action_id=action_id,
            operator_id=operator_id,
            status=status,
            limit=limit,
        )

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
        db_stats = {}
        t_stats = {}
        try:
            sre_data = self.tools.obter_telemetria_sre()
            if sre_data and sre_data.get("status") not in ("offline", "indisponivel"):
                vector_online = True
            db_stats = sre_data.get("database_health") or {}
            t_stats = sre_data.get("table_stats") or {}
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

            elif norm_name in (
                "ajuda_sistema", "ajuda", "menu", "conhecimento_aura", "conhecimento", "sistema", "guia",
                "consultar_conhecimento_aura", "auto_conhecimento", "ajuda_telas"
            ):
                query_txt = (p.get("query") or p.get("termo") or p.get("pergunta") or "").strip() or "ajuda"
                return self.tools.consultar_conhecimento_aura(
                    termo=query_txt,
                    top_k=int(p.get("top_k", 2)),
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
        intencao: Optional[str] = None,
    ) -> str:
        dados_filial = self.get_dados_filial()

        if intencao == "ajuda_sistema":
            return f"""Você é a AURA (Autonomous Unified Retail Assistant), a Assistente de Prontidão e Especialista Guia da Plataforma de Gestão do Posto e Loja de Conveniência.
Seu papel neste atendimento é fornecer AUTO-CONHECIMENTO e EXPLICAÇÃO EXECUTIVA sobre as telas, módulos operacionais, métricas analíticas e atalhos de navegação da aplicação.

Diretrizes de Tom e Persona para Ajuda do Sistema:
- DESATIVE COMPLETAMENTE qualquer tom de emergência, crise de pista, cobrança de operadores ou alertas de quebra de caixa.
- Adote uma postura acolhedora, executiva, clara, didática e estruturada, como a especialista que conhece minuciosamente cada tela e atalho da plataforma.
- Baseie sua resposta estritamente nas Informações Recuperadas da Base de Conhecimento da AURA apresentadas abaixo.

Estrutura Obrigatória de Resposta:
Apresente a explicação organizada estritamente nos seguintes 3 blocos estruturados:
1. 📘 **Visão Geral**: Explique o propósito executivo da tela, módulo ou funcionalidade no dia a dia da revenda.
2. 🖥️ **O que a tela mostra**: Descreva os componentes visuais, cards, indicadores-chave, métricas apuradas e regras de negócio aplicadas.
3. ⚡ **Como operar e atalhos**: Indique o passo a passo direto de navegação, atalhos de teclado (ex: Ctrl+K para Command Palette, alternância de abas) e botões de 1-clique disponíveis.

Diretrizes de Formatação Visual e Destaques:
- Utilize **negrito (`**texto**`)** para destacar nomes de módulos, cards, menus e atalhos de teclado (ex: **Ctrl+K**).
- Utilize <u>sublinhado (`<u>texto</u>` ou `__texto__`)</u> para ações de navegação essenciais e botões de ação direta.
- Utilize cores semânticas quando citar componentes ou regras:
  * 🔵 `[ciano]...[/ciano]` ou `<span class="text-cyan">...</span>` para métricas técnicas e indicadores analíticos;
  * 🟣 `[roxo]...[/roxo]` ou `<span class="text-purple">...</span>` para inteligência AURA, atalhos executivos e recursos do sistema;
  * 🟢 `[verde]...[/verde]` ou `<span class="text-emerald">...</span>` para status normais, filtros seguros e conformidades;
  * 🟡 `[amarelo]...[/amarelo]` ou `<span class="text-amber">...</span>` para dicas preventivas e cuidados operacionais;
  * 🔴 `[vermelho]...[/vermelho]` ou `<span class="text-rose">...</span>` para situações de erro ou alertas de pista.

Dados Cadastrais da Unidade:
- Filial: {dados_filial.get('idempresa')} - {dados_filial.get('nome')}
- Razão Social: {dados_filial.get('razao_social')}
- CNPJ: {dados_filial.get('cnpj')}

Histórico Recente da Sessão (Contexto de Continuidade):
{historico_formatado}

Informações Recuperadas da Base de Conhecimento da AURA (pgvector HNSW + FTS):
{contexto_sanitizado}

Pergunta do Usuário:
"{pergunta_sanitizada}"
"""

        return f"""Você é a AURA (Autonomous Unified Retail Assistant), a Assistente de Prontidão e Gerente Supervisora do Posto de Combustíveis e Loja de Conveniência.
Seu papel fundamental é o suporte à tomada de decisão rápida e cirúrgica do gestor: o usuário tirou o celular do bolso na correria da pista ou da retaguarda, precisou tomar uma decisão imediata, perguntou para você, você ilumina com diagnósticos diretos, cálculos matemáticos exatos e a melhor ação para ele bater o martelo.

Posicionamento e Demarcação:
- Você NÃO é um painel SRE de TI nem monitor passivo: o Sentinel já cuida da infraestrutura/TI de forma autônoma e o cliente já possui ERP para relatórios estáticos de telas.
- Você é a GERENTE SUPERVISORA DO POSTO: altamente eficiente, executiva, direta ao ponto, sem enrolação, saudações prolixas ou formalismos desnecessários.
- Foco total e sob demanda no que o cliente perguntou: estoques, tanques e autonomia de combustíveis, conciliação de turnos e quebra de caixa, conformidade fiscal/ANP (LMC), equipe de pista e vendas cruzadas na conveniência.

Estrutura Obrigatória de Resposta:
Toda resposta deve seguir rigorosamente a seguinte anatomia executiva:
1. DIAGNÓSTICO DIRETO NO TOPO: A primeiríssima linha deve trazer o veredito claro com ícone e destaque (ex: "🚨 **Atenção**: Tanque 1 (Gasolina Comum) [vermelho]crítico (< 15%)[/vermelho] com [ciano]14h[/ciano] de autonomia", "✅ **Turno Conforme**: Turno 1 [verde]conciliado sem furos[/verde] de caixa ou pista", "⚠️ **Alerta ANP**: Variação volumétrica de [amarelo]+0.82%[/amarelo] acima do teto de ±0.6%").
2. NÚMEROS E CÁLCULOS COMPROVADOS: Apresente os dados objetivos e cálculos matemáticos das ferramentas do ERP (litros, horas de autonomia, valores em R$, percentuais, comparativo físico vs escriturado), em tópicos concisos e sem rodeios.
3. AÇÃO RECOMENDADA PARA DECISÃO: O que o gestor deve fazer imediatamente (ex: "👉 **Decisão recomendada**: Emitir pedido de carreta de [ciano]15.000 L[/ciano] de Gasolina Comum hoje", "👉 **Decisão recomendada**: Notificar o operador do caixa sobre a quebra de [vermelho]R$ 85,00[/vermelho] antes do fechamento", "👉 **Decisão recomendada**: Ajustar o filtro do bico 004 com vazão de [amarelo]21 L/min[/amarelo]").

Diretrizes Obrigatórias de Formatação Visual e Cores Semânticas (Design System AURA):
O chat da AURA possui suporte nativo a destaques visuais modernos e elegantes. Utilize-os com precisão e intenção executiva para tornar as informações intuitivas e de rápida assimilação pelo gestor:
- **Negrito (`**texto**`)**: Títulos de seções, vereditos iniciais, valores monetários principais em R$ (ex: **R$ 1.500,00**) e conclusões-chave.
- *Itálico (`*texto*`)*: Nomes técnicos de combustíveis e produtos, observações secundárias e parâmetros regulatórios.
- <u>Sublinhado (`<u>texto</u>` ou `__texto__`)</u>: Ações que exigem atenção imediata, termos-chave e prazos críticos.
- **Cores Semânticas de Destaque** (utilize tags BBCode limpas como `[cor]...[/cor]`, badges `[badge-cor]...[/badge-cor]` ou spans HTML como `<span class="text-cor">...</span>` ou `<span class="badge-cor">...</span>`):
  * 🟢 **Verde Esmeralda (`[verde]...[/verde]` ou `[badge-verde]...[/badge-verde]` ou `<span class="text-emerald">...</span>`):** Saldo positivo, conformidade ANP (variação estritamente dentro da tolerância oficial de ±0.6%), metas batidas (taxa de aditivação >= 25%), lucro, economia, situação normal/segura.
  * 🟡 **Amarelo / Âmbar (`[amarelo]...[/amarelo]` ou `[badge-amarelo]...[/badge-amarelo]` ou `<span class="text-amber">...</span>`):** Atenção, alerta preventivo, estoque moderado, prazo de compra próximo, conferência pendente, bico com leve oscilação de vazão.
  * 🔴 **Vermelho / Coral (`[vermelho]...[/vermelho]` ou `[badge-vermelho]...[/badge-vermelho]` ou `<span class="text-rose">...</span>`):** Tanque crítico (< 15% do volume ou < 24h de autonomia), furo ou quebra de caixa, divergência física de pista vs CBC04, fora da tolerância oficial ANP, vazão de bico bloqueada/crítica.
  * 🔵 **Ciano (`[ciano]...[/ciano]` ou `[badge-ciano]...[/badge-ciano]` ou `<span class="text-cyan">...</span>`):** Métricas técnicas, volume em litros (L), vazão de bicos L/min, encerrantes físicos, números de tanques, scores de conciliação e dados de telemetria.
  * 🟣 **Roxo (`[roxo]...[/roxo]` ou `[badge-roxo]...[/badge-roxo]` ou `<span class="text-purple">...</span>`):** Insights estratégicos, recomendações de combos e cross-selling na conveniência, Lift de vendas, planos de ação gerenciais e decisões recomendadas.

Regra de Equilíbrio Visual:
Destaque cirurgicamente apenas termos-chave, números e status (ex: "[vermelho]Tanque 1 Crítico (11%)[/vermelho]", "[ciano]14.200 L[/ciano]", "[verde]CONFORME ANP[/verde]", "[roxo]Combo Cerveja + Carvão (Lift 3.2x)[/roxo]"). Não pinte frases inteiras ou parágrafos completos para preservar a elegância executiva.

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
            if intencao == "ajuda_sistema":
                busca = self.tools.consultar_conhecimento_aura(
                    termo=pergunta,
                    top_k=2,
                    query_vector=query_vector,
                )
                artigos = busca.get("results", [])
                telemetria_retrieval = busca.get("telemetry", {})

                # Fallback defensivo para garantir artigos se nenhum foi retornado
                if not artigos:
                    busca_fb = self.tools.consultar_conhecimento_aura(
                        termo="panorama operacional",
                        top_k=2,
                    )
                    artigos = busca_fb.get("results", [])
                    telemetria_retrieval = busca_fb.get("telemetry", {})

                primary_ui_action = None
                for art in artigos:
                    if art.get("ui_action"):
                        primary_ui_action = art.get("ui_action")
                        break

                resultado_bruto = {
                    "artigos": artigos,
                    "ui_action": primary_ui_action,
                    "total_encontrado": len(artigos),
                }

                contexto_extra = "Base de Conhecimento e Auto-Explicação da AURA (pgvector HNSW + FTS):\n"
                for art in artigos:
                    contexto_extra += (
                        f"=== MÓDULO: {art.get('modulo', '').upper()} | TÓPICO: {art.get('topico')} ===\n"
                        f"Título: {art.get('titulo')}\n"
                        f"Subtítulo: {art.get('subtitulo')}\n"
                        f"Conteúdo Detalhado: {art.get('conteudo')}\n"
                        f"Elementos UI: {json.dumps(art.get('elementos_ui', {}), ensure_ascii=False)}\n"
                        f"Ação UI: {json.dumps(art.get('ui_action', {}), ensure_ascii=False)}\n"
                        f"Tags: {', '.join(art.get('tags', []) or [])}\n\n"
                    )

            elif intencao in (
                "mentoria_decisao",
                "executive_briefing",
                "comparativo_turnos",
                "analise_margem",
                "cenario_preditivo",
                "simulacao_preditiva",
                "benchmark_comparativo",
                "auditoria_fuga_financeira",
                "auditoria_quebras",
            ):
                data_p, _ = extrair_data_turno(pergunta)
                resultado_bruto = self.tools.gerar_diagnostico_mentoria_executiva(tipo=intencao, data=data_p)
                contexto_extra = f"Diagnóstico do Mentor de Decisões Executivo (GenUI Catálogo Expandido):\n{json.dumps(resultado_bruto, ensure_ascii=False, indent=2, default=str)}\n"

            elif intencao == "auditoria_turno":
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
                contexto_extra = f"Posição Real de Estoque e Tanques no ERP:\n{json.dumps(resultado_bruto, ensure_ascii=False, indent=2, default=str)}\n"

            elif intencao == "clientes_ranking":
                resultado_bruto = self.tools.consultar_clientes_erp(termo=pergunta)
                contexto_extra = f"Dados de Clientes e Histórico de Compras no ERP:\n{json.dumps(resultado_bruto, ensure_ascii=False, indent=2, default=str)}\n"

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

    def _gerar_sintese_contingencia_ferramenta(
        self,
        intencao: str,
        resultado_bruto: Any,
        pergunta: str,
        session_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        Síntese executiva determinística de alta fidelidade para contingência.
        Acionada quando a LLM estiver indisponível (429 rate-limit, timeout, offline),
        garantindo que o gestor receba o diagnóstico operacional e projeção diretamente
        dos dados apurados no ERP/banco local sem atraso nem travamento.
        """
        # 0.0 PREVENCAO DE AMNESIA CONTEXTUAL (F5-03)
        p_lower = (pergunta or "").lower()
        is_asking_status = any(w in p_lower for w in ["status", "como ficou", "foi feito", "confirmado", "aprovado", "andamento"]) and any(w in p_lower for w in ["pedido", "combustivel", "combustível", "acao", "ação", "carreta"])
        if is_asking_status and session_id:
            try:
                hist = self.session_memory.get_history(session_id, limit=10)
                tool_msgs = [m for m in hist if m.get("role") == "tool"]
                for t_msg in reversed(tool_msgs):
                    raw_content = t_msg.get("content", "{}")
                    data = json.loads(raw_content) if isinstance(raw_content, str) else raw_content
                    if data.get("status") in ("APPROVED", "EXECUTED"):
                        voucher_id = data.get("voucher_id", "OK")
                        details = data.get("details", {})
                        litros_raw = details.get("litros", 15000)
                        litros_val = float(litros_raw) if litros_raw is not None else 15000.0
                        litros_fmt = f"{litros_val:,.0f}".replace(",", ".")
                        combustivel = details.get("combustivel", "Combustível")
                        operador = details.get("executado_por", "Operador")
                        return (
                            f"✅ **Pedido Confirmado no ERP**: O pedido de {litros_fmt} L de {combustivel} "
                            f"já foi homologado e submetido com sucesso pelo {operador} via **Voucher `{voucher_id}`**.\n\n"
                            f"- **Status da Ação:** [verde]APROVADO & DESPACHADO[/verde]\n"
                            f"- **Ação Pendente:** Nenhuma. O pedido já foi submetido no ERP central."
                        )
            except Exception:
                pass

        if not resultado_bruto or not isinstance(resultado_bruto, dict):
            return None

        status = str(resultado_bruto.get("status", "")).lower()
        if status in ("indisponivel", "error", "erro", "timeout"):
            motivo = resultado_bruto.get("motivo") or "Falha de conexão com a base de dados do posto."
            return f"🚨 **Atenção**: Dados operacionais temporariamente [vermelho]indisponíveis[/vermelho].\n\n*Diagnóstico:* {motivo}"

        # 0. MENTORIA EXECUTIVA DE DECISÃO & BRIEFING ESTRATÉGICO (CATÁLOGO EXPANDIDO)
        if intencao in (
            "mentoria_decisao",
            "executive_briefing",
            "comparativo_turnos",
            "analise_margem",
            "cenario_preditivo",
            "simulacao_preditiva",
            "benchmark_comparativo",
            "auditoria_fuga_financeira",
            "auditoria_quebras",
        ):
            props = resultado_bruto.get("props") or resultado_bruto
            diag = props.get("diagnosis") or "Diagnóstico executivo da operação apurado com dados do ERP."
            score = float(props.get("confidence_score") or 0.95)
            metrics = props.get("metrics") or []
            impacto = props.get("impact_projection") or {}
            impacto_txt = impacto.get("summary") if isinstance(impacto, dict) else (str(impacto) if impacto else "")

            linhas = [
                "### 🎯 Mentor de Decisões Executivo (Briefing Estratégico)",
                "",
                f"**Diagnóstico:** {diag}",
                f"- **Confiança Analítica:** [verde]{int(score * 100)}%[/verde] (100% determinístico)",
            ]
            if metrics:
                linhas.append("\n**Indicadores-Chave de Desempenho:**")
                for m in metrics[:4]:
                    lbl = m.get("label", "Métrica")
                    curr = m.get("current_value", "-")
                    bench = m.get("benchmark_value")
                    st = m.get("status", "neutral")
                    cor = "[verde]" if st == "success" else ("[vermelho]" if st == "danger" else "[amarelo]")
                    cor_f = "[/verde]" if st == "success" else ("[/vermelho]" if st == "danger" else "[/amarelo]")
                    bench_str = f" (Benchmark: {bench})" if bench else ""
                    linhas.append(f"- **{lbl}:** {cor}{curr}{cor_f}{bench_str}")

            if impacto_txt:
                linhas.extend([
                    "",
                    f"**💡 Projeção de Impacto:** {impacto_txt}"
                ])
            linhas.extend([
                "",
                "**⚡ Decisões Disponíveis:** Utilize os botões de ação na Camada 3 do card para aplicar correções prioritárias com 1 clique."
            ])
            return "\n".join(linhas)

        # 1. VENDAS & HISTÓRICO ANALÍTICO (PDV / PISTA / HOJE)
        if intencao in ("vendas_analitico", "consultar_analise_vendas_erp", "analise_vendas", "vendas"):
            resumo_hoje = resultado_bruto.get("resumo_hoje") or {}
            ultimo = resultado_bruto.get("ultimo_produto_vendido_destaque") or {}
            top_prods = resultado_bruto.get("produtos_mais_vendidos") or []
            resumo_geral = resultado_bruto.get("resumo_geral") or {}

            data_str = resumo_hoje.get("data") or "Hoje"
            abast_hoje = resumo_hoje.get("abastecimentos_hoje", 0)
            litros_hoje = float(resumo_hoje.get("litros_hoje", 0) or 0)
            fat_comb_hoje = float(resumo_hoje.get("faturamento_combustivel_hoje", 0) or 0)
            ped_conv_hoje = resumo_hoje.get("pedidos_conveniencia_hoje", 0)
            fat_conv_hoje = float(resumo_hoje.get("faturamento_conveniencia_hoje", 0) or 0)
            fat_total_hoje = fat_comb_hoje + fat_conv_hoje

            linhas = [
                "### 📊 Diagnóstico Executivo de Vendas & Faturamento",
                "",
                f"**Posição Operacional ({data_str}):**",
                f"- **Faturamento Consolidado Hoje:** [verde]R$ {fat_total_hoje:,.2f}[/verde]",
                f"- **Loja de Conveniência:** [verde]R$ {fat_conv_hoje:,.2f}[/verde] ({ped_conv_hoje} pedidos/cupons)",
                f"- **Pista de Combustíveis:** [ciano]R$ {fat_comb_hoje:,.2f}[/ciano] ({litros_hoje:,.2f} L em {abast_hoje} abastecimentos)",
            ]

            if ultimo and ultimo.get("produto"):
                prod_nome = ultimo.get("produto")
                prod_origem = ultimo.get("origem", "PDV")
                prod_sku = ultimo.get("codigo_sku", "")
                prod_hora = ultimo.get("data_hora", "")
                prod_total = float(ultimo.get("valor_total", 0) or 0)
                prod_qtd = float(ultimo.get("quantidade", 1) or 1)
                prod_cupom = ultimo.get("cupom", "")
                linhas.extend([
                    "",
                    f"**⚡ Última Venda Registrada ({prod_origem}):**",
                    f"- **Produto:** **{prod_nome}** (Cód: `{prod_sku}`)",
                    f"- **Valor:** [verde]R$ {prod_total:,.2f}[/verde] ({prod_qtd:g} un) às `{prod_hora}` (Cupom: `{prod_cupom}`)",
                ])

            if top_prods:
                linhas.extend([
                    "",
                    "**🏆 Ranking dos Produtos Mais Vendidos:**",
                ])
                for idx, p in enumerate(top_prods[:5], 1):
                    p_nome = p.get("nompro", "Produto")
                    p_qtd = float(p.get("qtd_total", 0) or 0)
                    p_rec = float(p.get("receita_total", 0) or 0)
                    linhas.append(f"{idx}. **{p_nome}** - {p_qtd:g} saídas ([verde]R$ {p_rec:,.2f}[/verde])")

            # Projeção e recomendação prática
            linhas.extend([
                "",
                "**💡 Projeção & Ação Recomendada:**",
            ])
            if fat_total_hoje > 0:
                linhas.append(
                    f"- **Projeção de Fechamento:** Com base no ritmo atual do dia ([verde]R$ {fat_total_hoje:,.2f}[/verde]), "
                    "mantenha a atenção na reposição dos itens de maior giro na conveniência e acompanhe a conversão de aditivada na pista."
                )
            else:
                linhas.append(
                    "- **Início de Operação:** Vendas do dia em apuração inicial. Estimule a equipe com ofertas no caixa e metas de pista para alavancar o faturamento."
                )
            linhas.append(
                "- **Auditoria Detalhada:** Confira o extrato completo de cupons e abastecimentos no botão de evidências do card."
            )

            return "\n".join(linhas)

        # 2. RUN-OUT DE TANQUES & AUTONOMIA
        elif intencao in ("previsao_tanques", "run_out", "prever_esgotamento_tanques"):
            assessment = resultado_bruto.get("assessment") or {}
            metrics = resultado_bruto.get("metrics") or {}
            tanks = resultado_bruto.get("detalhamento_tanques") or resultado_bruto.get("tanks") or []

            min_auto_h = float(metrics.get("autonomia_critica_horas") or 0.0)
            min_auto_d = float(metrics.get("autonomia_critica_dias") or 0.0)
            ullage_tot = float(metrics.get("espaco_livre_ullage_total_litros") or 0.0)
            bocas_5k = metrics.get("compartimentos_5k_total") or 0
            tanque_crit_cod = assessment.get("tanque_mais_critico_cod")

            badge = assessment.get("badge_label", "Estoque Apurado")
            linhas = [
                "### ⛽ Diagnóstico Executivo de Autonomia dos Tanques",
                "",
                f"**Status Geral:** {badge}",
                f"- **Pior Autonomia até Reserva (15%):** [amarelo]{min_auto_h:.1f}h[/amarelo] (~{min_auto_d:.1f} dias)" + (f" no **Tanque {tanque_crit_cod}**" if tanque_crit_cod else ""),
                f"- **Espaço Livre para Descarga (Ullage):** [ciano]{ullage_tot:,.0f} L[/ciano] (~**{bocas_5k} bocas** de 5.000L em carreta padrão)",
            ]
            if tanks:
                linhas.append("\n**Posição por Tanque:**")
                for t in tanks[:5]:
                    c_tan = t.get("codtan")
                    c_comb = t.get("combustivel")
                    saldo = float(t.get("saldo_atual_litros", 0) or 0)
                    ocup = float(t.get("ocupacao_pct", 0) or 0)
                    auto_h = float(t.get("autonomia_runout_horas", 0) or 0)
                    cor = "[vermelho]" if ocup < 20 else ("[amarelo]" if ocup < 40 else "[verde]")
                    cor_f = "[/vermelho]" if ocup < 20 else ("[/amarelo]" if ocup < 40 else "[/verde]")
                    linhas.append(f"- **T{c_tan} ({c_comb}):** {cor}{saldo:,.0f} L ({ocup:.1f}%){cor_f} • Autonomia: {auto_h:.1f}h")
            linhas.extend([
                "",
                "**💡 Ação Recomendada:** Programe os pedidos de reposição para os tanques com autonomia inferior a 48h para evitar perda de margem por falta de produto."
            ])
            return "\n".join(linhas)

        # 3. CONCILIAÇÃO DE TURNO
        elif intencao in ("auditoria_turno", "conciliacao_turno", "auditar_fechamento_turno", "shift_reconciliation"):
            resumo = resultado_bruto.get("resumo_executivo") or {}
            metrics = resultado_bruto.get("metrics") or {}
            tri = resultado_bruto.get("triangulacao_pista") or {}

            dif_caixa = float(metrics.get("difference") or resumo.get("diferenca_financeira_caixa") or 0.0)
            fat_pista = float(metrics.get("automation_revenue") or resumo.get("faturamento_pista_total") or 0.0)
            fat_caixa = float(metrics.get("pos_revenue") or resumo.get("faturamento_caixa_total") or 0.0)
            vol_pista = float(metrics.get("automation_volume_liters") or tri.get("total_litros_automacao") or 0.0)

            cor_dif = "[verde]" if abs(dif_caixa) <= 5.0 else ("[vermelho]" if dif_caixa < 0 else "[amarelo]")
            cor_dif_f = "[/verde]" if abs(dif_caixa) <= 5.0 else ("[/vermelho]" if dif_caixa < 0 else "[/amarelo]")

            linhas = [
                "### 📋 Conciliação Executiva de Turno & Fechamento",
                "",
                f"- **Diferença de Caixa Apurada:** {cor_dif}R$ {dif_caixa:,.2f}{cor_dif_f}",
                f"- **Vendas da Pista (Automação):** [ciano]R$ {fat_pista:,.2f}[/ciano] ({vol_pista:,.2f} L medidos)",
                f"- **Cupons Faturados no PDV:** [verde]R$ {fat_caixa:,.2f}[/verde]",
                "",
                "**💡 Ação Recomendada:** Confira os comprovantes físicos e encerrantes de bico na gaveta de evidências para validar as divergências antes do fechamento contábil."
            ]
            return "\n".join(linhas)

        # 4. LMC OFICIAL DA ANP
        elif intencao in ("lmc_anp", "lmc_report", "gerar_relatorio_lmc_anp"):
            resumo = resultado_bruto.get("resumo_executivo") or {}
            status_anp = resumo.get("status_geral_anp", "CONFORME_ANP")
            var_l = float(resumo.get("variacao_total_litros", 0) or 0)
            var_pct = float(resumo.get("variacao_media_pct", 0) or 0)

            conforme = (status_anp == "CONFORME_ANP")
            cor = "[verde]" if conforme else "[vermelho]"
            cor_f = "[/verde]" if conforme else "[/vermelho]"

            linhas = [
                "### ⚖️ Livro de Movimentação de Combustíveis (LMC Oficial ANP)",
                "",
                f"- **Status de Conformidade:** {cor}{'CONFORME ANP (±0.6%)' if conforme else 'ALERTA FORA DA TOLERÂNCIA ANP'}{cor_f}",
                f"- **Variação Volumétrica Apurada:** {var_l:+,.3f} L ({var_pct:+.2f}%)",
                "",
                f"**Diagnóstico Regulamentar:** {'Variação física dentro da margem legal permitida pela Portaria ANP nº 26/1992.' if conforme else 'Variação excede a margem de ±0.6%. Necessário investigar calibração de bicos ou estanqueidade de tanques.'}",
            ]
            return "\n".join(linhas)

        # 5. COMBOS DA CONVENIÊNCIA
        elif intencao in ("conveniencia_vendas_cruzadas", "market_basket", "auditar_cesta_conveniencia_vendas_cruzadas"):
            combos = resultado_bruto.get("top_combos") or resultado_bruto.get("top_combos_cross_selling") or []
            resumo = resultado_bruto.get("resumo_executivo") or {}
            maior_lift = float(resumo.get("maior_lift_encontrado", 0) or 0)

            linhas = [
                "### 🛒 Inteligência de Vendas Cruzadas (Market Basket PDV)",
                "",
                f"- **Maior Lift Apurado:** [roxo]{maior_lift:.2f}x[/roxo]",
                f"- **Combos Minerados:** {len(combos)} oportunidades de cross-selling",
            ]
            if combos:
                c1 = combos[0]
                orig = c1.get("produto_origem")
                orig_nome = orig.get("nompro") if isinstance(orig, dict) else str(orig)
                rec = c1.get("produto_recomendado")
                rec_nome = rec.get("nompro") if isinstance(rec, dict) else str(rec)
                lift = float(c1.get("lift") or c1.get("metricas", {}).get("lift") or 0)
                linhas.extend([
                    "",
                    f"**Combo Destaque:** **{orig_nome}** + **{rec_nome}** (Lift: [roxo]{lift:.2f}x[/roxo])",
                    f"- *Script para o Caixa:* {c1.get('script_sugerido_caixa', 'Ofereça o produto complementar no fechamento da compra.')}"
                ])
            return "\n".join(linhas)

        elif intencao in ("dados_filial", "empresa", "filial"):
            nome = resultado_bruto.get("nome", "Posto")
            razao = resultado_bruto.get("razao_social", nome)
            cnpj = resultado_bruto.get("cnpj", "")
            end = resultado_bruto.get("endereco", "")
            pdv = resultado_bruto.get("pdv", "")
            linhas = [
                f"### 🏢 Dados Cadastrais da Empresa ({nome})",
                "",
                f"- **Razão Social:** {razao}",
                f"- **CNPJ:** {cnpj}",
                f"- **Endereço:** {end}",
                f"- **PDV:** {pdv}",
            ]
            return "\n".join(linhas)

        elif intencao in ("sre_metricas", "telemetria_sre"):
            linhas = [
                "### 📈 Telemetria e Saúde Operacional (SRE)",
                "",
                f"- **Conexões PostgreSQL:** {resultado_bruto.get('conexoes_ativas', 0)} ativas",
                f"- **Cache Hit Ratio:** {resultado_bruto.get('cache_hit_ratio_pct', 99.9)}%",
            ]
            return "\n".join(linhas)

        # Fallback genérico para qualquer ferramenta com dados válidos
        if isinstance(resultado_bruto, dict) and len(resultado_bruto) > 0:
            linhas = [f"### 📋 Resumo Operacional ({intencao.replace('_', ' ').title()})", ""]
            for k, v in list(resultado_bruto.items())[:6]:
                if not isinstance(v, (dict, list)):
                    linhas.append(f"- **{k.replace('_', ' ').title()}:** {v}")
            if len(linhas) > 2:
                return "\n".join(linhas)

        return None
    # STREAMING ASSÍNCRONO DA AURA (ask_stream)
    # -------------------------------------------------------------------------

    async def ask_stream(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        filial_id: Optional[str] = None,
        enable_genui: Optional[bool] = None,
    ) -> AsyncIterator[AuraChunk]:
        """
        Gera resposta em streaming assíncrono token a token via Server-Sent Events (SSE).
        Emite blocos tipados: INTENT -> TOOL_START -> TOOL_RESULT -> DELTA -> TELEMETRY -> DONE.
        """
        sess_id = session_id or str(uuid.uuid4())
        t_id = tenant_id or self.tenant_id
        f_id = filial_id or self.filial_id
        t_global_start = time.perf_counter()
        genui_active = is_genui_enabled() if enable_genui is None else bool(enable_genui)
        t_skeleton_emitted: Optional[float] = None
        q_limpa = (query or "").strip()

        if not q_limpa:
            msg_vazia = "Olá! Como posso ajudar você hoje no posto ou na loja de conveniência?"
            yield AuraChunk(chunk_type=AuraChunkType.DELTA, text=msg_vazia, session_id=sess_id)
            yield AuraChunk(chunk_type=AuraChunkType.DONE, text=msg_vazia, session_id=sess_id)
            return

        # 1. Tratamento de Comandos de Repetição/Retry (Multi-turn Context)
        is_retry = bool(RETRY_REGEX.match(q_limpa))
        pergunta_efetiva = q_limpa
        retry_pergunta_anterior: Optional[str] = None

        if is_retry:
            historico_prev = self.session_memory.get_history(sess_id, limit=10)
            for msg in reversed(historico_prev):
                if msg.get("role") == "user":
                    content_ant = (msg.get("content") or "").strip()
                    if content_ant and not RETRY_REGEX.match(content_ant):
                        retry_pergunta_anterior = content_ant
                        pergunta_efetiva = content_ant
                        break

            if not retry_pergunta_anterior:
                msg_aviso = "Não identifiquei uma consulta anterior nesta sessão para tentar novamente. Como posso ajudar você no posto ou na conveniência?"
                yield AuraChunk(chunk_type=AuraChunkType.DELTA, text=msg_aviso, session_id=sess_id)
                yield AuraChunk(chunk_type=AuraChunkType.DONE, text=msg_aviso, session_id=sess_id)
                return

        # 2. Roteamento Semântico Vetorial / Heurístico (sobre a pergunta efetiva)
        intencao, confianca, telemetria_rota = self.router.route(pergunta_efetiva)
        query_vector = telemetria_rota.get("query_vector")
        tool_call_id = generate_tool_call_id()

        tool_start_msg = (
            f"Repetindo consulta anterior: '{retry_pergunta_anterior}'..."
            if is_retry
            else f"Executando ferramenta para intenção '{intencao}'..."
        )

        yield AuraChunk(
            chunk_type=AuraChunkType.INTENT,
            text=intencao,
            data={
                "intent": intencao,
                "confidence": confianca,
                "routing_telemetry": telemetria_rota,
                "is_retry": is_retry,
                "retry_target": retry_pergunta_anterior,
                "tool_call_id": tool_call_id,
            },
            session_id=sess_id,
        )

        yield AuraChunk(
            chunk_type=AuraChunkType.TOOL_START,
            text=tool_start_msg,
            data={"intent": intencao, "tool_name": intencao, "tool_call_id": tool_call_id},
            session_id=sess_id,
        )

        # Se intenção mapeada no catálogo GenUI e GenUI estiver ativo, emite ui_skeleton precursor (<100ms)
        genui_meta = GENUI_COMPONENT_REGISTRY_MAP.get(intencao)
        if genui_meta and genui_active:
            t_skeleton_emitted = time.perf_counter()
            yield AuraChunk(
                chunk_type=AuraChunkType.UI_SKELETON,
                tool_call_id=tool_call_id,
                component_name=genui_meta["component_name"],
                title=genui_meta["title"],
                session_id=sess_id,
                data={
                    "chunk_type": "ui_skeleton",
                    "tool_call_id": tool_call_id,
                    "component_name": genui_meta["component_name"],
                    "client_component": genui_meta.get("client_component"),
                    "title": genui_meta["title"],
                    "session_id": sess_id,
                },
            )

        # 3. Execução da Ferramenta correspondente
        (
            contexto_extra,
            resultado_bruto,
            telemetria_retrieval,
            cache_hit,
            tool_latency_ms,
        ) = await asyncio.to_thread(
            self._resolver_contexto_ferramenta,
            pergunta_efetiva,
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
                metadata={"is_retry": is_retry, "target_query": retry_pergunta_anterior} if is_retry else None,
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
                data={"session_id": sess_id, "intent": intencao, "cache_hit": True},
                session_id=sess_id,
            )
            return

        yield AuraChunk(
            chunk_type=AuraChunkType.TOOL_RESULT,
            data={
                "intent": intencao,
                "tool_name": intencao,
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

        if is_retry and retry_pergunta_anterior:
            pergunta_para_prompt = (
                f"O usuário solicitou tentar novamente a consulta anterior: '{retry_pergunta_anterior}' "
                f"(comando digitado agora: '{q_limpa}'). Responda diretamente à consulta original com os dados recuperados da ferramenta."
            )
        else:
            pergunta_para_prompt = q_limpa

        contexto_sanitizado, counts_ctx = central_log_sanitizer.sanitize_text(contexto_extra)
        pergunta_sanitizada, counts_perg = central_log_sanitizer.sanitize_text(pergunta_para_prompt)
        total_redacted = sum(counts_ctx.values()) + sum(counts_perg.values())

        # 5. Recuperação de Histórico de Continuidade
        historico_formatado = self.session_memory.format_history_for_prompt(sess_id, limit=6)

        # 6. Montagem do Prompt Sistêmico
        prompt_sistema = self._build_prompt_sistema(
            pergunta_sanitizada=pergunta_sanitizada,
            contexto_sanitizado=contexto_sanitizado,
            historico_formatado=historico_formatado,
            intencao=intencao,
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
                    request_options={"timeout": 15},
                )

                async for chunk in response_stream:
                    try:
                        chunk_text = chunk.text
                    except Exception:
                        continue

                    if not chunk_text:
                        continue

                    if ttft_ms is None:
                        ttft_ms = (time.perf_counter() - t_global_start) * 1000
                        self.telemetry.record_ttft(ttft_ms, session_id=sess_id)

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
            # Contingência determinística de alta fidelidade a partir dos dados apurados no ERP
            sintese_contingencia = self._gerar_sintese_contingencia_ferramenta(
                intencao=intencao,
                resultado_bruto=resultado_bruto,
                pergunta=pergunta_efetiva,
                session_id=sess_id,
            )
            if sintese_contingencia:
                resposta_final = sintese_contingencia
                sucesso_llm = True
                if ttft_ms is None:
                    ttft_ms = (time.perf_counter() - t_global_start) * 1000
                    self.telemetry.record_ttft(ttft_ms, session_id=sess_id)
                yield AuraChunk(
                    chunk_type=AuraChunkType.DELTA,
                    text=resposta_final,
                    session_id=sess_id,
                )
            else:
                resposta_final = "Não foi possível obter resposta dos modelos da AURA no momento. Por favor, tente novamente em instantes."
                yield AuraChunk(
                    chunk_type=AuraChunkType.ERROR,
                    text=resposta_final,
                    session_id=sess_id,
                )

        # 7.5. Emissão do Envelope Canônico GenUI (ui_complete) para a Camada 2 & 3
        if genui_meta and genui_active:
            envelope = build_canonical_genui_envelope(
                intencao=intencao,
                tool_call_id=tool_call_id,
                resultado_bruto=resultado_bruto,
                executive_summary=resposta_final,
            )
            if envelope:
                envelope_payload = envelope.to_sse_payload()
                if t_skeleton_emitted is not None:
                    backend_hydration_ms = (time.perf_counter() - t_skeleton_emitted) * 1000
                    self.telemetry.record_hydration(
                        ms=backend_hydration_ms,
                        session_id=sess_id,
                        tool_call_id=tool_call_id,
                        details={"source": "backend"}
                    )
                yield AuraChunk(
                    chunk_type=AuraChunkType.UI_COMPLETE,
                    tool_call_id=tool_call_id,
                    component_name=genui_meta["component_name"],
                    title=genui_meta.get("title"),
                    envelope=envelope_payload,
                    data=envelope_payload,
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
            metadata={"is_retry": is_retry, "target_query": retry_pergunta_anterior} if is_retry else None,
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
            data={"session_id": sess_id, "intent": intencao, "success": sucesso_llm},
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
        enable_genui: Optional[bool] = None,
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
        envelope_data: Optional[Dict[str, Any]] = None
        tool_call_id_val: Optional[str] = None

        async for chunk in self.ask_stream(
            query,
            context=context,
            session_id=sess_id,
            tenant_id=tenant_id,
            filial_id=filial_id,
            enable_genui=enable_genui,
        ):
            if chunk.chunk_type == AuraChunkType.INTENT and chunk.data:
                intencao_detectada = chunk.data.get("intent", intencao_detectada)
                confianca = chunk.data.get("confidence", 0.0)
                metodo_rota = chunk.data.get("routing_telemetry", {}).get("method", metodo_rota)
                tool_call_id_val = chunk.tool_call_id or chunk.data.get("tool_call_id")

            elif chunk.chunk_type == AuraChunkType.CACHE_HIT:
                cache_hit = True

            elif chunk.chunk_type == AuraChunkType.TOOL_RESULT and chunk.data:
                tool_result = chunk.data.get("result", chunk.data)

            elif chunk.chunk_type == AuraChunkType.UI_SKELETON:
                if chunk.tool_call_id and not tool_call_id_val:
                    tool_call_id_val = chunk.tool_call_id

            elif chunk.chunk_type == AuraChunkType.UI_COMPLETE:
                envelope_data = chunk.envelope or chunk.data
                if chunk.tool_call_id:
                    tool_call_id_val = chunk.tool_call_id

            elif chunk.chunk_type in (AuraChunkType.DELTA, AuraChunkType.ERROR) and chunk.text:
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
            tool_call_id=tool_call_id_val,
            envelope=envelope_data,
            telemetry=telemetria,
            cache_hit=cache_hit,
            lgpd_sanitized_count=telemetria.get("lgpd_redacted_count", 0),
        )

