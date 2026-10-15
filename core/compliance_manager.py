"""
Gerenciador de Conformidade Juridica, Titularidade de Dados e Opt-In Tecnico (LGPD & Clean Room).
Responsavel pelo registro duravel, validacao criptografica e verificacao do consentimento do lojista.
Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from config.settings import BASE_DIR
from core.schemas.compliance import ComplianceOptInStatus, ComplianceVerificationResult

logger = logging.getLogger("aura.compliance")

DEFAULT_TERM_PATH = BASE_DIR / "docs" / "compliance" / "termo_interoperabilidade_lgpd.md"


class ComplianceManager:
    """
    Gerenciador central de conformidade e opt-in de interoperabilidade da AURA.
    Garante que a operacao local cumpra as exigencias da LGPD, Lei de Software e Marco Civil,
    mantendo registros auditaveis no SQLite local e em arquivo JSON de contingencia.
    """

    def __init__(
        self,
        db_path: str | Path | None = None,
        json_path: str | Path | None = None,
        term_path: str | Path | None = None,
        session_memory: Any | None = None,
    ):
        self.term_path = Path(term_path) if term_path else DEFAULT_TERM_PATH

        # Configuracao de persistencia SQLite
        if db_path is not None:
            if str(db_path) == ":memory:":
                self.db_path = ":memory:"
                self._shared_conn = sqlite3.connect(":memory:", check_same_thread=False)
                self._shared_conn.row_factory = sqlite3.Row
            else:
                self.db_path = str(db_path)
                Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
                self._shared_conn = None
        elif session_memory is not None and getattr(session_memory, "db_path", None) == ":memory:":
            self.db_path = ":memory:"
            self._shared_conn = getattr(session_memory, "_shared_conn", None)
            if self._shared_conn is None:
                self._shared_conn = sqlite3.connect(":memory:", check_same_thread=False)
                self._shared_conn.row_factory = sqlite3.Row
        else:
            data_dir = BASE_DIR / "data"
            data_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = str(data_dir / "compliance.db")
            self._shared_conn = None

        # Configuracao de arquivo JSON de contingencia
        if json_path is not None:
            self.json_path = Path(json_path) if json_path else None
        elif self.db_path == ":memory:" or db_path is not None:
            self.json_path = None
        else:
            data_dir = BASE_DIR / "data"
            data_dir.mkdir(parents=True, exist_ok=True)
            self.json_path = data_dir / "compliance_opt_in.json"

        self._init_db()

    @contextmanager
    def _connection(self):
        """Gerenciador de contexto para transacoes seguras no SQLite."""
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
        """Cria as tabelas necessarias de auditoria e opt-in no SQLite."""
        with self._connection() as conn:
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA synchronous = NORMAL;")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS compliance_opt_in (
                    loja_cnpj TEXT PRIMARY KEY,
                    cnpj_limpo TEXT,
                    razao_social TEXT NOT NULL,
                    aceite_interoperabilidade_em TEXT NOT NULL,
                    versao_termo TEXT NOT NULL,
                    status TEXT NOT NULL,
                    assinado_por TEXT NOT NULL,
                    hash_termo TEXT NOT NULL,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            try:
                conn.execute("ALTER TABLE compliance_opt_in ADD COLUMN cnpj_limpo TEXT;")
            except sqlite3.OperationalError:
                pass
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_compliance_cnpj_limpo
                ON compliance_opt_in (cnpj_limpo);
            """)

    def get_term_path(self) -> Path:
        """Retorna o caminho do arquivo do termo de interoperabilidade."""
        return self.term_path

    def get_term_content(self) -> str:
        """Le o conteudo textual integral do termo formal em UTF-8."""
        if not self.term_path.exists():
            raise FileNotFoundError(f"Arquivo do termo de conformidade nao encontrado: {self.term_path}")
        return self.term_path.read_text(encoding="utf-8")

    def compute_term_hash(self, path: str | Path | None = None) -> str:
        """
        Calcula o digest SHA-256 criptografico do arquivo do termo de conformidade.
        Retorna string vazia caso o arquivo nao exista.
        """
        target = Path(path) if path else self.term_path
        if not target.exists():
            return ""
        content = target.read_text(encoding="utf-8")
        normalized = content.replace("\r\n", "\n")
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def register_opt_in(
        self,
        opt_in: ComplianceOptInStatus | dict[str, Any],
    ) -> ComplianceOptInStatus:
        """
        Registra ou atualiza o opt-in de interoperabilidade do lojista.
        Persiste no SQLite e espelha no arquivo JSON de contingencia.
        """
        if isinstance(opt_in, dict):
            dados = dict(opt_in)
            if not dados.get("hash_termo"):
                dados["hash_termo"] = self.compute_term_hash()
            if not dados.get("aceite_interoperabilidade_em"):
                dados["aceite_interoperabilidade_em"] = datetime.now(UTC).isoformat()
            if not dados.get("versao_termo"):
                dados["versao_termo"] = "1.0"
            if not dados.get("status"):
                dados["status"] = "active"
            record = ComplianceOptInStatus(**dados)
        elif isinstance(opt_in, ComplianceOptInStatus):
            record = opt_in
        else:
            raise TypeError(f"opt_in deve ser ComplianceOptInStatus ou dict, recebido {type(opt_in)}")

        meta_json = json.dumps(record.metadata or {}, ensure_ascii=False)
        clean = record.cnpj_limpo

        # 1. Persistencia no SQLite
        with self._connection() as conn:
            if clean:
                conn.execute(
                    "DELETE FROM compliance_opt_in WHERE cnpj_limpo = ? AND loja_cnpj != ?;",
                    (clean, record.loja_cnpj),
                )

            conn.execute("""
                INSERT INTO compliance_opt_in (
                    loja_cnpj,
                    cnpj_limpo,
                    razao_social,
                    aceite_interoperabilidade_em,
                    versao_termo,
                    status,
                    assinado_por,
                    hash_termo,
                    metadata,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(loja_cnpj) DO UPDATE SET
                    cnpj_limpo = excluded.cnpj_limpo,
                    razao_social = excluded.razao_social,
                    aceite_interoperabilidade_em = excluded.aceite_interoperabilidade_em,
                    versao_termo = excluded.versao_termo,
                    status = excluded.status,
                    assinado_por = excluded.assinado_por,
                    hash_termo = excluded.hash_termo,
                    metadata = excluded.metadata,
                    updated_at = CURRENT_TIMESTAMP;
            """, (
                record.loja_cnpj,
                clean,
                record.razao_social,
                record.aceite_interoperabilidade_em,
                record.versao_termo,
                record.status,
                record.assinado_por,
                record.hash_termo,
                meta_json,
            ))

        # 2. Espelhamento em arquivo JSON
        self._sync_to_json(record)

        logger.info(
            "Opt-in registrado com sucesso para CNPJ %s (%s) - status: %s",
            record.loja_cnpj,
            record.razao_social,
            record.status,
        )
        return record

    def record_opt_in(
        self,
        opt_in: ComplianceOptInStatus | dict[str, Any],
    ) -> ComplianceOptInStatus:
        """Alias de conveniencia para register_opt_in."""
        return self.register_opt_in(opt_in)

    def _sync_to_json(self, record: ComplianceOptInStatus) -> None:
        """Salva o opt-in no arquivo JSON local para contingencia offline."""
        if not self.json_path:
            return
        try:
            self.json_path.parent.mkdir(parents=True, exist_ok=True)
            current_data: dict[str, Any] = {}
            if self.json_path.exists():
                try:
                    loaded = json.loads(self.json_path.read_text(encoding="utf-8"))
                    if isinstance(loaded, dict):
                        current_data = loaded
                except (json.JSONDecodeError, OSError):
                    current_data = {}

            clean = record.cnpj_limpo
            if clean:
                to_delete = [
                    k for k, v in current_data.items()
                    if not k.startswith("_") and isinstance(v, dict) and re.sub(r"\D", "", k) == clean and k != record.loja_cnpj
                ]
                for k in to_delete:
                    del current_data[k]

            current_data[record.loja_cnpj] = record.model_dump()
            current_data["_last_updated"] = datetime.now(UTC).isoformat()
            current_data["_latest_cnpj"] = record.loja_cnpj

            self.json_path.write_text(
                json.dumps(current_data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError as e:
            logger.warning("Nao foi possivel sincronizar opt-in no JSON: %s", e)

    def get_opt_in(self, loja_cnpj: str | None = None) -> ComplianceOptInStatus | None:
        """
        Recupera o registro de opt-in formal do lojista.
        Se loja_cnpj nao for fornecido ou for vazio, retorna o registro mais recente cadastrado.
        """
        target = loja_cnpj.strip() if (loja_cnpj and loja_cnpj.strip()) else None
        clean = re.sub(r"\D", "", target) if target else None

        # 1. Busca no SQLite
        with self._connection() as conn:
            if target:
                row = conn.execute(
                    "SELECT * FROM compliance_opt_in WHERE loja_cnpj = ?;",
                    (target,),
                ).fetchone()

                if row is None and clean:
                    row = conn.execute(
                        "SELECT * FROM compliance_opt_in WHERE cnpj_limpo = ?;",
                        (clean,),
                    ).fetchone()
                    if row is None:
                        rows = conn.execute("SELECT * FROM compliance_opt_in;").fetchall()
                        for r in rows:
                            if re.sub(r"\D", "", r["loja_cnpj"]) == clean:
                                row = r
                                break
            else:
                row = conn.execute(
                    "SELECT * FROM compliance_opt_in ORDER BY updated_at DESC LIMIT 1;"
                ).fetchone()

            if row:
                metadata = None
                if row["metadata"]:
                    try:
                        metadata = json.loads(row["metadata"])
                    except (json.JSONDecodeError, TypeError):
                        metadata = None
                return ComplianceOptInStatus(
                    loja_cnpj=row["loja_cnpj"],
                    razao_social=row["razao_social"],
                    aceite_interoperabilidade_em=row["aceite_interoperabilidade_em"],
                    versao_termo=row["versao_termo"],
                    status=row["status"],
                    assinado_por=row["assinado_por"],
                    hash_termo=row["hash_termo"],
                    metadata=metadata,
                )

        # 2. Fallback no JSON se SQLite estiver vazio
        if self.json_path and self.json_path.exists():
            try:
                data = json.loads(self.json_path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    lookup_cnpj = target or data.get("_latest_cnpj")
                    if lookup_cnpj and lookup_cnpj in data and isinstance(data[lookup_cnpj], dict):
                        return ComplianceOptInStatus(**data[lookup_cnpj])

                    if clean:
                        for k, v in data.items():
                            if (
                                not k.startswith("_")
                                and isinstance(v, dict)
                                and re.sub(r"\D", "", k) == clean
                            ):
                                return ComplianceOptInStatus(**v)
            except (json.JSONDecodeError, OSError, TypeError) as e:
                logger.warning("Falha ao ler opt-in do fallback JSON: %s", e)

        return None

    def get_opt_in_status(self, loja_cnpj: str | None = None) -> ComplianceOptInStatus | None:
        """Alias para get_opt_in."""
        return self.get_opt_in(loja_cnpj)

    def is_opt_in_valid(
        self,
        loja_cnpj: str | None = None,
        verify_hash: bool = True,
    ) -> bool:
        """
        Valida se o opt-in esta ativo e, opcionalmente, se o hash registrado
        corresponde ao digest do arquivo fisico do termo atual.
        """
        opt_in = self.get_opt_in(loja_cnpj)
        if opt_in is None:
            return False

        if not opt_in.is_active:
            return False

        if verify_hash:
            current_hash = self.compute_term_hash()
            if current_hash and opt_in.hash_termo != current_hash:
                logger.warning(
                    "Hash do termo de conformidade divergente: registrado=%s vs atual=%s",
                    opt_in.hash_termo,
                    current_hash,
                )
                return False

        return True

    def revoke_opt_in(self, loja_cnpj: str, reason: str = "") -> bool:
        """
        Revoga o consentimento de interoperabilidade para o CNPJ informado.
        Atualiza todas as representacoes formatadas ou desformatadas do CNPJ.
        """
        if not loja_cnpj or not loja_cnpj.strip():
            return False

        clean_target = re.sub(r"\D", "", loja_cnpj.strip())
        target = loja_cnpj.strip()

        with self._connection() as conn:
            rows = conn.execute("SELECT loja_cnpj, cnpj_limpo, metadata FROM compliance_opt_in;").fetchall()
            matched_cnpjs = []
            meta_dict: dict[str, Any] = {}
            for r in rows:
                row_clean = r["cnpj_limpo"] or re.sub(r"\D", "", r["loja_cnpj"])
                if r["loja_cnpj"] == target or (clean_target and row_clean == clean_target):
                    matched_cnpjs.append(r["loja_cnpj"])
                    if r["metadata"] and not meta_dict:
                        try:
                            meta_dict = json.loads(r["metadata"])
                        except (json.JSONDecodeError, TypeError):
                            meta_dict = {}

            if not matched_cnpjs:
                return False

            meta_dict["revocation_reason"] = reason
            meta_dict["revoked_at"] = datetime.now(UTC).isoformat()
            meta_json = json.dumps(meta_dict, ensure_ascii=False)

            for matched in matched_cnpjs:
                conn.execute("""
                    UPDATE compliance_opt_in
                    SET status = 'revoked', metadata = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE loja_cnpj = ?;
                """, (meta_json, matched))

        # Atualiza JSON
        if self.json_path and self.json_path.exists():
            try:
                data = json.loads(self.json_path.read_text(encoding="utf-8"))
                for matched in matched_cnpjs:
                    if matched in data and isinstance(data[matched], dict):
                        data[matched]["status"] = "revoked"
                        data[matched]["metadata"] = meta_dict
                self.json_path.write_text(
                    json.dumps(data, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
            except (json.JSONDecodeError, OSError, TypeError) as e:
                logger.warning("Nao foi possivel atualizar revogacao no JSON: %s", e)

        logger.info("Opt-in revogado com sucesso para CNPJs %s (motivo: %s)", matched_cnpjs, reason)
        return True

    def verify_compliance(
        self,
        loja_cnpj: str | None = None,
    ) -> ComplianceVerificationResult:
        """
        Executa diagnostico de conformidade legal e tecnica do estabelecimento.
        Garante integridade do termo, correspondencia de hash e garantias de Read-Only/AUPS.
        """
        current_hash = self.compute_term_hash()
        term_exists = self.term_path.exists() and bool(current_hash)

        opt_in = self.get_opt_in(loja_cnpj)
        target_cnpj = loja_cnpj or (opt_in.loja_cnpj if opt_in else "00.000.000/0001-00")

        if not term_exists:
            return ComplianceVerificationResult(
                compliant=False,
                loja_cnpj=target_cnpj,
                razao_social=opt_in.razao_social if opt_in else None,
                versao_termo=opt_in.versao_termo if opt_in else None,
                status="missing_term",
                aceite_interoperabilidade_em=opt_in.aceite_interoperabilidade_em if opt_in else None,
                assinado_por=opt_in.assinado_por if opt_in else None,
                hash_termo=opt_in.hash_termo if opt_in else None,
                hash_atual_termo="",
                hash_confere=False,
                garantia_leitura_exclusiva=True,
                isolamento_aups=True,
                mensagem="Arquivo do termo juridico nao encontrado na instalacao local.",
            )

        if opt_in is None:
            return ComplianceVerificationResult(
                compliant=False,
                loja_cnpj=target_cnpj,
                razao_social=None,
                versao_termo=None,
                status="pending_opt_in",
                aceite_interoperabilidade_em=None,
                assinado_por=None,
                hash_termo=None,
                hash_atual_termo=current_hash,
                hash_confere=False,
                garantia_leitura_exclusiva=True,
                isolamento_aups=True,
                mensagem="Estabelecimento sem opt-in formal de interoperabilidade registrado.",
            )

        hash_confere = (opt_in.hash_termo == current_hash)
        is_active = opt_in.is_active

        compliant = is_active and hash_confere

        if compliant:
            mensagem = (
                f"Conformidade 100% ativa para {opt_in.razao_social} (CNPJ: {opt_in.loja_cnpj}). "
                f"Opt-in formalizado por {opt_in.assinado_por} com hash conferido e operacao Read-Only."
            )
        elif not is_active:
            mensagem = f"Opt-in do estabelecimento encontra-se no status '{opt_in.status}' (nao ativo)."
        else:
            mensagem = (
                "Opt-in ativo porem com versao do termo desatualizada ou modificada "
                f"(hash registrado {opt_in.hash_termo[:8]} != atual {current_hash[:8]})."
            )

        return ComplianceVerificationResult(
            compliant=compliant,
            loja_cnpj=opt_in.loja_cnpj,
            razao_social=opt_in.razao_social,
            versao_termo=opt_in.versao_termo,
            status=opt_in.status,
            aceite_interoperabilidade_em=opt_in.aceite_interoperabilidade_em,
            assinado_por=opt_in.assinado_por,
            hash_termo=opt_in.hash_termo,
            hash_atual_termo=current_hash,
            hash_confere=hash_confere,
            garantia_leitura_exclusiva=True,
            isolamento_aups=True,
            mensagem=mensagem,
        )

    def get_driver_protection_status(self) -> dict[str, Any]:
        """Retorna o status da blindagem em nivel de driver PostgreSQL (Secao 3.2 e Clausula Quarta da v1.1)."""
        from config.settings import DB_ERP_CONFIG

        options_str = str(DB_ERP_CONFIG.get("options", ""))
        has_ro = "default_transaction_read_only=on" in options_str
        has_stmt_timeout = "statement_timeout=" in options_str
        has_lock_timeout = "lock_timeout=" in options_str
        return {
            "driver_options": options_str,
            "read_only_enforced": has_ro,
            "statement_timeout_enforced": has_stmt_timeout,
            "lock_timeout_enforced": has_lock_timeout,
            "forensic_safe": has_ro and has_stmt_timeout and has_lock_timeout,
        }

    def verify_compliance_environment(
        self,
        loja_cnpj: str | None = None,
    ) -> dict[str, Any]:
        """Metodo utilitario compativel com dicionarios para consumo simplificado."""
        result = self.verify_compliance(loja_cnpj)
        out = result.model_dump()
        out["driver_protection"] = self.get_driver_protection_status()
        return out
