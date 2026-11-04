"""
Modulo de Memoria Auditavel da Camada Tenant (Fase 7).
Gerencia regras, apelidos de produto, preferencias e rotinas operacionais por posto/filial.
Implementa ciclo de vida estrito: pendente -> ativo / rejeitado / obsoleto.
Precedencia cognitiva maxima sobre camadas globais (tenant > erp > vertical > core).
Zero travessoes em todo o modulo.
"""

from __future__ import annotations

import json
import logging
import re
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config.settings import BASE_DIR

logger = logging.getLogger("AuraTenantMemory")

VALID_STATUSES = {"pendente", "ativo", "rejeitado", "obsoleto"}
VALID_CATEGORIES = {
    "apelido_produto",
    "rotina_operacional",
    "preferencia_gestor",
    "regra_posto",
    "geral",
}
VALID_ORIGINS = {"chat", "gestor", "api", "documento"}


@dataclass
class TenantMemoryFact:
    """Entidade de fato ou instrucao aprendida na camada tenant."""

    id: str
    tenant_id: str
    filial_id: int
    categoria: str
    chave: str
    conteudo: str
    status: str
    origem: str
    confianca: float
    metadata: dict[str, Any]
    criado_em: str
    atualizado_em: str
    aprovado_por: str | None = None
    aprovado_em: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class TenantMemoryManager:
    """
    Gerenciador de memoria duravel da camada tenant por filial.
    Persiste fatos locais em SQLite (data/aura_sessions.db) com suporte
    a sincronizacao opcional com pgvector em aura_core.aura_conhecimento_chunks.
    """

    def __init__(self, db_path: str | Path | None = None) -> None:
        if db_path is None:
            data_dir = BASE_DIR / "data"
            data_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = str(data_dir / "aura_sessions.db")
            self._shared_conn: sqlite3.Connection | None = None
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

    def _init_db(self) -> None:
        """Cria tabelas e indices de memoria do tenant com WAL."""
        with self._connection() as conn:
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA synchronous = NORMAL;")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS aura_tenant_memory (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    filial_id INTEGER NOT NULL DEFAULT 1,
                    categoria TEXT NOT NULL,
                    chave TEXT NOT NULL,
                    conteudo TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pendente',
                    origem TEXT NOT NULL DEFAULT 'chat',
                    confianca REAL NOT NULL DEFAULT 1.0,
                    metadata TEXT DEFAULT '{}',
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    aprovado_por TEXT,
                    aprovado_em TIMESTAMP
                );
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tenant_mem_scope
                    ON aura_tenant_memory (tenant_id, filial_id, status);
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tenant_mem_cat
                    ON aura_tenant_memory (tenant_id, categoria, status);
            """)

    def learn_fact(
        self,
        tenant_id: str,
        filial_id: int = 1,
        categoria: str = "regra_posto",
        chave: str = "",
        conteudo: str = "",
        status: str = "pendente",
        origem: str = "chat",
        confianca: float = 1.0,
        metadata: dict[str, Any] | None = None,
        fact_id: str | None = None,
    ) -> TenantMemoryFact:
        """
        Registra um fato ou regra para o tenant.
        Por padrao, nasce com status='pendente' para revisao humana,
        exceto quando cadastrado diretamente pelo gestor.
        """
        if not tenant_id or not isinstance(tenant_id, str):
            raise ValueError("tenant_id e obrigatorio e deve ser uma string valida.")
        if status not in VALID_STATUSES:
            raise ValueError(f"Status invalido: {status}. Esperado: {VALID_STATUSES}")
        if categoria not in VALID_CATEGORIES:
            categoria = "geral"
        if origem not in VALID_ORIGINS:
            origem = "chat"

        fid = fact_id or f"mem_{uuid.uuid4().hex[:12]}"
        now_iso = datetime.now(timezone.utc).isoformat()
        meta_dict = metadata or {}
        meta_json = json.dumps(meta_dict, ensure_ascii=False)

        aprovado_por = "gestor" if status == "ativo" else None
        aprovado_em = now_iso if status == "ativo" else None

        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO aura_tenant_memory (
                    id, tenant_id, filial_id, categoria, chave, conteudo,
                    status, origem, confianca, metadata, criado_em, atualizado_em,
                    aprovado_por, aprovado_em
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    chave = excluded.chave,
                    conteudo = excluded.conteudo,
                    status = excluded.status,
                    metadata = excluded.metadata,
                    atualizado_em = excluded.atualizado_em,
                    aprovado_por = excluded.aprovado_por,
                    aprovado_em = excluded.aprovado_em
                ;
                """,
                (
                    fid,
                    tenant_id.strip(),
                    int(filial_id),
                    categoria,
                    chave.strip()[:100],
                    conteudo.strip(),
                    status,
                    origem,
                    float(confianca),
                    meta_json,
                    now_iso,
                    now_iso,
                    aprovado_por,
                    aprovado_em,
                ),
            )

        logger.info(
            "Fato tenant registrado: id=%s tenant=%s filial=%d status=%s cat=%s",
            fid,
            tenant_id,
            filial_id,
            status,
            categoria,
        )

        return TenantMemoryFact(
            id=fid,
            tenant_id=tenant_id.strip(),
            filial_id=int(filial_id),
            categoria=categoria,
            chave=chave.strip()[:100],
            conteudo=conteudo.strip(),
            status=status,
            origem=origem,
            confianca=float(confianca),
            metadata=meta_dict,
            criado_em=now_iso,
            atualizado_em=now_iso,
            aprovado_por=aprovado_por,
            aprovado_em=aprovado_em,
        )

    def approve_fact(
        self,
        fact_id: str,
        approved_by: str = "gestor",
        tenant_id: str | None = None,
    ) -> TenantMemoryFact | None:
        """
        Aprova um fato pendente, tornando-o 'ativo'.
        Fatos ativos entram imediatamente no prompt e nas buscas cognitivas daquele tenant.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._connection() as conn:
            if tenant_id:
                cur = conn.execute(
                    """
                    UPDATE aura_tenant_memory
                    SET status = 'ativo',
                        aprovado_por = ?,
                        aprovado_em = ?,
                        atualizado_em = ?
                    WHERE id = ? AND tenant_id = ?
                    RETURNING *;
                    """,
                    (approved_by, now_iso, now_iso, fact_id, tenant_id),
                )
            else:
                cur = conn.execute(
                    """
                    UPDATE aura_tenant_memory
                    SET status = 'ativo',
                        aprovado_por = ?,
                        aprovado_em = ?,
                        atualizado_em = ?
                    WHERE id = ?
                    RETURNING *;
                    """,
                    (approved_by, now_iso, now_iso, fact_id),
                )
            row = cur.fetchone()
            if not row:
                return None

            fact = self._row_to_fact(row)
            self._sync_to_pgvector(fact)
            return fact

    def reject_fact(
        self,
        fact_id: str,
        reason: str | None = None,
        tenant_id: str | None = None,
    ) -> TenantMemoryFact | None:
        """Rejeita um fato pendente, marcando status='rejeitado'."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._connection() as conn:
            query = "SELECT * FROM aura_tenant_memory WHERE id = ?"
            params: list[Any] = [fact_id]
            if tenant_id:
                query += " AND tenant_id = ?"
                params.append(tenant_id)
            row = conn.execute(query, params).fetchone()
            if not row:
                return None

            current_meta = json.loads(row["metadata"] or "{}")
            if reason:
                current_meta["motivo_rejeicao"] = reason
            meta_json = json.dumps(current_meta, ensure_ascii=False)

            cur = conn.execute(
                """
                UPDATE aura_tenant_memory
                SET status = 'rejeitado',
                    metadata = ?,
                    atualizado_em = ?
                WHERE id = ?
                RETURNING *;
                """,
                (meta_json, now_iso, fact_id),
            )
            updated = cur.fetchone()
            return self._row_to_fact(updated) if updated else None

    def delete_fact(self, fact_id: str, tenant_id: str | None = None) -> bool:
        """Inativa um fato marcando status='obsoleto'."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._connection() as conn:
            query = "UPDATE aura_tenant_memory SET status = 'obsoleto', atualizado_em = ? WHERE id = ?"
            params = [now_iso, fact_id]
            if tenant_id:
                query += " AND tenant_id = ?"
                params.append(tenant_id)
            cur = conn.execute(query, params)
            return cur.rowcount > 0

    def list_facts(
        self,
        tenant_id: str,
        filial_id: int | None = None,
        status: str | None = None,
        categoria: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[TenantMemoryFact]:
        """Lista fatos do tenant com filtros operacionais."""
        clauses = ["tenant_id = ?"]
        params: list[Any] = [tenant_id.strip()]

        if filial_id is not None:
            clauses.append("filial_id = ?")
            params.append(int(filial_id))
        if status:
            clauses.append("status = ?")
            params.append(status)
        else:
            clauses.append("status != 'obsoleto'")
        if categoria:
            clauses.append("categoria = ?")
            params.append(categoria)

        sql = f"""
            SELECT * FROM aura_tenant_memory
            WHERE {' AND '.join(clauses)}
            ORDER BY criado_em DESC
            LIMIT ? OFFSET ?;
        """
        params.extend([max(1, limit), max(0, offset)])

        with self._connection() as conn:
            cur = conn.execute(sql, params)
            rows = cur.fetchall()
            return [self._row_to_fact(r) for r in rows]

    def get_active_memories(
        self,
        tenant_id: str,
        filial_id: int | None = None,
        query: str | None = None,
        limit: int = 15,
    ) -> list[TenantMemoryFact]:
        """
        Retorna memórias ativas ('ativo') para injeção no prompt ou resolução cognitiva.
        Se query for informada, filtra de forma lexical sobre chave e conteúdo.
        """
        clauses = ["tenant_id = ?", "status = 'ativo'"]
        params: list[Any] = [tenant_id.strip()]

        if filial_id is not None:
            clauses.append("(filial_id = ? OR filial_id = 0)")
            params.append(int(filial_id))

        if query and query.strip():
            terms = [t for t in re.findall(r"\w+", query.lower()) if len(t) >= 3]
            if terms:
                sub_or = " OR ".join(["(instr(lower(chave), ?) > 0 OR instr(lower(conteudo), ?) > 0)"] * len(terms))
                clauses.append(f"({sub_or})")
                for t in terms:
                    params.extend([t, t])

        sql = f"""
            SELECT * FROM aura_tenant_memory
            WHERE {' AND '.join(clauses)}
            ORDER BY
                CASE categoria
                    WHEN 'regra_posto' THEN 1
                    WHEN 'apelido_produto' THEN 2
                    WHEN 'rotina_operacional' THEN 3
                    WHEN 'preferencia_gestor' THEN 4
                    ELSE 5
                END,
                atualizado_em DESC
            LIMIT ?;
        """
        params.append(max(1, limit))

        with self._connection() as conn:
            cur = conn.execute(sql, params)
            return [self._row_to_fact(r) for r in cur.fetchall()]

    def format_memories_for_prompt(
        self,
        tenant_id: str,
        filial_id: int | None = None,
        query: str | None = None,
        limit: int = 10,
    ) -> str:
        """
        Formata memórias ativas em bloco de texto para inclusão no prompt executivo.
        Regra: Precedencia maxima sobre manuais de ERP, mas sem revogar normas legais core.
        """
        facts = self.get_active_memories(tenant_id, filial_id, query=query, limit=limit)
        if not facts:
            return ""

        lines = ["[MEMORIA DO POSTO (PREFERENCIAS E REGRAS ATIVAS DO TENANT)]:"]
        lines.append("- Estas regras sao especificas deste posto e tem precedencia sobre manuais genericos.")
        for f in facts:
            cat_label = f.categoria.replace("_", " ").title()
            chave_str = f" ({f.chave})" if f.chave else ""
            lines.append(f"- [{cat_label}{chave_str}]: {f.conteudo}")

        return "\n".join(lines)

    def detect_learning_opportunity(
        self,
        user_message: str,
        assistant_response: str = "",
    ) -> dict[str, Any] | None:
        """
        Analisa a interacao do operador para detectar oportunidade de aprendizado duravel.
        Exemplos detectados:
        - 'grave que...', 'lembre que...', 'aqui no posto sempre...'
        - 'chame coca lata de ...', 'apelido de x e y'
        - 'o fechamento do turno x ocorre as ...'
        """
        msg = (user_message or "").strip()
        if len(msg) < 8:
            return None

        # Padrao 1: Apelidos de produto / sinonimos
        alias_pat = re.compile(
            r"(?:chame|considere|trate|apelido|sinonimo)\s+(?:o|a|de)?\s*[\"']?([^\"',.]+?)[\"']?\s+(?:como|de|por)\s+[\"']?([^\"',.]+?)[\"']?$",
            re.IGNORECASE,
        )
        m = alias_pat.search(msg)
        if m:
            item_a, item_b = m.group(1).strip(), m.group(2).strip()
            return {
                "categoria": "apelido_produto",
                "chave": item_a,
                "conteudo": f"Apelido de produto: '{item_a}' refere-se a '{item_b}'.",
                "confianca": 0.95,
            }

        # Padrao 2: Regras explicitas ('grave que', 'lembre que', 'registre que', 'regra aqui:')
        explicit_pat = re.compile(
            r"(?:grave|lembre|registre|salve|anote|fixe)\s+(?:que|aqui|regra)?\s*[:,-]?\s*(.+)$",
            re.IGNORECASE,
        )
        m2 = explicit_pat.search(msg)
        if m2:
            regra_texto = m2.group(1).strip()
            cat = "regra_posto"
            if any(w in regra_texto.lower() for w in ("turno", "horario", "fechamento", "abertura", "rotina")):
                cat = "rotina_operacional"
            elif any(w in regra_texto.lower() for w in ("relatorio", "ordene", "prefiro", "formato")):
                cat = "preferencia_gestor"

            return {
                "categoria": cat,
                "chave": regra_texto[:40],
                "conteudo": regra_texto,
                "confianca": 0.90,
            }

        # Padrao 3: Rotinas do posto ('aqui no posto...', 'na nossa filial...')
        routine_pat = re.compile(
            r"(?:aqui no posto|na nossa filial|no nosso posto|nesta filial)\s+([a-zA-Z0-9_ ]+?)(?:sempre|nunca|so|somente)\s+(.+)$",
            re.IGNORECASE,
        )
        m3 = routine_pat.search(msg)
        if m3:
            sujeito = m3.group(1).strip()
            predicado = m3.group(2).strip()
            return {
                "categoria": "rotina_operacional",
                "chave": sujeito[:30],
                "conteudo": f"Na filial, {sujeito} sempre/somente {predicado}.",
                "confianca": 0.85,
            }

        return None

    def _sync_to_pgvector(self, fact: TenantMemoryFact) -> bool:
        """
        Sincroniza fato aprovado para a tabela central de chunks pgvector se disponivel.
        Mantem o isolamento com camada='tenant' e tenant_id informado.
        """
        try:
            from core.db_pool import get_vector_connection

            doc_id = f"TENANT-{fact.id}"
            embed_text = f"[Memoria do Posto: {fact.categoria}] {fact.chave}: {fact.conteudo}"
            hash_str = f"h_{uuid.uuid5(uuid.NAMESPACE_DNS, fact.id + fact.conteudo).hex[:16]}"

            with get_vector_connection(filial_id=fact.filial_id) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO aura_core.aura_conhecimento_chunks (
                            camada, vertical, erp, tenant_id, status,
                            fonte, doc_id, doc_titulo, breadcrumb, secao,
                            chunk_idx, chunk_total, conteudo, conteudo_embed,
                            hash_md5, atualizado_em
                        ) VALUES (
                            'tenant', 'posto', 'memoria_local', %s, 'ativo',
                            'aura_tenant_memory', %s, %s, %s, %s,
                            1, 1, %s, %s,
                            %s, now()
                        )
                        ON CONFLICT (camada, erp, tenant_id, doc_id, chunk_idx)
                        DO UPDATE SET
                            conteudo = EXCLUDED.conteudo,
                            conteudo_embed = EXCLUDED.conteudo_embed,
                            status = 'ativo',
                            atualizado_em = now();
                        """,
                        (
                            fact.tenant_id,
                            doc_id,
                            f"Regra do Posto: {fact.chave or fact.categoria}",
                            "Memoria do Posto > " + fact.categoria,
                            fact.categoria,
                            fact.conteudo,
                            embed_text,
                            hash_str,
                        ),
                    )
            return True
        except Exception as exc:
            logger.debug("Sincronizacao pgvector para fato %s ignorada/falhou: %s", fact.id, exc)
            return False

    @staticmethod
    def _row_to_fact(row: sqlite3.Row) -> TenantMemoryFact:
        meta = {}
        if row["metadata"]:
            try:
                meta = json.loads(row["metadata"])
            except Exception:
                pass
        return TenantMemoryFact(
            id=row["id"],
            tenant_id=row["tenant_id"],
            filial_id=row["filial_id"],
            categoria=row["categoria"],
            chave=row["chave"],
            conteudo=row["conteudo"],
            status=row["status"],
            origem=row["origem"],
            confianca=row["confianca"],
            metadata=meta,
            criado_em=row["criado_em"],
            atualizado_em=row["atualizado_em"],
            aprovado_por=row["aprovado_por"],
            aprovado_em=row["aprovado_em"],
        )
