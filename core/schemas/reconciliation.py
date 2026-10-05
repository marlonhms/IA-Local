"""
Contrato Estruturado Versionado para Conciliação de Turno & Caixa (AURA Precision Glass v1.0).
Garante semântica estrita, distinção entre null e zero, separação entre cálculo e explicação,
e prevenção contra apresentação de análises parciais como quebras definitivas.
"""
from __future__ import annotations
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict


class ReconciliationAssessment(BaseModel):
    """Diagnóstico e severidade do fechamento de turno."""
    model_config = ConfigDict(frozen=True)

    finality: Literal["partial", "final", "no_movement", "unavailable"] = Field(
        ...,
        description="Finalidade da análise: 'partial' para turnos com caixas abertos ou encerrantes pendentes; 'final' para fechamento definitivo; 'no_movement' para sem dados; 'unavailable' para erro."
    )
    severity: Literal["normal", "attention", "critical"] = Field(
        ...,
        description="Severidade: normal (conciliado/conforme), attention (análise parcial/alerta preventivo), critical (furo/divergência confirmada)."
    )
    status_code: str = Field(..., description="Código técnico legível (ex: TURNO_EM_ANDAMENTO, CONCILIADO, FURO_DE_CAIXA)")
    title: str = Field(..., description="Título executivo aprovado para a resposta")
    limitation: Optional[str] = Field(None, description="Limitação técnica ou operacional que afeta a interpretação do dado")
    badge_label: str = Field(..., description="Rótulo humano exibido no badge semântico de status")


class ReconciliationMetrics(BaseModel):
    """Métricas financeiras e volumétricas tipadas da conciliação."""
    model_config = ConfigDict(frozen=True)

    automation_revenue: float = Field(..., description="Faturamento medido pela automação Companytec CBC04 (R$)")
    automation_revenue_cents: int = Field(..., description="Faturamento da automação em centavos inteiros")
    pos_revenue: float = Field(..., description="Faturamento registrado nos caixas/pedidos PDV (R$)")
    pos_revenue_cents: int = Field(..., description="Faturamento do PDV em centavos inteiros")
    difference: float = Field(..., description="Diferença financeira (pos - automação) em R$")
    difference_cents: int = Field(..., description="Diferença financeira em centavos inteiros")
    difference_definition: str = Field(
        default="pos_minus_automation",
        description="Definição contábil da diferença: faturamento_pdv menos faturamento_automacao"
    )
    physical_volume_liters: Optional[float] = Field(
        None,
        description="Volume físico medido por encerrantes em litros (null quando pendente/não reportado, nunca convertido em zero falso)"
    )
    physical_volume_state: Literal["not_reported", "measured", "zero_registered"] = Field(
        default="not_reported",
        description="Estado da medição física: 'not_reported' (pendente), 'measured' (medido e faturado), 'zero_registered' (zero confirmado)"
    )
    automation_volume_liters: float = Field(..., description="Volume medido pela automação em tempo real (L)")
    is_provisional: bool = Field(
        ...,
        description="True se a diferença ainda for provisória (caixa aberto ou encerrante pendente); False se definitiva."
    )


class PendingItem(BaseModel):
    """Item impeditivo ou pendência operacional verificável."""
    model_config = ConfigDict(frozen=True)

    code: str = Field(..., description="Código canônico da pendência (ex: physical_readings_missing, registers_open)")
    label: str = Field(..., description="Rótulo legível humano")
    detail: Optional[str] = Field(None, description="Detalhamento operacional da pendência")
    severity: str = Field(default="attention", description="Severidade da pendência: 'attention' ou 'critical'")


class DataSource(BaseModel):
    """Proveniência e disponibilidade de fontes de dados no ERP."""
    model_config = ConfigDict(frozen=True)

    id: str = Field(..., description="Identificador da fonte (automation, pos, physical_readings, tanks)")
    label: str = Field(..., description="Nome humano amigável da fonte")
    availability: Literal["available", "missing", "unavailable"] = Field(
        ...,
        description="Disponibilidade: available (disponível), missing (não reportado/pendente), unavailable (erro/desconectado)"
    )
    data_as_of: Optional[str] = Field(None, description="Data/hora do dado mais recente da fonte")


class RecommendedAction(BaseModel):
    """Ação permitida recomendada ao gestor (sempre segura e manual externa ao ERP)."""
    model_config = ConfigDict(frozen=True)

    label: str = Field(..., description="Texto do botão ou ação recomendada")
    execution: str = Field(default="external_manual", description="Tipo de execução: 'external_manual' (ação no ERP físico)")
    detail: Optional[str] = Field(None, description="Orientação de como proceder")


class ReconciliationContext(BaseModel):
    """Contexto auditado com isolamento temporal e de unidade (Fase 1 / F1-07 e F1-11)."""
    model_config = ConfigDict(frozen=True, extra="allow")

    unit_id: str = Field(default="posto_01", description="Identificador único da unidade/filial auditada")
    shift_id: str = Field(default="todos", description="Turno auditado ou 'todos'")
    queried_at: str = Field(..., description="Timestamp ISO-8601 exato do momento da consulta da auditoria")
    data_auditada: Optional[str] = Field(None, description="Data efetiva dos dados auditados (YYYY-MM-DD)")
    data_solicitada: Optional[str] = Field(None, description="Parâmetro original de data solicitado pelo usuário")
    turno_solicitado: Optional[str] = Field(None, description="Parâmetro original de turno solicitado pelo usuário")
    period_start: Optional[str] = Field(None, description="Início do período contábil")
    period_end: Optional[str] = Field(None, description="Fim do período contábil")
    error: Optional[str] = Field(None, description="Detalhe de erro em caso de indisponibilidade de fonte")


class ReconciliationExplanation(BaseModel):
    """Explicação cognitiva isolada de dados numéricos oficiais (F1-09)."""
    model_config = ConfigDict(frozen=True, extra="allow")

    text: str = Field(..., description="Texto explicativo da auditoria")


class ShiftReconciliationContract(BaseModel):
    """Contrato oficial estruturado versionado para Conciliação de Turno & Caixa."""
    model_config = ConfigDict(frozen=True)

    schema_version: str = Field(default="1.0", description="Versão do schema do contrato")
    response_id: str = Field(..., description="Identificador único da resposta analítica")
    intent: str = Field(default="shift_reconciliation", description="Intenção canônica")
    context: ReconciliationContext = Field(..., description="Contexto da consulta (unidade, turno, data auditada, período)")
    assessment: ReconciliationAssessment = Field(..., description="Avaliação executiva de finalidade e severidade")
    metrics: ReconciliationMetrics = Field(..., description="Métricas financeiras e volumétricas oficiais")
    pending_items: List[PendingItem] = Field(default_factory=list, description="Pendências verificáveis")
    sources: List[DataSource] = Field(default_factory=list, description="Fontes auditadas e disponibilidade")
    recommended_action: RecommendedAction = Field(..., description="Próximo passo recomendado")
    explanation: ReconciliationExplanation = Field(..., description="Texto explicativo gerado de forma isolada dos números oficiais")
