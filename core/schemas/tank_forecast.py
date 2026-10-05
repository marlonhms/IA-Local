"""
Contrato Estruturado Versionado para Previsão de Esgotamento de Tanques & Sugestão de Carretas (AURA Precision Glass v1.0).
F5-03 & F5-04: Autonomia até reserva crítica (15%) vs run-out (0L), saldo vs capacidade, ullage em bocas de 5.000 L.
"""
from __future__ import annotations
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict
from core.schemas.reconciliation import PendingItem, DataSource, RecommendedAction


class TankForecastAssessment(BaseModel):
    """Diagnóstico e severidade da autonomia volumétrica dos tanques."""
    model_config = ConfigDict(frozen=True)

    status_code: str = Field(..., description="Código de status geral (ex: ALERTA_ESTOQUE_CRITICO, ESTOQUE_ESTAVEL)")
    severity: Literal["normal", "attention", "critical"] = Field(..., description="Severidade semântica")
    title: str = Field(..., description="Título executivo da análise")
    limitation: Optional[str] = Field(None, description="Limitação operacional ou da base de dados")
    badge_label: str = Field(..., description="Rótulo humano para o badge semântico")
    alerta_fim_de_semana: bool = Field(default=False, description="True se houver risco de desabastecimento no fim de semana")
    horizonte_critico_horas: Optional[float] = Field(None, description="Menor autonomia até a reserva crítica de 15% (horas)")
    horizonte_runout_horas: Optional[float] = Field(None, description="Menor autonomia até esgotamento total (horas)")
    tanque_mais_critico_cod: Optional[str] = Field(None, description="Código do tanque mais crítico")


class TankForecastMetrics(BaseModel):
    """Métricas volumétricas consolidadas de autonomia e pedidos."""
    model_config = ConfigDict(frozen=True)

    saldo_total_litros: float = Field(..., description="Saldo consolidado em litros")
    capacidade_total_litros: float = Field(..., description="Capacidade máxima consolidada em litros")
    ocupacao_geral_pct: float = Field(..., description="Taxa média de ocupação dos tanques (%)")
    autonomia_critica_horas: float = Field(..., description="Autonomia consolidada até a reserva crítica (horas)")
    autonomia_critica_dias: float = Field(..., description="Autonomia consolidada até a reserva crítica (dias)")
    autonomia_runout_horas: float = Field(..., description="Autonomia consolidada até esgotamento total (horas)")
    autonomia_runout_dias: float = Field(..., description="Autonomia consolidada até esgotamento total (dias)")
    espaco_livre_ullage_total_litros: float = Field(..., description="Espaço livre total para descarga (L)")
    compartimentos_5k_total: int = Field(..., description="Quantidade total de compartimentos padrão de 5.000 L")
    volume_sugerido_total_litros: float = Field(..., description="Volume total sugerido para compra em carreta (L)")
    tanques_criticos_count: int = Field(default=0, description="Quantidade de tanques com alerta crítico")
    tanques_zerados_count: int = Field(default=0, description="Quantidade de tanques zerados/secos")


class TankDetailItem(BaseModel):
    """Detalhamento operacional individualizado de cada tanque de combustível."""
    model_config = ConfigDict(frozen=True)

    codtan: str = Field(..., description="Código do tanque")
    combustivel: str = Field(..., description="Nome do combustível")
    categoria: str = Field(..., description="Categoria canônica do combustível")
    capacidade_litros: float = Field(..., description="Capacidade física do tanque (L)")
    saldo_atual_litros: float = Field(..., description="Saldo atual medido (L)")
    ocupacao_pct: float = Field(..., description="Percentual de ocupação atual (%)")
    estoque_critico_15pct_litros: float = Field(..., description="Volume de segurança de 15% (L)")
    saldo_util_critico_litros: float = Field(..., description="Saldo acima da reserva crítica (L)")
    consumo_diario_litros: float = Field(..., description="Consumo médio diário projetado (L/dia)")
    consumo_horario_litros: float = Field(..., description="Consumo médio horário projetado (L/h)")
    autonomia_critica_horas: float = Field(..., description="Horas até atingir a reserva de 15%")
    autonomia_critica_dias: float = Field(..., description="Dias até atingir a reserva de 15%")
    autonomia_runout_horas: float = Field(..., description="Horas até esgotamento total (0 L)")
    autonomia_runout_dias: float = Field(..., description="Dias até esgotamento total (0 L)")
    espaco_livre_ullage_litros: float = Field(..., description="Espaço livre para descarga (L)")
    compartimentos_5k: int = Field(..., description="Compartimentos padrão de 5.000 L que cabem")
    volume_sugerido_litros: float = Field(..., description="Volume sugerido para descarga (L)")
    alerta_critico: bool = Field(..., description="True se abaixo de 15% ou esgotado")
    status_operacional: str = Field(..., description="Status operacional do tanque")
    urgencia_pedido: str = Field(..., description="Classificação da urgência de compra")
    prazo_ideal_compra: str = Field(..., description="Prazo recomendado para emissão do pedido")
    data_hora_critico: str = Field(..., description="Projeção de data/hora do nível crítico")
    data_hora_runout: str = Field(..., description="Projeção de data/hora do esgotamento total")
    bicos_conectados: List[str] = Field(default_factory=list, description="Lista de bicos que puxam deste tanque")


class FuelForecastItem(BaseModel):
    """Consolidação de autonomia e sugestão de compra por tipo de combustível."""
    model_config = ConfigDict(frozen=True)

    combustivel: str = Field(..., description="Nome do combustível")
    capacidade_total_litros: float = Field(..., description="Capacidade total consolidada (L)")
    saldo_total_litros: float = Field(..., description="Saldo total consolidado (L)")
    ocupacao_pct: float = Field(..., description="Percentual de ocupação médio (%)")
    autonomia_critica_dias: float = Field(..., description="Autonomia até reserva de 15% (dias)")
    autonomia_runout_dias: float = Field(..., description="Autonomia até esgotamento (dias)")
    autonomia_runout_horas: float = Field(..., description="Autonomia até esgotamento (horas)")
    volume_sugerido_compra_litros: float = Field(..., description="Volume sugerido para compra (L)")
    compartimentos_5k_sugeridos: int = Field(..., description="Compartimentos de 5k sugeridos")
    alerta_fim_de_semana: bool = Field(default=False, description="True se em risco no fim de semana")
    tanques_vinculados: List[str] = Field(default_factory=list, description="Tanques que armazenam este combustível")


class OrderSuggestionItem(BaseModel):
    """Sugestão inteligente de pedido em compartimentos padrão de 5.000 L."""
    model_config = ConfigDict(frozen=True)

    tanque: str = Field(..., description="Código do tanque")
    combustivel: str = Field(..., description="Combustível a ser comprado")
    categoria: str = Field(..., description="Categoria do combustível")
    volume_sugerido_litros: float = Field(..., description="Volume do pedido sugerido (L)")
    compartimentos_5k: int = Field(..., description="Bocas de 5.000 L sugeridas")
    espaco_livre_ullage_litros: float = Field(..., description="Espaço livre no tanque (L)")
    autonomia_critica_dias: float = Field(..., description="Autonomia crítica atual (dias)")
    autonomia_runout_horas: float = Field(..., description="Autonomia total atual (horas)")
    urgencia: str = Field(..., description="Grau de urgência")
    prazo_ideal: str = Field(..., description="Prazo ideal para compra")
    justificativa: str = Field(..., description="Justificativa operacional")


class TankForecastContext(BaseModel):
    """Contexto auditado com isolamento temporal e filtros aplicados."""
    model_config = ConfigDict(frozen=True, extra="allow")

    unit_id: str = Field(default="posto_01", description="Unidade do posto")
    queried_at: str = Field(..., description="Timestamp ISO da consulta")
    filtro_combustivel: Optional[str] = Field(None, description="Filtro de combustível ou tanque aplicado")
    data_referencia: Optional[str] = Field(None, description="Data de referência utilizada na projeção")


class TankForecastExplanation(BaseModel):
    """Explicação cognitiva isolada de dados numéricos oficiais."""
    model_config = ConfigDict(frozen=True, extra="allow")

    text: str = Field(..., description="Texto explicativo isolado")


class TankForecastContract(BaseModel):
    """Contrato oficial estruturado versionado para Previsão de Esgotamento de Tanques."""
    model_config = ConfigDict(frozen=True)

    schema_version: str = Field(default="1.0", description="Versão do contrato")
    response_id: str = Field(..., description="ID único da resposta analítica")
    intent: str = Field(default="tank_forecast", description="Intenção canônica")
    context: TankForecastContext = Field(...)
    assessment: TankForecastAssessment = Field(...)
    metrics: TankForecastMetrics = Field(...)
    tanks: List[TankDetailItem] = Field(default_factory=list)
    fuel_summary: List[FuelForecastItem] = Field(default_factory=list)
    order_suggestions: List[OrderSuggestionItem] = Field(default_factory=list)
    pending_items: List[PendingItem] = Field(default_factory=list)
    sources: List[DataSource] = Field(default_factory=list)
    recommended_action: RecommendedAction = Field(...)
    explanation: TankForecastExplanation = Field(...)
