"""
Suite de testes unitarios para a Arquitetura Frontend TypeScript, Bundler Vite
e Alinhamento 1:1 de Contratos Estaticos com os Schemas Pydantic v2 (P2-6).
Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from pydantic import BaseModel

from core.schemas.compliance import (
    ComplianceOptInStatus,
    ComplianceVerificationResult,
)
from core.schemas.genui import (
    ActionAuditLogRecord,
    ActionExecuteRequest,
    ActionVoucher,
    ActionableDirectivePayload,
    BasketUpsellStrategyProps,
    BenchmarkComparisonProps,
    ComplianceStatusProps,
    ExecutiveDecisionProps,
    ExecutiveExceptionCard,
    FinancialLeakAuditProps,
    GenUIActionOption,
    GenUIEnvelope,
    MarginAnalysisProps,
    PredictiveScenarioProps,
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
FRONTEND_DIR = BASE_DIR / "web-frontend"


def _extract_ts_interfaces(ts_source: str) -> dict[str, set[str]]:
    """Extrai o mapa de interfaces TypeScript e seus respectivos nomes de propriedades."""
    interfaces: dict[str, set[str]] = {}
    pattern = re.compile(
        r"export\s+interface\s+([A-Za-z0-9_]+)(?:<[^\{]+>)?\s*\{([^}]+(?:\{[^}]*\}[^}]*)*)\}",
        re.MULTILINE | re.DOTALL,
    )
    prop_pattern = re.compile(r"^\s*([a-zA-Z_][a-zA-Z0-9_]*)\??\s*:", re.MULTILINE)

    for match in pattern.finditer(ts_source):
        iface_name = match.group(1)
        body = match.group(2)
        props = {m.group(1) for m in prop_pattern.finditer(body)}
        interfaces[iface_name] = props
    return interfaces


def test_package_json_and_tsconfig_strict_configuration() -> None:
    """Valida a existencia e configuracao estrita de package.json, tsconfig.json e vite.config.ts."""
    pkg_path = FRONTEND_DIR / "package.json"
    tsconfig_path = FRONTEND_DIR / "tsconfig.json"
    vite_path = FRONTEND_DIR / "vite.config.ts"

    assert pkg_path.exists(), "web-frontend/package.json deve existir"
    assert tsconfig_path.exists(), "web-frontend/tsconfig.json deve existir"
    assert vite_path.exists(), "web-frontend/vite.config.ts deve existir"

    pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
    assert "scripts" in pkg
    assert "dev" in pkg["scripts"]
    assert "build" in pkg["scripts"]
    assert "typecheck" in pkg["scripts"]
    assert "typescript" in pkg.get("devDependencies", {})
    assert "vite" in pkg.get("devDependencies", {})

    tsconfig = json.loads(tsconfig_path.read_text(encoding="utf-8"))
    compiler_opts = tsconfig.get("compilerOptions", {})
    assert compiler_opts.get("strict") is True
    assert compiler_opts.get("noImplicitAny") is True
    assert compiler_opts.get("target") == "ES2022"

    vite_src = vite_path.read_text(encoding="utf-8")
    assert "../web/dist" in vite_src
    assert "http://127.0.0.1:8000" in vite_src
    assert "treeshake" in vite_src


def test_pydantic_to_typescript_contract_parity() -> None:
    """
    Verifica por introspeccao que todos os campos dos schemas Pydantic v2 da AURA
    estao fielmente declarados nas interfaces TypeScript de aura-contracts.ts.
    """
    contracts_path = FRONTEND_DIR / "src" / "types" / "aura-contracts.ts"
    assert contracts_path.exists(), "aura-contracts.ts deve existir"

    ts_source = contracts_path.read_text(encoding="utf-8")
    ts_interfaces = _extract_ts_interfaces(ts_source)

    required_custom_interfaces = [
        "AuraMessage",
        "GenUIEvent",
        "ShiftReconciliationProps",
        "TankRunOutPredictionProps",
        "TelemetrySLISnapshot",
        "LiveSecurityTelemetry",
    ]
    for req_iface in required_custom_interfaces:
        assert req_iface in ts_interfaces, f"Interface TypeScript {req_iface} ausente"

    pydantic_models: dict[str, type[BaseModel]] = {
        "GenUIActionOption": GenUIActionOption,
        "GenUIEnvelope": GenUIEnvelope,
        "ActionExecuteRequest": ActionExecuteRequest,
        "ActionVoucher": ActionVoucher,
        "ActionAuditLogRecord": ActionAuditLogRecord,
        "ExecutiveDecisionProps": ExecutiveDecisionProps,
        "ExecutiveExceptionCard": ExecutiveExceptionCard,
        "ActionableDirectivePayload": ActionableDirectivePayload,
        "MarginAnalysisProps": MarginAnalysisProps,
        "PredictiveScenarioProps": PredictiveScenarioProps,
        "BenchmarkComparisonProps": BenchmarkComparisonProps,
        "FinancialLeakAuditProps": FinancialLeakAuditProps,
        "BasketUpsellStrategyProps": BasketUpsellStrategyProps,
        "ComplianceOptInStatus": ComplianceOptInStatus,
        "ComplianceVerificationResult": ComplianceVerificationResult,
        "ComplianceStatusProps": ComplianceStatusProps,
    }

    for model_name, model_cls in pydantic_models.items():
        assert model_name in ts_interfaces, (
            f"Interface TypeScript '{model_name}' nao encontrada em aura-contracts.ts"
        )
        ts_fields = ts_interfaces[model_name]
        pydantic_fields = set(model_cls.model_fields.keys())
        missing_in_ts = pydantic_fields - ts_fields
        assert not missing_in_ts, (
            f"Campos do schema Pydantic {model_name} ausentes em TypeScript: {missing_in_ts}"
        )


def test_aura_client_and_sdk_entrypoint() -> None:
    """Valida a implementacao do cliente tipado AuraApiClient e do ponto de entrada main.ts."""
    client_path = FRONTEND_DIR / "src" / "api" / "aura-client.ts"
    main_path = FRONTEND_DIR / "src" / "main.ts"

    assert client_path.exists(), "aura-client.ts deve existir"
    assert main_path.exists(), "main.ts deve existir"

    client_src = client_path.read_text(encoding="utf-8")
    assert "export class AuraApiClient" in client_src
    assert "/api/v1/aura/actions/execute" in client_src
    assert "/api/v1/aura/compliance/status" in client_src
    assert "/api/v1/aura/chat/stream" in client_src
    assert "/api/v1/cockpit/zero-click-feed" in client_src
    assert "/api/v1/aura/security/telemetry" in client_src
    assert "/metrics" in client_src
    assert "getZeroClickFeed" in client_src
    assert "getLiveSecurityTelemetry" in client_src
    assert "isValidGenUIEnvelope" in client_src
    assert "isValidActionVoucher" in client_src

    main_src = main_path.read_text(encoding="utf-8")
    assert "AuraFrontendSDK" in main_src
    assert "window.AuraSDK" in main_src


def test_zero_travessoes_in_p2_6_files() -> None:
    """Garante ausencia total de travessoes em todos os arquivos de P2-6."""
    files_to_check = [
        FRONTEND_DIR / "package.json",
        FRONTEND_DIR / "tsconfig.json",
        FRONTEND_DIR / "vite.config.ts",
        FRONTEND_DIR / "src" / "types" / "aura-contracts.ts",
        FRONTEND_DIR / "src" / "api" / "aura-client.ts",
        FRONTEND_DIR / "src" / "main.ts",
        BASE_DIR / "tests" / "unit" / "test_frontend_typescript_contracts.py",
    ]
    for path in files_to_check:
        content = path.read_text(encoding="utf-8")
        assert "\u2014" not in content, f"Travessao (em-dash) encontrado em {path.name}"
        assert "\u2013" not in content, f"Travessao (en-dash) encontrado em {path.name}"
