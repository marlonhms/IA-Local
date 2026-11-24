"""Cartucho Vertical de Tools para Postos de Combustiveis (Carbon Core P1.1).

Isola o despacho de intencoes exclusivas do nicho de combustiveis
(lmc_anp, auditar_conformidade_lmc_anp, vazao_bicos, desempenho_pista_frentistas,
benchmark_anp, benchmark_comparativo, custo_estoque_macro) fora do nucleo agnostico,
mantendo PostoTools como fachada retrocompativel.
Zero travessoes em todo o modulo.
"""

from __future__ import annotations

import logging
from typing import Any

from core.adapters.erp.base import BaseERPAdapter
from core.packs.registry import (
    DomainToolRegistry,
    ToolExecutionContext,
    ToolExecutionResult,
)

logger = logging.getLogger("FuelConvenienceCartridge")

PACK_ID = "fuel_convenience"

FUEL_ONLY_INTENTS: tuple[str, ...] = (
    "lmc_anp",
    "lmc_compliance",
    "lmc",
    "auditar_conformidade_lmc_anp",
    "vazao_bicos",
    "desempenho_pista_frentistas",
    "benchmark_anp",
    "benchmark_comparativo",
    "comparativo_turnos",
    "custo_estoque_macro",
    "analisar_custo_estoque_macroeconomico",
)


class FuelConvenienceTools:
    """Encapsula as ferramentas exclusivas da vertical fuel_convenience."""

    def __init__(
        self,
        erp_adapter: BaseERPAdapter,
        tools_facade: Any = None,
    ) -> None:
        self.erp_adapter = erp_adapter
        self._tools_facade = tools_facade

    @property
    def facade(self) -> Any:
        if self._tools_facade is None:
            from core.tools import PostoTools

            self._tools_facade = PostoTools(erp_adapter=self.erp_adapter)
        return self._tools_facade

    def auditar_lmc_anp(self, data: str | None = None, combustivel: str | None = None) -> dict[str, Any]:
        """Executa auditoria regulamentar LMC ANP (Portaria 26/1992)."""
        return self.facade.auditar_conformidade_lmc_anp(data=data, combustivel=combustivel)

    def auditar_vazao_bicos(
        self,
        data: str | None = None,
        turno: str | None = None,
        frentista: str | None = None,
        bico: str | None = None,
    ) -> dict[str, Any]:
        """Executa auditoria de vazao de bicos, bombas e desempenho de pista."""
        return self.facade.auditar_desempenho_pista_frentistas(
            data=data,
            turno=turno,
            frentista=frentista,
            bico=bico,
        )

    def comparar_benchmark_anp(
        self,
        data: str | None = None,
        turno: str | None = None,
        produto: str | None = None,
    ) -> dict[str, Any]:
        """Executa comparativo de precos e performance contra benchmark ANP."""
        return self.facade.comparar_benchmark_concorrencia(
            data=data,
            turno=turno,
            produto=produto,
        )

    def analisar_custo_estoque_macro(self, produto: str = "GASOLINA COMUM") -> dict[str, Any]:
        """Executa calculo de custo de carregamento Selic e pauta fiscal CONFAZ."""
        return self.facade.analisar_custo_estoque_macroeconomico(produto=produto)


def _extract_fuel_query_helpers(query: str) -> tuple[str | None, str | None, str | None]:
    """Extrai (data, turno, combustivel) reutilizando parsers deterministicos do engine."""
    try:
        from core.aura_engine import extrair_combustivel, extrair_data_turno

        data_p, turno_p = extrair_data_turno(query)
        comb_p = extrair_combustivel(query)
        return data_p, turno_p, comb_p
    except Exception:
        return None, None, None


def _handle_lmc_anp(ctx: ToolExecutionContext) -> ToolExecutionResult:
    data_p, _, comb_p = _extract_fuel_query_helpers(ctx.query)
    fuel_tools = FuelConvenienceTools(erp_adapter=ctx.erp_adapter, tools_facade=ctx.tools_facade)
    raw = fuel_tools.auditar_lmc_anp(data=data_p, combustivel=comb_p)
    return ToolExecutionResult(
        intent=ctx.intent,
        pack_id=PACK_ID,
        context_header="Auditoria de Conformidade LMC ANP (Portaria 26/1992):",
        raw_result=raw,
        source="cartridge:fuel_convenience",
    )


def _handle_vazao_bicos(ctx: ToolExecutionContext) -> ToolExecutionResult:
    data_p, turno_p, _ = _extract_fuel_query_helpers(ctx.query)
    fuel_tools = FuelConvenienceTools(erp_adapter=ctx.erp_adapter, tools_facade=ctx.tools_facade)
    raw = fuel_tools.auditar_vazao_bicos(data=data_p, turno=turno_p)
    return ToolExecutionResult(
        intent=ctx.intent,
        pack_id=PACK_ID,
        context_header="Auditoria de Vazao de Bicos e Desempenho de Pista:",
        raw_result=raw,
        source="cartridge:fuel_convenience",
    )


def _handle_benchmark_anp(ctx: ToolExecutionContext) -> ToolExecutionResult:
    data_p, turno_p, comb_p = _extract_fuel_query_helpers(ctx.query)
    fuel_tools = FuelConvenienceTools(erp_adapter=ctx.erp_adapter, tools_facade=ctx.tools_facade)
    raw = fuel_tools.comparar_benchmark_anp(data=data_p, turno=turno_p, produto=comb_p)
    return ToolExecutionResult(
        intent=ctx.intent,
        pack_id=PACK_ID,
        context_header="Benchmark Comparativo de Performance & Concorrencia ANP:",
        raw_result=raw,
        source="cartridge:fuel_convenience",
    )


def _handle_custo_estoque_macro(ctx: ToolExecutionContext) -> ToolExecutionResult:
    _, _, comb_p = _extract_fuel_query_helpers(ctx.query)
    fuel_tools = FuelConvenienceTools(erp_adapter=ctx.erp_adapter, tools_facade=ctx.tools_facade)
    raw = fuel_tools.analisar_custo_estoque_macro(produto=comb_p or "GASOLINA COMUM")
    return ToolExecutionResult(
        intent=ctx.intent,
        pack_id=PACK_ID,
        context_header="Custo de Carregamento de Estoque & Indicadores Macro (BACEN/CONFAZ):",
        raw_result=raw,
        source="cartridge:fuel_convenience",
    )


def register_fuel_convenience_cartridge(registry: DomainToolRegistry) -> None:
    """Registra todos os handlers exclusivos de posto no DomainToolRegistry."""
    for intent in ("lmc_anp", "lmc_compliance", "lmc", "auditar_conformidade_lmc_anp"):
        registry.register_pack_handler(PACK_ID, intent, _handle_lmc_anp)

    for intent in ("vazao_bicos", "desempenho_pista_frentistas"):
        registry.register_pack_handler(PACK_ID, intent, _handle_vazao_bicos)

    for intent in ("benchmark_anp", "benchmark_comparativo", "comparativo_turnos"):
        registry.register_pack_handler(PACK_ID, intent, _handle_benchmark_anp)

    for intent in ("custo_estoque_macro", "analisar_custo_estoque_macroeconomico"):
        registry.register_pack_handler(PACK_ID, intent, _handle_custo_estoque_macro)
