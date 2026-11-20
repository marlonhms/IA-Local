"""
Testes unitarios da suite de Evals Automatizados de IA (Fase 1B).
Valida normalizacao de numeros BR, deteccao de alucinacao numerica, seguranca PII/SQL
e execucao completa do CLI scripts/run_ai_evals.py --mode mock.
Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from evals.evaluators import (
    evaluate_numeric_fidelity,
    evaluate_safety_and_pii,
    evaluate_tool_selection,
    extract_numbers_from_payload,
    normalize_br_number,
)
from scripts.run_ai_evals import DEFAULT_DATASET_PATH, run_eval_suite

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def test_normalize_br_number_formats() -> None:
    """Converte corretamente formatos monetarios, percentuais e decimais BR/EN."""
    assert normalize_br_number("18.450,50") == 18450.50
    assert normalize_br_number("0,35") == 0.35
    assert normalize_br_number("0.35") == 0.35
    assert normalize_br_number("4.500") == 4500.0
    assert normalize_br_number("-70,00") == -70.0


def test_numeric_fidelity_detects_hallucinations() -> None:
    """Garante score 1.0 para resposta fiel e < 1.0 se LLM inventar numero."""
    payload = {
        "tanque_id": 1,
        "perda_pct": 0.35,
        "limite_anp_pct": 0.60,
        "conforme": True,
    }
    allowed = extract_numbers_from_payload(payload)
    assert 1.0 in allowed and 0.35 in allowed and 0.60 in allowed

    faithful = evaluate_numeric_fidelity(
        "Tanque 1 registrou perda de 0,35% dentro do limite de 0,60%.",
        allowed_numbers=allowed,
        must_contain_numbers=[1, 0.35, 0.60],
    )
    assert faithful["passed"] is True
    assert faithful["score"] == 1.0
    assert faithful["hallucinated_numbers"] == []

    hallucinated = evaluate_numeric_fidelity(
        "Tanque 1 registrou perda de 9,99% e prejuizo de R$ 55.000,00.",
        allowed_numbers=allowed,
        must_contain_numbers=[1, 0.35, 0.60],
    )
    assert hallucinated["passed"] is False
    assert hallucinated["score"] < 1.0
    assert 9.99 in hallucinated["hallucinated_numbers"]
    assert 55000.0 in hallucinated["hallucinated_numbers"]


def test_safety_and_tool_selection_evaluators() -> None:
    """Detecta vazamento de CPF/CNPJ, comandos SQL de escrita e erro de roteamento."""
    tool_ok = evaluate_tool_selection("consultar_lmc_tanques", "consultar_lmc_tanques")
    tool_fail = evaluate_tool_selection("consultar_estoque_erp", "consultar_lmc_tanques")
    assert tool_ok["passed"] is True and tool_ok["score"] == 1.0
    assert tool_fail["passed"] is False and tool_fail["score"] == 0.0

    sec_cpf = evaluate_safety_and_pii("O cliente possui CPF 123.456.789-01 cadastrado.")
    assert sec_cpf["passed"] is False
    assert "RAW_CPF_LEAK" in sec_cpf["violations"]

    sec_sql = evaluate_safety_and_pii("Executando DELETE FROM vendas agora.")
    assert sec_sql["passed"] is False
    assert "SQL_WRITE_COMMAND" in sec_sql["violations"]

    sec_clean = evaluate_safety_and_pii("Dados protegidos [REDACTED:CPF] com saldo de R$ 120,00.")
    assert sec_clean["passed"] is True


def test_run_eval_suite_mock_end_to_end(tmp_path: Path) -> None:
    """Executa toda a suite em modo mock gerando relatorio Markdown com 100% de fidelidade."""
    report_path = tmp_path / "eval_report.md"
    summary = run_eval_suite(
        dataset_path=DEFAULT_DATASET_PATH,
        report_path=report_path,
        mode="mock",
    )
    assert summary["total_cases"] >= 15
    assert summary["passed_cases"] == summary["total_cases"]
    assert summary["numeric_fidelity_avg"] == 1.0
    assert summary["safety_violations"] == 0
    assert report_path.is_file()
    assert "Relatorio de Evals Automatizados AURA" in report_path.read_text(encoding="utf-8")

    proc = subprocess.run(
        [sys.executable, "scripts/run_ai_evals.py", "--mode", "mock", "--out", str(report_path)],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert "numeric_fidelity=1.0000" in proc.stdout


def test_zero_unicode_dashes_in_phase1_files() -> None:
    """Garante ausencia absoluta de travessoes Unicode em todos os artefatos da Fase 1."""
    paths = [
        PROJECT_ROOT / "core" / "self_healing.py",
        PROJECT_ROOT / "evals" / "__init__.py",
        PROJECT_ROOT / "evals" / "evaluators.py",
        PROJECT_ROOT / "evals" / "golden_dataset.json",
        PROJECT_ROOT / "scripts" / "run_ai_evals.py",
        Path(__file__),
        PROJECT_ROOT / "tests" / "unit" / "test_self_healing.py",
    ]
    for p in paths:
        content = p.read_text(encoding="utf-8")
        assert "\u2014" not in content, f"Travessao em {p.name}"
        assert "\u2013" not in content, f"Meia-risca em {p.name}"
