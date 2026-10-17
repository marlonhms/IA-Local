"""
Testes Unitarios de Action Vouchers, Governanca RBAC, Idempotencia e Rollback
(core/aura_api.py, core/aura_engine.py, core/schemas/genui.py).
Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from core.aura_api import (
    create_aura_app,
    evaluate_action_permission,
    set_command_journal,
)
from core.aura_engine import AuraEngine, AuraSessionMemory
from core.command_journal import (
    AuraCommandJournal,
    CommandJournalStatus,
    reset_command_journal,
)
from core.schemas.genui import (
    ActionAuditLogRecord,
    ActionExecuteRequest,
    ActionVoucher,
    generate_action_voucher_signature,
    verify_action_voucher_signature,
)
from core.schemas.idempotency import (
    generate_action_id,
    generate_tool_call_id,
    generate_uuid4,
)


@pytest.fixture(autouse=True)
def _isolated_voucher_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    """Garante isolamento completo do Command Journal entre os testes de Action Vouchers."""
    journal_db = tmp_path / "voucher_test_journal.db"
    monkeypatch.setenv("AURA_COMMAND_JOURNAL_DB_PATH", str(journal_db))
    reset_command_journal()
    set_command_journal(None)
    yield
    reset_command_journal()
    set_command_journal(None)


class TestActionVoucherContractsAndSignatures:
    """Valida os contratos Pydantic v2 e a assinatura criptografica HMAC-SHA256."""

    def test_action_execute_request_validation(self) -> None:
        """Verifica aceitacao de UUIDs validos e rejeicao de identificadores malformados."""
        tool_id = generate_tool_call_id()
        act_id = generate_action_id()
        sess_id = f"sess_{uuid.uuid4()}"

        req = ActionExecuteRequest(
            session_id=sess_id,
            tool_call_id=tool_id,
            action_id=act_id,
            action_name="pedido_combustivel",
            action_type="mutation",
            payload={"litros": 15000, "combustivel": "GASOLINA COMUM"},
            operator_id="gerente_01",
            operator_role="gerente",
            idempotency_key=f"voucher:{act_id}:execute",
        )
        assert req.session_id == sess_id
        assert req.tool_call_id == tool_id
        assert req.action_id == act_id
        assert req.idempotency_key == f"voucher:{act_id}:execute"

        with pytest.raises(ValidationError):
            ActionExecuteRequest(tool_call_id="invalid_call_id", action_id=act_id)

        with pytest.raises(ValidationError):
            ActionExecuteRequest(tool_call_id=tool_id, action_id="invalid_action_id")

    def test_action_voucher_hmac_signature_and_tamper_detection(self) -> None:
        """Verifica geracao e validacao da assinatura HMAC-SHA256 e deteccao de adulteracao."""
        voucher_id = generate_uuid4()
        act_id = generate_action_id()
        tool_id = generate_tool_call_id()
        ts = datetime.now(UTC).isoformat()

        sig = generate_action_voucher_signature(
            voucher_id=voucher_id,
            action_id=act_id,
            tool_call_id=tool_id,
            status="APPROVED",
            timestamp=ts,
        )
        voucher = ActionVoucher(
            voucher_id=voucher_id,
            action_id=act_id,
            tool_call_id=tool_id,
            status="APPROVED",
            timestamp=ts,
            action_name="pedido_combustivel",
            details={"litros": 15000},
            signature=sig,
        )
        assert verify_action_voucher_signature(voucher) is True

        tampered = ActionVoucher(
            voucher_id=voucher_id,
            action_id=act_id,
            tool_call_id=tool_id,
            status="APPROVED",
            timestamp=ts,
            action_name="pedido_combustivel",
            details={"litros": 99999},
            signature="assinatura_forjada_invalida",
        )
        assert verify_action_voucher_signature(tampered) is False


class TestActionExecuteAndRollbackEndpoints:
    """Valida execucao transacional, idempotencia, RBAC, rollback e auditoria."""

    def test_execute_action_and_strict_idempotency(self, tmp_path: Path) -> None:
        """Garante emissao de ActionVoucher e retorno identico em reenvios do mesmo action_id."""
        mem = AuraSessionMemory(db_path=tmp_path / "sessions.db")
        journal = AuraCommandJournal(db_path=tmp_path / "journal.db")
        engine = AuraEngine(session_memory=mem)
        app = create_aura_app(engine=engine, command_journal=journal)
        client = TestClient(app)

        tool_id = generate_tool_call_id()
        act_id = generate_action_id()
        sess_id = f"sess_{uuid.uuid4()}"

        payload = {
            "session_id": sess_id,
            "tool_call_id": tool_id,
            "action_id": act_id,
            "action_name": "estancar_quebra",
            "action_type": "mutation",
            "payload": {"valor": 85.0, "turno": 1},
            "operator_id": "caixa_01",
            "operator_role": "caixa",
        }

        resp1 = client.post("/api/v1/aura/actions/execute", json=payload)
        assert resp1.status_code == 200
        v1 = resp1.json()
        assert v1["status"] == "APPROVED"
        assert v1["action_id"] == act_id
        assert verify_action_voucher_signature(ActionVoucher(**v1)) is True

        # Reenvio com o mesmo action_id e payload alterado deve devolver o voucher original imutavel
        payload_dup = dict(payload)
        payload_dup["payload"] = {"valor": 9999.0, "turno": 2}
        resp2 = client.post("/api/v1/aura/actions/execute", json=payload_dup)
        assert resp2.status_code == 200
        v2 = resp2.json()

        assert v2["voucher_id"] == v1["voucher_id"]
        assert v2["signature"] == v1["signature"]
        assert v2["details"]["valor"] == 85.0

        # Verifica injecao unica de mensagem role='tool' na sessao
        hist = mem.get_history(sess_id, limit=10)
        tool_msgs = [m for m in hist if m["role"] == "tool"]
        assert len(tool_msgs) == 1
        parsed = json.loads(tool_msgs[0]["content"])
        assert parsed["voucher_id"] == v1["voucher_id"]

    def test_rbac_governance_and_replay_attack_prevention(self, tmp_path: Path) -> None:
        """Verifica bloqueio HTTP 403 para perfis sem permissao mesmo em tentativa de replay."""
        mem = AuraSessionMemory(db_path=tmp_path / "sessions_rbac.db")
        journal = AuraCommandJournal(db_path=tmp_path / "journal_rbac.db")
        engine = AuraEngine(session_memory=mem)
        app = create_aura_app(engine=engine, command_journal=journal)
        client = TestClient(app)

        ok_f, _, _ = evaluate_action_permission("pedido_combustivel", "mutation", "frentista")
        assert ok_f is False
        ok_g, _, _ = evaluate_action_permission("pedido_combustivel", "mutation", "gerente")
        assert ok_g is True

        aid = generate_action_id()
        tid = generate_tool_call_id()
        sess_id = f"sess_{uuid.uuid4()}"

        # 1. Frentista bloqueado em mutacao de alto impacto
        resp_forbidden = client.post(
            "/api/v1/aura/actions/execute",
            json={
                "session_id": sess_id,
                "tool_call_id": tid,
                "action_id": aid,
                "action_name": "pedido_combustivel",
                "action_type": "mutation",
                "operator_id": "frentista_01",
                "operator_role": "frentista",
                "payload": {"litros": 15000},
            },
        )
        assert resp_forbidden.status_code == 403

        # 2. Gerente aprova a acao
        resp_ok = client.post(
            "/api/v1/aura/actions/execute",
            json={
                "session_id": sess_id,
                "tool_call_id": tid,
                "action_id": aid,
                "action_name": "pedido_combustivel",
                "action_type": "mutation",
                "operator_id": "gerente_01",
                "operator_role": "gerente",
                "payload": {"litros": 15000},
            },
        )
        assert resp_ok.status_code == 200

        # 3. Frentista tenta replay usando o mesmo action_id ja aprovado -> continua 403 Forbidden
        resp_replay = client.post(
            "/api/v1/aura/actions/execute",
            json={
                "session_id": sess_id,
                "tool_call_id": tid,
                "action_id": aid,
                "action_name": "pedido_combustivel",
                "action_type": "mutation",
                "operator_id": "frentista_02",
                "operator_role": "frentista",
                "payload": {"litros": 15000},
            },
        )
        assert resp_replay.status_code == 403

    def test_action_rollback_updates_voucher_journal_and_audit_log(self, tmp_path: Path) -> None:
        """Verifica que POST /api/v1/aura/actions/rollback estorna o voucher e atualiza o journal."""
        mem = AuraSessionMemory(db_path=tmp_path / "sessions_rb.db")
        journal = AuraCommandJournal(db_path=tmp_path / "journal_rb.db")
        engine = AuraEngine(session_memory=mem)
        app = create_aura_app(engine=engine, command_journal=journal)
        client = TestClient(app)

        aid = generate_action_id()
        tid = generate_tool_call_id()
        sess_id = f"sess_{uuid.uuid4()}"

        exec_resp = client.post(
            "/api/v1/aura/actions/execute",
            json={
                "session_id": sess_id,
                "tool_call_id": tid,
                "action_id": aid,
                "action_name": "pedido_combustivel",
                "action_type": "mutation",
                "operator_id": "gerente_01",
                "operator_role": "gerente",
                "payload": {"litros": 15000, "combustivel": "DIESEL S10"},
            },
        )
        assert exec_resp.status_code == 200

        rb_resp = client.post(
            "/api/v1/aura/actions/rollback",
            json={
                "action_id": aid,
                "session_id": sess_id,
                "tool_call_id": tid,
                "operator_id": "gerente_01",
                "operator_role": "gerente",
                "reason": "Cancelamento solicitado pela distribuidora",
            },
        )
        assert rb_resp.status_code == 200
        rb_data = rb_resp.json()
        assert rb_data["status"] == "ROLLED_BACK"
        assert rb_data["rolled_back"] is True
        assert rb_data["action_id"] == aid
        assert rb_data["journal_status"] == CommandJournalStatus.ROLLED_BACK.value

        # Verifica que o voucher em AuraSessionMemory foi atualizado para ROLLED_BACK com assinatura valida
        v_after = mem.get_action_voucher(aid)
        assert v_after is not None
        assert v_after.status == "ROLLED_BACK"
        assert verify_action_voucher_signature(v_after) is True

        # Verifica que o Command Journal tambem esta em ROLLED_BACK
        j_entry = journal.get_entry(f"voucher:{aid}:execute")
        assert j_entry is not None
        assert j_entry.status == CommandJournalStatus.ROLLED_BACK.value

        # Verifica trilha de auditoria via GET /api/v1/aura/audit/logs
        logs_resp = client.get(f"/api/v1/aura/audit/logs?action_id={aid}&status=ROLLED_BACK")
        assert logs_resp.status_code == 200
        logs_data = logs_resp.json()
        assert len(logs_data) == 1
        parsed_log = ActionAuditLogRecord(**logs_data[0])
        assert parsed_log.status == "ROLLED_BACK"
        journal.close()
