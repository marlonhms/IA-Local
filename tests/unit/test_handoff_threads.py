"""
Testes Unitarios das Sessoes Dedicadas de Retorno WhatsApp (Dual-Sync + Thread Isolation)
e Auditoria Fiscal XML/Quick-Action.

Zero travessoes Unicode em todo o arquivo.
"""

from __future__ import annotations

import time
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

import core.webhooks as webhooks_mod
from core.aura_api import create_aura_app
from core.command_journal import (
    AuraCommandJournal,
    format_brazil_phone_display,
    is_generic_or_numeric_name,
    normalize_whatsapp_phone,
    phone_match_key,
    reset_command_journal,
    set_command_journal,
    whatsapp_jid_candidates,
)
from core.tools import PostoTools
from core.webhooks import (
    WebhookDispatchResult,
    fetch_evolution_contact_profile,
    sync_inbound_messages_from_evolution,
)


@pytest.fixture
def isolated_journal():
    journal = AuraCommandJournal(db_path=":memory:")
    set_command_journal(journal)
    try:
        yield journal
    finally:
        journal.close()
        reset_command_journal()


@pytest.fixture
def partner_client(isolated_journal: AuraCommandJournal) -> TestClient:
    app = create_aura_app()
    return TestClient(app)


def _auth_headers(station_id: str = "posto_01") -> dict[str, str]:
    return {
        "X-Partner-Key": "aura-partner-default-key",
        "X-Station-ID": station_id,
    }


def test_brazil_phone_match_key_and_jid_candidates():
    with_nine = "5527999227721"
    without_nine = "552799227721@s.whatsapp.net"

    assert normalize_whatsapp_phone("27999227721") == with_nine
    assert normalize_whatsapp_phone(without_nine) == "552799227721"
    assert phone_match_key(with_nine) == phone_match_key(without_nine) == "2799227721"

    candidates = whatsapp_jid_candidates(with_nine)
    assert "5527999227721@s.whatsapp.net" in candidates
    assert "552799227721@s.whatsapp.net" in candidates


def test_handoff_outbound_creation_and_ninth_digit_correlation(
    partner_client: TestClient,
    isolated_journal: AuraCommandJournal,
    monkeypatch: pytest.MonkeyPatch,
):
    async def fake_send_text(phone: str, message_text: str, **kwargs: Any):
        return WebhookDispatchResult(
            success=True,
            service="evolution",
            target_url="http://evo.local/sendText",
            status_code=200,
            outbox_message_id="ob_txt_1",
        )

    async def fake_send_media(phone: str, media_base64: str, **kwargs: Any):
        return WebhookDispatchResult(
            success=True,
            service="evolution",
            target_url="http://evo.local/sendMedia",
            status_code=200,
            outbox_message_id="ob_med_1",
        )

    monkeypatch.setattr(webhooks_mod, "dispatch_evolution_message", fake_send_text)
    monkeypatch.setattr(webhooks_mod, "dispatch_evolution_media", fake_send_media)

    resp = partner_client.post(
        "/api/v1/partner/handoff",
        headers=_auth_headers(),
        json={
            "action_id": "handoff_contador_nf55",
            "phone": "27999227721",
            "contact_name": "Carlos Silva",
            "role_label": "Contador",
            "initial_message": "Segue auditoria da NF 901 com divergencia de ICMS.",
            "session_handoff_context": "Auditoria NF 901",
            "attachment_base64": "A" * 80,
            "station_id": "posto_01",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["session_id"] == "wa_handoff_5527999227721"
    assert body["thread_phone"] == "5527999227721"
    assert body["media_sent"] is True

    # Resposta passiva chegando sem o nono digito (12 digitos) deve cair na mesma thread
    reply_resp = partner_client.post(
        "/api/v1/partner/handoff-reply",
        headers=_auth_headers(),
        json={
            "phone": "552799227721@s.whatsapp.net",
            "message_text": "Recebi a nota, ja estou corrigindo no SPED!",
            "sender_name": "Carlos Contador",
            "external_msg_id": "MSG_EXT_999",
        },
    )
    assert reply_resp.status_code == 200
    rbody = reply_resp.json()
    assert rbody["accepted"] is True
    assert rbody["ingested"] is True
    assert rbody["session_id"] == "wa_handoff_5527999227721"
    assert rbody["thread_phone"] == "5527999227721"

    # Mesma mensagem repetida nao duplica
    dup_resp = partner_client.post(
        "/api/v1/partner/handoff-reply",
        headers=_auth_headers(),
        json={
            "phone": "5527999227721",
            "message_text": "Recebi a nota, ja estou corrigindo no SPED!",
            "external_msg_id": "MSG_EXT_999",
        },
    )
    assert dup_resp.status_code == 200
    assert dup_resp.json()["ingested"] is False

    threads = isolated_journal.list_handoff_threads()
    assert len(threads) == 1
    assert threads[0]["unread_count"] == 1
    assert threads[0]["total_messages"] == 2
    assert threads[0]["role_label"] == "Contador"


def test_handoff_reply_blocks_untracked_numbers_and_supports_mark_read(
    partner_client: TestClient,
    isolated_journal: AuraCommandJournal,
):
    blocked = partner_client.post(
        "/api/v1/partner/handoff-reply",
        headers=_auth_headers(),
        json={
            "phone": "5511988887777",
            "message_text": "Oi, bom dia!",
        },
    )
    assert blocked.status_code == 200
    assert blocked.json()["accepted"] is False
    assert blocked.json()["reason"] == "no_active_handoff"

    isolated_journal.record_handoff_message(
        thread_phone="5527988112233",
        direction="OUTBOUND",
        sender_label="Gestor AURA",
        message_text="Favor confirmar descarga do diesel S10.",
        contact_name="Marcos Gerente",
        role_label="Gerente",
        epoch_ts=int(time.time()),
    )

    # Formato webhook MESSAGES_UPSERT da Evolution API
    evo_push = partner_client.post(
        "/api/v1/partner/handoff-reply",
        headers=_auth_headers(),
        json={
            "event": "messages.upsert",
            "data": {
                "key": {
                    "id": "EVO_MSG_001",
                    "fromMe": False,
                    "remoteJid": "5527988112233@s.whatsapp.net",
                },
                "pushName": "Marcos Gerente",
                "message": {"conversation": "Tanque 02 descarregado com 15.000L."},
                "messageTimestamp": int(time.time()),
            },
        },
    )
    assert evo_push.status_code == 200
    assert evo_push.json()["accepted"] is True

    listing = partner_client.get(
        "/api/v1/partner/handoffs?sync_evolution=false",
        headers=_auth_headers(),
    )
    assert listing.status_code == 200
    data = listing.json()
    assert data["total_unread"] == 1
    assert data["threads"][0]["unread_count"] == 1

    read_resp = partner_client.post(
        "/api/v1/partner/handoffs/wa_handoff_5527988112233/read",
        headers=_auth_headers(),
    )
    assert read_resp.status_code == 200
    assert read_resp.json()["marked_read"] == 1

    listing_after = partner_client.get(
        "/api/v1/partner/handoffs?sync_evolution=false",
        headers=_auth_headers(),
    ).json()
    assert listing_after["total_unread"] == 0
    assert listing_after["threads"][0]["unread_count"] == 0


@pytest.mark.asyncio
async def test_evolution_find_messages_sync_with_strict_temporal_filter(
    isolated_journal: AuraCommandJournal,
    monkeypatch: pytest.MonkeyPatch,
):
    now_epoch = int(time.time())
    isolated_journal.record_handoff_message(
        thread_phone="5527999227721",
        direction="OUTBOUND",
        sender_label="Gestor AURA",
        message_text="Envio NF 123 para conferencia.",
        contact_name="Contador",
        role_label="Contador",
        epoch_ts=now_epoch,
    )

    records = [
        # Antiga (antes do handoff) -> deve ser ignorada
        {
            "key": {"id": "OLD_MSG", "fromMe": False, "remoteJid": "5527999227721@s.whatsapp.net"},
            "pushName": "Contador",
            "message": {"conversation": "Mensagem antiga de ontem"},
            "messageTimestamp": now_epoch - 3600,
        },
        # Enviada por nos mesmos -> deve ser ignorada
        {
            "key": {"id": "SELF_MSG", "fromMe": True, "remoteJid": "5527999227721@s.whatsapp.net"},
            "pushName": "Posto",
            "message": {"conversation": "Eco meu"},
            "messageTimestamp": now_epoch + 10,
        },
        # Resposta valida posterior ao handoff -> deve entrar!
        {
            "key": {"id": "VALID_REPLY_1", "fromMe": False, "remoteJid": "5527999227721@s.whatsapp.net"},
            "pushName": "Contador",
            "message": {"extendedTextMessage": {"text": "Ajustado CFOP para 1652, podem lancar!"}},
            "messageTimestamp": now_epoch + 25,
        },
    ]

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/chat/findMessages/webposto-n3"):
            body = request.content.decode("utf-8")
            if "5527999227721@s.whatsapp.net" in body:
                return httpx.Response(200, json={"messages": {"total": len(records), "records": records}})
            return httpx.Response(200, json={"messages": {"total": 0, "records": []}})
        return httpx.Response(404)

    monkeypatch.setattr(webhooks_mod, "EVOLUTION_API_URL", "http://mock-evo:8080")
    monkeypatch.setattr(webhooks_mod, "EVOLUTION_INSTANCE", "webposto-n3")
    monkeypatch.setattr(webhooks_mod, "_last_evolution_sync_ts", 0.0)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        sync_res = await sync_inbound_messages_from_evolution(
            isolated_journal,
            force=True,
            http_client=client,
        )

    assert sync_res["synced"] is True
    assert sync_res["ingested"] == 1

    threads = isolated_journal.list_handoff_threads()
    assert len(threads) == 1
    assert threads[0]["unread_count"] == 1
    texts = [m["message_text"] for m in threads[0]["messages"]]
    assert "Mensagem antiga de ontem" not in texts
    assert "Eco meu" not in texts
    assert "Ajustado CFOP para 1652, podem lancar!" in texts


def test_quick_action_fiscal_audit_persists_structured_metadata(
    partner_client: TestClient,
    isolated_journal: AuraCommandJournal,
):
    resp = partner_client.post(
        "/api/v1/partner/quick-actions",
        headers=_auth_headers(),
        json={
            "action_type": "PENDENCIA_FISCAL_ENTRADA",
            "option_key": "1",
            "voucher_id": "vch_fiscal_001",
            "parameters": {
                "station_id": "posto_01",
                "chave_acesso": "32250311222333000144550010000009011234567890",
                "numero_nf": "901",
                "resumo_divergencia": "CST 60 informado em Diesel S10 em vez de CST 61",
                "fornecedor": "Distribuidora Sul LTDA",
            },
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "COMPLETED"
    assert body["fiscal_audit"]["numero_nf"] == "901"

    entry = isolated_journal.get_entry_by_action_id("vch_fiscal_001")
    assert entry is not None
    assert entry.result_payload is not None
    assert entry.result_payload["fiscal_audit"]["fornecedor"] == "Distribuidora Sul LTDA"


def test_tools_auditar_documento_xml_with_prefix_prompt():
    tools = PostoTools()
    prompt_with_xml = (
        "Audite este arquivo XML oficial:\n\n"
        "<NFe><infNFe Id=\"NFe32250311222333000144550010000009011234567890\" versao=\"4.00\">"
        "<ide><cUF>32</cUF><nNF>901</nNF><mod>55</mod><idDest>1</idDest><indFinal>0</indFinal></ide>"
        "<emit><CNPJ>11222333000144</CNPJ><CRT>3</CRT><enderEmit><UF>ES</UF></enderEmit></emit>"
        "<dest><CNPJ>44555666000177</CNPJ><indIEDest>1</indIEDest><enderDest><UF>ES</UF></enderDest></dest>"
        "<det nItem=\"1\"><prod><xProd>OLEO DIESEL B S10</xProd><NCM>27101921</NCM><CFOP>5655</CFOP><vProd>1000.00</vProd></prod></det>"
        "<total><ICMSTot><vProd>1000.00</vProd><vNF>1000.00</vNF></ICMSTot></total>"
        "</infNFe></NFe>"
    )
    res = tools.auditar_documento_ou_chave_fiscal(prompt_with_xml)
    assert res["status"] == "sucesso"
    assert res["tipo"] == "xml_documento"
    assert res["resultado"]["modelo"] == "55"


def test_handoff_reply_accepts_evolution_lid_with_remote_jid_alt(
    partner_client: TestClient,
    isolated_journal: AuraCommandJournal,
):
    isolated_journal.record_handoff_message(
        thread_phone="5527992277217",
        direction="OUTBOUND",
        sender_label="Gestor AURA",
        message_text="Envio XML para conferencia.",
        contact_name="Contador",
        role_label="Contador",
        epoch_ts=int(time.time()),
    )

    lid_push = partner_client.post(
        "/api/v1/partner/handoff-reply",
        headers=_auth_headers(),
        json={
            "event": "messages.upsert",
            "data": {
                "key": {
                    "id": "EVO_LID_MSG_001",
                    "fromMe": False,
                    "remoteJid": "193256348495933@lid",
                    "remoteJidAlt": "5527992277217@s.whatsapp.net",
                    "addressingMode": "lid",
                },
                "pushName": "Contador",
                "message": {"conversation": "ok"},
                "messageTimestamp": int(time.time()) + 5,
            },
        },
    )
    assert lid_push.status_code == 200
    body = lid_push.json()
    assert body["accepted"] is True
    assert body["ingested"] is True

    listing = partner_client.get(
        "/api/v1/partner/handoffs?sync_evolution=false",
        headers=_auth_headers(),
    ).json()
    assert listing["total_unread"] == 1
    assert listing["threads"][0]["messages"][-1]["message_text"] == "ok"


@pytest.mark.asyncio
async def test_evolution_find_messages_sync_queries_remote_jid_alt_for_lid_replies(
    isolated_journal: AuraCommandJournal,
    monkeypatch: pytest.MonkeyPatch,
):
    import json

    now_epoch = int(time.time())
    isolated_journal.record_handoff_message(
        thread_phone="5527992277217",
        direction="OUTBOUND",
        sender_label="Gestor AURA",
        message_text="Favor confirmar lancamento.",
        contact_name="Contador",
        role_label="Contador",
        epoch_ts=now_epoch,
    )

    alt_records = [
        {
            "key": {
                "id": "AC5DF614A46460084D8B630CE22D3878",
                "fromMe": False,
                "remoteJid": "193256348495933@lid",
                "remoteJidAlt": "5527992277217@s.whatsapp.net",
                "addressingMode": "lid",
            },
            "pushName": "Contador",
            "message": {"conversation": "ok"},
            "messageTimestamp": now_epoch + 21,
        },
        {
            "key": {
                "id": "AC60DA21E5C08AE26E59F5B7D0EB42FC",
                "fromMe": False,
                "remoteJid": "193256348495933@lid",
                "remoteJidAlt": "5527992277217@s.whatsapp.net",
                "addressingMode": "lid",
            },
            "pushName": "Contador",
            "message": {"conversation": "obrigado"},
            "messageTimestamp": now_epoch + 60,
        },
        {
            "key": {
                "id": "OTHER_CONTACT_MSG",
                "fromMe": False,
                "remoteJid": "999999999999999@lid",
                "remoteJidAlt": "5511999998888@s.whatsapp.net",
                "addressingMode": "lid",
            },
            "pushName": "Outro",
            "message": {"conversation": "nao deve entrar"},
            "messageTimestamp": now_epoch + 65,
        },
    ]

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/chat/findMessages/webposto-n3"):
            payload = json.loads(request.content.decode("utf-8"))
            key_filter = (payload.get("where") or {}).get("key") or {}
            if key_filter.get("remoteJidAlt") == "5527992277217@s.whatsapp.net":
                return httpx.Response(200, json={"messages": {"total": len(alt_records), "records": alt_records}})
            return httpx.Response(200, json={"messages": {"total": 0, "records": []}})
        return httpx.Response(404)

    monkeypatch.setattr(webhooks_mod, "EVOLUTION_API_URL", "http://mock-evo:8080")
    monkeypatch.setattr(webhooks_mod, "EVOLUTION_INSTANCE", "webposto-n3")
    monkeypatch.setattr(webhooks_mod, "_last_evolution_sync_ts", 0.0)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        sync_res = await sync_inbound_messages_from_evolution(
            isolated_journal,
            force=True,
            http_client=client,
        )

    assert sync_res["synced"] is True
    assert sync_res["ingested"] == 2
    threads = isolated_journal.list_handoff_threads()
    assert len(threads) == 1
    assert threads[0]["unread_count"] == 2
    texts = [m["message_text"] for m in threads[0]["messages"]]
    assert "ok" in texts
    assert "obrigado" in texts
    assert "nao deve entrar" not in texts


@pytest.mark.asyncio
async def test_evolution_contact_identity_enrichment_and_phone_formatting(
    isolated_journal: AuraCommandJournal,
    monkeypatch: pytest.MonkeyPatch,
):
    assert format_brazil_phone_display("5527992277217") == "+55 (27) 99227-7217"
    assert format_brazil_phone_display("552732277217") == "+55 (27) 3227-7217"
    assert is_generic_or_numeric_name("Contador", "5527992277217", "Contador") is True
    assert is_generic_or_numeric_name("5527992277217", "5527992277217", "WhatsApp") is True
    assert is_generic_or_numeric_name("Marlon Henrique", "5527992277217", "Contador") is False

    now_epoch = int(time.time())
    isolated_journal.record_handoff_message(
        thread_phone="5527992277217",
        direction="OUTBOUND",
        sender_label="Gestor AURA",
        message_text="Envio relatorio SEFAZ.",
        contact_name="Contador",
        role_label="Contador",
        epoch_ts=now_epoch,
    )

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/chat/findContacts/webposto-n3"):
            return httpx.Response(
                200,
                json=[
                    {
                        "remoteJid": "5527992277217@s.whatsapp.net",
                        "pushName": "Marlon Henrique",
                        "profilePicUrl": "https://cdn.example.com/marlon.jpg",
                    }
                ],
            )
        if request.url.path.endswith("/chat/findMessages/webposto-n3"):
            return httpx.Response(200, json={"messages": {"total": 0, "records": []}})
        return httpx.Response(404)

    monkeypatch.setattr(webhooks_mod, "EVOLUTION_API_URL", "http://mock-evo:8080")
    monkeypatch.setattr(webhooks_mod, "EVOLUTION_INSTANCE", "webposto-n3")
    monkeypatch.setattr(webhooks_mod, "_last_evolution_sync_ts", 0.0)
    webhooks_mod._evolution_contact_cache.clear()

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        prof = await fetch_evolution_contact_profile("5527992277217", http_client=client, force=True)
        assert prof["push_name"] == "Marlon Henrique"
        assert prof["profile_pic_url"] == "https://cdn.example.com/marlon.jpg"

        await sync_inbound_messages_from_evolution(isolated_journal, force=True, http_client=client)

    threads = isolated_journal.list_handoff_threads()
    assert len(threads) == 1
    assert threads[0]["contact_name"] == "Marlon Henrique"
    assert threads[0]["role_label"] == "Contador"
    assert threads[0]["formatted_phone"] == "+55 (27) 99227-7217"


@pytest.mark.asyncio
async def test_evolution_ack_progression_sent_delivered_read_and_replied(
    isolated_journal: AuraCommandJournal,
    monkeypatch: pytest.MonkeyPatch,
):
    now_epoch = int(time.time())
    isolated_journal.record_handoff_message(
        thread_phone="5527992277217",
        direction="OUTBOUND",
        sender_label="Gestor AURA",
        message_text="Gatilho SEFAZ enviado.",
        contact_name="Marlon Henrique",
        role_label="Contador",
        epoch_ts=now_epoch,
    )

    assert isolated_journal.list_handoff_threads()[0]["delivery_status"] == "SENT"

    stage = {"records": []}

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/chat/findMessages/webposto-n3"):
            return httpx.Response(200, json={"messages": {"total": len(stage["records"]), "records": stage["records"]}})
        if request.url.path.endswith("/chat/findContacts/webposto-n3"):
            return httpx.Response(200, json=[])
        return httpx.Response(404)

    monkeypatch.setattr(webhooks_mod, "EVOLUTION_API_URL", "http://mock-evo:8080")
    monkeypatch.setattr(webhooks_mod, "EVOLUTION_INSTANCE", "webposto-n3")
    webhooks_mod._evolution_contact_cache.clear()

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        # 1. Entregue no aparelho
        stage["records"] = [
            {
                "key": {"id": "OUT_1", "fromMe": True, "remoteJid": "5527992277217@s.whatsapp.net"},
                "messageTimestamp": now_epoch + 1,
                "MessageUpdate": [{"status": "SERVER_ACK"}, {"status": "DELIVERY_ACK"}],
            }
        ]
        await sync_inbound_messages_from_evolution(isolated_journal, force=True, http_client=client)
        assert isolated_journal.list_handoff_threads()[0]["delivery_status"] == "DELIVERED"

        # 2. Visualizado pelo destinatario no WhatsApp
        stage["records"] = [
            {
                "key": {"id": "OUT_1", "fromMe": True, "remoteJid": "5527992277217@s.whatsapp.net"},
                "messageTimestamp": now_epoch + 1,
                "MessageUpdate": [{"status": "DELIVERY_ACK"}, {"status": "READ"}],
            }
        ]
        await sync_inbound_messages_from_evolution(isolated_journal, force=True, http_client=client)
        th_read = isolated_journal.list_handoff_threads()[0]
        assert th_read["delivery_status"] == "READ"
        assert "Visualizado" in th_read["delivery_status_label"]

        # 3. Retorno recebido -> promove para REPLIED
        stage["records"].append(
            {
                "key": {"id": "IN_1", "fromMe": False, "remoteJid": "5527992277217@s.whatsapp.net"},
                "pushName": "Marlon Henrique",
                "message": {"conversation": "Recebido e ajustado"},
                "messageTimestamp": now_epoch + 10,
            }
        )
        await sync_inbound_messages_from_evolution(isolated_journal, force=True, http_client=client)
        th_replied = isolated_journal.list_handoff_threads()[0]
        assert th_replied["delivery_status"] == "REPLIED"
        assert th_replied["unread_count"] == 1



