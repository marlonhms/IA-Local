"""Registro Agnostico de Ferramentas por Dominio (Carbon Core P1.1).

Despacha intencoes universais (auditoria_turno_caixa, previsao_runout_estoque,
market_basket_cross_sell, simular_cenario_what_if) operando estritamente sobre
BaseERPAdapter + entidades canonicas AUDS (UniversalSaleTransaction,
UniversalInventoryNode, UniversalCashierSession), e delega intencoes exclusivas
de vertical para cartuchos dedicados (ex: core/packs/fuel_convenience/).
Zero travessoes em todo o modulo.
"""

from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass, field
from itertools import combinations
from typing import Any, Callable

from core.adapters.erp.base import BaseERPAdapter
from core.domain.domain_pack_loader import DomainPackConfig, get_active_domain_pack

logger = logging.getLogger("DomainToolRegistry")


@dataclass(frozen=True)
class ToolExecutionContext:
    """Contexto imutavel passado aos handlers do DomainToolRegistry."""

    intent: str
    query: str
    domain_pack: DomainPackConfig
    erp_adapter: BaseERPAdapter
    tools_facade: Any = None
    extra_params: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ToolExecutionResult:
    """Resultado estruturado retornado por um handler do DomainToolRegistry."""

    intent: str
    pack_id: str
    context_header: str
    raw_result: dict[str, Any]
    source: str = "universal_auds"


ToolHandler = Callable[[ToolExecutionContext], ToolExecutionResult]


def _run_universal_cashier_shift_audit(ctx: ToolExecutionContext) -> ToolExecutionResult:
    """Auditoria deterministica de fechamento de turno/caixa sobre BaseERPAdapter + AUDS."""
    shifts = ctx.erp_adapter.get_cashier_shifts(limit=50)
    sales = ctx.erp_adapter.get_recent_sales(limit=200)
    cash_tol = float(ctx.domain_pack.get_tolerance("cash_tolerance_reais", 10.0))

    total_declarado = round(sum(float(s.total_declarado_reais) for s in shifts), 2)
    total_sistema = round(sum(float(s.total_sistema_reais) for s in shifts), 2)
    diferenca_total = round(total_declarado - total_sistema, 2)
    total_vendas_pdv = round(sum(float(v.total_reais) for v in sales), 2)

    turnos_fora_tolerancia = []
    for s in shifts:
        quebra = round(float(s.quebra_sobra_reais), 2)
        if abs(quebra) > cash_tol:
            turnos_fora_tolerancia.append({
                "caixa_id": s.caixa_id,
                "pdv": s.pdv,
                "operador": s.operador_nome,
                "turno": s.turno_descricao,
                "declarado_reais": round(float(s.total_declarado_reais), 2),
                "sistema_reais": round(float(s.total_sistema_reais), 2),
                "diferenca_reais": quebra,
            })

    status_audit = "ALERTA_DIVERGENCIA" if turnos_fora_tolerancia else "CONFORME"
    operator_label = ctx.domain_pack.get_vocabulary_term("operator", "operador")
    session_label = ctx.domain_pack.get_vocabulary_term("cashier_session", "turno_caixa")

    payload = {
        "status": status_audit,
        "pack_id": ctx.domain_pack.pack_id,
        "pack_name": ctx.domain_pack.pack_name,
        "vertical": ctx.domain_pack.vertical,
        "intent": ctx.intent,
        "adapter": ctx.erp_adapter.adapter_name,
        "tolerancia_caixa_reais": cash_tol,
        "total_turnos_auditados": len(shifts),
        "total_cupons_recentes": len(sales),
        "total_declarado_reais": total_declarado,
        "total_sistema_reais": total_sistema,
        "diferenca_total_reais": diferenca_total,
        "faturamento_cupons_reais": total_vendas_pdv,
        "turnos_fora_tolerancia": turnos_fora_tolerancia,
        "vocabulario_aplicado": {
            "operador": operator_label,
            "sessao_caixa": session_label,
        },
        "deterministico": True,
    }
    return ToolExecutionResult(
        intent=ctx.intent,
        pack_id=ctx.domain_pack.pack_id,
        context_header=(
            f"Auditoria Deterministica de {session_label} ({ctx.domain_pack.pack_name} / AUDS BaseERPAdapter):"
        ),
        raw_result=payload,
        source="universal_auds",
    )


def _run_universal_stock_runout_forecast(ctx: ToolExecutionContext) -> ToolExecutionResult:
    """Previsao deterministica de estoque/ruptura sobre BaseERPAdapter + AUDS."""
    catalog = ctx.erp_adapter.get_product_catalog(limit=100)
    sales = ctx.erp_adapter.get_recent_sales(limit=200)
    lot_multiple = float(ctx.domain_pack.get_tolerance("default_lot_multiple", 1.0)) or 1.0
    stock_unit = ctx.domain_pack.get_vocabulary_term("stock_unit", "UN")
    node_label = ctx.domain_pack.get_vocabulary_term("inventory_node", "estoque")

    demanda_por_sku: Counter[str] = Counter()
    for sale in sales:
        for item in sale.itens:
            demanda_por_sku[item.sku] += float(item.quantidade)

    itens_analisados = []
    for prod in catalog[:25]:
        demanda = round(float(demanda_por_sku.get(prod.sku, 0.0)), 3)
        sugestao_lotes = max(1, int(-(-demanda // lot_multiple))) if demanda > 0 else 0
        itens_analisados.append({
            "sku": prod.sku,
            "descricao": prod.descricao_produto,
            "grupo": prod.grupo_comercial,
            "preco_unitario_reais": round(float(prod.preco_unitario_reais), 2),
            "demanda_periodo": demanda,
            "unidade_medida": stock_unit,
            "lote_multiplo": lot_multiple,
            "lotes_sugeridos": sugestao_lotes,
        })

    itens_analisados.sort(key=lambda x: x["demanda_periodo"], reverse=True)

    payload = {
        "status": "OK",
        "pack_id": ctx.domain_pack.pack_id,
        "pack_name": ctx.domain_pack.pack_name,
        "vertical": ctx.domain_pack.vertical,
        "intent": ctx.intent,
        "adapter": ctx.erp_adapter.adapter_name,
        "unidade_estoque": stock_unit,
        "no_inventario": node_label,
        "lote_padrao": lot_multiple,
        "total_skus_catalogo": len(catalog),
        "total_cupons_analisados": len(sales),
        "itens_prioritarios": itens_analisados[:10],
        "deterministico": True,
    }
    return ToolExecutionResult(
        intent=ctx.intent,
        pack_id=ctx.domain_pack.pack_id,
        context_header=(
            f"Previsao Deterministica de Estoque / Ruptura ({ctx.domain_pack.pack_name} / AUDS BaseERPAdapter):"
        ),
        raw_result=payload,
        source="universal_auds",
    )


def _run_universal_market_basket(ctx: ToolExecutionContext) -> ToolExecutionResult:
    """Mineracao deterministica de Market Basket / Cross-Sell sobre BaseERPAdapter + AUDS."""
    sales = ctx.erp_adapter.get_recent_sales(limit=300)
    total_tx = len(sales)
    item_counts: Counter[str] = Counter()
    pair_counts: Counter[tuple[str, str]] = Counter()
    multi_item_tx = 0

    for sale in sales:
        unique_names = sorted({
            str(it.descricao_produto or it.sku).strip()
            for it in sale.itens
            if (it.descricao_produto or it.sku)
        })
        if len(unique_names) >= 2:
            multi_item_tx += 1
        for name in unique_names:
            item_counts[name] += 1
        for a, b in combinations(unique_names, 2):
            pair_counts[(a, b)] += 1

    combos = []
    if total_tx > 0:
        for (a, b), count_ab in pair_counts.most_common(10):
            supp_ab = count_ab / total_tx
            supp_a = item_counts[a] / total_tx
            supp_b = item_counts[b] / total_tx
            conf = count_ab / max(item_counts[a], 1)
            lift = supp_ab / max(supp_a * supp_b, 1e-9)
            combos.append({
                "anchor_product": a,
                "recommended_product": b,
                "coocorrencias": count_ab,
                "support_pct": round(supp_ab * 100.0, 2),
                "confidence_pct": round(conf * 100.0, 1),
                "lift": round(lift, 2),
            })

    payload = {
        "status": "OK",
        "pack_id": ctx.domain_pack.pack_id,
        "pack_name": ctx.domain_pack.pack_name,
        "vertical": ctx.domain_pack.vertical,
        "intent": ctx.intent,
        "adapter": ctx.erp_adapter.adapter_name,
        "total_transacoes_analisadas": total_tx,
        "cestas_multiplos_itens": multi_item_tx,
        "pct_cestas_multiplos_itens": round((multi_item_tx / total_tx) * 100.0, 2) if total_tx else 0.0,
        "top_combos": combos,
        "deterministico": True,
    }
    return ToolExecutionResult(
        intent=ctx.intent,
        pack_id=ctx.domain_pack.pack_id,
        context_header=(
            f"Analise Deterministica Market Basket & Cross-Sell ({ctx.domain_pack.pack_name} / AUDS BaseERPAdapter):"
        ),
        raw_result=payload,
        source="universal_auds",
    )


def _run_universal_what_if(ctx: ToolExecutionContext) -> ToolExecutionResult:
    """Despacha simulacao deterministica What-If em Python puro."""
    from core.whatif_simulator import run_whatif_simulation

    params = dict(ctx.extra_params)
    sim_type = str(params.get("simulation_type") or "price_change")
    params["simulation_type"] = sim_type
    if sim_type == "price_change" and "current_price" not in params:
        catalog = ctx.erp_adapter.get_product_catalog(limit=5)
        first_item = catalog[0] if catalog else None
        price = float(first_item.preco_unitario_reais) if first_item and first_item.preco_unitario_reais > 0 else 10.0
        params.setdefault("product_name", first_item.descricao_produto if first_item else "Produto Principal")
        params.setdefault("current_price", price)
        params.setdefault("unit_cost", round(price * 0.72, 2))
        params.setdefault("daily_volume", 100.0)
        params.setdefault("price_delta", round(price * 0.05, 2))

    res = run_whatif_simulation(params)
    res["pack_id"] = ctx.domain_pack.pack_id
    res["adapter"] = ctx.erp_adapter.adapter_name
    return ToolExecutionResult(
        intent=ctx.intent,
        pack_id=ctx.domain_pack.pack_id,
        context_header=f"Simulador Deterministico What-If ({ctx.domain_pack.pack_name}):",
        raw_result=res,
        source="universal_auds",
    )


def _run_generic_vertical_specific_intent(ctx: ToolExecutionContext) -> ToolExecutionResult:
    """Executa auditoria deterministica agnostica para specific_intents de packs nao-posto.

    Opera 100% sobre BaseERPAdapter (vendas, catalogo, caixa) e tolerancias do YAML
    do DomainPack ativo, sem nunca acessar tabelas proprietarias de combustivel.
    """
    sales = ctx.erp_adapter.get_recent_sales(limit=100)
    catalog = ctx.erp_adapter.get_product_catalog(limit=100)
    shifts = ctx.erp_adapter.get_cashier_shifts(limit=20)

    spec_item = next(
        (item for item in ctx.domain_pack.specific_intents if item.id == ctx.intent),
        None,
    )
    total_faturado = round(sum(float(s.total_reais) for s in sales), 2)
    total_itens_vendidos = round(
        sum(float(it.quantidade) for s in sales for it in s.itens),
        2,
    )
    total_quebra_caixa = round(sum(float(sh.quebra_sobra_reais) for sh in shifts), 2)

    payload = {
        "status": "OK",
        "pack_id": ctx.domain_pack.pack_id,
        "pack_name": ctx.domain_pack.pack_name,
        "vertical": ctx.domain_pack.vertical,
        "intent": ctx.intent,
        "descricao_intencao": spec_item.descricao if spec_item else ctx.intent,
        "adapter": ctx.erp_adapter.adapter_name,
        "metricas_erp_auds": {
            "total_cupons_recentes": len(sales),
            "faturamento_recente_reais": total_faturado,
            "total_unidades_vendidas": total_itens_vendidos,
            "skus_ativos_catalogo": len(catalog),
            "turnos_caixa_auditados": len(shifts),
            "saldo_diferenca_caixa_reais": total_quebra_caixa,
        },
        "tolerancias_pack": dict(ctx.domain_pack.tolerances),
        "vocabulario_pack": dict(ctx.domain_pack.vocabulary),
        "tabelas_legadas_posto_acessadas": False,
        "deterministico": True,
    }
    return ToolExecutionResult(
        intent=ctx.intent,
        pack_id=ctx.domain_pack.pack_id,
        context_header=(
            f"Auditoria Vertical [{ctx.intent}] ({ctx.domain_pack.pack_name} / AUDS BaseERPAdapter):"
        ),
        raw_result=payload,
        source=f"pack:{ctx.domain_pack.pack_id}",
    )


class DomainToolRegistry:
    """Registro central agnostico de tools universais e cartuchos verticais (P1.1)."""

    def __init__(self) -> None:
        self._universal_handlers: dict[str, ToolHandler] = {}
        self._pack_handlers: dict[str, dict[str, ToolHandler]] = {}

    def register_universal(self, intent: str, handler: ToolHandler) -> None:
        """Registra um handler universal AUDS disponivel para todas as verticais."""
        self._universal_handlers[intent.strip().lower()] = handler

    def register_pack_handler(self, pack_id: str, intent: str, handler: ToolHandler) -> None:
        """Registra um handler especifico de um cartucho vertical (ex: fuel_convenience)."""
        p_key = pack_id.strip().lower()
        i_key = intent.strip().lower()
        self._pack_handlers.setdefault(p_key, {})[i_key] = handler

    def list_universal_intents(self) -> list[str]:
        """Lista intencoes universais registradas no nucleo agnostico."""
        return sorted(self._universal_handlers.keys())

    def list_pack_intents(self, pack_id: str) -> list[str]:
        """Lista intencoes especificas registradas para um pack."""
        return sorted(self._pack_handlers.get(pack_id.strip().lower(), {}).keys())

    def resolve_handler(
        self,
        intent: str,
        domain_pack: DomainPackConfig,
    ) -> ToolHandler | None:
        """Resolve o handler mais especifico para (domain_pack, intent).

        Ordem de resolucao:
        1. Handler explicito do cartucho do pack ativo;
        2. Handler universal direto (ex: auditoria_turno_caixa, previsao_runout_estoque);
        3. Mapeamento reverso via domain_pack.intent_mappings (ex: fechamento_caixa_pbm -> auditoria_turno_caixa);
        4. Handler agnostico para specific_intents declaradas no YAML do pack ativo.
        """
        norm_intent = (intent or "").strip().lower()
        pack_key = domain_pack.pack_id.strip().lower()

        # 1. Handler dedicado do cartucho vertical
        pack_map = self._pack_handlers.get(pack_key, {})
        if norm_intent in pack_map:
            return pack_map[norm_intent]

        # 2. Handler universal direto
        if norm_intent in self._universal_handlers:
            return self._universal_handlers[norm_intent]

        # 3. Mapeamento reverso: intencao vertical mapeada no YAML -> handler universal AUDS
        for universal_intent, mapped_vertical_intent in domain_pack.intent_mappings.items():
            if mapped_vertical_intent.strip().lower() == norm_intent:
                if universal_intent.strip().lower() in self._universal_handlers:
                    return self._universal_handlers[universal_intent.strip().lower()]

        # 4. Specific intent declarada no YAML do pack ativo (sem tocar tabelas legadas de posto)
        specific_ids = {item.id.strip().lower() for item in domain_pack.specific_intents}
        if norm_intent in specific_ids:
            return _run_generic_vertical_specific_intent

        return None

    def can_handle(self, intent: str, domain_pack: DomainPackConfig | None = None) -> bool:
        """Indica se o registro possui handler para a intencao no pack ativo."""
        pack = domain_pack or get_active_domain_pack()
        return self.resolve_handler(intent, pack) is not None

    def dispatch(
        self,
        intent: str,
        query: str,
        erp_adapter: BaseERPAdapter,
        domain_pack: DomainPackConfig | None = None,
        tools_facade: Any = None,
        extra_params: dict[str, Any] | None = None,
    ) -> ToolExecutionResult | None:
        """Executa o handler resolvido retornando ToolExecutionResult ou None."""
        pack = domain_pack or get_active_domain_pack()
        handler = self.resolve_handler(intent, pack)
        if handler is None:
            return None

        ctx = ToolExecutionContext(
            intent=intent,
            query=query,
            domain_pack=pack,
            erp_adapter=erp_adapter,
            tools_facade=tools_facade,
            extra_params=dict(extra_params or {}),
        )
        return handler(ctx)


def create_default_tool_registry() -> DomainToolRegistry:
    """Cria instancia padrao do DomainToolRegistry com tools universais e cartucho fuel_convenience."""
    registry = DomainToolRegistry()

    # Tools Universais AUDS (BaseERPAdapter + entidades canonicas)
    registry.register_universal("auditoria_turno_caixa", _run_universal_cashier_shift_audit)
    registry.register_universal("previsao_runout_estoque", _run_universal_stock_runout_forecast)
    registry.register_universal("market_basket_cross_sell", _run_universal_market_basket)
    registry.register_universal("simular_cenario_what_if", _run_universal_what_if)
    registry.register_universal("what_if", _run_universal_what_if)
    registry.register_universal("whatif", _run_universal_what_if)

    # Registra o cartucho vertical de postos de combustiveis (isolado do core agnostico)
    from core.packs.fuel_convenience.tools import register_fuel_convenience_cartridge

    register_fuel_convenience_cartridge(registry)
    return registry
