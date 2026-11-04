"""
Modulo de Gestao de Consumo de Tokens, Custos e Orcamento da AURA.
Monitora tokens de entrada (prompt) e saida (completion), calcula custos em USD/BRL,
registra economia gerada por cache local (evitacao de custos) e gerencia
metas orcamentarias personalizaveis por filial/tenant.
Zero travessoes em todo o modulo.
"""

from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime, date, timedelta
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

logger = logging.getLogger("aura.token_budget")

# Tabela referencial de precos oficiais (USD por 1 Milhao de tokens)
# Baseada nos precos de mercado e Google AI Studio
DEFAULT_MODEL_PRICING: Dict[str, Dict[str, float]] = {
    "gemini-1.5-flash": {"input_usd_per_1m": 0.075, "output_usd_per_1m": 0.30},
    "gemini-2.0-flash": {"input_usd_per_1m": 0.100, "output_usd_per_1m": 0.40},
    "gemini-1.5-pro": {"input_usd_per_1m": 1.250, "output_usd_per_1m": 5.00},
    "gemini-2.5-flash": {"input_usd_per_1m": 0.100, "output_usd_per_1m": 0.40},
    "gemini-2.5-pro": {"input_usd_per_1m": 1.250, "output_usd_per_1m": 5.00},
}

DEFAULT_USD_TO_BRL: float = 5.80


def normalize_model_key(model_name: str) -> str:
    """Normaliza o nome do modelo para lookup na tabela de precos."""
    m = (model_name or "").lower().strip()
    if "2.5-pro" in m or "2_5_pro" in m:
        return "gemini-2.5-pro"
    if "2.5-flash" in m or "2_5_flash" in m:
        return "gemini-2.5-flash"
    if "2.0-flash" in m or "2_0_flash" in m:
        return "gemini-2.0-flash"
    if "pro" in m:
        return "gemini-1.5-pro"
    return "gemini-1.5-flash"


def calculate_token_cost(
    model_name: str,
    prompt_tokens: int,
    completion_tokens: int,
    usd_to_brl: float = DEFAULT_USD_TO_BRL,
) -> Dict[str, float]:
    """
    Calcula o custo deterministico da requisicao em USD e BRL.
    """
    key = normalize_model_key(model_name)
    pricing = DEFAULT_MODEL_PRICING.get(key, DEFAULT_MODEL_PRICING["gemini-1.5-flash"])

    in_rate = pricing["input_usd_per_1m"]
    out_rate = pricing["output_usd_per_1m"]

    cost_usd = ((prompt_tokens * in_rate) + (completion_tokens * out_rate)) / 1_000_000.0
    cost_brl = cost_usd * usd_to_brl

    return {
        "cost_usd": round(cost_usd, 6),
        "cost_brl": round(cost_brl, 6),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
    }


def calculate_avoided_cost(
    model_name: str,
    estimated_prompt_tokens: int,
    estimated_completion_tokens: int,
    usd_to_brl: float = DEFAULT_USD_TO_BRL,
) -> float:
    """
    Calcula o custo evitado (economia gerada por cache semantico ou resposta local).
    """
    calc = calculate_token_cost(
        model_name=model_name,
        prompt_tokens=estimated_prompt_tokens,
        completion_tokens=estimated_completion_tokens,
        usd_to_brl=usd_to_brl,
    )
    return calc["cost_brl"]


class TokenBudgetManager:
    """
    Gerenciador de consumo de tokens e limites orcamentarios por filial.
    Persiste historico em SQLite, emite alertas preventivos (ex: 80%) e
    permite degradacao inteligente ou bloqueio suave ao estourar o teto.
    """

    def __init__(self, db_path: Optional[Union[str, Path]] = None, session_memory=None):
        self.session_memory = session_memory
        if session_memory is not None and hasattr(session_memory, "db_path"):
            self.db_path = session_memory.db_path
            self._shared_conn = getattr(session_memory, "_shared_conn", None)
        elif str(db_path) == ":memory:":
            self.db_path = ":memory:"
            self._shared_conn = sqlite3.connect(":memory:", check_same_thread=False)
            self._shared_conn.row_factory = sqlite3.Row
        elif db_path is not None:
            self.db_path = str(db_path)
            self._shared_conn = None
        else:
            base_dir = Path(__file__).resolve().parent.parent
            data_dir = base_dir / "data"
            data_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = str(data_dir / "aura_sessions.db")
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

    def _init_db(self) -> None:
        """Cria as tabelas de controle de consumo e politicas se nao existirem."""
        with self._connection() as conn:
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA synchronous = NORMAL;")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS aura_token_ledger (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    filial_id TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    model_name TEXT NOT NULL,
                    prompt_tokens INTEGER DEFAULT 0,
                    completion_tokens INTEGER DEFAULT 0,
                    total_tokens INTEGER DEFAULT 0,
                    cost_usd REAL DEFAULT 0.0,
                    cost_brl REAL DEFAULT 0.0,
                    cache_hit INTEGER DEFAULT 0,
                    avoided_cost_brl REAL DEFAULT 0.0,
                    agent_role TEXT DEFAULT 'general_assistant',
                    intent_category TEXT DEFAULT 'general',
                    vertical_pack TEXT DEFAULT 'fuel_convenience'
                );
            """)
            cur_cols = conn.execute("PRAGMA table_info(aura_token_ledger);").fetchall()
            col_names = {r["name"] for r in cur_cols}
            if "agent_role" not in col_names:
                conn.execute("ALTER TABLE aura_token_ledger ADD COLUMN agent_role TEXT DEFAULT 'general_assistant';")
            if "intent_category" not in col_names:
                conn.execute("ALTER TABLE aura_token_ledger ADD COLUMN intent_category TEXT DEFAULT 'general';")
            if "vertical_pack" not in col_names:
                conn.execute("ALTER TABLE aura_token_ledger ADD COLUMN vertical_pack TEXT DEFAULT 'fuel_convenience';")
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_token_ledger_filial_ts 
                ON aura_token_ledger(filial_id, timestamp);
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_token_ledger_session 
                ON aura_token_ledger(session_id);
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_token_ledger_role 
                ON aura_token_ledger(filial_id, agent_role);
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_token_ledger_vertical 
                ON aura_token_ledger(vertical_pack);
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS aura_budget_policy (
                    filial_id TEXT PRIMARY KEY,
                    monthly_budget_brl REAL DEFAULT 30.00,
                    daily_budget_brl REAL DEFAULT 2.50,
                    alert_threshold_pct REAL DEFAULT 80.0,
                    policy_mode TEXT DEFAULT 'smart_pacing',
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()

    def get_or_create_policy(self, filial_id: str) -> Dict[str, Any]:
        """Obtem a politica orcamentaria da filial ou cria padrao se nao existir."""
        f_id = filial_id or "00001"
        with self._connection() as conn:
            cur = conn.execute(
                "SELECT * FROM aura_budget_policy WHERE filial_id = ?;", (f_id,)
            )
            row = cur.fetchone()
            if row:
                pol = dict(row)
                pol["enforcement_mode"] = pol.get("policy_mode")
                return pol

            # Insere politica padrao
            conn.execute("""
                INSERT OR IGNORE INTO aura_budget_policy (
                    filial_id, monthly_budget_brl, daily_budget_brl, alert_threshold_pct, policy_mode
                ) VALUES (?, 30.00, 2.50, 80.0, 'smart_pacing');
            """, (f_id,))
            conn.commit()

            cur = conn.execute(
                "SELECT * FROM aura_budget_policy WHERE filial_id = ?;", (f_id,)
            )
            row = cur.fetchone()
            pol = dict(row) if row else {
                "filial_id": f_id,
                "monthly_budget_brl": 30.00,
                "daily_budget_brl": 2.50,
                "alert_threshold_pct": 80.0,
                "policy_mode": "smart_pacing",
            }
            pol["enforcement_mode"] = pol.get("policy_mode")
            return pol

    def update_budget_policy(
        self,
        filial_id: str,
        monthly_budget_brl: Optional[float] = None,
        daily_budget_brl: Optional[float] = None,
        alert_threshold_pct: Optional[float] = None,
        policy_mode: Optional[str] = None,
        enforcement_mode: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Atualiza parametros de orcamento personalizaveis."""
        current = self.get_or_create_policy(filial_id)
        f_id = filial_id or "00001"

        mode_val = enforcement_mode if enforcement_mode is not None else policy_mode
        new_monthly = float(monthly_budget_brl) if monthly_budget_brl is not None else float(current["monthly_budget_brl"])
        new_daily = float(daily_budget_brl) if daily_budget_brl is not None else float(current["daily_budget_brl"])
        new_alert = float(alert_threshold_pct) if alert_threshold_pct is not None else float(current["alert_threshold_pct"])
        new_mode = str(mode_val).strip().lower() if mode_val is not None else str(current["policy_mode"])

        valid_modes = {"advisory", "smart_pacing", "strict_local"}
        if new_mode not in valid_modes:
            new_mode = "smart_pacing"

        ts = datetime.now(UTC).isoformat()
        with self._connection() as conn:
            conn.execute("""
                INSERT INTO aura_budget_policy (
                    filial_id, monthly_budget_brl, daily_budget_brl, alert_threshold_pct, policy_mode, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(filial_id) DO UPDATE SET
                    monthly_budget_brl = excluded.monthly_budget_brl,
                    daily_budget_brl = excluded.daily_budget_brl,
                    alert_threshold_pct = excluded.alert_threshold_pct,
                    policy_mode = excluded.policy_mode,
                    updated_at = excluded.updated_at;
            """, (f_id, new_monthly, new_daily, new_alert, new_mode, ts))
            conn.commit()

        updated_policy = self.get_or_create_policy(f_id)
        return {
            "status": "updated",
            "filial_id": f_id,
            "policy": updated_policy,
        }

    def record_usage(
        self,
        session_id: str,
        filial_id: str,
        tenant_id: str = "default_tenant",
        model_name: str = "gemini-2.5-flash",
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        cache_hit: bool = False,
        cached: bool = False,
        avoided_prompt_tokens: int = 0,
        avoided_completion_tokens: int = 0,
        timestamp: Optional[str] = None,
        agent_role: str = "general_assistant",
        intent_category: str = "general",
        vertical_pack: str = "fuel_convenience",
    ) -> Dict[str, Any]:
        """
        Registra uma transacao de consumo de tokens no livro-razao (ledger).
        Retorna o extrato da operacao e o percentual atual do orcamento mensal.
        """
        f_id = filial_id or "00001"
        t_id = tenant_id or "default"
        s_id = session_id or "default_session"
        ts = timestamp or datetime.now(UTC).isoformat()
        is_cache = cache_hit or cached

        if is_cache:
            eff_avoided_p = avoided_prompt_tokens or prompt_tokens or 450
            eff_avoided_c = avoided_completion_tokens or completion_tokens or 150
            cost_usd = 0.0
            cost_brl = 0.0
            total_tokens = 0
            p_tokens = 0
            c_tokens = 0
            avoided_brl = calculate_avoided_cost(
                model_name=model_name,
                estimated_prompt_tokens=eff_avoided_p,
                estimated_completion_tokens=eff_avoided_c,
            )
        else:
            calc = calculate_token_cost(
                model_name=model_name,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
            )
            cost_usd = calc["cost_usd"]
            cost_brl = calc["cost_brl"]
            total_tokens = calc["total_tokens"]
            p_tokens = prompt_tokens
            c_tokens = completion_tokens
            avoided_brl = 0.0

        with self._connection() as conn:
            conn.execute("""
                INSERT INTO aura_token_ledger (
                    session_id, filial_id, tenant_id, timestamp, model_name,
                    prompt_tokens, completion_tokens, total_tokens, cost_usd, cost_brl,
                    cache_hit, avoided_cost_brl, agent_role, intent_category, vertical_pack
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                s_id, f_id, t_id, ts, model_name,
                p_tokens, c_tokens, total_tokens, cost_usd, cost_brl,
                1 if is_cache else 0, avoided_brl,
                agent_role or "general_assistant",
                intent_category or "general",
                vertical_pack or "fuel_convenience",
            ))
            conn.commit()

        # Recalcula status do mes
        status = self.get_budget_status(filial_id=f_id)

        return {
            "session_id": s_id,
            "filial_id": f_id,
            "model_name": model_name,
            "prompt_tokens": p_tokens,
            "completion_tokens": c_tokens,
            "total_tokens": total_tokens,
            "cost_usd": cost_usd,
            "cost_brl": cost_brl,
            "cache_hit": cache_hit,
            "avoided_cost_brl": avoided_brl,
            "monthly_consumed_brl": status["monthly_consumed_brl"],
            "monthly_budget_brl": status["monthly_budget_brl"],
            "monthly_budget_pct": status["percentage_used"],
            "status": status["status"],
            "is_alert": status["is_alert"],
            "is_exceeded": status["is_exceeded"],
            "agent_role": agent_role,
            "intent_category": intent_category,
            "vertical_pack": vertical_pack,
        }

    def get_budget_status(
        self,
        filial_id: str,
        year: Optional[int] = None,
        month: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Retorna o panorama consolidado de consumo, metas e projecoes para a filial.
        """
        f_id = filial_id or "00001"
        now = datetime.now(UTC)
        y = year or now.year
        m = month or now.month

        prefix_month = f"{y:04d}-{m:02d}"
        prefix_today = now.strftime("%Y-%m-%d")

        policy = self.get_or_create_policy(f_id)
        monthly_budget = float(policy.get("monthly_budget_brl") or 30.00)
        daily_budget = float(policy.get("daily_budget_brl") or 2.50)
        alert_thresh = float(policy.get("alert_threshold_pct") or 80.0)
        policy_mode = str(policy.get("policy_mode") or "smart_pacing")

        with self._connection() as conn:
            # 1. Agregado do mes
            cur_m = conn.execute("""
                SELECT 
                    COUNT(*) as total_reqs,
                    SUM(total_tokens) as sum_tokens,
                    SUM(cost_brl) as sum_cost,
                    SUM(cost_usd) as sum_cost_usd,
                    SUM(avoided_cost_brl) as sum_avoided,
                    SUM(cache_hit) as sum_cache_hits
                FROM aura_token_ledger
                WHERE filial_id = ? AND timestamp LIKE ?;
            """, (f_id, f"{prefix_month}%"))
            row_m = cur_m.fetchone()

            # 2. Agregado de hoje
            cur_d = conn.execute("""
                SELECT 
                    SUM(total_tokens) as sum_tokens_today,
                    SUM(cost_brl) as sum_cost_today
                FROM aura_token_ledger
                WHERE filial_id = ? AND timestamp LIKE ?;
            """, (f_id, f"{prefix_today}%"))
            row_d = cur_d.fetchone()

        total_reqs = int(row_m["total_reqs"] or 0) if row_m else 0
        monthly_tokens = int(row_m["sum_tokens"] or 0) if row_m else 0
        monthly_cost = float(row_m["sum_cost"] or 0.0) if row_m else 0.0
        monthly_cost_usd = float(row_m["sum_cost_usd"] or 0.0) if row_m else 0.0
        avoided_cost = float(row_m["sum_avoided"] or 0.0) if row_m else 0.0
        cache_hits = int(row_m["sum_cache_hits"] or 0) if row_m else 0

        daily_tokens = int(row_d["sum_tokens_today"] or 0) if row_d else 0
        daily_cost = float(row_d["sum_cost_today"] or 0.0) if row_d else 0.0

        pct_used = (monthly_cost / monthly_budget * 100.0) if monthly_budget > 0 else 0.0
        is_exceeded = monthly_cost >= monthly_budget
        is_alert = pct_used >= alert_thresh

        if is_exceeded:
            status_label = "critical"
        elif is_alert:
            status_label = "warning"
        else:
            status_label = "normal"

        # Projecao fim do mes (Run-rate linear simples)
        day_of_month = max(1, now.day)
        last_day = 31 if m in (1, 3, 5, 7, 8, 10, 12) else (28 if m == 2 else 30)
        projected_cost = round((monthly_cost / day_of_month) * last_day, 2) if day_of_month > 0 else monthly_cost

        return {
            "filial_id": f_id,
            "period": prefix_month,
            "monthly_budget_brl": round(monthly_budget, 2),
            "daily_budget_brl": round(daily_budget, 2),
            "alert_threshold_pct": round(alert_thresh, 1),
            "policy_mode": policy_mode,
            "enforcement_mode": policy_mode,
            "monthly_consumed_brl": round(monthly_cost, 4),
            "monthly_consumed_usd": round(monthly_cost_usd, 4),
            "daily_consumed_brl": round(daily_cost, 4),
            "monthly_tokens": monthly_tokens,
            "daily_tokens": daily_tokens,
            "total_tokens_consumed": monthly_tokens,
            "total_cost_brl": round(monthly_cost, 4),
            "total_avoided_cost_brl": round(avoided_cost, 4),
            "avoided_cost_brl": round(avoided_cost, 4),
            "cache_hits_count": cache_hits,
            "total_requests_count": total_reqs,
            "percentage_used": round(pct_used, 2),
            "status": status_label,
            "is_alert": is_alert,
            "is_exceeded": is_exceeded,
            "projected_end_of_month_brl": projected_cost,
        }
    def get_usage_by_agent_role(self, filial_id: str, days: int = 30) -> list[Dict[str, Any]]:
        """Retorna o breakdown percentual e absoluto de tokens e custo agrupado por agent_role e intent_category."""
        f_id = filial_id or "00001"
        cutoff = (datetime.now(UTC) - timedelta(days=days)).isoformat()
        with self._connection() as conn:
            cur = conn.execute("""
                SELECT 
                    agent_role,
                    intent_category,
                    vertical_pack,
                    COUNT(*) as request_count,
                    SUM(prompt_tokens) as sum_prompt_tokens,
                    SUM(completion_tokens) as sum_completion_tokens,
                    SUM(total_tokens) as sum_total_tokens,
                    SUM(cost_brl) as sum_cost_brl,
                    SUM(cost_usd) as sum_cost_usd,
                    SUM(avoided_cost_brl) as sum_avoided_cost_brl
                FROM aura_token_ledger
                WHERE filial_id = ? AND timestamp >= ?
                GROUP BY agent_role, intent_category, vertical_pack
                ORDER BY sum_cost_brl DESC;
            """, (f_id, cutoff))
            rows = [dict(r) for r in cur.fetchall()]
            total_cost = sum(r.get("sum_cost_brl", 0.0) or 0.0 for r in rows)
            for r in rows:
                c = r.get("sum_cost_brl", 0.0) or 0.0
                r["cost_pct"] = round((c / total_cost * 100.0), 2) if total_cost > 0 else 0.0
            return rows

    def recommend_model_for_role(
        self,
        filial_id: str,
        agent_role: str,
        requested_model: str = "gemini-2.5-flash",
    ) -> Dict[str, Any]:
        """
        Implementa roteamento economico de modelos:
        - Micro-agentes de triagem operacional sao fixados em gemini-2.5-flash.
        - Se o consumo da filial ultrapassar alert_threshold_pct, aplica downgrade de pro para flash.
        """
        f_id = filial_id or "00001"
        status = self.get_budget_status(filial_id=f_id)
        is_alert = status.get("is_alert", False)
        is_exceeded = status.get("is_exceeded", False)

        target_role = (agent_role or "").strip().lower()
        low_cost_roles = {"erp_sop_triage_bot", "pos_productivity_bot"}

        chosen_model = requested_model
        downgrade_applied = False
        reason = "Modelo solicitado compativel com orcamento"

        if target_role in low_cost_roles:
            chosen_model = "gemini-2.5-flash"
            reason = "Papel operacional fixado em modelo de baixo custo"
        elif (is_alert or is_exceeded) and "pro" in (requested_model or "").lower():
            chosen_model = "gemini-2.5-flash"
            downgrade_applied = True
            reason = f"Downgrade preventivo ativo devido a orcamento em alerta ({status.get('percentage_used', 0.0)}% consumido)"

        return {
            "filial_id": f_id,
            "agent_role": target_role,
            "requested_model": requested_model,
            "recommended_model": chosen_model,
            "downgrade_applied": downgrade_applied,
            "reason": reason,
            "budget_status": status.get("status", "normal"),
            "percentage_used": status.get("percentage_used", 0.0),
        }

