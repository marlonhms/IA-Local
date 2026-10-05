"""
Contrato Estruturado Versionado para Market Basket Analysis & Combos da Conveniência (AURA Precision Glass v1.0).
F5-08: Associação de produtos, métricas de Suporte, Confiança e Lift (destaque para Lift >= 2.0), sem promessas irrealistas e com script prático para o operador de caixa.
"""
from __future__ import annotations
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict
from core.schemas.reconciliation import PendingItem, DataSource, RecommendedAction


class MarketBasketAssessment(BaseModel):
    """Diagnóstico estratégico de vendas cruzadas e cross-selling."""
    model_config = ConfigDict(frozen=True)

    status_code: str = Field(..., description="Status da auditoria (ex: SINERGIA_IDENTIFICADA, POUCAS_SINERGIAS, SEM_REGISTROS)")
    severity: Literal["normal", "attention", "critical"] = Field(..., description="Severidade semântica")
    title: str = Field(..., description="Título executivo da análise")
    limitation: Optional[str] = Field(None, description="Limitação da amostra de cupons e premissas estatísticas")
    badge_label: str = Field(..., description="Rótulo humano para o badge semântico")
    maior_lift: float = Field(..., description="Maior Lift encontrado na mineração de regras")
    regras_com_forte_sinergia_lift_2: int = Field(default=0, description="Quantidade de combos com Lift >= 2.0x")


class MarketBasketMetrics(BaseModel):
    """Métricas canônicas de Market Basket Analysis e cesta de compras."""
    model_config = ConfigDict(frozen=True)

    total_transacoes_analisadas: int = Field(..., description="Total de pedidos/cupons fiscais analisados")
    total_transacoes_multiplos_itens: int = Field(..., description="Cupons contendo 2 ou mais itens distintos")
    pct_cestas_multiplos_itens: float = Field(..., description="Percentual de compras com cross-selling natural (%)")
    total_itens_distintos: int = Field(..., description="Variedade de SKUs distintos minerados")
    total_regras_geradas: int = Field(..., description="Total de regras de associação descobertas")
    regras_forte_sinergia_count: int = Field(..., description="Quantidade de regras com Lift >= 2.0x")
    maior_lift: float = Field(..., description="Maior valor de Lift apurado")
    ticket_medio_reais: float = Field(..., description="Ticket médio global da loja de conveniência (R$)")


class MarketBasketComboItem(BaseModel):
    """Combo acionável de venda cruzada no balcão/PDV."""
    model_config = ConfigDict(frozen=True)

    produto_origem: str = Field(..., description="Produto âncora/origem comprado pelo cliente")
    produto_recomendado: str = Field(..., description="Produto complementar sugerido para venda cruzada")
    suporte_conjunto_pct: float = Field(..., description="Suporte da associação (%)")
    confianca_pct: float = Field(..., description="Confiança condicional P(B|A) (%)")
    lift: float = Field(..., description="Multiplicador de Lift (força da sinergia)")
    cupons_conjuntos: int = Field(..., description="Número de cupons que contêm ambos os itens")
    ticket_origem_reais: float = Field(default=0.0, description="Preço unitário médio do produto de origem (R$)")
    ticket_recomendado_reais: float = Field(default=0.0, description="Preço unitário médio do produto sugerido (R$)")
    script_sugerido_caixa: str = Field(..., description="Script prático e persuasivo para o operador de caixa")
    forte_sinergia: bool = Field(default=False, description="True se Lift >= 2.0 indicando alta probabilidade de conversão")


class MarketBasketRuleItem(BaseModel):
    """Regra técnica detalhada da mineração de associação."""
    model_config = ConfigDict(frozen=True)

    regra: str = Field(..., description="Apresentação formal da regra A -> B")
    suporte: float = Field(..., description="Suporte conjunto")
    confianca: float = Field(..., description="Confiança da regra")
    lift: float = Field(..., description="Multiplicador Lift")
    frequencia_conjunta: int = Field(..., description="Frequência em cupons")
    forte_sinergia: bool = Field(..., description="True se Lift >= 2.0")


class MarketBasketContext(BaseModel):
    """Contexto da auditoria de Market Basket."""
    model_config = ConfigDict(frozen=True, extra="allow")

    unit_id: str = Field(default="posto_01", description="Unidade do posto")
    queried_at: str = Field(..., description="Timestamp ISO da consulta")
    filtro_produto: Optional[str] = Field(None, description="Filtro de produto/SKU aplicado")
    min_lift: float = Field(default=1.2, description="Limiar mínimo de Lift adotado")
    min_suporte: float = Field(default=0.005, description="Limiar mínimo de Suporte adotado")
    min_confianca: float = Field(default=0.05, description="Limiar mínimo de Confiança adotado")
    data_inicio: Optional[str] = Field(None, description="Data início do recorte")
    data_fim: Optional[str] = Field(None, description="Data fim do recorte")


class MarketBasketExplanation(BaseModel):
    """Explicação cognitiva isolada de dados numéricos oficiais."""
    model_config = ConfigDict(frozen=True, extra="allow")

    text: str = Field(..., description="Texto explicativo isolado")


class MarketBasketContract(BaseModel):
    """Contrato oficial estruturado versionado para Market Basket da Conveniência."""
    model_config = ConfigDict(frozen=True)

    schema_version: str = Field(default="1.0", description="Versão do contrato")
    response_id: str = Field(..., description="ID único da resposta analítica")
    intent: str = Field(default="market_basket", description="Intenção canônica")
    context: MarketBasketContext = Field(...)
    assessment: MarketBasketAssessment = Field(...)
    metrics: MarketBasketMetrics = Field(...)
    top_combos: List[MarketBasketComboItem] = Field(default_factory=list)
    detailed_rules: List[MarketBasketRuleItem] = Field(default_factory=list)
    pending_items: List[PendingItem] = Field(default_factory=list)
    sources: List[DataSource] = Field(default_factory=list)
    recommended_action: RecommendedAction = Field(...)
    explanation: MarketBasketExplanation = Field(...)
