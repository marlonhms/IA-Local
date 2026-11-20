"""
Pacote de Evals Automatizados de IA da AURA (Fase 1B - Roadmap Next-Gen).
Avaliadores deterministicos em Python para fidelidade numerica, selecao de tools,
seguranca LGPD/SQL, latencia e custo de tokens.
Zero travessoes em todo o arquivo.
"""

from evals.evaluators import (
    evaluate_case,
    evaluate_latency_and_cost,
    evaluate_numeric_fidelity,
    evaluate_safety_and_pii,
    evaluate_tool_selection,
    extract_numbers_from_payload,
    extract_numbers_from_text,
    normalize_br_number,
)

__all__ = [
    "evaluate_case",
    "evaluate_latency_and_cost",
    "evaluate_numeric_fidelity",
    "evaluate_safety_and_pii",
    "evaluate_tool_selection",
    "extract_numbers_from_payload",
    "extract_numbers_from_text",
    "normalize_br_number",
]
