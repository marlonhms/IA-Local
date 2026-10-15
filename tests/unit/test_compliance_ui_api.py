"""
Suíte de Testes Unitários: Interface de Conformidade Legal, Opt-In do Lojista e Driver Shield v1.1.
Valida endpoints HTTP, schemas GenUI canônicos, execução de ferramentas no AuraEngine,
roteamento semântico de intenções e a regra inegociável de ZERO travessões.
Regra inegociável: ZERO travessões em todo o arquivo.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from config.settings import BASE_DIR
from core.aura_api import create_aura_app
from core.aura_engine import (
    AuraEngine,
    AuraSessionMemory,
    build_canonical_genui_envelope,
)
from core.compliance_manager import ComplianceManager
from core.schemas.genui import ComplianceStatusProps
from core.schemas.idempotency import generate_tool_call_id
from core.semantic_router import SemanticRouter


@pytest.fixture
def mock_engine() -> AuraEngine:
    """Fixture com AuraEngine isolada em memória."""
    mem = AuraSessionMemory(db_path=":memory:")
    comp_mgr = ComplianceManager(db_path=":memory:")
    return AuraEngine(
        tenant_id="tenant_ui_test",
        filial_id="posto_ui_01",
        session_memory=mem,
        compliance_manager=comp_mgr,
    )


@pytest.fixture
def client(mock_engine: AuraEngine) -> TestClient:
    """Fixture do TestClient FastAPI."""
    app = create_aura_app(mock_engine)
    return TestClient(app)


@pytest.mark.unit
class TestComplianceUIApi:
    """Testes dos endpoints e contratos de interface de conformidade."""

    def test_get_compliance_term_endpoint(self, client: TestClient) -> None:
        """Valida que GET /api/v1/aura/compliance/term retorna o documento oficial v1.1 e hash."""
        resp = client.get("/api/v1/aura/compliance/term")
        assert resp.status_code == 200
        data = resp.json()

        assert data["version"] == "1.1"
        assert "Termo de Interoperabilidade" in data["title"]
        assert len(data["hash_sha256"]) == 64
        assert len(data["content_markdown"]) > 500

        # Verifica fundamentação técnica e jurídica no texto markdown
        md = data["content_markdown"]
        assert "13.709/2018" in md
        assert "9.609/1998" in md
        assert "aura_service_ro" in md
        assert "statement_timeout" in md
        assert "lock_timeout" in md

    def test_get_compliance_status_endpoint(self, client: TestClient) -> None:
        """Valida que GET /api/v1/aura/compliance/status retorna a situação do posto."""
        resp = client.get("/api/v1/aura/compliance/status")
        assert resp.status_code == 200
        data = resp.json()

        assert "loja_cnpj" in data
        assert "compliant" in data
        assert "versao_termo" in data
        assert "garantia_leitura_exclusiva" in data
        assert data["garantia_leitura_exclusiva"] is True
        assert data["isolamento_aups"] is True

    def test_post_compliance_opt_in_endpoint(self, client: TestClient) -> None:
        """Valida o registro de opt-in formal do lojista via POST."""
        payload = {
            "loja_cnpj": "11.222.333/0001-44",
            "razao_social": "Auto Posto Alvorada Ltda",
            "assinado_por": "Diretor Financeiro",
            "metadata": {"origem": "painel_web_ui"},
        }
        resp = client.post("/api/v1/aura/compliance/opt-in", json=payload)
        assert resp.status_code == 200
        data = resp.json()

        assert data["sucesso"] is True
        assert data["status"] == "ok"
        assert data["opt_in"]["status"] == "active"
        assert data["opt_in"]["loja_cnpj"] == "11.222.333/0001-44"
        assert data["opt_in"]["razao_social"] == "Auto Posto Alvorada Ltda"
        assert data["opt_in"]["versao_termo"] == "1.1"

    async def test_compliance_status_tool_execution(self, mock_engine: AuraEngine) -> None:
        """Valida execução da ferramenta analítica compliance_status e envelope GenUI."""
        res = await mock_engine.execute_tool_direct("compliance_status", {})
        assert isinstance(res, dict)
        assert res.get("status") == "success"
        assert res.get("tool_name") == "compliance_status"
        data = res.get("data", {})
        assert data.get("garantia_leitura_exclusiva") is True
        assert data.get("isolamento_aups") is True

        # Valida construção do envelope canônico GenUI
        envelope = build_canonical_genui_envelope(
            intencao="compliance_status",
            tool_call_id=generate_tool_call_id(),
            resultado_bruto=data,
            executive_summary="Estabelecimento em total conformidade e blindado.",
        )
        assert envelope is not None
        assert envelope.component_name == "render_ComplianceStatusUI"
        assert envelope.client_component == "ComplianceStatusUI"

        # Valida que as propriedades atendem ao contrato canônico Pydantic
        props_dict = envelope.props or {}
        props_obj = ComplianceStatusProps.model_validate(props_dict)
        assert props_obj.versao_termo == "1.1"
        assert props_obj.garantia_leitura_exclusiva is True
        assert props_obj.driver_level_protection is True
        assert props_obj.statement_timeout_ms == 4000
        assert props_obj.lock_timeout_ms == 1000
        assert props_obj.role_banco == "aura_service_ro"
        assert len(props_obj.pilares_legais) >= 4
        assert len(envelope.actions) >= 2

    def test_semantic_router_compliance_intent_classification(self) -> None:
        """Valida que o SemanticRouter classifica corretamente as intenções de conformidade."""
        router = SemanticRouter()

        test_queries = [
            "qual o status de conformidade da aura?",
            "mostrar termo de interoperabilidade",
            "ver blindagem juridica e lgpd",
            "como funciona o driver shield do banco de dados?",
            "exibir termo de opt-in do posto",
        ]

        for q in test_queries:
            intent, _score, _meta = router.route(q)
            assert intent == "compliance_status", (
                f"Query '{q}' deveria ser classificada como 'compliance_status', mas retornou '{intent}'"
            )

    def test_zero_travessoes_in_ui_and_api_files(self) -> None:
        """
        Regra inegociável do projeto: ZERO TRAVESSÕES (em-dash e en-dash).
        Garante que nenhum arquivo da interface e da API de conformidade contenha travessões.
        """
        files_to_check = [
            BASE_DIR / "web" / "js" / "aura-compliance.js",
            BASE_DIR / "web" / "js" / "aura-genui-widgets.js",
            BASE_DIR / "web" / "js" / "aura-triggers.js",
            BASE_DIR / "web" / "js" / "aura-api.js",
            BASE_DIR / "web" / "index.html",
            BASE_DIR / "scripts" / "build_showcase_page.py",
            BASE_DIR / "tests" / "unit" / "test_compliance_ui_api.py",
        ]

        forbidden_chars = ["\u2014", "\u2013"]
        for f in files_to_check:
            assert f.exists(), f"Arquivo não encontrado: {f}"
            content = f.read_text(encoding="utf-8")
            for char in forbidden_chars:
                assert char not in content, (
                    f"Violação da regra ZERO TRAVESSÕES: caractere {char!r} detectado em {f.name}"
                )
